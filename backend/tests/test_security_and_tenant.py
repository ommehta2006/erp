import os
import tempfile
import unittest

from backend.factory_erp.security import SecurityError, hash_password, sign_token, verify_password, verify_token
from backend.factory_erp.store import DataStore, PermissionDenied


class SecurityAndTenantTests(unittest.TestCase):
    def test_password_hash_uses_salt_and_verifies(self):
        stored = hash_password("Correct-Horse-2026!")
        self.assertTrue(verify_password("Correct-Horse-2026!", stored))
        self.assertFalse(verify_password("wrong-password", stored))
        self.assertNotIn("Correct-Horse", stored)

    def test_token_signature_and_expiry_are_enforced(self):
        token = sign_token({"sub": "user-1", "tenant_id": "tenant-1"}, "secret", 60)
        self.assertEqual(verify_token(token, "secret")["sub"], "user-1")
        with self.assertRaises(SecurityError):
            verify_token(token + "x", "secret")

    def test_role_cannot_write_unpermitted_resource(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["APP_DATABASE"] = os.path.join(tmp, "app.sqlite3")
            store = DataStore(os.environ["APP_DATABASE"])
            try:
                user = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                employee = dict(user)
                employee["role"] = "EMPLOYEE"
                with self.assertRaises(PermissionDenied):
                    store.create_record(employee, "invoices", {"invoice_no": "INV-1", "amount": "10"})
            finally:
                store.close()

    def test_tenant_filter_blocks_cross_tenant_record_lookup(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(os.path.join(tmp, "app.sqlite3"))
            try:
                user = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                item = store.create_record(user, "tasks", {"title": "Tenant A task", "owner": "EMP-1", "status": "Open"})
                other = dict(user)
                other["tenant_id"] = "not-the-same-tenant"
                with self.assertRaises(Exception):
                    store.get_record(other, "tasks", item["id"])
            finally:
                store.close()

    def test_admin_can_create_user_without_exposing_password_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(os.path.join(tmp, "app.sqlite3"))
            try:
                admin = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                created = store.create_user(admin, {
                    "email": "employee.one@example.invalid",
                    "name": "Employee One",
                    "role": "EMPLOYEE",
                    "password": "Employee-One-2026!",
                })
                self.assertEqual(created["role"], "EMPLOYEE")
                self.assertNotIn("password", created)
                self.assertNotIn("password_hash", created)
                users = store.list_users(admin)
                self.assertTrue(any(u["email"] == "employee.one@example.invalid" for u in users))
            finally:
                store.close()

    def test_search_only_returns_visible_tenant_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(os.path.join(tmp, "app.sqlite3"))
            try:
                admin = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                results = store.search_records(admin, "boiler")
                self.assertTrue(any(r["resource"] in {"incidents", "boiler_logs", "documents"} for r in results))
                employee = dict(admin)
                employee["role"] = "EMPLOYEE"
                employee_results = store.search_records(employee, "invoice")
                self.assertEqual(employee_results, [])
            finally:
                store.close()

    def test_idempotency_replays_stored_response_for_actor_and_tenant(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(os.path.join(tmp, "app.sqlite3"))
            try:
                admin = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                response = {"item": store.create_record(admin, "tasks", {"title": "Calibrate scanner", "owner": "EMP-1001", "status": "Open"})}
                store.save_idempotency(admin, "idem-001", response)
                replay = store.get_idempotency(admin, "idem-001")
                self.assertEqual(replay["item"]["id"], response["item"]["id"])
                other = dict(admin)
                other["id"] = "another-actor"
                self.assertIsNone(store.get_idempotency(other, "idem-001"))
            finally:
                store.close()

    def test_operations_summary_and_settings_are_permissioned(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(os.path.join(tmp, "app.sqlite3"))
            try:
                admin = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                summary = store.operations_summary(admin)
                self.assertIn("cane_crushed_ton", summary)
                settings = store.settings_summary(admin)
                self.assertGreaterEqual(settings["module_count"], 30)
                employee = dict(admin)
                employee["role"] = "EMPLOYEE"
                with self.assertRaises(PermissionDenied):
                    store.settings_summary(employee)
            finally:
                store.close()

    def test_employee_mobile_home_and_actions_use_permitted_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = DataStore(os.path.join(tmp, "app.sqlite3"))
            try:
                admin = store.authenticate("admin@factorypulse.local", "ChangeMe-FactoryPulse-2026!")
                employee = store.create_user(admin, {
                    "email": "mobile.employee@example.invalid",
                    "name": "Mobile Employee",
                    "role": "EMPLOYEE",
                    "password": "Mobile-Employee-2026!",
                })
                employee_user = store.authenticate("mobile.employee@example.invalid", "Mobile-Employee-2026!")
                store.create_record(admin, "employees", {
                    "employee_code": "EMP-MOB-1",
                    "full_name": "Mobile Employee",
                    "department": "Crushing",
                    "role": "Operator",
                    "phone": "+91-90000-05555",
                    "email": "mobile.employee@example.invalid",
                    "shift": "A",
                    "status": "Active",
                })
                home = store.mobile_home(employee_user)
                self.assertIn("quick_actions", home)
                attendance = store.mobile_check_in(employee_user, {"gps_area": "Gate 1"})
                self.assertEqual(attendance["data"]["status"], "Checked In")
                leave = store.mobile_leave_request(employee_user, {"leave_type": "Sick Leave", "reason": "Fever"})
                self.assertEqual(leave["data"]["status"], "Pending")
                sos = store.mobile_incident_report(employee_user, {"area": "Mill House"}, sos=True)
                self.assertEqual(sos["data"]["severity"], "Critical")
            finally:
                store.close()


if __name__ == "__main__":
    unittest.main()
