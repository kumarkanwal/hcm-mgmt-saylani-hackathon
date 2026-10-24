from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rate_limit import limiter, login_rate_limit_key
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    UserResponse,
)
from app.services.auth_service import (
    change_password,
    get_authenticated_user_response,
    login,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
@limiter.limit(get_settings().auth_login_rate_limit, key_func=login_rate_limit_key)
def login_user(
    request: Request,
    payload: LoginRequest,
    session: Annotated[Session, Depends(get_db)],
) -> LoginResponse:
    return LoginResponse.model_validate(login(session, payload))


@router.get("/me", response_model=UserResponse)
def get_me(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> UserResponse:
    return get_authenticated_user_response(session, user.id)


@router.post("/change-password")
def update_password(
    payload: ChangePasswordRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_db)],
) -> dict[str, str]:
    change_password(
        session,
        user=user,
        old_password=payload.old_password,
        new_password=payload.new_password,
    )
    return {"message": "Password changed successfully"}
