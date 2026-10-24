from datetime import UTC, datetime

from sqlalchemy import func, select

from app.models import LeaveType, Notification
from app.services import attendance_service


def test_complete_hr_employee_payroll_workflow(
    client, phase2_employee, db_factory, monkeypatch
):
    context = phase2_employee
    employee_headers = context["employee_headers"]
    hr_headers = context["hr_headers"]
    admin_headers = context["admin_headers"]

    directory = client.get("/api/employees", headers=hr_headers)
    assert directory.status_code == 200
    assert directory.json()["items"][0]["employee_code"] == "EMP-001"
    salary = client.get(
        f"/api/employees/{context['employee']['id']}/salary", headers=hr_headers
    )
    assert salary.status_code == 200
    assert salary.json()["gross"] == 150000.0

    monkeypatch.setattr(
        attendance_service,
        "utc_now",
        lambda: datetime(2026, 10, 19, 4, 10, tzinfo=UTC),
    )
    checked_in = client.post(
        "/api/attendance/check-in", headers=employee_headers, json={"source": "web"}
    )
    assert checked_in.status_code == 200
    assert checked_in.json()["status"] == "present"
    monkeypatch.setattr(
        attendance_service,
        "utc_now",
        lambda: datetime(2026, 10, 19, 12, 10, tzinfo=UTC),
    )
    checked_out = client.post("/api/attendance/check-out", headers=employee_headers)
    assert checked_out.status_code == 200
    board = client.get("/api/attendance/board?date=2026-10-19", headers=hr_headers)
    assert board.status_code == 200
    assert board.json()[0]["status"] == "present"

    correction = client.post(
        "/api/attendance/corrections",
        headers=employee_headers,
        json={
            "date": "2026-10-20",
            "requested_check_in": "2026-10-20T09:10:00+05:00",
            "requested_check_out": "2026-10-20T17:10:00+05:00",
            "reason": "Device was unavailable",
        },
    )
    assert correction.status_code == 200, correction.text
    correction_id = correction.json()["id"]
    correction_inbox = client.get(
        "/api/attendance/corrections?status=pending", headers=hr_headers
    )
    assert correction_inbox.status_code == 200
    assert correction_inbox.json()["total"] == 1
    approved_correction = client.patch(
        f"/api/attendance/corrections/{correction_id}",
        headers=hr_headers,
        json={"action": "approve", "comment": "Verified"},
    )
    assert approved_correction.status_code == 200
    assert approved_correction.json()["status"] == "approved"

    with db_factory() as session:
        annual_id = session.scalar(
            select(LeaveType.id).where(LeaveType.code == "annual")
        )
    leave = client.post(
        "/api/leaves",
        headers=employee_headers,
        json={
            "leave_type_id": annual_id,
            "start_date": "2026-10-22",
            "end_date": "2026-10-23",
            "reason": "Family event",
        },
    )
    assert leave.status_code == 200, leave.text
    leave_id = leave.json()["id"]
    assert leave.json()["days"] == 2.0
    leave_inbox = client.get("/api/leaves?status=pending", headers=hr_headers)
    assert leave_inbox.status_code == 200
    assert leave_inbox.json()["total"] == 1
    approved_leave = client.patch(
        f"/api/leaves/{leave_id}/decision",
        headers=hr_headers,
        json={"action": "approve", "comment": "Approved"},
    )
    assert approved_leave.status_code == 200
    assert approved_leave.json()["status"] == "approved"
    balance = client.get("/api/leaves/balance", headers=employee_headers)
    assert balance.status_code == 200
    annual = next(item for item in balance.json() if item["code"] == "annual")
    assert annual["used"] == 2.0

    payroll = client.post(
        "/api/payroll/runs", headers=hr_headers, json={"month": "2026-10"}
    )
    assert payroll.status_code == 200, payroll.text
    payroll_id = payroll.json()["id"]
    payslip_id = payroll.json()["payslips"][0]["id"]
    assert payroll.json()["status"] == "draft"
    assert payroll.json()["payslips"][0]["paid_days"] == 4.0
    recalculated = client.post(
        f"/api/payroll/runs/{payroll_id}/recalculate", headers=hr_headers
    )
    assert recalculated.status_code == 200
    payslip_id = recalculated.json()["payslips"][0]["id"]
    assert (
        client.post(
            f"/api/payroll/runs/{payroll_id}/finalize", headers=hr_headers
        ).status_code
        == 403
    )

    finalized = client.post(
        f"/api/payroll/runs/{payroll_id}/finalize", headers=admin_headers
    )
    assert finalized.status_code == 200
    assert finalized.json()["status"] == "finalized"
    assert (
        client.post(
            f"/api/payroll/runs/{payroll_id}/recalculate", headers=hr_headers
        ).status_code
        == 409
    )
    mine = client.get("/api/payslips/me", headers=employee_headers)
    assert mine.status_code == 200
    assert mine.json()["items"][0]["month"] == "2026-10"
    pdf = client.get(f"/api/payslips/{payslip_id}/pdf", headers=employee_headers)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")

    dashboard = client.get(
        "/api/dashboard/hr?from=2026-10-20&to=2026-10-23", headers=hr_headers
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["headcount"] == 1
    assert dashboard.json()["pending_approvals"] == {
        "leave": 0,
        "corrections": 0,
    }
    admin_dashboard = client.get(
        "/api/dashboard/admin?from=2026-10-01&to=2026-10-31",
        headers=admin_headers,
    )
    assert admin_dashboard.status_code == 200
    assert admin_dashboard.json()["headcount"] == 1
    audit = client.get("/api/audit-logs?page_size=100", headers=admin_headers)
    assert audit.status_code == 200
    entities = {item["entity"] for item in audit.json()["items"]}
    assert {
        "employees",
        "attendance_corrections",
        "leave_requests",
        "payroll_runs",
    } <= entities
    with db_factory() as session:
        assert session.scalar(select(func.count(Notification.id))) == 3
    assert client.get("/api/audit-logs", headers=employee_headers).status_code == 403
    assert client.get("/api/employees", headers=employee_headers).status_code == 403
