# Setup, Deployment, and Operations

Last verified: 2026-07-12. Release: v0.5.0-reference. Owner: FactoryPulse delivery team.

Local setup:

```powershell
cd D:rappe-ERp\OUTPUTactorypulse-erp
copy .env.example .env
python -m backend.factory_erp.app
```

Test and verification:

```powershell
python -m py_compile backendactory_erppp.py backendactory_erp\store.py backendactory_erp\security.py
python -m unittest discover -s backend	ests
node --check frontendpp.js
python scripts\smoke_test.py --base-url http://127.0.0.1:8080
```

Docker:

```powershell
docker compose up --build
```

Required production configuration: set `APP_ENV=production`, set a long random `APP_SECRET_KEY`, replace bootstrap credentials, pin exact `CORS_ALLOWED_ORIGINS`, mount durable storage for `APP_DATABASE`, and place the app behind TLS.

Operations: monitor `/api/health`, container healthcheck status, disk space for the data volume, audit event growth, idempotency table growth, login failures, and error logs. Rotate bootstrap credentials immediately after first production administrator creation.


Native Frappe install path:

```powershell
cd D:rappe-ERp\OUTPUTactorypulse-erprappe_app
python toolsalidate_metadata.py
.\scripts\install_in_bench.ps1 -BenchPath C:\path	orappe-bench -SiteName factorypulse.local
```

A production Frappe deployment still requires a real bench, selected Frappe/ERPNext versions, database/cache services, TLS, secrets, backups, and owner authorization.

PWA checks: verify `/manifest.webmanifest`, `/service-worker.js`, and the `Employee App` navigation item after login. Mobile actions must create records through `/api/mobile/*` and appear in audit events.


v0.5 update: active deployment architecture is FastAPI backend on Railway, Next.js frontend on Vercel, and Supabase Postgres via `supabase/schema.sql`. The app is empty by default and department-first after login.
