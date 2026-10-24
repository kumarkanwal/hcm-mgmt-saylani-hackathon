from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.models.user import User
from app.schemas.admin import AdminDashboardResponse
from app.services.dashboard_service import get_admin_dashboard

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])
Admin = Annotated[User, Depends(require_role("admin"))]
Database = Annotated[Session, Depends(get_db)]
FromDate = Annotated[date | None, Query(alias="from")]
ToDate = Annotated[date | None, Query(alias="to")]


@router.get("/admin", response_model=AdminDashboardResponse)
def read_admin_dashboard(
    _: Admin,
    session: Database,
    from_date: FromDate = None,
    to_date: ToDate = None,
    department_id: int | None = Query(default=None, ge=1),
) -> dict:
    return get_admin_dashboard(
        session,
        from_date=from_date,
        to_date=to_date,
        department_id=department_id,
    )
