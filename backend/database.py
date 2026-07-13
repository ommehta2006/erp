import os
import sqlite3
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

load_dotenv()
try:
    from supabase import create_client
except Exception:
    create_client = None

ROOT = Path(__file__).resolve().parents[1]

DEPARTMENTS = {
    "hr": {"name": "HR & Employee", "modules": ["employees", "attendance", "employee_locations", "leave_requests", "leave_balances", "holiday_calendar", "salary_slips", "shifts", "departments", "payroll_runs", "recruitment", "performance_reviews", "training_records", "expense_claims", "visitor_passes"]},
    "finance": {"name": "Finance & Accounts", "modules": ["invoices", "purchase_orders", "sales_orders", "payroll_runs", "budgets", "tax_records", "farmer_payments", "approvals"]},
    "cane": {"name": "Cane & Farmer", "modules": ["farmers", "cane_registrations", "harvest_plans", "vehicles", "weighbridge_tickets", "farmer_payments"]},
    "manufacturing": {"name": "Manufacturing", "modules": ["production_batches", "boiler_logs", "packaging_runs", "byproducts", "power_generation", "distillery_batches", "ethanol_dispatches", "energy_meters"]},
    "inventory": {"name": "Inventory & Dispatch", "modules": ["inventory_items", "warehouses", "dispatches", "assets", "purchase_orders"]},
    "quality": {"name": "Quality & Compliance", "modules": ["quality_tests", "lab_instruments", "compliance_register", "documents", "incidents"]},
    "maintenance": {"name": "Maintenance & Assets", "modules": ["maintenance_work_orders", "assets", "tasks", "support_tickets"]},
    "sales": {"name": "Sales & Customer", "modules": ["sales_orders", "dispatches", "invoices", "customer_portal_requests"]},
    "admin": {"name": "Administration", "modules": ["approvals", "documents", "tasks", "support_tickets", "incidents"]},
    "security": {"name": "Security & Gate Control", "modules": ["gate_passes", "security_incidents", "contractor_passes", "vehicle_inspections", "patrol_rounds"]},
    "environment": {"name": "Environment & Sustainability", "modules": ["effluent_logs", "emissions_checks", "water_usage", "waste_movements", "sustainability_kpis"]},
    "it": {"name": "IT & Automation", "modules": ["it_assets", "automation_jobs", "system_access_requests", "iot_devices", "backup_checks"]},
    "projects": {"name": "Projects & Capex", "modules": ["capex_projects", "project_milestones", "contractor_bills", "material_requisitions", "risk_register"]},
}

MODULE_FIELDS = {
    "employees": ["employee_code", "full_name", "department", "role", "phone", "email", "shift", "status"],
    "attendance": ["employee_code", "date", "shift", "check_in", "check_out", "gps_area", "status"],
    "employee_locations": ["employee_code", "timestamp", "latitude", "longitude", "accuracy", "event", "status"],
    "leave_requests": ["employee_code", "leave_type", "from_date", "to_date", "reason", "status"],
    "leave_balances": ["employee_code", "leave_type", "opening_balance", "used_days", "available_days", "period", "status"],
    "holiday_calendar": ["holiday_no", "date", "name", "holiday_type", "location", "status"],
    "salary_slips": ["employee_code", "period", "gross_pay", "deductions", "net_pay", "payment_date", "status"],
    "shifts": ["name", "start_time", "end_time", "department", "supervisor", "status"],
    "departments": ["name", "head", "cost_center", "location", "status"],
    "payroll_runs": ["run_no", "period", "department", "gross_pay", "deductions", "net_pay", "approval_status", "status"],
    "recruitment": ["candidate_no", "full_name", "department", "position", "stage", "owner", "status"],
    "performance_reviews": ["review_no", "employee_code", "period", "manager", "rating", "summary", "status"],
    "training_records": ["training_no", "employee_code", "course", "trainer", "completion_date", "score", "status"],
    "expense_claims": ["claim_no", "employee_code", "department", "amount", "category", "approver", "status"],
    "visitor_passes": ["pass_no", "visitor_name", "company", "host_employee", "area", "check_in", "check_out", "status"],
    "invoices": ["invoice_no", "party", "invoice_type", "amount", "due_date", "payment_status", "status"],
    "purchase_orders": ["po_no", "supplier", "amount", "delivery_date", "department", "status"],
    "sales_orders": ["so_no", "customer", "product", "quantity", "amount", "dispatch_date", "status"],
    "budgets": ["budget_no", "department", "period", "allocated_amount", "used_amount", "owner", "status"],
    "tax_records": ["tax_no", "tax_type", "period", "amount", "jurisdiction", "filing_status", "status"],
    "farmer_payments": ["payment_no", "farmer_code", "season", "tonnage", "rate", "amount", "status"],
    "approvals": ["request_type", "request_ref", "requested_by", "approver", "risk", "decision", "status"],
    "farmers": ["farmer_code", "full_name", "village", "mobile", "bank_status", "status"],
    "cane_registrations": ["farmer_code", "plot_no", "village", "area_acres", "variety", "expected_tonnage", "status"],
    "harvest_plans": ["plot_no", "planned_date", "contractor", "vehicle_no", "expected_tonnage", "status"],
    "vehicles": ["vehicle_no", "type", "driver", "gps_device", "capacity_ton", "status"],
    "weighbridge_tickets": ["ticket_no", "vehicle_no", "farmer_code", "gross_weight", "tare_weight", "net_weight", "quality_status", "status"],
    "production_batches": ["batch_no", "date", "cane_crushed_ton", "sugar_bags", "recovery_percent", "molasses_ton", "power_kwh", "status"],
    "boiler_logs": ["log_no", "shift", "steam_pressure", "bagasse_feed", "water_level", "operator", "status"],
    "packaging_runs": ["run_no", "product", "bag_size", "bags_packed", "line", "supervisor", "status"],
    "byproducts": ["lot_no", "type", "quantity", "storage_location", "quality_grade", "disposition", "status"],
    "power_generation": ["shift", "date", "turbine", "generation_kwh", "export_kwh", "steam_pressure", "status"],
    "distillery_batches": ["batch_no", "feedstock", "start_date", "wash_volume", "alcohol_percent", "yield_litre", "status"],
    "ethanol_dispatches": ["dispatch_no", "buyer", "litres", "grade", "tanker_no", "invoice_no", "status"],
    "energy_meters": ["meter_no", "area", "reading_date", "kwh", "operator", "variance", "status"],
    "inventory_items": ["item_code", "name", "category", "warehouse", "quantity", "reorder_level", "status"],
    "warehouses": ["warehouse_code", "name", "type", "manager", "capacity", "utilization_percent", "status"],
    "dispatches": ["dispatch_no", "customer", "product", "vehicle_no", "quantity", "gate_pass", "status"],
    "assets": ["asset_code", "name", "department", "criticality", "last_service", "status"],
    "quality_tests": ["sample_no", "source", "brix", "pol", "purity", "tested_by", "status"],
    "lab_instruments": ["instrument_code", "name", "lab_area", "calibration_due", "owner", "condition", "status"],
    "compliance_register": ["compliance_no", "department", "law_or_standard", "owner", "due_date", "risk", "status"],
    "documents": ["document_no", "title", "category", "owner", "classification", "expiry_date", "status"],
    "incidents": ["incident_no", "area", "severity", "reported_by", "summary", "corrective_action", "status"],
    "maintenance_work_orders": ["work_order_no", "asset_code", "priority", "issue", "assigned_to", "due_date", "status"],
    "tasks": ["title", "owner", "department", "due_date", "priority", "status"],
    "support_tickets": ["ticket_no", "requester", "category", "priority", "assigned_to", "summary", "status"],
    "customer_portal_requests": ["request_no", "customer", "category", "summary", "assigned_to", "priority", "status"],
    "gate_passes": ["pass_no", "visitor_name", "company", "purpose", "host", "valid_until", "status"],
    "security_incidents": ["incident_no", "area", "severity", "reported_by", "summary", "action_taken", "status"],
    "contractor_passes": ["pass_no", "contractor", "work_area", "supervisor", "permit_no", "valid_until", "status"],
    "vehicle_inspections": ["inspection_no", "vehicle_no", "driver", "checklist_score", "defects", "inspector", "status"],
    "patrol_rounds": ["round_no", "area", "guard", "start_time", "end_time", "observations", "status"],
    "effluent_logs": ["log_no", "sample_date", "ph", "bod", "cod", "operator", "status"],
    "emissions_checks": ["check_no", "stack", "reading_date", "particulate_level", "inspector", "remarks", "status"],
    "water_usage": ["meter_no", "area", "reading_date", "kl_consumed", "variance", "operator", "status"],
    "waste_movements": ["movement_no", "waste_type", "quantity", "disposal_vendor", "manifest_no", "status"],
    "sustainability_kpis": ["kpi_no", "period", "energy_intensity", "water_intensity", "recycled_percent", "owner", "status"],
    "it_assets": ["asset_tag", "asset_type", "location", "owner", "warranty_until", "condition", "status"],
    "automation_jobs": ["job_no", "system", "job_type", "schedule", "last_run", "owner", "status"],
    "system_access_requests": ["request_no", "employee_code", "system", "role_requested", "approver", "risk", "status"],
    "iot_devices": ["device_id", "area", "sensor_type", "last_seen", "battery_percent", "firmware", "status"],
    "backup_checks": ["check_no", "system", "backup_date", "result", "restore_tested", "owner", "status"],
    "capex_projects": ["project_code", "name", "department", "budget", "spent", "owner", "status"],
    "project_milestones": ["milestone_no", "project_code", "title", "due_date", "owner", "completion_percent", "status"],
    "contractor_bills": ["bill_no", "contractor", "project_code", "amount", "invoice_date", "approval_status", "status"],
    "material_requisitions": ["mr_no", "project_code", "item", "quantity", "required_date", "approver", "status"],
    "risk_register": ["risk_no", "project_code", "risk", "impact", "mitigation_owner", "due_date", "status"],
}

MODULE_DESCRIPTIONS = {
    "security": "Gate, visitor, contractor, patrol, and incident controls.",
    "environment": "Effluent, emissions, water, waste, and sustainability KPIs.",
    "it": "IT assets, access, automation, IoT devices, and backups.",
    "projects": "Capex, milestones, contractor bills, requisitions, and project risks.",
}

REQUIRED_FIELDS = {
    resource: [field for field in fields if field != "status"][:2]
    for resource, fields in MODULE_FIELDS.items()
}

STATUS_VALUES = {"Open", "Active", "Pending", "Approved", "Rejected", "Completed", "Closed", "On Hold", "Critical"}
NUMERIC_FIELD_WORDS = {
    "accuracy",
    "acres",
    "alcohol",
    "amount",
    "available",
    "bags",
    "balance",
    "battery",
    "bod",
    "brix",
    "budget",
    "capacity",
    "cod",
    "deductions",
    "export",
    "feed",
    "generation",
    "gross",
    "intensity",
    "kl",
    "kwh",
    "latitude",
    "level",
    "litres",
    "longitude",
    "molasses",
    "net",
    "opening",
    "particulate",
    "pay",
    "percent",
    "ph",
    "pol",
    "power",
    "pressure",
    "purity",
    "quantity",
    "rate",
    "reading",
    "recovery",
    "score",
    "spent",
    "tare",
    "ton",
    "tonnage",
    "used",
    "utilization",
    "variance",
    "volume",
    "water",
    "weight",
    "yield",
}

class Storage:
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL", "").strip()
        self.supabase_key = (
            os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            or os.getenv("SUPABASE_SECRET_KEY")
            or os.getenv("SUPABASE_KEY")
            or ""
        ).strip()
        self.app_secret = os.getenv("APP_SECRET_KEY", "").strip()
        self.mode = "supabase" if self.supabase_url and self.supabase_key and create_client else "sqlite"
        self.client = create_client(self.supabase_url, self.supabase_key) if self.mode == "supabase" else None
        self.db_path = Path(os.getenv("APP_DATABASE", ROOT / "data" / "factorypulse.sqlite3"))
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_sqlite()

    def _init_sqlite(self):
        if self.mode != "sqlite":
            return
        con = sqlite3.connect(self.db_path)
        con.execute("create table if not exists records (id text primary key, resource text not null, data text not null, status text not null, created_at integer not null, updated_at integer not null)")
        con.execute("create index if not exists idx_records_resource on records(resource, updated_at desc)")
        con.execute("""
            create table if not exists app_users (
                id text primary key,
                email text not null unique,
                password_hash text,
                full_name text,
                role text not null default 'FACTORY_USER',
                department_id text,
                status text not null default 'Active',
                failed_login_count integer not null default 0,
                locked_until integer,
                last_login_at integer,
                created_at integer not null,
                updated_at integer not null
            )
        """)
        con.commit()
        con.close()

    def get_user_by_email(self, email: str):
        email = email.strip().lower()
        if self.mode == "supabase":
            response = self.client.table("app_users").select("*").eq("email", email).limit(1).execute()
            return response.data[0] if response.data else None
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        row = con.execute("select * from app_users where email = ? limit 1", (email,)).fetchone()
        con.close()
        return dict(row) if row else None

    def authenticate_user(self, email: str, password: str):
        email = email.strip().lower()
        if self.mode != "supabase":
            return None
        try:
            response = self.client.rpc("login_app_user", {"login_email": email, "login_password": password}).execute()
        except Exception:
            return None
        if not response.data:
            return None
        user = response.data[0] if isinstance(response.data, list) else response.data
        return {
            "email": user.get("email") or email,
            "name": user.get("full_name") or "FactoryPulse Admin",
            "role": user.get("role") or "FACTORY_ADMIN",
        }

    def record_login_success(self, email: str):
        email = email.strip().lower()
        now = int(time.time())
        if self.mode == "supabase":
            self.client.table("app_users").update({
                "failed_login_count": 0,
                "locked_until": None,
                "last_login_at": datetime.now(timezone.utc).isoformat(),
            }).eq("email", email).execute()
            return
        con = sqlite3.connect(self.db_path)
        con.execute("update app_users set failed_login_count = 0, locked_until = null, last_login_at = ?, updated_at = ? where email = ?", (now, now, email))
        con.commit()
        con.close()

    def record_login_failure(self, email: str, max_attempts: int = 5, lock_seconds: int = 900):
        email = email.strip().lower()
        now = int(time.time())
        user = self.get_user_by_email(email)
        if not user:
            return
        failed = int(user.get("failed_login_count") or 0) + 1
        locked_until = now + lock_seconds if failed >= max_attempts else user.get("locked_until")
        if self.mode == "supabase":
            self.client.table("app_users").update({
                "failed_login_count": failed,
                "locked_until": locked_until,
            }).eq("email", email).execute()
            return
        con = sqlite3.connect(self.db_path)
        con.execute("update app_users set failed_login_count = ?, locked_until = ?, updated_at = ? where email = ?", (failed, locked_until, now, email))
        con.commit()
        con.close()

    def list_records(self, resource: str, limit: int = 100):
        self._require_resource(resource)
        limit = min(max(int(limit), 1), 500)
        if self.mode == "supabase":
            try:
                response = self.client.table(resource).select("*").order("updated_at", desc=True).limit(limit).execute()
                return [self._normalize(row, resource) for row in response.data]
            except Exception:
                try:
                    response = self.client.table("records").select("*").eq("resource", resource).order("updated_at", desc=True).limit(limit).execute()
                    return [self._normalize(row, resource) for row in response.data]
                except Exception:
                    response = self.client.rpc("list_erp_records", {"api_secret": self.app_secret, "resource_name": resource, "row_limit": limit}).execute()
                    return [self._normalize(row, resource) for row in response.data]
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        rows = con.execute("select * from records where resource = ? order by updated_at desc limit ?", (resource, limit)).fetchall()
        con.close()
        return [self._normalize(dict(row), resource) for row in rows]

    def create_record(self, resource: str, payload: dict[str, Any]):
        fields = self._require_resource(resource)
        rejected = sorted(set(payload) - set(fields))
        if rejected:
            raise ValueError(f"Unknown fields: {', '.join(rejected)}")
        clean = {key: str(value).strip() for key, value in payload.items() if value is not None}
        self._validate_record(resource, clean)
        now = int(time.time())
        row = {"id": str(uuid.uuid4()), "resource": resource, "data": clean, "status": clean.get("status", "Open"), "created_at": now, "updated_at": now}
        if self.mode == "supabase":
            module_row = {key: clean.get(key, "") for key in fields if key != "status"}
            module_row["status"] = clean.get("status", "Open")
            try:
                response = self.client.table(resource).insert(module_row).execute()
                return self._normalize(response.data[0], resource)
            except Exception:
                try:
                    response = self.client.table("records").insert({
                        "resource": resource,
                        "data": clean,
                        "status": clean.get("status", "Open"),
                    }).execute()
                    return self._normalize(response.data[0], resource)
                except Exception as exc:
                    try:
                        response = self.client.rpc("create_erp_record", {"api_secret": self.app_secret, "resource_name": resource, "payload": clean}).execute()
                        return self._normalize(response.data[0], resource)
                    except Exception as rpc_exc:
                        raise ValueError("Supabase write is blocked. Run the secure_records_rpc.sql migration or configure a real service role key.") from rpc_exc
        con = sqlite3.connect(self.db_path)
        con.execute("insert into records values (?, ?, ?, ?, ?, ?)", (row["id"], resource, __import__("json").dumps(clean, sort_keys=True), row["status"], now, now))
        con.commit()
        con.close()
        return row

    def department(self, department_id: str):
        if department_id not in DEPARTMENTS:
            raise KeyError(department_id)
        dept = DEPARTMENTS[department_id]
        modules = []
        for resource in dept["modules"]:
            items = self.list_records(resource, 25)
            modules.append({"resource": resource, "label": resource.replace("_", " ").title(), "fields": MODULE_FIELDS[resource], "count": len(items), "items": items})
        return {"id": department_id, "name": dept["name"], "modules": modules}

    def dashboard(self):
        department_items = []
        total_records = 0
        total_modules = 0
        status_counts: dict[str, int] = {}
        priority_work = []
        for key, dept in DEPARTMENTS.items():
            module_summaries = []
            dept_count = 0
            for resource in dept["modules"]:
                items = self.list_records(resource, 50)
                total_modules += 1
                dept_count += len(items)
                for item in items:
                    status = item.get("status") or "Open"
                    status_counts[status] = status_counts.get(status, 0) + 1
                    if status in {"Critical", "Pending", "On Hold", "Open"} and len(priority_work) < 12:
                        data = item.get("data", {})
                        priority_work.append({
                            "department": dept["name"],
                            "resource": resource,
                            "title": data.get("title") or data.get("summary") or data.get("name") or data.get("project_code") or data.get("incident_no") or item.get("id"),
                            "status": status,
                        })
                module_summaries.append({"resource": resource, "label": resource.replace("_", " ").title(), "count": len(items)})
            total_records += dept_count
            department_items.append({
                "id": key,
                "name": dept["name"],
                "description": MODULE_DESCRIPTIONS.get(key, "Operational ERP workspace with validated records and live database storage."),
                "module_count": len(dept["modules"]),
                "record_count": dept_count,
                "modules": module_summaries,
            })
        return {
            "database": self.mode,
            "department_count": len(DEPARTMENTS),
            "module_count": total_modules,
            "record_count": total_records,
            "status_counts": status_counts,
            "departments": department_items,
            "priority_work": priority_work,
        }

    def _require_resource(self, resource: str):
        if resource not in MODULE_FIELDS:
            raise KeyError(resource)
        return MODULE_FIELDS[resource]

    def _validate_record(self, resource: str, data: dict[str, str]):
        missing = [field for field in REQUIRED_FIELDS.get(resource, []) if not data.get(field)]
        if missing:
            raise ValueError(f"Required fields missing: {', '.join(missing)}")
        status = data.get("status")
        if status and status not in STATUS_VALUES:
            raise ValueError(f"Status must be one of: {', '.join(sorted(STATUS_VALUES))}")
        for field, value in data.items():
            lowered = field.lower()
            if not value:
                continue
            if "email" in lowered and ("@" not in value or "." not in value.rsplit("@", 1)[-1]):
                raise ValueError(f"{field} must be a valid email address")
            words = set(lowered.split("_"))
            if words & NUMERIC_FIELD_WORDS:
                try:
                    number = float(value)
                except ValueError as exc:
                    raise ValueError(f"{field} must be numeric") from exc
                if "percent" in lowered and not 0 <= number <= 100:
                    raise ValueError(f"{field} must be between 0 and 100")
                if lowered == "ph" and not 0 <= number <= 14:
                    raise ValueError("ph must be between 0 and 14")
                if number < 0 and lowered not in {"variance"}:
                    raise ValueError(f"{field} cannot be negative")

    def _normalize(self, row: dict[str, Any], resource: str | None = None):
        resource = resource or row.get("resource")
        data = row.get("data", {})
        if isinstance(data, str):
            data = __import__("json").loads(data)
        if not data and resource in MODULE_FIELDS:
            data = {field: row.get(field, "") for field in MODULE_FIELDS[resource] if field != "status"}
        status = row.get("status", data.get("status", "Open"))
        data.setdefault("status", status)
        return {"id": row.get("id"), "resource": resource, "data": data, "status": status, "created_at": row.get("created_at"), "updated_at": row.get("updated_at")}

storage = Storage()
