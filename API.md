# API.md — REST contract (base: `/api`)

## Conventions
- Auth: `Authorization: Bearer <jwt>`. JWT payload: `{ sub: user_id, role, employee_id }`, 8 h expiry.
- Dates: ISO `YYYY-MM-DD`; times: ISO datetime (UTC). Money: number.
- List response: `{ items: [], total, page, page_size }` (query: `page`, `page_size`, default 1 / 20).
- Error: `{ detail: { code: "LEAVE_OVERLAP", message: "..." } }`
- Status codes: 200 ok · 201 created · 401 not logged in · 403 wrong role/scope · 404 · 409 conflict (duplicate check-in, finalized payroll) · 422 validation/business rule.
- Roles column: A = admin, H = hr, E = employee. "own" = only own records.

## M1 Auth & first run
| Method | Path | Roles | Body / Query | Returns |
|---|---|---|---|---|
| GET | /setup/status | public | – | `{ is_setup_done }` |
| POST | /setup | public (only once) | `{ company_name, admin_email, admin_password }` | 201 |
| POST | /auth/login | public | `{ email, password }` | `{ access_token, user: { id, email, role, employee_id, must_change_password } }` |
| POST | /auth/change-password | A H E | `{ old_password, new_password }` | 200 |
| GET | /auth/me | A H E | – | user + employee summary |

## M2 Organization setup
| Method | Path | Roles | Notes |
|---|---|---|---|
| GET / PUT | /settings | GET: A H · PUT: A | office_start, grace_minutes, half_day_hours, weekend_days, office_lat, office_lng, office_radius_m, company_name |
| GET / POST | /departments | GET: A H · POST: A | `{ name }` |
| PUT / DELETE | /departments/{id} | A | |
| GET / POST | /designations | GET: A H · POST: A | `{ name, department_id }` |
| GET / POST | /leave-types | GET: A H E · POST: A | `{ code, name, yearly_quota, is_paid }` |
| PUT | /leave-types/{id} | A | |
| GET / POST | /holidays | GET: A H E · POST: A | `{ date, name }` |
| DELETE | /holidays/{id} | A | |
| GET | /users | A | list logins |
| POST | /users | A | create HR: `{ email, password }` |
| PATCH | /users/{id}/deactivate | A | |
| POST | /users/{id}/reset-password | A | returns `{ temp_password }` |

## M3 Employees
| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | /employees | A H | query: `search, department_id, status, page, page_size` |
| POST | /employees | H | `{ employee_code, first_name, last_name, email, phone, gender, department_id, designation_id, join_date, basic_salary }` → creates login, returns `{ employee, temp_password }` |
| GET | /employees/{id} | A H (E own) | Employee 360: profile, salary, attendance summary, leave balance, last payslips |
| PATCH | /employees/{id} | H | job details, status, exit_date |
| PATCH | /employees/me | E | `{ phone, address }` only |
| POST | /employees/import?dry_run=true | H | multipart CSV → `{ valid_rows, errors: [{ row, field, reason }] }` |
| GET | /employees/export | H | CSV file |
| GET / PUT | /employees/{id}/salary | GET: A H · PUT: H | `{ basic }` (hra, medical computed) |

## M4 Attendance
| Method | Path | Roles | Notes |
|---|---|---|---|
| POST | /attendance/check-in | H E (own) | `{ source: "web"|"camera", lat?, lng?, accuracy? }` → 409 if already checked in |
| POST | /attendance/check-out | H E (own) | – |
| GET | /attendance/today | H E (own) | today's record or null |
| GET | /attendance/me | E | query `month=YYYY-MM` → calendar records |
| GET | /attendance/board | A H | query `date, department_id` → every employee + status |
| GET | /attendance | A H | query `employee_id, from, to` |
| POST | /attendance/corrections | E | `{ date, requested_check_in, requested_check_out, reason }` |
| GET | /attendance/corrections | A H (E own) | query `status` |
| PATCH | /attendance/corrections/{id} | H | `{ action: "approve"|"reject", comment }` |

## M5 Leave
| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | /leaves/balance | E own; A H with `employee_id` | `[{ leave_type, quota, used, pending, remaining }]` |
| POST | /leaves | H E (own) | `{ leave_type_id, start_date, end_date, reason }` → 422 on overlap / over-balance / zero working days |
| POST | /leaves/{id}/cancel | E own (pending or future approved) | |
| GET | /leaves/me | E | own history |
| GET | /leaves | A H | query `status, department_id, from, to` (approval inbox) |
| PATCH | /leaves/{id}/decision | H | `{ action: "approve"|"reject", comment }` → notification to employee |

## M6 Payroll
| Method | Path | Roles | Notes |
|---|---|---|---|
| POST | /payroll/runs | H | `{ month: "YYYY-MM" }` → creates draft + payslips |
| GET | /payroll/runs | A H | list |
| GET | /payroll/runs/{id} | A H | run + payslips |
| POST | /payroll/runs/{id}/recalculate | H | 409 if finalized |
| POST | /payroll/runs/{id}/finalize | A | locks; notifies employees |
| GET | /payslips/me | E | own payslips (finalized only) |
| GET | /payslips/{id}/pdf | A H (E own) | PDF file |

## M7 Dashboards (query for all: `from, to, department_id`)
| Method | Path | Roles | Returns |
|---|---|---|---|
| GET | /dashboard/admin | A | headcount, attrition_ytd, payroll_cost, avg_salary, headcount_by_dept, payroll_cost_by_dept, gender, tenure, recent_audit |
| GET | /dashboard/hr | A H | headcount, present_today, on_leave_today, late_today, pending_approvals, attendance_trend, absenteeism_by_dept, leave_by_type, top_late_comers |
| GET | /dashboard/me | E | today_status, hours_this_week, late_count, leave_balance, last_payslip |

## M8 AI
| Method | Path | Roles | Body | Returns |
|---|---|---|---|---|
| POST | /ai/chat | A H E | `{ message, history? }` | `{ answer, tools_used, ai_generated: true }` |
| POST | /ai/summary | A H | `{ kpis: {...} }` (current dashboard JSON) | `{ bullets: [3–5 strings] }` |
| POST | /ai/smart-leave | E H | `{ text }` | `{ leave_type, start_date, end_date, reason }` (form prefill only, NOT saved) |

AI tools (same services + scope as REST): get_headcount, get_attendance_summary, get_late_comers, get_leave_summary, get_my_leave_balance, get_payroll_summary, search_employees.
Limits: 15 s timeout, ~20 requests/user/hour (429), every call logged in ai_logs.

## M9 Comms & Audit
| Method | Path | Roles | Notes |
|---|---|---|---|
| GET | /announcements | A H E | |
| POST | /announcements | A H | `{ title, body }` |
| GET | /notifications | A H E (own) | |
| PATCH | /notifications/{id}/read | own | |
| GET | /audit-logs | A | query `entity, actor_id, from, to` |
