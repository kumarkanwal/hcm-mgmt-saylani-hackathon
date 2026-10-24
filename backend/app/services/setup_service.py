from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import ApiError
from app.core.security import hash_password
from app.models.organization import LeaveType
from app.models.user import Settings as CompanySettings
from app.models.user import User
from app.schemas.auth import SetupRequest
from app.services.audit_service import write_audit_log
from app.services.transactions import commit_or_rollback

SETUP_LOCK_KEY = 810_241_025
DEFAULT_LEAVE_TYPES = (
    ("annual", "Annual", 14, True),
    ("sick", "Sick", 8, True),
    ("casual", "Casual", 10, True),
    ("unpaid", "Unpaid", None, False),
)


def _lock_setup(session: Session) -> None:
    session.execute(select(func.pg_advisory_xact_lock(SETUP_LOCK_KEY)))


def _create_company(
    session: Session,
    *,
    company_name: str,
    admin_email: str,
    admin_password: str,
) -> User:
    settings = CompanySettings(id=1, company_name=company_name, is_setup_done=True)
    admin = User(
        email=admin_email.strip().lower(),
        password_hash=hash_password(admin_password),
        role="admin",
        is_active=True,
        must_change_password=False,
    )
    session.add_all([settings, admin])
    session.flush()

    leave_types = [
        LeaveType(code=code, name=name, yearly_quota=quota, is_paid=is_paid)
        for code, name, quota, is_paid in DEFAULT_LEAVE_TYPES
    ]
    session.add_all(leave_types)
    session.flush()
    write_audit_log(
        session,
        actor_id=None,
        action="create",
        entity="settings",
        entity_id=settings.id,
        after={"company_name": company_name, "is_setup_done": True},
    )
    write_audit_log(
        session,
        actor_id=None,
        action="create",
        entity="users",
        entity_id=admin.id,
        after={"email": admin.email, "role": admin.role},
    )
    for leave_type in leave_types:
        write_audit_log(
            session,
            actor_id=None,
            action="create",
            entity="leave_types",
            entity_id=leave_type.id,
            after={
                "code": leave_type.code,
                "name": leave_type.name,
                "yearly_quota": leave_type.yearly_quota,
                "is_paid": leave_type.is_paid,
            },
        )
    return admin


def create_company_setup(session: Session, payload: SetupRequest) -> None:
    with commit_or_rollback(session):
        _lock_setup(session)
        existing_settings = session.get(CompanySettings, 1)
        existing_user_id = session.scalar(select(User.id).limit(1))
        if existing_settings is not None or existing_user_id is not None:
            raise ApiError(
                409, "SETUP_ALREADY_DONE", "Company setup has already been completed"
            )
        _create_company(
            session,
            company_name=payload.company_name,
            admin_email=str(payload.admin_email),
            admin_password=payload.admin_password,
        )


def bootstrap_admin_from_environment(
    session: Session,
    settings: Settings | None = None,
) -> bool:
    config = settings or get_settings()
    if not config.admin_email and not config.admin_password:
        return False
    if not config.admin_email or not config.admin_password:
        raise RuntimeError("ADMIN_EMAIL and ADMIN_PASSWORD must both be configured")

    from pydantic import TypeAdapter, ValidationError
    from pydantic.networks import EmailStr

    try:
        email = str(TypeAdapter(EmailStr).validate_python(config.admin_email)).lower()
    except ValidationError as exc:
        raise RuntimeError("ADMIN_EMAIL is not a valid email address") from exc
    company_name = config.company_name.strip()
    if not company_name or len(company_name) > 150:
        raise RuntimeError("COMPANY_NAME must contain between 1 and 150 characters")

    with commit_or_rollback(session):
        _lock_setup(session)
        existing_settings = session.get(CompanySettings, 1)
        existing_user_id = session.scalar(select(User.id).limit(1))
        if existing_settings is not None:
            if existing_settings.is_setup_done:
                return False
            raise RuntimeError(
                "Settings exist but setup is incomplete; refusing Admin bootstrap"
            )
        if existing_user_id is not None:
            raise RuntimeError(
                "Users exist without company settings; refusing Admin bootstrap"
            )
        _create_company(
            session,
            company_name=company_name,
            admin_email=email,
            admin_password=config.admin_password,
        )
    return True
