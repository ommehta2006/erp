# Antigravity Handoff: Remaining ERP Completion

This folder is a working checklist for continuing the FactoryPulse ERP build from the current repository state.

Use this order:

1. Read `D:\Frappe-AI\erp\requirement_expert_level.md`.
2. Read `to_do\01_remaining_modules.md`.
3. Follow `to_do\02_execution_steps.md` one slice at a time.
4. Use `to_do\03_credentials_and_access.md` for local credential file locations.
5. Validate and deploy using `to_do\04_validation_and_deploy.md`.

Current live URLs:

- Backend: `https://erp-production-8664.up.railway.app`
- Backend health: `https://erp-production-8664.up.railway.app/api/health`
- ERP frontend: `https://erp-factorypulse.vercel.app`
- Login: `admin@gmail.com` / `admin`

Current project shape:

- Backend API: `D:\Frappe-AI\erp\backend`
- ERP web frontend: `D:\Frappe-AI\erp\frontend`
- Expo employee mobile app: `D:\Frappe-AI\erp\mobile`
- Supabase SQL files: `D:\Frappe-AI\erp\supabase`
- Final docs: `D:\Frappe-AI\erp\docs`

Important rules:

- Do not store raw fingerprint data or biometric templates.
- Use OS biometric success assertions only.
- Do not copy secrets into committed files.
- Every UI feature must call a real backend API.
- Every backend feature that needs new storage must include a Supabase SQL file.
- Run tests/builds before pushing or deploying.

