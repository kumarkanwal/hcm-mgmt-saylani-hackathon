from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import EntityBase


class Employee(EntityBase):
    __tablename__ = "employees"
    __table_args__ = (
        CheckConstraint(
            "gender IN ('male', 'female', 'other')", name="ck_employees_gender"
        ),
        CheckConstraint(
            "status IN ('probation', 'active', 'exited')", name="ck_employees_status"
        ),
        UniqueConstraint("employee_code", name="uq_employees_employee_code"),
        UniqueConstraint("email", name="uq_employees_email"),
    )

    employee_code: Mapped[str] = mapped_column(String(50), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(40), nullable=False)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gender: Mapped[str] = mapped_column(String(20), nullable=False)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    designation_id: Mapped[int] = mapped_column(
        ForeignKey("designations.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    join_date: Mapped[date] = mapped_column(Date, nullable=False)
    exit_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="probation",
        server_default=text("'probation'"),
    )

    department = relationship("Department", back_populates="employees", lazy="raise")
    designation = relationship("Designation", lazy="raise")
    users = relationship("User", back_populates="employee", lazy="raise")
    salary_structure = relationship(
        "SalaryStructure", back_populates="employee", uselist=False, lazy="raise"
    )


class SalaryStructure(EntityBase):
    __tablename__ = "salary_structures"
    __table_args__ = (
        UniqueConstraint("employee_id", name="uq_salary_structures_employee"),
        CheckConstraint("basic > 0", name="ck_salary_structures_basic_positive"),
        CheckConstraint("hra >= 0", name="ck_salary_structures_hra_nonnegative"),
        CheckConstraint(
            "medical >= 0", name="ck_salary_structures_medical_nonnegative"
        ),
        CheckConstraint(
            "hra = round(basic * 0.4, 2)", name="ck_salary_structures_hra_rate"
        ),
        CheckConstraint(
            "medical = round(basic * 0.1, 2)", name="ck_salary_structures_medical_rate"
        ),
    )

    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="RESTRICT"), nullable=False
    )
    basic: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    hra: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    medical: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)

    employee = relationship("Employee", back_populates="salary_structure", lazy="raise")
