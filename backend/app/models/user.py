from datetime import time

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    false,
    text,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class User(EntityBase):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'hr', 'employee')", name="ck_users_role"),
        CheckConstraint(
            "role != 'employee' OR employee_id IS NOT NULL",
            name="ck_users_employee_role_has_employee",
        ),
        UniqueConstraint("email", name="uq_users_email"),
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    must_change_password: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    employee_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "employees.id",
            name="fk_users_employee_id_employees_id",
            ondelete="RESTRICT",
        ),
        nullable=True,
        index=True,
    )

    employee = relationship("Employee", back_populates="users", lazy="raise")


class Settings(EntityBase):
    __tablename__ = "settings"
    __table_args__ = (
        CheckConstraint("id = 1", name="ck_settings_singleton"),
        CheckConstraint("grace_minutes >= 0", name="ck_settings_grace_minutes"),
        CheckConstraint("half_day_hours > 0", name="ck_settings_half_day_hours"),
        CheckConstraint("office_radius_m > 0", name="ck_settings_office_radius"),
    )

    # A fixed primary key plus check constraint enforces the documented single row.
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, default=1, server_default="1"
    )
    company_name: Mapped[str] = mapped_column(String(150), nullable=False)
    office_start: Mapped[time] = mapped_column(
        Time, nullable=False, default=time(9, 0), server_default=text("'09:00:00'")
    )
    grace_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=15, server_default="15"
    )
    half_day_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5, server_default="5"
    )
    weekend_days: Mapped[list[int]] = mapped_column(
        ARRAY(SmallInteger),
        nullable=False,
        default=lambda: [5, 6],
        server_default=text("ARRAY[5, 6]::smallint[]"),
    )
    office_lat: Mapped[float | None] = mapped_column(nullable=True)
    office_lng: Mapped[float | None] = mapped_column(nullable=True)
    office_radius_m: Mapped[int] = mapped_column(
        Integer, nullable=False, default=150, server_default="150"
    )
    is_setup_done: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
