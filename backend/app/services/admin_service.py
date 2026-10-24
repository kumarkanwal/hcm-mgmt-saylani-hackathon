import secrets
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.security import hash_password
from app.models.employee import Employee
from app.models.organization import Department, Designation, Holiday, LeaveType
from app.models.user import Settings as CompanySettings
from app.models.user import User
from app.schemas.admin import (
    DepartmentWrite,
    DesignationCreate,
    HolidayCreate,
    HRUserCreate,
    LeaveTypeCreate,
    LeaveTypeUpdate,
    SettingsUpdate,
)
from app.services.audit_service import write_audit_log
from app.services.transactions import commit_or_rollback


def _page(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {"items": items, "total": total, "page": page, "page_size": page_size}


def _settings_values(settings: CompanySettings) -> dict[str, Any]:
    return {
        "company_name": settings.company_name,
        "office_start": settings.office_start,
        "grace_minutes": settings.grace_minutes,
        "half_day_hours": settings.half_day_hours,
        "weekend_days": settings.weekend_days,
        "office_lat": settings.office_lat,
        "office_lng": settings.office_lng,
        "office_radius_m": settings.office_radius_m,
    }


def get_company_settings(session: Session) -> dict[str, Any]:
    settings = session.get(CompanySettings, 1)
    if settings is None or not settings.is_setup_done:
        raise ApiError(409, "SETUP_REQUIRED", "Company setup has not been completed")
    return _settings_values(settings)


def update_company_settings(
    session: Session, *, actor: User, payload: SettingsUpdate
) -> dict[str, Any]:
    with commit_or_rollback(session):
        settings = session.scalar(
            select(CompanySettings).where(CompanySettings.id == 1).with_for_update()
        )
        if settings is None or not settings.is_setup_done:
            raise ApiError(
                409, "SETUP_REQUIRED", "Company setup has not been completed"
            )
        before = _settings_values(settings)
        for field, value in payload.model_dump().items():
            setattr(settings, field, value)
        after = _settings_values(settings)
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="settings",
            entity_id=settings.id,
            before=before,
            after=after,
        )
    return after


def list_departments(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    total = session.scalar(select(func.count(Department.id))) or 0
    departments = session.scalars(
        select(Department)
        .order_by(func.lower(Department.name), Department.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return _page(departments, total, page, page_size)


def create_department(
    session: Session, *, actor: User, payload: DepartmentWrite
) -> Department:
    try:
        with commit_or_rollback(session):
            duplicate = session.scalar(
                select(Department.id).where(
                    func.lower(Department.name) == payload.name.lower()
                )
            )
            if duplicate is not None:
                raise ApiError(
                    409, "DEPARTMENT_EXISTS", "Department name already exists"
                )
            department = Department(name=payload.name)
            session.add(department)
            session.flush()
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="departments",
                entity_id=department.id,
                after={"name": department.name},
            )
        return department
    except IntegrityError as exc:
        raise ApiError(
            409, "DEPARTMENT_EXISTS", "Department name already exists"
        ) from exc


def update_department(
    session: Session, *, actor: User, department_id: int, payload: DepartmentWrite
) -> Department:
    try:
        with commit_or_rollback(session):
            department = session.scalar(
                select(Department)
                .where(Department.id == department_id)
                .with_for_update()
            )
            if department is None:
                raise ApiError(404, "DEPARTMENT_NOT_FOUND", "Department was not found")
            duplicate = session.scalar(
                select(Department.id).where(
                    Department.id != department_id,
                    func.lower(Department.name) == payload.name.lower(),
                )
            )
            if duplicate is not None:
                raise ApiError(
                    409, "DEPARTMENT_EXISTS", "Department name already exists"
                )
            before = {"name": department.name}
            department.name = payload.name
            write_audit_log(
                session,
                actor_id=actor.id,
                action="update",
                entity="departments",
                entity_id=department.id,
                before=before,
                after={"name": department.name},
            )
        return department
    except IntegrityError as exc:
        raise ApiError(
            409, "DEPARTMENT_EXISTS", "Department name already exists"
        ) from exc


def delete_department(session: Session, *, actor: User, department_id: int) -> None:
    with commit_or_rollback(session):
        department = session.scalar(
            select(Department).where(Department.id == department_id).with_for_update()
        )
        if department is None:
            raise ApiError(404, "DEPARTMENT_NOT_FOUND", "Department was not found")
        employee_count = session.scalar(
            select(func.count(Employee.id)).where(
                Employee.department_id == department_id
            )
        )
        if employee_count:
            raise ApiError(
                422,
                "DEPARTMENT_HAS_EMPLOYEES",
                "A department with employees cannot be deleted",
            )
        before = {"name": department.name}
        session.delete(department)
        session.flush()
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="departments",
            entity_id=department_id,
            before=before,
            after={"deleted": True},
        )


def list_designations(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    total = session.scalar(select(func.count(Designation.id))) or 0
    rows = session.execute(
        select(Designation, Department.name)
        .outerjoin(Department, Department.id == Designation.department_id)
        .order_by(func.lower(Designation.name), Designation.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    items = [
        {
            "id": designation.id,
            "name": designation.name,
            "department_id": designation.department_id,
            "department": department_name,
            "created_at": designation.created_at,
        }
        for designation, department_name in rows
    ]
    return _page(items, total, page, page_size)


def create_designation(
    session: Session, *, actor: User, payload: DesignationCreate
) -> dict[str, Any]:
    with commit_or_rollback(session):
        department_name = None
        if payload.department_id is not None:
            department = session.get(Department, payload.department_id)
            if department is None:
                raise ApiError(404, "DEPARTMENT_NOT_FOUND", "Department was not found")
            department_name = department.name
        designation = Designation(
            name=payload.name, department_id=payload.department_id
        )
        session.add(designation)
        session.flush()
        write_audit_log(
            session,
            actor_id=actor.id,
            action="create",
            entity="designations",
            entity_id=designation.id,
            after={
                "name": designation.name,
                "department_id": designation.department_id,
            },
        )
    return {
        "id": designation.id,
        "name": designation.name,
        "department_id": designation.department_id,
        "department": department_name,
        "created_at": designation.created_at,
    }


def list_leave_types(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    total = session.scalar(select(func.count(LeaveType.id))) or 0
    items = session.scalars(
        select(LeaveType)
        .order_by(LeaveType.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return _page(items, total, page, page_size)


def create_leave_type(
    session: Session, *, actor: User, payload: LeaveTypeCreate
) -> LeaveType:
    try:
        with commit_or_rollback(session):
            duplicate = session.scalar(
                select(LeaveType.id).where(LeaveType.code == payload.code)
            )
            if duplicate is not None:
                raise ApiError(
                    409, "LEAVE_TYPE_EXISTS", "Leave type code already exists"
                )
            leave_type = LeaveType(**payload.model_dump())
            session.add(leave_type)
            session.flush()
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="leave_types",
                entity_id=leave_type.id,
                after=payload.model_dump(),
            )
        return leave_type
    except IntegrityError as exc:
        raise ApiError(
            409, "LEAVE_TYPE_EXISTS", "Leave type code already exists"
        ) from exc


def update_leave_type(
    session: Session, *, actor: User, leave_type_id: int, payload: LeaveTypeUpdate
) -> LeaveType:
    with commit_or_rollback(session):
        leave_type = session.scalar(
            select(LeaveType).where(LeaveType.id == leave_type_id).with_for_update()
        )
        if leave_type is None:
            raise ApiError(404, "LEAVE_TYPE_NOT_FOUND", "Leave type was not found")
        before = {
            "name": leave_type.name,
            "yearly_quota": leave_type.yearly_quota,
        }
        changes = payload.model_dump(exclude_unset=True)
        for field, value in changes.items():
            setattr(leave_type, field, value)
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="leave_types",
            entity_id=leave_type.id,
            before=before,
            after={
                "name": leave_type.name,
                "yearly_quota": leave_type.yearly_quota,
            },
        )
    return leave_type


def list_holidays(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    total = session.scalar(select(func.count(Holiday.id))) or 0
    items = session.scalars(
        select(Holiday)
        .order_by(Holiday.date, Holiday.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return _page(items, total, page, page_size)


def create_holiday(session: Session, *, actor: User, payload: HolidayCreate) -> Holiday:
    try:
        with commit_or_rollback(session):
            duplicate = session.scalar(
                select(Holiday.id).where(Holiday.date == payload.date)
            )
            if duplicate is not None:
                raise ApiError(
                    409, "HOLIDAY_EXISTS", "A holiday already exists on this date"
                )
            holiday = Holiday(date=payload.date, name=payload.name)
            session.add(holiday)
            session.flush()
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="holidays",
                entity_id=holiday.id,
                after={"date": holiday.date, "name": holiday.name},
            )
        return holiday
    except IntegrityError as exc:
        raise ApiError(
            409, "HOLIDAY_EXISTS", "A holiday already exists on this date"
        ) from exc


def delete_holiday(session: Session, *, actor: User, holiday_id: int) -> None:
    with commit_or_rollback(session):
        holiday = session.scalar(
            select(Holiday).where(Holiday.id == holiday_id).with_for_update()
        )
        if holiday is None:
            raise ApiError(404, "HOLIDAY_NOT_FOUND", "Holiday was not found")
        before = {"date": holiday.date, "name": holiday.name}
        session.delete(holiday)
        session.flush()
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="holidays",
            entity_id=holiday_id,
            before=before,
            after={"deleted": True},
        )


def list_users(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    total = session.scalar(select(func.count(User.id))) or 0
    items = session.scalars(
        select(User).order_by(User.id).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return _page(items, total, page, page_size)


def _temporary_password() -> str:
    return secrets.token_urlsafe(18)


def create_hr_user(
    session: Session, *, actor: User, payload: HRUserCreate
) -> tuple[User, str]:
    temporary_password = payload.password or _temporary_password()
    password_hash = hash_password(temporary_password)
    normalized_email = str(payload.email).lower()
    try:
        with commit_or_rollback(session):
            duplicate = session.scalar(
                select(User.id).where(func.lower(User.email) == normalized_email)
            )
            if duplicate is not None:
                raise ApiError(
                    409, "USER_EXISTS", "A user with this email already exists"
                )
            user = User(
                email=normalized_email,
                password_hash=password_hash,
                role="hr",
                is_active=True,
                must_change_password=True,
            )
            session.add(user)
            session.flush()
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="users",
                entity_id=user.id,
                after={
                    "email": user.email,
                    "role": user.role,
                    "is_active": user.is_active,
                    "must_change_password": user.must_change_password,
                },
            )
        return user, temporary_password
    except IntegrityError as exc:
        raise ApiError(
            409, "USER_EXISTS", "A user with this email already exists"
        ) from exc


def deactivate_user(session: Session, *, actor: User, target_user_id: int) -> User:
    if actor.id == target_user_id:
        raise ApiError(
            422, "SELF_DEACTIVATION", "Administrators cannot deactivate themselves"
        )
    with commit_or_rollback(session):
        user = session.scalar(
            select(User).where(User.id == target_user_id).with_for_update()
        )
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "User was not found")
        if not user.is_active:
            raise ApiError(409, "USER_INACTIVE", "User is already inactive")
        user.is_active = False
        write_audit_log(
            session,
            actor_id=actor.id,
            action="deactivate",
            entity="users",
            entity_id=user.id,
            before={"is_active": True},
            after={"is_active": False},
        )
    return user


def reset_user_password(session: Session, *, actor: User, target_user_id: int) -> str:
    temporary_password = _temporary_password()
    password_hash = hash_password(temporary_password)
    with commit_or_rollback(session):
        user = session.scalar(
            select(User).where(User.id == target_user_id).with_for_update()
        )
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "User was not found")
        before = {"must_change_password": user.must_change_password}
        user.password_hash = password_hash
        user.must_change_password = True
        write_audit_log(
            session,
            actor_id=actor.id,
            action="reset",
            entity="users",
            entity_id=user.id,
            before=before,
            after={"must_change_password": True, "tokens_invalidated": True},
        )
    return temporary_password
