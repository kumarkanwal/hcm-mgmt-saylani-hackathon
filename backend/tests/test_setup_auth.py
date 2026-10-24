from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta

import jwt
import pytest
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.deps import require_employee_scope
from app.core.exceptions import ApiError
from app.core.rate_limit import limiter
from app.core.security import hash_password
from app.models import (
    AuditLog,
    Department,
    Designation,
    Employee,
    LeaveType,
    User,
)
from app.models import (
    Settings as CompanySettings,
)
from app.services.setup_service import bootstrap_admin_from_environment

ADMIN_EMAIL = "owner@example.com"
ADMIN_PASSWORD = "A-Secure-Admin-Pass-2026"


def setup_company(client, *, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD):
    return client.post(
        "/api/setup",
        json={
            "company_name": "Example Company",
            "admin_email": email,
            "admin_password": password,
        },
    )


def login(client, *, email: str = ADMIN_EMAIL, password: str = ADMIN_PASSWORD):
    return client.post("/api/auth/login", json={"email": email, "password": password})


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_cors_only_allows_the_configured_frontend(client):
    allowed_origin = get_settings().frontend_origins[0]
    preflight_headers = {
        "Origin": allowed_origin,
        "Access-Control-Request-Method": "GET",
    }
    allowed = client.options("/api/health", headers=preflight_headers)
    assert allowed.headers["access-control-allow-origin"] == allowed_origin

    denied = client.options(
        "/api/health",
        headers={**preflight_headers, "Origin": "https://untrusted.example"},
    )
    assert "access-control-allow-origin" not in denied.headers


def test_setup_status_and_atomic_initial_company_creation(client, db_factory):
    assert client.get("/api/setup/status").json() == {"is_setup_done": False}

    response = setup_company(client)

    assert response.status_code == 201
    assert response.json() == {"message": "Company setup completed"}
    assert client.get("/api/setup/status").json() == {"is_setup_done": True}
    with db_factory() as session:
        settings = session.get(CompanySettings, 1)
        admin = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        leave_types = session.scalars(select(LeaveType).order_by(LeaveType.code)).all()
        assert settings is not None
        assert settings.office_start.isoformat() == "09:00:00"
        assert settings.grace_minutes == 15
        assert settings.half_day_hours == 5
        assert settings.weekend_days == [5, 6]
        assert settings.office_radius_m == 150
        assert settings.is_setup_done is True
        assert admin is not None and admin.role == "admin" and admin.is_active
        assert admin.password_hash != ADMIN_PASSWORD
        assert admin.password_hash.startswith("$2b$")
        assert [
            (item.code, item.yearly_quota, item.is_paid) for item in leave_types
        ] == [
            ("annual", 14, True),
            ("casual", 10, True),
            ("sick", 8, True),
            ("unpaid", None, False),
        ]
        audit = session.scalars(select(AuditLog)).all()
        assert len(audit) == 6
        assert all(item.actor_id is None for item in audit)
        assert [item.entity for item in audit].count("leave_types") == 4
        assert ADMIN_PASSWORD not in str(
            [item.before for item in audit] + [item.after for item in audit]
        )


def test_setup_is_one_time_and_invalid_input_is_structured(client, db_factory):
    assert setup_company(client).status_code == 201
    conflict = setup_company(client, email="second@example.com")
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "SETUP_ALREADY_DONE"

    invalid = client.post(
        "/api/setup",
        json={
            "company_name": "   ",
            "admin_email": "not-an-email",
            "admin_password": "short",
        },
    )
    assert invalid.status_code == 422
    assert set(invalid.json()["detail"]) == {"code", "message"}
    with db_factory() as session:
        assert session.scalar(select(func.count(User.id))) == 1


def test_failed_setup_rolls_back_every_related_row(client, db_factory, monkeypatch):
    from app.services import setup_service

    monkeypatch.setattr(
        setup_service,
        "DEFAULT_LEAVE_TYPES",
        (("annual", "Annual", 14, True), ("annual", "Duplicate", 14, True)),
    )
    response = setup_company(client)
    assert response.status_code == 409
    with db_factory() as session:
        assert session.scalar(select(func.count(User.id))) == 0
        assert session.scalar(select(func.count(CompanySettings.id))) == 0
        assert session.scalar(select(func.count(LeaveType.id))) == 0
        assert session.scalar(select(func.count(AuditLog.id))) == 0


def test_concurrent_setup_requests_only_create_one_company(client, db_factory):
    barrier = __import__("threading").Barrier(2)

    def attempt(index: int) -> int:
        barrier.wait(timeout=5)
        return setup_company(client, email=f"owner{index}@example.com").status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = sorted(executor.map(attempt, (1, 2)))

    assert statuses == [201, 409]
    with db_factory() as session:
        assert session.scalar(select(func.count(User.id))) == 1
        assert session.scalar(select(func.count(CompanySettings.id))) == 1
        assert session.scalar(select(func.count(LeaveType.id))) == 4


def test_environment_bootstrap_is_idempotent_and_does_not_overwrite(db_factory):
    settings = get_settings().model_copy(
        update={
            "admin_email": "bootstrap@example.com",
            "admin_password": ADMIN_PASSWORD,
        }
    )
    with db_factory() as session:
        assert bootstrap_admin_from_environment(session, settings) is True
    with db_factory() as session:
        assert bootstrap_admin_from_environment(session, settings) is False
        assert session.scalar(select(func.count(User.id))) == 1
        assert session.scalar(select(User.email)) == "bootstrap@example.com"
        assert session.scalar(select(func.count(LeaveType.id))) == 4


def test_login_me_and_generic_invalid_credentials(client, db_factory):
    assert setup_company(client).status_code == 201
    success = login(client)
    assert success.status_code == 200
    body = success.json()
    assert body["user"] == {
        "id": 1,
        "email": ADMIN_EMAIL,
        "role": "admin",
        "employee_id": None,
        "must_change_password": False,
        "employee": None,
    }
    assert ADMIN_PASSWORD not in success.text
    assert "password_hash" not in success.text
    assert "access_token" in body
    claims = jwt.decode(
        body["access_token"],
        get_settings().jwt_secret,
        algorithms=["HS256"],
    )
    assert claims["employee_id"] is None
    assert claims["exp"] - claims["iat"] == 8 * 60 * 60

    me = client.get("/api/auth/me", headers=bearer(body["access_token"]))
    assert me.status_code == 200, me.text
    assert me.json()["email"] == ADMIN_EMAIL
    assert "password_hash" not in me.text

    invalid_password = login(client, password="Incorrect-Password-123")
    unknown_user = login(client, email="missing@example.com")
    assert invalid_password.status_code == unknown_user.status_code == 401
    assert invalid_password.json() == unknown_user.json()
    with db_factory() as session:
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(AuditLog.action == "login")
            )
            == 1
        )


@pytest.mark.parametrize("token_kind", ["expired", "tampered", "unsupported"])
def test_invalid_jwt_tokens_are_rejected(client, token_kind):
    setup_company(client)
    token = login(client).json()["access_token"]
    if token_kind == "expired":
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": "1",
                "role": "admin",
                "employee_id": None,
                "iat": now - timedelta(hours=2),
                "exp": now - timedelta(hours=1),
            },
            get_settings().jwt_secret,
            algorithm="HS256",
        )
    elif token_kind == "tampered":
        token = token[:-1] + ("A" if token[-1] != "A" else "B")
    else:
        now = datetime.now(UTC)
        token = jwt.encode(
            {
                "sub": "1",
                "role": "admin",
                "employee_id": None,
                "iat": now,
                "exp": now + timedelta(hours=1),
            },
            get_settings().jwt_secret,
            algorithm="HS512",
        )
    response = client.get("/api/auth/me", headers=bearer(token))
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "INVALID_TOKEN"


def test_missing_token_inactive_user_and_role_claim_are_not_trusted(client, db_factory):
    setup_company(client)
    token = login(client).json()["access_token"]
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/_test/admin", headers=bearer(token)).status_code == 200

    with db_factory() as session:
        user = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        user.role = "hr"
        session.commit()
    assert client.get("/api/_test/admin", headers=bearer(token)).status_code == 403
    assert client.get("/api/_test/protected", headers=bearer(token)).json() == {
        "role": "hr"
    }

    with db_factory() as session:
        user = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        user.is_active = False
        session.commit()
    denied = client.get("/api/auth/me", headers=bearer(token))
    assert denied.status_code == 401


def test_forced_password_change_and_password_update_audit(client, db_factory):
    setup_company(client)
    token = login(client).json()["access_token"]
    with db_factory() as session:
        user = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        user.must_change_password = True
        session.commit()

    assert client.get("/api/auth/me", headers=bearer(token)).status_code == 200
    blocked = client.get("/api/_test/protected", headers=bearer(token))
    assert blocked.status_code == 403
    assert blocked.json()["detail"]["code"] == "PASSWORD_CHANGE_REQUIRED"

    wrong = client.post(
        "/api/auth/change-password",
        headers=bearer(token),
        json={"old_password": "wrong-password", "new_password": "A-New-Password-123"},
    )
    assert wrong.status_code == 401
    changed = client.post(
        "/api/auth/change-password",
        headers=bearer(token),
        json={"old_password": ADMIN_PASSWORD, "new_password": "A-New-Password-123"},
    )
    assert changed.status_code == 200
    assert client.get("/api/_test/protected", headers=bearer(token)).status_code == 401
    assert login(client, password=ADMIN_PASSWORD).status_code == 401
    new_token = login(client, password="A-New-Password-123").json()["access_token"]
    assert (
        client.get("/api/_test/protected", headers=bearer(new_token)).status_code == 200
    )

    with db_factory() as session:
        user = session.scalar(select(User).where(User.email == ADMIN_EMAIL))
        audit = session.scalars(select(AuditLog)).all()
        assert user.must_change_password is False
        assert not any(
            "password_hash" in str(row.before) + str(row.after) for row in audit
        )
        audit_text = str([(row.before, row.after) for row in audit])
        assert ADMIN_PASSWORD not in audit_text
        assert "A-New-Password-123" not in audit_text


def test_employee_scope_helper_refuses_another_employee():
    employee = User(
        id=5,
        email="employee@example.com",
        password_hash="hash",
        role="employee",
        employee_id=14,
    )
    require_employee_scope(employee, 14)
    with pytest.raises(ApiError) as error:
        require_employee_scope(employee, 15)
    assert error.value.status_code == 403


def test_employee_auth_me_returns_only_the_permitted_summary(client, db_factory):
    assert setup_company(client).status_code == 201
    with db_factory() as session:
        department = Department(name="People")
        designation = Designation(name="Associate")
        session.add_all([department, designation])
        session.flush()
        employee = Employee(
            employee_code="EMP-1",
            first_name="Sam",
            last_name="Example",
            email="sam@example.com",
            phone="03000000000",
            gender="other",
            department_id=department.id,
            designation_id=designation.id,
            join_date=date(2026, 1, 1),
            status="active",
        )
        session.add(employee)
        session.flush()
        session.add(
            User(
                email="sam@example.com",
                password_hash=hash_password("Employee-Password-123"),
                role="employee",
                employee_id=employee.id,
            )
        )
        session.commit()

    employee_token = login(
        client, email="sam@example.com", password="Employee-Password-123"
    ).json()["access_token"]
    response = client.get("/api/auth/me", headers=bearer(employee_token))
    assert response.status_code == 200
    assert response.json()["employee"] == {
        "id": 1,
        "first_name": "Sam",
        "last_name": "Example",
        "department": "People",
        "designation": "Associate",
    }
    assert "phone" not in response.text
    assert "salary" not in response.text


def test_auth_login_rate_limit_applies_per_account(client):
    setup_company(client)
    limiter.enabled = True
    limiter.reset()
    try:
        responses = [login(client, password="Wrong-Password-000") for _ in range(11)]
    finally:
        limiter.enabled = False
    assert [response.status_code for response in responses[:10]] == [401] * 10
    assert responses[10].status_code == 429
    assert responses[10].json()["detail"]["code"] == "RATE_LIMITED"
