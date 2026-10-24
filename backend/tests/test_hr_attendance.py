from datetime import UTC, date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import func, select

from app.core.exceptions import ApiError
from app.models import (
    Attendance,
    AuditLog,
    Holiday,
    LeaveRequest,
    LeaveType,
    Notification,
    PayrollRun,
    Settings,
    User,
)
from app.schemas.hr import CheckInRequest
from app.services.attendance_service import check_in, check_out

KARACHI = ZoneInfo("Asia/Karachi")


def employee_user(session):
    return session.scalar(select(User).where(User.role == "employee"))


def test_attendance_boundary_duplicate_and_checkout_rules(phase2_employee, db_factory):
    with db_factory() as session:
        user = employee_user(session)
        at_0915 = datetime(2026, 10, 26, 9, 15, tzinfo=KARACHI).astimezone(UTC)
        result = check_in(
            session, user=user, payload=CheckInRequest(source="web"), now=at_0915
        )
        assert result["status"] == "present"
        with pytest.raises(ApiError) as duplicate:
            check_in(
                session,
                user=user,
                payload=CheckInRequest(source="web"),
                now=at_0915,
            )
        assert duplicate.value.status_code == 409
        checked_out = check_out(
            session,
            user=user,
            now=datetime(2026, 10, 26, 14, 15, tzinfo=KARACHI).astimezone(UTC),
        )
        assert checked_out["status"] == "present"
        with pytest.raises(ApiError) as second_checkout:
            check_out(
                session,
                user=user,
                now=datetime(2026, 10, 26, 15, 0, tzinfo=KARACHI).astimezone(UTC),
            )
        assert second_checkout.value.status_code == 409


def test_attendance_late_half_day_and_non_working_rejections(
    phase2_employee, db_factory
):
    with db_factory() as session:
        user = employee_user(session)
        with pytest.raises(ApiError) as no_check_in:
            check_out(
                session,
                user=user,
                now=datetime(2026, 10, 26, 17, 0, tzinfo=KARACHI).astimezone(UTC),
            )
        assert no_check_in.value.code == "CHECK_IN_REQUIRED"
        late = check_in(
            session,
            user=user,
            payload=CheckInRequest(source="web"),
            now=datetime(2026, 10, 27, 9, 16, tzinfo=KARACHI).astimezone(UTC),
        )
        assert late["status"] == "late"
        half_day = check_out(
            session,
            user=user,
            now=datetime(2026, 10, 27, 13, 0, tzinfo=KARACHI).astimezone(UTC),
        )
        assert half_day["status"] == "half_day"
        with pytest.raises(ApiError) as weekend:
            check_in(
                session,
                user=user,
                payload=CheckInRequest(source="web"),
                now=datetime(2026, 10, 25, 9, 0, tzinfo=KARACHI).astimezone(UTC),
            )
        assert weekend.value.code == "NON_WORKING_DAY"
        session.add(Holiday(date=date(2026, 10, 28), name="Holiday"))
        session.commit()
        with pytest.raises(ApiError) as holiday:
            check_in(
                session,
                user=user,
                payload=CheckInRequest(source="web"),
                now=datetime(2026, 10, 28, 9, 0, tzinfo=KARACHI).astimezone(UTC),
            )
        assert holiday.value.code == "NON_WORKING_DAY"
        annual_id = session.scalar(
            select(LeaveType.id).where(LeaveType.code == "annual")
        )
        session.add(
            LeaveRequest(
                employee_id=user.employee_id,
                leave_type_id=annual_id,
                start_date=date(2026, 10, 29),
                end_date=date(2026, 10, 29),
                days=1,
                reason="Approved leave",
                status="approved",
            )
        )
        session.commit()
        with pytest.raises(ApiError) as on_leave:
            check_in(
                session,
                user=user,
                payload=CheckInRequest(source="web"),
                now=datetime(2026, 10, 29, 9, 0, tzinfo=KARACHI).astimezone(UTC),
            )
        assert on_leave.value.code == "EMPLOYEE_ON_LEAVE"
        settings = session.get(Settings, 1)
        settings.office_lat = Decimal("24.860700")
        settings.office_lng = Decimal("67.001100")
        session.commit()
        camera = check_in(
            session,
            user=user,
            payload=CheckInRequest(
                source="camera", lat=24.8607, lng=67.0011, accuracy=10
            ),
            now=datetime(2026, 10, 30, 9, 0, tzinfo=KARACHI).astimezone(UTC),
        )
        assert camera["source"] == "camera"


def test_attendance_calendar_board_absent_and_missing_checkout(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    employee_id = context["employee"]["id"]
    with db_factory() as session:
        session.add(
            Attendance(
                employee_id=employee_id,
                date=date(2026, 10, 20),
                check_in=datetime(2026, 10, 20, 4, 0, tzinfo=UTC),
                status="present",
                source="web",
            )
        )
        session.commit()
    calendar = client.get(
        "/api/attendance/me?month=2026-10", headers=context["employee_headers"]
    )
    assert calendar.status_code == 200
    statuses = {item["date"]: item["status"] for item in calendar.json()["items"]}
    assert statuses["2026-10-20"] == "missing_checkout"
    assert statuses["2026-10-19"] == "absent"
    assert statuses["2026-10-25"] == "weekend"
    board = client.get(
        "/api/attendance/board?date=2026-10-20", headers=context["hr_headers"]
    )
    assert board.status_code == 200
    assert board.json()[0]["status"] == "missing_checkout"
    assert (
        client.get(
            "/api/attendance/board?date=2026-10-20", headers=context["employee_headers"]
        ).status_code
        == 403
    )


def test_correction_approval_updates_attendance_and_notifies(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    date_mismatch = client.post(
        "/api/attendance/corrections",
        headers=context["employee_headers"],
        json={
            "date": "2026-10-19",
            "requested_check_in": "2026-10-20T09:10:00+05:00",
            "reason": "Wrong date",
        },
    )
    assert date_mismatch.status_code == 422
    assert date_mismatch.json()["detail"]["code"] == "CORRECTION_DATE_MISMATCH"
    correction = client.post(
        "/api/attendance/corrections",
        headers=context["employee_headers"],
        json={
            "date": "2026-10-20",
            "requested_check_in": "2026-10-20T09:10:00+05:00",
            "requested_check_out": "2026-10-20T17:10:00+05:00",
            "reason": "Forgot to check in",
        },
    )
    assert correction.status_code == 200, correction.text
    correction_id = correction.json()["id"]
    duplicate = client.post(
        "/api/attendance/corrections",
        headers=context["employee_headers"],
        json={
            "date": "2026-10-20",
            "requested_check_in": "2026-10-20T09:00:00+05:00",
            "reason": "Duplicate",
        },
    )
    assert duplicate.status_code == 409
    assert (
        client.patch(
            f"/api/attendance/corrections/{correction_id}",
            headers=context["employee_headers"],
            json={"action": "approve"},
        ).status_code
        == 403
    )
    approved = client.patch(
        f"/api/attendance/corrections/{correction_id}",
        headers=context["hr_headers"],
        json={"action": "approve", "comment": "Verified"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved"
    repeated = client.patch(
        f"/api/attendance/corrections/{correction_id}",
        headers=context["hr_headers"],
        json={"action": "reject"},
    )
    assert repeated.status_code == 409
    rejected_request = client.post(
        "/api/attendance/corrections",
        headers=context["employee_headers"],
        json={
            "date": "2026-10-21",
            "requested_check_in": "2026-10-21T09:10:00+05:00",
            "reason": "Reject this one",
        },
    )
    rejected = client.patch(
        f"/api/attendance/corrections/{rejected_request.json()['id']}",
        headers=context["hr_headers"],
        json={"action": "reject", "comment": "Not verified"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    locked_request = client.post(
        "/api/attendance/corrections",
        headers=context["employee_headers"],
        json={
            "date": "2026-10-22",
            "requested_check_in": "2026-10-22T09:10:00+05:00",
            "reason": "Locked month",
        },
    )
    with db_factory() as session:
        hr_user = session.scalar(select(User).where(User.role == "hr"))
        session.add(
            PayrollRun(
                month="2026-10",
                status="finalized",
                created_by=hr_user.id,
                finalized_by=hr_user.id,
            )
        )
        session.commit()
    locked = client.patch(
        f"/api/attendance/corrections/{locked_request.json()['id']}",
        headers=context["hr_headers"],
        json={"action": "approve"},
    )
    assert locked.status_code == 409
    assert locked.json()["detail"]["code"] == "PAYROLL_FINALIZED"
    with db_factory() as session:
        attendance = session.scalar(
            select(Attendance).where(Attendance.date == date(2026, 10, 20))
        )
        assert attendance is not None and attendance.status == "present"
        assert session.scalar(select(func.count(Notification.id))) == 2
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "attendance_corrections"
                )
            )
            == 5
        )
