# AI Agent Plan — HCM Lite

This is the full task list for the AI developer. The AI is worth **15 points**, and judges also check AI security under **Security & RBAC**. They will ask live questions and compare the answers with the dashboard, so correctness matters more than clever wording.

Read **AGENTS.md**, **API.md**, **MODELS.md**, **docs/BACKEND_PLAN.md** (especially Section 13) and **docs/decision.md** before starting.

---

## 1. What the AI developer owns

- Everything inside `backend/app/ai/`
- The three endpoints: `/ai/chat`, `/ai/summary` and `/ai/smart-leave`
- The LangGraph agent and its tools
- Prompts, output validation, timeout, rate limit and logging for AI calls
- The list of live test questions, and checking that the answers are right

**Not yours:** the database, the business rules and the frontend screens. The backend developer gives you service functions; the frontend developer builds the chat panel and smart leave box against your endpoints.

**The one rule that matters most:** the AI explains and assists, but the database is the only source of truth. The model never queries the database, never writes data and never makes up numbers.

---

## 2. Stack

- **LangGraph** for the agent loop
- **Gemini** through `langchain-google-genai` (Groq is the backup if Gemini is slow or rate limited)
- **Pydantic** to validate every JSON output
- Settings from the environment: `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`, `AI_TIMEOUT_SECONDS` (15), `AI_RATE_LIMIT_PER_HOUR` (20)

Use a temperature of 0 for smart leave and tool selection so the answers stay consistent during the demo.

---

## 3. Folder layout

```
backend/app/ai/
  router.py      the three /ai endpoints
  graph.py       the LangGraph agent
  tools.py       the 7 tools, each wrapping a backend service function
  prompts.py     system prompts and the policy rules text
  schemas.py     shapes for requests, responses and model output
  guard.py       rate limit, timeout and logging helpers
  stubs.py       fake service functions for working before the backend is ready
```

---

## 4. Start today with stubs

You don't need to wait for the backend. In `stubs.py`, write fake versions of the 7 service functions that return sample data in the exact shapes from Section 6. Build and test the whole agent against them.

When the backend developer finishes the dashboards and services (their step 8), swap each stub for the real function. Because the shapes match, nothing else changes.

Agree on those shapes with the backend developer **in the first hour** and write them into API.md.

---

## 5. Feature 1 — Chat assistant

**Endpoint:** `POST /ai/chat` · **Who:** Admin, HR, Employee

**Request:** the user's message and, optionally, the last few messages of the conversation (the frontend keeps the history; the server stores none).

**Response:** the answer text, the list of tools that were used, and `ai_generated: true`.

### How it works
1. The endpoint gets the current user (role and employee id) from the backend's auth dependency.
2. It builds the agent with **only the tools that role is allowed to use** (see the table in Section 6). An employee's agent simply doesn't have the HR tools, so it can't misuse them.
3. The model decides which tool to call. The tool calls the backend service with the current user, so the service applies the same scope checks as the REST API.
4. The model writes a short answer using only what the tool returned.
5. Allow at most 3 tool calls per question, to avoid loops.

### What the system prompt must say
- You are the HCM Lite assistant for this company.
- Today's date, the user's role, and their name.
- Answer only from tool results or the policy rules below. If you don't have the data, say so.
- Never guess numbers. Never reveal another employee's salary or personal data to an employee.
- Keep answers short and clear. Use a small list when listing people.
- Reply in the same language the user writes in, including Roman Urdu (bonus).
- The policy rules from Section 8.

---

## 6. The 7 tools

Each tool is a thin wrapper around a backend service function. The tool description matters a lot, because the model reads it to decide which tool to pick, so write each one clearly.

| Tool | What it answers | Inputs | Returns | Roles |
|---|---|---|---|---|
| get_headcount | "How many active employees are in Sales?" | Optional department name | Total and a per-department list | Admin, HR |
| get_attendance_summary | "What is this month's attendance rate?" | Date range, optional department | Present, late, half day, absent, on leave, attendance rate | Admin, HR; an employee gets only their own |
| get_late_comers | "Who came late most often this month?" | Date range, how many to return | Names with late counts, highest first | Admin, HR |
| get_leave_summary | "Who is on leave today?" | Date range, optional department | Names on leave with their leave type, plus counts by type | Admin, HR |
| get_my_leave_balance | "How many sick leaves do I have left?" | None | For each type: quota, used, pending, remaining | Everyone (their own only) |
| get_payroll_summary | "What was the payroll cost last month?" | Month, optional department | Total gross, total net, average salary, employee count | Admin; HR if the team decides so |
| search_employees | "Find Ali in Engineering" | Search text | Name, code, department, designation. **Never salary.** | Admin, HR |

### Dates
Let the model pass words like "today", "this month" or "last month". Convert them to real dates in the tool, using the company time zone (Asia/Karachi). This is more reliable than asking the model to work out dates.

### Department names
The user will type names like "sales" or "Sales team". Match department names without caring about case. If nothing matches, return a helpful message listing the real department names.

---

## 7. Feature 2 — Dashboard summary

**Endpoint:** `POST /ai/summary` · **Who:** Admin, HR

**Request:** the KPI JSON currently shown on the dashboard, with its filters.

**Response:** 3 to 5 short insight bullets.

### Rules
- Use only the numbers in the JSON. No outside knowledge and no invented trends.
- Each bullet should say something useful, such as which department has the highest absenteeism, whether late arrivals are rising, or how many approvals are pending. Avoid simply repeating a number with no meaning.
- Validate that the output is a list of 3 to 5 strings. If not, retry once, then return a simple fallback message.
- If the JSON is mostly empty (a fresh company), return one bullet saying there isn't enough data yet. Judges start from an empty system, so this case will happen.

---

## 8. Feature 3 — Policy Q&A

This doesn't need a separate endpoint; it's part of chat. Put the rules from the brief into the system prompt as plain text:

- Office starts at 09:00 with a 15-minute grace period; late after 09:15
- Half day if less than 5 hours worked
- Weekend is Saturday and Sunday
- Leave quotas: annual 14, sick 8, casual 10, unpaid unlimited; leave counts working days only
- Overlapping leave or leave over the balance is not allowed
- Gross salary is 1.5 × basic (HRA 40%, medical 10%)
- Deductions for absent days, unpaid leave and half of each half day
- The tax slabs
- HR prepares payroll, Admin finalizes it, and finalized payroll is locked

**Better:** build this text from the live settings table, so if Admin changes the office start time the assistant knows it.

If a question isn't covered by these rules, the assistant says it doesn't know and suggests asking HR.

---

## 9. Feature 4 — Smart leave

**Endpoint:** `POST /ai/smart-leave` · **Who:** Employee, HR

**Request:** a sentence, for example "Need next Monday and Tuesday off for my sister's wedding".

**Response:** leave type, start date, end date and reason. This only fills the form; **nothing is saved**. The user checks it and presses Apply, which calls the normal leave endpoint, and the backend applies the real rules.

### How it works
1. Give the model today's date and weekday, the list of leave type codes, and the sentence.
2. Ask for JSON with exactly those four fields.
3. Validate with Pydantic: the type must be a real leave code, the dates must be valid, and the end date can't be before the start date.
4. If validation fails, retry once with the error message. If it fails again, return an error with the code `AI_PARSE_FAILED`, so the frontend opens the normal empty form.

### Choosing the leave type
- Illness, doctor, fever, hospital → **sick**
- Wedding, family event, personal work, travel → **casual**
- Vacation, holiday trip, several planned days → **annual**
- "Unpaid" mentioned → **unpaid**
- Not clear → **casual**

### Dates
- "Next Monday" means the first Monday after today. Today is Saturday 24 October 2026, so it's Monday 26 October.
- "Tomorrow", "day after tomorrow", "this Friday", "from the 3rd to the 5th", "for 3 days starting Monday" should all work.
- "Monday and Tuesday" means one range from Monday to Tuesday.

### The judges' test
"I need next Monday and Tuesday off for my sister's wedding" must return **casual**, **26 Oct 2026 to 27 Oct 2026**, with the reason about the sister's wedding. Test this many times.

---

## 10. Guardrails (judges check every one)

| Guardrail | How |
|---|---|
| API key only on the server | Read from `AI_API_KEY`. The browser only ever calls our backend. |
| Model never touches the database | Tools call service functions; there is no raw SQL anywhere in `ai/` |
| Role and data scope | Each role gets only its allowed tools, and the services check scope again |
| AI never saves data | No tool creates or changes anything. Smart leave only fills a form. |
| Validated JSON | Pydantic checks, one retry, then fall back to the normal form |
| 15-second timeout | If the model takes too long, return a friendly message such as "The assistant is busy right now, please try again or use the dashboard." |
| Rate limit | About 20 AI requests per user per hour. Over the limit, return 429 with a friendly message. Count from the `ai_logs` table so it survives restarts. |
| Logging | Every call writes to `ai_logs`: user, feature, prompt, tools called, response, time taken, success |
| Label | Every response includes `ai_generated: true`, and the frontend shows an "AI-generated" tag |

### Refusing the salary question
When an employee asks "What is Ali's salary?", there are two layers of protection:
1. The employee's agent has no tool that can return someone else's data.
2. The system prompt tells the model to politely say it can only share the user's own information.

The answer should be friendly, for example: "Sorry, I can only share your own salary and payslip details. For anything else, please contact HR."

---

## 11. Live test questions

Keep this list in a file, and run every question as the right role after each change. The numbers must match the dashboard.

**As HR**
- How many active employees are in {department}?
- Who came late most often this month?
- What is this month's attendance rate?
- Who is on leave today?
- How many leave requests are pending?
- Summarize the dashboard

**As Employee**
- How many sick leaves do I have left this year? (balance after approved leaves)
- What is {colleague}'s salary? (politely refuses)
- I need next Monday and Tuesday off for my sister's wedding (casual, correct dates)
- What time do I need to arrive to not be late? (09:15, from policy)
- Mujhe kal chutti chahiye, bukhar hai (bonus: sick leave for tomorrow)

**As Admin**
- What was the total payroll cost last month?
- Which department has the highest headcount?

**Edge cases**
- A question with no data yet (fresh company) gets an honest "no data yet" answer
- A question outside HR, like "What's the weather?", gets a polite redirect
- A wrong API key or the provider being down gives the friendly fallback, not a crash

---

## 12. Order of work

| Order | Work | Depends on |
|---|---|---|
| 1 | Agree on the tool return shapes with the backend developer and write them in API.md | Nothing |
| 2 | Model connection, settings, a simple test call | Nothing |
| 3 | Smart leave with validation and retry | Nothing (needs only leave codes) |
| 4 | Stubs and the chat agent with all 7 tools | Step 1 |
| 5 | Role-based tool lists and the policy prompt | Step 4 |
| 6 | Dashboard summary | Dashboard JSON shape |
| 7 | Timeout, rate limit, logging, fallback messages | Backend `ai_logs` table |
| 8 | Swap stubs for real service functions | Backend step 8 |
| 9 | Run the full test question list against real data | Checkpoint 2 |
| 10 | Roman Urdu bonus | Everything above |

After each step, push a small pull request into `dev` and update **docs/progress.md**.

**Tell the frontend developer early** that smart leave is ready, even with stubs, because the demo script includes it.

---

## 13. Done means

- All three `/ai/*` endpoints work and match API.md
- Every question in Section 11 gives the right answer as the right role
- AI numbers match the dashboard for data created during judging
- An employee can never get another person's data through the assistant
- The key is only in the backend environment, and `.env.example` has an empty placeholder
- Timeout, rate limit, retry and fallback all work, and every call is in `ai_logs`
- Every answer is labelled as AI-generated
