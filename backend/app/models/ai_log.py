from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class AILog(EntityBase):
    __tablename__ = "ai_logs"
    __table_args__ = (
        CheckConstraint(
            "feature IN ('chat', 'summary', 'smart_leave')", name="ck_ai_logs_feature"
        ),
        CheckConstraint("latency_ms >= 0", name="ck_ai_logs_latency"),
        Index("ix_ai_logs_user_created_at", "user_id", "created_at"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    feature: Mapped[str] = mapped_column(String(30), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tools_called: Mapped[list[Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    response: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)

    user = relationship("User", lazy="raise")
