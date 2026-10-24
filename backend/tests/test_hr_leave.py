from datetime import date

from sqlalchemy import func, select

from app.models import AuditLog, Holiday, LeaveRequest, LeaveType, Notification


def leave_type_id(db_factory, code: str) -> int:
    with db_factory() as session:
        return session.scalar(select(LeaveType.id).where(LeaveType.code == code))


def test_leave_working_days_balance_overlap_and_over_balance(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    annual_id = leave_type_id(db_factory, "annual")
    with db_factory() as session:
        session.add(Holiday(date=date(2026, 10, 28), name="Midweek Holiday"))
        session.commit()
    created = client.post(
        "/api/leaves",
        headers=context["employee_headers"],
        json={
            "leave_type_id": annual_id,
            "start_date": "2026-10-26",
            "end_date": "2026-11-01",
            "reason": "Family event",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["days"] == 4.0
    balance = client.get("/api/leaves/balance", headers=context["employee_headers"])
    annual = next(item for item in balance.json() if item["code"] == "annual")
    assert annual["pending"] == 4.0
    assert annual["remaining"] == 10.0
    overlap = client.post(
        "/api/leaves",
        headers=context["employee_headers"],
        json={
            "leave_type_id": annual_id,
            "start_date": "2026-10-30",
            "end_date": "2026-11-02",
            "reason": "Overlap",
        },
    )
    assert overlap.status_code == 422
    assert overlap.json()["detail"]["code"] == "LEAVE_OVERLAP"
    weekend = client.post(
        "/api/leaves",
        headers=context["employee_headers"],
        json={
            "leave_type_id": annual_id,
            "start_date": "2026-11-07",
            "end_date": "2026-11-08",
            "reason": "Weekend",
        },
    )
    assert weekend.status_code == 422
    assert weekend.json()["detail"]["code"] == "LEAVE_NO_WORKING_DAYS"
    over_balance = client.post(
        "/api/leaves",
        headers=context["employee_headers"],
        json={
            "leave_type_id": annual_id,
            "start_date": "2026-11-09",
            "end_date": "2026-11-27",
            "reason": "Too long",
        },
    )
    assert over_balance.status_code == 422
    assert over_balance.json()["detail"]["code"] == "LEAVE_OVER_BALANCE"


def test_leave_approval_rejection_cancellation_notifications_and_scope(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    sick_id = leave_type_id(db_factory, "sick")
    leave = client.post(
        "/api/leaves",
        headers=context["employee_headers"],
        json={
            "leave_type_id": sick_id,
            "start_date": "2026-11-02",
            "end_date": "2026-11-03",
            "reason": "Medical",
        },
    ).json()
    assert (
        client.patch(
            f"/api/leaves/{leave['id']}/decision",
            headers=context["employee_headers"],
            json={"action": "approve"},
        ).status_code
        == 403
    )
    approved = client.patch(
        f"/api/leaves/{leave['id']}/decision",
        headers=context["hr_headers"],
        json={"action": "approve", "comment": "Approved"},
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"
    repeated = client.patch(
        f"/api/leaves/{leave['id']}/decision",
        headers=context["hr_headers"],
        json={"action": "reject"},
    )
    assert repeated.status_code == 422
    assert repeated.json()["detail"]["code"] == "LEAVE_NOT_PENDING"
    cancelled = client.post(
        f"/api/leaves/{leave['id']}/cancel", headers=context["employee_headers"]
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    with db_factory() as session:
        assert session.scalar(select(func.count(Notification.id))) == 1
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "leave_requests"
                )
            )
            == 3
        )


def test_unpaid_leave_is_unlimited_and_hr_inbox_filters(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    unpaid_id = leave_type_id(db_factory, "unpaid")
    created = client.post(
        "/api/leaves",
        headers=context["employee_headers"],
        json={
            "leave_type_id": unpaid_id,
            "start_date": "2027-01-01",
            "end_date": "2027-03-31",
            "reason": "Extended unpaid leave",
        },
    )
    assert created.status_code == 200, created.text
    balance = client.get("/api/leaves/balance", headers=context["employee_headers"])
    unpaid = next(item for item in balance.json() if item["code"] == "unpaid")
    assert unpaid["quota"] is None
    assert unpaid["remaining"] is None
    inbox = client.get(
        "/api/leaves?status=pending&from=2027-01-01&to=2027-12-31",
        headers=context["hr_headers"],
    )
    assert inbox.status_code == 200
    assert inbox.json()["total"] == 1
    mine = client.get("/api/leaves/me", headers=context["employee_headers"])
    assert mine.json()["total"] == 1
    with db_factory() as session:
        assert session.scalar(select(func.count(LeaveRequest.id))) == 1
