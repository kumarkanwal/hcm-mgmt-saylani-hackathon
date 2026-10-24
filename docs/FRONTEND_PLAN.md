# Frontend Plan — HCM Lite

This is the full task list for the frontend developer. The frontend is what judges see and click during the whole demo, so a clear, consistent and reliable app matters as much as features. UI/UX is worth **10 points**, but the frontend also carries most of the **Core HR flows (25)** and **Data & analytics (20)** points, because judges test them through the screens.

Read **AGENTS.md**, **API.md**, **docs/BACKEND_PLAN.md**, **docs/AI_PLAN.md** and **docs/decision.md** before starting.

---

## 1. What the frontend developer owns

- Every screen for Admin, HR and Employee
- Login, first-run setup and the forced password change
- Role-based menus and route protection
- The three dashboards with charts and filters
- The AI chat panel, the "Summarize" button and the smart leave box (the UI only; the AI developer provides the endpoints)
- Loading, empty and error states on every page
- Phone-friendly layout from 375 px wide

**Not yours:** business rules. The frontend never calculates salary, tax, leave days or attendance status. It shows what the backend returns. Hiding a button is only for convenience; the backend still checks every request.

---

## 2. Stack

- **Next.js** (App Router) with **TypeScript**
- **Tailwind CSS** and **shadcn/ui** for components
- **TanStack Query** for fetching, caching and loading states
- **TanStack Table** for lists with search, filters and paging
- **React Hook Form** with **Zod** for forms
- **Recharts** for charts
- **sonner** (from shadcn) for toast messages
- **date-fns** for showing dates

Pick one style and keep it: one primary colour, the same spacing, the same table and form look on every page. Consistency is part of the score.

---

## 3. Routes

Use **one set of pages shared by all roles**. The menu changes by role, and buttons inside a page change by role. This means far fewer pages to build than having separate Admin, HR and Employee copies. (Record this in decision.md, since AGENTS.md originally listed role folders.)

| Page | Admin | HR | Employee |
|---|---|---|---|
| `/setup` | First run only | | |
| `/login` | ✓ | ✓ | ✓ |
| `/change-password` | ✓ | ✓ | ✓ |
| `/dashboard` | Company dashboard | HR dashboard | Personal dashboard |
| `/employees` | View | Manage | |
| `/employees/new` | | ✓ | |
| `/employees/import` | | ✓ | |
| `/employees/[id]` | View | Manage | |
| `/attendance` | Daily board | Daily board | My calendar |
| `/attendance/corrections` | View | Approve | My requests |
| `/leaves` | View all | Approval inbox | Apply + my history |
| `/payroll` | View + finalize | Create + review | |
| `/payroll/[id]` | View + finalize | Review + recalculate | |
| `/payslips` | | | My payslips |
| `/profile` | ✓ | ✓ | Edit phone + address |
| `/announcements` | Post + read | Post + read | Read |
| `/settings/company` | ✓ | View | |
| `/settings/organization` | Departments, designations, leave types, holidays | View | |
| `/users` | ✓ | | |
| `/audit` | ✓ | | |

If a user opens a page their role can't use, send them to `/dashboard`.

---

## 4. App flow when the site opens

1. Call `GET /setup/status`.
2. If setup isn't done, show `/setup`. Judges start here on a fresh install.
3. If there's no saved token, show `/login`.
4. After login, if `must_change_password` is true, send the user to `/change-password` and don't let them leave until it's done.
5. Otherwise, go to `/dashboard`.

If any request returns **401**, clear the token and go to the login page. If any request returns **403 with the code `PASSWORD_CHANGE_REQUIRED`**, go to the change password page.

---

## 5. Shared building blocks (build these first)

**API client** — one small helper used by every page. It adds the base URL (`/api`), attaches the token, reads the shared error format, and handles 401 and the password change code in one place.

**Auth context** — keeps the token and the current user (from `/auth/me`). Store the token in localStorage. Exposes the role so the menu and pages can use it.

**App layout** — sidebar on desktop, a slide-out menu on phones, a top bar with the company name, notification bell, user menu and logout, and a floating "Ask assistant" button.

**Data table** — one reusable table with server-side search, filters and paging (matching the `{ items, total, page, page_size }` shape).

**Page states** — three small components used on every page:
- **Loading:** skeleton rows or cards, not a blank screen
- **Empty:** a friendly message with the next action, for example "No employees yet. Register your first employee." This matters because judges start with an empty company.
- **Error:** the message from the backend and a "Try again" button

**Forms** — shared field, select, date picker and submit button styles. Show backend errors next to the right field when the backend names one, and show the rest as a toast.

**Confirm dialog** — for actions that can't be undone, like finalizing payroll or deactivating a user.

**Status badges** — one colour per status, used everywhere:
present (green), late (amber), half day (orange), absent (red), on leave (blue), missing checkout (grey), and pending, approved, rejected, draft, finalized.

---

## 6. Phase 1 — Setup and login

| Screen | What it does | API |
|---|---|---|
| First-run setup | Company name, admin email, password and confirm password. On success, show a short "Company created" message and go to login. | `GET /setup/status`, `POST /setup` |
| Login | Email and password. Show a clear message for wrong details or a deactivated account. | `POST /auth/login`, `GET /auth/me` |
| Change password | Old password, new password, confirm. Explain why when it's forced: "Please set your own password before continuing." | `POST /auth/change-password` |

---

## 7. Phase 2 — Admin screens

### Company settings (`/settings/company`)
- Company name, office start time, grace minutes, half-day hours, weekend days (checkboxes)
- Office latitude, longitude and radius in metres
- A **"Use my current location"** button that fills latitude and longitude from the browser, so judges don't have to type coordinates
- A note: "Changes apply to new records only"
- HR sees this page read-only

**API:** `GET /settings`, `PUT /settings`

### Organization (`/settings/organization`)
Four tabs, each with a simple table plus an add or edit dialog:
- **Departments** — refuse to delete one that has employees (show the backend message)
- **Designations** — name and department
- **Leave types** — name, quota (empty means unlimited), paid or unpaid
- **Holidays** — date and name, sorted by date

**API:** `/departments`, `/designations`, `/leave-types`, `/holidays`

### Users (`/users`)
- List of logins with role and active status
- "Create HR login" dialog (email and password)
- Deactivate (with confirm) and reset password. After a reset, show the temporary password once in a dialog with a copy button.

**API:** `GET /users`, `POST /users`, `PATCH /users/{id}/deactivate`, `POST /users/{id}/reset-password`

### Audit log (`/audit`)
- Table: time, who, action, entity
- Filters: entity, user, date range
- Clicking a row shows the before and after values side by side
- Read only, with no edit or delete buttons anywhere

**API:** `GET /audit-logs`

---

## 8. Phase 3 — Employees (HR manages, Admin views)

### Employee list (`/employees`)
- Search by name, code or email; filter by department and status; paging
- Columns: code, name, department, designation, status, join date
- HR sees "Register employee", "Import CSV" and "Export CSV" buttons

**API:** `GET /employees`, `GET /employees/export`

### Register employee (`/employees/new`)
- Code, first and last name, email, phone, gender, department, designation, join date, basic salary
- Show gross, HRA and medical as a live preview under the salary field (display only; the backend saves the real values)
- After saving, show a dialog: **"Employee registered. Temporary password: ______"** with a copy button and a note that they must change it at first login. This is a key demo moment.

**API:** `POST /employees`, `GET /departments`, `GET /designations`

### CSV import (`/employees/import`)
1. Upload the file and show a link to download a sample CSV with the correct columns.
2. Run a dry run first and show the results: how many rows are valid, and a table of errors (row, field, reason).
3. An "Import valid rows" button runs the real import.

**API:** `POST /employees/import?dry_run=true`, then `dry_run=false`

### Employee 360 (`/employees/[id]`)
One page with sections or tabs:
- Profile and job details (HR can edit)
- Salary (HR can change basic)
- This month's attendance summary
- Leave balance
- Last payslips

**API:** `GET /employees/{id}`, `PATCH /employees/{id}`, `GET` and `PUT /employees/{id}/salary`

---

## 9. Phase 4 — Attendance

### Check-in widget (on the Employee and HR dashboards)
- Shows the live time and today's status
- One big button that switches between **Check in** and **Check out**, and is disabled once both are done
- Shows check-in and check-out times and hours worked
- On a weekend, holiday or approved leave day, shows that instead of the button

**API:** `GET /attendance/today`, `POST /attendance/check-in`, `POST /attendance/check-out`

### My attendance (`/attendance` for Employee)
- A month calendar with a coloured status on each day, plus weekends and holidays
- A summary row: present, late, half days, absent
- Clicking a past day opens "Request correction" with times and a reason

**API:** `GET /attendance/me?month=`, `POST /attendance/corrections`

### Daily board (`/attendance` for Admin and HR)
- Date picker (default today) and department filter
- Counters at the top: present, late, absent, on leave
- Table: employee, department, check-in, check-out, status

**API:** `GET /attendance/board`

### Corrections (`/attendance/corrections`)
- HR: pending requests with Approve and Reject, each with an optional comment
- Employee: their own requests and statuses

**API:** `GET /attendance/corrections`, `PATCH /attendance/corrections/{id}`

---

## 10. Phase 5 — Leave

### Employee view (`/leaves`)
- **Balance cards** at the top: one per leave type showing remaining out of quota
- **Smart leave box:** a text field, "Type your request in plain words", for example "Need next Monday and Tuesday off for a wedding". On submit, fill the apply form below and highlight that it was filled by AI. The user checks it and presses Apply. If the AI fails (`AI_PARSE_FAILED`), just open the empty form with a short note.
- **Apply form:** leave type, start date, end date, reason. Show backend errors clearly (overlap, over balance, no working days).
- **History:** past requests with status, HR comment, and a Cancel button where allowed

**API:** `GET /leaves/balance`, `POST /ai/smart-leave`, `POST /leaves`, `GET /leaves/me`, `POST /leaves/{id}/cancel`

### HR view (`/leaves`)
- The approval inbox with Pending selected by default
- Each row: employee, department, type, dates, days, reason
- Approve and Reject with a comment dialog
- Filters: status, department, date range

Admin sees the same list without the action buttons.

**API:** `GET /leaves`, `PATCH /leaves/{id}/decision`

---

## 11. Phase 6 — Payroll and payslips

### Payroll list (`/payroll`)
- Table of runs: month, status, employees, total gross, total net
- HR: "Run payroll" with a month picker. If the month already exists, show the backend message.

### Payroll run (`/payroll/[id]`)
- Summary cards: total gross, total deductions, total tax, total net
- Table of payslips: employee, gross, working days, absent, unpaid, half days, deduction, tax, net
- HR on a draft: "Recalculate"
- Admin on a draft: **"Finalize"** with a confirm dialog explaining that it locks the month
- Finalized runs show a lock badge and no action buttons

**API:** `POST /payroll/runs`, `GET /payroll/runs`, `GET /payroll/runs/{id}`, `POST .../recalculate`, `POST .../finalize`

### My payslips (`/payslips`, Employee)
- List of months with net pay and a **Download PDF** button
- The PDF needs the token, so download it through the API client and save it as a file rather than opening a plain link

**API:** `GET /payslips/me`, `GET /payslips/{id}/pdf`

---

## 12. Phase 7 — Dashboards

All three dashboards have a **date range** filter and (for Admin and HR) a **department** filter at the top. Show numbers exactly as the backend returns them; don't recalculate anything. Every chart needs its own empty state for a fresh company.

### HR dashboard
- KPI cards: headcount, present today, on leave today, late today, pending approvals
- Line chart: attendance rate over the date range
- Bar chart: absenteeism by department
- Bar or donut chart: leave by type
- List: top 5 late-comers
- Announcements and the check-in widget

**API:** `GET /dashboard/hr`

### Admin dashboard
- KPI cards: headcount, attrition this year, payroll cost, average salary
- Bar charts: headcount by department, payroll cost by department
- Gender split and tenure groups
- Recent audit activity
- Announcements

**API:** `GET /dashboard/admin`

### Employee dashboard
- Check-in widget
- Hours this week against 40 (progress bar)
- Late count this month
- Leave balance
- Last payslip with a download button
- Announcements
- An "Ask my assistant" shortcut

**API:** `GET /dashboard/me`

### AI summary (Admin and HR)
A **"Summarize"** button on the dashboard sends the currently loaded dashboard data to the AI and shows 3–5 bullets in a card labelled **AI-generated**, with a loading state and a friendly message if it fails.

**API:** `POST /ai/summary`

---

## 13. Phase 8 — AI chat panel

- A floating button on every page opens a side panel (full screen on phones)
- A message list with user and assistant bubbles, and a typing indicator while waiting
- Each assistant reply shows a small **AI-generated** tag
- Two or three suggested questions to tap, depending on role:
  - HR: "Who is on leave today?", "Who came late most this month?"
  - Employee: "How many sick leaves do I have left?", "What time am I considered late?"
- Send the last few messages as history with each request; keep the conversation only in the browser
- If the server says the limit was reached (429) or the assistant timed out, show its friendly message in the chat instead of an error popup

**API:** `POST /ai/chat`

---

## 14. Phase 9 — Announcements, notifications and profile

| Feature | What it does | API |
|---|---|---|
| Announcements page | Admin and HR can post (title and body). Everyone sees the list. The latest 3 also appear on every dashboard. | `GET`, `POST /announcements` |
| Notification bell | Unread count in the top bar. Opening it lists notifications; clicking one marks it read and goes to the related page (for example, a leave decision goes to Leaves). Refresh every 30 seconds. | `GET /notifications`, `PATCH /notifications/{id}/read` |
| Profile | Shows the user's details. Employees can edit only phone and address. Includes a link to change password. | `GET /auth/me`, `PATCH /employees/me` |

---

## 15. Work before the backend is ready

Don't wait. For each page, write sample responses that match API.md exactly and use them while the backend is being built. Keep the switch in one place (the API client), so moving to the real backend is a single change.

When the backend developer says an endpoint is done, connect that page and test it with real data the same day.

---

## 16. Quality checklist (judges notice these)

- Every button that sends a request shows a loading state and can't be double-clicked
- Every success shows a toast ("Leave approved", "Employee registered")
- Every list has an empty state that tells the user what to do next
- Every error shows the backend's message, never "Something went wrong" with no detail
- Works at 375 px wide: tables scroll sideways inside their card, menus collapse
- Page titles and the browser tab title match the page
- Dates shown in a friendly format (24 Oct 2026); money shown with thousand separators
- No AI key or secret anywhere in the frontend; only `NEXT_PUBLIC_API_URL`

---

## 17. Bonus features (only after the core works)

**Dark mode** — shadcn makes this easy; add a toggle in the user menu.

**Camera check-in (web)** — on the check-in widget, an option to "Check in with camera":
1. Open the front camera with a live preview
2. Detect faces in the browser (face-api or MediaPipe from the brief); require exactly one face
3. Get the location from the browser, with its accuracy
4. Send the source, latitude, longitude, accuracy and face count to the check-in endpoint
5. Show the server's answer (accepted, or why it was rejected)
6. Tell the user what is captured: location and face detection only, no photo saved

Camera and location only work on HTTPS, so test this on the deployed site.

**PWA** — a manifest and icons so it can be installed on a phone.

---

## 18. Order of work and checkpoints

| Order | Work | Depends on |
|---|---|---|
| 1 | Project setup, theme, API client, auth context, layout, shared components | Nothing |
| 2 | Setup, login, change password, role menus | Backend step 2 |
| 3 | Company settings, organization, users | Backend step 3 |
| 4 | Employee list, register, Employee 360 | Backend step 4 → **Checkpoint 1** |
| 5 | Check-in widget, calendar, board, corrections | Backend step 5 |
| 6 | Leave pages and smart leave box | Backend step 6, AI smart leave |
| 7 | Payroll pages and payslips | Backend step 7 → **Checkpoint 2** |
| 8 | Three dashboards and the Summarize button | Backend step 8 |
| 9 | Chat panel, announcements, notifications, audit, profile | AI chat, backend step 9 → **Checkpoint 3** |
| 10 | Polish: empty states, phone layout, toasts, then bonus features | Everything above |

After each step, push a small pull request into `dev` and update **docs/progress.md**.

---

## 19. Walk through the demo before submitting

Run the brief's demo script on the deployed site, start to finish, from a fresh install:
1. Admin sets up the company, office hours, location, a department and leave types, then creates an HR login
2. HR registers two or three employees; one signs in, changes the password and checks in
3. The employee types a leave request in plain words and confirms the filled form; HR approves it
4. HR opens the dashboard, clicks Summarize and asks the assistant who is on leave, then runs payroll; Admin finalizes it
5. The employee downloads the payslip and asks for a colleague's salary (refused); Admin shows the audit log

Every step should take only a few clicks, with no page reloads or confusing screens. If a step feels slow or unclear, fix that before adding anything new.
