from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import ApiError
from app.core.security import decode_access_token, token_matches_current_password
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApiError(401, "UNAUTHENTICATED", "Authentication is required")

    settings = get_settings()
    claims = decode_access_token(credentials.credentials, settings)
    user = session.scalar(select(User).where(User.id == int(claims["sub"])))
    if (
        user is None
        or not user.is_active
        or not token_matches_current_password(claims, user, settings)
    ):
        raise ApiError(401, "UNAUTHENTICATED", "Authentication is required")
    if user.role == "employee" and user.employee_id is None:
        raise ApiError(
            401, "UNAUTHENTICATED", "Employee account is not linked to an employee"
        )

    # Current role and employee association come from the database, never stale JWT claims.
    if user.must_change_password and not (
        (request.method == "GET" and request.url.path == "/api/auth/me")
        or (
            request.method == "POST" and request.url.path == "/api/auth/change-password"
        )
    ):
        raise ApiError(
            403,
            "PASSWORD_CHANGE_REQUIRED",
            "Change your password before using this endpoint",
        )
    return user


def require_role(*roles: str) -> Callable[..., User]:
    allowed = frozenset(roles)

    def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed:
            raise ApiError(
                403, "FORBIDDEN", "You do not have permission to perform this action"
            )
        return user

    return dependency


def require_employee_scope(user: User, employee_id: int) -> None:
    if user.role == "employee" and user.employee_id != employee_id:
        raise ApiError(403, "FORBIDDEN", "You cannot access another employee's records")
