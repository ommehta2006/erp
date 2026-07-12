import json
import os
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .security import hash_password, verify_password


RESOURCE_CATALOG: Dict[str, Dict[str, Any]] = {
    "employees": {"label": "Employees", "icon": "users", "fields": ["employee_code", "full_name", "department", "role", "phone", "email", "shift", "status"]},
    "attendance": {"label": "Attendance", "icon": "calendar-check", "fields": ["employee_code", "date", "shift", "check_in", "check_out", "gps_area", "status"]},
    "leave_requests": {"label": "Leave", "icon": "calendar-days", "fields": ["employee_code", "leave_type", "from_date", "to_date", "reason", "status"]},
    "shifts": {"label": "Shifts", "icon": "clock", "fields": ["name", "start_time", "end_time", "department", "supervisor", "status"]},
    "departments": {"label": "Departments", "icon": "building-2", "fields": ["name", "head", "cost_center", "location", "status"]},
    "farmers": {"label": "Farmers", "icon": "sprout", "fields": ["farmer_code", "full_name", "village", "mobile", "bank_status", "status"]},
    "cane_registrations": {"label": "Cane Registration", "icon": "leaf", "fields": ["farmer_code", "plot_no", "village", "area_acres", "variety", "expected_tonnage", "status"]},
    "harvest_plans": {"label": "Harvest Plans", "icon": "route", "fields": ["plot_no", "planned_date", "contractor", "vehicle_no", "expected_tonnage", "status"]},
    "vehicles": {"label": "Vehicles", "icon": "truck", "fields": ["vehicle_no", "type", "driver", "gps_device", "capacity_ton", "status"]},
    "weighbridge_tickets": {"label": "Weighbridge", "icon": "scale", "fields": ["ticket_no", "vehicle_no", "farmer_code", "gross_weight", "tare_weight", "net_weight", "quality_status", "status"]},
    "production_batches": {"label": "Production", "icon": "factory", "fields": ["batch_no", "date", "cane_crushed_ton", "sugar_bags", "recovery_percent", "molasses_ton", "power_kwh", "status"]},
    "quality_tests": {"label": "Quality Lab", "icon": "flask-conical", "fields": ["sample_no", "source", "brix", "pol", "purity", "tested_by", "status"]},
    "maintenance_work_orders": {"label": "Maintenance", "icon": "wrench", "fields": ["work_order_no", "asset_code", "priority", "issue", "assigned_to", "due_date", "status"]},
    "assets": {"label": "Assets", "icon": "package-check", "fields": ["asset_code", "name", "department", "criticality", "last_service", "status"]},
    "inventory_items": {"label": "Inventory", "icon": "boxes", "fields": ["item_code", "name", "category", "warehouse", "quantity", "reorder_level", "status"]},
    "purchase_orders": {"label": "Purchasing", "icon": "shopping-cart", "fields": ["po_no", "supplier", "amount", "delivery_date", "department", "status"]},
    "sales_orders": {"label": "Sales", "icon": "receipt", "fields": ["so_no", "customer", "product", "quantity", "amount", "dispatch_date", "status"]},
    "invoices": {"label": "Finance", "icon": "indian-rupee", "fields": ["invoice_no", "party", "invoice_type", "amount", "due_date", "payment_status", "status"]},
    "incidents": {"label": "Safety", "icon": "shield-alert", "fields": ["incident_no", "area", "severity", "reported_by", "summary", "corrective_action", "status"]},
    "tasks": {"label": "Tasks", "icon": "list-checks", "fields": ["title", "owner", "department", "due_date", "priority", "status"]},
    "approvals": {"label": "Approvals", "icon": "badge-check", "fields": ["request_type", "request_ref", "requested_by", "approver", "risk", "decision", "status"]},
    "payroll_runs": {"label": "Payroll", "icon": "wallet-cards", "fields": ["run_no", "period", "department", "gross_pay", "deductions", "net_pay", "approval_status", "status"]},
    "training_records": {"label": "Training", "icon": "graduation-cap", "fields": ["training_no", "employee_code", "course", "trainer", "completion_date", "score", "status"]},
    "visitor_passes": {"label": "Visitors", "icon": "contact", "fields": ["pass_no", "visitor_name", "company", "host_employee", "area", "check_in", "check_out", "status"]},
    "documents": {"label": "Documents", "icon": "file-text", "fields": ["document_no", "title", "category", "owner", "classification", "expiry_date", "status"]},
    "dispatches": {"label": "Dispatch", "icon": "send", "fields": ["dispatch_no", "customer", "product", "vehicle_no", "quantity", "gate_pass", "status"]},
    "warehouses": {"label": "Warehouses", "icon": "warehouse", "fields": ["warehouse_code", "name", "type", "manager", "capacity", "utilization_percent", "status"]},
    "power_generation": {"label": "Power Plant", "icon": "zap", "fields": ["shift", "date", "turbine", "generation_kwh", "export_kwh", "steam_pressure", "status"]},
    "distillery_batches": {"label": "Distillery", "icon": "beaker", "fields": ["batch_no", "feedstock", "start_date", "wash_volume", "alcohol_percent", "yield_litre", "status"]},
    "ethanol_dispatches": {"label": "Ethanol", "icon": "fuel", "fields": ["dispatch_no", "buyer", "litres", "grade", "tanker_no", "invoice_no", "status"]},
    "byproducts": {"label": "By-products", "icon": "recycle", "fields": ["lot_no", "type", "quantity", "storage_location", "quality_grade", "disposition", "status"]},
    "boiler_logs": {"label": "Boiler", "icon": "gauge", "fields": ["log_no", "shift", "steam_pressure", "bagasse_feed", "water_level", "operator", "status"]},
    "packaging_runs": {"label": "Packaging", "icon": "package", "fields": ["run_no", "product", "bag_size", "bags_packed", "line", "supervisor", "status"]},
    "support_tickets": {"label": "Help Desk", "icon": "life-buoy", "fields": ["ticket_no", "requester", "category", "priority", "assigned_to", "summary", "status"]},
}

ROLE_PERMISSIONS = {
    "PLATFORM_ADMIN": {"*": ["read", "create", "update", "delete", "admin"]},
    "FACTORY_ADMIN": {"*": ["read", "create", "update", "delete"]},
    "HR_MANAGER": {"employees": ["read", "create", "update"], "attendance": ["read", "create", "update"], "leave_requests": ["read", "create", "update"], "shifts": ["read", "create", "update"], "departments": ["read"], "payroll_runs": ["read", "create", "update"], "training_records": ["read", "create", "update"], "visitor_passes": ["read", "create", "update"], "documents": ["read", "create", "update"], "approvals": ["read", "update"], "tasks": ["read", "create", "update"]},
    "PRODUCTION_MANAGER": {"production_batches": ["read", "create", "update"], "weighbridge_tickets": ["read", "update"], "quality_tests": ["read"], "harvest_plans": ["read", "update"], "power_generation": ["read", "create", "update"], "distillery_batches": ["read", "create", "update"], "byproducts": ["read", "create", "update"], "boiler_logs": ["read", "create", "update"], "packaging_runs": ["read", "create", "update"], "dispatches": ["read", "update"], "tasks": ["read", "create", "update"], "incidents": ["read", "create"]},
    "FARMER_OFFICER": {"farmers": ["read", "create", "update"], "cane_registrations": ["read", "create", "update"], "harvest_plans": ["read", "create", "update"], "vehicles": ["read"], "weighbridge_tickets": ["read"]},
    "QUALITY_MANAGER": {"quality_tests": ["read", "create", "update"], "weighbridge_tickets": ["read"], "production_batches": ["read"], "incidents": ["read", "create"]},
    "MAINTENANCE_MANAGER": {"assets": ["read", "create", "update"], "maintenance_work_orders": ["read", "create", "update"], "inventory_items": ["read"], "tasks": ["read", "create", "update"], "incidents": ["read", "create"]},
    "INVENTORY_MANAGER": {"inventory_items": ["read", "create", "update"], "warehouses": ["read", "create", "update"], "dispatches": ["read", "create", "update"], "purchase_orders": ["read", "create", "update"], "sales_orders": ["read"], "assets": ["read"]},
    "FINANCE_MANAGER": {"purchase_orders": ["read", "update"], "sales_orders": ["read", "create", "update"], "invoices": ["read", "create", "update"], "payroll_runs": ["read", "update"], "ethanol_dispatches": ["read", "create", "update"], "approvals": ["read", "update"]},
    "EMPLOYEE": {"employees": ["read"], "attendance": ["read", "create"], "leave_requests": ["read", "create"], "training_records": ["read"], "documents": ["read"], "visitor_passes": ["read", "create"], "support_tickets": ["read", "create"], "tasks": ["read", "update"], "incidents": ["read", "create"], "approvals": ["read"]},
}


class PermissionDenied(Exception):
    pass


class ValidationError(Exception):
    pass


class NotFound(Exception):
    pass


class DataStore:
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.migrate()
        self.seed()

    def migrate(self):
        self.conn.executescript(
            """
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS tenants (
                id TEXT PRIMARY KEY,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS records (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL REFERENCES tenants(id),
                resource TEXT NOT NULL,
                data TEXT NOT NULL,
                status TEXT NOT NULL,
                version INTEGER NOT NULL DEFAULT 1,
                created_by TEXT NOT NULL,
                updated_by TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_records_tenant_resource ON records(tenant_id, resource, updated_at DESC);
            CREATE TABLE IF NOT EXISTS audit_events (
                id TEXT PRIMARY KEY,
                tenant_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                resource TEXT NOT NULL,
                target_id TEXT,
                metadata TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_audit_tenant_created ON audit_events(tenant_id, created_at DESC);
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                tenant_id TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                response TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                PRIMARY KEY (tenant_id, actor_id, idempotency_key)
            );
            """
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

    def seed(self):
        slug = os.getenv("DEFAULT_TENANT_SLUG", "vp-sugar-factory")
        name = os.getenv("DEFAULT_TENANT_NAME", "Vasantdada Patil Sugar Factory")
        tenant = self.conn.execute("SELECT * FROM tenants WHERE slug = ?", (slug,)).fetchone()
        now = int(time.time())
        if not tenant:
            tenant_id = str(uuid.uuid4())
            self.conn.execute("INSERT INTO tenants VALUES (?, ?, ?, ?, ?)", (tenant_id, slug, name, "active", now))
        else:
            tenant_id = tenant["id"]

        email = os.getenv("BOOTSTRAP_ADMIN_EMAIL", "admin@factorypulse.local").lower()
        password = os.getenv("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe-FactoryPulse-2026!")
        existing = self.conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if not existing:
            self.conn.execute(
                "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), tenant_id, email, os.getenv("BOOTSTRAP_ADMIN_NAME", "FactoryPulse Admin"), "FACTORY_ADMIN", hash_password(password), "active", now),
            )

        if self.conn.execute("SELECT COUNT(*) c FROM records WHERE tenant_id = ?", (tenant_id,)).fetchone()["c"] == 0:
            self._seed_records(tenant_id, now)
        self.conn.commit()

    def _seed_records(self, tenant_id: str, now: int):
        admin = "system-seed"
        samples = {
            "employees": [
                {"employee_code": "EMP-1001", "full_name": "Aarav Patil", "department": "Crushing", "role": "Shift Supervisor", "phone": "+91-90000-10001", "email": "aarav.patil@example.invalid", "shift": "A", "status": "Active"},
                {"employee_code": "EMP-1042", "full_name": "Neha Kulkarni", "department": "Quality", "role": "Lab Analyst", "phone": "+91-90000-10042", "email": "neha.kulkarni@example.invalid", "shift": "B", "status": "Active"},
            ],
            "production_batches": [{"batch_no": "PRD-2026-0712-A", "date": "2026-07-12", "cane_crushed_ton": "8150", "sugar_bags": "17820", "recovery_percent": "11.34", "molasses_ton": "324", "power_kwh": "128400", "status": "Running"}],
            "weighbridge_tickets": [{"ticket_no": "WB-77881", "vehicle_no": "MH10-AB-1188", "farmer_code": "FARM-2201", "gross_weight": "28.4", "tare_weight": "9.8", "net_weight": "18.6", "quality_status": "Accepted", "status": "Posted"}],
            "inventory_items": [{"item_code": "CHEM-LIME-25", "name": "Process Lime", "category": "Chemical", "warehouse": "Main Stores", "quantity": "420", "reorder_level": "150", "status": "In Stock"}],
            "maintenance_work_orders": [{"work_order_no": "MWO-5120", "asset_code": "MILL-03", "priority": "High", "issue": "Bearing temperature above threshold", "assigned_to": "EMP-1001", "due_date": "2026-07-13", "status": "Open"}],
            "quality_tests": [{"sample_no": "LAB-90021", "source": "Mill Juice", "brix": "18.4", "pol": "15.2", "purity": "82.6", "tested_by": "EMP-1042", "status": "Verified"}],
            "approvals": [{"request_type": "Purchase Order", "request_ref": "PO-4021", "requested_by": "Stores", "approver": "Finance Manager", "risk": "Medium", "decision": "Pending", "status": "Awaiting Approval"}],
            "farmers": [{"farmer_code": "FARM-2201", "full_name": "Suresh Jadhav", "village": "Sangli", "mobile": "+91-90000-02201", "bank_status": "Verified", "status": "Active"}],
            "cane_registrations": [{"farmer_code": "FARM-2201", "plot_no": "PLT-77", "village": "Sangli", "area_acres": "4.5", "variety": "Co 86032", "expected_tonnage": "185", "status": "Surveyed"}],
            "incidents": [{"incident_no": "SAFE-301", "area": "Boiler House", "severity": "Low", "reported_by": "EMP-1001", "summary": "PPE non-compliance observed", "corrective_action": "Toolbox talk scheduled", "status": "Open"}],
        }
        for resource, rows in samples.items():
            for row in rows:
                self.conn.execute(
                    "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), tenant_id, resource, json.dumps(row, sort_keys=True), row.get("status", "Active"), 1, admin, admin, now, now),
                )

    def authenticate(self, email: str, password: str) -> Dict[str, Any] | None:
        user = self.conn.execute("SELECT * FROM users WHERE email = ? AND status = 'active'", (email.lower(),)).fetchone()
        if user and verify_password(password, user["password_hash"]):
            return self._user_dict(user)
        return None

    def get_user(self, user_id: str) -> Dict[str, Any] | None:
        user = self.conn.execute("SELECT * FROM users WHERE id = ? AND status = 'active'", (user_id,)).fetchone()
        return self._user_dict(user) if user else None

    def _user_dict(self, row) -> Dict[str, Any]:
        tenant = self.conn.execute("SELECT slug, name FROM tenants WHERE id = ?", (row["tenant_id"],)).fetchone()
        return {"id": row["id"], "tenant_id": row["tenant_id"], "tenant_slug": tenant["slug"], "tenant_name": tenant["name"], "email": row["email"], "name": row["name"], "role": row["role"]}

    def can(self, user: Dict[str, Any], resource: str, action: str) -> bool:
        rules = ROLE_PERMISSIONS.get(user["role"], {})
        allowed = set(rules.get(resource, [])) | set(rules.get("*", []))
        return action in allowed or "admin" in allowed

    def require(self, user: Dict[str, Any], resource: str, action: str):
        if resource not in RESOURCE_CATALOG and resource != "audit_events":
            raise NotFound("unknown resource")
        if not self.can(user, resource, action):
            self.audit(user, "permission_denied", resource, None, {"action": action})
            raise PermissionDenied("permission denied")

    def list_records(self, user: Dict[str, Any], resource: str, limit: int = 100) -> List[Dict[str, Any]]:
        self.require(user, resource, "read")
        limit = min(max(int(limit), 1), 500)
        rows = self.conn.execute(
            "SELECT * FROM records WHERE tenant_id = ? AND resource = ? ORDER BY updated_at DESC LIMIT ?",
            (user["tenant_id"], resource, limit),
        ).fetchall()
        return [self._record_dict(row) for row in rows]

    def get_record(self, user: Dict[str, Any], resource: str, record_id: str) -> Dict[str, Any]:
        self.require(user, resource, "read")
        row = self.conn.execute("SELECT * FROM records WHERE tenant_id = ? AND resource = ? AND id = ?", (user["tenant_id"], resource, record_id)).fetchone()
        if not row:
            raise NotFound("record not found")
        return self._record_dict(row)

    def create_record(self, user: Dict[str, Any], resource: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.require(user, resource, "create")
        data = self._validate_resource_payload(resource, payload)
        now = int(time.time())
        record_id = str(uuid.uuid4())
        self.conn.execute(
            "INSERT INTO records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (record_id, user["tenant_id"], resource, json.dumps(data, sort_keys=True), data.get("status", "Active"), 1, user["id"], user["id"], now, now),
        )
        self.conn.commit()
        self.audit(user, "create", resource, record_id, {"fields": sorted(data.keys())})
        return self.get_record(user, resource, record_id)

    def update_record(self, user: Dict[str, Any], resource: str, record_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.require(user, resource, "update")
        current = self.get_record(user, resource, record_id)
        data = current["data"]
        data.update(self._validate_resource_payload(resource, payload, partial=True))
        now = int(time.time())
        self.conn.execute(
            "UPDATE records SET data = ?, status = ?, version = version + 1, updated_by = ?, updated_at = ? WHERE tenant_id = ? AND resource = ? AND id = ?",
            (json.dumps(data, sort_keys=True), data.get("status", current["status"]), user["id"], now, user["tenant_id"], resource, record_id),
        )
        self.conn.commit()
        self.audit(user, "update", resource, record_id, {"fields": sorted(payload.keys())})
        return self.get_record(user, resource, record_id)

    def audit(self, user: Dict[str, Any], action: str, resource: str, target_id: str | None, metadata: Dict[str, Any]):
        self.conn.execute(
            "INSERT INTO audit_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), user["tenant_id"], user["id"], action, resource, target_id, json.dumps(metadata, sort_keys=True), int(time.time())),
        )
        self.conn.commit()

    def audit_events(self, user: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
        self.require(user, "audit_events", "read") if user["role"] != "FACTORY_ADMIN" else None
        rows = self.conn.execute(
            "SELECT * FROM audit_events WHERE tenant_id = ? ORDER BY created_at DESC LIMIT ?",
            (user["tenant_id"], min(int(limit), 500)),
        ).fetchall()
        return [dict(row) | {"metadata": json.loads(row["metadata"])} for row in rows]

    def dashboard(self, user: Dict[str, Any]) -> Dict[str, Any]:
        visible = [name for name in RESOURCE_CATALOG if self.can(user, name, "read")]
        counts = {}
        for resource in visible:
            counts[resource] = self.conn.execute("SELECT COUNT(*) c FROM records WHERE tenant_id = ? AND resource = ?", (user["tenant_id"], resource)).fetchone()["c"]
        production = self.list_records(user, "production_batches", 5) if "production_batches" in visible else []
        approvals = self.list_records(user, "approvals", 5) if "approvals" in visible else []
        work_orders = self.list_records(user, "maintenance_work_orders", 5) if "maintenance_work_orders" in visible else []
        return {"counts": counts, "production": production, "approvals": approvals, "work_orders": work_orders, "visible_resources": visible}

    def catalog_for(self, user: Dict[str, Any]) -> Dict[str, Any]:
        return {
            name: spec
            for name, spec in RESOURCE_CATALOG.items()
            if self.can(user, name, "read") or self.can(user, name, "create") or self.can(user, name, "update")
        }



    def mobile_home(self, user: Dict[str, Any]) -> Dict[str, Any]:
        visible = self.catalog_for(user)
        profile = None
        if self.can(user, "employees", "read"):
            rows = self.list_records(user, "employees", 25)
            profile = next((row for row in rows if row["data"].get("email", "").lower() == user["email"].lower()), None)
            profile = profile or (rows[0] if rows else None)
        return {
            "profile": profile,
            "quick_actions": [
                {"id": "check_in", "label": "Check in", "resource": "attendance"},
                {"id": "leave", "label": "Request leave", "resource": "leave_requests"},
                {"id": "incident", "label": "Report incident", "resource": "incidents"},
                {"id": "sos", "label": "Emergency SOS", "resource": "incidents"},
            ],
            "attendance": self.list_records(user, "attendance", 5) if "attendance" in visible else [],
            "tasks": self.list_records(user, "tasks", 5) if "tasks" in visible else [],
            "leave_requests": self.list_records(user, "leave_requests", 5) if "leave_requests" in visible else [],
            "training_records": self.list_records(user, "training_records", 5) if "training_records" in visible else [],
            "documents": self.list_records(user, "documents", 5) if "documents" in visible else [],
        }

    def mobile_check_in(self, user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_code = str(payload.get("employee_code") or self._employee_code_for(user) or user["email"]).strip()
        data = {
            "employee_code": employee_code,
            "date": str(payload.get("date") or time.strftime("%Y-%m-%d")),
            "shift": str(payload.get("shift") or "General"),
            "check_in": str(payload.get("check_in") or time.strftime("%H:%M")),
            "check_out": str(payload.get("check_out") or ""),
            "gps_area": str(payload.get("gps_area") or "Factory Gate"),
            "status": "Checked In",
        }
        item = self.create_record(user, "attendance", data)
        self.audit(user, "mobile_check_in", "attendance", item["id"], {"employee_code": employee_code})
        return item

    def mobile_leave_request(self, user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        employee_code = str(payload.get("employee_code") or self._employee_code_for(user) or user["email"]).strip()
        data = {
            "employee_code": employee_code,
            "leave_type": str(payload.get("leave_type") or "Casual Leave"),
            "from_date": str(payload.get("from_date") or time.strftime("%Y-%m-%d")),
            "to_date": str(payload.get("to_date") or payload.get("from_date") or time.strftime("%Y-%m-%d")),
            "reason": str(payload.get("reason") or "Requested from employee app"),
            "status": "Pending",
        }
        item = self.create_record(user, "leave_requests", data)
        self.audit(user, "mobile_leave_request", "leave_requests", item["id"], {"employee_code": employee_code})
        return item

    def mobile_incident_report(self, user: Dict[str, Any], payload: Dict[str, Any], sos: bool = False) -> Dict[str, Any]:
        severity = "Critical" if sos else str(payload.get("severity") or "Medium")
        data = {
            "incident_no": str(payload.get("incident_no") or f"MOB-{int(time.time())}"),
            "area": str(payload.get("area") or "Factory"),
            "severity": severity,
            "reported_by": str(payload.get("reported_by") or self._employee_code_for(user) or user["email"]),
            "summary": str(payload.get("summary") or ("Emergency SOS raised from employee app" if sos else "Incident reported from employee app")),
            "corrective_action": str(payload.get("corrective_action") or "Supervisor review required"),
            "status": "Open",
        }
        item = self.create_record(user, "incidents", data)
        self.audit(user, "mobile_sos" if sos else "mobile_incident_report", "incidents", item["id"], {"severity": severity})
        return item

    def _employee_code_for(self, user: Dict[str, Any]) -> str | None:
        try:
            rows = self.list_records(user, "employees", 50)
        except PermissionDenied:
            return None
        for row in rows:
            if row["data"].get("email", "").lower() == user["email"].lower():
                return row["data"].get("employee_code")
        return rows[0]["data"].get("employee_code") if rows else None

    def list_users(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        if user["role"] not in {"FACTORY_ADMIN", "PLATFORM_ADMIN", "HR_MANAGER"}:
            self.audit(user, "permission_denied", "users", None, {"action": "read"})
            raise PermissionDenied("permission denied")
        rows = self.conn.execute(
            "SELECT id, email, name, role, status, created_at FROM users WHERE tenant_id = ? ORDER BY created_at DESC",
            (user["tenant_id"],),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_user(self, user: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        if user["role"] not in {"FACTORY_ADMIN", "PLATFORM_ADMIN", "HR_MANAGER"}:
            self.audit(user, "permission_denied", "users", None, {"action": "create"})
            raise PermissionDenied("permission denied")
        email = str(payload.get("email", "")).strip().lower()
        name = str(payload.get("name", "")).strip()
        role = str(payload.get("role", "EMPLOYEE")).strip().upper()
        password = str(payload.get("password", ""))
        if "@" not in email or len(email) > 160:
            raise ValidationError("valid email is required")
        if not name or len(name) > 120:
            raise ValidationError("valid name is required")
        if role not in ROLE_PERMISSIONS:
            raise ValidationError("unknown role")
        user_id = str(uuid.uuid4())
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, user["tenant_id"], email, name, role, hash_password(password), "active", now),
        )
        self.conn.commit()
        self.audit(user, "create", "users", user_id, {"email": email, "role": role})
        return {"id": user_id, "email": email, "name": name, "role": role, "status": "active", "created_at": now}

    def search_records(self, user: Dict[str, Any], query: str, limit: int = 50) -> List[Dict[str, Any]]:
        query = str(query or "").strip().lower()
        if len(query) < 2:
            raise ValidationError("search query must be at least 2 characters")
        limit = min(max(int(limit), 1), 100)
        results: List[Dict[str, Any]] = []
        for resource in RESOURCE_CATALOG:
            if not self.can(user, resource, "read"):
                continue
            rows = self.conn.execute(
                "SELECT * FROM records WHERE tenant_id = ? AND resource = ? ORDER BY updated_at DESC LIMIT 200",
                (user["tenant_id"], resource),
            ).fetchall()
            for row in rows:
                item = self._record_dict(row)
                haystack = json.dumps(item["data"], sort_keys=True).lower()
                if query in haystack:
                    results.append({"resource": resource, "label": RESOURCE_CATALOG[resource]["label"], "item": item})
                    if len(results) >= limit:
                        return results
        return results

    def operations_summary(self, user: Dict[str, Any]) -> Dict[str, Any]:
        dashboard = self.dashboard(user)
        def first(resource: str, field: str, default: str = "0") -> str:
            if not self.can(user, resource, "read"):
                return default
            rows = self.list_records(user, resource, 1)
            return str(rows[0]["data"].get(field, default)) if rows else default
        return {
            "tenant": user["tenant_name"],
            "visible_module_count": len(dashboard["visible_resources"]),
            "record_count": sum(dashboard["counts"].values()),
            "cane_crushed_ton": first("production_batches", "cane_crushed_ton"),
            "recovery_percent": first("production_batches", "recovery_percent"),
            "power_generation_kwh": first("power_generation", "generation_kwh"),
            "sugar_bags": first("production_batches", "sugar_bags"),
            "open_approvals": dashboard["counts"].get("approvals", 0),
            "open_work_orders": dashboard["counts"].get("maintenance_work_orders", 0),
            "risk_signals": [
                "High-priority maintenance work orders require supervisor review",
                "Payroll runs remain draft until finance approval",
                "Visitor passes without checkout should be reviewed at shift close",
            ],
        }

    def settings_summary(self, user: Dict[str, Any]) -> Dict[str, Any]:
        if user["role"] not in {"FACTORY_ADMIN", "PLATFORM_ADMIN"}:
            self.audit(user, "permission_denied", "settings", None, {"action": "read"})
            raise PermissionDenied("permission denied")
        return {
            "tenant_slug": user["tenant_slug"],
            "tenant_name": user["tenant_name"],
            "app_env": os.getenv("APP_ENV", "development"),
            "database": "sqlite",
            "cors_configured": bool(os.getenv("CORS_ALLOWED_ORIGINS")),
            "token_ttl_seconds": int(os.getenv("TOKEN_TTL_SECONDS", "28800")),
            "available_roles": sorted(ROLE_PERMISSIONS.keys()),
            "module_count": len(RESOURCE_CATALOG),
        }

    def get_idempotency(self, user: Dict[str, Any], key: str | None) -> Dict[str, Any] | None:
        if not key:
            return None
        if len(key) > 128:
            raise ValidationError("idempotency key is too long")
        row = self.conn.execute(
            "SELECT response FROM idempotency_keys WHERE tenant_id = ? AND actor_id = ? AND idempotency_key = ?",
            (user["tenant_id"], user["id"], key),
        ).fetchone()
        return json.loads(row["response"]) if row else None

    def save_idempotency(self, user: Dict[str, Any], key: str | None, response: Dict[str, Any]):
        if not key:
            return
        if len(key) > 128:
            raise ValidationError("idempotency key is too long")
        self.conn.execute(
            "INSERT OR IGNORE INTO idempotency_keys VALUES (?, ?, ?, ?, ?)",
            (user["tenant_id"], user["id"], key, json.dumps(response, sort_keys=True), int(time.time())),
        )
        self.conn.commit()

    def _record_dict(self, row) -> Dict[str, Any]:
        return {
            "id": row["id"],
            "resource": row["resource"],
            "status": row["status"],
            "version": row["version"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "data": json.loads(row["data"]),
        }

    def _validate_resource_payload(self, resource: str, payload: Dict[str, Any], partial: bool = False) -> Dict[str, str]:
        if not isinstance(payload, dict):
            raise ValidationError("payload must be an object")
        if resource not in RESOURCE_CATALOG:
            raise NotFound("unknown resource")
        allowed = set(RESOURCE_CATALOG[resource]["fields"])
        rejected = sorted(set(payload) - allowed)
        if rejected:
            raise ValidationError(f"unknown fields: {', '.join(rejected)}")
        clean = {}
        for key, value in payload.items():
            if value is None:
                value = ""
            value = str(value).strip()
            if len(value) > 500:
                raise ValidationError(f"{key} is too long")
            clean[key] = value
        if not partial and not clean:
            raise ValidationError("at least one field is required")
        return clean
