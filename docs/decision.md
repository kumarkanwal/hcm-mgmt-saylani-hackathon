# Implementation decisions

## 2026-10-25 — Phase 1A database and authentication

- `settings` is constrained to `id = 1`, which enforces the documented single-row table at the database boundary.
- The model contract has no company-timezone column. `COMPANY_TIMEZONE` defaults to `Asia/Karachi` in environment-based backend settings; no schema field was added.
- Initial setup and environment bootstrap are system actions with no authenticated actor. `audit_logs.actor_id` is nullable so those create events are retained without attributing them to the Admin account they create.
- `MODELS.md` does not specify types or nullability for every field. Financial columns use `NUMERIC`, timestamps use timezone-aware values, optional values follow explicit nullable markers or API needs, and enumerated strings receive database check constraints.
- `POST /api/setup` specifies `201` but no success body. It currently returns a small `{ "message": "Company setup completed" }` confirmation; no Admin account or credential is returned.
- Setup and bootstrap serialize with a PostgreSQL transaction-scoped advisory lock. This protects the first-run singleton even when multiple workers race before any settings row exists.
- The Compose database owner remains separate from `hcm_lite_runtime`. The backend receives only the runtime URL; schema changes use `MIGRATION_DATABASE_URL` through the migration profile. The runtime role cannot create schemas or mutate/delete audit rows.

## 2026-10-25 — Admin management and dashboard

- Password-backed JWTs include an HMAC token version derived from the current password hash. Changing or resetting a password therefore invalidates previously issued access tokens without adding session tables or changing public API contracts.
- `API.md` requires `POST /users` with an email and password, while the Phase 1B handoff asks the server to generate a temporary password. The endpoint supports both: a supplied API-contract password is treated as the one-time temporary password, and omission generates a cryptographically secure password. Both paths set `must_change_password=true` and return the temporary password once.
- `MODELS.md` restricts leave-type codes to `annual`, `sick`, `casual`, and `unpaid`, and setup creates all four. The create route preserves that constraint, so normal initialized companies update these types rather than inventing unsupported codes.
- `MODELS.md` has no `delete` audit action. Successful department and holiday deletions are recorded as `update` events with the full prior snapshot and `after={"deleted": true}` so deletion remains auditable without silently changing the model contract.
- The Admin dashboard defaults to year-to-date in the configured company timezone. Payroll metrics include finalized runs only. Historical attrition uses join/exit dates because the current model has no employee-status history; recent audit activity remains organization-wide when a department filter is selected because audit rows do not carry a department key.

## 2026-10-25 — Phase 2 HR operations and payroll

- `salary_structures` has one row per employee rather than an effective-dated history. HR salary updates replace that row and advance `effective_from`; finalized payslips remain immutable historical snapshots of every monetary component.
- For joiners and leavers, a payslip's `gross` stores the prorated gross because `MODELS.md` has no separate prorated-gross column. `basic`, `hra`, and `medical` retain the contractual monthly snapshot. The specified tax calculation annualizes the full contractual monthly gross, so the full computed monthly tax is subtracted from prorated gross; tests lock this interpretation.
- Attendance check-in status is stored when the record is created and is not rewritten after a settings change. Calendar, absence, and working-day derivations use the current settings because the schema has no policy snapshot. A correction uses current settings when recalculating status and cannot be approved after that month's payroll is finalized.
- Cross-year leave requests reserve and consume quota independently in each calendar year. HR leave reporting clips approved requests to working days within the requested range; for a multi-year utilization range, the displayed quota is the yearly quota multiplied by the number of included calendar years. Unlimited leave has null quota and utilization.
- CSV imports are partial by contract: validation is shared with normal employee registration, and every valid row is committed as its own complete employee/salary/login/audit transaction. A failure cannot leave a partial employee, while other valid rows may still succeed and return their one-time temporary passwords.
- Phase 2 response contracts are defined by the Pydantic models in `backend/app/schemas/hr.py`. No shared API or model document was changed; the HR dashboard's flexible breakdown objects include explicit `quota` and `utilization_percent` values for leave usage.

## 2026-10-25 — Phase 3 employee experience and production integration

- The existing notification table stores only `message` and `type`. The API preserves those fields and derives stable `title`, `body`, and `link` presentation metadata from the constrained notification type, avoiding an undocumented schema change while satisfying the employee UI contract.
- Employee dashboard dates use the configured company timezone. Weekly totals contain completed shifts only so an open or missing checkout cannot inflate payroll-adjacent totals; today's `work_duration` may show the live elapsed duration of an open shift. The displayed weekly target is 40 hours and the daily series follows configured working weekdays.
- Dashboard attendance status calls the same derivation function used by attendance history, so leave, holiday, weekend, absence, and missing-checkout rules cannot drift between endpoints.
- Announcement title/body limits are 200/500 characters, matching the existing database and frontend expectations. Author display names use the linked employee name when available and fall back to the account email for system-style Admin accounts.
- Announcement creation, active-user notification fan-out, and audit insertion are one transaction. Notification fan-out is a set-based insert rather than one query per user. Reading notifications is always scoped to the authenticated account; cross-account IDs return not found.
- The existing 17-table schema supports all Phase 3 functionality, so the Alembic head remains `a49dab4c246b`. No `API.md`, `MODELS.md`, frontend, or AI-owned file was changed.
