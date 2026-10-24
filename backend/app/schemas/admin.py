from datetime import date, datetime, time
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


class MessageResponse(BaseModel):
    message: str


class SettingsResponse(BaseModel):
    company_name: str
    office_start: time
    grace_minutes: int
    half_day_hours: int
    weekend_days: list[int]
    office_lat: float | None
    office_lng: float | None
    office_radius_m: int


class SettingsUpdate(StrictModel):
    company_name: str = Field(min_length=1, max_length=150)
    office_start: time
    grace_minutes: int = Field(ge=0, le=1440)
    half_day_hours: int = Field(gt=0, le=24)
    weekend_days: list[int] = Field(max_length=7)
    office_lat: float | None = Field(default=None, ge=-90, le=90)
    office_lng: float | None = Field(default=None, ge=-180, le=180)
    office_radius_m: int = Field(gt=0, le=1_000_000)

    @field_validator("company_name")
    @classmethod
    def trim_company_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Company name must not be blank")
        return cleaned

    @field_validator("weekend_days")
    @classmethod
    def validate_weekend_days(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("Weekend days must be between 0 and 6")
        if len(set(value)) != len(value):
            raise ValueError("Weekend days must not contain duplicates")
        return sorted(value)

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "SettingsUpdate":
        if (self.office_lat is None) != (self.office_lng is None):
            raise ValueError("Office latitude and longitude must be supplied together")
        return self


class DepartmentWrite(StrictModel):
    name: str = Field(min_length=1, max_length=120)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Department name must not be blank")
        return cleaned


class DepartmentResponse(BaseModel):
    id: int
    name: str
    created_at: datetime


class DepartmentListResponse(BaseModel):
    items: list[DepartmentResponse]
    total: int
    page: int
    page_size: int


class DesignationCreate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    department_id: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Designation name must not be blank")
        return cleaned


class DesignationResponse(BaseModel):
    id: int
    name: str
    department_id: int | None
    department: str | None
    created_at: datetime


class DesignationListResponse(BaseModel):
    items: list[DesignationResponse]
    total: int
    page: int
    page_size: int


LeaveTypeCode = Literal["annual", "sick", "casual", "unpaid"]


class LeaveTypeCreate(StrictModel):
    code: LeaveTypeCode
    name: str = Field(min_length=1, max_length=100)
    yearly_quota: int | None = Field(default=None, ge=0)
    is_paid: bool

    @field_validator("code", mode="before")
    @classmethod
    def normalize_code(cls, value: object) -> object:
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Leave type name must not be blank")
        return cleaned


class LeaveTypeUpdate(StrictModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    yearly_quota: int | None = Field(default=None, ge=0)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Leave type name must not be blank")
        return cleaned

    @model_validator(mode="before")
    @classmethod
    def require_update_field(cls, value: object) -> object:
        if not isinstance(value, dict) or not value:
            raise ValueError("At least one field must be supplied")
        if "name" in value and value["name"] is None:
            raise ValueError("Leave type name must not be null")
        return value


class LeaveTypeResponse(BaseModel):
    id: int
    code: str
    name: str
    yearly_quota: int | None
    is_paid: bool
    created_at: datetime


class LeaveTypeListResponse(BaseModel):
    items: list[LeaveTypeResponse]
    total: int
    page: int
    page_size: int


class HolidayCreate(StrictModel):
    date: date
    name: str = Field(min_length=1, max_length=150)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Holiday name must not be blank")
        return cleaned


class HolidayResponse(BaseModel):
    id: int
    date: date
    name: str
    created_at: datetime


class HolidayListResponse(BaseModel):
    items: list[HolidayResponse]
    total: int
    page: int
    page_size: int


class HRUserCreate(StrictModel):
    email: EmailStr
    password: str | None = Field(default=None, min_length=8, max_length=72)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        return str(value).strip().lower() if isinstance(value, str) else value


class UserAdminResponse(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool
    must_change_password: bool
    employee_id: int | None
    created_at: datetime


class UserListResponse(BaseModel):
    items: list[UserAdminResponse]
    total: int
    page: int
    page_size: int


class HRUserCreateResponse(BaseModel):
    user: UserAdminResponse
    temp_password: str


class ResetPasswordResponse(BaseModel):
    temp_password: str


class AuditLogResponse(BaseModel):
    id: int
    actor_id: int | None
    action: str
    entity: str
    entity_id: int
    before: dict | None
    after: dict | None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int


class PayrollTotals(BaseModel):
    gross: float
    net: float


class DepartmentHeadcount(BaseModel):
    department_id: int
    department: str
    headcount: int


class DepartmentPayroll(BaseModel):
    department_id: int
    department: str
    gross: float
    net: float


class CategoryCount(BaseModel):
    category: str
    count: int


class AdminDashboardResponse(BaseModel):
    headcount: int
    attrition_ytd: float
    payroll_cost: PayrollTotals
    avg_salary: float | None
    headcount_by_dept: list[DepartmentHeadcount]
    payroll_cost_by_dept: list[DepartmentPayroll]
    gender: list[CategoryCount]
    tenure: list[CategoryCount]
    recent_audit: list[AuditLogResponse]
