from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.attendance import Attendance, AttendanceCorrection
from app.models.employee import Employee
from app.models.leave import LeaveRequest
from app.models.organization import Department
from app.models.user import User
from app.services.hr_utils import (
    get_company_settings,
    holiday_dates,
    local_date,
    month_bounds,
    working_dates,
)
from app.services.leave_service import get_leave_balance, leave_summary
from app.services.payroll_service import payroll_summary


def _require_management(user: User) -> None:
    if user.role not in {"admin", "hr"}:
        raise ApiError(403, "FORBIDDEN", "Management access is required")


def _require_department(session: Session, department_id: int | None) -> None:
    if department_id is not None and session.get(Department, department_id) is None:
        raise ApiError(404, "DEPARTMENT_NOT_FOUND", "Department was not found")


def get_headcount(
    session: Session, *, user: User, department_id: int | None = None
) -> dict[str, Any]:
    _require_management(user)
    _require_department(session, department_id)
    today = local_date()
    conditions = [
        Employee.status.in_(("active", "probation")),
        Employee.join_date <= today,
        or_(Employee.exit_date.is_(None), Employee.exit_date >= today),
    ]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    total = session.scalar(select(func.count(Employee.id)).where(*conditions)) or 0
    rows = session.execute(
        select(Department.id, Department.name, func.count(Employee.id))
        .join(Employee, Employee.department_id == Department.id)
        .where(*conditions)
        .group_by(Department.id, Department.name)
        .order_by(Department.name)
    ).all()
    return {
        "total": total,
        "by_department": [
            {"department_id": item_id, "department": name, "count": count}
            for item_id, name, count in rows
        ],
    }


def _report_data(
    session: Session,
    from_date: date,
    to_date: date,
    department_id: int | None,
    employee_id: int | None = None,
):
    if from_date > to_date:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    employee_conditions = [
        Employee.join_date <= to_date,
        or_(Employee.exit_date.is_(None), Employee.exit_date >= from_date),
    ]
    if department_id is not None:
        employee_conditions.append(Employee.department_id == department_id)
    if employee_id is not None:
        employee_conditions.append(Employee.id == employee_id)
    employees = session.execute(
        select(Employee, Department.name)
        .join(Department, Department.id == Employee.department_id)
        .where(*employee_conditions)
    ).all()
    ids = [employee.id for employee, _ in employees]
    attendance = (
        session.scalars(
            select(Attendance).where(
                Attendance.employee_id.in_(ids),
                Attendance.date >= from_date,
                Attendance.date <= to_date,
            )
        ).all()
        if ids
        else []
    )
    leaves = (
        session.scalars(
            select(LeaveRequest).where(
                LeaveRequest.employee_id.in_(ids),
                LeaveRequest.status == "approved",
                LeaveRequest.end_date >= from_date,
                LeaveRequest.start_date <= to_date,
            )
        ).all()
        if ids
        else []
    )
    return employees, attendance, leaves


def _summarize_attendance(
    employees: list,
    records: list[Attendance],
    leaves: list[LeaveRequest],
    work_days: list[date],
    *,
    today: date,
) -> dict[str, int | float]:
    record_map = {(item.employee_id, item.date): item for item in records}
    leave_days = {
        (leave.employee_id, day)
        for leave in leaves
        for day in work_days
        if leave.start_date <= day <= leave.end_date
    }
    counts = defaultdict(int)
    expected = 0
    for employee, _ in employees:
        for day in work_days:
            if not (
                employee.join_date <= day
                and (employee.exit_date is None or employee.exit_date >= day)
            ):
                continue
            if (employee.id, day) in leave_days:
                counts["on_leave"] += 1
                continue
            expected += 1
            record = record_map.get((employee.id, day))
            if record is None:
                if day < today:
                    counts["absent"] += 1
            elif record.check_out is None and day < today:
                counts["missing_checkout"] += 1
            else:
                counts[record.status] += 1
    numerator = (
        counts["present"]
        + counts["late"]
        + counts["missing_checkout"]
        + 0.5 * counts["half_day"]
    )
    return {
        "present": counts["present"],
        "late": counts["late"],
        "half_day": counts["half_day"],
        "missing_checkout": counts["missing_checkout"],
        "absent": counts["absent"],
        "on_leave": counts["on_leave"],
        "attendance_rate": round(numerator / expected * 100, 2) if expected else 0.0,
        "expected_work_days": expected,
    }


def get_attendance_summary(
    session: Session,
    *,
    user: User,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
) -> dict[str, Any]:
    if user.role == "employee":
        if user.employee_id is None:
            raise ApiError(
                422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
            )
        department_id = None
    elif user.role not in {"admin", "hr"}:
        raise ApiError(403, "FORBIDDEN", "You do not have permission")
    else:
        _require_department(session, department_id)
    employees, records, leaves = _report_data(
        session,
        from_date,
        to_date,
        department_id,
        employee_id=user.employee_id if user.role == "employee" else None,
    )
    settings = get_company_settings(session)
    work_days = working_dates(
        from_date,
        to_date,
        settings.weekend_days,
        holiday_dates(session, from_date, to_date),
    )
    return _summarize_attendance(
        employees, records, leaves, work_days, today=local_date()
    )


def get_late_comers(
    session: Session,
    *,
    user: User,
    from_date: date,
    to_date: date,
    limit: int = 5,
    department_id: int | None = None,
) -> list[dict[str, Any]]:
    _require_management(user)
    if from_date > to_date:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    _require_department(session, department_id)
    if limit < 1 or limit > 100:
        raise ApiError(422, "INVALID_LIMIT", "limit must be between 1 and 100")
    conditions = [
        Attendance.status == "late",
        Attendance.date >= from_date,
        Attendance.date <= to_date,
    ]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    rows = session.execute(
        select(
            Employee.id,
            Employee.employee_code,
            Employee.first_name,
            Employee.last_name,
            func.count(Attendance.id).label("late_count"),
        )
        .join(Attendance, Attendance.employee_id == Employee.id)
        .where(*conditions)
        .group_by(Employee.id)
        .order_by(func.count(Attendance.id).desc(), Employee.employee_code)
        .limit(limit)
    ).all()
    return [
        {
            "employee_id": item_id,
            "employee_code": code,
            "employee_name": f"{first} {last}",
            "late_count": count,
        }
        for item_id, code, first, last, count in rows
    ]


def get_leave_summary(
    session: Session,
    *,
    user: User,
    from_date: date,
    to_date: date,
    department_id: int | None = None,
) -> dict[str, Any]:
    _require_management(user)
    _require_department(session, department_id)
    return leave_summary(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
    )


def get_my_leave_balance(session: Session, *, user: User) -> list[dict[str, Any]]:
    if user.employee_id is None:
        raise ApiError(
            422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
        )
    return get_leave_balance(session, employee_id=user.employee_id)


def get_payroll_summary(
    session: Session,
    *,
    user: User,
    month: str,
    department_id: int | None = None,
) -> dict[str, Any]:
    _require_management(user)
    month_bounds(month)
    _require_department(session, department_id)
    return payroll_summary(session, month=month, department_id=department_id)


def search_employees(
    session: Session, *, user: User, text: str, limit: int = 10
) -> list[dict[str, Any]]:
    _require_management(user)
    if limit < 1 or limit > 100:
        raise ApiError(422, "INVALID_LIMIT", "limit must be between 1 and 100")
    pattern = f"%{text.strip()}%"
    rows = session.execute(
        select(
            Employee.id,
            Employee.employee_code,
            Employee.first_name,
            Employee.last_name,
            Department.name,
        )
        .join(Department, Department.id == Employee.department_id)
        .where(
            or_(
                Employee.employee_code.ilike(pattern),
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                Employee.email.ilike(pattern),
            )
        )
        .order_by(Employee.employee_code)
        .limit(limit)
    ).all()
    return [
        {
            "employee_id": item_id,
            "employee_code": code,
            "employee_name": f"{first} {last}",
            "department": department,
        }
        for item_id, code, first, last, department in rows
    ]


def get_hr_dashboard(
    session: Session,
    *,
    user: User,
    from_date: date | None,
    to_date: date | None,
    department_id: int | None,
) -> dict[str, Any]:
    _require_management(user)
    end = to_date or local_date()
    start = from_date or end - timedelta(days=29)
    if start > end:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    _require_department(session, department_id)
    headcount = get_headcount(session, user=user, department_id=department_id)["total"]
    today = local_date()
    today_summary = get_attendance_summary(
        session,
        user=user,
        from_date=today,
        to_date=today,
        department_id=department_id,
    )
    pending_leave_conditions = [LeaveRequest.status == "pending"]
    pending_correction_conditions = [AttendanceCorrection.status == "pending"]
    if department_id is not None:
        pending_leave_conditions.append(Employee.department_id == department_id)
        pending_correction_conditions.append(Employee.department_id == department_id)
    pending_leave = (
        session.scalar(
            select(func.count(LeaveRequest.id))
            .join(Employee, Employee.id == LeaveRequest.employee_id)
            .where(*pending_leave_conditions)
        )
        or 0
    )
    pending_corrections = (
        session.scalar(
            select(func.count(AttendanceCorrection.id))
            .join(Employee, Employee.id == AttendanceCorrection.employee_id)
            .where(*pending_correction_conditions)
        )
        or 0
    )

    employees, records, leaves = _report_data(session, start, end, department_id)
    settings = get_company_settings(session)
    work_days = working_dates(
        start, end, settings.weekend_days, holiday_dates(session, start, end)
    )
    attendance_trend = []
    for day in work_days:
        daily = _summarize_attendance(employees, records, leaves, [day], today=today)
        attendance_trend.append(
            {"date": day.isoformat(), "rate": daily["attendance_rate"]}
        )

    department_expected = defaultdict(int)
    department_absent = defaultdict(int)
    record_keys = {(item.employee_id, item.date) for item in records}
    leave_keys = {
        (leave.employee_id, day)
        for leave in leaves
        for day in work_days
        if leave.start_date <= day <= leave.end_date
    }
    department_names = {}
    for employee, department in employees:
        department_names[employee.department_id] = department
        for day in work_days:
            if employee.join_date <= day and (
                employee.exit_date is None or employee.exit_date >= day
            ):
                department_expected[employee.department_id] += 1
                if (
                    day < today
                    and (employee.id, day) not in record_keys
                    and (employee.id, day) not in leave_keys
                ):
                    department_absent[employee.department_id] += 1
    absenteeism = [
        {
            "department_id": item_id,
            "department": department_names[item_id],
            "absent_days": department_absent[item_id],
            "expected_days": expected,
            "rate": round(department_absent[item_id] / expected * 100, 2)
            if expected
            else 0.0,
        }
        for item_id, expected in sorted(department_expected.items())
    ]
    return {
        "headcount": headcount,
        "present_today": today_summary["present"]
        + today_summary["late"]
        + today_summary["half_day"],
        "on_leave_today": today_summary["on_leave"],
        "late_today": today_summary["late"],
        "pending_approvals": {
            "leave": pending_leave,
            "corrections": pending_corrections,
        },
        "attendance_trend": attendance_trend,
        "absenteeism_by_dept": absenteeism,
        "leave_by_type": get_leave_summary(
            session,
            user=user,
            from_date=start,
            to_date=end,
            department_id=department_id,
        )["by_type"],
        "top_late_comers": get_late_comers(
            session,
            user=user,
            from_date=start,
            to_date=end,
            limit=5,
            department_id=department_id,
        ),
    }
