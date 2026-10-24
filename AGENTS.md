# AGENTS.md — HCM Lite (Saylani Hackathon)

Instructions for Codex and every teammate. Read this before writing any code.

## Project
HCM Lite: web HR system with 3 roles (admin, hr, employee) and an AI assistant.
The system starts EMPTY. No seed/dummy data except the first-run Admin.

## Stack
- Frontend: Next.js (App Router) + TypeScript, Tailwind, shadcn/ui, TanStack Query, TanStack Table, React Hook Form + Zod, Recharts
- Backend: FastAPI (Python 3.12, uv), SQLAlchemy 2.0, Alembic, Pydantic v2, PyJWT, bcrypt
- AI: LangGraph + Gemini (langchain-google-genai) or Groq, tool calling
- DB: PostgreSQL 16
- PDF: ReportLab · CSV: python csv · Rate limit: slowapi · Tests: pytest
- Deploy: Docker Compose on VPS, Nginx (`/` → frontend, `/api` → backend), HTTPS via Certbot

## Folder structure
```
frontend/
  app/(auth)/  app/(admin)/  app/(hr)/  app/(employee)/
  components/  lib/api.ts  lib/auth.ts  hooks/
backend/
  app/main.py
  app/core/        config.py, security.py (JWT, bcrypt), deps.py (current_user, require_role)
  app/models/      SQLAlchemy models (one file per module)
  app/schemas/     Pydantic request/response models
  app/routers/     thin: parse request → call service → return
  app/services/    ALL business rules live here
  app/ai/          graph.py, tools.py, prompts.py
  tests/
  alembic/
```

## Rules (must follow)
1. Business rules go in `services/`. Routers and AI tools both call the same service functions.
2. Every endpoint checks role AND data scope on the server. An employee only reads rows with their own employee_id.
3. Follow `API.md` exactly (paths, fields, status codes). If you need to change it, update API.md in the same PR.
4. Follow `MODELS.md` for tables and fields.
5. Server sets all timestamps (check-in time, created_at). Never trust client time.
6. Every create/update/approve/finalize writes an audit_log row (actor, action, entity, before, after).
7. Never commit `.env` or keys. Only `.env.example`.
8. AI never writes to the DB on its own and never runs raw SQL. AI key only in backend env `AI_API_KEY`.
9. Keep PRs small: one feature per branch, merge into `dev`.
10. Frontend: every page has loading, empty and error states. Mobile width 375px+.

## Business rules (from the brief)
- Settings (defaults): office start 09:00, grace 15 min, half day under 5 h, weekend Sat–Sun, office lat/lng + radius 150 m. Apply to new records only.
- Attendance: one record per employee per day (second check-in → 409). Late if check-in after 09:15. half_day if worked < 5 h. absent if no record and no approved leave. missing_checkout if no check-out.
- Leave: count working days only (skip weekends + holidays). Quotas: annual 14, sick 8, casual 10, unpaid unlimited. Overlap or over-balance → 422.
- Payroll: gross = 1.5 × basic (HRA 40%, medical 10% of basic). per_day = gross ÷ working days in month. Deduct (absent + unpaid leave + 0.5 × half days) × per_day. Prorate joiners/leavers.
- Tax: annual = gross × 12. 0–600k: 0 · 600k–1.2M: 5% of amount over 600k · 1.2M–2.4M: 30k + 15% over 1.2M · 2.4M–3.6M: 210k + 25% over 2.4M · above 3.6M: 510k + 35% over 3.6M. Monthly tax = annual ÷ 12.
- Payroll: HR creates draft, Admin finalizes. Finalized runs are locked (edit → 409).
- Employee registration by HR creates a user login with a temporary password; must_change_password = true.
- Audit log can never be edited or deleted.

## Permissions summary
- admin: company settings, departments, leave types, holidays, create HR users, deactivate/reset any login, view everything, finalize payroll, audit log.
- hr: register/edit employees, CSV import/export, salary structures, attendance board, approve corrections & leave, payroll draft, HR dashboard. Cannot change settings, create admin, finalize payroll, view audit log.
- employee: own check-in/out, own attendance, request correction, apply/cancel own leave, own payslips, edit own phone & address. Cannot see others' data.

## Git
- Branches: `main` (stable, demo), `dev` (integration), `feat/<name>`.
- Commit style: `feat(leave): apply leave API`, `fix(payroll): tax slab`.
