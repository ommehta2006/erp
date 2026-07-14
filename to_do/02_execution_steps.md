# Execution Steps

Work in small deployable slices. Each slice must include backend, UI, SQL, validation, push, and deploy where needed.

## Standard Slice Flow

1. Inspect current files and live behavior.
2. Pick one unfinished module from `01_remaining_modules.md`.
3. Confirm existing API and database tables.
4. Add or update Supabase SQL in `D:\Frappe-AI\erp\supabase`.
5. Copy any new SQL to:
   `C:\Users\ommeh\Documents\Codex\2026-07-13\d-frappe-ai-erp\outputs`
6. Implement backend in `D:\Frappe-AI\erp\backend\main.py` and helpers only where needed.
7. Implement ERP web UI in `D:\Frappe-AI\erp\frontend\src\app`.
8. Implement Expo mobile UI in `D:\Frappe-AI\erp\mobile\App.tsx` when employee-facing.
9. Add validation, loading, empty, success, retry, and permission-denied states.
10. Run local checks.
11. Commit with a focused message.
12. Push to GitHub `master`.
13. Deploy Railway if backend changed.
14. Deploy Vercel if frontend changed.
15. Run live API checks.
16. Update this folder if remaining scope changes.

## Good Next Slices

### Slice 1: Salary Slip Download

- Backend: add employee salary slip detail/export endpoint.
- ERP: Finance salary slip publish button.
- Mobile: salary slip detail card with download/share-ready data.
- SQL: ensure `salary_slips` has publish fields if missing.
- Validation: login, generate/publish slip, employee can read only own slip.

### Slice 2: Mobile Attendance Detail

- Backend: add attendance detail endpoint with location and biometric evidence.
- Mobile: tap attendance history row to open detail screen.
- UI: show Day In/Out time, geofence status, accuracy, distance, late/early/overtime.
- Security: no other employee record access.

### Slice 3: Employee Documents

- Backend: CRUD and metadata validation for employee documents.
- ERP HR: document manager in employee profile.
- Mobile: profile document list.
- SQL: add missing document fields/indexes.
- Security: no public document URL unless signed or controlled.

### Slice 4: Role Permission Matrix

- Backend: expose role permissions and update endpoint.
- ERP Admin: matrix UI for roles vs permissions.
- Audit: record every permission change.
- Validation: permission-denied check for restricted user.

### Slice 5: Leave Accrual UI

- Backend: existing accrual runner polish if needed.
- ERP HR: run accrual, dry-run, expiry, carry-forward controls.
- Mobile: leave balance drilldown.
- Validation: allocation created once only.

## Coding Rules

- Keep edits scoped.
- Reuse existing `storage.create_record`, `storage.update_record`, and permission helpers.
- Do not add mock APIs.
- Do not add fake biometric matching.
- Do not store secret keys in source.
- For Supabase, prefer `create table if not exists`, `alter table add column if not exists`, indexes, triggers, and service-role RLS policy.
- Avoid changing unrelated formatting.

