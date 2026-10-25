from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.attendance import Attendance
from app.models.leave import LeaveRequest
from app.models.payroll import PayrollRun, Payslip
from app.models.user import User
from app.services.attendance_service import derive_attendance_status
from app.services.hr_utils import (
    get_company_settings,
    holiday_dates,
    local_date,
    month_bounds,
    utc_now,
)
from app.services.leave_service import get_leave_balance

WEEKLY_TARGET_HOURS = 40


def _duration_seconds(record: Attendance, *, now: datetime | None = None) -> float:
    if record.check_out is not None:
        end = record.check_out
    elif now is not None and record.date == local_date(now):
        end = now
    else:
        return 0.0
    return max(0.0, (end - record.check_in).total_seconds())


def _duration_label(seconds: float) -> str:
    total_minutes = int(seconds // 60)
    hours, minutes = divmod(total_minutes, 60)
    return f"{hours}h {minutes}m"


def get_employee_dashboard(
    session: Session, *, user: User, now: datetime | None = None
) -> dict[str, Any]:
    if user.employee_id is None:
        raise ApiError(
            422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
        )
    timestamp = now or utc_now()
    if timestamp.tzinfo is None:
        raise ValueError("Dashboard time must be timezone-aware")
    timestamp = timestamp.astimezone(UTC)
    today = local_date(timestamp)
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    month_start, month_end = month_bounds(f"{today.year:04d}-{today.month:02d}")
    query_start = min(week_start, month_start)
    query_end = max(today, min(week_end, month_end))

    records = session.scalars(
        select(Attendance).where(
            Attendance.employee_id == user.employee_id,
            Attendance.date >= query_start,
            Attendance.date <= query_end,
        )
    ).all()
    records_by_date = {record.date: record for record in records}
    today_record = records_by_date.get(today)
    on_leave = bool(
        session.scalar(
            select(LeaveRequest.id).where(
                LeaveRequest.employee_id == user.employee_id,
                LeaveRequest.status == "approved",
                LeaveRequest.start_date <= today,
                LeaveRequest.end_date >= today,
            )
        )
    )
    settings = get_company_settings(session)
    holidays = holiday_dates(session, today, today)
    today_status = derive_attendance_status(
        today,
        today=today,
        record=today_record,
        on_leave=on_leave,
        weekend_days=settings.weekend_days,
        holidays=holidays,
    )
    today_seconds = (
        _duration_seconds(today_record, now=timestamp) if today_record else 0.0
    )

    daily_hours = []
    weekly_seconds = 0.0
    current = week_start
    while current <= week_end:
        if current.weekday() not in settings.weekend_days:
            record = records_by_date.get(current)
            seconds = _duration_seconds(record) if record else 0.0
            weekly_seconds += seconds
            daily_hours.append(
                {
                    "day": current.strftime("%a"),
                    "date": current,
                    "hours": round(seconds / 3600, 2),
                }
            )
        current += timedelta(days=1)

    late_count = (
        session.scalar(
            select(func.count(Attendance.id)).where(
                Attendance.employee_id == user.employee_id,
                Attendance.date >= month_start,
                Attendance.date <= month_end,
                Attendance.status == "late",
            )
        )
        or 0
    )
    last_payslip_row = session.execute(
        select(Payslip, PayrollRun.month)
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .where(
            Payslip.employee_id == user.employee_id,
            PayrollRun.status == "finalized",
        )
        .order_by(PayrollRun.month.desc(), Payslip.id.desc())
        .limit(1)
    ).one_or_none()
    last_payslip = None
    if last_payslip_row is not None:
        payslip, month = last_payslip_row
        last_payslip = {
            "id": payslip.id,
            "month": month,
            "gross": float(payslip.gross),
            "deductions": float(payslip.deduction),
            "tax": float(payslip.tax),
            "net": float(payslip.net),
        }

    return {
        "today_status": {
            "date": today,
            "status": today_status,
            "check_in": today_record.check_in if today_record else None,
            "check_out": today_record.check_out if today_record else None,
            "work_duration": _duration_label(today_seconds),
        },
        "hours_this_week": round(weekly_seconds / 3600, 2),
        "weekly_target_hours": WEEKLY_TARGET_HOURS,
        "daily_hours": daily_hours,
        "late_count": late_count,
        "leave_balance": get_leave_balance(
            session, employee_id=user.employee_id, year=today.year
        ),
        "last_payslip": last_payslip,
    }
