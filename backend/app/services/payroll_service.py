from decimal import Decimal
from io import BytesIO
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.models.attendance import Attendance
from app.models.employee import Employee, SalaryStructure
from app.models.leave import LeaveRequest
from app.models.organization import Department, Designation, LeaveType
from app.models.payroll import PayrollRun, Payslip
from app.models.user import Settings as CompanySettings
from app.models.user import User
from app.services.audit_service import write_audit_log
from app.services.hr_utils import (
    active_during,
    get_company_settings,
    holiday_dates,
    money,
    month_bounds,
    working_dates,
)
from app.services.notification_service import notify_employee
from app.services.transactions import commit_or_rollback

ZERO = Decimal("0.00")


def annual_tax(monthly_gross: Decimal) -> Decimal:
    annual = monthly_gross * Decimal(12)
    if annual <= Decimal(600000):
        result = ZERO
    elif annual <= Decimal(1200000):
        result = (annual - Decimal(600000)) * Decimal("0.05")
    elif annual <= Decimal(2400000):
        result = Decimal(30000) + (annual - Decimal(1200000)) * Decimal("0.15")
    elif annual <= Decimal(3600000):
        result = Decimal(210000) + (annual - Decimal(2400000)) * Decimal("0.25")
    else:
        result = Decimal(510000) + (annual - Decimal(3600000)) * Decimal("0.35")
    return money(result)


def monthly_tax(monthly_gross: Decimal) -> Decimal:
    return money(annual_tax(monthly_gross) / Decimal(12))


def _payslip_dict(
    payslip: Payslip, employee_name: str, employee_code: str
) -> dict[str, Any]:
    return {
        "id": payslip.id,
        "employee_id": payslip.employee_id,
        "employee_name": employee_name,
        "employee_code": employee_code,
        "basic": float(payslip.basic),
        "hra": float(payslip.hra),
        "medical": float(payslip.medical),
        "gross": float(payslip.gross),
        "working_days": payslip.working_days,
        "paid_days": float(payslip.paid_days),
        "absent_days": float(payslip.absent_days),
        "unpaid_days": float(payslip.unpaid_days),
        "half_days": float(payslip.half_days),
        "deduction": float(payslip.deduction),
        "tax": float(payslip.tax),
        "net": float(payslip.net),
    }


def _run_dict(
    session: Session, run: PayrollRun, *, include_payslips: bool
) -> dict[str, Any]:
    payslips = []
    if include_payslips:
        rows = session.execute(
            select(
                Payslip, Employee.first_name, Employee.last_name, Employee.employee_code
            )
            .join(Employee, Employee.id == Payslip.employee_id)
            .where(Payslip.run_id == run.id)
            .order_by(Employee.employee_code)
        ).all()
        payslips = [
            _payslip_dict(item, f"{first} {last}", code)
            for item, first, last, code in rows
        ]
    return {
        "id": run.id,
        "month": run.month,
        "status": run.status,
        "created_by": run.created_by,
        "finalized_by": run.finalized_by,
        "finalized_at": run.finalized_at,
        "total_gross": float(run.total_gross),
        "total_net": float(run.total_net),
        "payslips": payslips,
        "created_at": run.created_at,
    }


def _calculate_employee(
    session: Session,
    *,
    run_id: int,
    employee: Employee,
    salary: SalaryStructure,
    month_start,
    month_end,
    month_working_dates,
) -> Payslip:
    employed_dates = [
        day
        for day in month_working_dates
        if active_during(employee.join_date, employee.exit_date, day)
    ]
    date_set = set(employed_dates)
    attendance = {
        item.date: item
        for item in session.scalars(
            select(Attendance).where(
                Attendance.employee_id == employee.id,
                Attendance.date >= month_start,
                Attendance.date <= month_end,
            )
        ).all()
    }
    leave_rows = session.execute(
        select(LeaveRequest, LeaveType.is_paid)
        .join(LeaveType, LeaveType.id == LeaveRequest.leave_type_id)
        .where(
            LeaveRequest.employee_id == employee.id,
            LeaveRequest.status == "approved",
            LeaveRequest.end_date >= month_start,
            LeaveRequest.start_date <= month_end,
        )
    ).all()
    paid_leave: set = set()
    unpaid_leave: set = set()
    for leave, is_paid in leave_rows:
        for day in date_set:
            if leave.start_date <= day <= leave.end_date:
                (paid_leave if is_paid else unpaid_leave).add(day)

    half_days = Decimal(
        sum(
            1
            for day in employed_dates
            if day not in paid_leave
            and day not in unpaid_leave
            and attendance.get(day)
            and attendance[day].status == "half_day"
        )
    )
    unpaid_days = Decimal(len(unpaid_leave))
    absent_days = Decimal(
        sum(
            1
            for day in employed_dates
            if day not in attendance
            and day not in paid_leave
            and day not in unpaid_leave
        )
    )
    full_gross = money(salary.basic + salary.hra + salary.medical)
    total_working = len(month_working_dates)
    employed_working = len(employed_dates)
    per_day = full_gross / Decimal(total_working)
    prorated_gross = money(per_day * Decimal(employed_working))
    deduction_units = absent_days + unpaid_days + half_days * Decimal("0.5")
    deduction = money(per_day * deduction_units)
    tax = monthly_tax(full_gross)
    net = money(prorated_gross - deduction - tax)
    paid_days = max(
        Decimal("0.00"),
        Decimal(employed_working)
        - absent_days
        - unpaid_days
        - half_days * Decimal("0.5"),
    )
    return Payslip(
        run_id=run_id,
        employee_id=employee.id,
        basic=salary.basic,
        hra=salary.hra,
        medical=salary.medical,
        gross=prorated_gross,
        working_days=total_working,
        paid_days=paid_days,
        absent_days=absent_days,
        unpaid_days=unpaid_days,
        half_days=half_days,
        deduction=deduction,
        tax=tax,
        net=net,
    )


def _rebuild_payslips(session: Session, run: PayrollRun) -> None:
    month_start, month_end = month_bounds(run.month)
    settings = get_company_settings(session)
    holidays = holiday_dates(session, month_start, month_end)
    month_days = working_dates(month_start, month_end, settings.weekend_days, holidays)
    if not month_days:
        raise ApiError(422, "NO_WORKING_DAYS", "Payroll month has no working days")
    session.execute(delete(Payslip).where(Payslip.run_id == run.id))
    rows = session.execute(
        select(Employee, SalaryStructure)
        .join(SalaryStructure, SalaryStructure.employee_id == Employee.id)
        .where(
            Employee.join_date <= month_end,
            or_(Employee.exit_date.is_(None), Employee.exit_date >= month_start),
        )
        .order_by(Employee.id)
    ).all()
    payslips = [
        _calculate_employee(
            session,
            run_id=run.id,
            employee=employee,
            salary=salary,
            month_start=month_start,
            month_end=month_end,
            month_working_dates=month_days,
        )
        for employee, salary in rows
    ]
    session.add_all(payslips)
    session.flush()
    run.total_gross = money(sum((item.gross for item in payslips), ZERO))
    run.total_net = money(sum((item.net for item in payslips), ZERO))


def create_payroll_run(session: Session, *, actor: User, month: str) -> dict[str, Any]:
    month_bounds(month)
    try:
        with commit_or_rollback(session):
            run = PayrollRun(month=month, status="draft", created_by=actor.id)
            session.add(run)
            session.flush()
            _rebuild_payslips(session, run)
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="payroll_runs",
                entity_id=run.id,
                after={
                    "month": run.month,
                    "status": run.status,
                    "total_gross": run.total_gross,
                    "total_net": run.total_net,
                },
            )
        return _run_dict(session, run, include_payslips=True)
    except IntegrityError as exc:
        raise ApiError(
            409, "PAYROLL_EXISTS", "Payroll run already exists for this month"
        ) from exc


def list_payroll_runs(session: Session, *, page: int, page_size: int) -> dict[str, Any]:
    total = session.scalar(select(func.count(PayrollRun.id))) or 0
    runs = session.scalars(
        select(PayrollRun)
        .order_by(PayrollRun.month.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_run_dict(session, run, include_payslips=False) for run in runs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_payroll_run(session: Session, *, run_id: int) -> dict[str, Any]:
    run = session.get(PayrollRun, run_id)
    if run is None:
        raise ApiError(404, "PAYROLL_NOT_FOUND", "Payroll run was not found")
    return _run_dict(session, run, include_payslips=True)


def recalculate_payroll(
    session: Session, *, actor: User, run_id: int
) -> dict[str, Any]:
    with commit_or_rollback(session):
        run = session.scalar(
            select(PayrollRun).where(PayrollRun.id == run_id).with_for_update()
        )
        if run is None:
            raise ApiError(404, "PAYROLL_NOT_FOUND", "Payroll run was not found")
        if run.status == "finalized":
            raise ApiError(
                409, "PAYROLL_FINALIZED", "Finalized payroll cannot be recalculated"
            )
        before = {"total_gross": run.total_gross, "total_net": run.total_net}
        _rebuild_payslips(session, run)
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="payroll_runs",
            entity_id=run.id,
            before=before,
            after={"total_gross": run.total_gross, "total_net": run.total_net},
        )
    return _run_dict(session, run, include_payslips=True)


def finalize_payroll(
    session: Session, *, actor: User, run_id: int, now=None
) -> dict[str, Any]:
    from app.services.hr_utils import utc_now

    with commit_or_rollback(session):
        run = session.scalar(
            select(PayrollRun).where(PayrollRun.id == run_id).with_for_update()
        )
        if run is None:
            raise ApiError(404, "PAYROLL_NOT_FOUND", "Payroll run was not found")
        if run.status == "finalized":
            raise ApiError(409, "PAYROLL_FINALIZED", "Payroll is already finalized")
        run.status = "finalized"
        run.finalized_by = actor.id
        run.finalized_at = now or utc_now()
        employee_ids = session.scalars(
            select(Payslip.employee_id).where(Payslip.run_id == run.id)
        ).all()
        for employee_id in employee_ids:
            notify_employee(
                session,
                employee_id=employee_id,
                notification_type="payslip",
                message=f"Payslip for {run.month} is available",
            )
        write_audit_log(
            session,
            actor_id=actor.id,
            action="finalize",
            entity="payroll_runs",
            entity_id=run.id,
            before={"status": "draft"},
            after={"status": "finalized", "finalized_by": actor.id},
        )
    return _run_dict(session, run, include_payslips=True)


def list_my_payslips(
    session: Session, *, user: User, page: int, page_size: int
) -> dict[str, Any]:
    if user.employee_id is None:
        raise ApiError(
            422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
        )
    conditions = [
        Payslip.employee_id == user.employee_id,
        PayrollRun.status == "finalized",
    ]
    total = (
        session.scalar(
            select(func.count(Payslip.id))
            .join(PayrollRun, PayrollRun.id == Payslip.run_id)
            .where(*conditions)
        )
        or 0
    )
    rows = session.execute(
        select(Payslip, PayrollRun.month)
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .where(*conditions)
        .order_by(PayrollRun.month.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": slip.id,
                "month": month,
                "gross": float(slip.gross),
                "deduction": float(slip.deduction),
                "tax": float(slip.tax),
                "net": float(slip.net),
            }
            for slip, month in rows
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def generate_payslip_pdf(
    session: Session, *, user: User, payslip_id: int
) -> tuple[bytes, str]:
    row = session.execute(
        select(
            Payslip,
            PayrollRun,
            Employee,
            Department.name,
            Designation.name,
            CompanySettings.company_name,
        )
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .join(Designation, Designation.id == Employee.designation_id)
        .join(CompanySettings, CompanySettings.id == 1)
        .where(Payslip.id == payslip_id)
    ).one_or_none()
    if row is None:
        raise ApiError(404, "PAYSLIP_NOT_FOUND", "Payslip was not found")
    payslip, run, employee, department, designation, company = row
    if user.role == "employee" and user.employee_id != employee.id:
        raise ApiError(403, "FORBIDDEN", "You cannot access another employee's payslip")
    if user.role == "employee" and run.status != "finalized":
        raise ApiError(403, "FORBIDDEN", "Draft payslips are not available")

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setPageCompression(0)
    width, height = A4
    pdf.setTitle(f"Payslip {run.month} - {employee.employee_code}")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(50, height - 60, company)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(50, height - 90, f"Payslip - {run.month}")
    pdf.setFont("Helvetica", 10)
    lines = [
        ("Employee", f"{employee.first_name} {employee.last_name}"),
        ("Employee Code", employee.employee_code),
        ("Department", department),
        ("Designation", designation),
        ("Basic", f"PKR {payslip.basic:,.2f}"),
        ("HRA", f"PKR {payslip.hra:,.2f}"),
        ("Medical", f"PKR {payslip.medical:,.2f}"),
        ("Gross", f"PKR {payslip.gross:,.2f}"),
        ("Attendance Deduction", f"PKR {payslip.deduction:,.2f}"),
        ("Tax", f"PKR {payslip.tax:,.2f}"),
        ("Net Salary", f"PKR {payslip.net:,.2f}"),
    ]
    y = height - 130
    for label, value in lines:
        pdf.setFont("Helvetica-Bold", 10)
        pdf.drawString(60, y, label)
        pdf.setFont("Helvetica", 10)
        pdf.drawRightString(width - 60, y, value)
        pdf.line(55, y - 5, width - 55, y - 5)
        y -= 28
    pdf.setFont("Helvetica-Oblique", 8)
    pdf.drawString(50, 40, "Generated by HCM Lite from the finalized payroll snapshot.")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue(), f"payslip-{employee.employee_code}-{run.month}.pdf"


def payroll_summary(
    session: Session, *, month: str, department_id: int | None
) -> dict[str, Any]:
    conditions = [PayrollRun.month == month]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    gross, net, count = session.execute(
        select(
            func.coalesce(func.sum(Payslip.gross), 0),
            func.coalesce(func.sum(Payslip.net), 0),
            func.count(Payslip.id),
        )
        .select_from(Payslip)
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .where(*conditions)
    ).one()
    return {
        "month": month,
        "employees": count,
        "gross": float(gross),
        "net": float(net),
    }
