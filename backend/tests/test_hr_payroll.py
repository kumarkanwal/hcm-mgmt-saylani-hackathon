from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.models import (
    Attendance,
    Employee,
    LeaveRequest,
    LeaveType,
    Notification,
    PayrollRun,
    Payslip,
    Settings,
)
from app.services.hr_utils import get_company_settings, holiday_dates, working_dates
from app.services.payroll_service import annual_tax, monthly_tax


@pytest.mark.parametrize(
    ("gross", "annual", "monthly"),
    [
        ("50000", "0.00", "0.00"),
        ("100000", "30000.00", "2500.00"),
        ("200000", "210000.00", "17500.00"),
        ("300000", "510000.00", "42500.00"),
        ("400000", "930000.00", "77500.00"),
    ],
)
def test_tax_slab_boundaries(gross, annual, monthly):
    assert annual_tax(Decimal(gross)) == Decimal(annual)
    assert monthly_tax(Decimal(gross)) == Decimal(monthly)


def seed_full_attendance(db_factory, employee_id: int, month: str = "2026-10"):
    with db_factory() as session:
        settings = get_company_settings(session)
        days = working_dates(
            date(2026, 10, 1),
            date(2026, 10, 31),
            settings.weekend_days,
            holiday_dates(session, date(2026, 10, 1), date(2026, 10, 31)),
        )
        session.add_all(
            Attendance(
                employee_id=employee_id,
                date=day,
                check_in=datetime(day.year, day.month, day.day, 4, tzinfo=UTC),
                check_out=datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
                status="present",
                source="web",
            )
            for day in days
        )
        session.commit()


def test_payroll_lifecycle_snapshot_pdf_notifications_and_permissions(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    employee_id = context["employee"]["id"]
    second = client.post(
        "/api/employees",
        headers=context["hr_headers"],
        json={
            "employee_code": "EMP-002",
            "first_name": "Second",
            "last_name": "Employee",
            "email": "payroll-second@example.com",
            "phone": "03220000000",
            "gender": "female",
            "department_id": context["department_id"],
            "designation_id": context["designation_id"],
            "join_date": "2026-01-01",
            "basic_salary": 80000,
        },
    )
    assert second.status_code == 201, second.text
    second_id = second.json()["employee"]["id"]
    seed_full_attendance(db_factory, employee_id)
    seed_full_attendance(db_factory, second_id)
    draft = client.post(
        "/api/payroll/runs",
        headers=context["hr_headers"],
        json={"month": "2026-10"},
    )
    assert draft.status_code == 200, draft.text
    body = draft.json()
    run_id = body["id"]
    slip = body["payslips"][0]
    second_slip = next(
        item for item in body["payslips"] if item["employee_id"] == second_id
    )
    assert slip["gross"] == 150000.0
    assert slip["absent_days"] == 0.0
    assert slip["tax"] == 10000.0
    assert slip["net"] == 140000.0
    assert (
        client.post(
            "/api/payroll/runs",
            headers=context["hr_headers"],
            json={"month": "2026-10"},
        ).status_code
        == 409
    )
    assert (
        client.get(
            f"/api/payslips/{slip['id']}/pdf", headers=context["employee_headers"]
        ).status_code
        == 403
    )
    assert (
        client.post(
            f"/api/payroll/runs/{run_id}/finalize", headers=context["hr_headers"]
        ).status_code
        == 403
    )
    finalized = client.post(
        f"/api/payroll/runs/{run_id}/finalize", headers=context["admin_headers"]
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "finalized"
    assert (
        client.post(
            f"/api/payroll/runs/{run_id}/recalculate", headers=context["hr_headers"]
        ).status_code
        == 409
    )

    assert (
        client.put(
            f"/api/employees/{employee_id}/salary",
            headers=context["hr_headers"],
            json={"basic": 200000},
        ).status_code
        == 200
    )
    stored = client.get(
        f"/api/payroll/runs/{run_id}", headers=context["hr_headers"]
    ).json()["payslips"][0]
    assert stored["basic"] == 100000.0
    assert stored["gross"] == 150000.0
    mine = client.get("/api/payslips/me", headers=context["employee_headers"])
    assert mine.status_code == 200 and mine.json()["total"] == 1
    pdf = client.get(
        f"/api/payslips/{slip['id']}/pdf", headers=context["employee_headers"]
    )
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")
    assert b"2026-10" in pdf.content
    assert b"150,000.00" in pdf.content
    assert (
        client.get(
            f"/api/payslips/{second_slip['id']}/pdf",
            headers=context["employee_headers"],
        ).status_code
        == 403
    )
    assert (
        client.get(
            "/api/payslips/99999/pdf", headers=context["employee_headers"]
        ).status_code
        == 404
    )
    with db_factory() as session:
        assert session.scalar(select(func.count(Notification.id))) == 2


def test_payroll_proration_absence_unpaid_and_half_day(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    employee_id = context["employee"]["id"]
    with db_factory() as session:
        employee = session.get(Employee, employee_id)
        employee.join_date = date(2026, 10, 15)
        employee.exit_date = date(2026, 10, 26)
        employee.status = "exited"
        unpaid_id = session.scalar(
            select(LeaveType.id).where(LeaveType.code == "unpaid")
        )
        session.add(
            LeaveRequest(
                employee_id=employee_id,
                leave_type_id=unpaid_id,
                start_date=date(2026, 10, 19),
                end_date=date(2026, 10, 19),
                days=Decimal("1.00"),
                reason="Unpaid",
                status="approved",
            )
        )
        settings = get_company_settings(session)
        days = working_dates(
            date(2026, 10, 15),
            date(2026, 10, 31),
            settings.weekend_days,
            set(),
        )
        for day in days:
            if day in {date(2026, 10, 19), date(2026, 10, 21)}:
                continue
            status = "half_day" if day == date(2026, 10, 20) else "present"
            session.add(
                Attendance(
                    employee_id=employee_id,
                    date=day,
                    check_in=datetime(day.year, day.month, day.day, 4, tzinfo=UTC),
                    check_out=datetime(
                        day.year,
                        day.month,
                        day.day,
                        8 if status == "half_day" else 12,
                        tzinfo=UTC,
                    ),
                    status=status,
                    source="web",
                )
            )
        session.commit()
    run = client.post(
        "/api/payroll/runs",
        headers=context["hr_headers"],
        json={"month": "2026-10"},
    )
    assert run.status_code == 200, run.text
    slip = run.json()["payslips"][0]
    assert slip["working_days"] == 22
    assert slip["paid_days"] == 5.5
    assert slip["absent_days"] == 1.0
    assert slip["unpaid_days"] == 1.0
    assert slip["half_days"] == 1.0
    assert slip["gross"] == 54545.45
    assert slip["deduction"] == 17045.45
    assert slip["net"] == 27500.0
    with db_factory() as session:
        assert session.scalar(select(func.count(Payslip.id))) == 1


def test_payroll_rejects_a_month_with_no_working_days(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    with db_factory() as session:
        settings = session.get(Settings, 1)
        settings.weekend_days = [0, 1, 2, 3, 4, 5, 6]
        session.commit()
    response = client.post(
        "/api/payroll/runs",
        headers=context["hr_headers"],
        json={"month": "2026-10"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NO_WORKING_DAYS"
    with db_factory() as session:
        assert session.scalar(select(func.count(PayrollRun.id))) == 0
