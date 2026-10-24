from datetime import date

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class Department(EntityBase):
    __tablename__ = "departments"
    __table_args__ = (UniqueConstraint("name", name="uq_departments_name"),)

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    employees = relationship("Employee", back_populates="department", lazy="raise")


class Designation(EntityBase):
    __tablename__ = "designations"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    department_id: Mapped[int | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"), nullable=True, index=True
    )
    department = relationship("Department", lazy="raise")


class LeaveType(EntityBase):
    __tablename__ = "leave_types"
    __table_args__ = (
        UniqueConstraint("code", name="uq_leave_types_code"),
        CheckConstraint(
            "code IN ('annual', 'sick', 'casual', 'unpaid')",
            name="ck_leave_types_code",
        ),
        CheckConstraint(
            "yearly_quota IS NULL OR yearly_quota >= 0",
            name="ck_leave_types_yearly_quota",
        ),
    )

    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    yearly_quota: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_paid: Mapped[bool] = mapped_column(Boolean, nullable=False)


class Holiday(EntityBase):
    __tablename__ = "holidays"
    __table_args__ = (UniqueConstraint("date", name="uq_holidays_date"),)

    date: Mapped[date] = mapped_column(Date, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
