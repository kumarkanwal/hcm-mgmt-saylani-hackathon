from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.hr import LeaveBalanceItem


class TodayStatus(BaseModel):
    date: date
    status: str
    check_in: datetime | None
    check_out: datetime | None
    work_duration: str


class DailyHours(BaseModel):
    day: str
    date: date
    hours: float


class DashboardPayslip(BaseModel):
    id: int
    month: str
    gross: float
    deductions: float
    tax: float
    net: float


class EmployeeDashboardResponse(BaseModel):
    today_status: TodayStatus
    hours_this_week: float
    weekly_target_hours: int
    daily_hours: list[DailyHours]
    late_count: int
    leave_balance: list[LeaveBalanceItem]
    last_payslip: DashboardPayslip | None
