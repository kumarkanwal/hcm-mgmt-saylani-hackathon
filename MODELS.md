# MODELS.md — Database tables (PostgreSQL)

All tables have `id` (int PK) and `created_at` (server default now) unless noted.

## users
email (unique) · password_hash · role (`admin|hr|employee`) · is_active (bool) · must_change_password (bool) · employee_id (FK employees, nullable)

## settings  (single row)
company_name · office_start (time, 09:00) · grace_minutes (15) · half_day_hours (5) · weekend_days (int[], e.g. [5,6] = Sat,Sun) · office_lat · office_lng · office_radius_m (150) · is_setup_done (bool)

## departments
name (unique)

## designations
name · department_id (FK, nullable)

## leave_types
code (unique: `annual|sick|casual|unpaid`) · name · yearly_quota (int, null = unlimited) · is_paid (bool)

## holidays
date (unique) · name

## employees
employee_code (unique) · first_name · last_name · email (unique) · phone · address · gender (`male|female|other`) · department_id (FK) · designation_id (FK) · join_date · exit_date (nullable) · status (`probation|active|exited`)

## salary_structures
employee_id (FK, unique) · basic (numeric) · hra (numeric = 0.4×basic) · medical (numeric = 0.1×basic) · effective_from (date)

## attendance
employee_id (FK) · date · check_in (timestamptz) · check_out (timestamptz, nullable) · status (`present|late|half_day|absent|missing_checkout|on_leave`) · source (`web|camera`) · lat · lng (nullable)
UNIQUE (employee_id, date)

## attendance_corrections
employee_id (FK) · date · requested_check_in · requested_check_out · reason · status (`pending|approved|rejected`) · reviewed_by (FK users) · comment

## leave_requests
employee_id (FK) · leave_type_id (FK) · start_date · end_date · days (working days) · reason · status (`pending|approved|rejected|cancelled`) · reviewed_by (FK users) · comment

## payroll_runs
month (unique, `YYYY-MM`) · status (`draft|finalized`) · created_by (FK users) · finalized_by (FK users) · finalized_at · total_gross · total_net

## payslips
run_id (FK) · employee_id (FK) · basic · hra · medical · gross · working_days · paid_days · absent_days · unpaid_days · half_days · deduction · tax · net
UNIQUE (run_id, employee_id)

## announcements
title · body · author_id (FK users)

## notifications
user_id (FK) · type (`leave_decision|payslip|correction|announcement`) · message · is_read (bool)

## audit_logs  (insert only)
actor_id (FK users) · action (`create|update|approve|reject|finalize|login|deactivate|reset`) · entity (table name) · entity_id · before (jsonb) · after (jsonb)

## ai_logs
user_id (FK) · feature (`chat|summary|smart_leave`) · prompt · tools_called (jsonb) · response · latency_ms · success (bool)
