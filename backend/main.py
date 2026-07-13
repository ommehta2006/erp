import base64
import hashlib
import hmac
import os
import time
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
