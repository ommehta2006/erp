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
    "hr": {"name": "HR & Employee", "modules": ["employees", "attendance", "attendance_policies", "employee_locations", "leave_requests", "leave_balances", "holiday_calendar", "salary_slips", "shifts", "departments", "payroll_runs", "recruitment", "performance_reviews", "training_records", "expense_claims", "visitor_passes"]},
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
    "attendance_policies": ["policy_name", "late_after_time", "grace_minutes", "tracking_interval_minutes", "background_location_required", "status"],
    "employee_locations": ["employee_code", "timestamp", "latitude", "longitude", "accuracy", "event", "status"],
    "leave_requests": ["employee_code", "leave_type", "from_date", "to_date", "reason", "status"],
    "leave_balances": ["employee_code", "leave_type", "opening_balance", "used_days", "available_days", "period", "status"],
    "holiday_calendar": ["holiday_no", "date", "name", "holiday_type", "location", "status"],
    "salary_slips": ["employee_code", "period", "gross_pay", "deductions", "net_pay", "payment_date", "status"],
    "shifts": ["name", "shift_type", "start_time", "end_time", "cross_midnight", "day_in_open_time", "day_in_close_time", "day_out_open_time", "day_out_close_time", "grace_minutes", "minimum_full_day_minutes", "minimum_half_day_minutes", "break_minutes", "auto_break_deduction", "overtime_eligible", "overtime_approval_required", "early_exit_grace_minutes", "late_mark_after_minutes", "maximum_late_marks", "weekly_working_days", "weekly_offs", "applicable_locations", "applicable_departments", "applicable_employees", "effective_start_date", "effective_end_date", "department", "supervisor", "status"],
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

EXPERT_HR_MODULES = {
    "companies": ["company_code", "name", "country", "tax_id", "status"],
    "branches": ["branch_code", "company", "name", "city", "state", "status"],
    "designations": ["designation_code", "department", "title", "grade", "status"],
    "employee_private_details": ["employee_code", "date_of_birth", "gender", "nationality", "tax_identifier_ref", "status"],
    "employee_bank_details": ["employee_code", "bank_name", "account_last4", "ifsc_or_routing", "verification_status", "status"],
    "employee_documents": ["employee_code", "document_type", "document_no_masked", "expiry_date", "verification_status", "status"],
    "employee_emergency_contacts": ["employee_code", "contact_name", "relationship", "phone", "address", "status"],
    "employee_lifecycle_events": ["event_no", "employee_code", "event_type", "effective_date", "previous_value", "new_value", "reason", "approved_by", "status"],
    "work_locations": ["location_id", "company", "branch", "location_name", "location_type", "full_address", "city", "state", "country", "latitude", "longitude", "geofence_type", "geofence_radius_meters", "allowed_gps_accuracy_meters", "time_zone", "approval_status", "status"],
    "geofences": ["geofence_id", "location_id", "geofence_type", "center_latitude", "center_longitude", "radius_meters", "polygon_coordinates", "allowed_accuracy_meters", "boundary_version", "effective_start_date", "effective_end_date", "approval_status", "status"],
    "geofence_versions": ["version_id", "geofence_id", "boundary_version", "change_summary", "changed_by", "approved_by", "effective_date", "status"],
    "geofence_polygon_points": ["point_id", "geofence_id", "boundary_version", "point_order", "latitude", "longitude", "status"],
    "employee_location_assignments": ["assignment_id", "employee_code", "location_id", "shift", "effective_start_date", "effective_end_date", "assignment_type", "approval_status", "status"],
    "employee_shift_assignments": ["assignment_id", "employee_code", "shift", "shift_type", "effective_start_date", "effective_end_date", "assignment_reason", "approved_by", "approval_status", "status"],
    "shift_rosters": ["roster_id", "employee_code", "shift", "roster_date", "location_id", "planned_start_time", "planned_end_time", "roster_type", "published_status", "approval_status", "status"],
    "attendance_records": ["attendance_record_id", "employee_code", "employee_name", "department", "designation", "company", "branch", "work_location", "shift", "attendance_date", "day_in_time", "day_out_time", "day_in_latitude", "day_in_longitude", "day_out_latitude", "day_out_longitude", "day_in_accuracy", "day_out_accuracy", "day_in_distance", "day_out_distance", "day_in_geofence_status", "day_out_geofence_status", "day_in_biometric_result", "day_out_biometric_result", "late_duration_minutes", "early_exit_minutes", "gross_work_minutes", "net_work_minutes", "overtime_minutes", "attendance_status", "payroll_status", "approval_status", "employee_remarks", "hr_remarks", "source", "status"],
    "attendance_location_events": ["event_id", "attendance_record_id", "employee_code", "event_type", "latitude", "longitude", "accuracy", "altitude", "speed", "provider", "captured_at", "received_at", "device_time", "server_time", "geofence_id", "geofence_version", "distance_meters", "inside_fence", "tolerance_applied", "mock_location_indicator", "risk_score", "validation_result", "failure_reason", "device_id", "ip_address", "app_version", "status"],
    "attendance_biometric_events": ["event_id", "attendance_record_id", "employee_code", "event_type", "verification_method", "verification_result", "assertion_reference", "trusted_device_id", "failure_reason", "risk_flags", "verified_at", "status"],
    "employee_biometric_enrollments": ["enrollment_id", "employee_code", "verification_method", "trusted_device_id", "assertion_reference", "enrolled_at", "privacy_notice", "approval_status", "status"],
    "attendance_validation_results": ["validation_id", "employee_code", "event_type", "location_id", "geofence_id", "employee_latitude", "employee_longitude", "geofence_latitude", "geofence_longitude", "distance_meters", "radius_meters", "inside_fence", "accuracy_meters", "allowed_accuracy_meters", "geofence_status", "validation_reason", "risk_flags", "server_validated_at", "status"],
    "attendance_correction_requests": ["request_id", "employee_code", "attendance_date", "requested_day_in_time", "requested_day_out_time", "reason", "current_record", "requested_changes", "manager_approval", "hr_approval", "final_status", "status"],
    "attendance_approvals": ["approval_id", "attendance_record_id", "employee_code", "approval_type", "approver", "decision", "comments", "decided_at", "status"],
    "device_registrations": ["device_id", "employee_code", "platform", "device_name", "app_version", "restricted_device", "registered_at", "approval_status", "status"],
    "device_integrity_events": ["event_id", "employee_code", "device_id", "signal_type", "risk_score", "risk_flags", "observed_at", "status"],
    "leave_types": ["leave_type", "paid_status", "requires_attachment", "allow_half_day", "allow_hourly", "status"],
    "leave_policies": ["policy_name", "leave_type", "accrual_rule", "carry_forward_rule", "negative_balance_allowed", "approval_levels", "payroll_impact", "status"],
    "leave_allocations": ["allocation_id", "employee_code", "leave_type", "period", "allocated_days", "used_days", "available_days", "expiry_date", "status"],
    "leave_applications": ["application_id", "employee_code", "leave_type", "start_date", "end_date", "half_day", "total_leave_days", "reason", "approver", "approval_status", "payroll_impact", "status"],
    "leave_approvals": ["approval_id", "application_id", "approver", "decision", "remarks", "decided_at", "status"],
    "holiday_calendars": ["calendar_id", "company", "country", "state", "branch", "location_id", "effective_year", "status"],
    "holidays": ["holiday_id", "calendar_id", "holiday_name", "holiday_date", "holiday_type", "paid_status", "optional_or_mandatory", "payroll_impact", "notes", "status"],
    "salary_structures": ["structure_id", "structure_name", "currency", "payment_frequency", "proration_method", "basic_salary", "allowances", "deductions", "employer_contributions", "employee_contributions", "gross_salary", "ctc", "net_salary_estimate", "approval_status", "status"],
    "salary_structure_components": ["component_id", "structure_id", "component_name", "component_type", "calculation_method", "amount", "percentage_of", "taxable", "payroll_impact", "status"],
    "employee_salary_assignments": ["assignment_id", "employee_code", "structure_id", "effective_date", "basic_salary", "allowances", "deductions", "employer_contributions", "employee_contributions", "gross_salary", "ctc", "net_salary_estimate", "currency", "payment_frequency", "approval_status", "status"],
    "salary_revision_history": ["revision_id", "employee_code", "structure_id", "effective_date", "basic_salary", "allowances", "deductions", "gross_salary", "ctc", "net_salary_estimate", "revision_type", "previous_salary", "new_salary", "increase_amount", "increase_percent", "reason", "supporting_document", "requested_by", "approved_by", "approval_status", "created_time", "status"],
    "payroll_periods": ["period_id", "period_name", "start_date", "end_date", "company", "branch", "attendance_close_status", "payroll_status", "status"],
    "payroll_policies": ["policy_id", "policy_name", "proration_method", "fixed_divisor", "rounding_rule", "max_adjustment_amount", "role_adjustment_limits", "retroactive_months_allowed", "approval_required", "lock_after_approval", "allow_reversal_after_lock", "adjustment_categories", "statutory_notes", "effective_start_date", "effective_end_date", "created_by", "updated_by", "approval_status", "status"],
    "payroll_statutory_rules": ["rule_id", "rule_name", "component_name", "deduction_type", "calculation_base", "rate_percent", "fixed_amount", "monthly_cap", "annual_exemption", "employee_min_gross", "employee_max_gross", "slab_config", "jurisdiction", "employer_contribution", "employee_contribution", "effective_start_date", "effective_end_date", "created_by", "approved_by", "approval_status", "status"],
    "payroll_employee_results": ["result_id", "payroll_run", "employee_code", "paid_days", "present_days", "paid_leave_days", "unpaid_leave_days", "gross_pay", "deductions", "net_pay", "validation_status", "status"],
    "payroll_calculation_lines": ["line_id", "result_id", "component_name", "component_type", "quantity", "rate", "amount", "formula", "source", "status"],
    "payroll_adjustments": ["adjustment_id", "employee_code", "payroll_month", "adjustment_type", "addition_or_deduction", "amount", "calculation_method", "quantity", "rate", "reason", "policy_reference", "supporting_attachment", "requested_by", "approval_status", "approved_by", "rejected_by", "approval_remarks", "payroll_inclusion_status", "limit_check", "duplicate_key", "reversal_of", "created_time", "updated_time", "status"],
    "payroll_approvals": ["approval_id", "payroll_run", "approver", "decision", "remarks", "decided_at", "status"],
    "payment_batches": ["batch_id", "payroll_run", "payment_date", "payment_method", "total_amount", "bank_file_reference", "payment_status", "status"],
    "notifications": ["notification_id", "recipient_employee_code", "recipient_email", "notification_type", "title", "message", "read_status", "delivery_status", "status"],
    "attachments": ["attachment_id", "entity_type", "entity_id", "file_name", "storage_path", "content_type", "uploaded_by", "status"],
    "audit_logs": ["audit_id", "actor", "action", "entity_type", "entity_id", "previous_values", "new_values", "reason", "ip_address", "device_info", "approval_reference", "status"],
}

MODULE_FIELDS.update(EXPERT_HR_MODULES)
DEPARTMENTS["hr"]["modules"] = [
    "employees", "employee_private_details", "employee_bank_details", "employee_documents", "employee_emergency_contacts",
    "employee_lifecycle_events", "work_locations", "geofences", "geofence_versions", "geofence_polygon_points",
    "employee_location_assignments", "employee_shift_assignments", "shifts", "shift_rosters", "attendance_policies",
    "attendance_records", "attendance_location_events", "attendance_biometric_events", "attendance_validation_results",
    "employee_biometric_enrollments",
    "attendance_correction_requests", "attendance_approvals", "leave_types", "leave_policies", "leave_allocations",
    "leave_balances", "leave_applications", "leave_approvals", "leave_requests", "holiday_calendars", "holidays",
    "holiday_calendar", "salary_structures", "employee_salary_assignments", "salary_revision_history", "salary_slips",
    "departments", "designations", "performance_reviews", "training_records", "recruitment", "visitor_passes",
]
DEPARTMENTS["finance"]["modules"] = [
    "payroll_periods", "payroll_policies", "payroll_runs", "payroll_employee_results", "payroll_calculation_lines", "payroll_adjustments",
    "payroll_approvals", "payroll_statutory_rules", "payment_batches", "salary_structures", "salary_structure_components", "salary_slips",
    "invoices", "purchase_orders", "sales_orders", "budgets", "tax_records", "farmer_payments", "expense_claims", "approvals",
]
DEPARTMENTS["admin"]["modules"] = [
    "approvals", "notifications", "attachments", "audit_logs", "documents", "tasks", "support_tickets",
    "device_registrations", "device_integrity_events", "incidents",
]

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

STATUS_VALUES = {
    "Open", "Active", "Inactive", "Pending", "Approved", "Rejected", "Completed", "Closed", "On Hold", "Critical",
    "Draft", "Locked", "Payment Processing", "Partially Paid", "Paid", "Cancelled", "Reversed", "Expired", "Encashed", "Present", "Absent", "Half Day", "Late", "Early Exit",
    "Overtime", "Out of Fence", "Pending Approval", "Attendance Corrected", "Failed", "Passed",
}
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
    "distance",
    "export",
    "feed",
    "generation",
    "gross",
    "hours",
    "intensity",
    "kl",
    "kwh",
    "latitude",
    "level",
    "litres",
    "longitude",
    "minutes",
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
    "radius",
    "rate",
    "reading",
    "recovery",
    "score",
    "spent",
    "speed",
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

    def list_users(self, limit: int = 200):
        limit = min(max(int(limit), 1), 500)
        if self.mode == "supabase":
            response = self.client.table("app_users").select("id,email,full_name,role,department_id,status,failed_login_count,locked_until,last_login_at,created_at,updated_at").limit(limit).execute()
            return response.data
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        rows = con.execute("select id,email,full_name,role,department_id,status,failed_login_count,locked_until,last_login_at,created_at,updated_at from app_users order by updated_at desc limit ?", (limit,)).fetchall()
        con.close()
        return [dict(row) for row in rows]

    def create_user(self, payload: dict[str, Any]):
        email = str(payload.get("email", "")).strip().lower()
        if not email:
            raise ValueError("email is required")
        now = int(time.time())
        row = {
            "id": str(uuid.uuid4()),
            "email": email,
            "password_hash": payload.get("password_hash"),
            "full_name": payload.get("full_name", ""),
            "role": payload.get("role", "FACTORY_USER"),
            "department_id": payload.get("department_id", ""),
            "status": payload.get("status", "Active"),
            "failed_login_count": 0,
            "locked_until": None,
            "last_login_at": None,
            "created_at": now,
            "updated_at": now,
        }
        if self.mode == "supabase":
            response = self.client.table("app_users").insert({
                "email": row["email"],
                "password_hash": row["password_hash"],
                "full_name": row["full_name"],
                "role": row["role"],
                "department_id": row["department_id"] or None,
                "status": row["status"],
            }).execute()
            return response.data[0]
        con = sqlite3.connect(self.db_path)
        con.execute(
            "insert into app_users (id,email,password_hash,full_name,role,department_id,status,failed_login_count,locked_until,last_login_at,created_at,updated_at) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (row["id"], row["email"], row["password_hash"], row["full_name"], row["role"], row["department_id"], row["status"], row["failed_login_count"], row["locked_until"], row["last_login_at"], row["created_at"], row["updated_at"]),
        )
        con.commit()
        con.close()
        clean = dict(row)
        clean.pop("password_hash", None)
        return clean

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

    def update_record(self, resource: str, record_id: str, payload: dict[str, Any]):
        fields = self._require_resource(resource)
        rejected = sorted(set(payload) - set(fields))
        if rejected:
            raise ValueError(f"Unknown fields: {', '.join(rejected)}")
        clean = {key: str(value).strip() for key, value in payload.items() if value is not None}
        if not clean:
            raise ValueError("No fields to update")
        now = int(time.time())
        if self.mode == "supabase":
            module_update = {key: clean[key] for key in clean if key != "status"}
            if "status" in clean:
                module_update["status"] = clean["status"]
            try:
                response = self.client.table(resource).update(module_update).eq("id", record_id).execute()
                if response.data:
                    return self._normalize(response.data[0], resource)
            except Exception:
                pass
            try:
                current = self.client.table("records").select("*").eq("id", record_id).limit(1).execute()
                if not current.data:
                    raise ValueError("Record not found")
                merged = self._normalize(current.data[0], resource)["data"]
                merged.update(clean)
                response = self.client.table("records").update({
                    "data": merged,
                    "status": merged.get("status", clean.get("status", "Open")),
                }).eq("id", record_id).execute()
                return self._normalize(response.data[0], resource)
            except Exception as exc:
                raise ValueError("Supabase update is blocked or record was not found.") from exc
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        row = con.execute("select * from records where id = ? and resource = ?", (record_id, resource)).fetchone()
        if not row:
            con.close()
            raise ValueError("Record not found")
        data = __import__("json").loads(row["data"])
        data.update(clean)
        status = data.get("status", row["status"])
        con.execute(
            "update records set data = ?, status = ?, updated_at = ? where id = ? and resource = ?",
            (__import__("json").dumps(data, sort_keys=True), status, now, record_id, resource),
        )
        con.commit()
        updated = con.execute("select * from records where id = ? and resource = ?", (record_id, resource)).fetchone()
        con.close()
        return self._normalize(dict(updated), resource)

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
