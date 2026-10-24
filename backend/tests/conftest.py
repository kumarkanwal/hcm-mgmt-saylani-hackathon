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
