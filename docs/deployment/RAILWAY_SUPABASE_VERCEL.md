# Railway + Supabase + Vercel Deployment

Target topology:

- Railway: FastAPI backend from `backend/`
- Supabase: production Postgres schema with one table per ERP module
- Vercel: Next frontend from `frontend/`

Status in this package:

- Backend is real API, authenticated, and connected to storage.
- Storage uses Supabase module tables when `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are set.
- Storage falls back to local SQLite for Docker/local testing.
- Frontend calls backend through `NEXT_PUBLIC_API_BASE`.
- App is empty by default. No demo seed records are inserted.
- `/api/health` is public for Railway healthchecks. Login and protected APIs return `503` until `APP_SECRET_KEY` and `BOOTSTRAP_ADMIN_PASSWORD` are configured.

Railway variables:

```text
APP_SECRET_KEY=<long random value>
APP_ENV=production
BOOTSTRAP_ADMIN_EMAIL=<admin email>
BOOTSTRAP_ADMIN_PASSWORD=<strong password>
CORS_ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app
SUPABASE_URL=https://<project>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<service role key>
```

Supabase setup:

1. Open Supabase SQL editor.
2. Run `supabase/schema.sql`. It creates 44 ERP module tables plus the legacy `records` compatibility table.
3. Keep service role key only in Railway, never in Vercel.

Vercel variables:

```text
NEXT_PUBLIC_API_BASE=https://<your-railway-backend>.up.railway.app
```

Verification:

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
python -m py_compile backend\main.py backend\database.py
cd frontend
npm ci
npm run lint
npm run build
```

Docker local backend:

```powershell
cd D:\frappe-ERp\OUTPUT\factorypulse-erp
docker compose up --build
```

Docker could not be verified in this run because Docker Desktop Linux engine was not reachable from the CLI.
