import csv
import io
import secrets
from decimal import Decimal
from typing import Any

from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ApiError
from app.core.security import hash_password
from app.models.employee import Employee, SalaryStructure
from app.models.organization import Department, Designation
from app.models.payroll import PayrollRun, Payslip
from app.models.user import User
from app.schemas.hr import EmployeeCreate, EmployeeSelfUpdate, EmployeeUpdate
from app.services.audit_service import write_audit_log
from app.services.hr_utils import local_date, money
from app.services.transactions import commit_or_rollback

CSV_COLUMNS = [
    "employee_code",
    "first_name",
    "last_name",
    "email",
    "phone",
    "gender",
    "department",
    "designation",
    "join_date",
    "basic_salary",
]
MAX_CSV_BYTES = 2 * 1024 * 1024


def _employee_dict(
    employee: Employee, department: str, designation: str
) -> dict[str, Any]:
    return {
        "id": employee.id,
        "employee_code": employee.employee_code,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "email": employee.email,
        "phone": employee.phone,
        "address": employee.address,
        "gender": employee.gender,
        "department_id": employee.department_id,
        "department": department,
        "designation_id": employee.designation_id,
        "designation": designation,
        "join_date": employee.join_date,
        "exit_date": employee.exit_date,
        "status": employee.status,
        "created_at": employee.created_at,
    }


def _salary_dict(salary: SalaryStructure) -> dict[str, Any]:
    return {
        "employee_id": salary.employee_id,
        "basic": float(salary.basic),
        "hra": float(salary.hra),
        "medical": float(salary.medical),
        "gross": float(salary.basic + salary.hra + salary.medical),
        "effective_from": salary.effective_from,
    }


def salary_components(basic: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    normalized = money(basic)
    if normalized <= 0:
        raise ApiError(422, "INVALID_SALARY", "Basic salary must be greater than zero")
    hra = money(normalized * Decimal("0.40"))
    medical = money(normalized * Decimal("0.10"))
    return normalized, hra, medical


def _validate_references(
    session: Session, department_id: int, designation_id: int
) -> tuple[Department, Designation]:
    department = session.get(Department, department_id)
    if department is None:
        raise ApiError(404, "DEPARTMENT_NOT_FOUND", "Department was not found")
    designation = session.get(Designation, designation_id)
    if designation is None:
        raise ApiError(404, "DESIGNATION_NOT_FOUND", "Designation was not found")
    if designation.department_id not in (None, department_id):
        raise ApiError(
            422,
            "DESIGNATION_DEPARTMENT_MISMATCH",
            "Designation does not belong to the selected department",
        )
    return department, designation


def _temporary_password() -> str:
    return secrets.token_urlsafe(18)


def create_employee(
    session: Session, *, actor: User, payload: EmployeeCreate
) -> tuple[dict[str, Any], str]:
    password = _temporary_password()
    password_hash = hash_password(password)
    basic, hra, medical = salary_components(payload.basic_salary)
    try:
        with commit_or_rollback(session):
            department, designation = _validate_references(
                session, payload.department_id, payload.designation_id
            )
            duplicate = session.scalar(
                select(Employee.id).where(
                    or_(
                        Employee.employee_code == payload.employee_code,
                        func.lower(Employee.email) == str(payload.email).lower(),
                    )
                )
            )
            user_duplicate = session.scalar(
                select(User.id).where(
                    func.lower(User.email) == str(payload.email).lower()
                )
            )
            if duplicate is not None or user_duplicate is not None:
                raise ApiError(
                    409,
                    "EMPLOYEE_EXISTS",
                    "Employee code or email already exists",
                )
            employee = Employee(
                employee_code=payload.employee_code,
                first_name=payload.first_name,
                last_name=payload.last_name,
                email=str(payload.email).lower(),
                phone=payload.phone,
                address=payload.address,
                gender=payload.gender,
                department_id=payload.department_id,
                designation_id=payload.designation_id,
                join_date=payload.join_date,
                status=payload.status,
            )
            session.add(employee)
            session.flush()
            salary = SalaryStructure(
                employee_id=employee.id,
                basic=basic,
                hra=hra,
                medical=medical,
                effective_from=payload.join_date,
            )
            user = User(
                email=employee.email,
                password_hash=password_hash,
                role="employee",
                employee_id=employee.id,
                is_active=True,
                must_change_password=True,
            )
            session.add_all([salary, user])
            session.flush()
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="employees",
                entity_id=employee.id,
                after={
                    "employee_code": employee.employee_code,
                    "email": employee.email,
                    "department_id": employee.department_id,
                    "designation_id": employee.designation_id,
                    "status": employee.status,
                },
            )
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="salary_structures",
                entity_id=salary.id,
                after={
                    "employee_id": employee.id,
                    "basic": basic,
                    "hra": hra,
                    "medical": medical,
                },
            )
            write_audit_log(
                session,
                actor_id=actor.id,
                action="create",
                entity="users",
                entity_id=user.id,
                after={
                    "email": user.email,
                    "role": user.role,
                    "employee_id": user.employee_id,
                    "must_change_password": True,
                },
            )
        return _employee_dict(employee, department.name, designation.name), password
    except IntegrityError as exc:
        raise ApiError(
            409, "EMPLOYEE_EXISTS", "Employee code or email already exists"
        ) from exc


def list_employees(
    session: Session,
    *,
    search: str | None,
    department_id: int | None,
    status: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    conditions = []
    if search:
        pattern = f"%{search.strip()}%"
        conditions.append(
            or_(
                Employee.employee_code.ilike(pattern),
                Employee.email.ilike(pattern),
                Employee.first_name.ilike(pattern),
                Employee.last_name.ilike(pattern),
                func.concat(Employee.first_name, " ", Employee.last_name).ilike(
                    pattern
                ),
            )
        )
    if department_id is not None:
        conditions.append(Employee.department_id == department_id)
    if status:
        conditions.append(Employee.status == status)
    total = session.scalar(select(func.count(Employee.id)).where(*conditions)) or 0
    rows = session.execute(
        select(Employee, Department.name, Designation.name)
        .join(Department, Department.id == Employee.department_id)
        .join(Designation, Designation.id == Employee.designation_id)
        .where(*conditions)
        .order_by(Employee.employee_code, Employee.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [_employee_dict(*row) for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def _get_employee_row(session: Session, employee_id: int):
    row = session.execute(
        select(Employee, Department.name, Designation.name)
        .join(Department, Department.id == Employee.department_id)
        .join(Designation, Designation.id == Employee.designation_id)
        .where(Employee.id == employee_id)
    ).one_or_none()
    if row is None:
        raise ApiError(404, "EMPLOYEE_NOT_FOUND", "Employee was not found")
    return row


def get_employee_360(session: Session, *, employee_id: int) -> dict[str, Any]:
    employee, department, designation = _get_employee_row(session, employee_id)
    salary = session.scalar(
        select(SalaryStructure).where(SalaryStructure.employee_id == employee_id)
    )
    from app.services.attendance_service import attendance_summary_for_employee
    from app.services.leave_service import get_leave_balance

    payslips = session.execute(
        select(Payslip, PayrollRun.month)
        .join(PayrollRun, PayrollRun.id == Payslip.run_id)
        .where(Payslip.employee_id == employee_id, PayrollRun.status == "finalized")
        .order_by(PayrollRun.month.desc())
        .limit(3)
    ).all()
    return {
        "employee": _employee_dict(employee, department, designation),
        "salary": _salary_dict(salary) if salary else None,
        "attendance_summary": attendance_summary_for_employee(session, employee_id),
        "leave_balance": get_leave_balance(session, employee_id=employee_id),
        "last_payslips": [
            {
                "id": slip.id,
                "month": month,
                "gross": float(slip.gross),
                "deduction": float(slip.deduction),
                "tax": float(slip.tax),
                "net": float(slip.net),
            }
            for slip, month in payslips
        ],
    }


def update_employee(
    session: Session,
    *,
    actor: User,
    employee_id: int,
    payload: EmployeeUpdate,
) -> dict[str, Any]:
    with commit_or_rollback(session):
        employee = session.scalar(
            select(Employee).where(Employee.id == employee_id).with_for_update()
        )
        if employee is None:
            raise ApiError(404, "EMPLOYEE_NOT_FOUND", "Employee was not found")
        department_id = payload.department_id or employee.department_id
        designation_id = payload.designation_id or employee.designation_id
        department, designation = _validate_references(
            session, department_id, designation_id
        )
        before = {
            "department_id": employee.department_id,
            "designation_id": employee.designation_id,
            "status": employee.status,
            "exit_date": employee.exit_date,
        }
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(employee, field, value)
        if employee.status == "exited" and employee.exit_date is None:
            employee.exit_date = local_date()
        if employee.exit_date is not None and employee.exit_date < employee.join_date:
            raise ApiError(
                422,
                "INVALID_EXIT_DATE",
                "Exit date must not be before the employee's join date",
            )
        if employee.exit_date is not None:
            employee.status = "exited"
            linked_users = session.scalars(
                select(User).where(User.employee_id == employee.id).with_for_update()
            ).all()
            for user in linked_users:
                user.is_active = False
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="employees",
            entity_id=employee.id,
            before=before,
            after={
                "department_id": employee.department_id,
                "designation_id": employee.designation_id,
                "status": employee.status,
                "exit_date": employee.exit_date,
            },
        )
    return _employee_dict(employee, department.name, designation.name)


def update_own_contact(
    session: Session, *, actor: User, payload: EmployeeSelfUpdate
) -> dict[str, Any]:
    if actor.employee_id is None:
        raise ApiError(
            422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
        )
    with commit_or_rollback(session):
        employee = session.scalar(
            select(Employee).where(Employee.id == actor.employee_id).with_for_update()
        )
        if employee is None:
            raise ApiError(404, "EMPLOYEE_NOT_FOUND", "Employee was not found")
        before = {"phone": employee.phone, "address": employee.address}
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(employee, field, value)
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="employees",
            entity_id=employee.id,
            before=before,
            after={"phone": employee.phone, "address": employee.address},
        )
    employee, department, designation = _get_employee_row(session, actor.employee_id)
    return _employee_dict(employee, department, designation)


def get_salary(session: Session, *, employee_id: int) -> dict[str, Any]:
    salary = session.scalar(
        select(SalaryStructure).where(SalaryStructure.employee_id == employee_id)
    )
    if salary is None:
        raise ApiError(404, "SALARY_NOT_FOUND", "Salary structure was not found")
    return _salary_dict(salary)


def update_salary(
    session: Session, *, actor: User, employee_id: int, basic_value: Decimal
) -> dict[str, Any]:
    basic, hra, medical = salary_components(basic_value)
    with commit_or_rollback(session):
        salary = session.scalar(
            select(SalaryStructure)
            .where(SalaryStructure.employee_id == employee_id)
            .with_for_update()
        )
        if salary is None:
            raise ApiError(404, "SALARY_NOT_FOUND", "Salary structure was not found")
        before = {"basic": salary.basic, "hra": salary.hra, "medical": salary.medical}
        salary.basic, salary.hra, salary.medical = basic, hra, medical
        salary.effective_from = local_date()
        write_audit_log(
            session,
            actor_id=actor.id,
            action="update",
            entity="salary_structures",
            entity_id=salary.id,
            before=before,
            after={"basic": basic, "hra": hra, "medical": medical},
        )
    return _salary_dict(salary)


def _csv_safe(value: str) -> str:
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def export_employees_csv(session: Session) -> bytes:
    rows = session.execute(
        select(Employee, Department.name, Designation.name, SalaryStructure.basic)
        .join(Department, Department.id == Employee.department_id)
        .join(Designation, Designation.id == Employee.designation_id)
        .outerjoin(SalaryStructure, SalaryStructure.employee_id == Employee.id)
        .order_by(Employee.employee_code)
    ).all()
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(CSV_COLUMNS + ["status", "exit_date"])
    for employee, department, designation, basic in rows:
        writer.writerow(
            [
                _csv_safe(employee.employee_code),
                _csv_safe(employee.first_name),
                _csv_safe(employee.last_name),
                _csv_safe(employee.email),
                _csv_safe(employee.phone),
                employee.gender,
                _csv_safe(department),
                _csv_safe(designation),
                employee.join_date.isoformat(),
                str(basic) if basic is not None else "",
                employee.status,
                employee.exit_date.isoformat() if employee.exit_date else "",
            ]
        )
    return output.getvalue().encode("utf-8-sig")


def import_employees_csv(
    session: Session, *, actor: User, content: bytes, dry_run: bool
) -> dict[str, Any]:
    if len(content) > MAX_CSV_BYTES:
        raise ApiError(422, "CSV_TOO_LARGE", "CSV file exceeds the 2 MB limit")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ApiError(422, "CSV_INVALID_ENCODING", "CSV must be valid UTF-8") from exc
    try:
        reader = csv.DictReader(io.StringIO(text))
    except csv.Error as exc:
        raise ApiError(422, "CSV_INVALID", "CSV file could not be parsed") from exc
    if reader.fieldnames != CSV_COLUMNS:
        raise ApiError(
            422, "CSV_INVALID_HEADERS", "CSV headers do not match the contract"
        )

    departments = {
        name.lower(): item_id
        for item_id, name in session.execute(select(Department.id, Department.name))
    }
    designations = {
        name.lower(): (item_id, department_id)
        for item_id, name, department_id in session.execute(
            select(Designation.id, Designation.name, Designation.department_id)
        )
    }
    seen_codes: set[str] = set()
    seen_emails: set[str] = set()
    valid: list[tuple[int, EmployeeCreate]] = []
    errors: list[dict[str, Any]] = []
    try:
        rows = list(reader)
    except csv.Error as exc:
        raise ApiError(422, "CSV_INVALID", "CSV file could not be parsed") from exc
    for row_number, row in enumerate(rows, start=2):
        row_errors = []
        department_name = (row.get("department") or "").strip().lower()
        designation_name = (row.get("designation") or "").strip().lower()
        department_id = departments.get(department_name)
        designation_info = designations.get(designation_name)
        if department_id is None:
            row_errors.append(("department", "Department was not found"))
        if designation_info is None:
            row_errors.append(("designation", "Designation was not found"))
        code = (row.get("employee_code") or "").strip()
        email = (row.get("email") or "").strip().lower()
        if code in seen_codes:
            row_errors.append(("employee_code", "Duplicate employee code in file"))
        if email in seen_emails:
            row_errors.append(("email", "Duplicate email in file"))
        seen_codes.add(code)
        seen_emails.add(email)
        if row_errors:
            errors.extend(
                {"row": row_number, "field": field, "reason": reason}
                for field, reason in row_errors
            )
            continue
        try:
            payload = EmployeeCreate.model_validate(
                {
                    "employee_code": row.get("employee_code"),
                    "first_name": row.get("first_name"),
                    "last_name": row.get("last_name"),
                    "email": row.get("email"),
                    "phone": row.get("phone"),
                    "gender": row.get("gender"),
                    "department_id": department_id,
                    "designation_id": designation_info[0],
                    "join_date": row.get("join_date"),
                    "basic_salary": row.get("basic_salary"),
                    "status": "probation",
                }
            )
            _validate_references(session, payload.department_id, payload.designation_id)
            duplicate = session.scalar(
                select(Employee.id).where(
                    or_(
                        Employee.employee_code == payload.employee_code,
                        func.lower(Employee.email) == str(payload.email).lower(),
                    )
                )
            )
            user_duplicate = session.scalar(
                select(User.id).where(
                    func.lower(User.email) == str(payload.email).lower()
                )
            )
            if duplicate is not None or user_duplicate is not None:
                raise ApiError(409, "EMPLOYEE_EXISTS", "Employee already exists")
            valid.append((row_number, payload))
        except (ValidationError, ApiError) as exc:
            if isinstance(exc, ValidationError):
                for item in exc.errors():
                    errors.append(
                        {
                            "row": row_number,
                            "field": str(item["loc"][-1]),
                            "reason": item["msg"],
                        }
                    )
            else:
                errors.append(
                    {"row": row_number, "field": "row", "reason": exc.message}
                )

    valid_rows = [item.model_dump(mode="json") for _, item in valid]
    created = []
    if not dry_run:
        for row_number, payload in valid:
            try:
                employee, password = create_employee(
                    session, actor=actor, payload=payload
                )
                created.append({"employee": employee, "temp_password": password})
            except ApiError as exc:
                errors.append(
                    {"row": row_number, "field": "row", "reason": exc.message}
                )
    return {"valid_rows": valid_rows, "errors": errors, "created": created}
