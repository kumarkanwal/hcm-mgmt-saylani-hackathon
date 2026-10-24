import hashlib
import json

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def login_rate_limit_key(request: Request) -> str:
    """Separate login buckets by account so a shared reverse proxy is not a global lockout."""
    raw_body = getattr(request, "_body", b"")
    account = "unknown"
    if raw_body:
        try:
            value = json.loads(raw_body)
            if isinstance(value, dict) and isinstance(value.get("email"), str):
                account = value["email"].strip().lower()
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass
    digest = hashlib.sha256(account.encode("utf-8")).hexdigest()[:20]
    remote = request.client.host if request.client else "unknown"
    return f"login:{remote}:{digest}"


limiter = Limiter(key_func=get_remote_address, default_limits=[])
