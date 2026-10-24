# HCM Lite backend foundation

Python 3.12 and uv manage this FastAPI service. Copy `.env.example` to `.env`
and set local secrets before running the app.

```powershell
uv sync --python 3.12
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

The application connects with `DATABASE_URL`, which should use the restricted
runtime database role. Alembic uses `MIGRATION_DATABASE_URL`, which should use
the HCM database owner. In Compose deployments, run migrations with:

```bash
docker compose --profile migration run --rm migrate
```

The `/api/health` endpoint is the deployment smoke check. Phase 1A also
provides the complete schema, first-run setup, and authentication endpoints;
see `../docs/progress.md` for the verified implementation status.
