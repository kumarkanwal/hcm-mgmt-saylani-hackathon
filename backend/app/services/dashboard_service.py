from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ApiError
from app.models.audit import AuditLog
from app.models.employee import Employee, SalaryStructure
from app.models.organization import Department
from app.models.payroll import PayrollRun, Payslip

ZERO = Decimal("0.00")


def _years_before(value: date, years: int) -> date:
    try:
        return value.replace(year=value.year - years)
    except ValueError:
        return value.replace(year=value.year - years, day=28)


def _active_conditions(report_date: date, department_id: int | None) -> list:
    conditions = [
        Employee.status.in_(("active", "probation")),
        Employee.join_date <= report_date,
        or_(Employee.exit_date.is_(None), Employee.exit_date >= report_date),
    ]
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    return conditions


def _employment_condition(report_date: date):
    return and_(
        Employee.join_date <= report_date,
        or_(Employee.exit_date.is_(None), Employee.exit_date >= report_date),
    )


def get_admin_dashboard(
    session: Session,
    *,
    from_date: date | None,
    to_date: date | None,
    department_id: int | None,
) -> dict:
    local_today = datetime.now(ZoneInfo(get_settings().company_timezone)).date()
    report_to = to_date or local_today
    report_from = from_date or date(report_to.year, 1, 1)
    if report_from > report_to:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    if department_id is not None and session.get(Department, department_id) is None:
        raise ApiError(404, "DEPARTMENT_NOT_FOUND", "Department was not found")

    active_conditions = _active_conditions(report_to, department_id)
    headcount = (
        session.scalar(select(func.count(Employee.id)).where(*active_conditions)) or 0
    )

    headcount_rows = session.execute(
        select(
            Department.id,
            Department.name,
            func.count(Employee.id),
        )
        .join(Employee, Employee.department_id == Department.id)
        .where(*active_conditions)
        .group_by(Department.id, Department.name)
        .order_by(func.lower(Department.name), Department.id)
    ).all()

    salary_average = session.scalar(
        select(
            func.avg(
                SalaryStructure.basic + SalaryStructure.hra + SalaryStructure.medical
            )
        )
        .join(Employee, Employee.id == SalaryStructure.employee_id)
        .where(*active_conditions)
    )

    gender_rows = session.execute(
        select(Employee.gender, func.count(Employee.id))
        .where(*active_conditions)
        .group_by(Employee.gender)
        .order_by(Employee.gender)
    ).all()

    one_year_ago = _years_before(report_to, 1)
    three_years_ago = _years_before(report_to, 3)
    tenure = session.execute(
        select(
            func.coalesce(
                func.sum(case((Employee.join_date > one_year_ago, 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(
                    case(
                        (
                            and_(
                                Employee.join_date <= one_year_ago,
                                Employee.join_date >= three_years_ago,
                            ),
                            1,
                        ),
                        else_=0,
                    )
                ),
                0,
            ),
            func.coalesce(
                func.sum(case((Employee.join_date < three_years_ago, 1), else_=0)),
                0,
            ),
        ).where(*active_conditions)
    ).one()

    employment_filters = []
    if department_id is not None:
        employment_filters.append(Employee.department_id == department_id)
    start_count, end_count = session.execute(
        select(
            func.coalesce(
                func.sum(case((_employment_condition(report_from), 1), else_=0)), 0
            ),
            func.coalesce(
                func.sum(case((_employment_condition(report_to), 1), else_=0)), 0
            ),
        ).where(*employment_filters)
    ).one()
    exits = (
        session.scalar(
            select(func.count(Employee.id)).where(
                Employee.exit_date.between(report_from, report_to),
                *employment_filters,
            )
        )
        or 0
    )
    average_headcount = (Decimal(start_count) + Decimal(end_count)) / Decimal(2)
    attrition = (
        (Decimal(exits) * Decimal(100) / average_headcount).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if average_headcount
        else ZERO
    )

    start_month = report_from.strftime("%Y-%m")
    end_month = report_to.strftime("%Y-%m")
    payroll_conditions = [
        PayrollRun.status == "finalized",
        PayrollRun.month >= start_month,
        PayrollRun.month <= end_month,
    ]
    if department_id is not None:
        payroll_conditions.append(Employee.department_id == department_id)
    gross_total, net_total = session.execute(
        select(
            func.coalesce(func.sum(Payslip.gross), 0),
            func.coalesce(func.sum(Payslip.net), 0),
        )
        .select_from(Payslip)
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .where(*payroll_conditions)
    ).one()

    payroll_rows = session.execute(
        select(
            Department.id,
            Department.name,
            func.coalesce(func.sum(Payslip.gross), 0),
            func.coalesce(func.sum(Payslip.net), 0),
        )
        .select_from(Payslip)
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .join(Employee, Employee.id == Payslip.employee_id)
        .join(Department, Department.id == Employee.department_id)
        .where(*payroll_conditions)
        .group_by(Department.id, Department.name)
        .order_by(func.lower(Department.name), Department.id)
    ).all()

    company_timezone = ZoneInfo(get_settings().company_timezone)
    audit_start = datetime.combine(
        report_from, time.min, tzinfo=company_timezone
    ).astimezone(UTC)
    audit_end = datetime.combine(
        report_to + timedelta(days=1), time.min, tzinfo=company_timezone
    ).astimezone(UTC)
    recent_audit = session.scalars(
        select(AuditLog)
        .where(AuditLog.created_at >= audit_start, AuditLog.created_at < audit_end)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .limit(10)
    ).all()

    return {
        "headcount": headcount,
        "attrition_ytd": float(attrition),
        "payroll_cost": {"gross": float(gross_total), "net": float(net_total)},
        "avg_salary": float(salary_average) if salary_average is not None else None,
        "headcount_by_dept": [
            {
                "department_id": item_id,
                "department": name,
                "headcount": count,
            }
            for item_id, name, count in headcount_rows
        ],
        "payroll_cost_by_dept": [
            {
                "department_id": item_id,
                "department": name,
                "gross": float(gross),
                "net": float(net),
            }
            for item_id, name, gross, net in payroll_rows
        ],
        "gender": [
            {"category": gender, "count": count} for gender, count in gender_rows
        ],
        "tenure": [
            {"category": "under_1_year", "count": tenure[0]},
            {"category": "1_to_3_years", "count": tenure[1]},
            {"category": "over_3_years", "count": tenure[2]},
        ],
        "recent_audit": recent_audit,
    }
