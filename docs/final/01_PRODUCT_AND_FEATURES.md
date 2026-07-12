# Product and Features

Last verified: 2026-07-12. Release: v0.4.0-reference. Owner: FactoryPulse delivery team.

FactoryPulse ERP is a deploy-ready reference app for a cooperative sugar factory. It includes an authenticated ERP workspace, employee operations, factory production modules, tenant administration, secure APIs, tenant isolation, audit events, Docker packaging, native Frappe custom app scaffold, and final handoff documentation.

Feature catalog: executive dashboard, operations KPI report, global search, module tables, create/update forms, CSV export, people and access administration, tenant security center, audit explorer, OpenAPI metadata, and responsive light/dark UI.

Supported modules: employees, attendance, leave, shifts, departments, farmers, cane registration, harvest planning, vehicles, weighbridge, production batches, quality tests, maintenance work orders, assets, inventory, purchasing, sales, invoices, safety incidents, tasks, approvals, payroll, training, visitors, documents, dispatch, warehouses, power generation, distillery, ethanol, by-products, boiler logs, packaging, and help desk.

Roles: FACTORY_ADMIN has full tenant administration. Domain roles include HR_MANAGER, PRODUCTION_MANAGER, FARMER_OFFICER, QUALITY_MANAGER, MAINTENANCE_MANAGER, INVENTORY_MANAGER, FINANCE_MANAGER, and EMPLOYEE. Every API request rechecks the server-side role before reading or mutating data.

Tenant model: logical tenant isolation via `tenant_id` on users, records, idempotency keys, and audit events. Cross-tenant lookup is denied server-side.

Frappe path: `frappe_app/` contains a native custom app scaffold with 36 DocType metadata files, hooks, install logic, permissions, API methods, tests, and bench install helpers.

Explicit limitation: this package includes a Frappe app source scaffold but does not prove installation in a live bench on this machine. It is structured so the same module catalog can be migrated into Frappe DocTypes, fixtures, workflows, reports, workspaces, and permissions.

Employee mobile app: installable PWA shell with mobile home, attendance check-in, leave request, incident report, SOS, task, training, and document views backed by `/api/mobile/*` endpoints.
