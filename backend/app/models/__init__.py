"""All SQLAlchemy models, imported here for Alembic metadata registration."""

from app.models.ai_log import AILog
from app.models.attendance import Attendance, AttendanceCorrection
from app.models.audit import AuditLog
from app.models.base import Base
from app.models.communication import Announcement, Notification
from app.models.employee import Employee, SalaryStructure
from app.models.leave import LeaveRequest
from app.models.organization import (
    Department,
    Designation,
    Holiday,
    LeaveType,
)
from app.models.payroll import PayrollRun, Payslip
from app.models.user import Settings, User

__all__ = [
    "AILog",
    "Announcement",
    "Attendance",
    "AttendanceCorrection",
    "AuditLog",
    "Base",
    "Department",
    "Designation",
    "Employee",
    "Holiday",
    "LeaveRequest",
    "LeaveType",
    "Notification",
    "PayrollRun",
    "Payslip",
    "SalaryStructure",
    "Settings",
    "User",
]
