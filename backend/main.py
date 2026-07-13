import base64
import hashlib
import hmac
import json
import math
import os
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import DEPARTMENTS, MODULE_DESCRIPTIONS, MODULE_FIELDS, storage

load_dotenv()
load_dotenv(Path(__file__).with_name(".env"))
app = FastAPI(title="FactoryPulse Global ERP API", version="0.5.0")
origins = [origin.strip() for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:8080").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@factorypulse.local")
ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "")
APP_SECRET_KEY = os.getenv("APP_SECRET_KEY", "")
AUTH_CONFIGURED = bool(APP_SECRET_KEY)
MAX_LOGIN_ATTEMPTS = int(os.getenv("MAX_LOGIN_ATTEMPTS", "5"))
LOGIN_LOCK_SECONDS = int(os.getenv("LOGIN_LOCK_SECONDS", "900"))

class LoginRequest(BaseModel):
    email: str
    password: str

class RecordCreate(BaseModel):
    data: dict[str, Any]

class EmployeeAttendanceEvent(BaseModel):
    employee_code: str | None = None
    shift: str = "General"
    latitude: float | None = None
    longitude: float | None = None
    accuracy: float | None = None
    note: str | None = None

class EmployeeLocationPing(BaseModel):
    employee_code: str | None = None
    latitude: float
    longitude: float
    accuracy: float | None = None
    event: str = "tracking"

class LeaveApplyRequest(BaseModel):
    employee_code: str | None = None
    leave_type: str
    from_date: str
    to_date: str
    reason: str

class AttendanceCorrectionRequest(BaseModel):
    attendance_date: str
    requested_day_in_time: str | None = None
    requested_day_out_time: str | None = None
    reason: str
    requested_changes: str | None = None

class LocationValidationRequest(BaseModel):
    event_type: str = "day_in"
    latitude: float
    longitude: float
    accuracy: float
    altitude: float | None = None
    speed: float | None = None
    provider: str = "device_gps"
    captured_at: str | None = None
    device_time: str | None = None
    device_id: str | None = None
    app_version: str | None = None
    mock_location_indicator: str | None = None

class BiometricVerificationRequest(BaseModel):
    event_type: str = "day_in"
    attendance_record_id: str | None = None
    verification_method: str
    verification_result: str
    assertion_reference: str | None = None
    trusted_device_id: str | None = None
    failure_reason: str | None = None
    risk_flags: str | None = None

class PayrollGenerateRequest(BaseModel):
    period_id: str | None = None
    period_name: str
    start_date: str
    end_date: str
    company: str | None = None
    branch: str | None = None
    department: str | None = None
    dry_run: bool = False

class HrEmployeeOnboardingRequest(BaseModel):
    employee_code: str
    full_name: str
    department: str
    role: str
    phone: str | None = None
    email: str
    shift: str = "General"
    status: str = "Active"
    date_of_birth: str | None = None
    gender: str | None = None
    nationality: str | None = None
    tax_identifier_ref: str | None = None
    bank_name: str | None = None
    account_last4: str | None = None
    ifsc_or_routing: str | None = None
    document_type: str | None = None
    document_no_masked: str | None = None
    document_expiry_date: str | None = None
    emergency_contact_name: str | None = None
    emergency_relationship: str | None = None
    emergency_phone: str | None = None
    emergency_address: str | None = None
    location_id: str | None = None
    location_assignment_type: str = "Primary"
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    salary_structure_id: str | None = None
    gross_salary: str | None = None
    ctc: str | None = None
    trusted_device_id: str | None = None
    device_platform: str | None = None
    device_name: str | None = None
    app_version: str | None = None
    lifecycle_reason: str = "Employee onboarded from HR command center"

class HrLifecycleEventRequest(BaseModel):
    employee_code: str
    event_type: str
    effective_date: str
    previous_value: str | None = None
    new_value: str
    reason: str
    approved_by: str | None = None
    status: str = "Approved"

def _sign(email: str) -> str:
    if not AUTH_CONFIGURED:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    payload = f"{email}:{int(time.time()) + 28800}"
    sig = hmac.new(APP_SECRET_KEY.encode(), payload.encode(), "sha256").hexdigest()
    return f"{payload}:{sig}"

def _verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algorithm, iterations, salt, expected = password_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt), int(iterations))
        actual = base64.b64encode(digest).decode()
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _locked_until_epoch(value: Any) -> int:
    if not value:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0

def _login_user(email: str, password: str):
    email = email.strip().lower()
    rpc_user = storage.authenticate_user(email, password)
    if rpc_user:
        return rpc_user
    user = storage.get_user_by_email(email)
    if user and user.get("status", "Active") != "Active":
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if user and _locked_until_epoch(user.get("locked_until")) > int(time.time()):
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again later.")
    if user and _verify_password(password, user.get("password_hash")):
        storage.record_login_success(email)
        return {
            "email": email,
            "name": user.get("full_name") or "FactoryPulse Admin",
            "role": user.get("role") or "FACTORY_ADMIN",
        }
    if user:
        storage.record_login_failure(email, MAX_LOGIN_ATTEMPTS, LOGIN_LOCK_SECONDS)
    if ADMIN_PASSWORD and email == ADMIN_EMAIL.strip().lower() and hmac.compare_digest(password, ADMIN_PASSWORD):
        return {"email": email, "name": "FactoryPulse Admin", "role": "FACTORY_ADMIN"}
    raise HTTPException(status_code=401, detail="Invalid email or password")

def _verify(authorization: str | None = Header(default=None)) -> str:
    if not AUTH_CONFIGURED:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        email, exp, sig = token.rsplit(":", 2)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    payload = f"{email}:{exp}"
    expected = hmac.new(APP_SECRET_KEY.encode(), payload.encode(), "sha256").hexdigest()
    if not hmac.compare_digest(sig, expected) or int(exp) < int(time.time()):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return email

def _employee_code(email: str, supplied: str | None = None) -> str:
    return email.strip().lower()

def _today() -> str:
    return date.today().isoformat()

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def _hhmm() -> str:
    return datetime.now().strftime("%H:%M")

def _gps(payload: EmployeeAttendanceEvent | EmployeeLocationPing) -> str:
    if payload.latitude is None or payload.longitude is None:
        return ""
    bits = [f"{payload.latitude:.6f}", f"{payload.longitude:.6f}"]
    if payload.accuracy is not None:
        bits.append(f"accuracy {payload.accuracy:.0f}m")
    return ", ".join(bits)

def _new_ref(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12].upper()}"

def _float_value(data: dict[str, Any], key: str, default: float = 0.0) -> float:
    try:
        value = data.get(key)
        return default if value in (None, "") else float(value)
    except (TypeError, ValueError):
        return default

def _json_points(value: str | None) -> list[tuple[float, float]]:
    if not value:
        return []
    try:
        raw = json.loads(value)
    except json.JSONDecodeError:
        return []
    points = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                lat = item.get("latitude") or item.get("lat")
                lon = item.get("longitude") or item.get("lng") or item.get("lon")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                lat, lon = item[0], item[1]
            else:
                continue
            try:
                points.append((float(lat), float(lon)))
            except (TypeError, ValueError):
                continue
    return points

def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371000.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def _point_in_polygon(latitude: float, longitude: float, points: list[tuple[float, float]]) -> bool:
    if len(points) < 3:
        return False
    inside = False
    j = len(points) - 1
    for i, point in enumerate(points):
        yi, xi = point
        yj, xj = points[j]
        crosses = (xi > longitude) != (xj > longitude)
        if crosses:
            slope_lat = (yj - yi) * (longitude - xi) / ((xj - xi) or 1e-12) + yi
            if latitude < slope_lat:
                inside = not inside
        j = i
    return inside

def _records_by_field(resource: str, field: str, value: str, limit: int = 500):
    return [
        item for item in storage.list_records(resource, limit)
        if str((item.get("data") or {}).get(field, "")).strip().lower() == value.strip().lower()
    ]

def _active_record(rows: list[dict[str, Any]]):
    return next((row for row in rows if row.get("status") == "Active"), None) or (rows[0] if rows else None)

def _employee_work_location(employee_code: str):
    assignments = _records_by_field("employee_location_assignments", "employee_code", employee_code)
    assignment = _active_record(assignments)
    if assignment:
        location_id = assignment.get("data", {}).get("location_id", "")
        location = _active_record(_records_by_field("work_locations", "location_id", location_id))
        if location:
            return assignment, location
    locations = storage.list_records("work_locations", 100)
    location = _active_record(locations)
    return None, location

def _geofence_for_location(location_id: str):
    geofences = _records_by_field("geofences", "location_id", location_id)
    return _active_record(geofences)

def _geofence_validation(employee_code: str, payload: LocationValidationRequest):
    assignment, location = _employee_work_location(employee_code)
    location_data = location.get("data", {}) if location else {}
    location_id = location_data.get("location_id", "")
    geofence = _geofence_for_location(location_id) if location_id else None
    geofence_data = geofence.get("data", {}) if geofence else {}
    allowed_accuracy = _float_value(geofence_data, "allowed_accuracy_meters") or _float_value(location_data, "allowed_gps_accuracy_meters", 50)
    risk_flags = []

    if payload.accuracy > allowed_accuracy:
        risk_flags.append("poor_accuracy")
        geofence_status = "Accuracy Rejected"
        validation_reason = f"Device accuracy {payload.accuracy:.0f}m exceeds allowed {allowed_accuracy:.0f}m."
        inside = False
        distance = 0.0
        center_lat = _float_value(geofence_data, "center_latitude") or _float_value(location_data, "latitude")
        center_lon = _float_value(geofence_data, "center_longitude") or _float_value(location_data, "longitude")
    elif not location or not geofence:
        geofence_status = "Geofence Not Assigned"
        validation_reason = "No active work location/geofence assignment found for this employee."
        inside = False
        distance = 0.0
        center_lat = _float_value(location_data, "latitude")
        center_lon = _float_value(location_data, "longitude")
        risk_flags.append("missing_geofence_assignment")
    else:
        center_lat = _float_value(geofence_data, "center_latitude") or _float_value(location_data, "latitude")
        center_lon = _float_value(geofence_data, "center_longitude") or _float_value(location_data, "longitude")
        geofence_type = (geofence_data.get("geofence_type") or location_data.get("geofence_type") or "Circular").lower()
        radius = _float_value(geofence_data, "radius_meters") or _float_value(location_data, "geofence_radius_meters", 100)
        distance = _haversine_meters(payload.latitude, payload.longitude, center_lat, center_lon)
        if "polygon" in geofence_type:
            points = _json_points(geofence_data.get("polygon_coordinates"))
            inside = _point_in_polygon(payload.latitude, payload.longitude, points)
            validation_reason = "Point is inside polygon geofence." if inside else "Point is outside polygon geofence."
        else:
            inside = distance <= radius
            validation_reason = f"Distance {distance:.1f}m within radius {radius:.1f}m." if inside else f"Distance {distance:.1f}m exceeds radius {radius:.1f}m."
        geofence_status = "Inside Fence" if inside else "Outside Fence"
        if not inside:
            risk_flags.append("outside_fence")

    radius = _float_value(geofence_data, "radius_meters") or _float_value(location_data, "geofence_radius_meters", 0)
    result = {
        "employee_code": employee_code,
        "event_type": payload.event_type,
        "location_id": location_id,
        "location_name": location_data.get("location_name", ""),
        "geofence_id": geofence_data.get("geofence_id", ""),
        "geofence_version": geofence_data.get("boundary_version", "1"),
        "employee_latitude": f"{payload.latitude:.8f}",
        "employee_longitude": f"{payload.longitude:.8f}",
        "geofence_latitude": f"{center_lat:.8f}" if center_lat else "",
        "geofence_longitude": f"{center_lon:.8f}" if center_lon else "",
        "distance_meters": f"{distance:.2f}",
        "radius_meters": f"{radius:.2f}",
        "inside_fence": "Yes" if inside else "No",
        "accuracy_meters": f"{payload.accuracy:.2f}",
        "allowed_accuracy_meters": f"{allowed_accuracy:.2f}",
        "geofence_status": geofence_status,
        "validation_reason": validation_reason,
        "risk_flags": ",".join(risk_flags) if risk_flags else "none",
        "server_validated_at": _now_iso(),
        "can_continue": bool(inside and payload.accuracy <= allowed_accuracy),
    }
    return result

def _write_audit(actor: str, action: str, entity_type: str, entity_id: str, new_values: dict[str, Any], reason: str = ""):
    try:
        storage.create_record("audit_logs", {
            "audit_id": _new_ref("AUD"),
            "actor": actor,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "previous_values": "",
            "new_values": json.dumps(new_values, sort_keys=True),
            "reason": reason,
            "status": "Active",
        })
    except Exception:
        pass

def _items(resource: str, limit: int = 500):
    try:
        return storage.list_records(resource, limit)
    except Exception:
        return []

def _status_count(items: list[dict[str, Any]], *statuses: str) -> int:
    wanted = {status.lower() for status in statuses}
    return len([item for item in items if str(item.get("status", "")).lower() in wanted])

def _resource_summary(resource: str, label: str):
    items = _items(resource)
    return {
        "resource": resource,
        "label": label,
        "count": len(items),
        "active": _status_count(items, "Active", "Approved", "Present", "Passed"),
        "pending": _status_count(items, "Pending", "Pending Approval", "Open", "Draft"),
        "failed": _status_count(items, "Failed", "Rejected", "Out of Fence", "Critical"),
    }

def _hr_overview():
    employees = _items("employees")
    work_locations = _items("work_locations")
    geofences = _items("geofences")
    assignments = _items("employee_location_assignments")
    attendance = _items("attendance_records")
    validation_results = _items("attendance_validation_results")
    biometric_events = _items("attendance_biometric_events")
    leave_applications = _items("leave_applications")
    correction_requests = _items("attendance_correction_requests")
    payroll_adjustments = _items("payroll_adjustments")
    salary_slips = _items("salary_slips")
    out_of_fence = [
        item for item in validation_results
        if (item.get("data", {}).get("geofence_status") or item.get("status")) in {"Outside Fence", "Accuracy Rejected", "Geofence Not Assigned"}
    ]
    pending_approvals = [
        item for item in [*attendance, *leave_applications, *correction_requests, *payroll_adjustments]
        if item.get("status") in {"Open", "Pending", "Pending Approval", "Draft"}
    ]
    return {
        "stats": {
            "employees": len(employees),
            "active_employees": _status_count(employees, "Active", "Approved"),
            "work_locations": len(work_locations),
            "geofences": len(geofences),
            "location_assignments": len(assignments),
            "attendance_records": len(attendance),
            "out_of_fence_attempts": len(out_of_fence),
            "pending_approvals": len(pending_approvals),
            "biometric_events": len(biometric_events),
            "leave_applications": len(leave_applications),
            "salary_slips": len(salary_slips),
        },
        "sections": [
            _resource_summary("employees", "Employee Directory"),
            _resource_summary("work_locations", "Work Locations"),
            _resource_summary("geofences", "Geofence Management"),
            _resource_summary("employee_location_assignments", "Location Assignments"),
            _resource_summary("attendance_records", "Attendance Records"),
            _resource_summary("attendance_validation_results", "Validation Results"),
            _resource_summary("attendance_biometric_events", "Biometric Events"),
            _resource_summary("attendance_correction_requests", "Correction Requests"),
            _resource_summary("leave_applications", "Leave Applications"),
            _resource_summary("payroll_adjustments", "Payroll Adjustments"),
            _resource_summary("audit_logs", "Audit Logs"),
        ],
        "exceptions": [
            {
                "resource": item.get("resource"),
                "id": item.get("id"),
                "employee_code": item.get("data", {}).get("employee_code", ""),
                "status": item.get("data", {}).get("geofence_status") or item.get("status"),
                "reason": item.get("data", {}).get("validation_reason") or item.get("data", {}).get("reason") or "",
            }
            for item in [*out_of_fence, *pending_approvals][:12]
        ],
    }

def _clean_text(value: Any) -> str:
    return str(value or "").strip()

def _employee_bundle(employee_code: str):
    employee = _active_record(_records_for_employee("employees", employee_code, 100)) or _active_record(_records_by_field("employees", "email", employee_code, 100))
    private_details = _records_for_employee("employee_private_details", employee_code, 20)
    bank_details = _records_for_employee("employee_bank_details", employee_code, 20)
    documents = _records_for_employee("employee_documents", employee_code, 50)
    emergency_contacts = _records_for_employee("employee_emergency_contacts", employee_code, 20)
    lifecycle = _records_for_employee("employee_lifecycle_events", employee_code, 100)
    salary_assignments = _records_for_employee("employee_salary_assignments", employee_code, 50)
    salary_revisions = _records_for_employee("salary_revision_history", employee_code, 50)
    location_assignments = _records_for_employee("employee_location_assignments", employee_code, 50)
    shift_assignments = _records_for_employee("employee_shift_assignments", employee_code, 50)
    device_registrations = _records_for_employee("device_registrations", employee_code, 50)
    biometric_enrollments = _records_for_employee("employee_biometric_enrollments", employee_code, 50)
    salary_slips = _records_for_employee("salary_slips", employee_code, 50)
    attendance = _records_for_employee("attendance_records", employee_code, 100)
    missing = []
    if not private_details:
        missing.append("private_details")
    if not bank_details:
        missing.append("bank_details")
    if not documents:
        missing.append("documents")
    if not emergency_contacts:
        missing.append("emergency_contacts")
    if not salary_assignments:
        missing.append("salary_assignment")
    if not location_assignments:
        missing.append("work_location")
    if not biometric_enrollments:
        missing.append("biometric_enrollment")
    return {
        "employee_code": employee_code,
        "employee": employee.get("data", {}) if employee else None,
        "private_details": [item.get("data", {}) for item in private_details],
        "bank_details": [item.get("data", {}) for item in bank_details],
        "documents": [item.get("data", {}) for item in documents],
        "emergency_contacts": [item.get("data", {}) for item in emergency_contacts],
        "lifecycle": [item.get("data", {}) for item in lifecycle],
        "salary_assignments": [item.get("data", {}) for item in salary_assignments],
        "salary_revisions": [item.get("data", {}) for item in salary_revisions],
        "location_assignments": [item.get("data", {}) for item in location_assignments],
        "shift_assignments": [item.get("data", {}) for item in shift_assignments],
        "device_registrations": [item.get("data", {}) for item in device_registrations],
        "biometric_enrollments": [item.get("data", {}) for item in biometric_enrollments],
        "salary_slips": [item.get("data", {}) for item in salary_slips],
        "attendance_records": [item.get("data", {}) for item in attendance],
        "profile_completeness": max(0, round(((7 - len(missing)) / 7) * 100)),
        "missing_sections": missing,
    }

def _trusted_biometric_enrollment(employee_code: str, method: str, trusted_device_id: str):
    for item in _records_for_employee("employee_biometric_enrollments", employee_code, 100):
        data = item.get("data", {})
        if (
            data.get("trusted_device_id", "").strip().lower() == trusted_device_id.strip().lower()
            and data.get("verification_method", "").strip().lower() == method.strip().lower()
            and item.get("status") in {"Active", "Approved"}
        ):
            return item
    return None

def _create_lifecycle_event(payload: HrLifecycleEventRequest, actor: str):
    employee_code = payload.employee_code.strip()
    if not employee_code or not payload.event_type.strip() or not payload.effective_date.strip():
        raise HTTPException(status_code=422, detail="employee_code, event_type, and effective_date are required.")
    item = storage.create_record("employee_lifecycle_events", {
        "event_no": _new_ref("LIFE"),
        "employee_code": employee_code,
        "event_type": payload.event_type.strip(),
        "effective_date": payload.effective_date.strip(),
        "previous_value": _clean_text(payload.previous_value),
        "new_value": payload.new_value.strip(),
        "reason": payload.reason.strip(),
        "approved_by": _clean_text(payload.approved_by) or actor,
        "status": payload.status.strip() or "Approved",
    })
    _write_audit(actor, "create_lifecycle_event", "employee_lifecycle_events", item.get("id", ""), item.get("data", {}), payload.reason)
    return item

def _onboard_employee(payload: HrEmployeeOnboardingRequest, actor: str):
    employee_code = payload.employee_code.strip()
    email = payload.email.strip().lower()
    if not employee_code or not payload.full_name.strip() or not email:
        raise HTTPException(status_code=422, detail="employee_code, full_name, and email are required.")
    if _records_for_employee("employees", employee_code, 10):
        raise HTTPException(status_code=409, detail="Employee code already exists.")
    if _records_by_field("employees", "email", email, 10):
        raise HTTPException(status_code=409, detail="Employee email already exists.")

    created: dict[str, Any] = {}
    employee = storage.create_record("employees", {
        "employee_code": employee_code,
        "full_name": payload.full_name.strip(),
        "department": payload.department.strip(),
        "role": payload.role.strip(),
        "phone": _clean_text(payload.phone),
        "email": email,
        "shift": payload.shift.strip() or "General",
        "status": payload.status.strip() or "Active",
    })
    created["employee"] = employee

    if payload.date_of_birth:
        created["private_details"] = storage.create_record("employee_private_details", {
            "employee_code": employee_code,
            "date_of_birth": payload.date_of_birth.strip(),
            "gender": _clean_text(payload.gender),
            "nationality": _clean_text(payload.nationality),
            "tax_identifier_ref": _clean_text(payload.tax_identifier_ref),
            "status": "Active",
        })
    if payload.bank_name:
        created["bank_details"] = storage.create_record("employee_bank_details", {
            "employee_code": employee_code,
            "bank_name": payload.bank_name.strip(),
            "account_last4": _clean_text(payload.account_last4)[-4:],
            "ifsc_or_routing": _clean_text(payload.ifsc_or_routing),
            "verification_status": "Pending",
            "status": "Pending",
        })
    if payload.document_type:
        created["document"] = storage.create_record("employee_documents", {
            "employee_code": employee_code,
            "document_type": payload.document_type.strip(),
            "document_no_masked": _clean_text(payload.document_no_masked),
            "expiry_date": _clean_text(payload.document_expiry_date),
            "verification_status": "Pending",
            "status": "Pending",
        })
    if payload.emergency_contact_name:
        created["emergency_contact"] = storage.create_record("employee_emergency_contacts", {
            "employee_code": employee_code,
            "contact_name": payload.emergency_contact_name.strip(),
            "relationship": _clean_text(payload.emergency_relationship),
            "phone": _clean_text(payload.emergency_phone),
            "address": _clean_text(payload.emergency_address),
            "status": "Active",
        })
    if payload.location_id:
        created["location_assignment"] = storage.create_record("employee_location_assignments", {
            "assignment_id": _new_ref("LOC-ASG"),
            "employee_code": employee_code,
            "location_id": payload.location_id.strip(),
            "shift": payload.shift.strip() or "General",
            "effective_start_date": _clean_text(payload.effective_start_date) or _today(),
            "effective_end_date": _clean_text(payload.effective_end_date),
            "assignment_type": payload.location_assignment_type.strip() or "Primary",
            "approval_status": "Approved",
            "status": "Active",
        })
    if payload.shift:
        created["shift_assignment"] = storage.create_record("employee_shift_assignments", {
            "assignment_id": _new_ref("SHIFT-ASG"),
            "employee_code": employee_code,
            "shift": payload.shift.strip(),
            "effective_start_date": _clean_text(payload.effective_start_date) or _today(),
            "effective_end_date": _clean_text(payload.effective_end_date),
            "approval_status": "Approved",
            "status": "Active",
        })
    if payload.gross_salary or payload.ctc:
        created["salary_assignment"] = storage.create_record("employee_salary_assignments", {
            "assignment_id": _new_ref("SAL-ASG"),
            "employee_code": employee_code,
            "structure_id": _clean_text(payload.salary_structure_id) or "DEFAULT",
            "effective_date": _clean_text(payload.effective_start_date) or _today(),
            "gross_salary": _clean_text(payload.gross_salary),
            "ctc": _clean_text(payload.ctc) or _clean_text(payload.gross_salary),
            "approval_status": "Approved",
            "status": "Active",
        })
    if payload.trusted_device_id:
        device_id = payload.trusted_device_id.strip()
        created["device_registration"] = storage.create_record("device_registrations", {
            "device_id": device_id,
            "employee_code": employee_code,
            "platform": _clean_text(payload.device_platform) or "mobile",
            "device_name": _clean_text(payload.device_name),
            "app_version": _clean_text(payload.app_version),
            "restricted_device": "Yes",
            "registered_at": _now_iso(),
            "approval_status": "Approved",
            "status": "Active",
        })
        created["biometric_enrollment"] = storage.create_record("employee_biometric_enrollments", {
            "enrollment_id": _new_ref("BIO-ENR"),
            "employee_code": employee_code,
            "verification_method": "fingerprint",
            "trusted_device_id": device_id,
            "assertion_reference": _new_ref("ASSERT"),
            "enrolled_at": _now_iso(),
            "privacy_notice": "Raw fingerprints and biometric templates are never stored. Only OS biometric enrollment metadata and assertion references are retained.",
            "approval_status": "Approved",
            "status": "Active",
        })

    lifecycle = _create_lifecycle_event(HrLifecycleEventRequest(
        employee_code=employee_code,
        event_type="Employee Joined",
        effective_date=_clean_text(payload.effective_start_date) or _today(),
        previous_value="",
        new_value=payload.department.strip(),
        reason=payload.lifecycle_reason,
        approved_by=actor,
        status="Approved",
    ), actor)
    created["lifecycle_event"] = lifecycle
    _write_audit(actor, "onboard_employee", "employees", employee_code, {key: value.get("data", {}) for key, value in created.items() if isinstance(value, dict)}, payload.lifecycle_reason)
    return {"created": created, "profile": _employee_bundle(employee_code)}

def _parse_iso_date(value: str, field: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field} must be YYYY-MM-DD") from exc

def _date_between(value: str, start: date, end: date) -> bool:
    if not value:
        return False
    try:
        current = datetime.strptime(value[:10], "%Y-%m-%d").date()
    except ValueError:
        return False
    return start <= current <= end

def _money(value: Any, default: float = 0.0) -> float:
    try:
        if value in (None, ""):
            return default
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return default

def _period_dates(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)

def _approved_status(row: dict[str, Any]) -> bool:
    data = row.get("data", {})
    status = str(row.get("status") or data.get("status") or "").lower()
    approval = str(data.get("approval_status") or data.get("approved_status") or "").lower()
    return approval == "approved" or status in {"active", "approved", "completed"}

def _payroll_employee_codes(assignments: list[dict[str, Any]], employees: list[dict[str, Any]]):
    codes = []
    for row in assignments:
        code = row.get("data", {}).get("employee_code", "")
        if code and code not in codes:
            codes.append(code)
    for row in employees:
        data = row.get("data", {})
        code = data.get("employee_code") or data.get("email")
        if code and code not in codes:
            codes.append(code)
    return codes

def _salary_assignment_for(employee_code: str):
    assignments = _records_for_employee("employee_salary_assignments", employee_code, 100)
    return _active_record(assignments)

def _payroll_calculation(payload: PayrollGenerateRequest, actor: str):
    start = _parse_iso_date(payload.start_date, "start_date")
    end = _parse_iso_date(payload.end_date, "end_date")
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    total_days = max((end - start).days + 1, 1)
    period_id = payload.period_id or payload.period_name.replace(" ", "-").upper()
    run_no = _new_ref("PAY")
    employees = _items("employees")
    assignments = _items("employee_salary_assignments")
    attendance = _items("attendance_records", 1000)
    legacy_attendance = _items("attendance", 1000)
    leave_applications = _items("leave_applications", 1000)
    adjustments = _items("payroll_adjustments", 1000)
    employee_codes = _payroll_employee_codes(assignments, employees)
    validation_errors = []
    results = []
    totals = {"gross_pay": 0.0, "deductions": 0.0, "net_pay": 0.0, "employees": 0}

    if not employee_codes:
        validation_errors.append("No employees or salary assignments found for payroll generation.")

    period_item = None
    run_item = None
    if not payload.dry_run and employee_codes:
        period_item = storage.create_record("payroll_periods", {
            "period_id": period_id,
            "period_name": payload.period_name,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "company": payload.company or "",
            "branch": payload.branch or "",
            "attendance_close_status": "Draft",
            "payroll_status": "Draft",
            "status": "Draft",
        })

    for employee_code in employee_codes:
        salary_assignment = _salary_assignment_for(employee_code)
        if not salary_assignment:
            validation_errors.append(f"{employee_code}: no active salary assignment.")
            continue
        salary_data = salary_assignment.get("data", {})
        monthly_gross = _money(salary_data.get("gross_salary") or salary_data.get("ctc"))
        if monthly_gross <= 0:
            validation_errors.append(f"{employee_code}: salary assignment has no gross_salary/ctc.")
            continue
        present_dates = {
            row.get("data", {}).get("attendance_date")
            for row in attendance
            if row.get("data", {}).get("employee_code", "").lower() == employee_code.lower()
            and _date_between(row.get("data", {}).get("attendance_date", ""), start, end)
            and (row.get("data", {}).get("attendance_status") or row.get("status")) in {"Present", "Active", "Approved", "Completed"}
        }
        present_dates.update({
            row.get("data", {}).get("date")
            for row in legacy_attendance
            if row.get("data", {}).get("employee_code", "").lower() == employee_code.lower()
            and _date_between(row.get("data", {}).get("date", ""), start, end)
            and row.get("data", {}).get("check_in")
        })
        paid_leave_days = 0.0
        unpaid_leave_days = 0.0
        for row in leave_applications:
            data = row.get("data", {})
            if data.get("employee_code", "").lower() != employee_code.lower() or data.get("approval_status") != "Approved":
                continue
            if not (_date_between(data.get("start_date", ""), start, end) or _date_between(data.get("end_date", ""), start, end)):
                continue
            days = _money(data.get("total_leave_days"), 1.0)
            if str(data.get("payroll_impact", "")).lower() == "unpaid":
                unpaid_leave_days += days
            else:
                paid_leave_days += days
        additions = 0.0
        deductions = 0.0
        adjustment_lines = []
        for row in adjustments:
            data = row.get("data", {})
            if data.get("employee_code", "").lower() != employee_code.lower() or data.get("payroll_month") != payload.period_name:
                continue
            if not _approved_status(row):
                continue
            amount = _money(data.get("amount"))
            if str(data.get("addition_or_deduction", "")).lower() == "deduction":
                deductions += amount
            else:
                additions += amount
            adjustment_lines.append(data)
        present_days = len([day for day in present_dates if day])
        paid_days = min(total_days, present_days + paid_leave_days)
        prorated_gross = round(monthly_gross * (paid_days / total_days), 2)
        net_pay = round(prorated_gross + additions - deductions, 2)
        result_id = _new_ref("PER")
        result = {
            "result_id": result_id,
            "payroll_run": run_no,
            "employee_code": employee_code,
            "paid_days": f"{paid_days:.2f}",
            "present_days": str(present_days),
            "paid_leave_days": f"{paid_leave_days:.2f}",
            "unpaid_leave_days": f"{unpaid_leave_days:.2f}",
            "gross_pay": f"{prorated_gross:.2f}",
            "deductions": f"{deductions:.2f}",
            "net_pay": f"{net_pay:.2f}",
            "validation_status": "Valid",
            "status": "Draft",
            "lines": [
                {"component_name": "Prorated Gross", "component_type": "Earning", "quantity": f"{paid_days:.2f}", "rate": f"{monthly_gross / total_days:.2f}", "amount": f"{prorated_gross:.2f}", "formula": "monthly_gross * paid_days / period_days", "source": "salary_assignment"},
                *[
                    {"component_name": line.get("adjustment_type", "Adjustment"), "component_type": line.get("addition_or_deduction", "Addition"), "quantity": line.get("quantity", "1"), "rate": line.get("rate", line.get("amount", "0")), "amount": line.get("amount", "0"), "formula": line.get("calculation_method", "manual"), "source": "payroll_adjustments"}
                    for line in adjustment_lines
                ],
            ],
        }
        totals["gross_pay"] += prorated_gross
        totals["deductions"] += deductions
        totals["net_pay"] += net_pay
        totals["employees"] += 1
        results.append(result)
        if not payload.dry_run:
            storage.create_record("payroll_employee_results", {key: value for key, value in result.items() if key != "lines"})
            for line in result["lines"]:
                storage.create_record("payroll_calculation_lines", {
                    "line_id": _new_ref("LINE"),
                    "result_id": result_id,
                    "component_name": line["component_name"],
                    "component_type": line["component_type"],
                    "quantity": line["quantity"],
                    "rate": line["rate"],
                    "amount": line["amount"],
                    "formula": line["formula"],
                    "source": line["source"],
                    "status": "Draft",
                })
            storage.create_record("salary_slips", {
                "employee_code": employee_code,
                "period": payload.period_name,
                "gross_pay": f"{prorated_gross:.2f}",
                "deductions": f"{deductions:.2f}",
                "net_pay": f"{net_pay:.2f}",
                "payment_date": "",
                "status": "Draft",
            })
    totals = {key: (round(value, 2) if isinstance(value, float) else value) for key, value in totals.items()}
    if not payload.dry_run and totals["employees"] > 0:
        run_item = storage.create_record("payroll_runs", {
            "run_no": run_no,
            "period": payload.period_name,
            "department": payload.department or "All",
            "gross_pay": f"{totals['gross_pay']:.2f}",
            "deductions": f"{totals['deductions']:.2f}",
            "net_pay": f"{totals['net_pay']:.2f}",
            "approval_status": "Draft",
            "status": "Draft",
        })
    if not payload.dry_run and run_item:
        _write_audit(actor, "generate_payroll", "payroll_runs", run_no, {"period": payload.period_name, "period_id": period_item.get("id") if period_item else period_id, "totals": totals}, "Draft payroll generated from attendance, leave, salary assignments, and approved adjustments.")
    return {
        "run_no": run_no,
        "period": payload.period_name,
        "dry_run": payload.dry_run,
        "totals": totals,
        "results": results,
        "validation_errors": validation_errors,
    }

def _persist_location_validation(employee_code: str, payload: LocationValidationRequest, validation: dict[str, Any], attendance_record_id: str = "pending"):
    event_id = _new_ref("LOC")
    storage.create_record("attendance_location_events", {
        "event_id": event_id,
        "attendance_record_id": attendance_record_id,
        "employee_code": employee_code,
        "event_type": payload.event_type,
        "latitude": str(payload.latitude),
        "longitude": str(payload.longitude),
        "accuracy": str(payload.accuracy),
        "altitude": "" if payload.altitude is None else str(payload.altitude),
        "speed": "" if payload.speed is None else str(payload.speed),
        "provider": payload.provider,
        "captured_at": payload.captured_at or _now_iso(),
        "received_at": _now_iso(),
        "device_time": payload.device_time or "",
        "server_time": _now_iso(),
        "geofence_id": validation["geofence_id"],
        "geofence_version": validation["geofence_version"],
        "distance_meters": validation["distance_meters"],
        "inside_fence": validation["inside_fence"],
        "tolerance_applied": "No",
        "mock_location_indicator": payload.mock_location_indicator or "Unknown",
        "risk_score": "0" if validation["risk_flags"] == "none" else "70",
        "validation_result": validation["geofence_status"],
        "failure_reason": "" if validation["can_continue"] else validation["validation_reason"],
        "device_id": payload.device_id or "",
        "ip_address": "",
        "app_version": payload.app_version or "",
        "status": "Passed" if validation["can_continue"] else "Failed",
    })
    validation_id = _new_ref("VAL")
    storage.create_record("attendance_validation_results", {
        "validation_id": validation_id,
        "employee_code": employee_code,
        "event_type": payload.event_type,
        "location_id": validation["location_id"],
        "geofence_id": validation["geofence_id"],
        "employee_latitude": validation["employee_latitude"],
        "employee_longitude": validation["employee_longitude"],
        "geofence_latitude": validation["geofence_latitude"],
        "geofence_longitude": validation["geofence_longitude"],
        "distance_meters": validation["distance_meters"],
        "radius_meters": validation["radius_meters"],
        "inside_fence": validation["inside_fence"],
        "accuracy_meters": validation["accuracy_meters"],
        "allowed_accuracy_meters": validation["allowed_accuracy_meters"],
        "geofence_status": validation["geofence_status"],
        "validation_reason": validation["validation_reason"],
        "risk_flags": validation["risk_flags"],
        "server_validated_at": validation["server_validated_at"],
        "status": "Passed" if validation["can_continue"] else "Failed",
    })
    return {"event_id": event_id, "validation_id": validation_id}

def _location_payload_from_attendance(kind: str, payload: EmployeeAttendanceEvent) -> LocationValidationRequest:
    if payload.latitude is None or payload.longitude is None or payload.accuracy is None:
        raise HTTPException(status_code=422, detail="Current latitude, longitude, and GPS accuracy are required.")
    return LocationValidationRequest(
        event_type=kind.replace("-", "_"),
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        provider="device_gps",
    )

def _records_for_employee(resource: str, employee_code: str, limit: int = 500):
    return [
        item for item in storage.list_records(resource, limit)
        if (item.get("data") or {}).get("employee_code", "").strip().lower() == employee_code.lower()
    ]

def _attendance_policy():
    default = {
        "policy_name": "Default Attendance Policy",
        "late_after_time": "09:15",
        "grace_minutes": "0",
        "tracking_interval_minutes": "5",
        "background_location_required": "Yes",
        "status": "Active",
    }
    try:
        policies = storage.list_records("attendance_policies", 100)
    except Exception:
        return default
    active = next((row for row in policies if row.get("status") == "Active"), None) or (policies[0] if policies else None)
    if not active:
        return default
    data = active.get("data", {})
    return {**default, **{key: str(value) for key, value in data.items() if value not in (None, "")}}

def _late_after_time(policy: dict[str, str]) -> str:
    value = policy.get("late_after_time", "09:15").strip()
    try:
        datetime.strptime(value, "%H:%M")
        return value
    except ValueError:
        return "09:15"

def _attendance_snapshot(employee_code: str, policy: dict[str, str] | None = None):
    policy = policy or _attendance_policy()
    late_after = _late_after_time(policy)
    today = _today()
    rows = _records_for_employee("attendance", employee_code)
    today_rows = [row for row in rows if row.get("data", {}).get("date") == today]
    day_in = next((row for row in today_rows if row.get("data", {}).get("check_in")), None)
    day_out = next((row for row in today_rows if row.get("data", {}).get("check_out")), None)
    late = False
    if day_in:
        check_in = day_in.get("data", {}).get("check_in", "")
        late = bool(check_in and check_in > late_after)
    return {
        "employee_code": employee_code,
        "date": today,
        "checked_in": bool(day_in and not day_out),
        "day_in_time": day_in.get("data", {}).get("check_in") if day_in else "",
        "day_out_time": day_out.get("data", {}).get("check_out") if day_out else "",
        "late_mark": late,
        "late_after_time": late_after,
        "records_today": len(today_rows),
    }

def _attendance_calendar(employee_code: str):
    today = date.today()
    attendance = _records_for_employee("attendance", employee_code, 1000)
    leaves = _records_for_employee("leave_requests", employee_code, 1000)
    holidays = storage.list_records("holiday_calendar", 500)
    present_dates = {row.get("data", {}).get("date") for row in attendance if row.get("data", {}).get("check_in")}
    leave_dates = set()
    for row in leaves:
        data = row.get("data", {})
        if data.get("status") in {"Approved", "Pending", "Open"}:
            leave_dates.add(data.get("from_date"))
    holiday_dates = {row.get("data", {}).get("date") for row in holidays}
    days = []
    present = absent = leave = holiday = 0
    for day in range(1, today.day + 1):
        current = date(today.year, today.month, day)
        value = current.isoformat()
        if value in holiday_dates:
            status = "holiday"
            holiday += 1
        elif value in leave_dates:
            status = "leave"
            leave += 1
        elif value in present_dates:
            status = "present"
            present += 1
        elif current.weekday() == 6:
            status = "weekly_off"
            holiday += 1
        else:
            status = "absent"
            absent += 1
        days.append({"date": value, "day": day, "status": status})
    return {"month": today.strftime("%B %Y"), "present": present, "absent": absent, "leave": leave, "holiday": holiday, "days": days}

@app.get("/")
def root():
    return {"service": "FactoryPulse Global ERP API", "version": "0.5.0", "database": storage.mode, "auth_configured": AUTH_CONFIGURED}

@app.get("/api/health")
def health():
    return {"status": "healthy", "database": storage.mode, "auth_configured": AUTH_CONFIGURED, "departments": len(DEPARTMENTS), "modules": len(MODULE_FIELDS)}

@app.post("/api/auth/login")
def login(payload: LoginRequest):
    if not AUTH_CONFIGURED:
        raise HTTPException(status_code=503, detail="Authentication is not configured")
    user = _login_user(payload.email, payload.password)
    return {"token": _sign(user["email"]), "user": user}

@app.get("/api/catalog")
def catalog(_: str = Depends(_verify)):
    return {"departments": DEPARTMENTS, "descriptions": MODULE_DESCRIPTIONS, "modules": MODULE_FIELDS, "database": storage.mode}

@app.get("/api/dashboard")
def dashboard(_: str = Depends(_verify)):
    return storage.dashboard()

@app.get("/api/mobile/summary")
def mobile_summary(_: str = Depends(_verify)):
    summary = storage.dashboard()
    return {
        "database": summary["database"],
        "stats": {
            "departments": summary["department_count"],
            "modules": summary["module_count"],
            "records": summary["record_count"],
        },
        "priority_work": summary["priority_work"][:8],
        "departments": [
            {
                "id": item["id"],
                "name": item["name"],
                "record_count": item["record_count"],
                "module_count": item["module_count"],
            }
            for item in summary["departments"]
        ],
    }

@app.get("/api/mobile/employee/summary")
def employee_summary(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    policy = _attendance_policy()
    attendance = _attendance_snapshot(employee_code, policy)
    calendar = _attendance_calendar(employee_code)
    salary = _records_for_employee("salary_slips", employee_code, 12)
    leaves = _records_for_employee("leave_requests", employee_code, 100)
    balances = _records_for_employee("leave_balances", employee_code, 20)
    locations = _records_for_employee("employee_locations", employee_code, 20)
    assignment, work_location = _employee_work_location(employee_code)
    return {
        "employee_code": employee_code,
        "attendance": attendance,
        "attendance_policy": policy,
        "assignment": assignment.get("data", {}) if assignment else None,
        "work_location": work_location.get("data", {}) if work_location else None,
        "calendar": calendar,
        "leave": {
            "pending": len([row for row in leaves if row.get("status") in {"Open", "Pending"}]),
            "approved": len([row for row in leaves if row.get("status") == "Approved"]),
            "balances": [row.get("data", {}) for row in balances],
        },
        "salary": {
            "latest": salary[0].get("data", {}) if salary else None,
            "count": len(salary),
        },
        "tracking": {
            "last_location": locations[0].get("data", {}) if locations else None,
            "ping_count": len(locations),
        },
    }

@app.get("/api/v1/employee/attendance/status")
def v1_employee_attendance_status(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    assignment, location = _employee_work_location(employee_code)
    return {
        "employee_code": employee_code,
        "attendance": _attendance_snapshot(employee_code),
        "attendance_policy": _attendance_policy(),
        "assignment": assignment.get("data", {}) if assignment else None,
        "work_location": location.get("data", {}) if location else None,
    }

@app.get("/api/v1/employee/work-location")
def v1_employee_work_location(email: str = Depends(_verify)):
    assignment, location = _employee_work_location(_employee_code(email))
    return {
        "assignment": assignment.get("data", {}) if assignment else None,
        "work_location": location.get("data", {}) if location else None,
    }

@app.get("/api/v1/employee/profile")
def v1_employee_profile(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    employee = _active_record(_records_for_employee("employees", employee_code, 20)) or _active_record(_records_by_field("employees", "email", email, 20))
    return {
        "employee_code": employee_code,
        "employee": employee.get("data", {}) if employee else {"employee_code": employee_code, "email": email, "status": "Active"},
        "private_details": [item.get("data", {}) for item in _records_for_employee("employee_private_details", employee_code, 20)],
        "documents": [item.get("data", {}) for item in _records_for_employee("employee_documents", employee_code, 20)],
        "emergency_contacts": [item.get("data", {}) for item in _records_for_employee("employee_emergency_contacts", employee_code, 20)],
        "lifecycle": [item.get("data", {}) for item in _records_for_employee("employee_lifecycle_events", employee_code, 100)],
    }

@app.get("/api/v1/employee/attendance/history")
def v1_employee_attendance_history(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    return {
        "items": _records_for_employee("attendance_records", employee_code, 100),
        "legacy_items": _records_for_employee("attendance", employee_code, 100),
        "location_events": _records_for_employee("attendance_location_events", employee_code, 100),
        "biometric_events": _records_for_employee("attendance_biometric_events", employee_code, 100),
        "correction_requests": _records_for_employee("attendance_correction_requests", employee_code, 100),
    }

@app.post("/api/v1/employee/attendance/correction")
def v1_employee_attendance_correction(payload: AttendanceCorrectionRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    if not payload.attendance_date.strip() or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="Attendance date and reason are required.")
    item = storage.create_record("attendance_correction_requests", {
        "request_id": _new_ref("COR"),
        "employee_code": employee_code,
        "attendance_date": payload.attendance_date.strip(),
        "requested_day_in_time": (payload.requested_day_in_time or "").strip(),
        "requested_day_out_time": (payload.requested_day_out_time or "").strip(),
        "reason": payload.reason.strip(),
        "current_record": "",
        "requested_changes": (payload.requested_changes or "").strip(),
        "manager_approval": "Pending",
        "hr_approval": "Pending",
        "final_status": "Pending Approval",
        "status": "Pending Approval",
    })
    _write_audit(email, "submit_attendance_correction", "attendance_correction_requests", item.get("id", ""), item.get("data", {}), payload.reason)
    return {"item": item}

@app.get("/api/v1/employee/leave/balance")
def v1_employee_leave_balance(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    return {
        "balances": _records_for_employee("leave_balances", employee_code, 100),
        "allocations": _records_for_employee("leave_allocations", employee_code, 100),
        "applications": _records_for_employee("leave_applications", employee_code, 100),
        "legacy_requests": _records_for_employee("leave_requests", employee_code, 100),
    }

@app.post("/api/v1/employee/attendance/validate-location")
def v1_validate_employee_location(payload: LocationValidationRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    validation = _geofence_validation(employee_code, payload)
    refs = _persist_location_validation(employee_code, payload, validation)
    _write_audit(email, "validate_location", "attendance_validation_results", refs["validation_id"], validation, validation["validation_reason"])
    return {"validation": validation, "refs": refs}

@app.post("/api/v1/employee/attendance/biometric")
def v1_employee_biometric(payload: BiometricVerificationRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    method = payload.verification_method.strip().lower()
    if method not in {"fingerprint", "device_credential"}:
        raise HTTPException(status_code=422, detail="Only fingerprint or device credential verification is allowed for this app. Raw biometric data is never stored.")
    result = payload.verification_result.strip().lower()
    if result not in {"success", "failed", "cancelled", "locked", "unavailable"}:
        raise HTTPException(status_code=422, detail="Invalid biometric verification result.")
    if result == "success":
        trusted_device_id = payload.trusted_device_id.strip() if payload.trusted_device_id else ""
        if not trusted_device_id:
            raise HTTPException(status_code=422, detail="trusted_device_id is required for successful biometric verification.")
        if not _trusted_biometric_enrollment(employee_code, method, trusted_device_id):
            raise HTTPException(status_code=403, detail="This employee/device biometric enrollment is not approved. HR must enroll the trusted device first.")
    event_id = _new_ref("BIO")
    item = storage.create_record("attendance_biometric_events", {
        "event_id": event_id,
        "attendance_record_id": payload.attendance_record_id or "pending",
        "employee_code": employee_code,
        "event_type": payload.event_type,
        "verification_method": method,
        "verification_result": result,
        "assertion_reference": payload.assertion_reference or _new_ref("ASSERT"),
        "trusted_device_id": payload.trusted_device_id or "",
        "failure_reason": payload.failure_reason or "",
        "risk_flags": payload.risk_flags or "none",
        "verified_at": _now_iso(),
        "status": "Passed" if result == "success" else "Failed",
    })
    _write_audit(email, "biometric_verification", "attendance_biometric_events", event_id, item.get("data", {}), "OS biometric result metadata only.")
    return {"item": item, "biometric_privacy": "Raw fingerprints and biometric templates are not captured, transmitted, or stored."}

@app.get("/api/v1/hr/overview")
def v1_hr_overview(_: str = Depends(_verify)):
    return _hr_overview()

@app.get("/api/v1/hr/employees-dashboard")
def v1_hr_employees_dashboard(_: str = Depends(_verify)):
    employees = _items("employees", 500)
    bundles = [_employee_bundle(row.get("data", {}).get("employee_code") or row.get("data", {}).get("email", "")) for row in employees]
    complete = [item for item in bundles if item["profile_completeness"] == 100]
    incomplete = [item for item in bundles if item["profile_completeness"] < 100]
    biometric_ready = [item for item in bundles if item["biometric_enrollments"]]
    return {
        "stats": {
            "employees": len(employees),
            "active": len([row for row in employees if row.get("status") == "Active"]),
            "complete_profiles": len(complete),
            "incomplete_profiles": len(incomplete),
            "biometric_ready": len(biometric_ready),
            "salary_assigned": len([item for item in bundles if item["salary_assignments"]]),
            "location_assigned": len([item for item in bundles if item["location_assignments"]]),
        },
        "employees": bundles,
        "missing_private_or_sensitive_notice": "Sensitive HR details are returned only to authenticated HR/admin users and biometric records never contain raw fingerprints or templates.",
    }

@app.get("/api/v1/hr/employees/{employee_code}")
def v1_hr_employee_detail(employee_code: str, _: str = Depends(_verify)):
    bundle = _employee_bundle(employee_code)
    if not bundle["employee"]:
        raise HTTPException(status_code=404, detail="Employee not found")
    return bundle

@app.post("/api/v1/hr/employees/onboard")
def v1_hr_employee_onboard(payload: HrEmployeeOnboardingRequest, email: str = Depends(_verify)):
    return _onboard_employee(payload, email)

@app.post("/api/v1/hr/employees/lifecycle")
def v1_hr_employee_lifecycle(payload: HrLifecycleEventRequest, email: str = Depends(_verify)):
    item = _create_lifecycle_event(payload, email)
    return {"item": item, "profile": _employee_bundle(payload.employee_code)}

@app.get("/api/v1/hr/geofence-dashboard")
def v1_hr_geofence_dashboard(_: str = Depends(_verify)):
    overview = _hr_overview()
    return {
        "stats": {
            "work_locations": overview["stats"]["work_locations"],
            "geofences": overview["stats"]["geofences"],
            "assignments": overview["stats"]["location_assignments"],
            "out_of_fence_attempts": overview["stats"]["out_of_fence_attempts"],
        },
        "validation_results": _items("attendance_validation_results", 100),
        "work_locations": _items("work_locations", 100),
        "geofences": _items("geofences", 100),
    }

@app.get("/api/v1/finance/payroll-dashboard")
def v1_finance_payroll_dashboard(_: str = Depends(_verify)):
    adjustments = _items("payroll_adjustments")
    runs = _items("payroll_runs")
    results = _items("payroll_employee_results")
    slips = _items("salary_slips")
    total_net = sum(_money(row.get("data", {}).get("net_pay")) for row in results)
    total_gross = sum(_money(row.get("data", {}).get("gross_pay")) for row in results)
    total_deductions = sum(_money(row.get("data", {}).get("deductions")) for row in results)
    return {
        "stats": {
            "payroll_runs": len(runs),
            "employee_results": len(results),
            "adjustments": len(adjustments),
            "pending_adjustments": _status_count(adjustments, "Open", "Pending", "Pending Approval", "Draft"),
            "salary_slips": len(slips),
            "total_gross": round(total_gross, 2),
            "total_deductions": round(total_deductions, 2),
            "total_net": round(total_net, 2),
        },
        "payroll_runs": runs[:20],
        "employee_results": results[:20],
        "adjustments": adjustments[:20],
    }

@app.post("/api/v1/payroll/generate")
def v1_generate_payroll(payload: PayrollGenerateRequest, email: str = Depends(_verify)):
    return _payroll_calculation(payload, email)

@app.post("/api/v1/payroll/validate")
def v1_validate_payroll(payload: PayrollGenerateRequest, email: str = Depends(_verify)):
    data = payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()
    data["dry_run"] = True
    return _payroll_calculation(PayrollGenerateRequest(**data), email)

@app.post("/api/mobile/employee/day-in")
def employee_day_in(payload: EmployeeAttendanceEvent, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    policy = _attendance_policy()
    snapshot = _attendance_snapshot(employee_code, policy)
    if snapshot["checked_in"]:
        raise HTTPException(status_code=409, detail="Day-in already active. Complete day-out first.")
    location_payload = _location_payload_from_attendance("day-in", payload)
    validation = _geofence_validation(employee_code, location_payload)
    refs = _persist_location_validation(employee_code, location_payload, validation)
    if not validation["can_continue"]:
        raise HTTPException(status_code=422, detail=validation["validation_reason"])
    data = {
        "employee_code": employee_code,
        "date": _today(),
        "shift": payload.shift or "General",
        "check_in": _hhmm(),
        "gps_area": _gps(payload),
        "status": "Active",
    }
    item = storage.create_record("attendance", data)
    storage.create_record("attendance_records", {
        "attendance_record_id": _new_ref("ATT"),
        "employee_code": employee_code,
        "employee_name": employee_code,
        "department": "",
        "designation": "",
        "company": "",
        "branch": "",
        "work_location": validation["location_name"],
        "shift": payload.shift or "General",
        "attendance_date": _today(),
        "day_in_time": _hhmm(),
        "day_in_latitude": validation["employee_latitude"],
        "day_in_longitude": validation["employee_longitude"],
        "day_in_accuracy": validation["accuracy_meters"],
        "day_in_distance": validation["distance_meters"],
        "day_in_geofence_status": validation["geofence_status"],
        "day_in_biometric_result": "Pending",
        "attendance_status": "Present",
        "payroll_status": "Pending",
        "approval_status": "Approved" if validation["inside_fence"] == "Yes" else "Pending",
        "source": "employee_mobile",
        "status": "Active",
    })
    if payload.latitude is not None and payload.longitude is not None:
        storage.create_record("employee_locations", {
            "employee_code": employee_code,
            "timestamp": _now_iso(),
            "latitude": str(payload.latitude),
            "longitude": str(payload.longitude),
            "accuracy": str(payload.accuracy or ""),
            "event": "day_in",
            "status": "Active",
        })
    _write_audit(email, "day_in", "attendance", item.get("id", ""), {"attendance": item, "validation": validation}, "Employee mobile day-in.")
    return {"item": item, "attendance": _attendance_snapshot(employee_code, policy), "attendance_policy": policy, "validation": validation, "refs": refs}

@app.post("/api/mobile/employee/day-out")
def employee_day_out(payload: EmployeeAttendanceEvent, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    policy = _attendance_policy()
    snapshot = _attendance_snapshot(employee_code, policy)
    if not snapshot["day_in_time"]:
        raise HTTPException(status_code=409, detail="Day-in is required before day-out.")
    if snapshot["day_out_time"]:
        raise HTTPException(status_code=409, detail="Day-out already recorded for today.")
    location_payload = _location_payload_from_attendance("day-out", payload)
    validation = _geofence_validation(employee_code, location_payload)
    refs = _persist_location_validation(employee_code, location_payload, validation)
    if not validation["can_continue"]:
        raise HTTPException(status_code=422, detail=validation["validation_reason"])
    data = {
        "employee_code": employee_code,
        "date": _today(),
        "shift": payload.shift or "General",
        "check_out": _hhmm(),
        "gps_area": _gps(payload),
        "status": "Completed",
    }
    item = storage.create_record("attendance", data)
    if payload.latitude is not None and payload.longitude is not None:
        storage.create_record("employee_locations", {
            "employee_code": employee_code,
            "timestamp": _now_iso(),
            "latitude": str(payload.latitude),
            "longitude": str(payload.longitude),
            "accuracy": str(payload.accuracy or ""),
            "event": "day_out",
            "status": "Completed",
        })
    _write_audit(email, "day_out", "attendance", item.get("id", ""), {"attendance": item, "validation": validation}, "Employee mobile day-out.")
    return {"item": item, "attendance": _attendance_snapshot(employee_code, policy), "attendance_policy": policy, "validation": validation, "refs": refs}

@app.post("/api/mobile/employee/location")
def employee_location(payload: EmployeeLocationPing, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    snapshot = _attendance_snapshot(employee_code)
    if not snapshot["checked_in"]:
        raise HTTPException(status_code=409, detail="Location tracking is allowed only during active working hours after day-in.")
    location_payload = LocationValidationRequest(
        event_type=payload.event or "tracking",
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy or 9999,
        provider="device_gps",
    )
    validation = _geofence_validation(employee_code, location_payload)
    refs = _persist_location_validation(employee_code, location_payload, validation)
    item = storage.create_record("employee_locations", {
        "employee_code": employee_code,
        "timestamp": _now_iso(),
        "latitude": str(payload.latitude),
        "longitude": str(payload.longitude),
        "accuracy": str(payload.accuracy or ""),
        "event": payload.event or "tracking",
        "status": "Active",
    })
    return {"item": item, "tracking": {"active": True}, "validation": validation, "refs": refs}

@app.get("/api/mobile/employee/calendar")
def employee_calendar(email: str = Depends(_verify)):
    return _attendance_calendar(_employee_code(email))

@app.get("/api/mobile/employee/attendance-policy")
def employee_attendance_policy(_: str = Depends(_verify)):
    return _attendance_policy()

@app.get("/api/mobile/employee/salary")
def employee_salary(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    return {"items": _records_for_employee("salary_slips", employee_code, 24)}

@app.post("/api/mobile/employee/leave")
def employee_leave(payload: LeaveApplyRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    if not payload.leave_type.strip() or not payload.from_date.strip() or not payload.to_date.strip():
        raise HTTPException(status_code=422, detail="Leave type, from date, and to date are required.")
    item = storage.create_record("leave_requests", {
        "employee_code": employee_code,
        "leave_type": payload.leave_type.strip(),
        "from_date": payload.from_date.strip(),
        "to_date": payload.to_date.strip(),
        "reason": payload.reason.strip(),
        "status": "Pending",
    })
    return {"item": item}

@app.get("/api/departments")
def departments(_: str = Depends(_verify)):
    dashboard_data = storage.dashboard()
    counts = {item["id"]: item for item in dashboard_data["departments"]}
    return {"items": [{"id": key, "name": value["name"], "modules": value["modules"], "description": MODULE_DESCRIPTIONS.get(key, ""), "record_count": counts.get(key, {}).get("record_count", 0)} for key, value in DEPARTMENTS.items()]}

@app.get("/api/departments/{department_id}")
def department(department_id: str, _: str = Depends(_verify)):
    try:
        return storage.department(department_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Department not found")

@app.get("/api/modules/{resource}")
def list_module(resource: str, _: str = Depends(_verify)):
    try:
        return {"resource": resource, "fields": MODULE_FIELDS[resource], "items": storage.list_records(resource)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Module not found")

@app.post("/api/modules/{resource}")
def create_module_record(resource: str, payload: RecordCreate, _: str = Depends(_verify)):
    try:
        return {"item": storage.create_record(resource, payload.data)}
    except KeyError:
        raise HTTPException(status_code=404, detail="Module not found")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

@app.get("/api/hr/employees")
def hr_employees(_: str = Depends(_verify)):
    return storage.list_records("employees")

@app.get("/api/finance/invoices")
def finance_invoices(_: str = Depends(_verify)):
    return storage.list_records("invoices")

@app.get("/api/operations/incidents")
def operations_incidents(_: str = Depends(_verify)):
    return storage.list_records("incidents")
