# Backend Plan — HCM Lite

This is the full task list for the backend developer. The frontend, the AI agent and deployment are all built on top of this work, so every endpoint here matches **API.md** exactly. If anything needs to change, update API.md first and tell the team.

Read **AGENTS.md**, **API.md**, **MODELS.md** and **docs/decision.md** before starting.

---

## 1. What the backend owns

- The database (all tables in MODELS.md) and migrations
- Login, roles and permission checks on every request
- All business rules: attendance status, leave days, payroll and tax
- Every REST endpoint in API.md except the three `/ai/*` endpoints (those belong to the AI developer)
- Service functions that the AI developer calls from the agent tools (Section 13)
- Audit log and notifications
- Tests for the rules that judges will check

The AI developer does **not** touch the database directly. They call the service functions listed in Section 13, so those names and return shapes must stay stable.

---

## 2. Project structure

```
backend/app/
  main.py          app setup, CORS, routers, error handler
  core/            config, database session, security (JWT + bcrypt), dependencies
  models/          one file per module
  schemas/         request and response shapes
  routers/         thin: read input, call a service, return the result
  services/        all business rules
  ai/              owned by the AI developer
backend/tests/
backend/alembic/
```

Routers must stay thin. If a rule is written inside a router, the AI tools won't follow it and the answers won't match the dashboard.

---

## 3. Rules that apply to every endpoint

**Base path:** everything lives under `/api`.

**Authentication:** the client sends the token in the Authorization header. The token holds the user id, role and employee id, and expires after 8 hours.

**Permission checks happen in two layers:**
1. **Role check.** Is this role allowed to call this endpoint at all? If not, return 403.
2. **Scope check.** Is this record theirs? An employee can only read rows with their own employee id. If they ask for someone else's record, return 403 (or 404 if you prefer not to reveal that it exists, but pick one approach and use it everywhere).

**Inactive users:** the login is refused, and any token they already hold stops working.

**Forced password change:** while `must_change_password` is true, the only endpoints the user can call are `/auth/me` and `/auth/change-password`. Everything else returns 403 with the code `PASSWORD_CHANGE_REQUIRED`. The frontend uses that code to show the change password screen.

**Error format** is always the same so the frontend can show messages easily:
`{ detail: { code, message } }`

| Status | When |
|---|---|
| 400 | Bad request that is not a business rule |
| 401 | Missing, expired or invalid token |
| 403 | Wrong role, wrong scope, or password change required |
| 404 | Record not found |
| 409 | Conflict: second check-in on the same day, payroll month already exists, editing a finalized payroll, setup already done |
| 422 | Validation or business rule failure: leave overlap, over balance, outside office radius |
| 429 | Too many AI requests |

**Lists** always return `{ items, total, page, page_size }`, with page 1 and a page size of 20 by default.

**Time:** the server sets every timestamp and never trusts time sent from the client. Store times in UTC, and work out "today", "late" and "half day" in the company time zone (Asia/Karachi, kept in config).

**Audit:** every create, update, approve, reject, finalize, deactivate and password reset writes one audit row with the actor, action, entity, entity id, and the record before and after. Build one small helper for this and call it from the services.

---

## 4. Phase 1 — Foundation (do this first, everyone depends on it)

### 4.1 Setup
- FastAPI app with CORS allowed for the frontend URL
- Database connection from `DATABASE_URL`
- A health endpoint at `/api/health` returning `{ status: "ok" }`, used by deployment
- A global error handler that turns every error into the shared error format
- Dockerfile for the backend (the deployment lead will check it)

### 4.2 All database tables
Create every table from MODELS.md in the first migration, even modules you will build later. This lets everyone work in parallel without changing the schema all day.

Remember the unique rules:
- one attendance row per employee per day
- one payroll run per month
- one payslip per employee per run
- unique employee code and email

### 4.3 First-run setup

| Endpoint | Who | What it does |
|---|---|---|
| GET `/setup/status` | Anyone | Returns whether setup is done. The frontend calls this on first load to decide whether to show the setup screen or the login screen. |
| POST `/setup` | Anyone, only once | Takes the company name, admin email and admin password. Creates the settings row with default rules, creates the Admin user, and fills in the four leave types (annual 14, sick 8, casual 10, unpaid unlimited) from the brief. Returns 409 if setup is already done. |

If `ADMIN_EMAIL` and `ADMIN_PASSWORD` are set in the environment, create the Admin automatically on startup instead.

The four leave types and default settings come from the brief's rules, not dummy data, so filling them in is allowed.

### 4.4 Authentication

| Endpoint | Who | What it does |
|---|---|---|
| POST `/auth/login` | Anyone | Checks the email and password (bcrypt), refuses inactive users, returns the token and a small user object including `must_change_password`. Writes a login audit row. |
| POST `/auth/change-password` | Logged in | Checks the old password, saves the new one (minimum 8 characters), and sets `must_change_password` to false. |
| GET `/auth/me` | Logged in | Returns the user plus a short employee summary (name, department, designation) if they are linked to an employee. |

Build two reusable dependencies: one that gives you the current user, and one that limits an endpoint to certain roles. Every router uses them.

**Checkpoint:** someone can set up the company and log in as Admin. Tell the frontend developer as soon as this works.

---

## 5. Phase 2 — Organization setup

| Endpoint | Who | What it does |
|---|---|---|
| GET `/settings` | Admin, HR | Company name, office start time, grace minutes, half-day hours, weekend days, office latitude, longitude and radius |
| PUT `/settings` | Admin | Updates settings. Changes apply to new records only; never recompute old attendance. |
| GET, POST `/departments` | Get: Admin, HR · Post: Admin | Name must be unique |
| PUT, DELETE `/departments/{id}` | Admin | Refuse to delete a department that still has employees (422) |
| GET, POST `/designations` | Get: Admin, HR · Post: Admin | Name, plus an optional department |
| GET, POST `/leave-types` | Get: everyone · Post: Admin | Code, name, yearly quota (empty means unlimited), paid or unpaid |
| PUT `/leave-types/{id}` | Admin | Change name or quota |
| GET, POST `/holidays` | Get: everyone · Post: Admin | Date and name, date must be unique |
| DELETE `/holidays/{id}` | Admin | |
| GET `/users` | Admin | All logins with role and active status |
| POST `/users` | Admin | Create an HR login only. Never allow creating another Admin here. |
| PATCH `/users/{id}/deactivate` | Admin | Admin cannot deactivate themselves |
| POST `/users/{id}/reset-password` | Admin | Generates a temporary password, sets `must_change_password` to true, and returns it once |

All of these write audit rows.

---

## 6. Phase 3 — Employees

| Endpoint | Who | What it does |
|---|---|---|
| GET `/employees` | Admin, HR | Search by name, code or email. Filter by department and status. Paged, done in the database (not in Python). |
| POST `/employees` | HR | Creates the employee, their salary structure and their login in one transaction. Generates a temporary password, sets `must_change_password` to true, and returns the employee plus the temporary password so HR can share it. |
| GET `/employees/{id}` | Admin, HR, or the employee themselves | The "Employee 360" view: profile, department and designation, salary, this month's attendance summary, leave balance, and the last 3 payslips |
| PATCH `/employees/{id}` | HR | Job details, department, designation, status, and exit date. Setting an exit date also deactivates their login. |
| PATCH `/employees/me` | Employee | Phone and address only. Ignore any other field they send. |
| POST `/employees/import` | HR | Accepts a CSV upload. With dry run on, it only checks the file and returns the valid rows and a list of errors, each with the row number, field and reason. With dry run off, it creates only the valid rows. |
| GET `/employees/export` | HR | Downloads all employees as CSV |
| GET `/employees/{id}/salary` | Admin, HR | Basic, HRA, medical and gross |
| PUT `/employees/{id}/salary` | HR | Takes only the basic salary. HRA is 40% of basic and medical is 10%, worked out on the server. |

**Registration checks:** required fields, valid email, unique code and email, the department exists, the date is in ISO format, and salary is greater than 0. Use the same checks for both the form and the CSV import.

**CSV columns:** employee_code, first_name, last_name, email, phone, gender, department (by name), designation (by name), join_date, basic_salary.

New employees start with the status `probation` unless HR chooses `active`.

---

## 7. Phase 4 — Attendance

### Status rules
- **late:** check-in is after office start plus grace (09:15 by default)
- **present:** checked in on time
- **half_day:** checked out after working less than 5 hours (this replaces present or late)
- **missing_checkout:** a past day with a check-in but no check-out
- **on_leave:** an approved leave covers that day
- **absent:** a working day with no record and no approved leave. Don't store a row for this; work it out when reading the board, calendar, dashboards and payroll. That way there are no nightly jobs to run.

Weekends and holidays are never absent.

### Endpoints

| Endpoint | Who | What it does |
|---|---|---|
| POST `/attendance/check-in` | HR, Employee (themselves) | The server records the time. Returns 409 if they already checked in today, and 422 if it's a weekend, a holiday, or they're on approved leave. Works out late or present. |
| POST `/attendance/check-out` | HR, Employee (themselves) | Returns 422 if there was no check-in today, and 409 if they already checked out. Works out half day from the hours worked. |
| GET `/attendance/today` | HR, Employee (themselves) | Today's record, or empty. The check-in widget uses this. |
| GET `/attendance/me` | Employee | One month of records for the calendar, including the worked-out absent, leave, weekend and holiday days so the frontend doesn't need to calculate anything |
| GET `/attendance/board` | Admin, HR | Every active employee for a chosen date with their status, check-in and check-out times. Filter by department. |
| GET `/attendance` | Admin, HR | Records for one employee across a date range |
| POST `/attendance/corrections` | Employee | Requests a correction for a past day with new times and a reason. Only one pending request per day. |
| GET `/attendance/corrections` | Admin, HR (all), Employee (their own) | Filter by status |
| PATCH `/attendance/corrections/{id}` | HR | Approve or reject with a comment. Approving creates or updates the attendance row and recalculates its status. The employee gets a notification. |

### Camera check-in (bonus, but plan for it now)
When the source is `camera`, the request also includes latitude, longitude, GPS accuracy, and the number of faces found. Reject with 422 if:
- the number of faces is not exactly one
- GPS accuracy is worse than 100 metres
- the distance from the office (Haversine formula) is more than the radius in settings

The server decides; the phone only sends data. Don't store photos. Add the face count field to API.md when you build this.

---

## 8. Phase 5 — Leave

### Rules
- Count working days only: skip weekends and holidays.
- A request with zero working days is refused (422).
- A request that overlaps another pending or approved leave is refused (422).
- **Balance:** remaining equals the yearly quota minus approved days minus pending days, for the current year. If the new request is more than what remains, refuse it (422). Unpaid leave has no limit.
- The employee can cancel a pending leave, or an approved leave that hasn't started yet.

### Endpoints

| Endpoint | Who | What it does |
|---|---|---|
| GET `/leaves/balance` | Employee (themselves), Admin and HR (with an employee id) | For each leave type: quota, used, pending and remaining |
| POST `/leaves` | Employee, HR (for themselves) | Leave type, start date, end date and reason. Saves the number of working days. Starts as pending. |
| POST `/leaves/{id}/cancel` | The employee who owns it | Follows the cancel rule above |
| GET `/leaves/me` | Employee | Their own history |
| GET `/leaves` | Admin, HR | The approval inbox. Filter by status, department and date range. Show the employee's name and department in each row. |
| PATCH `/leaves/{id}/decision` | HR | Approve or reject with a comment. Only pending requests can be decided. Recheck the balance when approving. Sends the employee a notification. |

Use clear error codes: `LEAVE_OVERLAP`, `LEAVE_OVER_BALANCE`, `LEAVE_NO_WORKING_DAYS`, `LEAVE_NOT_PENDING`.

---

## 9. Phase 6 — Payroll

### Calculation for each employee in the month
1. **Gross** = basic + HRA (40%) + medical (10%), which is 1.5 × basic.
2. **Working days** = the weekdays in the month that are not holidays.
3. **Per day** = gross ÷ working days.
4. **Proration:** if the employee joined or left during the month, they're paid only for working days while employed.
5. **Deduction** = per day × (absent days + unpaid leave days + 0.5 × half days).
6. **Tax:** take gross × 12, apply the slab below, then divide by 12.
   - Up to 600,000: no tax
   - 600,000 to 1,200,000: 5% of the amount above 600,000
   - 1,200,000 to 2,400,000: 30,000 plus 15% above 1,200,000
   - 2,400,000 to 3,600,000: 210,000 plus 25% above 2,400,000
   - Above 3,600,000: 510,000 plus 35% above 3,600,000
7. **Net** = prorated gross − deduction − monthly tax. Round money to 2 decimal places.

Save every number on the payslip so it never changes after finalizing, even if a salary changes later.

Include employees who are active or on probation, have a salary structure, and were employed at some point in that month.

### Endpoints

| Endpoint | Who | What it does |
|---|---|---|
| POST `/payroll/runs` | HR | Creates a draft run for a month along with all its payslips. Returns 409 if that month already exists. |
| GET `/payroll/runs` | Admin, HR | All runs with month, status and totals |
| GET `/payroll/runs/{id}` | Admin, HR | One run with every payslip and employee names |
| POST `/payroll/runs/{id}/recalculate` | HR | Rebuilds the payslips of a draft (for example, after approving late corrections). Returns 409 if it's finalized. |
| POST `/payroll/runs/{id}/finalize` | Admin | Locks the run. After this, nothing about it can change (409). Every employee in the run gets a payslip notification. |
| GET `/payslips/me` | Employee | Their own payslips from finalized runs only |
| GET `/payslips/{id}/pdf` | Admin, HR, or the owner | A clean one-page PDF: company name, employee details, month, earnings, deductions, tax and net pay |

---

## 10. Phase 7 — Dashboards

Every number is computed in the database. All three endpoints accept a date range (from, to) and a department filter. The frontend shows the numbers as they are, and the AI summary uses the same JSON.

### Formulas (from the brief)
- **Headcount:** employees active or on probation on the end date
- **Attrition:** exits in the period ÷ average headcount × 100
- **Attendance rate:** (present + late + missing checkout + 0.5 × half day) ÷ (working-day records − on leave)
- **Late %:** late ÷ (present + late)
- **Absenteeism:** absent days ÷ expected working days, per department
- **Leave use:** approved days ÷ quota, per leave type and department
- **Payroll cost:** total gross and net by month and department
- **Average salary:** mean gross by department and designation

### Endpoints

| Endpoint | Who | Returns |
|---|---|---|
| GET `/dashboard/admin` | Admin | Headcount, attrition this year, payroll cost, average salary, headcount by department, payroll cost by department, gender split, tenure groups (under 1 year, 1 to 3 years, more than 3 years), the 10 latest audit entries |
| GET `/dashboard/hr` | Admin, HR | Headcount, present today, on leave today, late today, pending approvals (leave + corrections), daily attendance rate for the range, absenteeism by department, leave by type, top 5 late-comers |
| GET `/dashboard/me` | Employee | Today's status, hours this week out of 40, late count this month, leave balance, last payslip |

Write down the exact JSON shape of each dashboard in API.md as soon as it's ready, because both the frontend and the AI developer depend on it.

---

## 11. Phase 8 — Announcements, notifications and audit

| Endpoint | Who | What it does |
|---|---|---|
| GET `/announcements` | Everyone | Newest first, with the author's name |
| POST `/announcements` | Admin, HR | Title and body. Every active user gets a notification. |
| GET `/notifications` | Everyone (their own) | Newest first, with the unread count |
| PATCH `/notifications/{id}/read` | The owner | Marks it read |
| GET `/audit-logs` | Admin | Filter by entity, user and date range. Read only: there are no update or delete endpoints, and the service never edits these rows. |

**Notifications are created when:** a leave is approved or rejected, a correction is decided, a payroll run is finalized, or an announcement is posted.

---

## 12. AI support tables (for the AI developer)

The AI developer owns the `/ai/*` endpoints. The backend only provides:
- the `ai_logs` table and a small helper to write a row
- the current user dependency, so the AI endpoints know the role and employee id

---

## 13. Service functions the AI agent will call

These sit in `services/` and are used by both the REST endpoints and the AI tools. Each takes the current user and enforces the same scope as the API. Keep these names stable, and share the return shapes with the AI developer early.

| Function | Returns | Who can use it |
|---|---|---|
| get_headcount (optional department) | Total, and per department | Admin, HR |
| get_attendance_summary (date range, optional department) | Present, late, half day, absent, on leave, attendance rate | Admin, HR; an employee gets only their own |
| get_late_comers (date range, limit) | Names with late counts | Admin, HR |
| get_leave_summary (date range, optional department) | Who is on leave and the counts by type | Admin, HR |
| get_my_leave_balance | The current user's balance per type | Everyone (their own only) |
| get_payroll_summary (month, optional department) | Totals and averages | Admin; HR without individual salaries if you want to be careful |
| search_employees (text) | Names, codes, departments. **No salary fields.** | Admin, HR |

If an employee asks about another person, the service refuses before the AI ever sees the data. That's what makes the "colleague's salary" test pass.

---

## 14. Tests to write

Keep the tests short and focused on the rules judges will check:
- Late at 09:16, on time at 09:15
- Half day when working less than 5 hours
- A second check-in returns 409
- Leave across a weekend counts only working days
- Leave over a holiday skips the holiday
- Overlapping leave and over-balance leave both return 422
- Gross and the tax slab at each boundary (600k, 1.2M, 2.4M, 3.6M)
- Proration for someone joining mid-month
- Editing a finalized payroll returns 409
- An employee reading another employee's record returns 403
- HR calling finalize payroll or audit log returns 403

---

## 15. Order of work and checkpoints

| Order | Work | Tell the team when done |
|---|---|---|
| 1 | Setup, all tables, health endpoint | Deployment lead can deploy |
| 2 | First-run setup, login, role and scope checks | Frontend can build login |
| 3 | Organization setup and users | **Checkpoint 1** together with employees |
| 4 | Employees with login creation | **Checkpoint 1:** setup → HR → employee works live |
| 5 | Attendance and corrections | Frontend check-in widget and board |
| 6 | Leave | Frontend leave screens; AI smart leave can be tested end to end |
| 7 | Payroll and payslip PDF | **Checkpoint 2:** full HR flow works |
| 8 | Dashboards and service functions | AI developer connects the tools |
| 9 | Announcements, notifications, audit | **Checkpoint 3:** full demo flow |
| 10 | Tests and cleanup | Ready for judging |

After each step, push a small pull request into `dev`, update **docs/progress.md**, and record any API change in **API.md** and **docs/decision.md**.

---

## 16. Done means

- Every endpoint in API.md (except `/ai/*`) works and returns the agreed shape
- Every endpoint checks role and scope on the server
- Passwords are hashed and secrets come only from the environment
- The judges' demo flow works from a fresh install with no dummy data
- Dashboard numbers match the records created during judging
- The tests in Section 14 pass
