import csv
import io
from typing import Any

import frappe
from frappe import _
from frappe.utils import now_datetime

RESOURCE_DOCTYPES = {
    "employees": "FactoryPulse Employees",
    "attendance": "FactoryPulse Attendance",
    "leave_requests": "FactoryPulse Leave",
    "shifts": "FactoryPulse Shifts",
    "departments": "FactoryPulse Departments",
    "farmers": "FactoryPulse Farmers",
    "cane_registrations": "FactoryPulse Cane Registration",
    "harvest_plans": "FactoryPulse Harvest Plans",
    "vehicles": "FactoryPulse Vehicles",
    "weighbridge_tickets": "FactoryPulse Weighbridge",
    "production_batches": "FactoryPulse Production",
    "quality_tests": "FactoryPulse Quality Lab",
    "maintenance_work_orders": "FactoryPulse Maintenance",
    "assets": "FactoryPulse Assets",
    "inventory_items": "FactoryPulse Inventory",
    "purchase_orders": "FactoryPulse Purchasing",
    "sales_orders": "FactoryPulse Sales",
    "invoices": "FactoryPulse Finance",
    "incidents": "FactoryPulse Safety",
    "tasks": "FactoryPulse Tasks",
    "approvals": "FactoryPulse Approvals",
    "payroll_runs": "FactoryPulse Payroll",
    "training_records": "FactoryPulse Training",
    "visitor_passes": "FactoryPulse Visitors",
    "documents": "FactoryPulse Documents",
    "dispatches": "FactoryPulse Dispatch",
    "warehouses": "FactoryPulse Warehouses",
    "power_generation": "FactoryPulse Power Plant",
    "distillery_batches": "FactoryPulse Distillery",
    "ethanol_dispatches": "FactoryPulse Ethanol",
    "byproducts": "FactoryPulse By-products",
    "boiler_logs": "FactoryPulse Boiler",
    "packaging_runs": "FactoryPulse Packaging",
    "support_tickets": "FactoryPulse Help Desk"
}

ROLE_RESOURCE_ACTIONS = {
    "PLATFORM_ADMIN": {
        "*": [
            "read",
            "create",
            "update",
            "delete",
            "admin"
        ]
    },
    "FACTORY_ADMIN": {
        "*": [
            "read",
            "create",
            "update",
            "delete"
        ]
    },
    "HR_MANAGER": {
        "employees": [
            "read",
            "create",
            "update"
        ],
        "attendance": [
            "read",
            "create",
            "update"
        ],
        "leave_requests": [
            "read",
            "create",
            "update"
        ],
        "shifts": [
            "read",
            "create",
            "update"
        ],
        "departments": [
            "read"
        ],
        "payroll_runs": [
            "read",
            "create",
            "update"
        ],
        "training_records": [
            "read",
            "create",
            "update"
        ],
        "visitor_passes": [
            "read",
            "create",
            "update"
        ],
        "documents": [
            "read",
            "create",
            "update"
        ],
        "approvals": [
            "read",
            "update"
        ],
        "tasks": [
            "read",
            "create",
            "update"
        ]
    },
    "PRODUCTION_MANAGER": {
        "production_batches": [
            "read",
            "create",
            "update"
        ],
        "weighbridge_tickets": [
            "read",
            "update"
        ],
        "quality_tests": [
            "read"
        ],
        "harvest_plans": [
            "read",
            "update"
        ],
        "power_generation": [
            "read",
            "create",
            "update"
        ],
        "distillery_batches": [
            "read",
            "create",
            "update"
        ],
        "byproducts": [
            "read",
            "create",
            "update"
        ],
        "boiler_logs": [
            "read",
            "create",
            "update"
        ],
        "packaging_runs": [
            "read",
            "create",
            "update"
        ],
        "dispatches": [
            "read",
            "update"
        ],
        "tasks": [
            "read",
            "create",
            "update"
        ],
        "incidents": [
            "read",
            "create"
        ]
    },
    "FARMER_OFFICER": {
        "farmers": [
            "read",
            "create",
            "update"
        ],
        "cane_registrations": [
            "read",
            "create",
            "update"
        ],
        "harvest_plans": [
            "read",
            "create",
            "update"
        ],
        "vehicles": [
            "read"
        ],
        "weighbridge_tickets": [
            "read"
        ]
    },
    "QUALITY_MANAGER": {
        "quality_tests": [
            "read",
            "create",
            "update"
        ],
        "weighbridge_tickets": [
            "read"
        ],
        "production_batches": [
            "read"
        ],
        "incidents": [
            "read",
            "create"
        ]
    },
    "MAINTENANCE_MANAGER": {
        "assets": [
            "read",
            "create",
            "update"
        ],
        "maintenance_work_orders": [
            "read",
            "create",
            "update"
        ],
        "inventory_items": [
            "read"
        ],
        "tasks": [
            "read",
            "create",
            "update"
        ],
        "incidents": [
            "read",
            "create"
        ]
    },
    "INVENTORY_MANAGER": {
        "inventory_items": [
            "read",
            "create",
            "update"
        ],
        "warehouses": [
            "read",
            "create",
            "update"
        ],
        "dispatches": [
            "read",
            "create",
            "update"
        ],
        "purchase_orders": [
            "read",
            "create",
            "update"
        ],
        "sales_orders": [
            "read"
        ],
        "assets": [
            "read"
        ]
    },
    "FINANCE_MANAGER": {
        "purchase_orders": [
            "read",
            "update"
        ],
        "sales_orders": [
            "read",
            "create",
            "update"
        ],
        "invoices": [
            "read",
            "create",
            "update"
        ],
        "payroll_runs": [
            "read",
            "update"
        ],
        "ethanol_dispatches": [
            "read",
            "create",
            "update"
        ],
        "approvals": [
            "read",
            "update"
        ]
    },
    "EMPLOYEE": {
        "employees": [
            "read"
        ],
        "attendance": [
            "read",
            "create"
        ],
        "leave_requests": [
            "read",
            "create"
        ],
        "training_records": [
            "read"
        ],
        "documents": [
            "read"
        ],
        "visitor_passes": [
            "read",
            "create"
        ],
        "support_tickets": [
            "read",
            "create"
        ],
        "tasks": [
            "read",
            "update"
        ],
        "incidents": [
            "read",
            "create"
        ],
        "approvals": [
            "read"
        ]
    }
}


class FactoryPulsePermissionError(frappe.PermissionError):
    pass


def _resource_doctype(resource: str) -> str:
    if resource not in RESOURCE_DOCTYPES:
        frappe.throw(_("Unknown FactoryPulse resource"), frappe.DoesNotExistError)
    return RESOURCE_DOCTYPES[resource]


def _require(resource: str, action: str):
    doctype = _resource_doctype(resource)
    if not frappe.has_permission(doctype, ptype=action):
        raise FactoryPulsePermissionError(_("Not permitted"))
    return doctype


@frappe.whitelist(methods=["GET"])
def catalog() -> dict[str, Any]:
    resources = {}
    for resource, doctype in RESOURCE_DOCTYPES.items():
        if frappe.has_permission(doctype, ptype="read"):
            meta = frappe.get_meta(doctype)
            resources[resource] = {
                "doctype": doctype,
                "label": meta.name.replace("FactoryPulse ", ""),
                "fields": [df.fieldname for df in meta.fields if df.fieldtype not in {"Section Break", "Column Break"}],
            }
    return {"resources": resources}


@frappe.whitelist(methods=["GET"])
def list_records(resource: str, limit: int = 100) -> dict[str, Any]:
    doctype = _require(resource, "read")
    limit = min(max(int(limit), 1), 500)
    fields = ["name", "modified"] + [df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldtype not in {"Section Break", "Column Break"}]
    rows = frappe.get_all(doctype, fields=fields, limit_page_length=limit, order_by="modified desc")
    return {"items": rows}


@frappe.whitelist(methods=["POST"])
def create_record(resource: str, data: dict[str, Any] | None = None, idempotency_key: str | None = None) -> dict[str, Any]:
    doctype = _require(resource, "create")
    if idempotency_key:
        existing = frappe.db.get_value("FactoryPulse Idempotency Key", {"key": idempotency_key, "owner_user": frappe.session.user}, "response_json")
        if existing:
            return frappe.parse_json(existing)
    data = data or frappe.form_dict.get("data") or {}
    allowed = {df.fieldname for df in frappe.get_meta(doctype).fields if df.fieldtype not in {"Section Break", "Column Break"}}
    rejected = sorted(set(data) - allowed)
    if rejected:
        frappe.throw(_("Unknown fields: {0}").format(", ".join(rejected)), frappe.ValidationError)
    doc = frappe.get_doc({"doctype": doctype, **data})
    doc.insert()
    response = {"item": doc.as_dict()}
    if idempotency_key:
        frappe.get_doc({
            "doctype": "FactoryPulse Idempotency Key",
            "key": idempotency_key,
            "owner_user": frappe.session.user,
            "response_json": frappe.as_json(response),
        }).insert(ignore_permissions=True)
    _audit("create", doctype, doc.name, {"resource": resource})
    return response


@frappe.whitelist(methods=["GET"])
def operations_summary() -> dict[str, Any]:
    def latest(resource: str, field: str, default: str = "0") -> str:
        doctype = _resource_doctype(resource)
        if not frappe.has_permission(doctype, ptype="read"):
            return default
        rows = frappe.get_all(doctype, fields=[field], limit_page_length=1, order_by="modified desc")
        return str(rows[0].get(field, default)) if rows else default
    return {
        "cane_crushed_ton": latest("production_batches", "cane_crushed_ton"),
        "recovery_percent": latest("production_batches", "recovery_percent"),
        "power_generation_kwh": latest("power_generation", "generation_kwh"),
        "sugar_bags": latest("production_batches", "sugar_bags"),
        "generated_at": now_datetime(),
    }


@frappe.whitelist(methods=["GET"])
def export_csv(resource: str) -> str:
    doctype = _require(resource, "read")
    meta = frappe.get_meta(doctype)
    fields = [df.fieldname for df in meta.fields if df.fieldtype not in {"Section Break", "Column Break"}]
    rows = frappe.get_all(doctype, fields=["name", *fields], limit_page_length=500)
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["name", *fields], extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    frappe.local.response.filename = f"{resource}.csv"
    frappe.local.response.filecontent = output.getvalue()
    frappe.local.response.type = "download"
    return output.getvalue()


@frappe.whitelist(methods=["GET"])
def secure_search(q: str, limit: int = 50) -> dict[str, Any]:
    q = (q or "").strip()
    if len(q) < 2:
        frappe.throw(_("Search query must be at least 2 characters"), frappe.ValidationError)
    results = []
    limit = min(max(int(limit), 1), 100)
    for resource, doctype in RESOURCE_DOCTYPES.items():
        if not frappe.has_permission(doctype, ptype="read"):
            continue
        meta = frappe.get_meta(doctype)
        fields = [df.fieldname for df in meta.fields if df.fieldtype in {"Data", "Small Text", "Text", "Select"}]
        filters = []
        for field in fields[:8]:
            filters.append([doctype, field, "like", f"%{q}%"])
        # Frappe get_list OR filters vary by version; keep this conservative.
        rows = frappe.get_all(doctype, fields=["name", *fields[:4]], limit_page_length=20, order_by="modified desc")
        for row in rows:
            if q.lower() in frappe.as_json(row).lower():
                results.append({"resource": resource, "doctype": doctype, "item": row})
                if len(results) >= limit:
                    return {"items": results}
    return {"items": results}


def create_daily_operations_snapshot():
    # Hook target for scheduler. Real deployments can extend this to persist a KPI DocType.
    frappe.logger("factorypulse_erp").info("FactoryPulse daily operations snapshot executed")


def _audit(action: str, resource: str, target: str, metadata: dict[str, Any]):
    if frappe.db.exists("DocType", "FactoryPulse Audit Event"):
        frappe.get_doc({
            "doctype": "FactoryPulse Audit Event",
            "action": action,
            "resource": resource,
            "target_id": target,
            "actor": frappe.session.user,
            "metadata_json": frappe.as_json(metadata),
        }).insert(ignore_permissions=True)


@frappe.whitelist(methods=["GET"])
def mobile_home() -> dict[str, Any]:
    return {
        "catalog": catalog(),
        "attendance": list_records("attendance", 5).get("items", []),
        "tasks": list_records("tasks", 5).get("items", []),
        "leave_requests": list_records("leave_requests", 5).get("items", []),
        "training_records": list_records("training_records", 5).get("items", []),
        "documents": list_records("documents", 5).get("items", []),
    }


@frappe.whitelist(methods=["POST"])
def mobile_check_in(data: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = data or frappe.form_dict.get("data") or {}
    return create_record("attendance", {
        "employee_code": payload.get("employee_code") or frappe.session.user,
        "date": payload.get("date") or now_datetime().date().isoformat(),
        "shift": payload.get("shift") or "General",
        "check_in": payload.get("check_in") or now_datetime().strftime("%H:%M"),
        "check_out": payload.get("check_out") or "",
        "gps_area": payload.get("gps_area") or "Factory Gate",
        "status": "Checked In",
    })


@frappe.whitelist(methods=["POST"])
def mobile_leave_request(data: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = data or frappe.form_dict.get("data") or {}
    return create_record("leave_requests", {
        "employee_code": payload.get("employee_code") or frappe.session.user,
        "leave_type": payload.get("leave_type") or "Casual Leave",
        "from_date": payload.get("from_date") or now_datetime().date().isoformat(),
        "to_date": payload.get("to_date") or payload.get("from_date") or now_datetime().date().isoformat(),
        "reason": payload.get("reason") or "Requested from employee app",
        "status": "Pending",
    })


@frappe.whitelist(methods=["POST"])
def mobile_incident(data: dict[str, Any] | None = None, sos: bool = False) -> dict[str, Any]:
    payload = data or frappe.form_dict.get("data") or {}
    return create_record("incidents", {
        "incident_no": payload.get("incident_no") or f"MOB-{frappe.generate_hash(length=8)}",
        "area": payload.get("area") or "Factory",
        "severity": "Critical" if sos else payload.get("severity") or "Medium",
        "reported_by": payload.get("reported_by") or frappe.session.user,
        "summary": payload.get("summary") or ("Emergency SOS raised from employee app" if sos else "Incident reported from employee app"),
        "corrective_action": payload.get("corrective_action") or "Supervisor review required",
        "status": "Open",
    })


@frappe.whitelist(methods=["POST"])
def mobile_sos(data: dict[str, Any] | None = None) -> dict[str, Any]:
    return mobile_incident(data=data, sos=True)
