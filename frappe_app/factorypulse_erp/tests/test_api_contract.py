import unittest

from factorypulse_erp.api import RESOURCE_DOCTYPES


class FactoryPulseApiContractTests(unittest.TestCase):
    def test_core_resources_are_registered(self):
        for resource in ["employees", "attendance", "production_batches", "maintenance_work_orders", "payroll_runs", "power_generation"]:
            self.assertIn(resource, RESOURCE_DOCTYPES)

    def test_doctype_names_are_factorypulse_namespaced(self):
        self.assertTrue(all(name.startswith("FactoryPulse ") for name in RESOURCE_DOCTYPES.values()))
