from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.exceptions import ApiError
from app.models.user import User
from app.schemas.hr import (
    DecisionRequest,
    LeaveBalanceItem,
    LeaveCreate,
    LeaveResponse,
    PaginatedLeaves,
)
from app.services.leave_service import (
    cancel_leave,
    create_leave,
    decide_leave,
    get_leave_balance,
    list_leaves,
)

router = APIRouter(prefix="/api/leaves", tags=["leave"])
Database = Annotated[Session, Depends(get_db)]
AnyRole = Annotated[User, Depends(require_role("admin", "hr", "employee"))]
Employee = Annotated[User, Depends(require_role("employee"))]
EmployeeOrHR = Annotated[User, Depends(require_role("employee", "hr"))]
HR = Annotated[User, Depends(require_role("hr"))]
FromDate = Annotated[date | None, Query(alias="from")]
ToDate = Annotated[date | None, Query(alias="to")]


@router.get("/balance", response_model=list[LeaveBalanceItem])
def read_balance(
    user: AnyRole,
    session: Database,
    employee_id: int | None = Query(default=None, ge=1),
) -> list[dict]:
    if user.role == "employee":
        if user.employee_id is None:
            raise ApiError(
                422, "EMPLOYEE_LINK_REQUIRED", "Account is not linked to an employee"
            )
        target = user.employee_id
    else:
        if employee_id is None:
            raise ApiError(422, "EMPLOYEE_ID_REQUIRED", "employee_id is required")
        target = employee_id
    return get_leave_balance(session, employee_id=target)


@router.post("", response_model=LeaveResponse)
def write_leave(payload: LeaveCreate, user: EmployeeOrHR, session: Database) -> dict:
    return create_leave(session, user=user, payload=payload)


@router.post("/{leave_id}/cancel", response_model=LeaveResponse)
def cancel_own_leave(leave_id: int, user: Employee, session: Database) -> dict:
    return cancel_leave(session, user=user, leave_id=leave_id)


@router.get("/me", response_model=PaginatedLeaves)
def read_my_leaves(
    user: Employee,
    session: Database,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_leaves(
        session,
        user=user,
        own_only=True,
        status=None,
        department_id=None,
        from_date=None,
        to_date=None,
        page=page,
        page_size=page_size,
    )


@router.get("", response_model=PaginatedLeaves)
def read_leaves(
    user: Annotated[User, Depends(require_role("admin", "hr"))],
    session: Database,
    status_filter: Literal["pending", "approved", "rejected", "cancelled"]
    | None = Query(default=None, alias="status"),
    department_id: int | None = Query(default=None, ge=1),
    from_date: FromDate = None,
    to_date: ToDate = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_leaves(
        session,
        user=user,
        own_only=False,
        status=status_filter,
        department_id=department_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.patch("/{leave_id}/decision", response_model=LeaveResponse)
def review_leave(
    leave_id: int, payload: DecisionRequest, reviewer: HR, session: Database
) -> dict:
    return decide_leave(session, reviewer=reviewer, leave_id=leave_id, payload=payload)
