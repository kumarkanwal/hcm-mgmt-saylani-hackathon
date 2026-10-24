from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EmployeeCreate(StrictModel):
    employee_code: str = Field(min_length=1, max_length=50)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    phone: str = Field(min_length=1, max_length=40)
    address: str | None = Field(default=None, max_length=500)
    gender: Literal["male", "female", "other"]
    department_id: int = Field(ge=1)
    designation_id: int = Field(ge=1)
    join_date: date
    basic_salary: Decimal = Field(gt=0)
    status: Literal["probation", "active"] = "probation"

    @field_validator("employee_code", "first_name", "last_name", "phone")
    @classmethod
    def trim_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Value must not be blank")
        return cleaned

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return str(value).strip().lower() if isinstance(value, str) else value


class EmployeeUpdate(StrictModel):
    department_id: int | None = Field(default=None, ge=1)
    designation_id: int | None = Field(default=None, ge=1)
    status: Literal["probation", "active", "exited"] | None = None
    exit_date: date | None = None

    @model_validator(mode="before")
    @classmethod
    def require_field(cls, value: object) -> object:
        if not isinstance(value, dict) or not value:
            raise ValueError("At least one field must be supplied")
        return value


class EmployeeSelfUpdate(StrictModel):
    phone: str | None = Field(default=None, min_length=1, max_length=40)
    address: str | None = Field(default=None, max_length=500)

    @model_validator(mode="before")
    @classmethod
    def require_field(cls, value: object) -> object:
        if not isinstance(value, dict) or not value:
            raise ValueError("At least one field must be supplied")
        return value


class EmployeeSummary(BaseModel):
    id: int
    employee_code: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    address: str | None
    gender: str
    department_id: int
    department: str
    designation_id: int
    designation: str
    join_date: date
    exit_date: date | None
    status: str
    created_at: datetime


class EmployeeListResponse(BaseModel):
    items: list[EmployeeSummary]
    total: int
    page: int
    page_size: int


class SalaryResponse(BaseModel):
    employee_id: int
    basic: float
    hra: float
    medical: float
    gross: float
    effective_from: date


class SalaryUpdate(StrictModel):
    basic: Decimal = Field(gt=0)


class EmployeeCreateResponse(BaseModel):
    employee: EmployeeSummary
    temp_password: str


class AttendanceSummary(BaseModel):
    present: int
    late: int
    half_day: int
    missing_checkout: int
    absent: int
    on_leave: int


class LeaveBalanceItem(BaseModel):
    leave_type_id: int
    leave_type: str
    code: str
    quota: float | None
    used: float
    pending: float
    remaining: float | None


class PayslipSummary(BaseModel):
    id: int
    month: str
    gross: float
    deduction: float
    tax: float
    net: float


class Employee360(BaseModel):
    employee: EmployeeSummary
    salary: SalaryResponse | None
    attendance_summary: AttendanceSummary
    leave_balance: list[LeaveBalanceItem]
    last_payslips: list[PayslipSummary]


class CSVError(BaseModel):
    row: int
    field: str
    reason: str


class CSVImportResponse(BaseModel):
    valid_rows: list[dict]
    errors: list[CSVError]
    created: list[EmployeeCreateResponse]


class CheckInRequest(StrictModel):
    source: Literal["web", "camera"] = "web"
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    accuracy: float | None = Field(default=None, ge=0)


class AttendanceResponse(BaseModel):
    id: int | None = None
    employee_id: int
    date: date
    check_in: datetime | None
    check_out: datetime | None
    status: str
    source: str | None = None


class AttendanceCalendarResponse(BaseModel):
    items: list[AttendanceResponse]
    month: str


class AttendanceListResponse(BaseModel):
    items: list[AttendanceResponse]
    total: int
    page: int
    page_size: int


class AttendanceBoardItem(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department_id: int
    department: str
    date: date
    status: str
    check_in: datetime | None
    check_out: datetime | None


class AttendanceCorrectionCreate(StrictModel):
    date: date
    requested_check_in: datetime | None = None
    requested_check_out: datetime | None = None
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def validate_times(self) -> "AttendanceCorrectionCreate":
        if self.requested_check_in is None and self.requested_check_out is None:
            raise ValueError("At least one requested time is required")
        if (
            self.requested_check_in is not None
            and self.requested_check_out is not None
            and self.requested_check_out <= self.requested_check_in
        ):
            raise ValueError("Requested check-out must be after check-in")
        for value in (self.requested_check_in, self.requested_check_out):
            if value is not None and value.tzinfo is None:
                raise ValueError("Requested times must include a timezone offset")
        return self


class DecisionRequest(StrictModel):
    action: Literal["approve", "reject"]
    comment: str | None = Field(default=None, max_length=1000)


class AttendanceCorrectionResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    date: date
    requested_check_in: datetime | None
    requested_check_out: datetime | None
    reason: str
    status: str
    reviewed_by: int | None
    comment: str | None
    created_at: datetime


class PaginatedCorrections(BaseModel):
    items: list[AttendanceCorrectionResponse]
    total: int
    page: int
    page_size: int


class LeaveCreate(StrictModel):
    leave_type_id: int = Field(ge=1)
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def validate_dates(self) -> "LeaveCreate":
        if self.end_date < self.start_date:
            raise ValueError("End date must not be before start date")
        return self


class LeaveResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    department_id: int
    department: str
    leave_type_id: int
    leave_type: str
    start_date: date
    end_date: date
    days: float
    reason: str
    status: str
    reviewed_by: int | None
    comment: str | None
    created_at: datetime


class PaginatedLeaves(BaseModel):
    items: list[LeaveResponse]
    total: int
    page: int
    page_size: int


class PayrollRunCreate(StrictModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class PayslipResponse(BaseModel):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    basic: float
    hra: float
    medical: float
    gross: float
    working_days: int
    paid_days: float
    absent_days: float
    unpaid_days: float
    half_days: float
    deduction: float
    tax: float
    net: float


class PayrollRunResponse(BaseModel):
    id: int
    month: str
    status: str
    created_by: int
    finalized_by: int | None
    finalized_at: datetime | None
    total_gross: float
    total_net: float
    payslips: list[PayslipResponse] = Field(default_factory=list)
    created_at: datetime


class PayrollRunListResponse(BaseModel):
    items: list[PayrollRunResponse]
    total: int
    page: int
    page_size: int


class PayslipListResponse(BaseModel):
    items: list[PayslipSummary]
    total: int
    page: int
    page_size: int


class HRDashboardResponse(BaseModel):
    headcount: int
    present_today: int
    on_leave_today: int
    late_today: int
    pending_approvals: dict[str, int]
    attendance_trend: list[dict]
    absenteeism_by_dept: list[dict]
    leave_by_type: list[dict]
    top_late_comers: list[dict]
