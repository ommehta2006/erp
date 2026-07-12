app_name = "factorypulse_erp"
app_title = "FactoryPulse ERP"
app_publisher = "FactoryPulse Delivery Team"
app_description = "Secure sugar factory ERP and employee operations custom app"
app_email = "admin@example.invalid"
app_license = "Proprietary"

required_apps = ["frappe"]
after_install = "factorypulse_erp.install.after_install"
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "FactoryPulse Admin", "FactoryPulse HR Manager", "FactoryPulse Production Manager",
        "FactoryPulse Farmer Officer", "FactoryPulse Quality Manager", "FactoryPulse Maintenance Manager",
        "FactoryPulse Inventory Manager", "FactoryPulse Finance Manager", "FactoryPulse Employee"
    ]]]},
]
scheduler_events = {
    "daily": ["factorypulse_erp.api.create_daily_operations_snapshot"]
}
permission_query_conditions = {
    "FactoryPulse Audit Event": "factorypulse_erp.permissions.tenant_permission_query"
}
has_permission = {
    "FactoryPulse Audit Event": "factorypulse_erp.permissions.has_tenant_permission"
}
