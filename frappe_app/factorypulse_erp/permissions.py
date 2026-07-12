import frappe


def _tenant_field_exists(doctype: str) -> bool:
    meta = frappe.get_meta(doctype)
    return any(field.fieldname == "tenant_id" for field in meta.fields)


def tenant_permission_query(user=None):
    user = user or frappe.session.user
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return ""
    tenant_id = frappe.db.get_value("User", user, "default_company") or ""
    if not tenant_id:
        return "1 = 0"
    return f"`tabFactoryPulse Audit Event`.`tenant_id` = {frappe.db.escape(tenant_id)}"


def has_tenant_permission(doc, user=None, permission_type=None):
    user = user or frappe.session.user
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True
    tenant_id = frappe.db.get_value("User", user, "default_company") or ""
    return bool(tenant_id and getattr(doc, "tenant_id", None) == tenant_id)
