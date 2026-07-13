# System Architecture and Security

Last verified: 2026-07-12. Release: v0.5.0-reference. Owner: FactoryPulse delivery team.

Architecture: Python standard-library HTTP server, SQLite persistence, static SPA frontend, Docker runtime, and file-based environment configuration. The server owns authentication, authorization, validation, audit logging, idempotency, CSV export, OpenAPI metadata, and tenant resolution.

Security controls: PBKDF2-SHA256 password hashing, HMAC-signed expiring bearer tokens, no stack traces in production mode, request body size limit, login rate limiting, CORS origin allowlist, security headers, schema allowlists, role permissions, actor-scoped idempotency keys, redacted user administration responses, and audit events.

Trust boundaries: browser UI is untrusted; all access decisions are repeated by the API. The tenant boundary is `tenant_id` from the verified session, never a client-supplied tenant field. Audit records and idempotency keys are tenant-scoped.

Deployment boundary: Docker runs as a non-root user, exposes port 8080, includes a healthcheck, and stores mutable SQLite data in a mounted volume.

Frappe implementation path: `frappe_app/` now maps each resource in `RESOURCE_CATALOG` to a namespaced FactoryPulse DocType or supporting DocType, includes role setup in `install.py`, permission helpers, whitelisted API methods, scheduler hooks, audit/idempotency DocTypes, and bench install scripts. A live bench install remains required to prove ERPNext runtime compatibility.
