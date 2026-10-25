import pytest
from sqlalchemy import func, select

from app.models import Announcement, AuditLog, Notification, User
from app.services import communication_service


def _create_inactive_employee(client, context, db_factory):
    created = client.post(
        "/api/employees",
        headers=context["hr_headers"],
        json={
            "employee_code": "EMP-INACTIVE",
            "first_name": "Inactive",
            "last_name": "Employee",
            "email": "inactive-employee@example.com",
            "phone": "03001112222",
            "gender": "other",
            "department_id": context["department_id"],
            "designation_id": context["designation_id"],
            "join_date": "2026-01-01",
            "basic_salary": 70000,
        },
    )
    assert created.status_code == 201, created.text
    with db_factory() as session:
        user = session.scalar(
            select(User).where(User.email == "inactive-employee@example.com")
        )
        user.is_active = False
        session.commit()
        return user.id


def test_announcements_permissions_order_authors_audit_and_active_notifications(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    inactive_user_id = _create_inactive_employee(client, context, db_factory)

    for headers in (
        context["admin_headers"],
        context["hr_headers"],
        context["employee_headers"],
    ):
        empty = client.get("/api/announcements", headers=headers)
        assert empty.status_code == 200
        assert empty.json() == {"items": [], "total": 0, "page": 1, "page_size": 20}

    assert (
        client.post(
            "/api/announcements",
            headers=context["employee_headers"],
            json={"title": "Not allowed", "body": "Employee post"},
        ).status_code
        == 403
    )
    assert (
        client.post(
            "/api/announcements",
            headers=context["hr_headers"],
            json={"title": "   ", "body": "Message"},
        ).status_code
        == 422
    )

    first = client.post(
        "/api/announcements",
        headers=context["admin_headers"],
        json={"title": "Office update", "body": "The office opens at 9 AM."},
    )
    assert first.status_code == 201, first.text
    assert first.json()["author_role"] == "admin"
    assert first.json()["author_name"] == "phase2-admin@example.com"
    second = client.post(
        "/api/announcements",
        headers=context["hr_headers"],
        json={"title": "Benefits update", "body": "Review the updated policy."},
    )
    assert second.status_code == 201, second.text
    assert second.json()["author_role"] == "hr"

    listing = client.get(
        "/api/announcements?page=1&page_size=1",
        headers=context["employee_headers"],
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert listing.json()["items"][0]["title"] == "Benefits update"
    with db_factory() as session:
        assert session.scalar(select(func.count(Announcement.id))) == 2
        assert (
            session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.type == "announcement"
                )
            )
            == 6
        )
        assert (
            session.scalar(
                select(func.count(Notification.id)).where(
                    Notification.user_id == inactive_user_id
                )
            )
            == 0
        )
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "announcements"
                )
            )
            == 2
        )


def test_notifications_are_private_paginated_and_idempotently_read(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    client.post(
        "/api/announcements",
        headers=context["hr_headers"],
        json={"title": "One", "body": "First message"},
    )
    client.post(
        "/api/announcements",
        headers=context["hr_headers"],
        json={"title": "Two", "body": "Second message"},
    )
    page = client.get(
        "/api/notifications?page=1&page_size=1",
        headers=context["employee_headers"],
    )
    assert page.status_code == 200
    body = page.json()
    assert body["total"] == 2
    assert body["unread_count"] == 2
    assert len(body["items"]) == 1
    assert body["items"][0]["title"] == "New announcement"
    assert body["items"][0]["link"] == "/announcements"
    own_notification_id = body["items"][0]["id"]

    admin_page = client.get("/api/notifications", headers=context["admin_headers"])
    admin_notification_id = admin_page.json()["items"][0]["id"]
    assert (
        client.patch(
            f"/api/notifications/{admin_notification_id}/read",
            headers=context["employee_headers"],
        ).status_code
        == 404
    )

    marked = client.patch(
        f"/api/notifications/{own_notification_id}/read",
        headers=context["employee_headers"],
    )
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    repeated = client.patch(
        f"/api/notifications/{own_notification_id}/read",
        headers=context["employee_headers"],
    )
    assert repeated.status_code == 200
    assert repeated.json()["is_read"] is True
    refreshed = client.get("/api/notifications", headers=context["employee_headers"])
    assert refreshed.json()["unread_count"] == 1
    assert all(
        item["id"] != admin_notification_id for item in refreshed.json()["items"]
    )
    with db_factory() as session:
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "notifications"
                )
            )
            == 1
        )


def test_communication_endpoints_require_authentication(client):
    assert client.get("/api/announcements").status_code == 401
    assert (
        client.post(
            "/api/announcements", json={"title": "Title", "body": "Body"}
        ).status_code
        == 401
    )
    assert client.get("/api/notifications").status_code == 401
    assert client.patch("/api/notifications/1/read").status_code == 401


def test_announcement_notification_failure_rolls_back_everything(
    client, phase2_context, db_factory, monkeypatch
):
    def fail_notification(*args, **kwargs):
        raise RuntimeError("notification failure")

    monkeypatch.setattr(
        communication_service, "notify_all_active_users", fail_notification
    )
    with pytest.raises(RuntimeError, match="notification failure"):
        client.post(
            "/api/announcements",
            headers=phase2_context["hr_headers"],
            json={"title": "Rollback", "body": "This must not be stored."},
        )
    with db_factory() as session:
        assert session.scalar(select(func.count(Announcement.id))) == 0
        assert session.scalar(select(func.count(Notification.id))) == 0
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "announcements"
                )
            )
            == 0
        )
