import calendar
from datetime import UTC, date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.organization import Holiday
from app.models.user import Settings as CompanySettings

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def company_timezone() -> ZoneInfo:
    return ZoneInfo(get_settings().company_timezone)


def utc_now() -> datetime:
    return datetime.now(UTC)


def local_date(value: datetime | None = None) -> date:
    return (value or utc_now()).astimezone(company_timezone()).date()


def get_company_settings(session: Session) -> CompanySettings:
    settings = session.get(CompanySettings, 1)
    if settings is None or not settings.is_setup_done:
        from app.core.exceptions import ApiError

        raise ApiError(409, "SETUP_REQUIRED", "Company setup has not been completed")
    return settings


def holiday_dates(session: Session, start: date, end: date) -> set[date]:
    return set(
        session.scalars(
            select(Holiday.date).where(Holiday.date >= start, Holiday.date <= end)
        ).all()
    )


def working_dates(
    start: date, end: date, weekend_days: list[int], holidays: set[date]
) -> list[date]:
    if end < start:
        return []
    days = []
    current = start
    while current <= end:
        if current.weekday() not in weekend_days and current not in holidays:
            days.append(current)
        current += timedelta(days=1)
    return days


def month_bounds(month: str) -> tuple[date, date]:
    try:
        year, month_number = (int(part) for part in month.split("-"))
        last_day = calendar.monthrange(year, month_number)[1]
    except (ValueError, TypeError) as exc:
        from app.core.exceptions import ApiError

        raise ApiError(422, "INVALID_MONTH", "Month must use YYYY-MM format") from exc
    return date(year, month_number, 1), date(year, month_number, last_day)


def active_during(join_date: date, exit_date: date | None, day: date) -> bool:
    return join_date <= day and (exit_date is None or exit_date >= day)
