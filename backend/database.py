import os
import sqlite3
import time
import uuid
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
    "hr": {"name": "HR & Employee", "modules": ["employees", "attendance", "leave_requests", "shifts", "departments", "payroll_runs", "recruitment", "performance_reviews", "training_records", "expense_claims", "visitor_passes"]},
    "finance": {"name": "Finance & Accounts", "modules": ["invoices", "purchase_orders", "sales_orders", "payroll_runs", "budgets", "tax_records", "farmer_payments", "approvals"]},
    "cane": {"name": "Cane & Farmer", "modules": ["farmers", "cane_registrations", "harvest_plans", "vehicles", "weighbridge_tickets", "farmer_payments"]},
    "manufacturing": {"name": "Manufacturing", "modules": ["production_batches", "boiler_logs", "packaging_runs", "byproducts", "power_generation", "distillery_batches", "ethanol_dispatches", "energy_meters"]},
    "inventory": {"name": "Inventory & Dispatch", "modules": ["inventory_items", "warehouses", "dispatches", "assets", "purchase_orders"]},
    "quality": {"name": "Quality & Compliance", "modules": ["quality_tests", "lab_instruments", "compliance_register", "documents", "incidents"]},
    "maintenance": {"name": "Maintenance & Assets", "modules": ["maintenance_work_orders", "assets", "tasks", "support_tickets"]},
    "sales": {"name": "Sales & Customer", "modules": ["sales_orders", "dispatches", "invoices", "customer_portal_requests"]},
    "admin": {"name": "Administration", "modules": ["approvals", "documents", "tasks", "support_tickets", "incidents"]},
}

MODULE_FIELDS = {
    "employees": ["employee_code", "full_name", "department", "role", "phone", "email", "shift", "status"],
    "attendance": ["employee_code", "date", "shift", "check_in", "check_out", "gps_area", "status"],
    "leave_requests": ["employee_code", "leave_type", "from_date", "to_date", "reason", "status"],
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
        con.commit()
        con.close()

    def list_records(self, resource: str, limit: int = 100):
        self._require_resource(resource)
        limit = min(max(int(limit), 1), 500)
        if self.mode == "supabase":
            response = self.client.table(resource).select("*").order("updated_at", desc=True).limit(limit).execute()
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
        now = int(time.time())
        row = {"id": str(uuid.uuid4()), "resource": resource, "data": clean, "status": clean.get("status", "Open"), "created_at": now, "updated_at": now}
        if self.mode == "supabase":
            module_row = {key: clean.get(key, "") for key in fields if key != "status"}
            module_row["status"] = clean.get("status", "Open")
            response = self.client.table(resource).insert(module_row).execute()
            return self._normalize(response.data[0], resource)
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

    def _require_resource(self, resource: str):
        if resource not in MODULE_FIELDS:
            raise KeyError(resource)
        return MODULE_FIELDS[resource]

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
