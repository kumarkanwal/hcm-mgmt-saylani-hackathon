import os
from collections.abc import Generator
from typing import Annotated

import pytest
from alembic.config import Config
from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from alembic import command
from app.core.config import get_settings
from app.core.database import get_db
from app.core.deps import get_current_user, require_role
from app.core.rate_limit import limiter
from app.main import app
from app.models import Base, User


@pytest.fixture(scope="session")
def test_engine():
    test_url = get_settings().test_database_url
    if not test_url:
        pytest.fail("TEST_DATABASE_URL must point to a dedicated test database")
    parsed_url = make_url(test_url)
    if parsed_url.database != "hcm_lite_test" or parsed_url.host not in {
        "127.0.0.1",
        "localhost",
    }:
        pytest.fail(
            "Refusing to run tests outside the isolated local hcm_lite_test database"
        )

    os.environ["ALEMBIC_DATABASE_URL"] = test_url
    alembic_config = Config("alembic.ini")
    command.upgrade(alembic_config, "head")

    engine = create_engine(test_url, pool_pre_ping=True)
    with engine.connect() as connection:
        version = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if version is None:
        pytest.fail("Test database did not reach the current Alembic revision")
    yield engine
    engine.dispose()
    os.environ.pop("ALEMBIC_DATABASE_URL", None)


@pytest.fixture(autouse=True)
def clear_test_data(test_engine) -> Generator[None, None, None]:
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with test_engine.begin() as connection:
        connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )
    yield
    limiter.reset()


@pytest.fixture
def client(test_engine) -> Generator[TestClient, None, None]:
    factory = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_db() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    was_enabled = limiter.enabled
    limiter.enabled = False
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        limiter.enabled = was_enabled
        app.dependency_overrides.pop(get_db, None)


def _admin_only(
    user: Annotated[User, Depends(require_role("admin"))],
) -> dict[str, str]:
    return {"role": user.role}


def _protected(user: Annotated[User, Depends(get_current_user)]) -> dict[str, str]:
    return {"role": user.role}


if not any(getattr(route, "path", None) == "/api/_test/admin" for route in app.routes):
    app.add_api_route("/api/_test/admin", _admin_only, include_in_schema=False)
    app.add_api_route("/api/_test/protected", _protected, include_in_schema=False)


@pytest.fixture
def db_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)


@pytest.fixture
def phase2_context(client):
    setup = client.post(
        "/api/setup",
        json={
            "company_name": "Phase 2 Test Company",
            "admin_email": "phase2-admin@example.com",
            "admin_password": "Phase2-Admin-Pass-2026",
        },
    )
    assert setup.status_code == 201
    admin_login = client.post(
        "/api/auth/login",
        json={
            "email": "phase2-admin@example.com",
            "password": "Phase2-Admin-Pass-2026",
        },
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    department = client.post(
        "/api/departments", headers=admin_headers, json={"name": "Engineering"}
    ).json()
    designation = client.post(
        "/api/designations",
        headers=admin_headers,
        json={"name": "Software Engineer", "department_id": department["id"]},
    ).json()
    hr = client.post(
        "/api/users", headers=admin_headers, json={"email": "phase2-hr@example.com"}
    ).json()
    hr_login = client.post(
        "/api/auth/login",
        json={"email": "phase2-hr@example.com", "password": hr["temp_password"]},
    )
    hr_headers = {"Authorization": f"Bearer {hr_login.json()['access_token']}"}
    changed = client.post(
        "/api/auth/change-password",
        headers=hr_headers,
        json={
            "old_password": hr["temp_password"],
            "new_password": "Phase2-HR-Permanent-2026",
        },
    )
    assert changed.status_code == 200
    hr_login = client.post(
        "/api/auth/login",
        json={
            "email": "phase2-hr@example.com",
            "password": "Phase2-HR-Permanent-2026",
        },
    )
    return {
        "admin_headers": admin_headers,
        "hr_headers": {"Authorization": f"Bearer {hr_login.json()['access_token']}"},
        "department_id": department["id"],
        "designation_id": designation["id"],
    }


@pytest.fixture
def phase2_employee(client, phase2_context):
    created = client.post(
        "/api/employees",
        headers=phase2_context["hr_headers"],
        json={
            "employee_code": "EMP-001",
            "first_name": "Test",
            "last_name": "Employee",
            "email": "employee1@example.com",
            "phone": "03000000000",
            "gender": "other",
            "department_id": phase2_context["department_id"],
            "designation_id": phase2_context["designation_id"],
            "join_date": "2026-01-01",
            "basic_salary": 100000,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    login = client.post(
        "/api/auth/login",
        json={"email": "employee1@example.com", "password": body["temp_password"]},
    )
    temporary_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    assert (
        client.post(
            "/api/auth/change-password",
            headers=temporary_headers,
            json={
                "old_password": body["temp_password"],
                "new_password": "Employee-Permanent-2026",
            },
        ).status_code
        == 200
    )
    login = client.post(
        "/api/auth/login",
        json={
            "email": "employee1@example.com",
            "password": "Employee-Permanent-2026",
        },
    )
    return {
        **phase2_context,
        "employee": body["employee"],
        "employee_headers": {"Authorization": f"Bearer {login.json()['access_token']}"},
    }
