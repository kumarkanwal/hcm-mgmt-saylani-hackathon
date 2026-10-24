import bcrypt
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import Settings, get_settings
from app.core.exceptions import ApiError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.employee import Employee
from app.models.user import User
from app.schemas.auth import LoginRequest, UserResponse
from app.services.audit_service import write_audit_log
from app.services.transactions import commit_or_rollback

# Run the same bcrypt work for unknown accounts to reduce account-enumeration timing.
_DUMMY_HASH = bcrypt.hashpw(b"non-user-account-placeholder", bcrypt.gensalt(rounds=12))
INVALID_CREDENTIALS = ApiError(
    401, "INVALID_CREDENTIALS", "Email or password is incorrect"
)


def login(
    session: Session, payload: LoginRequest, settings: Settings | None = None
) -> dict:
    config = settings or get_settings()
    with commit_or_rollback(session):
        user = session.scalar(
            select(User).where(func.lower(User.email) == str(payload.email).lower())
        )
        if user is None:
            try:
                candidate = payload.password.encode("utf-8")[:72]
            except UnicodeEncodeError:
                candidate = b"invalid-password-encoding"
            bcrypt.checkpw(candidate, _DUMMY_HASH)
            raise INVALID_CREDENTIALS
        password_is_valid = verify_password(payload.password, user.password_hash)
        if not user.is_active or not password_is_valid:
            raise INVALID_CREDENTIALS

        token = create_access_token(user, config)
        write_audit_log(
            session,
            actor_id=user.id,
            action="login",
            entity="users",
            entity_id=user.id,
            after={"role": user.role},
        )
        result = {
            "access_token": token,
            "user": {
                "id": user.id,
                "email": user.email,
                "role": user.role,
                "employee_id": user.employee_id,
                "must_change_password": user.must_change_password,
            },
        }
    return result


def get_authenticated_user_response(session: Session, user_id: int) -> UserResponse:
    user = session.scalar(
        select(User)
        .options(
            joinedload(User.employee).joinedload(Employee.department),
            joinedload(User.employee).joinedload(Employee.designation),
        )
        .where(User.id == user_id)
    )
    if user is None or not user.is_active:
        raise ApiError(401, "UNAUTHENTICATED", "Authentication is required")

    employee_summary = None
    if user.employee is not None:
        employee_summary = {
            "id": user.employee.id,
            "first_name": user.employee.first_name,
            "last_name": user.employee.last_name,
            "department": user.employee.department.name
            if user.employee.department
            else None,
            "designation": user.employee.designation.name
            if user.employee.designation
            else None,
        }
    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        employee_id=user.employee_id,
        must_change_password=user.must_change_password,
        employee=employee_summary,
    )


def change_password(
    session: Session,
    *,
    user: User,
    old_password: str,
    new_password: str,
) -> None:
    new_hash = hash_password(new_password)
    with commit_or_rollback(session):
        current = session.scalar(
            select(User).where(User.id == user.id).with_for_update()
        )
        if current is None or not current.is_active:
            raise ApiError(401, "UNAUTHENTICATED", "Authentication is required")
        if not verify_password(old_password, current.password_hash):
            raise ApiError(401, "INVALID_CREDENTIALS", "Current password is incorrect")
        old_must_change_password = current.must_change_password
        current.password_hash = new_hash
        current.must_change_password = False
        write_audit_log(
            session,
            actor_id=current.id,
            action="update",
            entity="users",
            entity_id=current.id,
            before={"must_change_password": old_must_change_password},
            after={"must_change_password": False},
        )
