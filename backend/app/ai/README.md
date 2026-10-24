# HCM Lite AI — Gemini only

The existing LangGraph assistant, seven read-only tools, dashboard summaries, smart-leave previews and policy Q&A use Google Gemini exclusively. Provider configuration and secrets remain backend-only. The retired provider and its SDK dependency have been removed. Historical results in VERIFICATION.md describe earlier versions; the latest section records current behavior.

## Local AI Testing Playground

Requires your installed Python 3.11 (Python 3.12+ remains supported). From backend/:

```sh
uv sync --python 3.11 --no-python-downloads
AI_PLAYGROUND=1 uv run --python 3.11 --no-python-downloads python -m app.ai.dev_playground
```

Open http://127.0.0.1:8765. Refresh an existing browser tab after updates. There is no model selector: every request goes to Gemini. Stop with Ctrl+C. If the port is already occupied by this playground, use the running instance instead of starting another.

The development entry point explicitly loads backend/.env, then root .env, without overriding exported environment variables. Set AI_PLAYGROUND_ENV_FILE to select a different local .env. The production Settings class does not load files automatically. Never publish keys.

```dotenv
AI_PROVIDER=gemini
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.1-flash-lite
AI_TIMEOUT_SECONDS=15
AI_RATE_LIMIT_PER_HOUR=20
AI_TIMEZONE=Asia/Karachi
```

AI_API_KEY and AI_MODEL remain legacy Gemini aliases. Provider-specific settings take precedence. Other providers are rejected. There is no cross-provider fallback. Provider failures return safe errors; structured extraction still retries invalid output once within the overall deadline.

The browser offers Chat, Dashboard Summary and Smart Leave tabs, Admin/HR/Employee identities, bounded conversation history, loading/error states, AI labels, tools used, provider attempts and latency. Role changes clear conversation and prior results. Admin can read payroll totals; HR cannot. Employees can access only their own attendance and leave balance. Leave previews never submit requests. Relative dates use Asia/Karachi; Roman Urdu leave input is supported. Factual replies use the original evidence-rendering English templates.

Nine fictional employee records span Engineering, Sales, Human Resources, Marketing and Finance. Headcount, payroll and dashboard aggregates derive from the same deterministic demo records. Data is fixed for the server start date. Demo payslips are illustrative records, not a replacement for production payroll calculations. Empty and insufficient dashboard scenarios are available. No PostgreSQL, Docker, frontend framework or real HR writes are used.

The standalone development app requires AI_PLAYGROUND=1, binds only 127.0.0.1:8765, rejects foreign origins/hosts/non-loopback clients, requires a browser POST token and serves allowlisted assets with a same-origin content policy. It is never mounted by production. In-memory rolling-hour limits/logging are exclusive to this playground. Do not deploy it.

## Production integration and contracts

Mount create_router(current_user, get_ai_service) under /api once. Without real dependencies the normal router fails closed. Production requires the existing JWT current_user dependency and backend-owned services, never simulated identities or demo records.

AIService orchestrates authentication/account checks, role guards, operational reservation, deadline, workflows and safe log completion. Chat uses StateGraph START -> agent -> authorized tools -> agent -> END, then evidence selection. Maximum three tools per question. Client history is untrusted, never evidence. Summary reloads authoritative KPIs rather than trusting client values. Smart leave validates dates, type and reason and never writes a leave record.

ServiceAdapter binds exactly these async read functions, each receiving current_user and independently enforcing role and data scope:

| Function | Arguments | Result schema in schemas.py | Roles |
|---|---|---|---|
| get_headcount | department? | Headcount | Admin/HR |
| get_attendance_summary | start_date, end_date, department? | Attendance | Admin/HR; Employee own |
| get_late_comers | dates, department?, limit | LateResult | Admin/HR |
| get_leave_summary | dates, department? | LeaveSummary | Admin/HR |
| get_my_leave_balance | none | Balances | Own linked employee |
| get_payroll_summary | month YYYY-MM, department? | Payroll | Admin |
| search_employees | text | Employees | Admin/HR |

Supporting callbacks: departments(current_user)->list[str]; policy(current_user)->complete Policy projection; dashboard(current_user, context:KPIContext)->KPIs. Policy must include office_start, grace_minutes, half_day_hours, weekend_days and leave_quotas. Do not silently substitute old defaults for changed live settings. Dashboard chart schemas remain provisional and adapters must normalize actual backend data. Services compute all official metrics; AI does not recalculate production business rules.

OperationsAdapter binds reserve(current_user,feature,limit)->request_id and complete(request_id,record). Production reserve must atomically count/reserve attempts across workers, all three features, successes and failures over a rolling hour and persist an initial ai_logs row. Complete maps the model's user_id, feature, redacted prompt/response, tools_called, latency_ms, success fields. Provider attempts are safe metadata, not an invented database column. Reconcile stale reservations. A small cleanup budget stays inside the 15-second request deadline. Never use the demo in-memory implementation in production.

## API

Existing API.md contracts are unchanged:

- POST /api/ai/chat: `{message,history?}` -> `{answer,tools_used,ai_generated:true}`; all roles.
- POST /api/ai/summary: `{kpis:{...}}` -> `{bullets:[...]}`; Admin/HR. Three to five facts, or one insufficient-data bullet.
- POST /api/ai/smart-leave: `{text}` -> `{leave_type,start_date,end_date,reason}`; Employee/HR. Form prefill only.

Shared errors: `{detail:{code,message}}`. 401 auth; 403 scope/account/password; 422 invalid input/parse/clarification/tool limit; 429 quota; 503 provider/service/configuration unavailable; 504 timeout. Browser diagnostics never expose keys or raw exception bodies. Logs redact user/model text. No SQL, shell tools, external web tools or HR write tools are exposed to the agent.

Try: Sales headcount; attendance this month; today's leave; Engineering directory; own sick balance; policy grace period; Admin payroll last month; an employee asking for a colleague's salary (no salary disclosed). Smart leave: “Next Monday and Tuesday off for my sister's wedding”, “Tomorrow annual leave”, or “Mujhe kal chutti chahiye, bukhar hai.” Ambiguous dates request clarification.

## Tests and troubleshooting

```sh
uv run --python 3.11 --no-python-downloads python -m pytest -q
uv run --python 3.11 --no-python-downloads ruff check app/ai
uv run --python 3.11 --no-python-downloads ruff format app/ai --check
node --check app/ai/playground/app.js
```

Routine tests use injected model doubles. Optional AI_RUN_LIVE=1 enables the Gemini tool-calling/structured-output smoke test with exported credentials. Production JWT/PostgreSQL integration remains skipped until those backend components exist. See VERIFICATION.md for actual runs.

AI_CONFIGURATION means the Gemini key/model is missing. AI_PROVIDER_AUTH means account/model access was denied. A 504 means inference exceeded the existing 15-second budget. The 20/hour development quota resets when the server restarts; production must persist it. Browser stale-token errors require reloading the page. Unknown departments produce clarification rather than widened scope.

Files: config.py/providers.py; router.py/guard.py; graph.py/tools.py; schemas.py/adapters.py/services.py; policy.py/prompts.py/render.py/dates.py; smart_leave.py/dashboard_summary.py; dev_playground.py/dev_data.py/dev_adapters.py/playground/; tests/.
