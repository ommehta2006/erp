# FactoryPulse ERP Frappe App

This folder contains a native custom Frappe app scaffold generated from the verified FactoryPulse reference implementation. It is intended to be copied or linked into a Frappe bench as `apps/factorypulse_erp`.

The standalone app in the parent folder remains the runnable review build. This Frappe app is the migration path toward the requested ERPNext/Frappe deployment.

## Install in a bench

```bash
cd /path/to/frappe-bench
bench get-app /path/to/D/frappe-ERp/OUTPUT/factorypulse-erp/frappe_app
bench --site factorypulse.local install-app factorypulse_erp
bench --site factorypulse.local migrate
bench --site factorypulse.local run-tests --app factorypulse_erp
```

Use a site-per-factory tenant model. Do not share one site across unrelated tenants unless row isolation is formally designed and tested.


## Verification without bench

These checks do not prove a full Frappe installation, but they catch broken package metadata and malformed DocType JSON before handoff:

```bash
python tools/validate_metadata.py
python -m py_compile factorypulse_erp/api.py factorypulse_erp/hooks.py factorypulse_erp/install.py factorypulse_erp/permissions.py
```

## What the app includes

- 34 operational DocTypes generated from the verified factory ERP catalog.
- Audit and idempotency DocTypes.
- Hooks, role fixtures, scheduler event, install hook, permission helper, and whitelisted API methods.
- Bench install helpers for PowerShell and Bash.
- Module catalog documentation in `docs/MODULE_CATALOG.md`.


## Employee mobile methods

`factorypulse_erp.api` includes `mobile_home`, `mobile_check_in`, `mobile_leave_request`, `mobile_incident`, and `mobile_sos` whitelisted methods. They are intended to back ERPNext/Frappe Desk or mobile web pages using the same server-side permission model as the standalone app.
