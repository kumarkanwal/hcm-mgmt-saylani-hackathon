# HCM Lite progress

## Phase 0 — environment and repository preparation (2026-10-25)

- Added an isolated PostgreSQL 16 development service (`hcm-lite-postgres`) on loopback port 5433 with health check and persistent volume `hcm_lite_dev_data`.
- Removed host publication of PostgreSQL from the existing production Compose config and added database health gating for the backend.
- Added the Python 3.12 / uv FastAPI foundation, SQLAlchemy and Alembic configuration, PostgreSQL driver, environment settings, and `/api/health` smoke endpoint.
- Verified both Compose configurations, database health and `SELECT 1` from the container and backend host environment, dependency compatibility, and FastAPI health response.
- No business models, migrations, or feature endpoints have been implemented. The first schema migration remains Phase 1 work governed by `MODELS.md`.

## Phase 1A — database, authentication and security (2026-10-25)

- Added typed SQLAlchemy 2.0 mappings for all 17 tables in `MODELS.md` and the complete PostgreSQL initial migration (`a49dab4c246b`).
- Added company setup, environment Admin bootstrap, login, current-user and password-change services and routes.
- Added bcrypt password handling, signed eight-hour JWTs, active-user database checks, central forced-password-change and role checks, employee ownership helper, structured errors, exact-origin CORS, and login/setup rate limits.
- Added atomic setup with a PostgreSQL advisory transaction lock, default settings and leave types, insert-only audit behavior, and safe system actor handling.
- Setup audits the settings row, first Admin, and each of the four required default leave types in the same transaction.
- Split the runtime database role from the migration owner, limited backend/frontend Compose environment exposure, and disabled runtime updates/deletes of audit rows.
- Recovery verification: 21 pytest tests passed against isolated `hcm_lite_test` (one upstream Starlette/httpx deprecation warning); Ruff format and lint checks passed for all 36 backend Python files; Python compilation and `alembic check` passed.
- A brand-new disposable database migrated from base to `a49dab4c246b`, contained all 17 contract tables plus `alembic_version`, and was removed after verification. The working HCM database remains empty and at the same head revision.
- A live disposable-database flow using the restricted runtime role passed health, setup, Admin login, nullable Admin `employee_id` JWT handling, and `/auth/me`; setup plus login produced seven audit rows. The runtime role was denied schema creation and audit-log update/delete, as designed.
- Implemented endpoints: `GET /api/setup/status`, `POST /api/setup`, `POST /api/auth/login`, `POST /api/auth/change-password`, and `GET /api/auth/me`.
- Remaining for Phase 1B: organization management, HR account-management endpoints, and audit-log viewing. No employee, attendance, leave, payroll, dashboard, or AI endpoints were added.
- Note: the pre-existing root `README.md` migration command predates the restricted runtime role; use the migration profile documented in `backend/README.md`. Updating the root README was outside the Phase 1A file scope.

## Phase 1B — Admin management (2026-10-25)

- Implemented settings read/update with validation, role enforcement, and transactional before/after auditing.
- Implemented paginated department, designation, leave-type, holiday, and user-management APIs with contract validation, database uniqueness handling, and audit coverage.
- Implemented HR account creation, deactivation, and password reset. Temporary credentials are never stored or audited in plaintext, and password changes/resets invalidate existing JWTs.
- Implemented paginated, filterable, newest-first Admin audit-log access while preserving database-level append-only runtime permissions.
- Implemented endpoints: `GET/PUT /api/settings`; `GET/POST /api/departments`; `PUT/DELETE /api/departments/{id}`; `GET/POST /api/designations`; `GET/POST /api/leave-types`; `PUT /api/leave-types/{id}`; `GET/POST /api/holidays`; `DELETE /api/holidays/{id}`; `GET/POST /api/users`; `PATCH /api/users/{id}/deactivate`; `POST /api/users/{id}/reset-password`; and `GET /api/audit-logs`.

## Phase 1C — Admin dashboard and integration (2026-10-25)

- Implemented `GET /api/dashboard/admin` with date and department filters, empty-state behavior, headcount, attrition, finalized payroll totals, average gross salary, department headcount/payroll breakdowns, gender distribution, tenure groups, and the latest ten audit events.
- Dashboard calculations use database aggregation and Decimal-backed monetary columns; no employee or payroll demo data is added to the working database.
- Added Admin management, authorization, validation, concurrency, confidentiality, aggregate, filter, empty-state, and complete end-to-end workflow tests while retaining all Phase 1A tests.
- Final verification: 37 pytest tests passed with zero failures (one upstream Starlette/httpx deprecation warning); Ruff format/lint, Python compilation, Alembic drift detection, both Compose configurations, and OpenAPI route generation passed.
- A fresh disposable database migrated to `a49dab4c246b` and completed a live restricted-runtime-role flow covering setup, settings, department, designation, holiday, generated HR credentials, HR login, password reset, audit listing, and the empty Admin dashboard. It produced 14 expected audit rows and was removed afterward; the working database was not populated.
- Contract limitations are recorded in `docs/decision.md`: leave codes are restricted to the four `MODELS.md` values, audit deletions use the existing `update` action, and historical attrition is derived from join/exit dates because status history is not modeled.
- Remaining work begins with the Phase 2 HR backend: employee registration/import/export, salary management, attendance and corrections, leave approval, payroll draft generation, and the HR dashboard.

## Phase 2 — Complete HR backend (2026-10-25)

- Implemented atomic HR employee registration with salary and employee-login creation, generated one-time credentials, employee directory search/filter/pagination, Employee 360, controlled employment updates and exit deactivation, employee contact self-service, salary calculation/update, and audited changes.
- Implemented secure CSV dry-run/import/export with exact headers, row-level errors, duplicate/reference validation, partial valid-row creation, a 2 MB limit, UTF-8 validation, sensitive-field exclusion, and spreadsheet formula-injection protection.
- Implemented server-timestamped attendance check-in/check-out, timezone-aware late and half-day boundaries, weekend/holiday/approved-leave rejection, derived absent/missing-checkout/calendar/board states, date-range history, optional camera GPS radius validation, and concurrency-safe correction requests and decisions.
- Implemented working-day leave balances and requests, holiday/weekend exclusion, overlap and quota enforcement, unlimited unpaid leave, employee cancellation, HR approval/rejection, row locking/advisory locking, filters, notifications, and transactional audits.
- Implemented Decimal-based payroll draft creation and recalculation, tax slabs, attendance/unpaid/half-day deductions, joiner/leaver proration, one-run-per-month enforcement, Admin-only finalization, immutable finalized snapshots, employee notifications, finalized employee payslip listing, and in-memory one-page ReportLab PDFs with ownership checks.
- Implemented `GET /api/dashboard/hr` with date/department filters, empty states, headcount, today's attendance/leave, pending approvals, daily attendance rates, department absenteeism, clipped leave utilization, and deterministic top late-comers. Existing Admin dashboard behavior remains covered by regression and integration tests.
- Added stable permission-aware AI service functions: `get_headcount`, `get_attendance_summary`, `get_late_comers`, `get_leave_summary`, `get_my_leave_balance`, `get_payroll_summary`, and `search_employees`. No AI router or AI-owned file was changed.
- Added routes for `/api/employees`, employee salary/import/export/self-service, `/api/attendance` and corrections, `/api/leaves`, `/api/payroll/runs`, `/api/payslips`, and `/api/dashboard/hr`. OpenAPI now generates 45 paths.
- Added `python-multipart` and `reportlab`; the existing database schema was sufficient, so Alembic remains at `a49dab4c246b` with no new migration.
- Added 24 Phase 2 test cases, including a controlled-time, isolated-PostgreSQL workflow from first-run setup through attendance, correction, leave, payroll recalculation/finalization, PDF, both dashboards, audit, notifications, and cross-role denials. Full verification: 61 pytest cases passed with zero failures (one upstream Starlette/httpx deprecation warning); Ruff lint/format, Python compilation, OpenAPI generation, Alembic drift detection, and both Compose configurations passed.
- Remaining Phase 3 work includes Employee dashboard and notification/announcement APIs plus the separate AI teammate's `/ai/*` implementation; frontend and deployment work remain outside this backend phase.

## Phase 3 — Employee backend, integration, and production readiness (2026-10-25)

- Implemented `GET /api/dashboard/me` with company-timezone status, live today duration, completed weekly hours, configured workdays, current-month late count, leave balances, and the latest finalized payslip. Every query is scoped through the authenticated employee link.
- Implemented paginated announcements and private notifications: `GET/POST /api/announcements`, `GET /api/notifications`, and `PATCH /api/notifications/{id}/read`. Admin/HR can publish; all active roles can read; notification reads are owner-only and idempotent.
- Announcement publication now creates active-user notifications and an audit row atomically using set-based fan-out. Added validation for self-service phone updates and employee exit dates, and removed repeated settings/holiday queries from leave-balance calculation.
- Extended the complete setup-to-payroll integration flow through announcement publication, employee notifications, read state, and employee dashboard. Added rollback, pagination, ownership, authorization, timezone-boundary, empty-state, finalized-payslip, OpenAPI-inventory, and security-scheme tests.
- Restored the production Nginx reverse-proxy configuration, added a backend container health check, and gated frontend/Nginx startup on backend health. Compose interpolation and Nginx syntax validate successfully.
- Final regression result: 69 pytest cases passed with zero failures (one upstream Starlette/httpx deprecation warning). The API exposes 49 paths and Alembic remains at `a49dab4c246b`; no schema migration was required.
- The separate AI teammate may consume the permission-aware functions in `app/services/reporting_service.py`; no AI router or AI-owned implementation was added or overwritten.
