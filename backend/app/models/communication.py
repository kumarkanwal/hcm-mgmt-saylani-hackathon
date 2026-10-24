from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, String, Text, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class Announcement(EntityBase):
    __tablename__ = "announcements"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )

    author = relationship("User", lazy="raise")


class Notification(EntityBase):
    __tablename__ = "notifications"
    __table_args__ = (
        CheckConstraint(
            "type IN ('leave_decision', 'payslip', 'correction', 'announcement')",
            name="ck_notifications_type",
        ),
        Index("ix_notifications_user_unread", "user_id", "is_read"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    user = relationship("User", lazy="raise")
