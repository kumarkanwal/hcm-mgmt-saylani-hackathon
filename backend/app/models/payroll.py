from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class PayrollRun(EntityBase):
    __tablename__ = "payroll_runs"
    __table_args__ = (
        CheckConstraint(
            "month ~ '^\\d{4}-(0[1-9]|1[0-2])$'", name="ck_payroll_runs_month"
        ),
        CheckConstraint(
            "status IN ('draft', 'finalized')", name="ck_payroll_runs_status"
        ),
        UniqueConstraint("month", name="uq_payroll_runs_month"),
    )

    month: Mapped[str] = mapped_column(String(7), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default=text("'draft'")
    )
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    finalized_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    finalized_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_gross: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, default=Decimal("0.00"), server_default="0"
    )
    total_net: Mapped[Decimal] = mapped_column(
        Numeric(16, 2), nullable=False, default=Decimal("0.00"), server_default="0"
    )

    creator = relationship("User", foreign_keys=[created_by], lazy="raise")
    finalizer = relationship("User", foreign_keys=[finalized_by], lazy="raise")
    payslips = relationship("Payslip", back_populates="run", lazy="raise")


class Payslip(EntityBase):
    __tablename__ = "payslips"
    __table_args__ = (
        UniqueConstraint("run_id", "employee_id", name="uq_payslips_run_employee"),
        Index("ix_payslips_employee", "employee_id"),
        CheckConstraint("working_days >= 0", name="ck_payslips_working_days"),
        CheckConstraint("paid_days >= 0", name="ck_payslips_paid_days"),
    )

    run_id: Mapped[int] = mapped_column(
        ForeignKey("payroll_runs.id", ondelete="RESTRICT"), nullable=False
    )
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    basic: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    hra: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    medical: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    gross: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    working_days: Mapped[int] = mapped_column(Integer, nullable=False)
    paid_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    absent_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    unpaid_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    half_days: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    deduction: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tax: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    net: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    run = relationship("PayrollRun", back_populates="payslips", lazy="raise")
    employee = relationship("Employee", lazy="raise")
