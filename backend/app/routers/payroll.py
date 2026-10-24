from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.hr import (
    PayrollRunCreate,
    PayrollRunListResponse,
    PayrollRunResponse,
    PayslipListResponse,
)
from app.services.payroll_service import (
    create_payroll_run,
    finalize_payroll,
    generate_payslip_pdf,
    get_payroll_run,
    list_my_payslips,
    list_payroll_runs,
    recalculate_payroll,
)

router = APIRouter(prefix="/api", tags=["payroll"])
Database = Annotated[Session, Depends(get_db)]
HR = Annotated[User, Depends(require_role("hr"))]
Admin = Annotated[User, Depends(require_role("admin"))]
Management = Annotated[User, Depends(require_role("admin", "hr"))]
Employee = Annotated[User, Depends(require_role("employee"))]
AnyRole = Annotated[User, Depends(require_role("admin", "hr", "employee"))]


@router.post("/payroll/runs", response_model=PayrollRunResponse)
def write_payroll_run(payload: PayrollRunCreate, actor: HR, session: Database) -> dict:
    return create_payroll_run(session, actor=actor, month=payload.month)


@router.get("/payroll/runs", response_model=PayrollRunListResponse)
def read_payroll_runs(
    _: Management,
    session: Database,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_payroll_runs(session, page=page, page_size=page_size)


@router.get("/payroll/runs/{run_id}", response_model=PayrollRunResponse)
def read_payroll_run(run_id: int, _: Management, session: Database) -> dict:
    return get_payroll_run(session, run_id=run_id)


@router.post("/payroll/runs/{run_id}/recalculate", response_model=PayrollRunResponse)
def rebuild_payroll(run_id: int, actor: HR, session: Database) -> dict:
    return recalculate_payroll(session, actor=actor, run_id=run_id)


@router.post("/payroll/runs/{run_id}/finalize", response_model=PayrollRunResponse)
def lock_payroll(run_id: int, actor: Admin, session: Database) -> dict:
    return finalize_payroll(session, actor=actor, run_id=run_id)


@router.get("/payslips/me", response_model=PayslipListResponse)
def read_my_payslips(
    user: Employee,
    session: Database,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_my_payslips(session, user=user, page=page, page_size=page_size)


@router.get("/payslips/{payslip_id}/pdf")
def read_payslip_pdf(payslip_id: int, user: AnyRole, session: Database) -> Response:
    content, filename = generate_payslip_pdf(session, user=user, payslip_id=payslip_id)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
