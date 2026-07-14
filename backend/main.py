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
from fastapi import Depends, FastAPI, Header, HTTPException, Response
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

ROLE_PERMISSIONS = {
    "FACTORY_ADMIN": {"admin:*", "hr:*", "finance:*", "reports:*", "records:*", "employee:*"},
    "SUPER_ADMIN": {"admin:*", "hr:*", "finance:*", "reports:*", "records:*", "employee:*"},
    "HR_ADMIN": {"hr:*", "reports:read", "records:hr", "employee:read"},
    "HR_MANAGER": {"hr:read", "hr:attendance", "hr:leave", "reports:read", "records:hr"},
    "FINANCE_ADMIN": {"finance:*", "reports:read", "records:finance"},
    "REPORTING_MANAGER": {"reports:read"},
    "AUDITOR": {"reports:read", "admin:audit", "hr:read", "finance:read"},
    "EMPLOYEE": {"employee:*"},
    "FACTORY_USER": {"reports:read"},
}

RESOURCE_PERMISSIONS = {
    "finance": "finance:write",
    "hr": "hr:write",
    "admin": "admin:write",
}

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

class LeaveApplicationRequest(BaseModel):
    employee_code: str | None = None
    leave_type: str
    start_date: str
    end_date: str
    half_day: bool = False
    reason: str
    approver: str | None = None
    payroll_impact: str = "Paid"

class LeaveDecisionRequest(BaseModel):
    application_id: str
    decision: str
    remarks: str | None = None
    approver: str | None = None
    payroll_impact: str | None = None

class LeaveAllocationRequest(BaseModel):
    employee_code: str
    leave_type: str
    period: str
    allocated_days: float
    expiry_date: str | None = None
    status: str = "Active"

class HolidayRequest(BaseModel):
    calendar_id: str
    holiday_name: str
    holiday_date: str
    holiday_type: str = "Company Holiday"
    paid_status: str = "Paid"
    optional_or_mandatory: str = "Mandatory"
    payroll_impact: str = "Paid"
    notes: str | None = None
    status: str = "Active"

class AttendanceCorrectionRequest(BaseModel):
    attendance_date: str
    requested_day_in_time: str | None = None
    requested_day_out_time: str | None = None
    reason: str
    requested_changes: str | None = None

class AttendanceDecisionRequest(BaseModel):
    attendance_record_id: str
    decision: str
    comments: str | None = None
    approval_type: str = "HR Review"

class AttendanceCorrectionDecisionRequest(BaseModel):
    request_id: str
    decision: str
    comments: str | None = None
    apply_to_attendance: bool = True

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

class HrWorkLocationRequest(BaseModel):
    location_id: str | None = None
    company: str = "FactoryPulse"
    branch: str = "Main"
    location_name: str
    location_type: str = "Factory"
    full_address: str
    city: str
    state: str
    country: str = "India"
    latitude: float
    longitude: float
    geofence_type: str = "Circular"
    geofence_radius_meters: float = 100
    allowed_gps_accuracy_meters: float = 50
    time_zone: str = "Asia/Kolkata"
    approval_status: str = "Approved"
    status: str = "Active"

class HrGeofenceRequest(BaseModel):
    geofence_id: str | None = None
    location_id: str
    geofence_type: str = "Circular"
    center_latitude: float
    center_longitude: float
    radius_meters: float = 100
    polygon_coordinates: str | None = None
    allowed_accuracy_meters: float = 50
    boundary_version: str = "1"
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    approval_status: str = "Approved"
    status: str = "Active"

class HrGeofenceTestRequest(BaseModel):
    location_id: str
    latitude: float
    longitude: float
    accuracy: float = 10

class HrLocationAssignmentRequest(BaseModel):
    employee_code: str
    location_id: str
    shift: str = "General"
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    assignment_type: str = "Primary"
    approval_status: str = "Approved"
    status: str = "Active"

class HrAttendancePolicyRequest(BaseModel):
    policy_name: str = "Default Attendance Policy"
    late_after_time: str = "09:15"
    grace_minutes: int = 0
    tracking_interval_minutes: int = 5
    background_location_required: bool = True
    status: str = "Active"

class HrShiftRequest(BaseModel):
    name: str
    shift_type: str = "Fixed"
    start_time: str
    end_time: str
    cross_midnight: bool = False
    day_in_open_time: str | None = None
    day_in_close_time: str | None = None
    day_out_open_time: str | None = None
    day_out_close_time: str | None = None
    grace_minutes: int = 0
    minimum_full_day_minutes: int = 480
    minimum_half_day_minutes: int = 240
    break_minutes: int = 0
    auto_break_deduction: bool = False
    overtime_eligible: bool = False
    overtime_approval_required: bool = True
    early_exit_grace_minutes: int = 0
    late_mark_after_minutes: int = 0
    maximum_late_marks: int = 3
    weekly_working_days: str = "Mon,Tue,Wed,Thu,Fri,Sat"
    weekly_offs: str = "Sun"
    applicable_locations: str | None = None
    applicable_departments: str | None = None
    applicable_employees: str | None = None
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    department: str = "All"
    supervisor: str | None = None
    status: str = "Active"

class HrShiftAssignmentRequest(BaseModel):
    employee_code: str
    shift: str
    shift_type: str = "Fixed"
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    assignment_reason: str | None = None
    approval_status: str = "Approved"
    status: str = "Active"

class HrShiftRosterRequest(BaseModel):
    employee_code: str
    shift: str
    roster_date: str
    location_id: str | None = None
    planned_start_time: str | None = None
    planned_end_time: str | None = None
    roster_type: str = "Regular"
    published_status: str = "Published"
    approval_status: str = "Approved"
    status: str = "Active"

class NotificationReadRequest(BaseModel):
    notification_id: str

class AdminJobRunRequest(BaseModel):
    job_type: str
    dry_run: bool = False

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

class PayrollAdjustmentRequest(BaseModel):
    employee_code: str
    payroll_month: str
    adjustment_type: str
    addition_or_deduction: str
    amount: float
    calculation_method: str = "Manual"
    quantity: float | None = None
    rate: float | None = None
    reason: str
    policy_reference: str
    supporting_attachment: str | None = None

class PayrollAdjustmentDecisionRequest(BaseModel):
    adjustment_id: str
    decision: str
    remarks: str | None = None

class PayrollRunDecisionRequest(BaseModel):
    run_no: str
    decision: str
    remarks: str | None = None

class PaymentBatchRequest(BaseModel):
    payroll_run: str
    payment_date: str
    payment_method: str = "Bank Transfer"
    bank_file_reference: str | None = None
    mark_salary_slips: bool = True

class PaymentBatchDecisionRequest(BaseModel):
    batch_id: str
    decision: str
    remarks: str | None = None

class PayrollPolicyRequest(BaseModel):
    policy_name: str = "Default Payroll Policy"
    proration_method: str = "Calendar Day"
    fixed_divisor: float | None = None
    rounding_rule: str = "Round 2 Decimals"
    max_adjustment_amount: float = 50000
    role_adjustment_limits: str | None = None
    retroactive_months_allowed: int = 2
    approval_required: bool = True
    lock_after_approval: bool = True
    allow_reversal_after_lock: bool = True
    adjustment_categories: str | None = None
    statutory_notes: str | None = None
    effective_start_date: str | None = None
    effective_end_date: str | None = None
    approval_status: str = "Approved"
    status: str = "Active"

class SalaryStructureRequest(BaseModel):
    structure_id: str | None = None
    structure_name: str
    currency: str = "INR"
    payment_frequency: str = "Monthly"
    proration_method: str = "Payroll Policy"
    basic_salary: float = 0
    allowances: float = 0
    deductions: float = 0
    employer_contributions: float = 0
    employee_contributions: float = 0
    approval_status: str = "Approved"
    status: str = "Active"

class SalaryComponentRequest(BaseModel):
    structure_id: str
    component_name: str
    component_type: str = "Earning"
    calculation_method: str = "Fixed"
    amount: float = 0
    percentage_of: str | None = None
    taxable: bool = True
    payroll_impact: str = "Gross"
    status: str = "Active"

class SalaryAssignmentRequest(BaseModel):
    employee_code: str
    structure_id: str
    effective_date: str
    basic_salary: float = 0
    allowances: float = 0
    deductions: float = 0
    employer_contributions: float = 0
    employee_contributions: float = 0
    currency: str = "INR"
    payment_frequency: str = "Monthly"
    approval_status: str = "Approved"
    status: str = "Active"

class SalaryRevisionRequest(BaseModel):
    employee_code: str
    structure_id: str
    effective_date: str
    basic_salary: float = 0
    allowances: float = 0
    deductions: float = 0
    revision_type: str = "Salary Revision"
    reason: str
    supporting_document: str | None = None

class SalaryRevisionDecisionRequest(BaseModel):
    revision_id: str
    decision: str
    remarks: str | None = None

class AdminUserCreateRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str
    department_id: str | None = None
    status: str = "Active"

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

def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    iterations = 260000
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return "pbkdf2_sha256$%s$%s$%s" % (
        iterations,
        base64.b64encode(salt).decode(),
        base64.b64encode(digest).decode(),
    )

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

def _user_context(email: str):
    normalized = email.strip().lower()
    if normalized == ADMIN_EMAIL.strip().lower():
        return {"email": normalized, "name": "FactoryPulse Admin", "role": "FACTORY_ADMIN", "status": "Active"}
    user = storage.get_user_by_email(normalized)
    if user:
        return {
            "email": normalized,
            "name": user.get("full_name") or normalized,
            "role": user.get("role") or "FACTORY_USER",
            "department_id": user.get("department_id"),
            "status": user.get("status", "Active"),
        }
    employee = _active_record(_records_by_field("employees", "email", normalized, 20))
    if employee:
        data = employee.get("data", {})
        return {"email": normalized, "name": data.get("full_name") or normalized, "role": "EMPLOYEE", "employee_code": data.get("employee_code") or normalized, "status": data.get("status", "Active")}
    return {"email": normalized, "name": normalized, "role": "FACTORY_USER", "status": "Active"}

def _permission_allowed(role: str, permission: str):
    permissions = ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS["FACTORY_USER"])
    namespace = permission.split(":", 1)[0]
    return permission in permissions or f"{namespace}:*" in permissions or "admin:*" in permissions

def _require_permission(email: str, permission: str):
    user = _user_context(email)
    if user.get("status") != "Active":
        raise HTTPException(status_code=403, detail="User is not active.")
    if not _permission_allowed(user["role"], permission):
        _write_audit(email, "permission_denied", "rbac", permission, {"role": user["role"], "permission": permission}, "RBAC permission denied.")
        raise HTTPException(status_code=403, detail=f"Permission denied: {permission}")
    return user

def _resource_department(resource: str):
    for department_id, department in DEPARTMENTS.items():
        if resource in department.get("modules", []):
            return department_id
    return ""

def _require_resource_write(email: str, resource: str):
    department = _resource_department(resource)
    permission = RESOURCE_PERMISSIONS.get(department, "records:write")
    if department and _permission_allowed(_user_context(email)["role"], f"records:{department}"):
        return _user_context(email)
    return _require_permission(email, permission)

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

def _validate_lat_lon(latitude: float, longitude: float):
    if latitude < -90 or latitude > 90:
        raise HTTPException(status_code=422, detail="latitude must be between -90 and 90.")
    if longitude < -180 or longitude > 180:
        raise HTTPException(status_code=422, detail="longitude must be between -180 and 180.")

def _validate_geofence_numbers(radius: float, accuracy: float):
    if radius < 10 or radius > 5000:
        raise HTTPException(status_code=422, detail="geofence radius must be between 10 and 5000 meters.")
    if accuracy < 1 or accuracy > 500:
        raise HTTPException(status_code=422, detail="allowed GPS accuracy must be between 1 and 500 meters.")

def _validate_polygon_payload(geofence_type: str, polygon_coordinates: str | None):
    if "polygon" not in geofence_type.lower():
        return
    points = _json_points(polygon_coordinates)
    if len(points) < 3:
        raise HTTPException(status_code=422, detail="polygon geofence requires at least three valid coordinate points.")

def _test_geofence(location_id: str, latitude: float, longitude: float, accuracy: float):
    _validate_lat_lon(latitude, longitude)
    location = _active_record(_records_by_field("work_locations", "location_id", location_id))
    if not location:
        raise HTTPException(status_code=404, detail="Work location not found.")
    geofence = _geofence_for_location(location_id)
    if not geofence:
        raise HTTPException(status_code=404, detail="Active geofence not found for this location.")
    location_data = location.get("data", {})
    geofence_data = geofence.get("data", {})
    center_lat = _float_value(geofence_data, "center_latitude") or _float_value(location_data, "latitude")
    center_lon = _float_value(geofence_data, "center_longitude") or _float_value(location_data, "longitude")
    radius = _float_value(geofence_data, "radius_meters") or _float_value(location_data, "geofence_radius_meters", 100)
    allowed_accuracy = _float_value(geofence_data, "allowed_accuracy_meters") or _float_value(location_data, "allowed_gps_accuracy_meters", 50)
    geofence_type = (geofence_data.get("geofence_type") or location_data.get("geofence_type") or "Circular").lower()
    distance = _haversine_meters(latitude, longitude, center_lat, center_lon)
    if "polygon" in geofence_type:
        inside = _point_in_polygon(latitude, longitude, _json_points(geofence_data.get("polygon_coordinates")))
    else:
        inside = distance <= radius
    accuracy_ok = accuracy <= allowed_accuracy
    return {
        "location_id": location_id,
        "location_name": location_data.get("location_name", ""),
        "geofence_id": geofence_data.get("geofence_id", ""),
        "geofence_type": geofence_data.get("geofence_type", "Circular"),
        "latitude": f"{latitude:.8f}",
        "longitude": f"{longitude:.8f}",
        "center_latitude": f"{center_lat:.8f}",
        "center_longitude": f"{center_lon:.8f}",
        "distance_meters": f"{distance:.2f}",
        "radius_meters": f"{radius:.2f}",
        "accuracy_meters": f"{accuracy:.2f}",
        "allowed_accuracy_meters": f"{allowed_accuracy:.2f}",
        "inside_fence": "Yes" if inside else "No",
        "accuracy_ok": "Yes" if accuracy_ok else "No",
        "geofence_status": "Inside Fence" if inside and accuracy_ok else ("Accuracy Rejected" if not accuracy_ok else "Outside Fence"),
        "validation_reason": "Coordinate can be used for attendance." if inside and accuracy_ok else "Coordinate requires review or must be rejected by attendance policy.",
        "server_validated_at": _now_iso(),
    }

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

def _notify_employee(employee_code: str, notification_type: str, title: str, message: str, email: str = ""):
    try:
        return storage.create_record("notifications", {
            "notification_id": _new_ref("NTF"),
            "recipient_employee_code": employee_code,
            "recipient_email": email or employee_code,
            "notification_type": notification_type,
            "title": title,
            "message": message,
            "read_status": "Unread",
            "delivery_status": "In App",
            "status": "Open",
        })
    except Exception:
        return None

def _employee_notifications(employee_code: str, email: str, limit: int = 100):
    rows = _items("notifications", limit)
    normalized_code = employee_code.strip().lower()
    normalized_email = email.strip().lower()
    return [
        item for item in rows
        if (
            item.get("data", {}).get("recipient_employee_code", "").strip().lower() == normalized_code
            or item.get("data", {}).get("recipient_email", "").strip().lower() == normalized_email
        )
    ]

def _salary_slip_rows(employee_code: str, limit: int = 24):
    rows = _records_for_employee("salary_slips", employee_code, limit)
    return [
        {
            "id": item.get("id", ""),
            "period": item.get("data", {}).get("period", ""),
            "gross_pay": item.get("data", {}).get("gross_pay", "0"),
            "deductions": item.get("data", {}).get("deductions", "0"),
            "net_pay": item.get("data", {}).get("net_pay", "0"),
            "payment_date": item.get("data", {}).get("payment_date", ""),
            "status": item.get("status") or item.get("data", {}).get("status", ""),
            "lines": [
                {
                    "component_name": "Gross Pay",
                    "component_type": "Earning",
                    "amount": item.get("data", {}).get("gross_pay", "0"),
                },
                {
                    "component_name": "Deductions",
                    "component_type": "Deduction",
                    "amount": item.get("data", {}).get("deductions", "0"),
                },
                {
                    "component_name": "Net Pay",
                    "component_type": "Net",
                    "amount": item.get("data", {}).get("net_pay", "0"),
                },
            ],
        }
        for item in rows
    ]

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

def _leave_day_count(start_value: str, end_value: str, half_day: bool = False) -> float:
    start = _parse_iso_date(start_value, "start_date")
    end = _parse_iso_date(end_value, "end_date")
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    if half_day and start == end:
        return 0.5
    return float((end - start).days + 1)

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

def _latest_leave_approval(application_id: str):
    approvals = [
        item for item in _items("leave_approvals", 500)
        if item.get("data", {}).get("application_id") == application_id
    ]
    return approvals[0] if approvals else None

def _effective_leave_status(application: dict[str, Any]) -> str:
    data = application.get("data", {})
    approval = _latest_leave_approval(data.get("application_id", ""))
    if approval:
        decision = approval.get("data", {}).get("decision", "")
        if decision in {"Approved", "Rejected", "Cancelled"}:
            return decision
    return data.get("approval_status") or application.get("status") or "Pending"

def _leave_application_summary(application: dict[str, Any]):
    data = application.get("data", {})
    status = _effective_leave_status(application)
    return {
        "id": application.get("id"),
        "application_id": data.get("application_id"),
        "employee_code": data.get("employee_code"),
        "leave_type": data.get("leave_type"),
        "start_date": data.get("start_date"),
        "end_date": data.get("end_date"),
        "half_day": data.get("half_day"),
        "total_leave_days": data.get("total_leave_days"),
        "reason": data.get("reason"),
        "approver": data.get("approver"),
        "approval_status": status,
        "payroll_impact": data.get("payroll_impact"),
        "status": status,
        "raw": data,
    }

def _leave_usage_by_employee():
    usage: dict[tuple[str, str, str], float] = {}
    for item in _items("leave_applications", 1000):
        data = item.get("data", {})
        if _effective_leave_status(item) != "Approved":
            continue
        key = (data.get("employee_code", ""), data.get("leave_type", ""), data.get("start_date", "")[:4] or date.today().strftime("%Y"))
        usage[key] = usage.get(key, 0.0) + _money(data.get("total_leave_days"))
    return usage

def _leave_balance_rows():
    usage = _leave_usage_by_employee()
    rows = []
    for allocation in _items("leave_allocations", 1000):
        data = allocation.get("data", {})
        key = (data.get("employee_code", ""), data.get("leave_type", ""), data.get("period", ""))
        allocated = _money(data.get("allocated_days"))
        used = usage.get(key, _money(data.get("used_days")))
        rows.append({
            "employee_code": data.get("employee_code"),
            "leave_type": data.get("leave_type"),
            "period": data.get("period"),
            "allocated_days": round(allocated, 2),
            "used_days": round(used, 2),
            "available_days": round(max(allocated - used, 0), 2),
            "expiry_date": data.get("expiry_date"),
            "status": allocation.get("status"),
        })
    return rows

def _leave_dashboard():
    applications = [_leave_application_summary(item) for item in _items("leave_applications", 1000)]
    holidays = [item.get("data", {}) for item in _items("holidays", 500)]
    calendars = [item.get("data", {}) for item in _items("holiday_calendars", 500)]
    balances = _leave_balance_rows()
    pending = [item for item in applications if item["approval_status"] in {"Open", "Pending", "Pending Approval", "Draft"}]
    approved = [item for item in applications if item["approval_status"] == "Approved"]
    rejected = [item for item in applications if item["approval_status"] == "Rejected"]
    paid_holidays = [item for item in holidays if str(item.get("paid_status", "")).lower() == "paid"]
    return {
        "stats": {
            "applications": len(applications),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "balances": len(balances),
            "holidays": len(holidays),
            "paid_holidays": len(paid_holidays),
            "calendars": len(calendars),
        },
        "applications": applications[:100],
        "pending": pending[:50],
        "balances": balances[:100],
        "holidays": holidays[:100],
        "calendars": calendars[:50],
    }

def _create_leave_application(payload: LeaveApplicationRequest, actor: str, employee_code: str | None = None):
    code = (employee_code or payload.employee_code or "").strip()
    if not code:
        raise HTTPException(status_code=422, detail="employee_code is required.")
    if not payload.leave_type.strip() or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="leave_type and reason are required.")
    days = _leave_day_count(payload.start_date, payload.end_date, payload.half_day)
    app_id = _new_ref("LEAVE")
    item = storage.create_record("leave_applications", {
        "application_id": app_id,
        "employee_code": code,
        "leave_type": payload.leave_type.strip(),
        "start_date": payload.start_date.strip(),
        "end_date": payload.end_date.strip(),
        "half_day": "Yes" if payload.half_day else "No",
        "total_leave_days": f"{days:.2f}",
        "reason": payload.reason.strip(),
        "approver": _clean_text(payload.approver),
        "approval_status": "Pending",
        "payroll_impact": payload.payroll_impact.strip() or "Paid",
        "status": "Pending",
    })
    _write_audit(actor, "apply_leave", "leave_applications", app_id, item.get("data", {}), payload.reason)
    _notify_employee(code, "leave_submitted", "Leave request submitted", f"{payload.leave_type.strip()} from {payload.start_date} to {payload.end_date} is pending approval.", actor)
    return item

def _record_key(item: dict[str, Any], id_field: str):
    data = item.get("data", {})
    return data.get(id_field) or item.get("id") or ""

def _find_record(resource: str, identifier: str, id_field: str, limit: int = 1000):
    needle = identifier.strip().lower()
    return next(
        (
            item for item in _items(resource, limit)
            if str(item.get("id", "")).lower() == needle
            or str(item.get("data", {}).get(id_field, "")).lower() == needle
        ),
        None,
    )

def _minutes_between(start_value: str | None, end_value: str | None) -> int:
    if not start_value or not end_value:
        return 0
    try:
        start = datetime.strptime(start_value[:5], "%H:%M")
        end = datetime.strptime(end_value[:5], "%H:%M")
        if end < start:
            end += timedelta(days=1)
        return int((end - start).total_seconds() // 60)
    except ValueError:
        return 0

def _attendance_row_summary(item: dict[str, Any]):
    data = item.get("data", {})
    record_id = data.get("attendance_record_id") or item.get("id")
    employee_code = data.get("employee_code", "")
    location_events = [
        event for event in _records_for_employee("attendance_location_events", employee_code, 1000)
        if event.get("data", {}).get("attendance_record_id") in {record_id, "pending"}
    ]
    biometric_events = [
        event for event in _records_for_employee("attendance_biometric_events", employee_code, 1000)
        if event.get("data", {}).get("attendance_record_id") in {record_id, "pending"}
    ]
    approvals = [
        approval for approval in _records_for_employee("attendance_approvals", employee_code, 500)
        if approval.get("data", {}).get("attendance_record_id") == record_id
    ]
    day_in_fence = data.get("day_in_geofence_status", "")
    day_out_fence = data.get("day_out_geofence_status", "")
    exception_fences = {"Outside Fence", "Out of Fence", "Accuracy Rejected", "Geofence Not Assigned"}
    if day_in_fence in exception_fences:
        geofence_status = day_in_fence
    elif day_out_fence in exception_fences:
        geofence_status = day_out_fence
    else:
        geofence_status = day_out_fence or day_in_fence or "Location Not Verified"
    missing_day_out = bool(data.get("day_in_time") and not data.get("day_out_time"))
    latest_biometric = biometric_events[0].get("data", {}) if biometric_events else {}
    return {
        "id": item.get("id"),
        "attendance_record_id": record_id,
        "employee_code": employee_code,
        "employee_name": data.get("employee_name") or employee_code,
        "department": data.get("department", ""),
        "designation": data.get("designation", ""),
        "attendance_date": data.get("attendance_date", ""),
        "shift": data.get("shift", ""),
        "day_in_time": data.get("day_in_time", ""),
        "day_out_time": data.get("day_out_time", ""),
        "gross_work_minutes": data.get("gross_work_minutes") or str(_minutes_between(data.get("day_in_time"), data.get("day_out_time"))),
        "late_duration_minutes": data.get("late_duration_minutes", ""),
        "early_exit_minutes": data.get("early_exit_minutes", ""),
        "attendance_status": data.get("attendance_status") or item.get("status") or "Open",
        "approval_status": data.get("approval_status") or item.get("status") or "Open",
        "geofence_status": geofence_status,
        "biometric_status": latest_biometric.get("verification_result") or data.get("day_in_biometric_result") or "Pending",
        "missing_day_out": missing_day_out,
        "evidence": {
            "location_events": len(location_events),
            "biometric_events": len(biometric_events),
            "approvals": len(approvals),
            "latest_location": location_events[0].get("data", {}) if location_events else None,
            "latest_biometric": latest_biometric or None,
        },
        "raw": data,
    }

def _attendance_dashboard():
    records = [_attendance_row_summary(item) for item in _items("attendance_records", 1000)]
    validation_results = _items("attendance_validation_results", 1000)
    correction_requests = _items("attendance_correction_requests", 1000)
    approvals = _items("attendance_approvals", 1000)
    out_of_fence = [
        item for item in records
        if item["geofence_status"] in {"Outside Fence", "Boundary Tolerance Applied", "Accuracy Rejected", "Geofence Not Assigned", "Out of Fence"}
    ]
    missing_day_out = [item for item in records if item["missing_day_out"]]
    pending_records = [item for item in records if item["approval_status"] in {"Open", "Pending", "Pending Approval", "Draft"}]
    pending_corrections = [
        item for item in correction_requests
        if item.get("status") in {"Open", "Pending", "Pending Approval", "Draft"}
        or item.get("data", {}).get("final_status") in {"Open", "Pending", "Pending Approval", ""}
    ]
    failed_biometrics = [
        item for item in _items("attendance_biometric_events", 1000)
        if item.get("status") == "Failed" or item.get("data", {}).get("verification_result") in {"failed", "locked", "unavailable"}
    ]
    return {
        "stats": {
            "attendance_records": len(records),
            "pending_records": len(pending_records),
            "out_of_fence": len(out_of_fence),
            "missing_day_out": len(missing_day_out),
            "correction_requests": len(correction_requests),
            "pending_corrections": len(pending_corrections),
            "failed_biometrics": len(failed_biometrics),
            "validation_results": len(validation_results),
            "approvals": len(approvals),
        },
        "records": records[:200],
        "out_of_fence": out_of_fence[:100],
        "missing_day_out": missing_day_out[:100],
        "correction_requests": correction_requests[:100],
        "pending_corrections": pending_corrections[:100],
        "validation_results": validation_results[:100],
        "failed_biometrics": failed_biometrics[:100],
    }

def _attendance_csv(rows: list[dict[str, Any]]):
    headers = [
        "attendance_record_id", "employee_code", "employee_name", "attendance_date", "shift",
        "day_in_time", "day_out_time", "gross_work_minutes", "attendance_status",
        "approval_status", "geofence_status", "biometric_status",
    ]
    lines = [",".join(headers)]
    for row in rows:
        values = []
        for header in headers:
            value = str(row.get(header, "")).replace('"', '""')
            values.append(f'"{value}"')
        lines.append(",".join(values))
    return "\n".join(lines) + "\n"

def _csv_from_rows(rows: list[dict[str, Any]], preferred_headers: list[str] | None = None):
    headers = preferred_headers or []
    seen = set(headers)
    for row in rows:
        for key in row:
            if key not in seen and not isinstance(row.get(key), (dict, list)):
                headers.append(key)
                seen.add(key)
    if not headers:
        headers = ["message"]
        rows = [{"message": "No data"}]
    lines = [",".join(headers)]
    for row in rows:
        values = []
        for header in headers:
            value = str(row.get(header, "")).replace('"', '""')
            values.append(f'"{value}"')
        lines.append(",".join(values))
    return "\n".join(lines) + "\n"

def _group_count(rows: list[dict[str, Any]], key: str):
    grouped: dict[str, int] = {}
    for row in rows:
        label = str(row.get(key) or "Unassigned")
        grouped[label] = grouped.get(label, 0) + 1
    return [{"label": label, "count": count} for label, count in sorted(grouped.items())]

def _report_sources():
    return {
        "attendance": [_attendance_row_summary(item) for item in _items("attendance_records", 1000)],
        "leave_dashboard": _leave_dashboard(),
        "payroll_results": [item.get("data", {}) for item in _items("payroll_employee_results", 1000)],
        "payroll_runs": [item.get("data", {}) for item in _items("payroll_runs", 500)],
        "adjustments": [item.get("data", {}) for item in _items("payroll_adjustments", 1000)],
        "lifecycle": [item.get("data", {}) for item in _items("employee_lifecycle_events", 1000)],
        "validation_results": [item.get("data", {}) for item in _items("attendance_validation_results", 1000)],
        "employees": [item.get("data", {}) for item in _items("employees", 1000)],
        "biometric_events": _items("attendance_biometric_events", 1000),
        "salary_revisions": [item.get("data", {}) for item in _items("salary_revision_history", 1000)],
        "audit_logs": _items("audit_logs", 1000),
    }

def _report_rows(report_id: str, sources: dict[str, Any] | None = None):
    report_id = report_id.strip().lower()
    sources = sources or _report_sources()
    attendance = sources["attendance"]
    leave_dashboard = sources["leave_dashboard"]
    payroll_results = sources["payroll_results"]
    payroll_runs = sources["payroll_runs"]
    adjustments = sources["adjustments"]
    lifecycle = sources["lifecycle"]
    validation_results = sources["validation_results"]
    employees = sources["employees"]

    if report_id == "daily_attendance":
        return attendance
    if report_id == "department_attendance":
        return [
            {
                "department": item["label"],
                "records": item["count"],
                "present": len([row for row in attendance if (row.get("department") or "Unassigned") == item["label"] and row.get("attendance_status") in {"Present", "Approved", "Attendance Corrected"}]),
                "out_of_fence": len([row for row in attendance if (row.get("department") or "Unassigned") == item["label"] and row.get("geofence_status") in {"Outside Fence", "Out of Fence", "Accuracy Rejected"}]),
            }
            for item in _group_count(attendance, "department")
        ]
    if report_id == "late_arrivals":
        return [
            row for row in attendance
            if _money(row.get("late_duration_minutes")) > 0 or row.get("attendance_status") == "Late"
        ]
    if report_id == "missing_day_out":
        return [row for row in attendance if row.get("missing_day_out")]
    if report_id == "out_of_fence":
        return [
            row for row in attendance
            if row.get("geofence_status") in {"Outside Fence", "Out of Fence", "Accuracy Rejected", "Geofence Not Assigned"}
        ]
    if report_id == "biometric_failures":
        return [
            item.get("data", {}) for item in sources["biometric_events"]
            if item.get("status") == "Failed" or item.get("data", {}).get("verification_result") in {"failed", "locked", "unavailable"}
        ]
    if report_id == "leave_usage":
        return leave_dashboard["balances"]
    if report_id == "holiday_impact":
        return leave_dashboard["holidays"]
    if report_id == "payroll_summary":
        return [
            {
                "run_no": row.get("run_no"),
                "period": row.get("period"),
                "department": row.get("department"),
                "gross_pay": row.get("gross_pay"),
                "deductions": row.get("deductions"),
                "net_pay": row.get("net_pay"),
                "approval_status": row.get("approval_status"),
                "status": row.get("status"),
            }
            for row in payroll_runs
        ] or [
            {
                "employee_code": row.get("employee_code"),
                "payroll_run": row.get("payroll_run"),
                "paid_days": row.get("paid_days"),
                "gross_pay": row.get("gross_pay"),
                "deductions": row.get("deductions"),
                "net_pay": row.get("net_pay"),
                "status": row.get("status"),
            }
            for row in payroll_results
        ]
    if report_id == "payroll_variance":
        by_employee: dict[str, list[dict[str, Any]]] = {}
        for row in payroll_results:
            by_employee.setdefault(row.get("employee_code", ""), []).append(row)
        return [
            {
                "employee_code": employee_code,
                "result_count": len(rows),
                "latest_net_pay": rows[0].get("net_pay", "0"),
                "lowest_net_pay": min(_money(row.get("net_pay")) for row in rows),
                "highest_net_pay": max(_money(row.get("net_pay")) for row in rows),
                "variance": round(max(_money(row.get("net_pay")) for row in rows) - min(_money(row.get("net_pay")) for row in rows), 2),
            }
            for employee_code, rows in by_employee.items()
        ]
    if report_id == "salary_adjustments":
        return adjustments
    if report_id == "salary_increment_history":
        return sources["salary_revisions"]
    if report_id == "employee_lifecycle":
        return lifecycle
    if report_id == "geofence_compliance":
        return [
            {
                "validation_id": row.get("validation_id"),
                "employee_code": row.get("employee_code"),
                "event_type": row.get("event_type"),
                "location_id": row.get("location_id"),
                "distance_meters": row.get("distance_meters"),
                "inside_fence": row.get("inside_fence"),
                "accuracy_meters": row.get("accuracy_meters"),
                "geofence_status": row.get("geofence_status"),
                "validation_reason": row.get("validation_reason"),
                "server_validated_at": row.get("server_validated_at"),
                "status": row.get("status"),
            }
            for row in validation_results
        ]
    if report_id == "employee_turnover":
        exit_events = [row for row in lifecycle if row.get("event_type", "").lower() in {"resignation", "termination", "exit clearance", "final settlement"}]
        join_events = [row for row in lifecycle if row.get("event_type", "").lower() in {"employee joined", "offer accepted", "rehire"}]
        return [
            {"metric": "active_employees", "count": len([row for row in employees if row.get("status") == "Active"])},
            {"metric": "join_events", "count": len(join_events)},
            {"metric": "exit_events", "count": len(exit_events)},
            {"metric": "turnover_percent", "count": round((len(exit_events) / max(len(employees), 1)) * 100, 2)},
        ]
    raise HTTPException(status_code=404, detail="Report not found")

def _report_catalog():
    return [
        {"id": "daily_attendance", "title": "Daily Attendance", "domain": "Attendance", "description": "Employee day-in/day-out, approval, geofence, and biometric status."},
        {"id": "department_attendance", "title": "Department Attendance", "domain": "Attendance", "description": "Attendance counts grouped by department."},
        {"id": "late_arrivals", "title": "Late Arrivals", "domain": "Attendance", "description": "Late employees and late-duration evidence."},
        {"id": "missing_day_out", "title": "Missing Day Out", "domain": "Attendance", "description": "Employees checked in without a recorded day-out."},
        {"id": "out_of_fence", "title": "Out-of-Fence Attendance", "domain": "Geofence", "description": "Geofence exceptions and rejected location validation evidence."},
        {"id": "biometric_failures", "title": "Biometric Failures", "domain": "Attendance", "description": "Failed, locked, or unavailable biometric events."},
        {"id": "leave_usage", "title": "Leave Usage", "domain": "Leave", "description": "Allocated, used, and available leave balances."},
        {"id": "holiday_impact", "title": "Holiday Impact", "domain": "Leave", "description": "Paid/unpaid holidays and payroll impact."},
        {"id": "payroll_summary", "title": "Payroll Summary", "domain": "Payroll", "description": "Payroll runs or employee payroll result totals."},
        {"id": "payroll_variance", "title": "Payroll Variance", "domain": "Payroll", "description": "Net-pay spread by employee across generated payroll results."},
        {"id": "salary_adjustments", "title": "Salary Adjustments", "domain": "Finance", "description": "Approved and pending finance payroll adjustments."},
        {"id": "salary_increment_history", "title": "Salary Increment History", "domain": "HR", "description": "Employee salary revisions and increment history."},
        {"id": "employee_lifecycle", "title": "Employee Lifecycle Events", "domain": "HR", "description": "Promotions, transfers, warnings, exits, and other lifecycle events."},
        {"id": "employee_turnover", "title": "Employee Turnover", "domain": "HR", "description": "Join, exit, and turnover metrics."},
        {"id": "geofence_compliance", "title": "Geofence Compliance", "domain": "Geofence", "description": "Location validation outcomes, distances, and accuracy evidence."},
    ]

def _reports_dashboard():
    catalog = _report_catalog()
    sources = _report_sources()
    reports = []
    for report in catalog:
        rows = _report_rows(report["id"], sources)
        reports.append({
            **report,
            "row_count": len(rows),
            "sample": rows[:5],
        })
    summary = {
        "reports": len(reports),
        "attendance_records": len(sources["attendance"]),
        "leave_applications": len(sources["leave_dashboard"]["applications"]),
        "payroll_results": len(sources["payroll_results"]),
        "geofence_validations": len(sources["validation_results"]),
        "audit_events": len(sources["audit_logs"]),
    }
    return {"stats": summary, "reports": reports}

def _security_dashboard():
    users = storage.list_users(250)
    bootstrap = {
        "email": ADMIN_EMAIL.strip().lower(),
        "full_name": "FactoryPulse Admin",
        "role": "FACTORY_ADMIN",
        "department_id": "admin",
        "status": "Active",
        "failed_login_count": 0,
        "locked_until": None,
        "bootstrap": True,
    }
    user_rows = [bootstrap, *users]
    audit_logs = _items("audit_logs", 500)
    device_events = _items("device_integrity_events", 500)
    permission_denied = [item for item in audit_logs if item.get("data", {}).get("action") == "permission_denied"]
    locked_users = [item for item in user_rows if _locked_until_epoch(item.get("locked_until")) > int(time.time())]
    failed_login_users = [item for item in user_rows if int(item.get("failed_login_count") or 0) > 0]
    return {
        "stats": {
            "users": len(user_rows),
            "active_users": len([item for item in user_rows if item.get("status") == "Active"]),
            "locked_users": len(locked_users),
            "failed_login_users": len(failed_login_users),
            "roles": len(ROLE_PERMISSIONS),
            "audit_logs": len(audit_logs),
            "permission_denied_events": len(permission_denied),
            "device_integrity_events": len(device_events),
        },
        "users": user_rows,
        "roles": [
            {"role": role, "permissions": sorted(permissions)}
            for role, permissions in sorted(ROLE_PERMISSIONS.items())
        ],
        "recent_audit": audit_logs[:50],
        "permission_denied": permission_denied[:50],
        "device_integrity_events": device_events[:50],
        "protected_surfaces": [
            {"surface": "HR administration", "permission": "hr:*"},
            {"surface": "Finance payroll", "permission": "finance:*"},
            {"surface": "Reports", "permission": "reports:read"},
            {"surface": "Generic record writes", "permission": "records:<department> or department write"},
            {"surface": "Security center", "permission": "admin:security"},
            {"surface": "Operations jobs", "permission": "admin:ops"},
        ],
    }

def _audit_row(item: dict[str, Any]):
    data = item.get("data", {})
    return {
        "id": item.get("id", ""),
        "audit_id": data.get("audit_id", item.get("id", "")),
        "actor": data.get("actor", ""),
        "action": data.get("action", ""),
        "entity_type": data.get("entity_type", ""),
        "entity_id": data.get("entity_id", ""),
        "reason": data.get("reason", ""),
        "ip_address": data.get("ip_address", ""),
        "device_info": data.get("device_info", ""),
        "approval_reference": data.get("approval_reference", ""),
        "status": item.get("status") or data.get("status", ""),
        "new_values": data.get("new_values", ""),
        "previous_values": data.get("previous_values", ""),
    }

def _audit_dashboard():
    rows = [_audit_row(item) for item in _items("audit_logs", 1000)]
    permission_denied = [row for row in rows if row["action"] == "permission_denied"]
    sensitive = [
        row for row in rows
        if row["entity_type"] in {"attendance_records", "payroll_runs", "payroll_adjustments", "employees", "app_users", "rbac"}
    ]
    actions: dict[str, int] = {}
    actors: dict[str, int] = {}
    entities: dict[str, int] = {}
    for row in rows:
        actions[row["action"] or "unknown"] = actions.get(row["action"] or "unknown", 0) + 1
        actors[row["actor"] or "unknown"] = actors.get(row["actor"] or "unknown", 0) + 1
        entities[row["entity_type"] or "unknown"] = entities.get(row["entity_type"] or "unknown", 0) + 1
    return {
        "stats": {
            "events": len(rows),
            "permission_denied": len(permission_denied),
            "sensitive_events": len(sensitive),
            "actors": len(actors),
            "actions": len(actions),
            "entities": len(entities),
        },
        "events": rows[:500],
        "permission_denied": permission_denied[:100],
        "sensitive_events": sensitive[:100],
        "actions": [{"label": key, "count": count} for key, count in sorted(actions.items(), key=lambda item: item[1], reverse=True)[:20]],
        "actors": [{"label": key, "count": count} for key, count in sorted(actors.items(), key=lambda item: item[1], reverse=True)[:20]],
        "entities": [{"label": key, "count": count} for key, count in sorted(entities.items(), key=lambda item: item[1], reverse=True)[:20]],
    }

def _job_record(job_type: str, actor: str, status: str):
    return storage.create_record("automation_jobs", {
        "job_no": _new_ref("JOB"),
        "system": "FactoryPulse ERP",
        "job_type": job_type,
        "schedule": "Manual",
        "last_run": _now_iso(),
        "owner": actor,
        "status": status,
    })

def _run_missing_day_out_job(actor: str, dry_run: bool):
    rows = _items("attendance_records", 1000)
    affected = []
    for item in rows:
        data = item.get("data", {})
        if data.get("day_in_time") and not data.get("day_out_time") and data.get("attendance_status") != "Missing Day Out":
            affected.append(item)
    if not dry_run:
        for item in affected:
            data = item.get("data", {})
            storage.update_record("attendance_records", item.get("id", ""), {
                "attendance_status": "Missing Day Out",
                "approval_status": "Pending Approval",
                "hr_remarks": "Detected by missing day-out background job.",
                "status": "Pending Approval",
            })
            _notify_employee(data.get("employee_code", ""), "missing_day_out", "Missing Day Out", f"{data.get('attendance_date', 'Today')} has no Day Out. Submit a correction or contact HR.", data.get("employee_code", ""))
    return {"affected": len(affected), "records": [_attendance_row_summary(item) for item in affected[:50]]}

def _run_late_mark_job(actor: str, dry_run: bool):
    policy = _attendance_policy()
    late_after = _late_after_time(policy)
    rows = _items("attendance_records", 1000)
    affected = []
    for item in rows:
        data = item.get("data", {})
        day_in = data.get("day_in_time", "")
        if day_in and day_in > late_after and data.get("attendance_status") != "Late":
            affected.append(item)
    if not dry_run:
        for item in affected:
            data = item.get("data", {})
            minutes_late = max(_minutes_between(late_after, data.get("day_in_time", "")), 0)
            storage.update_record("attendance_records", item.get("id", ""), {
                "late_duration_minutes": str(minutes_late),
                "attendance_status": "Late",
                "approval_status": data.get("approval_status") or "Approved",
                "hr_remarks": f"Late mark calculated after {late_after}.",
                "status": "Late",
            })
            _notify_employee(data.get("employee_code", ""), "late_attendance", "Late attendance marked", f"{data.get('attendance_date', 'Today')} Day In was after {late_after}.", data.get("employee_code", ""))
    return {"affected": len(affected), "late_after_time": late_after, "records": [_attendance_row_summary(item) for item in affected[:50]]}

def _run_notification_delivery_job(actor: str, dry_run: bool):
    rows = _items("notifications", 1000)
    pending = [item for item in rows if item.get("data", {}).get("delivery_status", "") in {"", "Pending"} or item.get("status") == "Open"]
    if not dry_run:
        for item in pending:
            storage.update_record("notifications", item.get("id", ""), {
                "delivery_status": "In App",
                "status": item.get("data", {}).get("read_status") == "Read" and "Closed" or "Open",
            })
    return {"affected": len(pending), "notifications": [item.get("data", {}) for item in pending[:50]]}

def _run_payroll_preparation_job(actor: str, dry_run: bool):
    employees = _items("employees", 1000)
    salary_assignments = _items("employee_salary_assignments", 1000)
    attendance_exceptions = [
        row for row in _attendance_dashboard()["records"]
        if row.get("missing_day_out") or row.get("approval_status") in {"Open", "Pending", "Pending Approval"}
    ]
    missing_salary = [
        item.get("data", {}).get("employee_code") or item.get("data", {}).get("email", "")
        for item in employees
        if not _salary_assignment_for(item.get("data", {}).get("employee_code") or item.get("data", {}).get("email", ""))
    ]
    return {
        "affected": len(attendance_exceptions) + len(missing_salary),
        "employees": len(employees),
        "salary_assignments": len(salary_assignments),
        "attendance_exceptions": attendance_exceptions[:50],
        "missing_salary_assignments": missing_salary[:50],
        "ready_for_payroll": not attendance_exceptions and not missing_salary,
    }

def _operations_dashboard():
    jobs = _items("automation_jobs", 200)
    notifications = _items("notifications", 500)
    attendance = _attendance_dashboard()
    return {
        "stats": {
            "jobs": len(jobs),
            "completed_jobs": _status_count(jobs, "Completed"),
            "dry_runs": len([item for item in jobs if item.get("data", {}).get("schedule") == "Manual Dry Run"]),
            "notifications_open": _status_count(notifications, "Open"),
            "missing_day_out": attendance["stats"]["missing_day_out"],
            "pending_attendance": attendance["stats"]["pending_records"],
        },
        "jobs": jobs[:100],
        "available_jobs": [
            {"job_type": "missing_day_out_detection", "title": "Missing Day Out Detection", "description": "Find active Day In records without Day Out and send employee notifications."},
            {"job_type": "late_mark_finalization", "title": "Late Mark Finalization", "description": "Apply HR policy late marks from backend attendance records."},
            {"job_type": "notification_delivery", "title": "Notification Delivery", "description": "Finalize in-app notification delivery status for open notifications."},
            {"job_type": "payroll_preparation", "title": "Payroll Preparation", "description": "Check attendance exceptions and missing salary assignments before payroll."},
        ],
        "attendance_exceptions": {
            "missing_day_out": attendance["missing_day_out"][:50],
            "out_of_fence": attendance["out_of_fence"][:50],
            "pending_corrections": attendance["pending_corrections"][:50],
        },
    }

def _run_operations_job(job_type: str, actor: str, dry_run: bool = False):
    normalized = job_type.strip().lower()
    runners = {
        "missing_day_out_detection": _run_missing_day_out_job,
        "late_mark_finalization": _run_late_mark_job,
        "notification_delivery": _run_notification_delivery_job,
        "payroll_preparation": _run_payroll_preparation_job,
    }
    if normalized not in runners:
        raise HTTPException(status_code=422, detail=f"job_type must be one of: {', '.join(sorted(runners))}")
    result = runners[normalized](actor, dry_run)
    job = None
    if not dry_run:
        job = _job_record(normalized, actor, "Completed")
    else:
        job = storage.create_record("automation_jobs", {
            "job_no": _new_ref("JOB"),
            "system": "FactoryPulse ERP",
            "job_type": normalized,
            "schedule": "Manual Dry Run",
            "last_run": _now_iso(),
            "owner": actor,
            "status": "Draft",
        })
    _write_audit(actor, "run_operations_job", "automation_jobs", job.get("data", {}).get("job_no", job.get("id", "")), {"job_type": normalized, "dry_run": dry_run, "result": result}, "Operations background job executed.")
    return {"job": job, "result": result, "dashboard": _operations_dashboard()}

def _apply_attendance_correction(request: dict[str, Any], actor: str, comments: str):
    data = request.get("data", {})
    employee_code = data.get("employee_code", "")
    attendance_date = data.get("attendance_date", "")
    record = next(
        (
            item for item in _records_for_employee("attendance_records", employee_code, 1000)
            if item.get("data", {}).get("attendance_date") == attendance_date
        ),
        None,
    )
    update_payload = {
        "approval_status": "Approved",
        "attendance_status": "Attendance Corrected",
        "hr_remarks": comments or data.get("reason", "Attendance corrected by HR"),
        "status": "Attendance Corrected",
    }
    if data.get("requested_day_in_time"):
        update_payload["day_in_time"] = data.get("requested_day_in_time")
    if data.get("requested_day_out_time"):
        update_payload["day_out_time"] = data.get("requested_day_out_time")
    if update_payload.get("day_in_time") and update_payload.get("day_out_time"):
        minutes = _minutes_between(update_payload.get("day_in_time"), update_payload.get("day_out_time"))
        update_payload["gross_work_minutes"] = str(minutes)
        update_payload["net_work_minutes"] = str(minutes)
    if record:
        updated = storage.update_record("attendance_records", record.get("id", ""), update_payload)
    else:
        employee = _active_record(_records_for_employee("employees", employee_code, 20))
        employee_data = employee.get("data", {}) if employee else {}
        updated = storage.create_record("attendance_records", {
            "attendance_record_id": _new_ref("ATT"),
            "employee_code": employee_code,
            "employee_name": employee_data.get("full_name", employee_code),
            "department": employee_data.get("department", ""),
            "designation": employee_data.get("role", ""),
            "company": "",
            "branch": "",
            "work_location": "",
            "shift": employee_data.get("shift", ""),
            "attendance_date": attendance_date,
            "day_in_time": data.get("requested_day_in_time", ""),
            "day_out_time": data.get("requested_day_out_time", ""),
            "day_in_geofence_status": "Manual Override",
            "day_out_geofence_status": "Manual Override",
            "day_in_biometric_result": "Manual Correction",
            "day_out_biometric_result": "Manual Correction",
            "gross_work_minutes": str(_minutes_between(data.get("requested_day_in_time"), data.get("requested_day_out_time"))),
            "net_work_minutes": str(_minutes_between(data.get("requested_day_in_time"), data.get("requested_day_out_time"))),
            "attendance_status": "Attendance Corrected",
            "payroll_status": "Pending",
            "approval_status": "Approved",
            "employee_remarks": data.get("reason", ""),
            "hr_remarks": comments,
            "source": "hr_correction",
            "status": "Attendance Corrected",
        })
    _write_audit(actor, "apply_attendance_correction", "attendance_records", updated.get("id", ""), updated.get("data", {}), comments)
    return updated

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

def _salary_totals(basic_salary: float, allowances: float, deductions: float, employer_contributions: float = 0, employee_contributions: float = 0):
    basic = max(float(basic_salary or 0), 0)
    allow = max(float(allowances or 0), 0)
    deduct = max(float(deductions or 0), 0)
    employer = max(float(employer_contributions or 0), 0)
    employee = max(float(employee_contributions or 0), 0)
    gross = round(basic + allow, 2)
    ctc = round(gross + employer, 2)
    net = round(gross - deduct - employee, 2)
    return {
        "basic_salary": basic,
        "allowances": allow,
        "deductions": deduct,
        "employer_contributions": employer,
        "employee_contributions": employee,
        "gross_salary": gross,
        "ctc": ctc,
        "net_salary_estimate": net,
    }

def _fmt_money(value: float):
    return f"{float(value or 0):.2f}"

def _find_salary_revision(revision_id: str):
    normalized = revision_id.strip().lower()
    for item in _items("salary_revision_history", 1000):
        data = item.get("data", {})
        if item.get("id", "").lower() == normalized or data.get("revision_id", "").strip().lower() == normalized:
            return item
    return None

def _salary_dashboard():
    structures = _items("salary_structures", 250)
    components = _items("salary_structure_components", 500)
    assignments = _items("employee_salary_assignments", 1000)
    revisions = _items("salary_revision_history", 1000)
    pending_revisions = [
        item for item in revisions
        if (item.get("data", {}).get("approval_status") or item.get("status")) in {"Pending Approval", "Pending", "Draft", "Open"}
    ]
    approved_revisions = [
        item for item in revisions
        if (item.get("data", {}).get("approval_status") or item.get("status")) == "Approved"
    ]
    current_ctc = sum(_money(item.get("data", {}).get("ctc")) for item in assignments if (item.get("data", {}).get("status") or item.get("status")) == "Active")
    return {
        "stats": {
            "structures": len(structures),
            "components": len(components),
            "assignments": len(assignments),
            "active_assignments": len([item for item in assignments if (item.get("data", {}).get("status") or item.get("status")) == "Active"]),
            "pending_revisions": len(pending_revisions),
            "approved_revisions": len(approved_revisions),
            "current_ctc": round(current_ctc, 2),
        },
        "structures": structures[:100],
        "components": components[:200],
        "assignments": assignments[:200],
        "pending_revisions": pending_revisions[:100],
        "recent_revisions": revisions[:200],
    }

def _create_salary_structure(payload: SalaryStructureRequest, actor: str):
    if not payload.structure_name.strip():
        raise HTTPException(status_code=422, detail="structure_name is required.")
    totals = _salary_totals(payload.basic_salary, payload.allowances, payload.deductions, payload.employer_contributions, payload.employee_contributions)
    structure_id = _clean_text(payload.structure_id) or _new_ref("SAL-STRUCT")
    item = storage.create_record("salary_structures", {
        "structure_id": structure_id,
        "structure_name": payload.structure_name.strip(),
        "currency": payload.currency.strip() or "INR",
        "payment_frequency": payload.payment_frequency.strip() or "Monthly",
        "proration_method": payload.proration_method.strip() or "Payroll Policy",
        "basic_salary": _fmt_money(totals["basic_salary"]),
        "allowances": _fmt_money(totals["allowances"]),
        "deductions": _fmt_money(totals["deductions"]),
        "employer_contributions": _fmt_money(totals["employer_contributions"]),
        "employee_contributions": _fmt_money(totals["employee_contributions"]),
        "gross_salary": _fmt_money(totals["gross_salary"]),
        "ctc": _fmt_money(totals["ctc"]),
        "net_salary_estimate": _fmt_money(totals["net_salary_estimate"]),
        "approval_status": payload.approval_status.strip() or "Approved",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(actor, "create_salary_structure", "salary_structures", structure_id, item.get("data", {}), "Salary structure created.")
    return {"item": item, "dashboard": _salary_dashboard()}

def _create_salary_component(payload: SalaryComponentRequest, actor: str):
    if not payload.structure_id.strip() or not payload.component_name.strip():
        raise HTTPException(status_code=422, detail="structure_id and component_name are required.")
    component_type = payload.component_type.strip()
    if component_type not in {"Earning", "Deduction", "Employer Contribution", "Employee Contribution"}:
        raise HTTPException(status_code=422, detail="component_type must be Earning, Deduction, Employer Contribution, or Employee Contribution.")
    if payload.amount < 0:
        raise HTTPException(status_code=422, detail="amount cannot be negative.")
    item = storage.create_record("salary_structure_components", {
        "component_id": _new_ref("SCOMP"),
        "structure_id": payload.structure_id.strip(),
        "component_name": payload.component_name.strip(),
        "component_type": component_type,
        "calculation_method": payload.calculation_method.strip() or "Fixed",
        "amount": _fmt_money(payload.amount),
        "percentage_of": _clean_text(payload.percentage_of),
        "taxable": "Yes" if payload.taxable else "No",
        "payroll_impact": payload.payroll_impact.strip() or "Gross",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(actor, "create_salary_component", "salary_structure_components", item.get("data", {}).get("component_id", item.get("id", "")), item.get("data", {}), "Salary component created.")
    return {"item": item, "dashboard": _salary_dashboard()}

def _create_salary_assignment(payload: SalaryAssignmentRequest, actor: str, reason: str = "Salary assignment created."):
    if not payload.employee_code.strip() or not payload.structure_id.strip() or not payload.effective_date.strip():
        raise HTTPException(status_code=422, detail="employee_code, structure_id, and effective_date are required.")
    _parse_iso_date(payload.effective_date, "effective_date")
    totals = _salary_totals(payload.basic_salary, payload.allowances, payload.deductions, payload.employer_contributions, payload.employee_contributions)
    item = storage.create_record("employee_salary_assignments", {
        "assignment_id": _new_ref("SAL-ASG"),
        "employee_code": payload.employee_code.strip(),
        "structure_id": payload.structure_id.strip(),
        "effective_date": payload.effective_date.strip(),
        "basic_salary": _fmt_money(totals["basic_salary"]),
        "allowances": _fmt_money(totals["allowances"]),
        "deductions": _fmt_money(totals["deductions"]),
        "employer_contributions": _fmt_money(totals["employer_contributions"]),
        "employee_contributions": _fmt_money(totals["employee_contributions"]),
        "gross_salary": _fmt_money(totals["gross_salary"]),
        "ctc": _fmt_money(totals["ctc"]),
        "net_salary_estimate": _fmt_money(totals["net_salary_estimate"]),
        "currency": payload.currency.strip() or "INR",
        "payment_frequency": payload.payment_frequency.strip() or "Monthly",
        "approval_status": payload.approval_status.strip() or "Approved",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(actor, "create_salary_assignment", "employee_salary_assignments", item.get("data", {}).get("assignment_id", item.get("id", "")), item.get("data", {}), reason)
    _notify_employee(payload.employee_code.strip(), "salary_revision_approved", "Salary assignment updated", f"Effective {payload.effective_date}, gross salary is {totals['gross_salary']:.2f}.", payload.employee_code.strip())
    return item

def _request_salary_revision(payload: SalaryRevisionRequest, actor: str):
    if not payload.employee_code.strip() or not payload.structure_id.strip() or not payload.reason.strip():
        raise HTTPException(status_code=422, detail="employee_code, structure_id, and reason are required.")
    _parse_iso_date(payload.effective_date, "effective_date")
    current = _salary_assignment_for(payload.employee_code.strip())
    current_ctc = _money(current.get("data", {}).get("ctc")) if current else 0
    totals = _salary_totals(payload.basic_salary, payload.allowances, payload.deductions)
    increase = round(totals["ctc"] - current_ctc, 2)
    increase_percent = round((increase / current_ctc) * 100, 2) if current_ctc else 0
    item = storage.create_record("salary_revision_history", {
        "revision_id": _new_ref("SAL-REV"),
        "employee_code": payload.employee_code.strip(),
        "structure_id": payload.structure_id.strip(),
        "effective_date": payload.effective_date.strip(),
        "basic_salary": _fmt_money(totals["basic_salary"]),
        "allowances": _fmt_money(totals["allowances"]),
        "deductions": _fmt_money(totals["deductions"]),
        "gross_salary": _fmt_money(totals["gross_salary"]),
        "ctc": _fmt_money(totals["ctc"]),
        "net_salary_estimate": _fmt_money(totals["net_salary_estimate"]),
        "revision_type": payload.revision_type.strip() or "Salary Revision",
        "previous_salary": _fmt_money(current_ctc),
        "new_salary": _fmt_money(totals["ctc"]),
        "increase_amount": _fmt_money(increase),
        "increase_percent": f"{increase_percent:.2f}",
        "reason": payload.reason.strip(),
        "supporting_document": _clean_text(payload.supporting_document),
        "requested_by": actor,
        "approved_by": "",
        "approval_status": "Pending Approval",
        "created_time": _now_iso(),
        "status": "Pending Approval",
    })
    _write_audit(actor, "request_salary_revision", "salary_revision_history", item.get("data", {}).get("revision_id", item.get("id", "")), item.get("data", {}), payload.reason)
    return {"item": item, "dashboard": _salary_dashboard()}

def _decide_salary_revision(payload: SalaryRevisionDecisionRequest, actor: str):
    item = _find_salary_revision(payload.revision_id)
    if not item:
        raise HTTPException(status_code=404, detail="Salary revision not found.")
    data = item.get("data", {})
    decision = payload.decision.strip().title()
    if decision not in {"Approved", "Rejected"}:
        raise HTTPException(status_code=422, detail="decision must be Approved or Rejected.")
    if (data.get("approval_status") or item.get("status")) not in {"Pending Approval", "Pending", "Draft", "Open"}:
        raise HTTPException(status_code=409, detail="Salary revision is already decided.")
    updated = storage.update_record("salary_revision_history", item.get("id", ""), {
        "approval_status": decision,
        "approved_by": actor if decision == "Approved" else "",
        "status": decision,
    })
    if decision == "Approved":
        _create_salary_assignment(SalaryAssignmentRequest(
            employee_code=data.get("employee_code", ""),
            structure_id=data.get("structure_id", ""),
            effective_date=data.get("effective_date", _today()),
            basic_salary=_money(data.get("basic_salary")),
            allowances=_money(data.get("allowances")),
            deductions=_money(data.get("deductions")),
        ), actor, "Approved salary revision created new effective salary assignment.")
        _create_lifecycle_event(HrLifecycleEventRequest(
            employee_code=data.get("employee_code", ""),
            event_type="Salary Revision",
            effective_date=data.get("effective_date", _today()),
            previous_value=data.get("previous_salary", ""),
            new_value=data.get("new_salary", ""),
            reason=payload.remarks or data.get("reason", "Salary revision approved"),
            approved_by=actor,
            status="Approved",
        ), actor)
    else:
        _notify_employee(data.get("employee_code", ""), "salary_revision_rejected", "Salary revision rejected", payload.remarks or "Salary revision was rejected.", data.get("employee_code", ""))
    _write_audit(actor, f"{decision.lower()}_salary_revision", "salary_revision_history", data.get("revision_id", item.get("id", "")), updated.get("data", {}), payload.remarks or decision)
    return {"item": updated, "dashboard": _salary_dashboard()}

PAYROLL_ADJUSTMENT_TYPES = {
    "Additional Salary", "Deduction", "Bonus", "Incentive", "Reimbursement", "Arrear", "Recovery",
    "Loan Deduction", "Advance Deduction", "Attendance Penalty", "Unpaid Leave Deduction",
    "Holiday Adjustment", "Correction", "Tax Adjustment", "Other Approved Adjustment", "Reversal",
}
PAYROLL_LOCKED_STATUSES = {"Approved", "Locked", "Payment Processing", "Paid", "Partially Paid"}
PAYROLL_PAYMENT_READY_STATUSES = {"Approved", "Locked", "Payment Processing", "Partially Paid"}
PAYROLL_PAYMENT_FINAL_STATUSES = {"Paid", "Cancelled", "Reversed"}
FINANCE_ADJUSTMENT_LIMIT = float(os.getenv("FINANCE_ADJUSTMENT_LIMIT", "50000"))
PAYROLL_PRORATION_METHODS = {"Calendar Day", "Working Day", "Fixed Divisor", "Organization Specific Formula"}

def _csv_values(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        raw = json.loads(value)
        if isinstance(raw, list):
            return [str(item).strip() for item in raw if str(item).strip()]
    except Exception:
        pass
    return [item.strip() for item in value.split(",") if item.strip()]

def _active_payroll_policy():
    rows = _items("payroll_policies", 100)
    active = [
        item for item in rows
        if (item.get("data", {}).get("status") or item.get("status")) == "Active"
        and (item.get("data", {}).get("approval_status") or "Approved") == "Approved"
    ]
    if active:
        return active[0]
    categories = sorted(PAYROLL_ADJUSTMENT_TYPES - {"Reversal"})
    return {
        "id": "default",
        "status": "Active",
        "data": {
            "policy_id": "DEFAULT-PAYROLL-POLICY",
            "policy_name": "Default Payroll Policy",
            "proration_method": "Calendar Day",
            "fixed_divisor": "",
            "rounding_rule": "Round 2 Decimals",
            "max_adjustment_amount": f"{FINANCE_ADJUSTMENT_LIMIT:.2f}",
            "role_adjustment_limits": "",
            "retroactive_months_allowed": "2",
            "approval_required": "true",
            "lock_after_approval": "true",
            "allow_reversal_after_lock": "true",
            "adjustment_categories": ", ".join(categories),
            "statutory_notes": "Default policy generated from environment configuration.",
            "effective_start_date": "",
            "effective_end_date": "",
            "created_by": "system",
            "updated_by": "system",
            "approval_status": "Approved",
            "status": "Active",
        },
    }

def _payroll_policy_categories(policy: dict[str, Any] | None = None):
    data = (policy or _active_payroll_policy()).get("data", {})
    categories = _csv_values(data.get("adjustment_categories"))
    return categories or sorted(PAYROLL_ADJUSTMENT_TYPES - {"Reversal"})

def _payroll_adjustment_limit(policy: dict[str, Any] | None = None):
    data = (policy or _active_payroll_policy()).get("data", {})
    return _money(data.get("max_adjustment_amount"), FINANCE_ADJUSTMENT_LIMIT) or FINANCE_ADJUSTMENT_LIMIT

def _bool_setting(value: Any, default: bool = True) -> bool:
    if value in (None, ""):
        return default
    return str(value).strip().lower() in {"1", "true", "yes", "on"}

def _role_adjustment_limit(policy: dict[str, Any], actor: str):
    data = policy.get("data", {})
    base_limit = _payroll_adjustment_limit(policy)
    role_limits = data.get("role_adjustment_limits", "")
    if not role_limits:
        return base_limit
    try:
        parsed = json.loads(role_limits)
    except Exception:
        return base_limit
    role = _user_context(actor).get("role", "")
    try:
        role_limit = float(parsed.get(role, base_limit))
    except (TypeError, ValueError, AttributeError):
        role_limit = base_limit
    return min(base_limit, role_limit) if role_limit > 0 else base_limit

def _month_distance_from_current(period: str):
    try:
        year, month = [int(part) for part in period[:7].split("-", 1)]
    except Exception:
        return 0
    today = date.today()
    return (today.year - year) * 12 + (today.month - month)

def _enforce_retroactive_adjustment_rule(policy: dict[str, Any], payroll_month: str):
    allowed = int(_money(policy.get("data", {}).get("retroactive_months_allowed"), 0))
    distance = _month_distance_from_current(payroll_month)
    if distance > allowed:
        raise HTTPException(status_code=422, detail=f"Retroactive adjustments are limited to {allowed} month(s) by payroll policy.")

def _working_days_between(start: date, end: date):
    days = 0
    cursor = start
    while cursor <= end:
        if cursor.weekday() < 5:
            days += 1
        cursor += timedelta(days=1)
    return max(days, 1)

def _payroll_divisor(policy: dict[str, Any], start: date, end: date, total_days: int):
    data = policy.get("data", {})
    method = data.get("proration_method") or "Calendar Day"
    if method == "Working Day":
        return _working_days_between(start, end), "working_days"
    if method == "Fixed Divisor":
        return max(_money(data.get("fixed_divisor"), total_days), 1), "fixed_divisor"
    if method == "Organization Specific Formula":
        divisor = _money(data.get("fixed_divisor"), total_days) or total_days
        return max(divisor, 1), "organization_specific_formula"
    return total_days, "calendar_days"

def _payroll_policy_dashboard():
    policies = _items("payroll_policies", 100)
    active = _active_payroll_policy()
    data = active.get("data", {})
    adjustments = _items("payroll_adjustments", 500)
    runs = _items("payroll_runs", 250)
    locked_runs = [item for item in runs if (item.get("data", {}).get("approval_status") or item.get("status")) in PAYROLL_LOCKED_STATUSES]
    return {
        "active_policy": data,
        "policies": policies[:50],
        "stats": {
            "policies": len(policies),
            "active_policies": len([item for item in policies if (item.get("data", {}).get("status") or item.get("status")) == "Active"]),
            "adjustments": len(adjustments),
            "locked_runs": len(locked_runs),
            "max_adjustment_amount": _payroll_adjustment_limit(active),
            "retroactive_months_allowed": int(_money(data.get("retroactive_months_allowed"), 0)),
        },
        "allowed_proration_methods": sorted(PAYROLL_PRORATION_METHODS),
        "default_adjustment_categories": sorted(PAYROLL_ADJUSTMENT_TYPES - {"Reversal"}),
    }

def _save_payroll_policy(payload: PayrollPolicyRequest, actor: str):
    method = payload.proration_method.strip()
    if method not in PAYROLL_PRORATION_METHODS:
        raise HTTPException(status_code=422, detail=f"proration_method must be one of: {', '.join(sorted(PAYROLL_PRORATION_METHODS))}")
    if payload.max_adjustment_amount <= 0:
        raise HTTPException(status_code=422, detail="max_adjustment_amount must be greater than zero.")
    if method == "Fixed Divisor" and (payload.fixed_divisor is None or payload.fixed_divisor <= 0):
        raise HTTPException(status_code=422, detail="fixed_divisor is required for Fixed Divisor proration.")
    if payload.retroactive_months_allowed < 0:
        raise HTTPException(status_code=422, detail="retroactive_months_allowed cannot be negative.")
    categories = _csv_values(payload.adjustment_categories) or sorted(PAYROLL_ADJUSTMENT_TYPES - {"Reversal"})
    invalid_categories = sorted(set(categories) - (PAYROLL_ADJUSTMENT_TYPES - {"Reversal"}))
    if invalid_categories:
        raise HTTPException(status_code=422, detail=f"Unsupported adjustment categories: {', '.join(invalid_categories)}")
    now = _now_iso()
    for item in _items("payroll_policies", 100):
        data = item.get("data", {})
        if (data.get("status") or item.get("status")) == "Active":
            storage.update_record("payroll_policies", item.get("id", ""), {
                "status": "Inactive",
                "updated_by": actor,
            })
    item = storage.create_record("payroll_policies", {
        "policy_id": _new_ref("PPOL"),
        "policy_name": payload.policy_name.strip() or "Payroll Policy",
        "proration_method": method,
        "fixed_divisor": f"{payload.fixed_divisor:.2f}" if payload.fixed_divisor is not None else "",
        "rounding_rule": payload.rounding_rule.strip() or "Round 2 Decimals",
        "max_adjustment_amount": f"{payload.max_adjustment_amount:.2f}",
        "role_adjustment_limits": _clean_text(payload.role_adjustment_limits),
        "retroactive_months_allowed": str(payload.retroactive_months_allowed),
        "approval_required": "true" if payload.approval_required else "false",
        "lock_after_approval": "true" if payload.lock_after_approval else "false",
        "allow_reversal_after_lock": "true" if payload.allow_reversal_after_lock else "false",
        "adjustment_categories": ", ".join(categories),
        "statutory_notes": _clean_text(payload.statutory_notes),
        "effective_start_date": _clean_text(payload.effective_start_date),
        "effective_end_date": _clean_text(payload.effective_end_date),
        "created_by": actor,
        "updated_by": actor,
        "approval_status": payload.approval_status.strip() or "Approved",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(actor, "save_payroll_policy", "payroll_policies", item.get("data", {}).get("policy_id", item.get("id", "")), item.get("data", {}), "Finance payroll policy updated.")
    return {"item": item, "dashboard": _payroll_policy_dashboard()}

def _payroll_period_locked(period: str) -> dict[str, Any] | None:
    normalized = period.strip().lower()
    for run in _items("payroll_runs", 1000):
        data = run.get("data", {})
        if str(data.get("period", "")).strip().lower() != normalized:
            continue
        status = data.get("approval_status") or run.get("status") or data.get("status")
        if status in PAYROLL_LOCKED_STATUSES or run.get("status") in PAYROLL_LOCKED_STATUSES:
            return run
    return None

def _find_payroll_adjustment(adjustment_id: str):
    normalized = adjustment_id.strip().lower()
    for item in _items("payroll_adjustments", 1000):
        data = item.get("data", {})
        if item.get("id", "").lower() == normalized or str(data.get("adjustment_id", "")).strip().lower() == normalized:
            return item
    return None

def _adjustment_duplicate_key(employee_code: str, payroll_month: str, adjustment_type: str, amount: float, direction: str):
    bits = [
        employee_code.strip().lower(),
        payroll_month.strip().lower(),
        adjustment_type.strip().lower(),
        direction.strip().lower(),
        f"{amount:.2f}",
    ]
    return hashlib.sha256("|".join(bits).encode()).hexdigest()

def _adjustment_dashboard():
    policy = _active_payroll_policy()
    rows = _items("payroll_adjustments", 1000)
    runs = _items("payroll_runs", 250)
    pending = [item for item in rows if (item.get("data", {}).get("approval_status") or item.get("status")) in {"Pending Approval", "Pending", "Draft", "Open"}]
    approved = [item for item in rows if (item.get("data", {}).get("approval_status") or item.get("status")) == "Approved"]
    rejected = [item for item in rows if (item.get("data", {}).get("approval_status") or item.get("status")) == "Rejected"]
    reversed_rows = [item for item in rows if (item.get("data", {}).get("approval_status") or item.get("status")) == "Reversed"]
    additions = sum(_money(item.get("data", {}).get("amount")) for item in approved if item.get("data", {}).get("addition_or_deduction") == "Addition")
    deductions = sum(_money(item.get("data", {}).get("amount")) for item in approved if item.get("data", {}).get("addition_or_deduction") == "Deduction")
    return {
        "stats": {
            "adjustments": len(rows),
            "pending": len(pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "reversed": len(reversed_rows),
            "approved_additions": round(additions, 2),
            "approved_deductions": round(deductions, 2),
            "net_adjustment": round(additions - deductions, 2),
            "payroll_runs": len(runs),
        },
        "limit": _payroll_adjustment_limit(policy),
        "policy": policy.get("data", {}),
        "pending": pending[:100],
        "recent": rows[:100],
        "payroll_runs": runs[:50],
        "allowed_types": _payroll_policy_categories(policy),
        "allowed_directions": ["Addition", "Deduction"],
    }

def _create_payroll_adjustment(payload: PayrollAdjustmentRequest, actor: str):
    employee_code = payload.employee_code.strip()
    payroll_month = payload.payroll_month.strip()
    adjustment_type = payload.adjustment_type.strip()
    direction = payload.addition_or_deduction.strip().title()
    reason = payload.reason.strip()
    policy_reference = payload.policy_reference.strip()
    amount = round(float(payload.amount), 2)
    policy = _active_payroll_policy()
    allowed_categories = set(_payroll_policy_categories(policy))
    adjustment_limit = _role_adjustment_limit(policy, actor)
    if not employee_code or not payroll_month:
        raise HTTPException(status_code=422, detail="employee_code and payroll_month are required.")
    if adjustment_type not in allowed_categories:
        raise HTTPException(status_code=422, detail=f"adjustment_type must be one of: {', '.join(sorted(allowed_categories))}")
    if direction not in {"Addition", "Deduction"}:
        raise HTTPException(status_code=422, detail="addition_or_deduction must be Addition or Deduction.")
    if amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be greater than zero.")
    if amount > adjustment_limit:
        raise HTTPException(status_code=422, detail=f"amount exceeds configured adjustment limit {adjustment_limit:.2f}.")
    if len(reason) < 8:
        raise HTTPException(status_code=422, detail="reason must explain the adjustment.")
    if len(policy_reference) < 3:
        raise HTTPException(status_code=422, detail="policy_reference is required for payroll audit.")
    locked = _payroll_period_locked(payroll_month)
    if locked:
        raise HTTPException(status_code=409, detail=f"Payroll period {payroll_month} is locked or approved. Use reversal/supplementary process.")
    _enforce_retroactive_adjustment_rule(policy, payroll_month)
    duplicate_key = _adjustment_duplicate_key(employee_code, payroll_month, adjustment_type, amount, direction)
    for item in _items("payroll_adjustments", 1000):
        data = item.get("data", {})
        if data.get("duplicate_key") == duplicate_key and (data.get("approval_status") or item.get("status")) not in {"Rejected", "Reversed", "Cancelled"}:
            raise HTTPException(status_code=409, detail="Duplicate active adjustment found for employee, month, type, direction, and amount.")
    now = _now_iso()
    item = storage.create_record("payroll_adjustments", {
        "adjustment_id": _new_ref("PADJ"),
        "employee_code": employee_code,
        "payroll_month": payroll_month,
        "adjustment_type": adjustment_type,
        "addition_or_deduction": direction,
        "amount": f"{amount:.2f}",
        "calculation_method": payload.calculation_method.strip() or "Manual",
        "quantity": f"{payload.quantity:.2f}" if payload.quantity is not None else "1.00",
        "rate": f"{payload.rate:.2f}" if payload.rate is not None else f"{amount:.2f}",
        "reason": reason,
        "policy_reference": policy_reference,
        "supporting_attachment": _clean_text(payload.supporting_attachment),
        "requested_by": actor,
        "approval_status": "Pending Approval",
        "approved_by": "",
        "rejected_by": "",
        "approval_remarks": "",
        "payroll_inclusion_status": "Pending Approval",
        "limit_check": f"within_role_limit:{adjustment_limit:.2f}",
        "duplicate_key": duplicate_key,
        "reversal_of": "",
        "created_time": now,
        "updated_time": now,
        "status": "Pending Approval",
    })
    _write_audit(actor, "create_payroll_adjustment", "payroll_adjustments", item.get("data", {}).get("adjustment_id", item.get("id", "")), item.get("data", {}), reason)
    _notify_employee(employee_code, "salary_adjustment_added", "Salary adjustment submitted", f"{adjustment_type} {direction.lower()} of {amount:.2f} is pending finance approval.", employee_code)
    return {"item": item, "dashboard": _adjustment_dashboard()}

def _decide_payroll_adjustment(payload: PayrollAdjustmentDecisionRequest, actor: str):
    item = _find_payroll_adjustment(payload.adjustment_id)
    if not item:
        raise HTTPException(status_code=404, detail="Payroll adjustment not found.")
    data = item.get("data", {})
    decision = payload.decision.strip().title()
    remarks = (payload.remarks or "").strip()
    current_status = data.get("approval_status") or item.get("status")
    policy = _active_payroll_policy()
    if current_status in {"Reversed", "Cancelled"}:
        raise HTTPException(status_code=409, detail=f"Adjustment is already {current_status}.")
    if _payroll_period_locked(data.get("payroll_month", "")) and decision != "Reversed":
        raise HTTPException(status_code=409, detail="Payroll period is locked. Use reversal for corrections.")
    if decision not in {"Approved", "Rejected", "Reversed"}:
        raise HTTPException(status_code=422, detail="decision must be Approved, Rejected, or Reversed.")
    update_payload = {
        "approval_status": decision,
        "approval_remarks": remarks or decision,
        "updated_time": _now_iso(),
        "status": decision,
    }
    if decision == "Approved":
        if current_status == "Approved":
            raise HTTPException(status_code=409, detail="Adjustment is already approved.")
        update_payload["approved_by"] = actor
        update_payload["payroll_inclusion_status"] = "Included In Next Payroll"
        notification_type = "salary_adjustment_approved"
    elif decision == "Rejected":
        update_payload["rejected_by"] = actor
        update_payload["payroll_inclusion_status"] = "Rejected"
        notification_type = "salary_adjustment_rejected"
    else:
        if current_status != "Approved":
            raise HTTPException(status_code=409, detail="Only approved adjustments can be reversed.")
        if _payroll_period_locked(data.get("payroll_month", "")) and not _bool_setting(policy.get("data", {}).get("allow_reversal_after_lock"), True):
            raise HTTPException(status_code=409, detail="Payroll policy does not allow reversal after payroll lock.")
        reversed_direction = "Deduction" if data.get("addition_or_deduction") == "Addition" else "Addition"
        reversal = storage.create_record("payroll_adjustments", {
            "adjustment_id": _new_ref("PADJ"),
            "employee_code": data.get("employee_code", ""),
            "payroll_month": data.get("payroll_month", ""),
            "adjustment_type": "Reversal",
            "addition_or_deduction": reversed_direction,
            "amount": data.get("amount", "0"),
            "calculation_method": "Reversal",
            "quantity": data.get("quantity", "1"),
            "rate": data.get("rate", data.get("amount", "0")),
            "reason": f"Reversal of {data.get('adjustment_id', item.get('id', ''))}. {remarks}",
            "policy_reference": data.get("policy_reference", ""),
            "supporting_attachment": data.get("supporting_attachment", ""),
            "requested_by": actor,
            "approval_status": "Approved",
            "approved_by": actor,
            "rejected_by": "",
            "approval_remarks": remarks or "Reversal approved",
            "payroll_inclusion_status": "Included In Next Payroll",
            "limit_check": data.get("limit_check", ""),
            "duplicate_key": _adjustment_duplicate_key(data.get("employee_code", ""), data.get("payroll_month", ""), "Reversal", _money(data.get("amount")), reversed_direction),
            "reversal_of": data.get("adjustment_id", item.get("id", "")),
            "created_time": _now_iso(),
            "updated_time": _now_iso(),
            "status": "Approved",
        })
        update_payload["payroll_inclusion_status"] = "Reversed"
        update_payload["reversal_of"] = reversal.get("data", {}).get("adjustment_id", reversal.get("id", ""))
        notification_type = "salary_adjustment_reversed"
    updated = storage.update_record("payroll_adjustments", item.get("id", ""), update_payload)
    storage.create_record("payroll_approvals", {
        "approval_id": _new_ref("PAPP"),
        "payroll_run": data.get("payroll_month", ""),
        "approver": actor,
        "decision": decision,
        "remarks": remarks,
        "decided_at": _now_iso(),
        "status": decision,
    })
    _write_audit(actor, f"{decision.lower()}_payroll_adjustment", "payroll_adjustments", data.get("adjustment_id", item.get("id", "")), updated.get("data", {}), remarks or decision)
    _notify_employee(data.get("employee_code", ""), notification_type, f"Salary adjustment {decision.lower()}", remarks or f"Your {data.get('adjustment_type', 'payroll adjustment')} was {decision.lower()}.", data.get("employee_code", ""))
    return {"item": updated, "dashboard": _adjustment_dashboard()}

def _decide_payroll_run(payload: PayrollRunDecisionRequest, actor: str):
    normalized = payload.run_no.strip().lower()
    run = next(
        (
            item for item in _items("payroll_runs", 1000)
            if item.get("id", "").lower() == normalized or item.get("data", {}).get("run_no", "").strip().lower() == normalized
        ),
        None,
    )
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")
    decision = payload.decision.strip().title()
    if decision not in {"Approved", "Locked", "Payment Processing", "Paid", "Cancelled", "Reversed"}:
        raise HTTPException(status_code=422, detail="decision must be Approved, Locked, Payment Processing, Paid, Cancelled, or Reversed.")
    policy = _active_payroll_policy()
    stored_decision = "Locked" if decision == "Approved" and _bool_setting(policy.get("data", {}).get("lock_after_approval"), True) else decision
    updated = storage.update_record("payroll_runs", run.get("id", ""), {
        "approval_status": stored_decision,
        "status": stored_decision,
    })
    storage.create_record("payroll_approvals", {
        "approval_id": _new_ref("PAPP"),
        "payroll_run": run.get("data", {}).get("run_no", run.get("id", "")),
        "approver": actor,
        "decision": stored_decision,
        "remarks": payload.remarks or "",
        "decided_at": _now_iso(),
        "status": stored_decision,
    })
    _write_audit(actor, f"{stored_decision.lower().replace(' ', '_')}_payroll_run", "payroll_runs", run.get("data", {}).get("run_no", run.get("id", "")), updated.get("data", {}), payload.remarks or stored_decision)
    return {"item": updated, "dashboard": v1_finance_payroll_dashboard(actor)}

def _find_payroll_run(run_no: str):
    normalized = run_no.strip().lower()
    return next(
        (
            item for item in _items("payroll_runs", 1000)
            if item.get("id", "").lower() == normalized or str(item.get("data", {}).get("run_no", "")).strip().lower() == normalized
        ),
        None,
    )

def _find_payment_batch(batch_id: str):
    normalized = batch_id.strip().lower()
    return next(
        (
            item for item in _items("payment_batches", 1000)
            if item.get("id", "").lower() == normalized or str(item.get("data", {}).get("batch_id", "")).strip().lower() == normalized
        ),
        None,
    )

def _salary_slips_for_period(period: str, limit: int = 1000):
    normalized = period.strip().lower()
    return [
        item for item in _items("salary_slips", limit)
        if str(item.get("data", {}).get("period", "")).strip().lower() == normalized
    ]

def _update_salary_slips_for_period(period: str, status: str, payment_date: str | None = None):
    updated = []
    for slip in _salary_slips_for_period(period):
        payload = {"status": status}
        if payment_date is not None:
            payload["payment_date"] = payment_date
        updated.append(storage.update_record("salary_slips", slip.get("id", ""), payload))
    return updated

def _payment_dashboard():
    runs = _items("payroll_runs", 500)
    batches = _items("payment_batches", 500)
    slips = _items("salary_slips", 1000)
    active_batch_runs = {
        str(item.get("data", {}).get("payroll_run", "")).strip().lower()
        for item in batches
        if (item.get("data", {}).get("payment_status") or item.get("status")) not in PAYROLL_PAYMENT_FINAL_STATUSES
    }
    ready_runs = []
    for run in runs:
        data = run.get("data", {})
        run_no = str(data.get("run_no", run.get("id", ""))).strip()
        status = data.get("approval_status") or run.get("status") or data.get("status")
        if status in PAYROLL_PAYMENT_READY_STATUSES and run_no.lower() not in active_batch_runs:
            ready_runs.append(run)
    total_paid = sum(_money(item.get("data", {}).get("total_amount")) for item in batches if (item.get("data", {}).get("payment_status") or item.get("status")) == "Paid")
    total_processing = sum(_money(item.get("data", {}).get("total_amount")) for item in batches if (item.get("data", {}).get("payment_status") or item.get("status")) == "Payment Processing")
    return {
        "stats": {
            "payment_batches": len(batches),
            "ready_runs": len(ready_runs),
            "processing_batches": _status_count(batches, "Payment Processing"),
            "paid_batches": _status_count(batches, "Paid"),
            "cancelled_batches": _status_count(batches, "Cancelled", "Reversed"),
            "salary_slips": len(slips),
            "paid_slips": _status_count(slips, "Paid"),
            "processing_slips": _status_count(slips, "Payment Processing"),
            "total_paid": round(total_paid, 2),
            "total_processing": round(total_processing, 2),
        },
        "ready_runs": ready_runs[:100],
        "payment_batches": batches[:100],
        "salary_slips": slips[:100],
        "payment_methods": ["Bank Transfer", "NEFT", "RTGS", "IMPS", "UPI", "Cheque", "Cash"],
    }

def _create_payment_batch(payload: PaymentBatchRequest, actor: str):
    run = _find_payroll_run(payload.payroll_run)
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found.")
    run_data = run.get("data", {})
    run_no = str(run_data.get("run_no", run.get("id", ""))).strip()
    run_status = run_data.get("approval_status") or run.get("status") or run_data.get("status")
    if run_status not in PAYROLL_PAYMENT_READY_STATUSES:
        raise HTTPException(status_code=409, detail="Payroll run must be approved, locked, or in payment processing before payment batch creation.")
    for batch in _items("payment_batches", 1000):
        data = batch.get("data", {})
        same_run = str(data.get("payroll_run", "")).strip().lower() == run_no.lower()
        batch_status = data.get("payment_status") or batch.get("status")
        if same_run and batch_status not in PAYROLL_PAYMENT_FINAL_STATUSES:
            raise HTTPException(status_code=409, detail="An active payment batch already exists for this payroll run.")
    _parse_iso_date(payload.payment_date, "payment_date")
    method = payload.payment_method.strip() or "Bank Transfer"
    slips = _salary_slips_for_period(str(run_data.get("period", "")))
    slip_total = sum(_money(item.get("data", {}).get("net_pay")) for item in slips)
    total_amount = _money(run_data.get("net_pay")) or slip_total
    if total_amount <= 0:
        raise HTTPException(status_code=422, detail="Payroll run has no payable net amount.")
    batch_id = _new_ref("PBAT")
    bank_reference = (payload.bank_file_reference or "").strip() or f"BANKFILE-{batch_id}"
    batch = storage.create_record("payment_batches", {
        "batch_id": batch_id,
        "payroll_run": run_no,
        "payment_date": payload.payment_date,
        "payment_method": method,
        "total_amount": f"{total_amount:.2f}",
        "bank_file_reference": bank_reference,
        "payment_status": "Payment Processing",
        "status": "Payment Processing",
    })
    storage.update_record("payroll_runs", run.get("id", ""), {
        "approval_status": "Payment Processing",
        "status": "Payment Processing",
    })
    updated_slips = _update_salary_slips_for_period(str(run_data.get("period", "")), "Payment Processing", payload.payment_date) if payload.mark_salary_slips else []
    storage.create_record("payroll_approvals", {
        "approval_id": _new_ref("PAPP"),
        "payroll_run": run_no,
        "approver": actor,
        "decision": "Payment Processing",
        "remarks": f"Payment batch {batch_id} created with {method}.",
        "decided_at": _now_iso(),
        "status": "Payment Processing",
    })
    _write_audit(actor, "create_payment_batch", "payment_batches", batch_id, batch.get("data", {}), f"{len(updated_slips)} salary slips moved to payment processing.")
    return {"item": batch, "updated_salary_slips": len(updated_slips), "dashboard": _payment_dashboard()}

def _decide_payment_batch(payload: PaymentBatchDecisionRequest, actor: str):
    batch = _find_payment_batch(payload.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Payment batch not found.")
    data = batch.get("data", {})
    current_status = data.get("payment_status") or batch.get("status")
    decision = payload.decision.strip().title()
    if decision not in {"Payment Processing", "Paid", "Cancelled", "Reversed"}:
        raise HTTPException(status_code=422, detail="decision must be Payment Processing, Paid, Cancelled, or Reversed.")
    if current_status in {"Paid", "Cancelled", "Reversed"} and current_status != decision:
        raise HTTPException(status_code=409, detail=f"Payment batch is already {current_status}.")
    run = _find_payroll_run(str(data.get("payroll_run", "")))
    run_period = str(run.get("data", {}).get("period", "")) if run else ""
    payment_date = data.get("payment_date") or _today()
    if decision == "Paid":
        run_status = "Paid"
        slip_status = "Paid"
        slip_payment_date = payment_date
    elif decision == "Payment Processing":
        run_status = "Payment Processing"
        slip_status = "Payment Processing"
        slip_payment_date = payment_date
    elif decision == "Cancelled":
        run_status = "Locked"
        slip_status = "Draft"
        slip_payment_date = ""
    else:
        run_status = "Reversed"
        slip_status = "Reversed"
        slip_payment_date = ""
    updated_batch = storage.update_record("payment_batches", batch.get("id", ""), {
        "payment_status": decision,
        "status": decision,
    })
    if run:
        storage.update_record("payroll_runs", run.get("id", ""), {
            "approval_status": run_status,
            "status": run_status,
        })
    updated_slips = _update_salary_slips_for_period(run_period, slip_status, slip_payment_date) if run_period else []
    if decision == "Paid":
        for slip in updated_slips[:100]:
            slip_data = slip.get("data", {})
            _notify_employee(slip_data.get("employee_code", ""), "salary_paid", "Salary payment completed", f"Salary for {slip_data.get('period', run_period)} has been marked paid.", slip_data.get("employee_code", ""))
    storage.create_record("payroll_approvals", {
        "approval_id": _new_ref("PAPP"),
        "payroll_run": data.get("payroll_run", ""),
        "approver": actor,
        "decision": decision,
        "remarks": payload.remarks or decision,
        "decided_at": _now_iso(),
        "status": decision,
    })
    _write_audit(actor, f"{decision.lower().replace(' ', '_')}_payment_batch", "payment_batches", data.get("batch_id", batch.get("id", "")), updated_batch.get("data", {}), payload.remarks or decision)
    return {"item": updated_batch, "updated_salary_slips": len(updated_slips), "dashboard": _payment_dashboard()}

def _payment_batch_csv(batch_id: str):
    batch = _find_payment_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Payment batch not found.")
    data = batch.get("data", {})
    run = _find_payroll_run(str(data.get("payroll_run", "")))
    period = str(run.get("data", {}).get("period", "")) if run else ""
    slips = _salary_slips_for_period(period) if period else []
    rows = [["batch_id", "payroll_run", "employee_code", "period", "net_pay", "payment_date", "payment_status"]]
    for slip in slips:
        slip_data = slip.get("data", {})
        rows.append([
            data.get("batch_id", batch.get("id", "")),
            data.get("payroll_run", ""),
            slip_data.get("employee_code", ""),
            slip_data.get("period", ""),
            slip_data.get("net_pay", "0"),
            data.get("payment_date", ""),
            data.get("payment_status", batch.get("status", "")),
        ])
    def cell(value: Any):
        text = str(value).replace('"', '""')
        return f'"{text}"'
    csv_body = "\n".join(",".join(cell(value) for value in row) for row in rows)
    return Response(content=csv_body, media_type="text/csv", headers={"Content-Disposition": f"attachment; filename={data.get('batch_id', 'payment_batch')}.csv"})

def _payroll_calculation(payload: PayrollGenerateRequest, actor: str):
    start = _parse_iso_date(payload.start_date, "start_date")
    end = _parse_iso_date(payload.end_date, "end_date")
    if end < start:
        raise HTTPException(status_code=422, detail="end_date must be on or after start_date")
    total_days = max((end - start).days + 1, 1)
    payroll_policy = _active_payroll_policy()
    divisor, divisor_source = _payroll_divisor(payroll_policy, start, end, total_days)
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
            if data.get("employee_code", "").lower() != employee_code.lower() or _effective_leave_status(row) != "Approved":
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
        paid_days = min(float(divisor), present_days + paid_leave_days)
        daily_rate = monthly_gross / float(divisor or total_days)
        prorated_gross = round(monthly_gross * (paid_days / float(divisor or total_days)), 2)
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
                {"component_name": "Prorated Gross", "component_type": "Earning", "quantity": f"{paid_days:.2f}", "rate": f"{daily_rate:.2f}", "amount": f"{prorated_gross:.2f}", "formula": f"monthly_gross * paid_days / {divisor_source}:{divisor}", "source": "salary_assignment"},
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
            _notify_employee(employee_code, "salary_slip_generated", "Salary slip generated", f"{payload.period_name} draft net pay is {net_pay:.2f}.", employee_code)
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
        "policy": {
            "policy_id": payroll_policy.get("data", {}).get("policy_id", "DEFAULT-PAYROLL-POLICY"),
            "policy_name": payroll_policy.get("data", {}).get("policy_name", "Default Payroll Policy"),
            "proration_method": payroll_policy.get("data", {}).get("proration_method", "Calendar Day"),
            "divisor": divisor,
            "divisor_source": divisor_source,
        },
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

def _validate_hhmm(value: str, field: str) -> str:
    clean = value.strip()
    try:
        datetime.strptime(clean, "%H:%M")
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{field} must use HH:MM 24-hour format.")
    return clean

def _optional_hhmm(value: str | None, fallback: str, field: str) -> str:
    clean = _clean_text(value)
    return _validate_hhmm(clean, field) if clean else fallback

def _active_shift_for_employee(employee_code: str, target_date: str | None = None):
    target = target_date or _today()
    rosters = [
        item for item in _records_for_employee("shift_rosters", employee_code, 500)
        if item.get("data", {}).get("roster_date") == target and (item.get("data", {}).get("status") or item.get("status")) == "Active"
    ]
    roster = rosters[0] if rosters else None
    shift_name = roster.get("data", {}).get("shift") if roster else ""
    if not shift_name:
        assignments = [
            item for item in _records_for_employee("employee_shift_assignments", employee_code, 500)
            if (item.get("data", {}).get("status") or item.get("status")) == "Active"
            and (not item.get("data", {}).get("effective_start_date") or item.get("data", {}).get("effective_start_date") <= target)
            and (not item.get("data", {}).get("effective_end_date") or item.get("data", {}).get("effective_end_date") >= target)
        ]
        assignment = assignments[0] if assignments else None
        shift_name = assignment.get("data", {}).get("shift") if assignment else ""
    shift = next(
        (
            item for item in _items("shifts", 500)
            if item.get("data", {}).get("name", "").strip().lower() == (shift_name or "").strip().lower()
            and (item.get("data", {}).get("status") or item.get("status")) == "Active"
        ),
        None,
    )
    return {"roster": roster, "shift": shift, "shift_name": shift_name or "General"}

def _hr_settings_dashboard():
    policies = _items("attendance_policies", 100)
    shifts = _items("shifts", 200)
    shift_assignments = _items("employee_shift_assignments", 500)
    rosters = _items("shift_rosters", 500)
    active_policy = _attendance_policy()
    active_shifts = [item for item in shifts if item.get("status") == "Active"]
    today = _today()
    today_rosters = [item for item in rosters if item.get("data", {}).get("roster_date") == today]
    night_shifts = [item for item in shifts if item.get("data", {}).get("cross_midnight") == "Yes"]
    return {
        "active_policy": active_policy,
        "policies": policies,
        "shifts": shifts,
        "shift_assignments": shift_assignments,
        "shift_rosters": rosters,
        "stats": {
            "policies": len(policies),
            "active_policies": len([item for item in policies if item.get("status") == "Active"]),
            "shifts": len(shifts),
            "active_shifts": len(active_shifts),
            "assignments": len(shift_assignments),
            "rosters": len(rosters),
            "today_rosters": len(today_rosters),
            "night_shifts": len(night_shifts),
            "late_after_time": active_policy.get("late_after_time", "09:15"),
            "tracking_interval_minutes": active_policy.get("tracking_interval_minutes", "5"),
        },
        "rules": {
            "late_mark_source": "HR attendance policy",
            "active_late_after_time": _late_after_time(active_policy),
            "background_location_required": active_policy.get("background_location_required", "Yes"),
            "employee_app_effect": "Employee Day In uses active roster/shift first, then HR attendance policy fallback.",
        },
    }

def _attendance_snapshot(employee_code: str, policy: dict[str, str] | None = None):
    policy = policy or _attendance_policy()
    today = _today()
    shift_context = _active_shift_for_employee(employee_code, today)
    shift_data = shift_context.get("shift", {}).get("data", {}) if shift_context.get("shift") else {}
    late_after = shift_data.get("start_time") or _late_after_time(policy)
    if shift_data.get("late_mark_after_minutes"):
        try:
            base = datetime.strptime(shift_data.get("start_time", late_after), "%H:%M")
            late_after = (base + timedelta(minutes=int(float(shift_data.get("late_mark_after_minutes", "0"))))).strftime("%H:%M")
        except Exception:
            late_after = _late_after_time(policy)
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
        "assigned_shift": shift_context.get("shift_name", "General"),
        "shift_start_time": shift_data.get("start_time", ""),
        "shift_end_time": shift_data.get("end_time", ""),
        "cross_midnight": shift_data.get("cross_midnight", "No"),
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
    salary = _salary_slip_rows(employee_code, 12)
    notifications = _employee_notifications(employee_code, email, 100)
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
            "latest": salary[0] if salary else None,
            "count": len(salary),
        },
        "notifications": {
            "unread": len([row for row in notifications if row.get("data", {}).get("read_status", "Unread") == "Unread"]),
            "latest": notifications[0].get("data", {}) if notifications else None,
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
    _notify_employee(employee_code, "attendance_correction_submitted", "Attendance correction submitted", f"{payload.attendance_date.strip()} correction request is pending HR review.", email)
    return {"item": item}

@app.get("/api/v1/employee/leave/balance")
def v1_employee_leave_balance(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    balances = [item for item in _leave_balance_rows() if str(item.get("employee_code", "")).lower() == employee_code.lower()]
    return {
        "balances": balances,
        "allocations": _records_for_employee("leave_allocations", employee_code, 100),
        "applications": [_leave_application_summary(item) for item in _records_for_employee("leave_applications", employee_code, 100)],
        "legacy_requests": _records_for_employee("leave_requests", employee_code, 100),
    }

@app.post("/api/v1/employee/leave/apply")
def v1_employee_leave_apply(payload: LeaveApplicationRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    item = _create_leave_application(payload, email, employee_code)
    return {"item": item, "summary": _leave_application_summary(item)}

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
def v1_hr_overview(email: str = Depends(_verify)):
    _require_permission(email, "hr:read")
    return _hr_overview()

@app.get("/api/v1/hr/employees-dashboard")
def v1_hr_employees_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "hr:read")
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
def v1_hr_employee_detail(employee_code: str, email: str = Depends(_verify)):
    _require_permission(email, "hr:read")
    bundle = _employee_bundle(employee_code)
    if not bundle["employee"]:
        raise HTTPException(status_code=404, detail="Employee not found")
    return bundle

@app.post("/api/v1/hr/employees/onboard")
def v1_hr_employee_onboard(payload: HrEmployeeOnboardingRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    return _onboard_employee(payload, email)

@app.post("/api/v1/hr/employees/lifecycle")
def v1_hr_employee_lifecycle(payload: HrLifecycleEventRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    item = _create_lifecycle_event(payload, email)
    return {"item": item, "profile": _employee_bundle(payload.employee_code)}

@app.get("/api/v1/hr/leave-dashboard")
def v1_hr_leave_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "hr:leave")
    return _leave_dashboard()

@app.post("/api/v1/hr/leave/applications")
def v1_hr_leave_application(payload: LeaveApplicationRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:leave")
    item = _create_leave_application(payload, email, payload.employee_code)
    return {"item": item, "summary": _leave_application_summary(item), "dashboard": _leave_dashboard()}

@app.post("/api/v1/hr/leave/decision")
def v1_hr_leave_decision(payload: LeaveDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:leave")
    decision = payload.decision.strip().title()
    if decision not in {"Approved", "Rejected", "Cancelled"}:
        raise HTTPException(status_code=422, detail="decision must be Approved, Rejected, or Cancelled.")
    applications = _items("leave_applications", 1000)
    application = next((item for item in applications if item.get("data", {}).get("application_id") == payload.application_id or item.get("id") == payload.application_id), None)
    if not application:
        raise HTTPException(status_code=404, detail="Leave application not found.")
    app_id = application.get("data", {}).get("application_id", payload.application_id)
    approval = storage.create_record("leave_approvals", {
        "approval_id": _new_ref("LAP"),
        "application_id": app_id,
        "approver": _clean_text(payload.approver) or email,
        "decision": decision,
        "remarks": _clean_text(payload.remarks),
        "decided_at": _now_iso(),
        "status": decision,
    })
    update_payload = {
        "approval_status": decision,
        "status": decision,
    }
    if payload.payroll_impact:
        update_payload["payroll_impact"] = payload.payroll_impact.strip()
    updated = storage.update_record("leave_applications", application.get("id", ""), update_payload)
    _write_audit(email, "decide_leave", "leave_applications", app_id, {"decision": decision, "remarks": payload.remarks or "", "updated": updated.get("data", {})}, "HR leave decision")
    return {"approval": approval, "application": _leave_application_summary(updated), "dashboard": _leave_dashboard()}

@app.post("/api/v1/hr/leave/allocations")
def v1_hr_leave_allocation(payload: LeaveAllocationRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:leave")
    if not payload.employee_code.strip() or not payload.leave_type.strip() or payload.allocated_days < 0:
        raise HTTPException(status_code=422, detail="employee_code, leave_type, and non-negative allocated_days are required.")
    item = storage.create_record("leave_allocations", {
        "allocation_id": _new_ref("LALLOC"),
        "employee_code": payload.employee_code.strip(),
        "leave_type": payload.leave_type.strip(),
        "period": payload.period.strip(),
        "allocated_days": f"{payload.allocated_days:.2f}",
        "used_days": "0.00",
        "available_days": f"{payload.allocated_days:.2f}",
        "expiry_date": _clean_text(payload.expiry_date),
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "allocate_leave", "leave_allocations", item.get("id", ""), item.get("data", {}), "HR leave allocation")
    return {"item": item, "dashboard": _leave_dashboard()}

@app.post("/api/v1/hr/holidays")
def v1_hr_holiday(payload: HolidayRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:leave")
    _parse_iso_date(payload.holiday_date, "holiday_date")
    item = storage.create_record("holidays", {
        "holiday_id": _new_ref("HOL"),
        "calendar_id": payload.calendar_id.strip(),
        "holiday_name": payload.holiday_name.strip(),
        "holiday_date": payload.holiday_date.strip(),
        "holiday_type": payload.holiday_type.strip(),
        "paid_status": payload.paid_status.strip(),
        "optional_or_mandatory": payload.optional_or_mandatory.strip(),
        "payroll_impact": payload.payroll_impact.strip(),
        "notes": _clean_text(payload.notes),
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "create_holiday", "holidays", item.get("id", ""), item.get("data", {}), "HR holiday creation")
    return {"item": item, "dashboard": _leave_dashboard()}

@app.get("/api/v1/hr/settings-dashboard")
def v1_hr_settings_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "hr:read")
    return _hr_settings_dashboard()

@app.post("/api/v1/hr/attendance-policy")
def v1_hr_attendance_policy(payload: HrAttendancePolicyRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    late_after = _validate_hhmm(payload.late_after_time, "late_after_time")
    if payload.grace_minutes < 0 or payload.grace_minutes > 120:
        raise HTTPException(status_code=422, detail="grace_minutes must be between 0 and 120.")
    if payload.tracking_interval_minutes < 1 or payload.tracking_interval_minutes > 120:
        raise HTTPException(status_code=422, detail="tracking_interval_minutes must be between 1 and 120.")
    for item in _items("attendance_policies", 100):
        if item.get("status") == "Active":
            try:
                storage.update_record("attendance_policies", item.get("id", ""), {"status": "Inactive"})
            except Exception:
                pass
    item = storage.create_record("attendance_policies", {
        "policy_name": payload.policy_name.strip() or "Default Attendance Policy",
        "late_after_time": late_after,
        "grace_minutes": str(payload.grace_minutes),
        "tracking_interval_minutes": str(payload.tracking_interval_minutes),
        "background_location_required": "Yes" if payload.background_location_required else "No",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "set_attendance_policy", "attendance_policies", item.get("id", ""), item.get("data", {}), "HR updated attendance policy used by employee Day In.")
    return {"item": item, "dashboard": _hr_settings_dashboard()}

@app.post("/api/v1/hr/shifts")
def v1_hr_shift(payload: HrShiftRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    start_time = _validate_hhmm(payload.start_time, "start_time")
    end_time = _validate_hhmm(payload.end_time, "end_time")
    if not payload.name.strip():
        raise HTTPException(status_code=422, detail="name is required.")
    if payload.minimum_half_day_minutes < 0 or payload.minimum_full_day_minutes <= 0 or payload.minimum_half_day_minutes > payload.minimum_full_day_minutes:
        raise HTTPException(status_code=422, detail="minimum day minute rules are invalid.")
    if payload.grace_minutes < 0 or payload.grace_minutes > 180:
        raise HTTPException(status_code=422, detail="grace_minutes must be between 0 and 180.")
    item = storage.create_record("shifts", {
        "name": payload.name.strip(),
        "shift_type": payload.shift_type.strip() or "Fixed",
        "start_time": start_time,
        "end_time": end_time,
        "cross_midnight": "Yes" if payload.cross_midnight else "No",
        "day_in_open_time": _optional_hhmm(payload.day_in_open_time, start_time, "day_in_open_time"),
        "day_in_close_time": _optional_hhmm(payload.day_in_close_time, start_time, "day_in_close_time"),
        "day_out_open_time": _optional_hhmm(payload.day_out_open_time, end_time, "day_out_open_time"),
        "day_out_close_time": _optional_hhmm(payload.day_out_close_time, end_time, "day_out_close_time"),
        "grace_minutes": str(payload.grace_minutes),
        "minimum_full_day_minutes": str(payload.minimum_full_day_minutes),
        "minimum_half_day_minutes": str(payload.minimum_half_day_minutes),
        "break_minutes": str(max(payload.break_minutes, 0)),
        "auto_break_deduction": "Yes" if payload.auto_break_deduction else "No",
        "overtime_eligible": "Yes" if payload.overtime_eligible else "No",
        "overtime_approval_required": "Yes" if payload.overtime_approval_required else "No",
        "early_exit_grace_minutes": str(max(payload.early_exit_grace_minutes, 0)),
        "late_mark_after_minutes": str(max(payload.late_mark_after_minutes, 0)),
        "maximum_late_marks": str(max(payload.maximum_late_marks, 0)),
        "weekly_working_days": payload.weekly_working_days.strip(),
        "weekly_offs": payload.weekly_offs.strip(),
        "applicable_locations": _clean_text(payload.applicable_locations),
        "applicable_departments": _clean_text(payload.applicable_departments),
        "applicable_employees": _clean_text(payload.applicable_employees),
        "effective_start_date": _clean_text(payload.effective_start_date),
        "effective_end_date": _clean_text(payload.effective_end_date),
        "department": payload.department.strip() or "All",
        "supervisor": _clean_text(payload.supervisor),
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "create_shift", "shifts", item.get("id", ""), item.get("data", {}), "HR shift created.")
    return {"item": item, "dashboard": _hr_settings_dashboard()}

@app.post("/api/v1/hr/shift-assignments")
def v1_hr_shift_assignment(payload: HrShiftAssignmentRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    if not payload.employee_code.strip() or not payload.shift.strip():
        raise HTTPException(status_code=422, detail="employee_code and shift are required.")
    shift = next((item for item in _items("shifts", 500) if item.get("data", {}).get("name", "").lower() == payload.shift.strip().lower()), None)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found.")
    item = storage.create_record("employee_shift_assignments", {
        "assignment_id": _new_ref("SASSIGN"),
        "employee_code": payload.employee_code.strip(),
        "shift": payload.shift.strip(),
        "shift_type": payload.shift_type.strip() or shift.get("data", {}).get("shift_type", "Fixed"),
        "effective_start_date": _clean_text(payload.effective_start_date),
        "effective_end_date": _clean_text(payload.effective_end_date),
        "assignment_reason": _clean_text(payload.assignment_reason),
        "approved_by": email,
        "approval_status": payload.approval_status.strip() or "Approved",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "assign_employee_shift", "employee_shift_assignments", item.get("id", ""), item.get("data", {}), "HR assigned employee shift.")
    _notify_employee(payload.employee_code.strip(), "shift_changed", "Shift assignment updated", f"Your shift is now {payload.shift.strip()}.", payload.employee_code.strip())
    return {"item": item, "dashboard": _hr_settings_dashboard()}

@app.post("/api/v1/hr/shift-rosters")
def v1_hr_shift_roster(payload: HrShiftRosterRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    if not payload.employee_code.strip() or not payload.shift.strip() or not payload.roster_date.strip():
        raise HTTPException(status_code=422, detail="employee_code, shift, and roster_date are required.")
    _parse_iso_date(payload.roster_date, "roster_date")
    shift = next((item for item in _items("shifts", 500) if item.get("data", {}).get("name", "").lower() == payload.shift.strip().lower()), None)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found.")
    shift_data = shift.get("data", {})
    planned_start = _optional_hhmm(payload.planned_start_time, shift_data.get("start_time", "09:00"), "planned_start_time")
    planned_end = _optional_hhmm(payload.planned_end_time, shift_data.get("end_time", "18:00"), "planned_end_time")
    duplicate = next(
        (
            item for item in _records_for_employee("shift_rosters", payload.employee_code.strip(), 500)
            if item.get("data", {}).get("roster_date") == payload.roster_date.strip()
            and (item.get("data", {}).get("status") or item.get("status")) == "Active"
        ),
        None,
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="Active roster already exists for this employee and date.")
    item = storage.create_record("shift_rosters", {
        "roster_id": _new_ref("ROST"),
        "employee_code": payload.employee_code.strip(),
        "shift": payload.shift.strip(),
        "roster_date": payload.roster_date.strip(),
        "location_id": _clean_text(payload.location_id),
        "planned_start_time": planned_start,
        "planned_end_time": planned_end,
        "roster_type": payload.roster_type.strip() or "Regular",
        "published_status": payload.published_status.strip() or "Published",
        "approval_status": payload.approval_status.strip() or "Approved",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "publish_shift_roster", "shift_rosters", item.get("id", ""), item.get("data", {}), "HR published employee shift roster.")
    _notify_employee(payload.employee_code.strip(), "shift_changed", "Shift roster published", f"{payload.roster_date}: {payload.shift.strip()} {planned_start}-{planned_end}.", payload.employee_code.strip())
    return {"item": item, "dashboard": _hr_settings_dashboard()}

@app.get("/api/v1/hr/attendance-dashboard")
def v1_hr_attendance_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "hr:attendance")
    return _attendance_dashboard()

@app.get("/api/v1/reports/dashboard")
def v1_reports_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "reports:read")
    return _reports_dashboard()

@app.get("/api/v1/admin/security-dashboard")
def v1_admin_security_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "admin:security")
    return _security_dashboard()

@app.get("/api/v1/admin/audit-dashboard")
def v1_admin_audit_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "admin:audit")
    return _audit_dashboard()

@app.get("/api/v1/admin/audit/export")
def v1_admin_audit_export(email: str = Depends(_verify)):
    _require_permission(email, "admin:audit")
    csv = _csv_from_rows(_audit_dashboard()["events"], [
        "audit_id", "actor", "action", "entity_type", "entity_id", "reason", "status", "ip_address", "device_info", "approval_reference",
    ])
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-logs.csv"},
    )

@app.get("/api/v1/admin/operations-dashboard")
def v1_admin_operations_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "admin:ops")
    return _operations_dashboard()

@app.post("/api/v1/admin/operations/run")
def v1_admin_run_operations_job(payload: AdminJobRunRequest, email: str = Depends(_verify)):
    _require_permission(email, "admin:ops")
    return _run_operations_job(payload.job_type, email, payload.dry_run)

@app.post("/api/v1/admin/users")
def v1_admin_create_user(payload: AdminUserCreateRequest, email: str = Depends(_verify)):
    _require_permission(email, "admin:security")
    role = payload.role.strip().upper()
    if role not in ROLE_PERMISSIONS:
        raise HTTPException(status_code=422, detail=f"role must be one of: {', '.join(sorted(ROLE_PERMISSIONS))}")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="password must be at least 8 characters.")
    if storage.get_user_by_email(payload.email):
        raise HTTPException(status_code=409, detail="User already exists.")
    item = storage.create_user({
        "email": payload.email,
        "password_hash": _hash_password(payload.password),
        "full_name": payload.full_name.strip(),
        "role": role,
        "department_id": _clean_text(payload.department_id),
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "create_app_user", "app_users", item.get("id", item.get("email", "")), {"email": item.get("email"), "role": item.get("role"), "status": item.get("status")}, "Admin created RBAC user.")
    return {"item": item, "dashboard": _security_dashboard()}

@app.get("/api/v1/reports/{report_id}")
def v1_report_detail(report_id: str, email: str = Depends(_verify)):
    _require_permission(email, "reports:read")
    rows = _report_rows(report_id)
    catalog = {item["id"]: item for item in _report_catalog()}
    meta = catalog.get(report_id, {"id": report_id, "title": report_id.replace("_", " ").title(), "domain": "Report", "description": ""})
    return {**meta, "row_count": len(rows), "rows": rows[:500]}

@app.get("/api/v1/reports/{report_id}/export")
def v1_report_export(report_id: str, email: str = Depends(_verify)):
    _require_permission(email, "reports:read")
    rows = _report_rows(report_id)
    csv = _csv_from_rows(rows)
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={report_id}.csv"},
    )

@app.get("/api/v1/hr/attendance/export")
def v1_hr_attendance_export(email: str = Depends(_verify)):
    _require_permission(email, "hr:attendance")
    csv = _attendance_csv(_attendance_dashboard()["records"])
    return Response(
        content=csv,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=attendance-report.csv"},
    )

@app.post("/api/v1/hr/attendance/decision")
def v1_hr_attendance_decision(payload: AttendanceDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:attendance")
    decision = payload.decision.strip().title()
    if decision not in {"Approved", "Rejected", "Pending Approval"}:
        raise HTTPException(status_code=422, detail="decision must be Approved, Rejected, or Pending Approval.")
    record = _find_record("attendance_records", payload.attendance_record_id, "attendance_record_id")
    if not record:
        raise HTTPException(status_code=404, detail="Attendance record not found.")
    record_no = record.get("data", {}).get("attendance_record_id") or record.get("id", "")
    approval = storage.create_record("attendance_approvals", {
        "approval_id": _new_ref("AAPR"),
        "attendance_record_id": record_no,
        "employee_code": record.get("data", {}).get("employee_code", ""),
        "approval_type": payload.approval_type.strip() or "HR Review",
        "approver": email,
        "decision": decision,
        "comments": _clean_text(payload.comments),
        "decided_at": _now_iso(),
        "status": decision,
    })
    update_payload = {
        "approval_status": decision,
        "hr_remarks": _clean_text(payload.comments),
        "status": decision,
    }
    if decision == "Rejected":
        update_payload["attendance_status"] = "Rejected"
    updated = storage.update_record("attendance_records", record.get("id", ""), update_payload)
    _write_audit(email, "attendance_decision", "attendance_records", record_no, {"decision": decision, "comments": payload.comments or ""}, "HR attendance decision")
    return {"approval": approval, "attendance": _attendance_row_summary(updated), "dashboard": _attendance_dashboard()}

@app.post("/api/v1/hr/attendance/correction-decision")
def v1_hr_attendance_correction_decision(payload: AttendanceCorrectionDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:attendance")
    decision = payload.decision.strip().title()
    if decision not in {"Approved", "Rejected"}:
        raise HTTPException(status_code=422, detail="decision must be Approved or Rejected.")
    request = _find_record("attendance_correction_requests", payload.request_id, "request_id")
    if not request:
        raise HTTPException(status_code=404, detail="Attendance correction request not found.")
    request_no = request.get("data", {}).get("request_id") or request.get("id", "")
    updated_request = storage.update_record("attendance_correction_requests", request.get("id", ""), {
        "hr_approval": decision,
        "final_status": decision,
        "status": decision,
    })
    corrected = None
    if decision == "Approved" and payload.apply_to_attendance:
        corrected = _apply_attendance_correction(updated_request, email, payload.comments or "Approved attendance correction")
    approval = storage.create_record("attendance_approvals", {
        "approval_id": _new_ref("AAPR"),
        "attendance_record_id": corrected.get("data", {}).get("attendance_record_id", request_no) if corrected else request_no,
        "employee_code": request.get("data", {}).get("employee_code", ""),
        "approval_type": "Correction Request",
        "approver": email,
        "decision": decision,
        "comments": _clean_text(payload.comments),
        "decided_at": _now_iso(),
        "status": decision,
    })
    _write_audit(email, "attendance_correction_decision", "attendance_correction_requests", request_no, {"decision": decision, "comments": payload.comments or ""}, "HR attendance correction decision")
    return {"approval": approval, "request": updated_request, "corrected_attendance": corrected, "dashboard": _attendance_dashboard()}

@app.get("/api/v1/hr/geofence-dashboard")
def v1_hr_geofence_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "hr:read")
    overview = _hr_overview()
    work_locations = _items("work_locations", 200)
    geofences = _items("geofences", 200)
    assignments = _items("employee_location_assignments", 500)
    validation_results = _items("attendance_validation_results", 200)
    return {
        "stats": {
            "work_locations": overview["stats"]["work_locations"],
            "geofences": overview["stats"]["geofences"],
            "assignments": overview["stats"]["location_assignments"],
            "out_of_fence_attempts": overview["stats"]["out_of_fence_attempts"],
            "active_locations": len([item for item in work_locations if item.get("status") == "Active"]),
            "pending_approval": len([item for item in [*work_locations, *geofences] if item.get("data", {}).get("approval_status") == "Pending"]),
            "failed_validations": len([item for item in validation_results if item.get("status") == "Failed"]),
        },
        "validation_results": validation_results,
        "work_locations": work_locations,
        "geofences": geofences,
        "assignments": assignments,
    }

@app.post("/api/v1/hr/work-locations")
def v1_hr_create_work_location(payload: HrWorkLocationRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    _validate_lat_lon(payload.latitude, payload.longitude)
    _validate_geofence_numbers(payload.geofence_radius_meters, payload.allowed_gps_accuracy_meters)
    if not payload.location_name.strip() or not payload.full_address.strip():
        raise HTTPException(status_code=422, detail="location_name and full_address are required.")
    location_id = (payload.location_id or _new_ref("LOCN")).strip()
    if _records_by_field("work_locations", "location_id", location_id, 1):
        raise HTTPException(status_code=409, detail="location_id already exists.")
    item = storage.create_record("work_locations", {
        "location_id": location_id,
        "company": payload.company.strip(),
        "branch": payload.branch.strip(),
        "location_name": payload.location_name.strip(),
        "location_type": payload.location_type.strip(),
        "full_address": payload.full_address.strip(),
        "city": payload.city.strip(),
        "state": payload.state.strip(),
        "country": payload.country.strip(),
        "latitude": f"{payload.latitude:.8f}",
        "longitude": f"{payload.longitude:.8f}",
        "geofence_type": payload.geofence_type.strip(),
        "geofence_radius_meters": f"{payload.geofence_radius_meters:.2f}",
        "allowed_gps_accuracy_meters": f"{payload.allowed_gps_accuracy_meters:.2f}",
        "time_zone": payload.time_zone.strip(),
        "approval_status": payload.approval_status.strip(),
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "create_work_location", "work_locations", location_id, item.get("data", {}), "HR work location created.")
    return {"item": item, "dashboard": v1_hr_geofence_dashboard(email)}

@app.post("/api/v1/hr/geofences")
def v1_hr_create_geofence(payload: HrGeofenceRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    _validate_lat_lon(payload.center_latitude, payload.center_longitude)
    _validate_geofence_numbers(payload.radius_meters, payload.allowed_accuracy_meters)
    _validate_polygon_payload(payload.geofence_type, payload.polygon_coordinates)
    location = _active_record(_records_by_field("work_locations", "location_id", payload.location_id))
    if not location:
        raise HTTPException(status_code=404, detail="Work location not found.")
    geofence_id = (payload.geofence_id or _new_ref("GEO")).strip()
    if _records_by_field("geofences", "geofence_id", geofence_id, 1):
        raise HTTPException(status_code=409, detail="geofence_id already exists.")
    item = storage.create_record("geofences", {
        "geofence_id": geofence_id,
        "location_id": payload.location_id.strip(),
        "geofence_type": payload.geofence_type.strip(),
        "center_latitude": f"{payload.center_latitude:.8f}",
        "center_longitude": f"{payload.center_longitude:.8f}",
        "radius_meters": f"{payload.radius_meters:.2f}",
        "polygon_coordinates": payload.polygon_coordinates or "",
        "allowed_accuracy_meters": f"{payload.allowed_accuracy_meters:.2f}",
        "boundary_version": payload.boundary_version.strip() or "1",
        "effective_start_date": _clean_text(payload.effective_start_date),
        "effective_end_date": _clean_text(payload.effective_end_date),
        "approval_status": payload.approval_status.strip(),
        "status": payload.status.strip() or "Active",
    })
    version = storage.create_record("geofence_versions", {
        "version_id": _new_ref("GEOV"),
        "geofence_id": geofence_id,
        "boundary_version": payload.boundary_version.strip() or "1",
        "change_summary": "Initial geofence boundary created.",
        "changed_by": email,
        "approved_by": email if payload.approval_status.strip() == "Approved" else "",
        "effective_date": payload.effective_start_date or _today(),
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "create_geofence", "geofences", geofence_id, {"geofence": item.get("data", {}), "version": version.get("data", {})}, "HR geofence created.")
    return {"item": item, "version": version, "dashboard": v1_hr_geofence_dashboard(email)}

@app.post("/api/v1/hr/geofences/test")
def v1_hr_test_geofence(payload: HrGeofenceTestRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:read")
    result = _test_geofence(payload.location_id.strip(), payload.latitude, payload.longitude, payload.accuracy)
    _write_audit(email, "test_geofence_coordinate", "geofences", result["geofence_id"], result, "HR tested coordinate against geofence.")
    return result

@app.post("/api/v1/hr/location-assignments")
def v1_hr_create_location_assignment(payload: HrLocationAssignmentRequest, email: str = Depends(_verify)):
    _require_permission(email, "hr:write")
    if not payload.employee_code.strip() or not payload.location_id.strip():
        raise HTTPException(status_code=422, detail="employee_code and location_id are required.")
    if not _active_record(_records_by_field("work_locations", "location_id", payload.location_id)):
        raise HTTPException(status_code=404, detail="Work location not found.")
    item = storage.create_record("employee_location_assignments", {
        "assignment_id": _new_ref("LASSIGN"),
        "employee_code": payload.employee_code.strip(),
        "location_id": payload.location_id.strip(),
        "shift": payload.shift.strip() or "General",
        "effective_start_date": _clean_text(payload.effective_start_date),
        "effective_end_date": _clean_text(payload.effective_end_date),
        "assignment_type": payload.assignment_type.strip() or "Primary",
        "approval_status": payload.approval_status.strip() or "Approved",
        "status": payload.status.strip() or "Active",
    })
    _write_audit(email, "assign_employee_location", "employee_location_assignments", item.get("id", ""), item.get("data", {}), "HR assigned employee work location.")
    return {"item": item, "dashboard": v1_hr_geofence_dashboard(email)}

@app.get("/api/v1/finance/salary-dashboard")
def v1_finance_salary_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
    return _salary_dashboard()

@app.post("/api/v1/finance/salary-structures")
def v1_finance_salary_structure(payload: SalaryStructureRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _create_salary_structure(payload, email)

@app.post("/api/v1/finance/salary-components")
def v1_finance_salary_component(payload: SalaryComponentRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _create_salary_component(payload, email)

@app.post("/api/v1/finance/salary-assignments")
def v1_finance_salary_assignment(payload: SalaryAssignmentRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    item = _create_salary_assignment(payload, email)
    return {"item": item, "dashboard": _salary_dashboard()}

@app.post("/api/v1/finance/salary-revisions")
def v1_finance_salary_revision(payload: SalaryRevisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _request_salary_revision(payload, email)

@app.post("/api/v1/finance/salary-revisions/decision")
def v1_finance_salary_revision_decision(payload: SalaryRevisionDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _decide_salary_revision(payload, email)

@app.get("/api/v1/finance/payroll-dashboard")
def v1_finance_payroll_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
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
        "policy": _active_payroll_policy().get("data", {}),
    }

@app.get("/api/v1/finance/settings-dashboard")
def v1_finance_settings_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
    return _payroll_policy_dashboard()

@app.post("/api/v1/finance/payroll-policy")
def v1_finance_save_payroll_policy(payload: PayrollPolicyRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _save_payroll_policy(payload, email)

@app.get("/api/v1/finance/adjustments-dashboard")
def v1_finance_adjustments_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
    return _adjustment_dashboard()

@app.post("/api/v1/finance/payroll-adjustments")
def v1_create_payroll_adjustment(payload: PayrollAdjustmentRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _create_payroll_adjustment(payload, email)

@app.post("/api/v1/finance/payroll-adjustments/decision")
def v1_decide_payroll_adjustment(payload: PayrollAdjustmentDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _decide_payroll_adjustment(payload, email)

@app.post("/api/v1/finance/payroll-runs/decision")
def v1_decide_payroll_run(payload: PayrollRunDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _decide_payroll_run(payload, email)

@app.get("/api/v1/finance/payment-dashboard")
def v1_finance_payment_dashboard(email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
    return _payment_dashboard()

@app.post("/api/v1/finance/payment-batches")
def v1_create_payment_batch(payload: PaymentBatchRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _create_payment_batch(payload, email)

@app.post("/api/v1/finance/payment-batches/decision")
def v1_decide_payment_batch(payload: PaymentBatchDecisionRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _decide_payment_batch(payload, email)

@app.get("/api/v1/finance/payment-batches/{batch_id}/export")
def v1_export_payment_batch(batch_id: str, email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
    return _payment_batch_csv(batch_id)

@app.post("/api/v1/payroll/generate")
def v1_generate_payroll(payload: PayrollGenerateRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:write")
    return _payroll_calculation(payload, email)

@app.post("/api/v1/payroll/validate")
def v1_validate_payroll(payload: PayrollGenerateRequest, email: str = Depends(_verify)):
    _require_permission(email, "finance:read")
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
    _notify_employee(employee_code, "day_in_success", "Day In recorded", f"Day In at {_hhmm()} with {validation['geofence_status']} status.", email)
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
    _notify_employee(employee_code, "day_out_success", "Day Out recorded", f"Day Out at {_hhmm()} with {validation['geofence_status']} status.", email)
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
    slips = _salary_slip_rows(employee_code, 24)
    totals = {
        "gross_pay": round(sum(_money(item.get("gross_pay")) for item in slips), 2),
        "deductions": round(sum(_money(item.get("deductions")) for item in slips), 2),
        "net_pay": round(sum(_money(item.get("net_pay")) for item in slips), 2),
    }
    return {"items": slips, "latest": slips[0] if slips else None, "totals": totals}

@app.get("/api/v1/employee/salary-slips")
def v1_employee_salary_slips(email: str = Depends(_verify)):
    return employee_salary(email)

@app.get("/api/v1/employee/notifications")
def v1_employee_notifications(email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    notifications = _employee_notifications(employee_code, email, 100)
    return {
        "items": notifications,
        "unread": len([row for row in notifications if row.get("data", {}).get("read_status", "Unread") == "Unread"]),
    }

@app.post("/api/v1/employee/notifications/read")
def v1_employee_notification_read(payload: NotificationReadRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email)
    notification = next(
        (
            item for item in _employee_notifications(employee_code, email, 200)
            if item.get("id") == payload.notification_id or item.get("data", {}).get("notification_id") == payload.notification_id
        ),
        None,
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found.")
    updated = storage.update_record("notifications", notification.get("id", ""), {"read_status": "Read", "status": "Closed"})
    return {"item": updated, "dashboard": v1_employee_notifications(email)}

@app.post("/api/mobile/employee/leave")
def employee_leave(payload: LeaveApplyRequest, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    if not payload.leave_type.strip() or not payload.from_date.strip() or not payload.to_date.strip():
        raise HTTPException(status_code=422, detail="Leave type, from date, and to date are required.")
    application = _create_leave_application(LeaveApplicationRequest(
        employee_code=employee_code,
        leave_type=payload.leave_type,
        start_date=payload.from_date,
        end_date=payload.to_date,
        reason=payload.reason,
    ), email, employee_code)
    item = storage.create_record("leave_requests", {
        "employee_code": employee_code,
        "leave_type": payload.leave_type.strip(),
        "from_date": payload.from_date.strip(),
        "to_date": payload.to_date.strip(),
        "reason": payload.reason.strip(),
        "status": "Pending",
    })
    return {"item": item, "application": application}

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
def create_module_record(resource: str, payload: RecordCreate, email: str = Depends(_verify)):
    _require_resource_write(email, resource)
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
