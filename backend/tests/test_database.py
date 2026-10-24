from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.models import (
    Attendance,
    Base,
    Department,
    Designation,
    Employee,
    PayrollRun,
    Payslip,
    User,
)

EXPECTED_TABLES = {
    "users",
    "settings",
    "departments",
    "designations",
    "leave_types",
    "holidays",
    "employees",
    "salary_structures",
    "attendance",
    "attendance_corrections",
    "leave_requests",
    "payroll_runs",
    "payslips",
    "announcements",
    "notifications",
    "audit_logs",
    "ai_logs",
}


def test_migration_creates_all_contract_tables_and_revision(test_engine):
    inspector = inspect(test_engine)
    assert set(inspector.get_table_names()) == EXPECTED_TABLES | {"alembic_version"}
    assert inspector.get_foreign_keys("users")
    audit_actor_fk = next(
        item
        for item in inspector.get_foreign_keys("audit_logs")
        if item["constrained_columns"] == ["actor_id"]
    )
    assert audit_actor_fk["options"]["ondelete"] == "RESTRICT"
    leave_type_checks = {
        item["name"] for item in inspector.get_check_constraints("leave_types")
    }
    assert {"ck_leave_types_code", "ck_leave_types_yearly_quota"}.issubset(
        leave_type_checks
    )
    assert inspector.get_unique_constraints("users")
    assert inspector.get_unique_constraints("attendance")
    assert inspector.get_unique_constraints("payroll_runs")
    assert inspector.get_unique_constraints("payslips")
    with test_engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version"))
            == "a49dab4c246b"
        )


def test_password_hash_storage_and_unique_email_constraint(db_factory):
    with db_factory() as session:
        session.add(
            User(email="unique@example.com", password_hash="bcrypt-hash", role="admin")
        )
        session.commit()
        session.add(User(email="unique@example.com", password_hash="other", role="hr"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()


def test_database_transaction_rolls_back_failed_write(db_factory):
    with db_factory() as session:
        session.add(
            User(email="rollback@example.com", password_hash="hash", role="admin")
        )
        session.flush()
        session.rollback()
    with db_factory() as session:
        assert (
            session.scalar(select(User).where(User.email == "rollback@example.com"))
            is None
        )


def test_all_financial_columns_use_numeric_not_float():
    for table_name in ("salary_structures", "payslips", "payroll_runs"):
        table = Base.metadata.tables[table_name]
        money_columns = {
            column.name: column.type
            for column in table.columns
            if column.name
            in {
                "basic",
                "hra",
                "medical",
                "gross",
                "deduction",
                "tax",
                "net",
                "total_gross",
                "total_net",
            }
        }
        assert money_columns
        assert all(
            type(column).__name__ == "Numeric" for column in money_columns.values()
        )
    assert Decimal("1.10") + Decimal("2.20") == Decimal("3.30")


def test_financial_rule_and_status_constraints_exist(test_engine):
    inspector = inspect(test_engine)
    salary_checks = {
        item["name"] for item in inspector.get_check_constraints("salary_structures")
    }
    assert "ck_salary_structures_hra_rate" in salary_checks
    assert "ck_salary_structures_medical_rate" in salary_checks
    user_checks = {item["name"] for item in inspector.get_check_constraints("users")}
    assert "ck_users_role" in user_checks
    assert "ck_users_employee_role_has_employee" in user_checks


def test_employee_attendance_payroll_and_payslip_uniqueness(db_factory):
    with db_factory() as session:
        admin = User(email="admin@example.com", password_hash="hash", role="admin")
        department = Department(name="Operations")
        designation = Designation(name="Coordinator")
        session.add_all([admin, department, designation])
        session.flush()
        employee = Employee(
            employee_code="E-100",
            first_name="Ada",
            last_name="Example",
            email="ada@example.com",
            phone="03000000000",
            gender="female",
            department_id=department.id,
            designation_id=designation.id,
            join_date=date(2026, 1, 1),
            status="active",
        )
        session.add(employee)
        session.commit()

        session.add(
            Employee(
                employee_code="E-100",
                first_name="Another",
                last_name="Person",
                email="another@example.com",
                phone="03000000001",
                gender="other",
                department_id=department.id,
                designation_id=designation.id,
                join_date=date(2026, 1, 1),
                status="active",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        session.add(
            Attendance(
                employee_id=employee.id,
                date=date(2026, 10, 25),
                check_in=datetime(2026, 10, 25, 4, tzinfo=UTC),
                status="present",
                source="web",
            )
        )
        session.commit()
        session.add(
            Attendance(
                employee_id=employee.id,
                date=date(2026, 10, 25),
                check_in=datetime(2026, 10, 25, 5, tzinfo=UTC),
                status="present",
                source="web",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        run = PayrollRun(month="2026-10", created_by=admin.id)
        session.add(run)
        session.commit()
        session.add(PayrollRun(month="2026-10", created_by=admin.id))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        payslip = Payslip(
            run_id=run.id,
            employee_id=employee.id,
            basic=Decimal("100.00"),
            hra=Decimal("40.00"),
            medical=Decimal("10.00"),
            gross=Decimal("150.00"),
            working_days=20,
            paid_days=Decimal("20.00"),
            absent_days=Decimal("0.00"),
            unpaid_days=Decimal("0.00"),
            half_days=Decimal("0.00"),
            deduction=Decimal("0.00"),
            tax=Decimal("0.00"),
            net=Decimal("150.00"),
        )
        session.add(payslip)
        session.commit()
        session.add(
            Payslip(
                run_id=run.id,
                employee_id=employee.id,
                basic=Decimal("100.00"),
                hra=Decimal("40.00"),
                medical=Decimal("10.00"),
                gross=Decimal("150.00"),
                working_days=20,
                paid_days=Decimal("20.00"),
                absent_days=Decimal("0.00"),
                unpaid_days=Decimal("0.00"),
                half_days=Decimal("0.00"),
                deduction=Decimal("0.00"),
                tax=Decimal("0.00"),
                net=Decimal("150.00"),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
