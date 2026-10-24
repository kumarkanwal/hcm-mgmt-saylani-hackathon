# HCM Lite

AI-assisted Human Capital Management for Admin, HR and Employees — Saylani Hackathon, 24 Oct 2026.

- **Live:** <add link>
- **Stack:** Next.js · FastAPI · PostgreSQL · LangGraph · Docker

## Run locally (under 10 minutes)
```bash
git clone <repo-url> && cd hcm-lite
cp .env.example .env        # set passwords, JWT_SECRET, AI_API_KEY
docker compose up -d --build
docker compose exec backend alembic upgrade head
```
Open http://localhost → first-run setup asks for company name and Admin account.

## First Admin
Created on the first-run screen, or set `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`.

## AI key
Set `AI_API_KEY` (and `AI_PROVIDER`, `AI_MODEL`) in `.env`. The key is only used by the backend.

## Done / Not done
- [ ] M1 Auth & Access
- [ ] M2 Organization Setup
- [ ] M3 Employees
- [ ] M4 Attendance
- [ ] M5 Leave
- [ ] M6 Payroll Lite
- [ ] M7 Dashboards
- [ ] M8 AI Assistant
- [ ] M9 Comms & Audit
- [ ] Bonus: camera attendance

## Team
| Name | Role |
|---|---|
| | Backend 1 (Lead) |
| | Backend 2 |
| | Frontend 1 |
| | Frontend 2 |
