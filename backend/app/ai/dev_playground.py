"""Explicit local playground. Never import or mount this in the production app."""

import os
import secrets
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import Field
from starlette.middleware.trustedhost import TrustedHostMiddleware

from .config import Settings
from .dev_adapters import CURRENT_RECORD, IDENTITIES, DemoBackend, DemoOperations
from .dev_data import DEPARTMENTS, DemoData
from .exceptions import AIError
from .guard import AIService
from .providers import ProviderManager
from .schemas import ChatRequest, KPIContext, LeaveRequest, Schema, SummaryRequest

URL = "http://127.0.0.1:8765"
ASSETS = Path(__file__).parent / "playground"


class DashboardRequest(Schema):
    context: KPIContext = Field(default_factory=KPIContext)
    scenario: Literal["normal", "empty", "insufficient"] = "normal"


def load_dev_environment():
    """Only the explicit playground entry point loads local environment files."""
    from dotenv import load_dotenv

    selected = os.environ.get("AI_PLAYGROUND_ENV_FILE")
    backend = Path(__file__).resolve().parents[2]
    if selected:
        path = Path(selected).expanduser().resolve()
        if not path.is_file():
            raise RuntimeError("Selected playground env file does not exist.")
        load_dotenv(path, override=False)
    else:
        for path in (backend / ".env", backend.parent / ".env"):
            if path.is_file():
                load_dotenv(path, override=False)


def create_app(*, settings=None, manager=None, today=None):
    if os.environ.get("AI_PLAYGROUND") != "1":
        raise RuntimeError("Playground disabled. Set AI_PLAYGROUND=1 explicitly.")
    settings = settings or Settings()
    manager = manager if manager is not None else ProviderManager.configured(settings)
    data = DemoData(today or datetime.now(ZoneInfo(settings.ai_timezone)).date())
    backend = DemoBackend(data)
    operations = DemoOperations()
    token = secrets.token_urlsafe(32)
    app = FastAPI(
        title="HCM Lite — Local AI Playground",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1"])
    app.state.manager = manager
    app.state.operations = operations

    @app.middleware("http")
    async def local_only(request: Request, call_next):
        if not request.client or request.client.host != "127.0.0.1":
            return JSONResponse(
                {"detail": {"code": "LOCAL_ONLY", "message": "Loopback access only."}},
                403,
            )
        if request.headers.get("origin") not in {None, URL}:
            return JSONResponse(
                {
                    "detail": {
                        "code": "LOCAL_ONLY",
                        "message": "Only the local playground origin is allowed.",
                    }
                },
                403,
            )
        if request.method == "POST" and not secrets.compare_digest(
            request.headers.get("x-playground-token", ""), token
        ):
            return JSONResponse(
                {
                    "detail": {
                        "code": "LOCAL_ONLY",
                        "message": "Reload the playground page before sending requests.",
                    }
                },
                403,
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request, exc):
        return JSONResponse(
            {
                "detail": {
                    "code": "AI_INVALID_REQUEST",
                    "message": "Check the request fields and limits.",
                }
            },
            422,
        )

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return HTMLResponse(
            (ASSETS / "index.html").read_text().replace("__PLAYGROUND_TOKEN__", token)
        )

    @app.get("/assets/{name}")
    async def asset(name: str):
        if name not in {"style.css", "app.js"}:
            raise AIError("NOT_FOUND", "Asset not found.", 404)
        return FileResponse(ASSETS / name)

    @app.get("/dev/status")
    async def status():
        return {
            "demo": True,
            "python": sys.version.split()[0],
            "today": data.today.isoformat(),
            "departments": list(DEPARTMENTS),
            "providers": [
                {"name": p.name, "configured": True} for p in manager.providers
            ],
            "roles": {
                r: {
                    "name": next(
                        e.name for e in data.employees if e.id == u.employee_id
                    ),
                    "employee_code": f"DEMO-{u.employee_id:03d}",
                }
                for r, u in IDENTITIES.items()
            },
            "note": "Configured does not mean live-verified. Only HR data is simulated.",
        }

    def user(request):
        role = request.headers.get("x-demo-role", "")
        if role not in IDENTITIES:
            raise AIError("AI_FORBIDDEN", "Choose Admin, HR or Employee.", 403)
        return IDENTITIES[role].model_copy()

    async def run(feature, payload, request, service_backend=backend):
        identity = user(request)
        record = {}
        handle = CURRENT_RECORD.set(record)
        try:
            if not manager.providers:
                raise AIError(
                    "AI_CONFIGURATION",
                    "No real provider is configured. Set GEMINI_API_KEY and GEMINI_MODEL in your local .env.",
                )
            service = AIService(
                service_backend,
                operations,
                manager,
                settings,
                clock=lambda: data.today,
            )
            result = await service.run(feature, payload, identity)
            return {
                "result": result.model_dump(mode="json"),
                "meta": record,
                "demo": True,
            }
        except AIError as caught:
            detail, status_code = caught.detail, caught.status_code
            attempts = record.get("attempts", [])
            if attempts and attempts[-1].get("http_status") in {401, 403}:
                permission_error = AIError(
                    "AI_PROVIDER_AUTH",
                    "The provider denied access (HTTP 401/403). Check the Gemini key, model permissions and account access.",
                )
                detail, status_code = (
                    permission_error.detail,
                    permission_error.status_code,
                )
            return JSONResponse(
                {"detail": detail, "meta": record, "demo": True}, status_code
            )
        finally:
            CURRENT_RECORD.reset(handle)

    @app.post("/dev/chat")
    async def chat(payload: ChatRequest, request: Request):
        return await run("chat", payload, request)

    @app.post("/dev/smart-leave")
    async def leave(payload: LeaveRequest, request: Request):
        return await run("smart_leave", payload, request)

    @app.post("/dev/dashboard")
    async def dashboard(payload: DashboardRequest, request: Request):
        return await DemoBackend(data, payload.scenario).dashboard(
            user(request), payload.context
        )

    @app.post("/dev/summary")
    async def summary(payload: DashboardRequest, request: Request):
        selected = DemoBackend(data, payload.scenario)
        kpis = await selected.dashboard(user(request), payload.context)
        return await run("summary", SummaryRequest(kpis=kpis), request, selected)

    return app


def main():
    load_dev_environment()
    if os.environ.get("AI_PLAYGROUND") != "1":
        raise SystemExit("Set AI_PLAYGROUND=1 to enable the local demo playground.")
    try:
        settings = Settings()
        app = create_app(settings=settings)
    except Exception:  # noqa: BLE001 -- never print settings validation inputs containing secrets
        raise SystemExit(
            "Playground configuration is invalid. Check provider names, model settings and HTTPS URL; no secret values were printed."
        ) from None
    names = (
        ", ".join(p.name for p in app.state.manager.providers)
        or "Unavailable — add provider keys/model in local .env"
    )
    print(
        f"HCM Lite — DEMO DATA ONLY\n{URL}\nPython {sys.version.split()[0]}\nConfigured providers (not live-verified): {names}"
    )
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8765, proxy_headers=False, access_log=False)


if __name__ == "__main__":
    main()
