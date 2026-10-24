from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.models.user import Settings as CompanySettings
from app.schemas.auth import SetupRequest, SetupResponse, SetupStatusResponse
from app.services.setup_service import create_company_setup

router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusResponse)
def setup_status(session: Annotated[Session, Depends(get_db)]) -> SetupStatusResponse:
    settings = session.scalar(select(CompanySettings).where(CompanySettings.id == 1))
    return SetupStatusResponse(is_setup_done=bool(settings and settings.is_setup_done))


@router.post("", response_model=SetupResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(get_settings().setup_rate_limit)
def setup_company(
    request: Request,
    payload: SetupRequest,
    session: Annotated[Session, Depends(get_db)],
) -> SetupResponse:
    create_company_setup(session, payload)
    return SetupResponse(message="Company setup completed")
