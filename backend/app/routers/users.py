from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.admin import (
    HRUserCreate,
    HRUserCreateResponse,
    ResetPasswordResponse,
    UserAdminResponse,
    UserListResponse,
)
from app.services.admin_service import (
    create_hr_user,
    deactivate_user,
    list_users,
    reset_user_password,
)

router = APIRouter(prefix="/api/users", tags=["users"])
Admin = Annotated[User, Depends(require_role("admin"))]
Database = Annotated[Session, Depends(get_db)]
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("", response_model=UserListResponse)
def read_users(
    _: Admin, session: Database, page: Page = 1, page_size: PageSize = 20
) -> dict:
    return list_users(session, page=page, page_size=page_size)


@router.post(
    "", response_model=HRUserCreateResponse, status_code=status.HTTP_201_CREATED
)
def write_hr_user(
    payload: HRUserCreate, actor: Admin, session: Database
) -> HRUserCreateResponse:
    user, temporary_password = create_hr_user(session, actor=actor, payload=payload)
    return HRUserCreateResponse(
        user=UserAdminResponse.model_validate(user, from_attributes=True),
        temp_password=temporary_password,
    )


@router.patch("/{user_id}/deactivate", response_model=UserAdminResponse)
def disable_user(user_id: int, actor: Admin, session: Database) -> UserAdminResponse:
    return UserAdminResponse.model_validate(
        deactivate_user(session, actor=actor, target_user_id=user_id),
        from_attributes=True,
    )


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
def reset_password(
    user_id: int, actor: Admin, session: Database
) -> ResetPasswordResponse:
    return ResetPasswordResponse(
        temp_password=reset_user_password(session, actor=actor, target_user_id=user_id)
    )
