import frappe
from frappe.model.document import Document


class FactorypulseTasks(Document):
    def before_insert(self):
        if hasattr(self, "tenant_id") and not self.tenant_id:
            self.tenant_id = frappe.db.get_value("User", frappe.session.user, "default_company") or frappe.local.site
