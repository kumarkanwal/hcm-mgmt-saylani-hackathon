
## AI module — 25 October 2026 (local ai_agent branch)

Implemented backend/app/ai: LangGraph chat, seven read-only scoped tool wrappers, authoritative policy/summary interfaces, smart leave prefill, Qwen primary with Gemini fallback, guarded routes, deadlines, validation and safe operational logging/rate-limit contracts. Added dependency manifest/lock, nonsecret environment examples and AI integration documentation.

Verified with Python 3.12.15: 125 tests passed, 2 skipped, 0 failed. Lint and formatting checks passed. Skips: real JWT/PostgreSQL integration (backend absent) and opt-in live provider checks (credentials unavailable in process environment). Fixture-based tests are not real database/provider integration.

Pending backend-owned bindings: current_user; seven services; department/policy/dashboard projections; atomic durable ai_logs rate reservations and completion. Live Qwen/Gemini model availability and multi-worker rate-limit atomicity remain unverified. See backend/app/ai/README.md and VERIFICATION.md. All changes remain local and uncommitted; nothing staged, committed, pushed, merged or published.
