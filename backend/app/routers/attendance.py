from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.hr import (
    AttendanceBoardItem,
    AttendanceCalendarResponse,
    AttendanceCorrectionCreate,
    AttendanceCorrectionResponse,
    AttendanceListResponse,
    AttendanceResponse,
    CheckInRequest,
    DecisionRequest,
    PaginatedCorrections,
)
from app.services.attendance_service import (
    attendance_board,
    attendance_calendar,
    attendance_today,
    check_in,
    check_out,
    decide_correction,
    list_attendance,
    list_corrections,
    request_correction,
)

router = APIRouter(prefix="/api/attendance", tags=["attendance"])
Database = Annotated[Session, Depends(get_db)]
EmployeeOrHR = Annotated[User, Depends(require_role("employee", "hr"))]
Management = Annotated[User, Depends(require_role("admin", "hr"))]
Employee = Annotated[User, Depends(require_role("employee"))]
BoardDate = Annotated[date, Query(alias="date")]
EmployeeId = Annotated[int, Query(ge=1)]
FromDate = Annotated[date, Query(alias="from")]
ToDate = Annotated[date, Query(alias="to")]


@router.post("/check-in", response_model=AttendanceResponse)
def create_check_in(
    payload: CheckInRequest, user: EmployeeOrHR, session: Database
) -> dict:
    return check_in(session, user=user, payload=payload)


@router.post("/check-out", response_model=AttendanceResponse)
def create_check_out(user: EmployeeOrHR, session: Database) -> dict:
    return check_out(session, user=user)


@router.get("/today", response_model=AttendanceResponse | None)
def read_today(user: EmployeeOrHR, session: Database) -> dict | None:
    return attendance_today(session, user=user)


@router.get("/me", response_model=AttendanceCalendarResponse)
def read_my_attendance(
    user: Employee,
    session: Database,
    month: str = Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$"),
) -> dict:
    return attendance_calendar(session, user=user, month=month)


@router.get("/board", response_model=list[AttendanceBoardItem])
def read_board(
    _: Management,
    session: Database,
    day: BoardDate,
    department_id: int | None = Query(default=None, ge=1),
) -> list[dict]:
    return attendance_board(session, day=day, department_id=department_id)


@router.get("", response_model=AttendanceListResponse)
def read_attendance(
    _: Management,
    session: Database,
    employee_id: EmployeeId,
    from_date: FromDate,
    to_date: ToDate,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_attendance(
        session,
        employee_id=employee_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )


@router.post("/corrections", response_model=AttendanceCorrectionResponse)
def create_correction(
    payload: AttendanceCorrectionCreate, user: Employee, session: Database
) -> dict:
    return request_correction(session, user=user, payload=payload)


@router.get("/corrections", response_model=PaginatedCorrections)
def read_corrections(
    user: Annotated[User, Depends(require_role("admin", "hr", "employee"))],
    session: Database,
    status_filter: Literal["pending", "approved", "rejected"] | None = Query(
        default=None, alias="status"
    ),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    return list_corrections(
        session,
        user=user,
        status=status_filter,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/corrections/{correction_id}", response_model=AttendanceCorrectionResponse
)
def review_correction(
    correction_id: int,
    payload: DecisionRequest,
    reviewer: Annotated[User, Depends(require_role("hr"))],
    session: Database,
) -> dict:
    return decide_correction(
        session, reviewer=reviewer, correction_id=correction_id, payload=payload
    )
