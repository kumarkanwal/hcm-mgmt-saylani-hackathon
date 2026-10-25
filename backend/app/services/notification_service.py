from sqlalchemy import insert, literal, select
from sqlalchemy.orm import Session

from app.models.communication import Notification
from app.models.user import User


def notify_employee(
    session: Session, *, employee_id: int, notification_type: str, message: str
) -> None:
    user_ids = session.scalars(
        select(User.id).where(User.employee_id == employee_id, User.is_active.is_(True))
    ).all()
    session.add_all(
        Notification(user_id=user_id, type=notification_type, message=message)
        for user_id in user_ids
    )


def notify_all_active_users(
    session: Session, *, notification_type: str, message: str
) -> None:
    session.execute(
        insert(Notification).from_select(
            ["user_id", "type", "message"],
            select(
                User.id,
                literal(notification_type),
                literal(message),
            ).where(User.is_active.is_(True)),
        )
    )
