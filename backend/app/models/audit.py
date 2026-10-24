from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class AuditLog(EntityBase):
    __tablename__ = "audit_logs"
    __table_args__ = (
        CheckConstraint(
            "action IN ('create', 'update', 'approve', 'reject', 'finalize', 'login', 'deactivate', 'reset')",
            name="ck_audit_logs_action",
        ),
        Index("ix_audit_logs_entity", "entity", "entity_id"),
        Index("ix_audit_logs_created_at", "created_at"),
    )

    # Nullable actor supports system-initiated first-run setup without inventing a user.
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    entity: Mapped[str] = mapped_column(String(80), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    before: Mapped[dict[str, Any] | None] = mapped_column(
        "before", JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    after: Mapped[dict[str, Any] | None] = mapped_column(
        "after", JSON().with_variant(JSONB, "postgresql"), nullable=True
    )

    actor = relationship("User", lazy="raise")
