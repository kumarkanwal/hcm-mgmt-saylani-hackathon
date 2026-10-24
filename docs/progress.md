# HCM Lite progress

## Phase 0 — environment and repository preparation (2026-10-25)

- Added an isolated PostgreSQL 16 development service (`hcm-lite-postgres`) on loopback port 5433 with health check and persistent volume `hcm_lite_dev_data`.
- Removed host publication of PostgreSQL from the existing production Compose config and added database health gating for the backend.
- Added the Python 3.12 / uv FastAPI foundation, SQLAlchemy and Alembic configuration, PostgreSQL driver, environment settings, and `/api/health` smoke endpoint.
- Verified both Compose configurations, database health and `SELECT 1` from the container and backend host environment, dependency compatibility, and FastAPI health response.
- No business models, migrations, or feature endpoints have been implemented. The first schema migration remains Phase 1 work governed by `MODELS.md`.
