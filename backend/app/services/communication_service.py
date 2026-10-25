from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.communication import Announcement, Notification
from app.models.employee import Employee
from app.models.user import User
from app.schemas.communication import AnnouncementCreate
from app.services.audit_service import write_audit_log
from app.services.notification_service import notify_all_active_users
from app.services.transactions import commit_or_rollback

NOTIFICATION_DISPLAY = {
    "leave_decision": ("Leave request update", "/leaves"),
    "payslip": ("New payslip available", "/payslips"),
    "correction": ("Attendance correction update", "/attendance"),
    "announcement": ("New announcement", "/announcements"),
}


def _author_name(email: str, first_name: str | None, last_name: str | None) -> str:
    name = " ".join(part for part in (first_name, last_name) if part).strip()
    return name or email


def _announcement_dict(row) -> dict[str, Any]:
    announcement, email, role, first_name, last_name = row
    return {
        "id": announcement.id,
        "title": announcement.title,
        "body": announcement.body,
        "author_id": announcement.author_id,
        "author_name": _author_name(email, first_name, last_name),
        "author_role": role,
        "created_at": announcement.created_at,
    }


def _announcement_query():
    return (
        select(
            Announcement,
            User.email,
            User.role,
            Employee.first_name,
            Employee.last_name,
        )
        .join(User, User.id == Announcement.author_id)
        .outerjoin(Employee, Employee.id == User.employee_id)
    )


def list_announcements(
    session: Session, *, page: int, page_size: int
) -> dict[str, Any]:
    total = session.scalar(select(func.count(Announcement.id))) or 0
    rows = session.execute(
        _announcement_query()
        .order_by(Announcement.created_at.desc(), Announcement.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_announcement_dict(row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def create_announcement(
    session: Session, *, actor: User, payload: AnnouncementCreate
) -> dict[str, Any]:
    with commit_or_rollback(session):
        announcement = Announcement(
            title=payload.title,
            body=payload.body,
            author_id=actor.id,
        )
        session.add(announcement)
        session.flush()
        notify_all_active_users(
            session,
            notification_type="announcement",
            message=f"New announcement: {announcement.title}",
        )
        write_audit_log(
            session,
            actor_id=actor.id,
            action="create",
            entity="announcements",
            entity_id=announcement.id,
            after={
                "title": announcement.title,
                "body": announcement.body,
                "author_id": announcement.author_id,
            },
        )
    row = session.execute(
        _announcement_query().where(Announcement.id == announcement.id)
    ).one()
    return _announcement_dict(row)


def _notification_dict(notification: Notification) -> dict[str, Any]:
    title, link = NOTIFICATION_DISPLAY[notification.type]
    return {
        "id": notification.id,
        "title": title,
        "body": notification.message,
        "message": notification.message,
        "type": notification.type,
        "link": link,
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


def list_notifications(
    session: Session, *, user: User, page: int, page_size: int
) -> dict[str, Any]:
    own = Notification.user_id == user.id
    total = session.scalar(select(func.count(Notification.id)).where(own)) or 0
    unread = (
        session.scalar(
            select(func.count(Notification.id)).where(
                own, Notification.is_read.is_(False)
            )
        )
        or 0
    )
    items = session.scalars(
        select(Notification)
        .where(own)
        .order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_notification_dict(item) for item in items],
        "total": total,
        "unread_count": unread,
        "page": page,
        "page_size": page_size,
    }


def mark_notification_read(
    session: Session, *, user: User, notification_id: int
) -> dict[str, Any]:
    with commit_or_rollback(session):
        notification = session.scalar(
            select(Notification)
            .where(
                Notification.id == notification_id,
                Notification.user_id == user.id,
            )
            .with_for_update()
        )
        if notification is None:
            raise ApiError(404, "NOTIFICATION_NOT_FOUND", "Notification was not found")
        if not notification.is_read:
            notification.is_read = True
            write_audit_log(
                session,
                actor_id=user.id,
                action="update",
                entity="notifications",
                entity_id=notification.id,
                before={"is_read": False},
                after={"is_read": True},
            )
    return _notification_dict(notification)
