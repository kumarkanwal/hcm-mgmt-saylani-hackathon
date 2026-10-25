from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.organization import Department, LeaveType
from app.models.user import User
from app.schemas.hr import DecisionRequest, LeaveCreate
from app.services.audit_service import write_audit_log
from app.services.hr_utils import (
    get_company_settings,
    holiday_dates,
    local_date,
    working_dates,
)
from app.services.notification_service import notify_employee
from app.services.transactions import commit_or_rollback


def _employee_id(user: User) -> int:
    if user.employee_id is None:
        raise ApiError(
            422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
        )
    return user.employee_id


def _working_day_count(session: Session, start: date, end: date) -> int:
    settings = get_company_settings(session)
    holidays = holiday_dates(session, start, end)
    return len(working_dates(start, end, settings.weekend_days, holidays))


def _days_in_year(session: Session, request: LeaveRequest, year: int) -> int:
    start = max(request.start_date, date(year, 1, 1))
    end = min(request.end_date, date(year, 12, 31))
    return _working_day_count(session, start, end) if start <= end else 0


def get_leave_balance(
    session: Session, *, employee_id: int, year: int | None = None
) -> list[dict[str, Any]]:
    selected_year = year or local_date().year
    year_start = date(selected_year, 1, 1)
    year_end = date(selected_year, 12, 31)
    leave_types = session.scalars(select(LeaveType).order_by(LeaveType.id)).all()
    requests = session.scalars(
        select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status.in_(("pending", "approved")),
            LeaveRequest.end_date >= year_start,
            LeaveRequest.start_date <= year_end,
        )
    ).all()
    settings = get_company_settings(session)
    year_work_days = working_dates(
        year_start,
        year_end,
        settings.weekend_days,
        holiday_dates(session, year_start, year_end),
    )

    def request_days(request: LeaveRequest) -> Decimal:
        return Decimal(
            sum(
                1
                for day in year_work_days
                if request.start_date <= day <= request.end_date
            )
        )

    result = []
    for leave_type in leave_types:
        relevant = [item for item in requests if item.leave_type_id == leave_type.id]
        used = sum(request_days(item) for item in relevant if item.status == "approved")
        pending = sum(
            request_days(item) for item in relevant if item.status == "pending"
        )
        quota = (
            Decimal(leave_type.yearly_quota)
            if leave_type.yearly_quota is not None
            else None
        )
        result.append(
            {
                "leave_type_id": leave_type.id,
                "leave_type": leave_type.name,
                "code": leave_type.code,
                "quota": float(quota) if quota is not None else None,
                "used": float(used),
                "pending": float(pending),
                "remaining": float(quota - used - pending)
                if quota is not None
                else None,
            }
        )
    return result


def _ensure_balance(
    session: Session,
    *,
    employee_id: int,
    leave_type: LeaveType,
    start_date: date,
    end_date: date,
    exclude_request_id: int | None = None,
) -> None:
    if leave_type.yearly_quota is None:
        return
    for year in range(start_date.year, end_date.year + 1):
        requested_days = _working_day_count(
            session,
            max(start_date, date(year, 1, 1)),
            min(end_date, date(year, 12, 31)),
        )
        conditions = [
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.leave_type_id == leave_type.id,
            LeaveRequest.status.in_(("pending", "approved")),
            LeaveRequest.end_date >= date(year, 1, 1),
            LeaveRequest.start_date <= date(year, 12, 31),
        ]
        if exclude_request_id is not None:
            conditions.append(LeaveRequest.id != exclude_request_id)
        existing = session.scalars(select(LeaveRequest).where(*conditions)).all()
        reserved = sum(_days_in_year(session, item, year) for item in existing)
        if reserved + requested_days > leave_type.yearly_quota:
            raise ApiError(
                422, "LEAVE_OVER_BALANCE", "Leave request exceeds the available balance"
            )


def _leave_dict(
    request: LeaveRequest,
    employee: Employee,
    department: str,
    leave_type: str,
) -> dict[str, Any]:
    return {
        "id": request.id,
        "employee_id": request.employee_id,
        "employee_name": f"{employee.first_name} {employee.last_name}",
        "department_id": employee.department_id,
        "department": department,
        "leave_type_id": request.leave_type_id,
        "leave_type": leave_type,
        "start_date": request.start_date,
        "end_date": request.end_date,
        "days": float(request.days),
        "reason": request.reason,
        "status": request.status,
        "reviewed_by": request.reviewed_by,
        "comment": request.comment,
        "created_at": request.created_at,
    }


def _get_leave_row(session: Session, leave_id: int):
    row = session.execute(
        select(LeaveRequest, Employee, Department.name, LeaveType.name)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .where(LeaveRequest.id == leave_id)
    ).one_or_none()
    if row is None:
        raise ApiError(404, "LEAVE_NOT_FOUND", "Leave request was not found")
    return row


def create_leave(
    session: Session, *, user: User, payload: LeaveCreate
) -> dict[str, Any]:
    employee_id = _employee_id(user)
    leave_type = session.get(LeaveType, payload.leave_type_id)
    if leave_type is None:
        raise ApiError(404, "LEAVE_TYPE_NOT_FOUND", "Leave type was not found")
    days = _working_day_count(session, payload.start_date, payload.end_date)
    if days == 0:
        raise ApiError(422, "LEAVE_NO_WORKING_DAYS", "Leave contains no working days")
    lock_key = 2_000_000_000 + employee_id
    with commit_or_rollback(session):
        session.execute(select(func.pg_advisory_xact_lock(lock_key)))
        overlap = session.scalar(
            select(LeaveRequest.id).where(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status.in_(("pending", "approved")),
                LeaveRequest.start_date <= payload.end_date,
                LeaveRequest.end_date >= payload.start_date,
            )
        )
        if overlap is not None:
            raise ApiError(
                422, "LEAVE_OVERLAP", "Leave request overlaps existing leave"
            )
        _ensure_balance(
            session,
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
        request = LeaveRequest(
            employee_id=employee_id,
            leave_type_id=payload.leave_type_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            days=Decimal(days),
            reason=payload.reason.strip(),
        )
        session.add(request)
        session.flush()
        write_audit_log(
            session,
            actor_id=user.id,
            action="create",
            entity="leave_requests",
            entity_id=request.id,
            after={
                "employee_id": employee_id,
                "leave_type_id": request.leave_type_id,
                "start_date": request.start_date,
                "end_date": request.end_date,
                "days": request.days,
                "status": request.status,
            },
        )
    request, employee, department, leave_name = _get_leave_row(session, request.id)
    return _leave_dict(request, employee, department, leave_name)


def cancel_leave(session: Session, *, user: User, leave_id: int) -> dict[str, Any]:
    employee_id = _employee_id(user)
    with commit_or_rollback(session):
        request = session.scalar(
            select(LeaveRequest).where(LeaveRequest.id == leave_id).with_for_update()
        )
        if request is None:
            raise ApiError(404, "LEAVE_NOT_FOUND", "Leave request was not found")
        if request.employee_id != employee_id:
            raise ApiError(
                403, "FORBIDDEN", "You cannot cancel another employee's leave"
            )
        if not (
            request.status == "pending"
            or (request.status == "approved" and request.start_date > local_date())
        ):
            raise ApiError(422, "LEAVE_CANNOT_CANCEL", "Leave cannot be cancelled")
        before = {"status": request.status}
        request.status = "cancelled"
        write_audit_log(
            session,
            actor_id=user.id,
            action="update",
            entity="leave_requests",
            entity_id=request.id,
            before=before,
            after={"status": "cancelled"},
        )
    request, employee, department, leave_name = _get_leave_row(session, request.id)
    return _leave_dict(request, employee, department, leave_name)


def list_leaves(
    session: Session,
    *,
    user: User,
    own_only: bool,
    status: str | None,
    department_id: int | None,
    from_date: date | None,
    to_date: date | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    conditions = []
    if own_only or user.role == "employee":
        conditions.append(LeaveRequest.employee_id == _employee_id(user))
    if status:
        conditions.append(LeaveRequest.status == status)
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    if from_date is not None:
        conditions.append(LeaveRequest.end_date >= from_date)
    if to_date is not None:
        conditions.append(LeaveRequest.start_date <= to_date)
    if from_date and to_date and from_date > to_date:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    base = (
        select(LeaveRequest, Employee, Department.name, LeaveType.name)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .where(*conditions)
    )
    total = session.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = session.execute(
        base.order_by(LeaveRequest.created_at.desc(), LeaveRequest.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_leave_dict(*row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def decide_leave(
    session: Session,
    *,
    reviewer: User,
    leave_id: int,
    payload: DecisionRequest,
) -> dict[str, Any]:
    with commit_or_rollback(session):
        request = session.scalar(
            select(LeaveRequest).where(LeaveRequest.id == leave_id).with_for_update()
        )
        if request is None:
            raise ApiError(404, "LEAVE_NOT_FOUND", "Leave request was not found")
        if request.status != "pending":
            raise ApiError(422, "LEAVE_NOT_PENDING", "Leave request is not pending")
        session.execute(
            select(func.pg_advisory_xact_lock(2_000_000_000 + request.employee_id))
        )
        if payload.action == "approve":
            leave_type = session.get(LeaveType, request.leave_type_id)
            _ensure_balance(
                session,
                employee_id=request.employee_id,
                leave_type=leave_type,
                start_date=request.start_date,
                end_date=request.end_date,
                exclude_request_id=request.id,
            )
            request.status = "approved"
        else:
            request.status = "rejected"
        request.reviewed_by = reviewer.id
        request.comment = payload.comment
        write_audit_log(
            session,
            actor_id=reviewer.id,
            action="approve" if payload.action == "approve" else "reject",
            entity="leave_requests",
            entity_id=request.id,
            before={"status": "pending"},
            after={"status": request.status, "comment": request.comment},
        )
        notify_employee(
            session,
            employee_id=request.employee_id,
            notification_type="leave_decision",
            message=f"Leave request was {request.status}",
        )
    request, employee, department, leave_name = _get_leave_row(session, request.id)
    return _leave_dict(request, employee, department, leave_name)


def leave_summary(
    session: Session,
    *,
    from_date: date,
    to_date: date,
    department_id: int | None,
) -> dict[str, Any]:
    if from_date > to_date:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    conditions = [
        LeaveRequest.status == "approved",
        LeaveRequest.end_date >= from_date,
        LeaveRequest.start_date <= to_date,
    ]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    rows = session.execute(
        select(LeaveRequest, LeaveType)
        .select_from(LeaveRequest)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .join(Employee, Employee.id == LeaveRequest.employee_id)
        .where(*conditions)
    ).all()
    settings = get_company_settings(session)
    work_days = working_dates(
        from_date,
        to_date,
        settings.weekend_days,
        holiday_dates(session, from_date, to_date),
    )
    totals: dict[str, dict[str, Any]] = {}
    year_count = to_date.year - from_date.year + 1
    for request, leave_type in rows:
        days = sum(
            1 for day in work_days if request.start_date <= day <= request.end_date
        )
        if days == 0:
            continue
        item = totals.setdefault(
            leave_type.code,
            {
                "code": leave_type.code,
                "leave_type": leave_type.name,
                "days": 0.0,
                "quota": (
                    float(leave_type.yearly_quota * year_count)
                    if leave_type.yearly_quota is not None
                    else None
                ),
                "utilization_percent": None,
            },
        )
        item["days"] += float(days)
    for item in totals.values():
        if item["quota"]:
            item["utilization_percent"] = round(item["days"] / item["quota"] * 100, 2)
    return {"by_type": [totals[code] for code in sorted(totals)]}
