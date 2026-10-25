# HCM Lite backend

FastAPI on Python 3.12, managed with uv, backed by PostgreSQL 16. The database
starts empty: first-run setup creates only company defaults and the first Admin.

## Local development

Copy `.env.example` to `.env` and set local-only secrets. Never commit `.env`.

```powershell
uv sync --python 3.12
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Run verification from this directory:

```powershell
uv run pytest -q
uvx ruff check app tests alembic
uvx ruff format --check app tests alembic
uv run python -m compileall -q app tests alembic
uv run alembic check
uv lock --check
```

The application connects with `DATABASE_URL`, which should use the restricted
runtime database role. Alembic uses `MIGRATION_DATABASE_URL`, which should use
the HCM database owner. The current migration head is `a49dab4c246b`.

## Phase 3 APIs

| Method and endpoint | Roles | Input | Output |
| --- | --- | --- | --- |
| `PATCH /api/employees/me` | employee | `EmployeeSelfUpdate` | `EmployeeSummary` |
| `POST /api/attendance/check-in` | employee, HR | `CheckInRequest` | `AttendanceResponse` |
| `POST /api/attendance/check-out` | employee, HR | none | `AttendanceResponse` |
| `GET /api/attendance/today` | employee, HR | none | `AttendanceResponse` or null |
| `GET /api/attendance/me` | employee | `month` query | `AttendanceCalendarResponse` |
| `POST /api/attendance/corrections` | employee | `AttendanceCorrectionCreate` | `AttendanceCorrectionResponse` |
| `GET /api/attendance/corrections` | all roles | pagination/status query | `PaginatedCorrections` (employee is own-scoped) |
| `GET /api/leaves/balance` | all roles | optional `employee_id` for management | `LeaveBalanceItem[]` |
| `POST /api/leaves` | employee, HR | `LeaveCreate` | `LeaveResponse` |
| `POST /api/leaves/{id}/cancel` | employee | path ID | `LeaveResponse` (owner-only) |
| `GET /api/leaves/me` | employee | pagination query | `PaginatedLeaves` |
| `GET /api/payslips/me` | employee | pagination query | `PayslipListResponse` (finalized only) |
| `GET /api/payslips/{id}/pdf` | all roles | path ID | PDF (employee is owner-only) |
| `GET /api/dashboard/me` | employee | none | `EmployeeDashboardResponse` |
| `GET /api/announcements` | all roles | pagination query | `AnnouncementListResponse` |
| `POST /api/announcements` | Admin, HR | `AnnouncementCreate` | `AnnouncementResponse` (201) |
| `GET /api/notifications` | all roles | pagination query | `NotificationListResponse` (own only) |
| `PATCH /api/notifications/{id}/read` | all roles | path ID | `NotificationResponse` (owner-only) |

Authentication failures return `401`; role or scope denials return `403` except
private resource IDs, which return `404` to avoid disclosure. Validation and
business-rule failures return structured `422` errors. Duplicate attendance
check-in and locked payroll/correction conflicts return `409`. Exact field
definitions and endpoint-specific error codes are in `../API.md` and generated
OpenAPI schemas.

All prior Admin, HR, employee, attendance, leave, payroll, payslip, and dashboard
routes remain available. Interactive schemas are served at `/docs` outside
production mode; `/api/health` is the deployment smoke check.

## Shared services for the AI teammate

Import these functions from `app.services.reporting_service`; pass the current
SQLAlchemy `Session` and authenticated `User`. They enforce role and employee
scope internally and return JSON-serializable dictionaries/lists:

```python
get_headcount(session, *, user, department_id=None) -> dict
get_attendance_summary(session, *, user, from_date, to_date, department_id=None) -> dict
get_late_comers(session, *, user, from_date, to_date, limit=5, department_id=None) -> list
get_leave_summary(session, *, user, from_date, to_date, department_id=None) -> dict
get_my_leave_balance(session, *, user) -> list
get_payroll_summary(session, *, user, month, department_id=None) -> dict
search_employees(session, *, user, text, limit=10) -> list
```

Management-only functions reject employees with `403 FORBIDDEN`.
`get_attendance_summary` scopes an employee to their own record;
`get_my_leave_balance` requires an employee-linked account. Invalid ranges,
months, and limits return structured `422` errors, and missing departments
return `404`. AI code must call these services rather than run SQL or write data.

## Production deployment

Back up the database before changing an existing deployment. Then deploy in this
order from the repository root:

```bash
docker compose up -d db
docker compose --profile migration run --rm migrate
docker compose up -d --build backend frontend nginx
curl --fail http://localhost/api/health
```

Store database passwords, `JWT_SECRET`, `AI_API_KEY`, and TLS material outside
Git. Terminate HTTPS with Certbot-managed certificates on the VPS and expose
only Nginx; PostgreSQL and application containers use the private Compose
network. For rollback, restore the database backup if a migration changed data,
deploy the prior image/revision, and run its documented compatible migration.
Do not downgrade blindly after a destructive migration.

The repository Nginx config handles HTTP reverse proxying; certificate issuance,
DNS, host firewall rules, and the actual VPS rollout remain environment-owned
operations and must be verified on the target host.
