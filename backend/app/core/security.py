import hashlib
import hmac
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from app.core.config import Settings
from app.core.exceptions import ApiError
from app.models.user import User

JWT_ALGORITHM = "HS256"
BCRYPT_MAX_BYTES = 72
BCRYPT_ROUNDS = 12


def password_token_version(user: User, settings: Settings) -> str:
    return hmac.new(
        settings.jwt_secret.encode("utf-8"),
        user.password_hash.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def validate_password_length(password: str) -> None:
    try:
        encoded = password.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ApiError(
            422, "VALIDATION_ERROR", "Password contains invalid characters"
        ) from exc
    if len(password) < 8:
        raise ApiError(
            422, "VALIDATION_ERROR", "Password must be at least 8 characters long"
        )
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ApiError(
            422, "VALIDATION_ERROR", "Password must be at most 72 UTF-8 bytes"
        )


def hash_password(password: str) -> str:
    validate_password_length(password)
    hashed = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    )
    return hashed.decode("ascii")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        encoded = password.encode("utf-8")
        if len(encoded) > BCRYPT_MAX_BYTES:
            return False
        return bcrypt.checkpw(encoded, password_hash.encode("ascii"))
    except (ValueError, TypeError, UnicodeEncodeError):
        return False


def create_access_token(user: User, settings: Settings) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": str(user.id),
        "role": user.role,
        "employee_id": user.employee_id,
        "pwdv": password_token_version(user, settings),
        "iat": now,
        "exp": now + timedelta(hours=settings.jwt_expire_hours),
    }
    return jwt.encode(claims, settings.jwt_secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> dict[str, object]:
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "role", "pwdv", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:
        raise ApiError(
            401, "INVALID_TOKEN", "Invalid or expired authentication token"
        ) from exc

    subject = claims.get("sub")
    role = claims.get("role")
    employee_id = claims.get("employee_id")
    pwdv = claims.get("pwdv")
    if (
        not isinstance(subject, str)
        or not subject.isdecimal()
        or role not in {"admin", "hr", "employee"}
        or not isinstance(pwdv, str)
        or len(pwdv) != 64
        or (
            employee_id is not None
            and (not isinstance(employee_id, int) or employee_id < 1)
        )
        or (role == "employee" and employee_id is None)
    ):
        raise ApiError(401, "INVALID_TOKEN", "Invalid or expired authentication token")
    return claims


def token_matches_current_password(
    claims: dict[str, object], user: User, settings: Settings
) -> bool:
    token_version = claims.get("pwdv")
    return isinstance(token_version, str) and hmac.compare_digest(
        token_version, password_token_version(user, settings)
    )
