# API and Integrations

Last verified: 2026-07-12. Release: v0.4.0-reference. Owner: FactoryPulse delivery team.

API conventions: JSON by default, bearer token authentication, stable error envelope, bounded request bodies, resource field allowlists, tenant resolution from the signed token, server-side RBAC, idempotent creates with `Idempotency-Key`, and CSV export for permitted modules.

Reference artifacts: live `/api/openapi.json` and checked-in `docs/api/openapi.json`.

Core endpoints: `/api/health`, `/api/auth/login`, `/api/me`, `/api/catalog`, `/api/dashboard`, `/api/search`, `/api/reports/operations-summary`, `/api/admin/users`, `/api/admin/settings`, `/api/audit-events`, `/api/{resource}`, `/api/{resource}/{id}`, and `/api/export/{resource}.csv`.

Security behavior: admin user creation validates roles, hashes passwords, and never returns password hashes. Search, dashboard, reports, exports, lists, reads, creates, and updates are filtered by authenticated tenant and role. Unknown fields are rejected.

No outbound production integrations are enabled in this reference build. Integration-ready records exist for vehicles, weighbridge, purchase orders, sales orders, invoices, dispatch, ethanol dispatch, and help desk workflows.

Frappe API methods: `frappe_app/factorypulse_erp/api.py` provides whitelisted `catalog`, `list_records`, `create_record`, `operations_summary`, `export_csv`, and `secure_search` methods with Frappe permission checks.

Employee mobile endpoints: `/api/mobile/home`, `/api/mobile/check-in`, `/api/mobile/leave-request`, `/api/mobile/incident`, and `/api/mobile/sos`. These use authenticated bearer sessions, server-side RBAC, tenant scoping, validation, persistence, and audit events.
