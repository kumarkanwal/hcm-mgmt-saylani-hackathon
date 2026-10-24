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
