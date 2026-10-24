# Local verification — 25 October 2026 (Asia/Karachi)

## Executed

Python 3.12.15, dependencies pinned in backend/uv.lock.

From backend/:

- `.venv/bin/python -m pytest -q` — **125 passed, 2 skipped, 0 failed**, 0.63 s on final run.
- `.venv/bin/ruff check app/ai --no-cache` — passed.
- `.venv/bin/ruff format app/ai --check --no-cache` — 28 Python files already formatted.
- `git diff --check` — passed; no staged files.
- Generated-source AST parsing and credential-pattern review — passed (tests contain deliberately fake credentials).

The first suite run found a missing import in a newly added SDK-compatibility test (123 passed, 1 failed, 2 skipped). The import was corrected; the full suite then passed. A final compatibility test for google-genai HTTP errors was added and passed. No failures are hidden.

## Skips

1. `test_real_backend_postgres_and_jwt`: repository has no real FastAPI app, JWT dependency, database models, services or migrations. No real PostgreSQL/JWT behavior was exercised.
2. `test_live_both_providers_tool_calling_and_structured_output`: live requests are opt-in; both provider keys are not present in the process environment. No secret files were loaded and no billable model calls were made.

Actual installed provider clients were instantiated with fake test keys and successfully bound tool schemas and structured output without making network requests. This checks SDK API compatibility, not authentication, regional model availability or model behavior.

## Acceptance status

| Requirement | Status |
|---|---|
| Organized implementation in backend/app/ai | Implemented and locally checked |
| LangGraph tool loop; maximum three calls | Implemented and tested |
| Seven read-only tool wrappers | Implemented and tested against service fixtures |
| Three API contracts | Implemented and tested through a FastAPI harness |
| Qwen primary / Gemini fallback | Configured; deterministic failover tests pass |
| Live compatible Qwen and Gemini models | Awaiting credentials and live verification |
| Grounded chat and policy replies | Implemented and tested with fixed evidence rendering |
| Dashboard summaries | Implemented and tested; authoritative dashboard adapter required |
| Smart leave | Implemented and tested; no save path exists |
| Role and own-employee scope | AI layer tested; independent real backend scope enforcement pending |
| Prompt/history isolation and sensitive field rejection | Implemented and tested |
| Overall deadline, malformed-output retry, safe errors | Implemented and tested |
| Shared rate limit and logging | Enforcement interfaces and injected tests pass; durable production callbacks pending |
| Real JWT, inactive account reload, database reads | Blocked by absent backend components |
| No SQL, HR writes, production seed fixtures | Source reviewed and architectural tests pass |
| Documentation and nonsecret env examples | Complete |
| Deployment | Not performed |
| Local-only Git restrictions | ai_agent; no staging, commits, pushes or remote mutations |

## Integration handoff

Bind the real current_user dependency, seven read services, department names, complete live policy projection, role-scoped dashboard aggregation, and atomic durable ai_logs reservation/completion callbacks. Detailed signatures and provisional output schemas are in README.md, services.py and schemas.py. Verify detailed chart mappings with the backend developer; API.md currently does not define them. No production backend files were fabricated.

Free-form generated prose and Roman Urdu answer prose are not implemented: the model chooses evidence, and the server renders English factual templates. Roman Urdu leave input is covered. Ambiguous day-only dates request clarification. Comparative chart narratives are not generated.

The pre-existing untracked root environment file was left untouched. Its contents were not read. The empty backend/ai directory was preserved; the implementation uses the specified backend/app/ai path.


## Local AI Testing Playground — Python 3.11 verification (25 October 2026)

This section supersedes earlier provider/test-environment status for the local playground. Production backend integration remains absent.

- Interpreter: existing `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11`, **Python 3.11.9**. No interpreter was downloaded/installed for this task. Existing AI dependency versions were retained; installed metadata confirms 3.11 support. Uvicorn/click were added and uv.lock regenerated for >=3.11.
- `uv sync --python 3.11 --no-python-downloads`: succeeded (an initial transient virtual-environment directory-removal error succeeded on retry).
- `uv run --python 3.11 --no-python-downloads python -m pytest -q`: **164 passed, 0 failed, 2 skipped** (final 0.89 s). Existing tests plus 39 playground checks ran. Skips remain the opt-in two-provider live pytest and absent real production JWT/PostgreSQL integration.
- `uv run --python 3.11 --no-python-downloads ruff check app/ai`: passed.
- `uv run --python 3.11 --no-python-downloads ruff format app/ai --check`: 33 Python files already formatted.
- `node --check app/ai/playground/app.js`: passed.
- Local API/HTML/static assets and security headers: HTTP tests passed, including role checks, own scope, foreign origins/hosts, non-loopback clients and POST-token enforcement.
- Live Playwright/Chromium browser checks: real Gemini Sales headcount (3), switching roles clears chat, real sick-leave preview for 26 October 2026 using server date 25 October, real Sales dashboard summary, all three tabs, zero page JavaScript errors, and no horizontal overflow at 375px. Desktop/mobile screenshots were inspected at `/tmp/hcm-playground-desktop.png` and `/tmp/hcm-playground-mobile.png`.
- Real Gemini `gemini-3.1-flash-lite`: success for structured output, LangGraph tool calls, browser chat, smart leave, dashboard summary, policy Q&A, salary non-disclosure under an adversarial employee prompt, Roman Urdu sick leave and Admin payroll. Demo payroll matched fixture source totals (gross 1035000, net 990000, 9 employees).
- Real Alibaba `qwen-plus`: HTTP 403; `qwen-flash`: HTTP 403. No successful Alibaba inference is claimed. The provider denied access; the account-side cause (region/project/model permissions/key/account) was not established. The original local Character model setting was corrected without changing keys, but that did not resolve access denial.
- Shared failover: deterministic Qwen timeout/429/503 -> Gemini tests passed; missing Gemini/both unavailable covered. A separate live smoke check injected a simulated primary timeout and successfully called real Gemini. This is **simulated-primary/live-backup**, not a successful live Alibaba outage test.
- Existing no-fallback-on-401/403 behavior is preserved. Browser direct-Gemini mode allows testing while Alibaba access is repaired; it does not pretend Alibaba succeeded or bypass its denial through automatic retry.
- An intermediate provider-selector edit caused six error-response tests to fail. The development handler was fixed, regression tests were added, and the full final suite passed. No failures were hidden.

### Files for this increment

New: `dev_playground.py`, `dev_data.py`, `dev_adapters.py`, `playground/index.html`, `playground/style.css`, `playground/app.js`, `tests/test_playground.py`.

Modified: backend pyproject.toml and uv.lock (Python >=3.11, Uvicorn); AI README.md and VERIFICATION.md; smart_leave.py (explicit annual-leave wording); root .env.example (development flag). The gitignored root .env had only its nonsecret Qwen model entries corrected. No keys were displayed or copied into browser assets. Prior uncommitted AI implementation and docs/progress.md changes were preserved.

### Run

From backend/: `AI_PLAYGROUND=1 uv run --python 3.11 --no-python-downloads python -m app.ai.dev_playground`.

Open http://127.0.0.1:8765 and choose **Gemini only · direct test** for the currently working provider. Ctrl+C stops the server. The development server was left running for the user after verification.

Remaining limitation: live Qwen requires corrected Alibaba account/model access. Production authentication, PostgreSQL services and durable rate-limit/log callbacks are not implemented by this development playground. Demo in-memory storage is never mounted in production. No commits, staging, pushes, pull requests, merges or remote mutations were performed; current local branch remains ai_agent.


## Current configuration — Gemini only (25 October 2026)

At the user's request, removed the retired provider's client construction, settings, environment entries, dependency and playground selector. The sole configured model is gemini-3.1-flash-lite. langchain-openai and its unused SDK dependencies were uninstalled; uv.lock regenerated. Gemini credentials were preserved and never printed. Earlier multi-provider sections above are historical and no longer describe current configuration.

Python 3.11.9: full routine suite **164 passed, 0 failed, 2 skipped** (0.66 s); the skips are opt-in live pytest and unavailable production JWT/PostgreSQL integration. Lint passed; all 33 Python files pass formatting. Browser JS syntax passed. A separate real HTTP smoke test against the restarted server returned HTTP 200, Sales headcount 3, using get_headcount with three successful Gemini calls, 10466 ms. Status lists only Gemini; HTML has no provider selector. No Qwen/Alibaba/OpenAI-SDK references remain in executable AI source, browser assets, dependency manifest or lockfile.

The Gemini-only development server is running at http://127.0.0.1:8765. Reload an existing browser tab to load updated assets and its new per-process request token. No files staged, no commits, pushes, PRs or remote mutations.
