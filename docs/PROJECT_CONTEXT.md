# FactoryPulse ERP Project Context

Last updated: 2026-07-13

## Repository

- Local path: `D:\frappe-ERp\OUTPUT\factorypulse-erp`
- GitHub remote: `https://github.com/ommehta2006/erp.git`
- Branch: `master`

## Current Goal

Build a deploy-ready factory ERP and employee operations app with:

- Professional department-first ERP UI.
- Real authenticated backend APIs.
- Supabase production database.
- Railway backend deployment.
- Vercel frontend deployment.
- No demo seed data and no fake API responses.

## Active Stack

- Backend: FastAPI in `backend/`
- Frontend: Next.js in `frontend/`
- Production DB: Supabase Postgres
- Backend hosting: Railway
- Frontend hosting: Vercel
- Local/container fallback DB: SQLite at `APP_DATABASE`

## Important Files

- Backend API: `backend/main.py`
- Backend storage/catalog: `backend/database.py`
- Frontend home: `frontend/src/app/page.tsx`
- Frontend login: `frontend/src/app/login/page.tsx`
- Department module UI: `frontend/src/app/departments/[id]/page.tsx`
- Railway config: `railway.json`
- Vercel config from repo root: `vercel.json`
- Vercel config if Root Directory is `frontend`: `frontend/vercel.json`
- Dockerfile: `Dockerfile`
- Docker ignore: `.dockerignore`
- Supabase full schema: `supabase/schema.sql`
- Deployment guide: `docs/deployment/RAILWAY_SUPABASE_VERCEL.md`

## ERP Departments

The live catalog includes:

- HR & Employee
- Finance & Accounts
- Cane & Farmer
- Manufacturing
- Inventory & Dispatch
- Quality & Compliance
- Maintenance & Assets
- Sales & Customer
- Administration

## SQL Database File

`supabase/schema.sql` is the full database file to run in Supabase SQL Editor. It was validated against a fresh PostgreSQL 16 container.

It creates 51 tables:

- 44 ERP module tables used by the current production API.
- 6 platform/system tables: `erp_departments`, `erp_modules`, `app_users`, `audit_events`, `uploaded_files`, `integration_events`.
- 1 legacy compatibility table: `records`.
- 9 department catalog rows.
- 56 department-module mapping rows.
- Updated-at triggers, RLS enablement, and operational indexes.

Module tables:

`employees`, `attendance`, `leave_requests`, `shifts`, `departments`, `payroll_runs`, `recruitment`, `performance_reviews`, `training_records`, `expense_claims`, `visitor_passes`, `invoices`, `purchase_orders`, `sales_orders`, `budgets`, `tax_records`, `farmer_payments`, `approvals`, `farmers`, `cane_registrations`, `harvest_plans`, `vehicles`, `weighbridge_tickets`, `production_batches`, `boiler_logs`, `packaging_runs`, `byproducts`, `power_generation`, `distillery_batches`, `ethanol_dispatches`, `energy_meters`, `inventory_items`, `warehouses`, `dispatches`, `assets`, `quality_tests`, `lab_instruments`, `compliance_register`, `documents`, `incidents`, `maintenance_work_orders`, `tasks`, `support_tickets`, `customer_portal_requests`.

## Backend Behavior

- `/api/health` is public for Railway healthchecks.
- Login and protected APIs require `APP_SECRET_KEY` and `BOOTSTRAP_ADMIN_PASSWORD`.
- If auth secrets are missing, healthcheck still returns 200, but login/protected APIs return 503.
- If `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set, backend uses Supabase.
- If Supabase variables are missing, backend falls back to local SQLite.
- The app starts empty. No demo rows are inserted.

## Railway Raw Env Template

Use real values in Railway. Do not commit real secrets.

```env
APP_ENV=production
APP_SECRET_KEY=REPLACE_WITH_LONG_RANDOM_SECRET
BOOTSTRAP_ADMIN_EMAIL=admin@yourcompany.com
BOOTSTRAP_ADMIN_PASSWORD=REPLACE_WITH_STRONG_PASSWORD
CORS_ALLOWED_ORIGINS=https://YOUR-VERCEL-APP.vercel.app
SUPABASE_URL=https://YOUR-SUPABASE-PROJECT.supabase.co
SUPABASE_SERVICE_ROLE_KEY=REPLACE_WITH_SUPABASE_SERVICE_ROLE_OR_SECRET_KEY
# Alternative accepted backend alias:
# SUPABASE_SECRET_KEY=REPLACE_WITH_SUPABASE_SECRET_KEY
APP_DATABASE=./data/factorypulse.sqlite3
```

Important:

- Supabase service/secret key belongs only in Railway.
- Do not put Supabase secret/service role key in Vercel.
- If any real key was pasted into chat or logs, rotate it in Supabase before final production use.

## Vercel Env

```env
NEXT_PUBLIC_API_BASE=https://YOUR-RAILWAY-BACKEND.up.railway.app
```

## Supabase Setup

1. Open Supabase SQL Editor.
2. Run `supabase/schema.sql`.
3. Confirm all module tables exist.
4. Put `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in Railway.

## Verified Locally

Completed checks during build:

- Python compile for `backend/main.py` and `backend/database.py`.
- Backend API smoke test with explicit auth env vars.
- Backend healthcheck smoke test without auth env vars.
- Docker image build.
- Docker container `/api/health` returns 200 without auth env vars.
- Docker container login works with auth env vars.
- Frontend install/build from repo root using `npm --prefix frontend`.
- Frontend install/build from `frontend/` root using `npm ci && npm run build`.

Known warning:

- `npm ci` reports 2 moderate dependency advisories. They were not force-upgraded because `npm audit fix --force` may introduce breaking dependency changes.

## Deployment Notes

Railway:

- Use latest `master`.
- Healthcheck path: `/api/health`.
- Required for usable login: `APP_SECRET_KEY`, `BOOTSTRAP_ADMIN_EMAIL`, `BOOTSTRAP_ADMIN_PASSWORD`.
- Required for Supabase storage: `SUPABASE_URL` plus either `SUPABASE_SERVICE_ROLE_KEY` or `SUPABASE_SECRET_KEY`.

Vercel:

- If Root Directory is repo root, root `vercel.json` uses:
  - `npm --prefix frontend ci`
  - `npm --prefix frontend run build`
- If Root Directory is `frontend`, `frontend/vercel.json` uses:
  - `npm ci`
  - `npm run build`

## Recent Fixes

- Removed old `backend_old/` and `frontend_old/`.
- Removed tracked runtime SQLite DB/log files.
- Added `.gitignore` and `.dockerignore`.
- Fixed Railway healthcheck startup behavior.
- Fixed Docker CMD JSON-form warning.
- Fixed Vercel install command ambiguity.
- Added full Supabase SQL schema with all ERP module tables.
- Added platform/system SQL tables, catalog metadata, indexes, triggers, and RLS enablement.
- Updated backend Supabase storage to use module tables directly.

## Remaining Manual Steps

- Rotate any real Supabase keys that were pasted into chat/logs.
- Run `supabase/schema.sql` in Supabase.
- Set Railway variables.
- Set Vercel variable `NEXT_PUBLIC_API_BASE`.
- Redeploy Railway and Vercel from latest `master`.
