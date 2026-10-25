from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.communication import (
    AnnouncementCreate,
    AnnouncementListResponse,
    AnnouncementResponse,
    NotificationListResponse,
    NotificationResponse,
)
from app.services.communication_service import (
    create_announcement,
    list_announcements,
    list_notifications,
    mark_notification_read,
)

router = APIRouter(prefix="/api", tags=["communications"])
Database = Annotated[Session, Depends(get_db)]
AnyRole = Annotated[User, Depends(require_role("admin", "hr", "employee"))]
Management = Annotated[User, Depends(require_role("admin", "hr"))]


@router.get("/announcements", response_model=AnnouncementListResponse)
def read_announcements(
    _: AnyRole,
    session: Database,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_announcements(session, page=page, page_size=page_size)


@router.post(
    "/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_announcement(
    payload: AnnouncementCreate, actor: Management, session: Database
) -> dict:
    return create_announcement(session, actor=actor, payload=payload)


@router.get("/notifications", response_model=NotificationListResponse)
def read_notifications(
    user: AnyRole,
    session: Database,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_notifications(session, user=user, page=page, page_size=page_size)


@router.patch(
    "/notifications/{notification_id}/read", response_model=NotificationResponse
)
def read_notification(notification_id: int, user: AnyRole, session: Database) -> dict:
    return mark_notification_read(session, user=user, notification_id=notification_id)
