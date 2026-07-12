import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict


class SecurityError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def hash_password(password: str, salt: str | None = None) -> str:
    if len(password) < 12:
        raise ValueError("password must be at least 12 characters")
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), 220_000)
    return f"pbkdf2_sha256$220000${salt}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, rounds, salt, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("ascii"), int(rounds))
        return hmac.compare_digest(_b64(digest), expected)
    except Exception:
        return False


def sign_token(payload: Dict[str, Any], secret: str, ttl_seconds: int) -> str:
    now = int(time.time())
    safe_payload = dict(payload)
    safe_payload.update({"iat": now, "exp": now + ttl_seconds, "jti": secrets.token_urlsafe(16)})
    encoded = _b64(json.dumps(safe_payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    signature = _b64(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}"


def verify_token(token: str, secret: str) -> Dict[str, Any]:
    try:
        encoded, signature = token.split(".", 1)
        expected = _b64(hmac.new(secret.encode("utf-8"), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise SecurityError("invalid token signature")
        payload = json.loads(_unb64(encoded))
        if int(payload.get("exp", 0)) < int(time.time()):
            raise SecurityError("token expired")
        return payload
    except SecurityError:
        raise
    except Exception as exc:
        raise SecurityError("invalid token") from exc


def production_secret_from_env(name: str, default: str) -> str:
    value = os.getenv(name, default)
    if os.getenv("APP_ENV") == "production" and value == default:
        raise RuntimeError(f"{name} must be set to a production secret")
    return value
