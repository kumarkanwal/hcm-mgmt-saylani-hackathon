from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_role
from app.core.exceptions import ApiError
from app.models.user import User
from app.schemas.admin import AuditLogListResponse
from app.services.audit_service import list_audit_logs

router = APIRouter(prefix="/api/audit-logs", tags=["audit"])
Admin = Annotated[User, Depends(require_role("admin"))]
Database = Annotated[Session, Depends(get_db)]
EntityFilter = Annotated[str | None, Query(min_length=1, max_length=80)]
ActorFilter = Annotated[int | None, Query(ge=1)]
FromDate = Annotated[date | None, Query(alias="from")]
ToDate = Annotated[date | None, Query(alias="to")]


@router.get("", response_model=AuditLogListResponse)
def read_audit_logs(
    _: Admin,
    session: Database,
    entity: EntityFilter = None,
    actor_id: ActorFilter = None,
    from_date: FromDate = None,
    to_date: ToDate = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> dict:
    if from_date is not None and to_date is not None and from_date > to_date:
        raise ApiError(422, "INVALID_DATE_RANGE", "from must not be after to")
    return list_audit_logs(
        session,
        entity=entity,
        actor_id=actor_id,
        from_date=from_date,
        to_date=to_date,
        page=page,
        page_size=page_size,
    )
