import base64
import hashlib
import hmac
import os
import time
from datetime import date, datetime, timezone
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
    return {
        "employee_code": employee_code,
        "attendance": attendance,
        "attendance_policy": policy,
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

@app.post("/api/mobile/employee/day-in")
def employee_day_in(payload: EmployeeAttendanceEvent, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    policy = _attendance_policy()
    snapshot = _attendance_snapshot(employee_code, policy)
    if snapshot["checked_in"]:
        raise HTTPException(status_code=409, detail="Day-in already active. Complete day-out first.")
    data = {
        "employee_code": employee_code,
        "date": _today(),
        "shift": payload.shift or "General",
        "check_in": _hhmm(),
        "gps_area": _gps(payload),
        "status": "Active",
    }
    item = storage.create_record("attendance", data)
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
    return {"item": item, "attendance": _attendance_snapshot(employee_code, policy), "attendance_policy": policy}

@app.post("/api/mobile/employee/day-out")
def employee_day_out(payload: EmployeeAttendanceEvent, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    policy = _attendance_policy()
    snapshot = _attendance_snapshot(employee_code, policy)
    if not snapshot["day_in_time"]:
        raise HTTPException(status_code=409, detail="Day-in is required before day-out.")
    if snapshot["day_out_time"]:
        raise HTTPException(status_code=409, detail="Day-out already recorded for today.")
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
    return {"item": item, "attendance": _attendance_snapshot(employee_code, policy), "attendance_policy": policy}

@app.post("/api/mobile/employee/location")
def employee_location(payload: EmployeeLocationPing, email: str = Depends(_verify)):
    employee_code = _employee_code(email, payload.employee_code)
    snapshot = _attendance_snapshot(employee_code)
    if not snapshot["checked_in"]:
        raise HTTPException(status_code=409, detail="Location tracking is allowed only during active working hours after day-in.")
    item = storage.create_record("employee_locations", {
        "employee_code": employee_code,
        "timestamp": _now_iso(),
        "latitude": str(payload.latitude),
        "longitude": str(payload.longitude),
        "accuracy": str(payload.accuracy or ""),
        "event": payload.event or "tracking",
        "status": "Active",
    })
    return {"item": item, "tracking": {"active": True}}

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
