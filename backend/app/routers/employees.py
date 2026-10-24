from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_employee_scope, require_role
from app.models.user import User
from app.schemas.hr import (
    CSVImportResponse,
    Employee360,
    EmployeeCreate,
    EmployeeCreateResponse,
    EmployeeListResponse,
    EmployeeSelfUpdate,
    EmployeeSummary,
    EmployeeUpdate,
    SalaryResponse,
    SalaryUpdate,
)
from app.services.employee_service import (
    create_employee,
    export_employees_csv,
    get_employee_360,
    get_salary,
    import_employees_csv,
    list_employees,
    update_employee,
    update_own_contact,
    update_salary,
)

router = APIRouter(prefix="/api/employees", tags=["employees"])
Database = Annotated[Session, Depends(get_db)]
AdminOrHR = Annotated[User, Depends(require_role("admin", "hr"))]
HR = Annotated[User, Depends(require_role("hr"))]
AnyRole = Annotated[User, Depends(require_role("admin", "hr", "employee"))]


@router.get("", response_model=EmployeeListResponse)
def read_employees(
    _: AdminOrHR,
    session: Database,
    search: str | None = Query(default=None, max_length=255),
    department_id: int | None = Query(default=None, ge=1),
    status_filter: Literal["probation", "active", "exited"] | None = Query(
        default=None, alias="status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_employees(
        session,
        search=search,
        department_id=department_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.post(
    "", response_model=EmployeeCreateResponse, status_code=status.HTTP_201_CREATED
)
def write_employee(
    payload: EmployeeCreate, actor: HR, session: Database
) -> EmployeeCreateResponse:
    employee, temporary_password = create_employee(
        session, actor=actor, payload=payload
    )
    return EmployeeCreateResponse(
        employee=EmployeeSummary.model_validate(employee),
        temp_password=temporary_password,
    )


@router.patch("/me", response_model=EmployeeSummary)
def revise_own_contact(
    payload: EmployeeSelfUpdate,
    actor: Annotated[User, Depends(require_role("employee"))],
    session: Database,
) -> dict:
    return update_own_contact(session, actor=actor, payload=payload)


@router.post("/import", response_model=CSVImportResponse)
async def import_employees(
    actor: HR,
    session: Database,
    file: Annotated[UploadFile, File()],
    dry_run: bool = Query(default=True),
) -> dict:
    content = await file.read(2 * 1024 * 1024 + 1)
    return import_employees_csv(session, actor=actor, content=content, dry_run=dry_run)


@router.get("/export")
def export_employees(_: HR, session: Database) -> Response:
    return Response(
        content=export_employees_csv(session),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="employees.csv"'},
    )


@router.get("/{employee_id}", response_model=Employee360)
def read_employee(employee_id: int, user: AnyRole, session: Database) -> dict:
    require_employee_scope(user, employee_id)
    return get_employee_360(session, employee_id=employee_id)


@router.patch("/{employee_id}", response_model=EmployeeSummary)
def revise_employee(
    employee_id: int, payload: EmployeeUpdate, actor: HR, session: Database
) -> dict:
    return update_employee(
        session, actor=actor, employee_id=employee_id, payload=payload
    )


@router.get("/{employee_id}/salary", response_model=SalaryResponse)
def read_salary(employee_id: int, _: AdminOrHR, session: Database) -> dict:
    return get_salary(session, employee_id=employee_id)


@router.put("/{employee_id}/salary", response_model=SalaryResponse)
def revise_salary(
    employee_id: int, payload: SalaryUpdate, actor: HR, session: Database
) -> dict:
    return update_salary(
        session, actor=actor, employee_id=employee_id, basic_value=payload.basic
    )
