from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.exceptions import ApiError
from app.models import Attendance, AttendanceCorrection, LeaveRequest, LeaveType, User
from app.services.reporting_service import (
    get_attendance_summary,
    get_headcount,
    get_late_comers,
    get_leave_summary,
    get_my_leave_balance,
    get_payroll_summary,
    search_employees,
)


def _seed_reporting_data(client, context, db_factory):
    second = client.post(
        "/api/employees",
        headers=context["hr_headers"],
        json={
            "employee_code": "EMP-002",
            "first_name": "Second",
            "last_name": "Person",
            "email": "employee2@example.com",
            "phone": "03110000000",
            "gender": "female",
            "department_id": context["department_id"],
            "designation_id": context["designation_id"],
            "join_date": "2026-01-01",
            "basic_salary": 80000,
        },
    )
    assert second.status_code == 201, second.text
    second_id = second.json()["employee"]["id"]
    first_id = context["employee"]["id"]
    with db_factory() as session:
        annual_id = session.scalar(
            select(LeaveType.id).where(LeaveType.code == "annual")
        )
        session.add_all(
            [
                Attendance(
                    employee_id=first_id,
                    date=date(2026, 10, 20),
                    check_in=datetime(2026, 10, 20, 4, tzinfo=UTC),
                    check_out=datetime(2026, 10, 20, 12, tzinfo=UTC),
                    status="present",
                    source="web",
                ),
                Attendance(
                    employee_id=second_id,
                    date=date(2026, 10, 20),
                    check_in=datetime(2026, 10, 20, 4, 30, tzinfo=UTC),
                    check_out=datetime(2026, 10, 20, 12, tzinfo=UTC),
                    status="late",
                    source="web",
                ),
                LeaveRequest(
                    employee_id=first_id,
                    leave_type_id=annual_id,
                    start_date=date(2026, 10, 21),
                    end_date=date(2026, 10, 21),
                    days=Decimal("1.00"),
                    reason="Approved day",
                    status="approved",
                ),
                LeaveRequest(
                    employee_id=second_id,
                    leave_type_id=annual_id,
                    start_date=date(2026, 11, 2),
                    end_date=date(2026, 11, 2),
                    days=Decimal("1.00"),
                    reason="Pending day",
                    status="pending",
                ),
                AttendanceCorrection(
                    employee_id=first_id,
                    date=date(2026, 10, 22),
                    requested_check_in=datetime(2026, 10, 22, 4, tzinfo=UTC),
                    requested_check_out=datetime(2026, 10, 22, 12, tzinfo=UTC),
                    reason="Missed entry",
                    status="pending",
                ),
            ]
        )
        session.commit()
    return first_id, second_id


def test_hr_dashboard_empty_state(client, phase2_context):
    response = client.get(
        "/api/dashboard/hr?from=2026-10-20&to=2026-10-23",
        headers=phase2_context["hr_headers"],
    )
    assert response.status_code == 200
    body = response.json()
    assert body["headcount"] == 0
    assert body["present_today"] == 0
    assert body["on_leave_today"] == 0
    assert body["pending_approvals"] == {"leave": 0, "corrections": 0}
    assert body["absenteeism_by_dept"] == []
    assert body["leave_by_type"] == []
    assert body["top_late_comers"] == []


def test_hr_dashboard_aggregates_filters_and_authorization(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    _seed_reporting_data(client, context, db_factory)
    response = client.get(
        "/api/dashboard/hr?from=2026-10-20&to=2026-10-23",
        headers=context["hr_headers"],
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["headcount"] == 2
    assert body["pending_approvals"] == {"leave": 1, "corrections": 1}
    assert len(body["attendance_trend"]) == 4
    assert body["attendance_trend"][0] == {"date": "2026-10-20", "rate": 100.0}
    assert body["leave_by_type"][0]["days"] == 1.0
    assert body["top_late_comers"][0]["employee_code"] == "EMP-002"
    assert body["top_late_comers"][0]["late_count"] == 1
    assert body["absenteeism_by_dept"][0]["department"] == "Engineering"

    filtered = client.get(
        "/api/dashboard/hr?from=2026-10-20&to=2026-10-23"
        f"&department_id={context['department_id']}",
        headers=context["admin_headers"],
    )
    assert filtered.status_code == 200 and filtered.json()["headcount"] == 2
    assert (
        client.get("/api/dashboard/hr", headers=context["employee_headers"]).status_code
        == 403
    )
    assert (
        client.get(
            "/api/dashboard/hr?from=2026-10-23&to=2026-10-20",
            headers=context["hr_headers"],
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/dashboard/hr?department_id=99999", headers=context["hr_headers"]
        ).status_code
        == 404
    )


def test_ai_reporting_services_have_stable_shapes_and_employee_scope(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    first_id, _ = _seed_reporting_data(client, context, db_factory)
    with db_factory() as session:
        hr = session.scalar(select(User).where(User.email == "phase2-hr@example.com"))
        employee = session.scalar(select(User).where(User.employee_id == first_id))

        headcount = get_headcount(session, user=hr)
        assert headcount["total"] == 2
        assert headcount["by_department"][0]["department"] == "Engineering"
        summary = get_attendance_summary(
            session,
            user=employee,
            from_date=date(2026, 10, 20),
            to_date=date(2026, 10, 20),
        )
        assert summary == {
            "present": 1,
            "late": 0,
            "half_day": 0,
            "missing_checkout": 0,
            "absent": 0,
            "on_leave": 0,
            "attendance_rate": 100.0,
            "expected_work_days": 1,
        }
        late = get_late_comers(
            session,
            user=hr,
            from_date=date(2026, 10, 20),
            to_date=date(2026, 10, 20),
        )
        assert late[0]["employee_code"] == "EMP-002"
        leave = get_leave_summary(
            session,
            user=hr,
            from_date=date(2026, 10, 1),
            to_date=date(2026, 10, 31),
        )
        assert leave["by_type"][0]["days"] == 1.0
        balances = get_my_leave_balance(session, user=employee)
        assert {item["code"] for item in balances} == {
            "annual",
            "sick",
            "casual",
            "unpaid",
        }
        assert get_payroll_summary(session, user=hr, month="2026-10") == {
            "month": "2026-10",
            "employees": 0,
            "gross": 0.0,
            "net": 0.0,
        }
        matches = search_employees(session, user=hr, text="Second")
        assert matches[0]["employee_code"] == "EMP-002"
        with pytest.raises(ApiError) as forbidden:
            get_headcount(session, user=employee)
        assert forbidden.value.status_code == 403


def test_reporting_service_rejects_invalid_ranges(client, phase2_employee, db_factory):
    with db_factory() as session:
        employee = session.scalar(
            select(User).where(User.email == "employee1@example.com")
        )
        with pytest.raises(ApiError) as invalid:
            get_attendance_summary(
                session,
                user=employee,
                from_date=date(2026, 10, 2),
                to_date=date(2026, 10, 1),
            )
        assert invalid.value.status_code == 422
