# FactoryPulse ERP

Current reference release: `v0.4.0-reference`


FactoryPulse ERP is a deploy-ready reference implementation for a secure factory ERP, employee operations app, and tenant administration workspace. It was generated from the `emergent-erp-ai-builder` blueprint and the factory requirements in `00_requirement.md`.

This package is intentionally self-contained: the API, RBAC, tenant isolation, audit log, persistence, seeded factory data, and professional responsive UI all run with Python standard library + SQLite. It is ready for local client review and can be containerized immediately.

## What is included

- Secure HTTP API with bearer tokens, PBKDF2 password hashing, HMAC-signed session tokens, idempotent creates, rate limiting, request size limits, CORS allowlist, security headers, OpenAPI metadata, CSV export, and structured errors.
- Real persistence using SQLite. No screen is hardcoded to fake API responses.
- Tenant-isolated records and server-side role checks for every API route.
- Professional responsive ERP UI with dashboard, operations report, module navigation, command palette/search, dense tables, create/update forms, CSV exports, people/access administration, security center, dark mode, audit view, and mobile layouts.
- Factory ERP modules for employees, attendance, leave, shifts, departments, farmers, cane registration, harvest planning, vehicles, weighbridge, production, quality, maintenance, assets, inventory, buying, sales, invoices, incidents, tasks, approvals, payroll, training, visitors, documents, dispatch, warehouses, power generation, distillery, ethanol, by-products, boiler, packaging, and help desk.
- Dockerfile, Docker Compose, smoke test, unit tests, environment contract, and final handoff docs.

## Local run

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
copy .env.example .env
python -m backend.factory_erp.app
```

Open http://127.0.0.1:8080 and sign in with the development credentials in `.env.example`, or set your own `BOOTSTRAP_ADMIN_EMAIL` and `BOOTSTRAP_ADMIN_PASSWORD`.

## Tests

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
python -m unittest discover -s backend\tests
```

## Docker

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
docker compose up --build
```

## Production notes

- Replace all bootstrap secrets before deployment.
- Put the app behind TLS.
- Set `APP_ENV=production`.
- Set `CORS_ALLOWED_ORIGINS` to exact production origins.
- Use a managed database for production-scale use. SQLite is suitable for review, pilots, and single-node demos only.
- For a Frappe/ERPNext production program, map the module catalog and workflows in `docs/final` into custom DocTypes, fixtures, workflows, reports, and permission rules.


## API reference

- Live metadata: http://127.0.0.1:8080/api/openapi.json
- Static artifact: `docs/api/openapi.json`
- Authenticated examples use `Authorization: Bearer <token>`.
- Writes reject unknown fields and create operations support `Idempotency-Key`.

## Verification evidence

```powershell
python -m py_compile backendactory_erppp.py backendactory_erp\store.py backendactory_erp\security.py
python -m unittest discover -s backend	ests
node --check frontendpp.js
python scripts\smoke_test.py --base-url http://127.0.0.1:8080
```


## Native Frappe app path

A native custom Frappe app scaffold is included at `frappe_app/` for the ERPNext/Frappe deployment track. It includes 36 DocType metadata files, hooks, install logic, permission helpers, whitelisted API methods, role fixtures, metadata validator, and bench install scripts.

Quick local checks:

```powershell
cd D:rappe-ERp\OUTPUTactorypulse-erprappe_app
python toolsalidate_metadata.py
Get-ChildItem -Recurse -File | Where-Object { $_.Extension -eq '.py' } | ForEach-Object { python -m py_compile $_.FullName }
```

Bench install helper:

```powershell
cd D:rappe-ERp\OUTPUTactorypulse-erprappe_app
.\scripts\install_in_bench.ps1 -BenchPath C:\path	orappe-bench -SiteName factorypulse.local
```


## Employee mobile app

The SPA now includes an `Employee App` surface and PWA shell for worker self-service. It uses real secure APIs:

- `GET /api/mobile/home`
- `POST /api/mobile/check-in`
- `POST /api/mobile/leave-request`
- `POST /api/mobile/incident`
- `POST /api/mobile/sos`

The PWA files are `frontend/manifest.webmanifest` and `frontend/service-worker.js`.
