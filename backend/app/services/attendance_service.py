import math
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.attendance import Attendance, AttendanceCorrection
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.organization import Department, Holiday
from app.models.payroll import PayrollRun
from app.models.user import User
from app.schemas.hr import AttendanceCorrectionCreate, CheckInRequest, DecisionRequest
from app.services.audit_service import write_audit_log
from app.services.hr_utils import (
    company_timezone,
    get_company_settings,
    holiday_dates,
    local_date,
    month_bounds,
    utc_now,
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


def _attendance_dict(record: Attendance) -> dict[str, Any]:
    return {
        "id": record.id,
        "employee_id": record.employee_id,
        "date": record.date,
        "check_in": record.check_in,
        "check_out": record.check_out,
        "status": record.status,
        "source": record.source,
    }


def _status_for_check_in(settings, value: datetime) -> str:
    local_value = value.astimezone(company_timezone())
    threshold = datetime.combine(
        local_value.date(), settings.office_start, tzinfo=company_timezone()
    ) + timedelta(minutes=settings.grace_minutes)
    return "late" if local_value > threshold else "present"


def _status_for_times(settings, check_in: datetime, check_out: datetime | None) -> str:
    if check_out is not None:
        hours = (check_out - check_in).total_seconds() / 3600
        if hours < settings.half_day_hours:
            return "half_day"
    return _status_for_check_in(settings, check_in)


def _is_approved_leave(session: Session, employee_id: int, day: date) -> bool:
    return bool(
        session.scalar(
            select(LeaveRequest.id).where(
                LeaveRequest.employee_id == employee_id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= day,
                LeaveRequest.end_date >= day,
            )
        )
    )


def _validate_camera(settings, payload: CheckInRequest) -> None:
    if payload.source != "camera":
        return
    if (
        payload.lat is None
        or payload.lng is None
        or payload.accuracy is None
        or settings.office_lat is None
        or settings.office_lng is None
    ):
        raise ApiError(
            422, "LOCATION_REQUIRED", "Camera check-in requires configured GPS data"
        )
    if payload.accuracy > 100:
        raise ApiError(
            422, "GPS_INACCURATE", "GPS accuracy must be 100 metres or better"
        )
    office_lat = float(settings.office_lat)
    office_lng = float(settings.office_lng)
    radius = 6_371_000
    lat1, lat2 = math.radians(office_lat), math.radians(payload.lat)
    delta_lat = math.radians(payload.lat - office_lat)
    delta_lng = math.radians(payload.lng - office_lng)
    haversine = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lng / 2) ** 2
    )
    distance = radius * 2 * math.atan2(math.sqrt(haversine), math.sqrt(1 - haversine))
    if distance > settings.office_radius_m:
        raise ApiError(
            422, "OUTSIDE_OFFICE_RADIUS", "Location is outside the office radius"
        )


def check_in(
    session: Session,
    *,
    user: User,
    payload: CheckInRequest,
    now: datetime | None = None,
) -> dict[str, Any]:
    employee_id = _employee_id(user)
    timestamp = (now or utc_now()).astimezone(UTC)
    day = local_date(timestamp)
    settings = get_company_settings(session)
    if day.weekday() in settings.weekend_days:
        raise ApiError(422, "NON_WORKING_DAY", "Check-in is not allowed on weekends")
    if session.scalar(select(Holiday.id).where(Holiday.date == day)) is not None:
        raise ApiError(422, "NON_WORKING_DAY", "Check-in is not allowed on holidays")
    if _is_approved_leave(session, employee_id, day):
        raise ApiError(
            422, "EMPLOYEE_ON_LEAVE", "Check-in is not allowed during approved leave"
        )
    _validate_camera(settings, payload)
    try:
        with commit_or_rollback(session):
            record = Attendance(
                employee_id=employee_id,
                date=day,
                check_in=timestamp,
                status=_status_for_check_in(settings, timestamp),
                source=payload.source,
                lat=payload.lat,
                lng=payload.lng,
            )
            session.add(record)
            session.flush()
            write_audit_log(
                session,
                actor_id=user.id,
                action="create",
                entity="attendance",
                entity_id=record.id,
                after=_attendance_dict(record),
            )
        return _attendance_dict(record)
    except IntegrityError as exc:
        raise ApiError(
            409, "ALREADY_CHECKED_IN", "Attendance already exists for today"
        ) from exc


def check_out(
    session: Session, *, user: User, now: datetime | None = None
) -> dict[str, Any]:
    employee_id = _employee_id(user)
    timestamp = (now or utc_now()).astimezone(UTC)
    day = local_date(timestamp)
    with commit_or_rollback(session):
        record = session.scalar(
            select(Attendance)
            .where(Attendance.employee_id == employee_id, Attendance.date == day)
            .with_for_update()
        )
        if record is None:
            raise ApiError(422, "CHECK_IN_REQUIRED", "Check in before checking out")
        if record.check_out is not None:
            raise ApiError(
                409, "ALREADY_CHECKED_OUT", "Attendance is already checked out"
            )
        if timestamp <= record.check_in:
            raise ApiError(422, "INVALID_CHECK_OUT", "Check-out must be after check-in")
        before = _attendance_dict(record)
        record.check_out = timestamp
        record.status = _status_for_times(
            get_company_settings(session), record.check_in, record.check_out
        )
        write_audit_log(
            session,
            actor_id=user.id,
            action="update",
            entity="attendance",
            entity_id=record.id,
            before=before,
            after=_attendance_dict(record),
        )
    return _attendance_dict(record)


def attendance_today(session: Session, *, user: User) -> dict[str, Any] | None:
    employee_id = _employee_id(user)
    record = session.scalar(
        select(Attendance).where(
            Attendance.employee_id == employee_id, Attendance.date == local_date()
        )
    )
    return _attendance_dict(record) if record else None


def derive_attendance_status(
    day: date,
    *,
    today: date,
    record: Attendance | None,
    on_leave: bool,
    weekend_days: list[int],
    holidays: set[date],
) -> str:
    if day.weekday() in weekend_days:
        return "weekend"
    if day in holidays:
        return "holiday"
    if on_leave:
        return "on_leave"
    if record is not None:
        if record.check_out is None and day < today:
            return "missing_checkout"
        return record.status
    return "absent" if day < today else "not_recorded"


def attendance_calendar(session: Session, *, user: User, month: str) -> dict[str, Any]:
    employee_id = _employee_id(user)
    start, end = month_bounds(month)
    settings = get_company_settings(session)
    holidays = holiday_dates(session, start, end)
    records = {
        item.date: item
        for item in session.scalars(
            select(Attendance).where(
                Attendance.employee_id == employee_id,
                Attendance.date >= start,
                Attendance.date <= end,
            )
        ).all()
    }
    leaves = session.scalars(
        select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.end_date >= start,
            LeaveRequest.start_date <= end,
        )
    ).all()
    leave_days = {
        current
        for leave in leaves
        for current in (
            leave.start_date + timedelta(days=offset)
            for offset in range((leave.end_date - leave.start_date).days + 1)
        )
    }
    today = local_date()
    items = []
    current = start
    while current <= end:
        record = records.get(current)
        items.append(
            {
                "id": record.id if record else None,
                "employee_id": employee_id,
                "date": current,
                "check_in": record.check_in if record else None,
                "check_out": record.check_out if record else None,
                "status": derive_attendance_status(
                    current,
                    today=today,
                    record=record,
                    on_leave=current in leave_days,
                    weekend_days=settings.weekend_days,
                    holidays=holidays,
                ),
                "source": record.source if record else None,
            }
        )
        current += timedelta(days=1)
    return {"items": items, "month": month}


def attendance_board(
    session: Session, *, day: date, department_id: int | None
) -> list[dict[str, Any]]:
    conditions = [
        Employee.join_date <= day,
        or_(Employee.exit_date.is_(None), Employee.exit_date >= day),
        Employee.status.in_(("active", "probation")),
    ]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    employees = session.execute(
        select(Employee, Department.name)
        .join(Department, Department.id == Employee.department_id)
        .where(*conditions)
        .order_by(Employee.employee_code)
    ).all()
    employee_ids = [employee.id for employee, _ in employees]
    records = (
        {
            item.employee_id: item
            for item in session.scalars(
                select(Attendance).where(
                    Attendance.employee_id.in_(employee_ids), Attendance.date == day
                )
            ).all()
        }
        if employee_ids
        else {}
    )
    on_leave = (
        set(
            session.scalars(
                select(LeaveRequest.employee_id).where(
                    LeaveRequest.employee_id.in_(employee_ids),
                    LeaveRequest.status == "approved",
                    LeaveRequest.start_date <= day,
                    LeaveRequest.end_date >= day,
                )
            ).all()
        )
        if employee_ids
        else set()
    )
    settings = get_company_settings(session)
    holidays = holiday_dates(session, day, day)
    today = local_date()
    return [
        {
            "employee_id": employee.id,
            "employee_code": employee.employee_code,
            "employee_name": f"{employee.first_name} {employee.last_name}",
            "department_id": employee.department_id,
            "department": department,
            "date": day,
            "status": derive_attendance_status(
                day,
                today=today,
                record=records.get(employee.id),
                on_leave=employee.id in on_leave,
                weekend_days=settings.weekend_days,
                holidays=holidays,
            ),
            "check_in": records[employee.id].check_in
            if employee.id in records
            else None,
            "check_out": records[employee.id].check_out
            if employee.id in records
            else None,
        }
        for employee, department in employees
    ]


def list_attendance(
    session: Session,
    *,
    employee_id: int,
    from_date: date,
    to_date: date,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    if from_date > to_date:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    conditions = [
        Attendance.employee_id == employee_id,
        Attendance.date >= from_date,
        Attendance.date <= to_date,
    ]
    total = session.scalar(select(func.count(Attendance.id)).where(*conditions)) or 0
    records = session.scalars(
        select(Attendance)
        .where(*conditions)
        .order_by(Attendance.date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_attendance_dict(item) for item in records],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def attendance_summary_for_employee(
    session: Session, employee_id: int
) -> dict[str, int]:
    today = local_date()
    start = today.replace(day=1)
    calendar_data = _calendar_for_employee_range(session, employee_id, start, today)
    counts = {
        key: 0
        for key in (
            "present",
            "late",
            "half_day",
            "missing_checkout",
            "absent",
            "on_leave",
        )
    }
    for item in calendar_data:
        if item["status"] in counts:
            counts[item["status"]] += 1
    return counts


def _calendar_for_employee_range(
    session: Session, employee_id: int, start: date, end: date
) -> list[dict[str, Any]]:
    settings = get_company_settings(session)
    holidays = holiday_dates(session, start, end)
    records = {
        item.date: item
        for item in session.scalars(
            select(Attendance).where(
                Attendance.employee_id == employee_id,
                Attendance.date >= start,
                Attendance.date <= end,
            )
        ).all()
    }
    leaves = session.scalars(
        select(LeaveRequest).where(
            LeaveRequest.employee_id == employee_id,
            LeaveRequest.status == "approved",
            LeaveRequest.end_date >= start,
            LeaveRequest.start_date <= end,
        )
    ).all()
    leave_days = {
        day
        for leave in leaves
        for day in (
            leave.start_date + timedelta(days=offset)
            for offset in range((leave.end_date - leave.start_date).days + 1)
        )
    }
    today = local_date()
    return [
        {
            "date": day,
            "status": derive_attendance_status(
                day,
                today=today,
                record=records.get(day),
                on_leave=day in leave_days,
                weekend_days=settings.weekend_days,
                holidays=holidays,
            ),
        }
        for day in working_dates(start, end, [], set())
    ]


def _correction_dict(
    correction: AttendanceCorrection, employee_name: str
) -> dict[str, Any]:
    return {
        "id": correction.id,
        "employee_id": correction.employee_id,
        "employee_name": employee_name,
        "date": correction.date,
        "requested_check_in": correction.requested_check_in,
        "requested_check_out": correction.requested_check_out,
        "reason": correction.reason,
        "status": correction.status,
        "reviewed_by": correction.reviewed_by,
        "comment": correction.comment,
        "created_at": correction.created_at,
    }


def request_correction(
    session: Session, *, user: User, payload: AttendanceCorrectionCreate
) -> dict[str, Any]:
    employee_id = _employee_id(user)
    if payload.date >= local_date():
        raise ApiError(
            422, "CORRECTION_PAST_DATE_REQUIRED", "Corrections are only for past dates"
        )
    for requested_time in (
        payload.requested_check_in,
        payload.requested_check_out,
    ):
        if (
            requested_time is not None
            and requested_time.astimezone(company_timezone()).date() != payload.date
        ):
            raise ApiError(
                422,
                "CORRECTION_DATE_MISMATCH",
                "Requested times must fall on the correction date",
            )
    lock_key = 1_000_000_000 + employee_id * 100_000 + payload.date.toordinal()
    with commit_or_rollback(session):
        session.execute(select(func.pg_advisory_xact_lock(lock_key)))
        pending = session.scalar(
            select(AttendanceCorrection.id).where(
                AttendanceCorrection.employee_id == employee_id,
                AttendanceCorrection.date == payload.date,
                AttendanceCorrection.status == "pending",
            )
        )
        if pending is not None:
            raise ApiError(
                409, "CORRECTION_PENDING", "A pending correction already exists"
            )
        correction = AttendanceCorrection(
            employee_id=employee_id,
            date=payload.date,
            requested_check_in=payload.requested_check_in,
            requested_check_out=payload.requested_check_out,
            reason=payload.reason.strip(),
        )
        session.add(correction)
        session.flush()
        write_audit_log(
            session,
            actor_id=user.id,
            action="create",
            entity="attendance_corrections",
            entity_id=correction.id,
            after={
                "employee_id": employee_id,
                "date": payload.date,
                "status": "pending",
            },
        )
    employee = session.get(Employee, employee_id)
    return _correction_dict(correction, f"{employee.first_name} {employee.last_name}")


def list_corrections(
    session: Session,
    *,
    user: User,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    conditions = []
    if user.role == "employee":
        conditions.append(AttendanceCorrection.employee_id == _employee_id(user))
    if status:
        conditions.append(AttendanceCorrection.status == status)
    total = (
        session.scalar(select(func.count(AttendanceCorrection.id)).where(*conditions))
        or 0
    )
    rows = session.execute(
        select(AttendanceCorrection, Employee.first_name, Employee.last_name)
        .join(Employee, Employee.id == AttendanceCorrection.employee_id)
        .where(*conditions)
        .order_by(
            AttendanceCorrection.created_at.desc(), AttendanceCorrection.id.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            _correction_dict(item, f"{first} {last}") for item, first, last in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def decide_correction(
    session: Session,
    *,
    reviewer: User,
    correction_id: int,
    payload: DecisionRequest,
) -> dict[str, Any]:
    with commit_or_rollback(session):
        correction = session.scalar(
            select(AttendanceCorrection)
            .where(AttendanceCorrection.id == correction_id)
            .with_for_update()
        )
        if correction is None:
            raise ApiError(404, "CORRECTION_NOT_FOUND", "Correction was not found")
        if correction.status != "pending":
            raise ApiError(
                409, "CORRECTION_NOT_PENDING", "Correction is already decided"
            )
        if (
            session.scalar(
                select(PayrollRun.id).where(
                    PayrollRun.month == correction.date.strftime("%Y-%m"),
                    PayrollRun.status == "finalized",
                )
            )
            is not None
        ):
            raise ApiError(
                409, "PAYROLL_FINALIZED", "Finalized payroll locks this correction"
            )
        correction.status = "approved" if payload.action == "approve" else "rejected"
        correction.reviewed_by = reviewer.id
        correction.comment = payload.comment
        if payload.action == "approve":
            attendance = session.scalar(
                select(Attendance)
                .where(
                    Attendance.employee_id == correction.employee_id,
                    Attendance.date == correction.date,
                )
                .with_for_update()
            )
            attendance_before = _attendance_dict(attendance) if attendance else None
            if attendance is None:
                if correction.requested_check_in is None:
                    raise ApiError(
                        422, "CHECK_IN_REQUIRED", "A corrected check-in is required"
                    )
                attendance = Attendance(
                    employee_id=correction.employee_id,
                    date=correction.date,
                    check_in=correction.requested_check_in.astimezone(UTC),
                    check_out=(
                        correction.requested_check_out.astimezone(UTC)
                        if correction.requested_check_out
                        else None
                    ),
                    status="present",
                    source="web",
                )
                session.add(attendance)
                session.flush()
            else:
                if correction.requested_check_in is not None:
                    attendance.check_in = correction.requested_check_in.astimezone(UTC)
                if correction.requested_check_out is not None:
                    attendance.check_out = correction.requested_check_out.astimezone(
                        UTC
                    )
            if (
                attendance.check_out is not None
                and attendance.check_out <= attendance.check_in
            ):
                raise ApiError(
                    422,
                    "INVALID_CORRECTION_TIMES",
                    "Corrected check-out must be after check-in",
                )
            attendance.status = _status_for_times(
                get_company_settings(session), attendance.check_in, attendance.check_out
            )
            write_audit_log(
                session,
                actor_id=reviewer.id,
                action="update" if attendance_before else "create",
                entity="attendance",
                entity_id=attendance.id,
                before=attendance_before,
                after=_attendance_dict(attendance),
            )
        write_audit_log(
            session,
            actor_id=reviewer.id,
            action="approve" if payload.action == "approve" else "reject",
            entity="attendance_corrections",
            entity_id=correction.id,
            before={"status": "pending"},
            after={"status": correction.status, "comment": correction.comment},
        )
        notify_employee(
            session,
            employee_id=correction.employee_id,
            notification_type="correction",
            message=f"Attendance correction was {correction.status}",
        )
    employee = session.get(Employee, correction.employee_id)
    return _correction_dict(correction, f"{employee.first_name} {employee.last_name}")
