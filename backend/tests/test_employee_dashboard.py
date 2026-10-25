from datetime import UTC, date, datetime

from sqlalchemy import select

from app.models import Attendance, LeaveRequest, LeaveType, PayrollRun, Payslip, User
from app.services import employee_dashboard_service


def test_employee_dashboard_empty_and_approved_leave_states(
    client, phase2_employee, db_factory, monkeypatch
):
    context = phase2_employee
    # UTC is still Sunday while the configured Karachi date is already Monday.
    dashboard_now = datetime(2026, 10, 25, 20, 0, tzinfo=UTC)
    monkeypatch.setattr(employee_dashboard_service, "utc_now", lambda: dashboard_now)
    empty = client.get("/api/dashboard/me", headers=context["employee_headers"])
    assert empty.status_code == 200, empty.text
    body = empty.json()
    assert body["today_status"] == {
        "date": "2026-10-26",
        "status": "not_recorded",
        "check_in": None,
        "check_out": None,
        "work_duration": "0h 0m",
    }
    assert body["hours_this_week"] == 0.0
    assert body["weekly_target_hours"] == 40
    assert len(body["daily_hours"]) == 5
    assert body["late_count"] == 0
    assert body["last_payslip"] is None

    with db_factory() as session:
        annual_id = session.scalar(
            select(LeaveType.id).where(LeaveType.code == "annual")
        )
        session.add(
            LeaveRequest(
                employee_id=context["employee"]["id"],
                leave_type_id=annual_id,
                start_date=date(2026, 10, 26),
                end_date=date(2026, 10, 26),
                days=1,
                reason="Approved day",
                status="approved",
            )
        )
        session.commit()
    on_leave = client.get("/api/dashboard/me", headers=context["employee_headers"])
    assert on_leave.status_code == 200
    assert on_leave.json()["today_status"]["status"] == "on_leave"
    annual = next(
        item for item in on_leave.json()["leave_balance"] if item["code"] == "annual"
    )
    assert annual["used"] == 1.0

    assert (
        client.get("/api/dashboard/me", headers=context["hr_headers"]).status_code
        == 403
    )
    assert client.get("/api/dashboard/me").status_code == 401


def test_employee_dashboard_hours_lates_and_latest_finalized_payslip(
    client, phase2_employee, db_factory, monkeypatch
):
    context = phase2_employee
    employee_id = context["employee"]["id"]
    dashboard_now = datetime(2026, 10, 28, 7, 0, tzinfo=UTC)
    monkeypatch.setattr(employee_dashboard_service, "utc_now", lambda: dashboard_now)
    with db_factory() as session:
        hr = session.scalar(select(User).where(User.role == "hr"))
        admin = session.scalar(select(User).where(User.role == "admin"))
        session.add_all(
            [
                Attendance(
                    employee_id=employee_id,
                    date=date(2026, 10, 26),
                    check_in=datetime(2026, 10, 26, 4, 16, tzinfo=UTC),
                    check_out=datetime(2026, 10, 26, 9, 16, tzinfo=UTC),
                    status="late",
                    source="web",
                ),
                Attendance(
                    employee_id=employee_id,
                    date=date(2026, 10, 27),
                    check_in=datetime(2026, 10, 27, 4, 0, tzinfo=UTC),
                    check_out=datetime(2026, 10, 27, 12, 0, tzinfo=UTC),
                    status="present",
                    source="web",
                ),
                Attendance(
                    employee_id=employee_id,
                    date=date(2026, 10, 28),
                    check_in=datetime(2026, 10, 28, 4, 0, tzinfo=UTC),
                    status="present",
                    source="web",
                ),
            ]
        )
        finalized = PayrollRun(
            month="2026-09",
            status="finalized",
            created_by=hr.id,
            finalized_by=admin.id,
            finalized_at=datetime(2026, 9, 30, 12, tzinfo=UTC),
            total_gross=150000,
            total_net=125000,
        )
        draft = PayrollRun(
            month="2026-10",
            status="draft",
            created_by=hr.id,
            total_gross=180000,
            total_net=150000,
        )
        session.add_all([finalized, draft])
        session.flush()
        session.add_all(
            [
                Payslip(
                    run_id=finalized.id,
                    employee_id=employee_id,
                    basic=100000,
                    hra=40000,
                    medical=10000,
                    gross=150000,
                    working_days=22,
                    paid_days=22,
                    absent_days=0,
                    unpaid_days=0,
                    half_days=0,
                    deduction=15000,
                    tax=10000,
                    net=125000,
                ),
                Payslip(
                    run_id=draft.id,
                    employee_id=employee_id,
                    basic=120000,
                    hra=48000,
                    medical=12000,
                    gross=180000,
                    working_days=22,
                    paid_days=22,
                    absent_days=0,
                    unpaid_days=0,
                    half_days=0,
                    deduction=10000,
                    tax=20000,
                    net=150000,
                ),
            ]
        )
        session.commit()

    response = client.get("/api/dashboard/me", headers=context["employee_headers"])
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["today_status"]["status"] == "present"
    assert body["today_status"]["work_duration"] == "3h 0m"
    assert body["hours_this_week"] == 13.0
    assert [item["hours"] for item in body["daily_hours"][:3]] == [5.0, 8.0, 0.0]
    assert body["late_count"] == 1
    assert body["last_payslip"] == {
        "id": body["last_payslip"]["id"],
        "month": "2026-09",
        "gross": 150000.0,
        "deductions": 15000.0,
        "tax": 10000.0,
        "net": 125000.0,
    }
