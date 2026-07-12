import frappe

ROLES = [
    "FactoryPulse Admin", "FactoryPulse HR Manager", "FactoryPulse Production Manager",
    "FactoryPulse Farmer Officer", "FactoryPulse Quality Manager", "FactoryPulse Maintenance Manager",
    "FactoryPulse Inventory Manager", "FactoryPulse Finance Manager", "FactoryPulse Employee"
]


def after_install():
    for role in ROLES:
        if not frappe.db.exists("Role", role):
            doc = frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1})
            doc.insert(ignore_permissions=True)
    frappe.db.commit()
