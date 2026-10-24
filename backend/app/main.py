import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.core.exceptions import ApiError
from app.core.rate_limit import limiter
from app.routers import audit, auth, dashboard, organization, setup, users
from app.services.setup_service import bootstrap_admin_from_environment

logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if settings.admin_email or settings.admin_password:
        with SessionLocal() as session:
            bootstrap_admin_from_environment(session, settings)
    yield


app = FastAPI(title="HCM Lite API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message}},
    )


@app.exception_handler(ApiError)
async def api_error_handler(_: Request, exc: ApiError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    _: Request, __: RequestValidationError
) -> JSONResponse:
    return error_response(422, "VALIDATION_ERROR", "Request validation failed")


@app.exception_handler(StarletteHTTPException)
async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    known = {
        400: ("BAD_REQUEST", "The request could not be processed"),
        401: ("UNAUTHENTICATED", "Authentication is required"),
        403: ("FORBIDDEN", "You do not have permission to perform this action"),
        404: ("NOT_FOUND", "The requested resource was not found"),
        409: ("CONFLICT", "The request conflicts with existing data"),
        422: ("VALIDATION_ERROR", "Request validation failed"),
    }
    code, message = known.get(
        exc.status_code, ("HTTP_ERROR", "The request could not be completed")
    )
    if isinstance(exc.detail, dict) and {"code", "message"}.issubset(exc.detail):
        code, message = exc.detail["code"], exc.detail["message"]
    return error_response(exc.status_code, code, message)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_error_handler(_: Request, __: RateLimitExceeded) -> JSONResponse:
    return error_response(429, "RATE_LIMITED", "Too many requests; try again later")


@app.exception_handler(IntegrityError)
async def integrity_error_handler(_: Request, __: IntegrityError) -> JSONResponse:
    return error_response(409, "CONFLICT", "The request conflicts with existing data")


@app.exception_handler(SQLAlchemyError)
async def database_error_handler(_: Request, __: SQLAlchemyError) -> JSONResponse:
    logger.error("Database operation failed")
    return error_response(500, "INTERNAL_ERROR", "The request could not be completed")


@app.exception_handler(Exception)
async def unexpected_error_handler(_: Request, __: Exception) -> JSONResponse:
    logger.error("Unhandled API error")
    return error_response(500, "INTERNAL_ERROR", "The request could not be completed")


app.include_router(setup.router)
app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(dashboard.router)


@app.get("/api/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}
