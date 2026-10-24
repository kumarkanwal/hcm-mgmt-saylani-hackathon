from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.admin import (
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentWrite,
    DesignationCreate,
    DesignationListResponse,
    DesignationResponse,
    HolidayCreate,
    HolidayListResponse,
    HolidayResponse,
    LeaveTypeCreate,
    LeaveTypeListResponse,
    LeaveTypeResponse,
    LeaveTypeUpdate,
    MessageResponse,
    SettingsResponse,
    SettingsUpdate,
)
from app.services.admin_service import (
    create_department,
    create_designation,
    create_holiday,
    create_leave_type,
    delete_department,
    delete_holiday,
    get_company_settings,
    list_departments,
    list_designations,
    list_holidays,
    list_leave_types,
    update_company_settings,
    update_department,
    update_leave_type,
)

router = APIRouter(prefix="/api", tags=["organization"])
Admin = Annotated[User, Depends(require_role("admin"))]
AdminOrHR = Annotated[User, Depends(require_role("admin", "hr"))]
AnyRole = Annotated[User, Depends(require_role("admin", "hr", "employee"))]
Database = Annotated[Session, Depends(get_db)]
Page = Annotated[int, Query(ge=1)]
PageSize = Annotated[int, Query(ge=1, le=100)]


@router.get("/settings", response_model=SettingsResponse)
def read_settings(_: AdminOrHR, session: Database) -> dict:
    return get_company_settings(session)


@router.put("/settings", response_model=SettingsResponse)
def write_settings(payload: SettingsUpdate, actor: Admin, session: Database) -> dict:
    return update_company_settings(session, actor=actor, payload=payload)


@router.get("/departments", response_model=DepartmentListResponse)
def read_departments(
    _: AdminOrHR, session: Database, page: Page = 1, page_size: PageSize = 20
) -> dict:
    return list_departments(session, page=page, page_size=page_size)


@router.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_department(
    payload: DepartmentWrite, actor: Admin, session: Database
) -> DepartmentResponse:
    return DepartmentResponse.model_validate(
        create_department(session, actor=actor, payload=payload), from_attributes=True
    )


@router.put("/departments/{department_id}", response_model=DepartmentResponse)
def rename_department(
    department_id: int, payload: DepartmentWrite, actor: Admin, session: Database
) -> DepartmentResponse:
    return DepartmentResponse.model_validate(
        update_department(
            session, actor=actor, department_id=department_id, payload=payload
        ),
        from_attributes=True,
    )


@router.delete("/departments/{department_id}", response_model=MessageResponse)
def remove_department(
    department_id: int, actor: Admin, session: Database
) -> MessageResponse:
    delete_department(session, actor=actor, department_id=department_id)
    return MessageResponse(message="Department deleted")


@router.get("/designations", response_model=DesignationListResponse)
def read_designations(
    _: AdminOrHR, session: Database, page: Page = 1, page_size: PageSize = 20
) -> dict:
    return list_designations(session, page=page, page_size=page_size)


@router.post(
    "/designations",
    response_model=DesignationResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_designation(
    payload: DesignationCreate, actor: Admin, session: Database
) -> dict:
    return create_designation(session, actor=actor, payload=payload)


@router.get("/leave-types", response_model=LeaveTypeListResponse)
def read_leave_types(
    _: AnyRole, session: Database, page: Page = 1, page_size: PageSize = 20
) -> dict:
    return list_leave_types(session, page=page, page_size=page_size)


@router.post(
    "/leave-types",
    response_model=LeaveTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_leave_type(
    payload: LeaveTypeCreate, actor: Admin, session: Database
) -> LeaveTypeResponse:
    return LeaveTypeResponse.model_validate(
        create_leave_type(session, actor=actor, payload=payload), from_attributes=True
    )


@router.put("/leave-types/{leave_type_id}", response_model=LeaveTypeResponse)
def revise_leave_type(
    leave_type_id: int, payload: LeaveTypeUpdate, actor: Admin, session: Database
) -> LeaveTypeResponse:
    return LeaveTypeResponse.model_validate(
        update_leave_type(
            session, actor=actor, leave_type_id=leave_type_id, payload=payload
        ),
        from_attributes=True,
    )


@router.get("/holidays", response_model=HolidayListResponse)
def read_holidays(
    _: AnyRole, session: Database, page: Page = 1, page_size: PageSize = 20
) -> dict:
    return list_holidays(session, page=page, page_size=page_size)


@router.post(
    "/holidays",
    response_model=HolidayResponse,
    status_code=status.HTTP_201_CREATED,
)
def write_holiday(
    payload: HolidayCreate, actor: Admin, session: Database
) -> HolidayResponse:
    return HolidayResponse.model_validate(
        create_holiday(session, actor=actor, payload=payload), from_attributes=True
    )


@router.delete("/holidays/{holiday_id}", response_model=MessageResponse)
def remove_holiday(holiday_id: int, actor: Admin, session: Database) -> MessageResponse:
    delete_holiday(session, actor=actor, holiday_id=holiday_id)
    return MessageResponse(message="Holiday deleted")
