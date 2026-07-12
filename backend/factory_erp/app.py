import csv
import hashlib
import io
import json
import os
import shutil
import sqlite3
import tempfile
import time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .security import SecurityError, production_secret_from_env, sign_token, verify_token
from .store import DataStore, NotFound, PermissionDenied, RESOURCE_CATALOG, ValidationError


ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"


def load_env_file(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


load_env_file(ROOT / ".env")
SECRET = production_secret_from_env("APP_SECRET_KEY", "replace-with-a-long-random-secret-before-use")
TOKEN_TTL = int(os.getenv("TOKEN_TTL_SECONDS", "28800"))
STORE = DataStore(os.getenv("APP_DATABASE", str(ROOT / "data" / "factorypulse.sqlite3")))
RATE_LIMIT = {}


class Handler(BaseHTTPRequestHandler):
    server_version = "FactoryPulseERP/1.0"

    def log_message(self, fmt, *args):
        if os.getenv("APP_ENV") != "test":
            super().log_message(fmt, *args)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "geolocation=(), microphone=(), camera=()")
        self.send_header("Cache-Control", "no-store" if self.path.startswith("/api/") else "public, max-age=300")
        origin = self.headers.get("Origin")
        allowed = [o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",") if o.strip()]
        if origin and origin in allowed:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, Idempotency-Key")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        self.route()

    def do_POST(self):
        self.route()

    def do_PATCH(self):
        self.route()

    def route(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            return self.route_api(parsed)
        return self.serve_static(parsed.path)

    def route_api(self, parsed):
        try:
            path = parsed.path.strip("/").split("/")
            query = parse_qs(parsed.query)
            if parsed.path == "/api/health":
                return self.json(200, {"ok": True, "service": "factorypulse-erp", "time": int(time.time())})
            if parsed.path == "/api/openapi.json":
                return self.json(200, self.openapi_spec())
            if parsed.path == "/api/auth/login" and self.command == "POST":
                return self.login()

            user = self.current_user()
            if parsed.path == "/api/me":
                return self.json(200, {"user": {k: user[k] for k in ["email", "name", "role", "tenant_slug", "tenant_name"]}})
            if parsed.path == "/api/catalog":
                return self.json(200, {"resources": STORE.catalog_for(user)})
            if parsed.path == "/api/dashboard":
                return self.json(200, STORE.dashboard(user))
            if parsed.path == "/api/mobile/home" and self.command == "GET":
                return self.json(200, STORE.mobile_home(user))
            if parsed.path == "/api/mobile/check-in" and self.command == "POST":
                return self.json(201, {"item": STORE.mobile_check_in(user, self.read_json())})
            if parsed.path == "/api/mobile/leave-request" and self.command == "POST":
                return self.json(201, {"item": STORE.mobile_leave_request(user, self.read_json())})
            if parsed.path == "/api/mobile/incident" and self.command == "POST":
                return self.json(201, {"item": STORE.mobile_incident_report(user, self.read_json())})
            if parsed.path == "/api/mobile/sos" and self.command == "POST":
                return self.json(201, {"item": STORE.mobile_incident_report(user, self.read_json(), sos=True)})
            if parsed.path == "/api/audit-events":
                return self.json(200, {"items": STORE.audit_events(user, int(query.get("limit", ["100"])[0]))})
            if parsed.path == "/api/admin/users" and self.command == "GET":
                return self.json(200, {"items": STORE.list_users(user)})
            if parsed.path == "/api/admin/users" and self.command == "POST":
                return self.json(201, {"item": STORE.create_user(user, self.read_json())})
            if parsed.path == "/api/admin/settings" and self.command == "GET":
                return self.json(200, STORE.settings_summary(user))
            if parsed.path == "/api/ops/preflight" and self.command == "GET":
                self.require_ops_admin(user)
                return self.json(200, self.ops_preflight())
            if parsed.path == "/api/ops/security-scan" and self.command == "GET":
                self.require_ops_admin(user)
                return self.json(200, self.ops_security_scan())
            if parsed.path == "/api/ops/backup" and self.command == "POST":
                self.require_ops_admin(user)
                return self.json(201, self.ops_backup(user))
            if parsed.path == "/api/ops/restore-test" and self.command == "POST":
                self.require_ops_admin(user)
                return self.json(200, self.ops_restore_test())
            if parsed.path == "/api/search" and self.command == "GET":
                return self.json(200, {"items": STORE.search_records(user, query.get("q", [""])[0], int(query.get("limit", ["50"])[0]))})
            if parsed.path == "/api/reports/operations-summary" and self.command == "GET":
                return self.json(200, STORE.operations_summary(user))
            if len(path) == 3 and path[1] == "export" and self.command == "GET":
                resource = path[2].removesuffix(".csv")
                return self.csv_export(user, resource)

            if len(path) >= 2:
                resource = path[1]
                if self.command == "GET" and len(path) == 2:
                    return self.json(200, {"items": STORE.list_records(user, resource, int(query.get("limit", ["100"])[0]))})
                if self.command == "POST" and len(path) == 2:
                    idem_key = self.headers.get("Idempotency-Key")
                    cached = STORE.get_idempotency(user, idem_key)
                    if cached:
                        return self.json(200, cached)
                    response = {"item": STORE.create_record(user, resource, self.read_json())}
                    STORE.save_idempotency(user, idem_key, response)
                    return self.json(201, response)
                if self.command == "GET" and len(path) == 3:
                    return self.json(200, {"item": STORE.get_record(user, resource, path[2])})
                if self.command == "PATCH" and len(path) == 3:
                    return self.json(200, {"item": STORE.update_record(user, resource, path[2], self.read_json())})
            return self.error(404, "not_found", "route not found")
        except PermissionDenied as exc:
            return self.error(403, "permission_denied", str(exc))
        except NotFound as exc:
            return self.error(404, "not_found", str(exc))
        except ValidationError as exc:
            return self.error(422, "validation_error", str(exc))
        except SecurityError as exc:
            return self.error(401, "unauthorized", str(exc))
        except Exception:
            if os.getenv("APP_ENV") == "development":
                raise
            return self.error(500, "internal_error", "request failed")


    def openapi_spec(self):
        paths = {
            "/api/health": {"get": {"summary": "Service health"}},
            "/api/auth/login": {"post": {"summary": "Password login"}},
            "/api/me": {"get": {"summary": "Current user"}},
            "/api/catalog": {"get": {"summary": "Visible module catalog"}},
            "/api/dashboard": {"get": {"summary": "Role-filtered executive dashboard"}},
            "/api/mobile/home": {"get": {"summary": "Employee mobile home"}},
            "/api/mobile/check-in": {"post": {"summary": "Employee attendance check-in"}},
            "/api/mobile/leave-request": {"post": {"summary": "Employee leave request"}},
            "/api/mobile/incident": {"post": {"summary": "Employee incident report"}},
            "/api/mobile/sos": {"post": {"summary": "Employee emergency SOS"}},
            "/api/search": {"get": {"summary": "Global tenant-safe search"}},
            "/api/reports/operations-summary": {"get": {"summary": "Operations KPI report"}},
            "/api/admin/users": {"get": {"summary": "List tenant users"}, "post": {"summary": "Create tenant user"}},
            "/api/admin/settings": {"get": {"summary": "Tenant and runtime settings summary"}},
            "/api/ops/preflight": {"get": {"summary": "Deployment preflight checks"}},
            "/api/ops/security-scan": {"get": {"summary": "Local secret/security scan"}},
            "/api/ops/backup": {"post": {"summary": "Create SQLite backup"}},
            "/api/ops/restore-test": {"post": {"summary": "Restore-test latest backup"}},
            "/api/audit-events": {"get": {"summary": "Tenant audit events"}},
        }
        for resource in RESOURCE_CATALOG:
            paths[f"/api/{resource}"] = {"get": {"summary": f"List {resource}"}, "post": {"summary": f"Create {resource}"}}
            paths[f"/api/{resource}/{'{id}'}"] = {"get": {"summary": f"Read {resource}"}, "patch": {"summary": f"Update {resource}"}}
            paths[f"/api/export/{resource}.csv"] = {"get": {"summary": f"Export {resource} as CSV"}}
        return {
            "openapi": "3.1.0",
            "info": {"title": "FactoryPulse ERP API", "version": "0.5.0-reference"},
            "security": [{"bearerAuth": []}],
            "paths": paths,
            "components": {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}},
        }

    def csv_export(self, user, resource):
        items = STORE.list_records(user, resource, 500)
        output = io.StringIO()
        fields = RESOURCE_CATALOG[resource]["fields"]
        writer = csv.DictWriter(output, fieldnames=["id", "version", *fields], extrasaction="ignore")
        writer.writeheader()
        for item in items:
            writer.writerow({"id": item["id"], "version": item["version"], **item["data"]})
        raw = output.getvalue().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", f"attachment; filename={resource}.csv")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


    def require_ops_admin(self, user):
        if user.get("role") not in {"FACTORY_ADMIN", "PLATFORM_ADMIN"}:
            STORE.audit(user, "permission_denied", "operations", None, {"action": "admin"})
            raise PermissionDenied("permission denied")

    def ops_preflight(self):
        required = [
            "README.md", ".env.example", "Dockerfile", "docker-compose.yml",
            "backend/factory_erp/app.py", "backend/factory_erp/store.py",
            "frontend/index.html", "frontend/app.js", "frontend/styles.css",
            "frontend/manifest.webmanifest", "frontend/service-worker.js",
            "docs/api/openapi.json", "frappe_app/tools/validate_metadata.py",
        ]
        items = []
        for rel in required:
            path = ROOT / rel
            items.append({"check": f"file:{rel}", "ok": path.exists(), "detail": str(path)})
        db_path = Path(os.getenv("APP_DATABASE", str(ROOT / "data" / "factorypulse.sqlite3")))
        if db_path.exists():
            try:
                con = sqlite3.connect(db_path)
                ok = con.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                con.close()
                items.append({"check": "database:integrity", "ok": ok, "detail": str(db_path)})
            except Exception as exc:
                items.append({"check": "database:integrity", "ok": False, "detail": str(exc)})
        else:
            items.append({"check": "database:exists", "ok": False, "detail": str(db_path)})
        backup_dir = ROOT / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        items.append({"check": "backup_dir:writable", "ok": os.access(backup_dir, os.W_OK), "detail": str(backup_dir)})
        return {"ok": all(item["ok"] for item in items), "items": items}

    def ops_security_scan(self):
        patterns = [
            ("private_key", "-----BEGIN PRIVATE KEY-----"),
            ("aws_access_key", "AKIA"),
            ("hardcoded_default_secret", "replace-with-a-long-random-secret-before-use"),
        ]
        findings = []
        for path in ROOT.rglob("*"):
            if not path.is_file() or any(part in {"data", ".git", "__pycache__"} for part in path.parts):
                continue
            if path.name == ".env.example":
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for rule, needle in patterns:
                if needle in content:
                    findings.append({"file": path.relative_to(ROOT).as_posix(), "rule": rule})
        return {"ok": not findings, "findings": findings}

    def _sha256(self, path: Path):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def ops_backup(self, user):
        db_path = Path(os.getenv("APP_DATABASE", str(ROOT / "data" / "factorypulse.sqlite3")))
        if not db_path.exists():
            raise NotFound("database not found")
        backup_dir = ROOT / "data" / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        stamp = time.strftime("%Y%m%d-%H%M%S")
        target = backup_dir / f"{db_path.stem}-{stamp}.sqlite3"
        shutil.copy2(db_path, target)
        manifest = {"backup": str(target), "bytes": target.stat().st_size, "sha256": self._sha256(target), "created_at": stamp}
        target.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        STORE.audit(user, "backup_created", "operations", target.name, {"bytes": manifest["bytes"], "sha256": manifest["sha256"]})
        return manifest

    def ops_restore_test(self):
        backup_dir = ROOT / "data" / "backups"
        backups = sorted(backup_dir.glob("*.sqlite3"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not backups:
            raise NotFound("no backup available")
        backup = backups[0]
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "restore.sqlite3"
            shutil.copy2(backup, target)
            con = sqlite3.connect(target)
            integrity = con.execute("PRAGMA integrity_check").fetchone()[0]
            tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
            con.close()
        return {"ok": integrity == "ok", "backup": str(backup), "integrity": integrity, "tables": tables}

    def login(self):
        ip = self.client_address[0]
        now = time.time()
        bucket = RATE_LIMIT.setdefault(ip, [])
        RATE_LIMIT[ip] = [t for t in bucket if now - t < 60]
        if len(RATE_LIMIT[ip]) >= 20:
            return self.error(429, "rate_limited", "too many login attempts")
        RATE_LIMIT[ip].append(now)

        body = self.read_json()
        user = STORE.authenticate(str(body.get("email", "")), str(body.get("password", "")))
        if not user:
            return self.error(401, "invalid_credentials", "invalid email or password")
        token = sign_token({"sub": user["id"], "tenant_id": user["tenant_id"], "role": user["role"]}, SECRET, TOKEN_TTL)
        STORE.audit(user, "login", "session", user["id"], {"method": "password"})
        return self.json(200, {"token": token, "user": {k: user[k] for k in ["email", "name", "role", "tenant_slug", "tenant_name"]}})

    def current_user(self):
        header = self.headers.get("Authorization", "")
        if not header.startswith("Bearer "):
            raise SecurityError("missing bearer token")
        payload = verify_token(header.removeprefix("Bearer ").strip(), SECRET)
        user = STORE.get_user(payload.get("sub", ""))
        if not user or user["tenant_id"] != payload.get("tenant_id"):
            raise SecurityError("invalid session context")
        return user

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length > 262_144:
            raise ValidationError("request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise ValidationError("invalid JSON") from exc

    def json(self, status, payload):
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def error(self, status, code, message):
        return self.json(status, {"error": {"code": code, "message": message, "correlation_id": f"req-{int(time.time() * 1000)}"}})

    def serve_static(self, path):
        target = "index.html" if path in ("", "/") else path.lstrip("/")
        file_path = (FRONTEND / target).resolve()
        if FRONTEND not in file_path.parents and file_path != FRONTEND:
            return self.error(404, "not_found", "file not found")
        if not file_path.exists() or file_path.is_dir():
            file_path = FRONTEND / "index.html"
        content_type = "text/html; charset=utf-8"
        if file_path.suffix == ".css":
            content_type = "text/css; charset=utf-8"
        elif file_path.suffix == ".js":
            content_type = "application/javascript; charset=utf-8"
        raw = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main():
    host = os.getenv("APP_HOST", "127.0.0.1")
    port = int(os.getenv("APP_PORT", "8080"))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"FactoryPulse ERP running on http://{host}:{port}")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
