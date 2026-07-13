# Database and Migrations

Last verified: 2026-07-12. Release: v0.5.0-reference. Owner: FactoryPulse delivery team.

Database: SQLite file configured by `APP_DATABASE`.

Tables: `tenants`, `users`, `records`, `audit_events`, and `idempotency_keys`.

`records` stores tenant-bound ERP records with resource name, JSON payload, status, version, creator/updater, and timestamps. `idempotency_keys` stores actor- and tenant-scoped write responses to prevent duplicate creates from retried requests.

Migrations run automatically on startup through `DataStore.migrate()` and are idempotent `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` operations.

Synthetic seed data is inserted only when the tenant has no records. Seeded names and contact values use safe example data and `.invalid` email domains where applicable.

Backup: stop writes or place the service behind maintenance mode, copy the SQLite database file and WAL files, verify checksum, and restore into an isolated environment before trusting a backup. For production-scale multi-user use, migrate the persistence boundary to a managed relational database.

Frappe DocTypes: `frappe_app/factorypulse_erp/factorypulse_erp/doctype/` contains 36 namespaced DocType metadata files, including operational modules, audit events, and idempotency keys. Validate with `python tools/validate_metadata.py` from `frappe_app/`.
