# HCM Lite backend foundation

Python 3.12 and uv manage this FastAPI service. Copy `.env.example` to `.env`
and set local secrets before running the app.

```powershell
uv sync --python 3.12
uv run uvicorn app.main:app --reload
```

The `/api/health` endpoint is the Phase 0 smoke-check endpoint. Database
schema and business endpoints are intentionally not part of this foundation.
