# Validation And Deploy Checklist

Run the checks that match the files changed in the slice.

## Backend Checks

```powershell
python -m py_compile D:\Frappe-AI\erp\backend\main.py D:\Frappe-AI\erp\backend\database.py
```

If backend behavior changed, add a local SQLite smoke test with:

```powershell
$env:APP_DATABASE='C:\tmp\erp_smoke.sqlite3'
$env:SUPABASE_URL=''
$env:SUPABASE_SERVICE_ROLE_KEY=''
$env:SUPABASE_SECRET_KEY=''
$env:APP_SECRET_KEY='local-test-secret'
```

## Frontend Checks

```powershell
cd D:\Frappe-AI\erp\frontend
npm.cmd run lint
npm.cmd run build
```

## Mobile Checks

```powershell
cd D:\Frappe-AI\erp\mobile
npm.cmd run typecheck
npx.cmd expo export --platform android --output-dir .expo-export-check --clear
Remove-Item -LiteralPath 'D:\Frappe-AI\erp\mobile\.expo-export-check' -Recurse -Force
```

## Live API Smoke

```powershell
$login = Invoke-RestMethod -Uri 'https://erp-production-8664.up.railway.app/api/auth/login' -Method Post -ContentType 'application/json' -Body '{"email":"admin@gmail.com","password":"admin"}' -TimeoutSec 30
$headers = @{ Authorization = "Bearer $($login.token)" }
$health = Invoke-RestMethod -Uri 'https://erp-production-8664.up.railway.app/api/health' -TimeoutSec 30
$summary = Invoke-RestMethod -Uri 'https://erp-production-8664.up.railway.app/api/mobile/summary' -Headers $headers -TimeoutSec 30
$profile = Invoke-RestMethod -Uri 'https://erp-production-8664.up.railway.app/api/v1/employee/profile' -Headers $headers -TimeoutSec 30
$reports = Invoke-RestMethod -Uri 'https://erp-production-8664.up.railway.app/api/v1/reports/dashboard' -Headers $headers -TimeoutSec 30
@{
  health = $health
  mobile_departments = $summary.stats.departments
  employee_code = $profile.employee_code
  report_count = $reports.stats.reports
} | ConvertTo-Json -Depth 8
```

## Git Checklist

```powershell
git -c safe.directory='D:/Frappe-AI/erp' -C 'D:\Frappe-AI\erp' status --short
git -c safe.directory='D:/Frappe-AI/erp' -C 'D:\Frappe-AI\erp' diff --stat
git -c safe.directory='D:/Frappe-AI/erp' -C 'D:\Frappe-AI\erp' log --oneline -5
```

## Production Acceptance

For each completed slice, prove:

- SQL is present if new tables/columns are needed.
- API returns live data and validates input.
- Web/mobile UI uses the real API.
- Auth is required.
- Employee data is scoped to the logged-in employee.
- Admin/HR/Finance actions write audit records where sensitive.
- Build/typecheck passes.
- Live deploy is healthy.

