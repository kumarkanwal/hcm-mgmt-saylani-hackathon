from concurrent.futures import ThreadPoolExecutor
from datetime import date

from sqlalchemy import func, select

from app.core.security import hash_password
from app.models import AuditLog, Department, Designation, Employee, User

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin-Password-2026"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_admin(client) -> dict[str, str]:
    response = client.post(
        "/api/setup",
        json={
            "company_name": "Admin API Company",
            "admin_email": ADMIN_EMAIL,
            "admin_password": ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
    )
    assert login.status_code == 200
    return bearer(login.json()["access_token"])


def add_user(
    db_factory,
    *,
    email: str,
    role: str,
    password: str = "Role-Password-2026",
    employee_id: int | None = None,
) -> None:
    with db_factory() as session:
        session.add(
            User(
                email=email,
                password_hash=hash_password(password),
                role=role,
                employee_id=employee_id,
                must_change_password=False,
            )
        )
        session.commit()


def login_headers(client, email: str, password: str = "Role-Password-2026"):
    response = client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return bearer(response.json()["access_token"])


def add_employee_user(db_factory, *, email: str = "employee@example.com") -> None:
    with db_factory() as session:
        department = Department(name="Employee Department")
        designation = Designation(name="Employee Designation")
        session.add_all([department, designation])
        session.flush()
        employee = Employee(
            employee_code="EMP-ADMIN-TEST",
            first_name="Employee",
            last_name="Example",
            email=email,
            phone="03000000000",
            gender="other",
            department_id=department.id,
            designation_id=designation.id,
            join_date=date(2025, 1, 1),
            status="active",
        )
        session.add(employee)
        session.flush()
        session.add(
            User(
                email=email,
                password_hash=hash_password("Role-Password-2026"),
                role="employee",
                employee_id=employee.id,
                must_change_password=False,
            )
        )
        session.commit()


def test_settings_permissions_validation_and_audit(client, db_factory):
    admin_headers = setup_admin(client)
    current = client.get("/api/settings", headers=admin_headers)
    assert current.status_code == 200
    assert current.json()["office_start"] == "09:00:00"

    update = client.put(
        "/api/settings",
        headers=admin_headers,
        json={
            "company_name": "Updated Company",
            "office_start": "08:30:00",
            "grace_minutes": 10,
            "half_day_hours": 4,
            "weekend_days": [5, 6],
            "office_lat": 24.8607,
            "office_lng": 67.0011,
            "office_radius_m": 200,
        },
    )
    assert update.status_code == 200
    assert update.json()["company_name"] == "Updated Company"
    assert update.json()["office_radius_m"] == 200

    invalid_payload = update.request.content
    assert invalid_payload
    invalid = client.put(
        "/api/settings",
        headers=admin_headers,
        json={
            **update.json(),
            "office_lat": 91,
            "office_radius_m": 0,
        },
    )
    assert invalid.status_code == 422

    add_user(db_factory, email="hr@example.com", role="hr")
    hr_headers = login_headers(client, "hr@example.com")
    assert client.get("/api/settings", headers=hr_headers).status_code == 200
    assert (
        client.put("/api/settings", headers=hr_headers, json=update.json()).status_code
        == 403
    )

    add_employee_user(db_factory)
    employee_headers = login_headers(client, "employee@example.com")
    assert client.get("/api/settings", headers=employee_headers).status_code == 403

    with db_factory() as session:
        audit = session.scalars(
            select(AuditLog).where(
                AuditLog.entity == "settings", AuditLog.actor_id.is_not(None)
            )
        ).all()
        assert len(audit) == 1
        assert audit[0].before["company_name"] == "Admin API Company"
        assert audit[0].after["company_name"] == "Updated Company"


def test_department_crud_conflicts_permissions_and_audit(client, db_factory):
    admin_headers = setup_admin(client)
    created = client.post(
        "/api/departments", headers=admin_headers, json={"name": "Engineering"}
    )
    assert created.status_code == 201
    department_id = created.json()["id"]
    duplicate = client.post(
        "/api/departments", headers=admin_headers, json={"name": "engineering"}
    )
    assert duplicate.status_code == 409

    renamed = client.put(
        f"/api/departments/{department_id}",
        headers=admin_headers,
        json={"name": "Product Engineering"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Product Engineering"
    listing = client.get("/api/departments?page=1&page_size=1", headers=admin_headers)
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["id"] == department_id
    assert (
        client.put(
            "/api/departments/99999",
            headers=admin_headers,
            json={"name": "Missing"},
        ).status_code
        == 404
    )

    add_user(db_factory, email="hr@example.com", role="hr")
    hr_headers = login_headers(client, "hr@example.com")
    assert client.get("/api/departments", headers=hr_headers).status_code == 200
    assert (
        client.post(
            "/api/departments", headers=hr_headers, json={"name": "Denied"}
        ).status_code
        == 403
    )

    deleted = client.delete(f"/api/departments/{department_id}", headers=admin_headers)
    assert deleted.status_code == 200
    with db_factory() as session:
        deletion_audit = session.scalar(
            select(AuditLog).where(
                AuditLog.entity == "departments",
                AuditLog.entity_id == department_id,
                AuditLog.after["deleted"].as_boolean().is_(True),
            )
        )
        assert deletion_audit is not None


def test_concurrent_department_duplicate_rolls_back_change_and_audit(
    client, db_factory
):
    admin_headers = setup_admin(client)
    barrier = __import__("threading").Barrier(2)

    def attempt() -> int:
        barrier.wait(timeout=5)
        return client.post(
            "/api/departments",
            headers=admin_headers,
            json={"name": "Concurrent"},
        ).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(lambda _: attempt(), range(2)))
    assert statuses == [201, 409]
    with db_factory() as session:
        assert (
            session.scalar(
                select(func.count(Department.id)).where(Department.name == "Concurrent")
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "departments",
                    AuditLog.after["name"].as_string() == "Concurrent",
                )
            )
            == 1
        )


def test_department_with_employee_cannot_be_deleted(client, db_factory):
    admin_headers = setup_admin(client)
    with db_factory() as session:
        department = Department(name="People")
        designation = Designation(name="Associate", department=department)
        session.add_all([department, designation])
        session.flush()
        session.add(
            Employee(
                employee_code="EMP-LINKED",
                first_name="Linked",
                last_name="Employee",
                email="linked@example.com",
                phone="03000000001",
                gender="female",
                department_id=department.id,
                designation_id=designation.id,
                join_date=date(2025, 1, 1),
                status="active",
            )
        )
        session.commit()
        department_id = department.id
    response = client.delete(f"/api/departments/{department_id}", headers=admin_headers)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "DEPARTMENT_HAS_EMPLOYEES"


def test_designation_creation_validation_and_hr_listing(client, db_factory):
    admin_headers = setup_admin(client)
    department = client.post(
        "/api/departments", headers=admin_headers, json={"name": "Operations"}
    ).json()
    created = client.post(
        "/api/designations",
        headers=admin_headers,
        json={"name": "Coordinator", "department_id": department["id"]},
    )
    assert created.status_code == 201
    assert created.json()["department"] == "Operations"
    assert (
        client.post(
            "/api/designations",
            headers=admin_headers,
            json={"name": "Invalid", "department_id": 99999},
        ).status_code
        == 404
    )
    add_user(db_factory, email="hr@example.com", role="hr")
    hr_headers = login_headers(client, "hr@example.com")
    listing = client.get("/api/designations", headers=hr_headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert (
        client.post(
            "/api/designations",
            headers=hr_headers,
            json={"name": "Denied", "department_id": None},
        ).status_code
        == 403
    )


def test_leave_type_defaults_updates_and_contract_constraints(client, db_factory):
    admin_headers = setup_admin(client)
    defaults = client.get("/api/leave-types", headers=admin_headers)
    assert defaults.status_code == 200
    assert {item["code"] for item in defaults.json()["items"]} == {
        "annual",
        "sick",
        "casual",
        "unpaid",
    }
    annual = next(item for item in defaults.json()["items"] if item["code"] == "annual")
    updated = client.put(
        f"/api/leave-types/{annual['id']}",
        headers=admin_headers,
        json={"name": "Annual Leave", "yearly_quota": 16},
    )
    assert updated.status_code == 200
    assert updated.json()["yearly_quota"] == 16
    assert (
        client.post(
            "/api/leave-types",
            headers=admin_headers,
            json={
                "code": "annual",
                "name": "Duplicate",
                "yearly_quota": 10,
                "is_paid": True,
            },
        ).status_code
        == 409
    )
    invalid = client.post(
        "/api/leave-types",
        headers=admin_headers,
        json={
            "code": "bereavement",
            "name": "Bereavement",
            "yearly_quota": -1,
            "is_paid": True,
        },
    )
    assert invalid.status_code == 422

    add_employee_user(db_factory)
    employee_headers = login_headers(client, "employee@example.com")
    assert client.get("/api/leave-types", headers=employee_headers).status_code == 200


def test_holiday_crud_validation_and_permissions(client, db_factory):
    admin_headers = setup_admin(client)
    created = client.post(
        "/api/holidays",
        headers=admin_headers,
        json={"date": "2026-12-25", "name": "Public Holiday"},
    )
    assert created.status_code == 201
    holiday_id = created.json()["id"]
    assert (
        client.post(
            "/api/holidays",
            headers=admin_headers,
            json={"date": "2026-12-25", "name": "Duplicate"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/holidays",
            headers=admin_headers,
            json={"date": "not-a-date", "name": "Invalid"},
        ).status_code
        == 422
    )
    assert client.get("/api/holidays", headers=admin_headers).json()["total"] == 1

    add_user(db_factory, email="hr@example.com", role="hr")
    hr_headers = login_headers(client, "hr@example.com")
    assert client.get("/api/holidays", headers=hr_headers).status_code == 200
    assert (
        client.post(
            "/api/holidays",
            headers=hr_headers,
            json={"date": "2026-01-01", "name": "Denied"},
        ).status_code
        == 403
    )
    assert (
        client.delete(f"/api/holidays/{holiday_id}", headers=admin_headers).status_code
        == 200
    )
    assert (
        client.delete("/api/holidays/99999", headers=admin_headers).status_code == 404
    )


def test_hr_user_creation_listing_and_privilege_escalation_prevention(client):
    admin_headers = setup_admin(client)
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "new-hr@example.com", "password": "Temporary-HR-Pass-2026"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["user"]["role"] == "hr"
    assert body["user"]["must_change_password"] is True
    assert body["temp_password"] == "Temporary-HR-Pass-2026"
    assert "password_hash" not in created.text
    listing = client.get("/api/users", headers=admin_headers)
    assert listing.json()["total"] == 2
    assert "password_hash" not in listing.text
    assert "temp_password" not in listing.text

    login = client.post(
        "/api/auth/login",
        json={"email": "new-hr@example.com", "password": body["temp_password"]},
    )
    assert login.status_code == 200
    hr_headers = bearer(login.json()["access_token"])
    blocked = client.get("/api/departments", headers=hr_headers)
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"
    changed = client.post(
        "/api/auth/change-password",
        headers=hr_headers,
        json={
            "old_password": body["temp_password"],
            "new_password": "Permanent-HR-Pass-2026",
        },
    )
    assert changed.status_code == 200
    new_hr_headers = login_headers(
        client, "new-hr@example.com", "Permanent-HR-Pass-2026"
    )
    assert client.get("/api/departments", headers=new_hr_headers).status_code == 200
    assert client.get("/api/users", headers=new_hr_headers).status_code == 403

    escalation = client.post(
        "/api/users",
        headers=admin_headers,
        json={
            "email": "admin2@example.com",
            "password": "Temporary-Admin-Pass-2026",
            "role": "admin",
        },
    )
    assert escalation.status_code == 422
    assert (
        client.post(
            "/api/users",
            headers=admin_headers,
            json={"email": "new-hr@example.com", "password": "Another-Pass-2026"},
        ).status_code
        == 409
    )


def test_deactivation_denies_existing_tokens_and_self_deactivation(client):
    admin_headers = setup_admin(client)
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "deactivate@example.com", "password": "Temporary-Pass-2026"},
    ).json()
    user_id = created["user"]["id"]
    login = client.post(
        "/api/auth/login",
        json={"email": "deactivate@example.com", "password": created["temp_password"]},
    )
    existing_headers = bearer(login.json()["access_token"])
    assert (
        client.patch("/api/users/1/deactivate", headers=admin_headers).status_code
        == 422
    )
    deactivated = client.patch(
        f"/api/users/{user_id}/deactivate", headers=admin_headers
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["is_active"] is False
    assert client.get("/api/auth/me", headers=existing_headers).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={
                "email": "deactivate@example.com",
                "password": created["temp_password"],
            },
        ).status_code
        == 401
    )


def test_password_reset_invalidates_tokens_and_never_audits_secrets(client, db_factory):
    admin_headers = setup_admin(client)
    created = client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "reset@example.com", "password": "Original-Temp-Pass-2026"},
    ).json()
    user_id = created["user"]["id"]
    old_login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": "Original-Temp-Pass-2026"},
    ).json()
    old_headers = bearer(old_login["access_token"])

    reset = client.post(f"/api/users/{user_id}/reset-password", headers=admin_headers)
    assert reset.status_code == 200
    temporary_password = reset.json()["temp_password"]
    assert temporary_password not in reset.headers.values()
    assert client.get("/api/auth/me", headers=old_headers).status_code == 401
    assert (
        client.post(
            "/api/auth/login",
            json={"email": "reset@example.com", "password": "Original-Temp-Pass-2026"},
        ).status_code
        == 401
    )
    new_login = client.post(
        "/api/auth/login",
        json={"email": "reset@example.com", "password": temporary_password},
    )
    assert new_login.status_code == 200
    assert new_login.json()["user"]["must_change_password"] is True

    with db_factory() as session:
        audits = session.scalars(
            select(AuditLog).where(AuditLog.entity_id == user_id)
        ).all()
        audit_text = str([(row.before, row.after) for row in audits])
        user = session.get(User, user_id)
        assert temporary_password not in audit_text
        assert "password_hash" not in audit_text
        assert user.password_hash not in audit_text


def test_audit_log_filters_pagination_order_and_permissions(client, db_factory):
    admin_headers = setup_admin(client)
    client.post("/api/departments", headers=admin_headers, json={"name": "First"})
    client.post("/api/departments", headers=admin_headers, json={"name": "Second"})
    audit = client.get(
        "/api/audit-logs?entity=departments&page=1&page_size=1",
        headers=admin_headers,
    )
    assert audit.status_code == 200
    assert audit.json()["total"] == 2
    assert len(audit.json()["items"]) == 1
    assert audit.json()["items"][0]["after"]["name"] == "Second"
    assert "password" not in audit.text.lower()
    actor_id = audit.json()["items"][0]["actor_id"]
    by_actor = client.get(f"/api/audit-logs?actor_id={actor_id}", headers=admin_headers)
    assert by_actor.status_code == 200
    assert all(item["actor_id"] == actor_id for item in by_actor.json()["items"])
    assert (
        client.get(
            "/api/audit-logs?from=2026-12-31&to=2026-01-01",
            headers=admin_headers,
        ).status_code
        == 422
    )

    add_user(db_factory, email="hr@example.com", role="hr")
    hr_headers = login_headers(client, "hr@example.com")
    assert client.get("/api/audit-logs", headers=hr_headers).status_code == 403
    with db_factory() as session:
        assert session.scalar(select(func.count(AuditLog.id))) >= 9
