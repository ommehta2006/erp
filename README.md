# FactoryPulse ERP

FactoryPulse ERP is a deploy-ready factory ERP and employee operations app built from the `emergent-erp-ai-builder` blueprint. The active stack is:

- `backend/`: FastAPI API for Railway or Docker
- `frontend/`: Next.js app for Vercel
- `supabase/schema.sql`: full Supabase Postgres schema with one table per ERP module
- `frappe_app/`: retained native Frappe/ERPNext scaffold for a separate ERPNext path

The app starts empty by design. No demo records are seeded. After login, the home page shows department containers first. Each department opens its own module workspace and reads/writes records through authenticated backend API routes.

## ERP Coverage

Departments included in the live catalog:

- HR & Employee
- Finance & Accounts
- Cane & Farmer
- Manufacturing
- Inventory & Dispatch
- Quality & Compliance
- Maintenance & Assets
- Sales & Customer
- Administration

The module catalog covers employees, attendance, leave, shifts, payroll, recruitment, performance, training, expenses, visitors, invoices, purchase orders, sales orders, budgets, taxes, farmers, cane registration, harvest plans, vehicles, weighbridge, production, boiler, packaging, byproducts, power generation, distillery, ethanol dispatch, inventory, warehouses, dispatches, assets, quality tests, lab instruments, compliance, documents, incidents, maintenance work orders, tasks, support tickets, approvals, and customer portal requests.

## Security

- Bearer-token authentication with HMAC-signed expiring tokens.
- Constant-time password comparison.
- Required `APP_SECRET_KEY` and `BOOTSTRAP_ADMIN_PASSWORD`; healthcheck stays available without them, but login and protected APIs return `503` until they are configured.
- CORS allowlist through `CORS_ALLOWED_ORIGINS`.
- Server-side module allowlists; unknown modules are rejected.
- Supabase service role key is backend-only and must never be exposed to Vercel.

## Local Backend

Create `backend/.env` from `backend/.env.example` and set real local secrets:

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
copy backend\.env.example backend\.env
```

Run the backend:

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp\backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Local Frontend

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp\frontend
npm ci
$env:NEXT_PUBLIC_API_BASE="http://127.0.0.1:8000"
npm run dev
```

Open `http://127.0.0.1:3000` and sign in with the credentials set in `backend/.env`.

## Docker

Docker Compose reads `backend/.env`:

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
docker compose up --build
```

## Production Deployment

Use the detailed guide in `docs/deployment/RAILWAY_SUPABASE_VERCEL.md`.

Production target:

- Railway: deploy backend with `APP_ENV=production`, `APP_SECRET_KEY`, bootstrap admin credentials, `CORS_ALLOWED_ORIGINS`, `SUPABASE_URL`, and `SUPABASE_SERVICE_ROLE_KEY`.
- Supabase: run `supabase/schema.sql` before pointing Railway to the database. It creates all ERP module tables plus the legacy `records` compatibility table.
- Vercel: deploy `frontend/` with `NEXT_PUBLIC_API_BASE` set to the Railway backend URL.

## Verification

Current verification commands:

```powershell
python -m py_compile backend\main.py backend\database.py
cd frontend
npm ci
npm run lint
npm run build
```

Docker verification requires Docker Desktop Linux engine to be reachable from the CLI.
