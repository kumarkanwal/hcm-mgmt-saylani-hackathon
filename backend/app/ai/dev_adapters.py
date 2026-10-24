"""Development-only service fixtures and ephemeral operational state. Never production bindings."""

import asyncio
import time
from collections import Counter, deque
from contextvars import ContextVar
from uuid import uuid4

from .dev_data import DEPARTMENTS, DemoData
from .exceptions import AIError
from .policy import Policy
from .schemas import KPIContext, User

IDENTITIES = {
    "admin": User(id=9001, role="admin", employee_id=9),
    "hr": User(id=9002, role="hr", employee_id=7),
    "employee": User(id=9003, role="employee", employee_id=1),
}
CURRENT_RECORD: ContextVar[dict | None] = ContextVar(
    "playground_request_record", default=None
)


class DemoBackend:
    def __init__(self, data: DemoData, scenario="normal"):
        self.data = data
        self.scenario = scenario

    def identity(self, user):
        expected = IDENTITIES.get(user.role)
        if expected is None or user != expected:
            raise AIError("AI_FORBIDDEN", "Unknown demo identity.", 403)

    def employees(self, user, department=None):
        self.identity(user)
        rows = [] if self.scenario == "empty" else list(self.data.employees)
        if department:
            match = next(
                (d for d in DEPARTMENTS if d.casefold() == department.casefold()), None
            )
            if not match:
                raise AIError("AI_INVALID_REQUEST", "Unknown department.", 422)
            rows = [e for e in rows if e.department == match]
        if user.role == "employee":
            rows = [e for e in rows if e.id == user.employee_id]
        return rows

    async def departments(self, user):
        self.identity(user)
        if user.role == "employee":
            raise AIError("AI_FORBIDDEN", "Directory is restricted.", 403)
        return list(DEPARTMENTS)

    async def policy(self, user):
        self.identity(user)
        return Policy().model_dump(mode="json")

    async def read(self, name, user, args):
        self.identity(user)
        own = {"get_my_leave_balance", "get_attendance_summary"}
        if user.role == "employee" and name not in own:
            raise AIError("AI_FORBIDDEN", "Only your own records are available.", 403)
        if name == "get_payroll_summary" and user.role != "admin":
            raise AIError("AI_FORBIDDEN", "Payroll totals require Admin.", 403)
        if "employee_id" in args or (
            user.role == "employee" and args.get("department")
        ):
            raise AIError(
                "AI_FORBIDDEN", "Identity and data scope cannot be changed.", 403
            )
        employees = self.employees(user, args.get("department"))
        ids = {e.id for e in employees}
        if name == "get_headcount":
            counts = Counter(e.department for e in employees)
            return {
                "total": len(employees),
                "departments": [
                    {"department": d, "count": n} for d, n in sorted(counts.items())
                ],
            }
        if name in {"get_attendance_summary", "get_late_comers", "get_leave_summary"}:
            start, end = args["start_date"], args["end_date"]
            rows = [
                r
                for r in self.data.attendance
                if r.employee_id in ids and start <= r.day <= end
            ]
            counts = Counter(r.status for r in rows)
            if name == "get_attendance_summary":
                denominator = len(rows) - counts["on_leave"]
                numerator = (
                    counts["present"] + counts["late"] + 0.5 * counts["half_day"]
                )
                return {
                    **{
                        k: counts[k]
                        for k in ("present", "late", "half_day", "absent", "on_leave")
                    },
                    "attendance_rate": round(100 * numerator / denominator, 2)
                    if denominator
                    else 0,
                }
            if name == "get_late_comers":
                late = Counter(r.employee_id for r in rows if r.status == "late")
                names = {e.id: e.name for e in employees}
                return {
                    "employees": [
                        {"name": names[i], "late_count": n}
                        for i, n in sorted(
                            late.items(), key=lambda pair: (-pair[1], pair[0])
                        )[: args.get("limit", 5)]
                    ]
                }
            leaves = [
                l
                for l in self.data.leaves
                if l.employee_id in ids
                and l.status == "approved"
                and l.start_date <= end
                and l.end_date >= start
            ]
            names = {e.id: e.name for e in employees}
            return {
                "employees": [
                    {"name": names[l.employee_id], "leave_type": l.leave_type}
                    for l in leaves
                ],
                "counts": dict(Counter(l.leave_type for l in leaves)),
            }
        if name == "get_my_leave_balance":
            if user.employee_id is None:
                raise AIError("AI_FORBIDDEN", "No linked demo employee.", 403)
            leaves = [
                l
                for l in self.data.leaves
                if l.employee_id == user.employee_id
                and l.start_date.year == self.data.today.year
            ]
            result = []
            for code, quota in Policy().leave_quotas.items():
                used = sum(
                    l.days
                    for l in leaves
                    if l.leave_type == code and l.status == "approved"
                )
                pending = sum(
                    l.days
                    for l in leaves
                    if l.leave_type == code and l.status == "pending"
                )
                result.append(
                    {
                        "leave_type": code,
                        "quota": quota,
                        "used": used,
                        "pending": pending,
                        "remaining": None if quota is None else quota - used - pending,
                    }
                )
            return {"balances": result}
        if name == "get_payroll_summary":
            rows = [
                r
                for r in self.data.payslips
                if r.employee_id in ids and r.month == args["month"]
            ]
            gross = sum(r.gross for r in rows)
            return {
                "total_gross": gross,
                "total_net": sum(r.net for r in rows),
                "average_salary": gross / len(rows) if rows else 0,
                "employee_count": len(rows),
            }
        if name == "search_employees":
            query = args["text"].casefold()
            return {
                "employees": [
                    {
                        "name": e.name,
                        "employee_code": f"DEMO-{e.id:03d}",
                        "department": e.department,
                        "designation": e.designation,
                    }
                    for e in employees
                    if query
                    in f"{e.name} {e.department} {e.designation} DEMO-{e.id:03d}".casefold()
                ]
            }
        raise AIError("AI_FORBIDDEN", "Unknown read operation.", 403)

    async def dashboard(self, user, context: KPIContext):
        self.identity(user)
        if user.role == "employee":
            raise AIError("AI_FORBIDDEN", "Company dashboard is restricted.", 403)
        employees = self.employees(user, context.department)
        if self.scenario == "insufficient":
            return {
                "headcount": len(employees),
                "context": context.model_dump(mode="json"),
            }
        start = context.start_date or self.data.today.replace(day=1)
        end = context.end_date or self.data.today
        args = {"start_date": start, "end_date": end}
        if context.department:
            args["department"] = context.department
        head = await self.read(
            "get_headcount", user, {"department": context.department}
        )
        today_rows = Counter(
            r.status
            for r in self.data.attendance
            if r.employee_id in {e.id for e in employees} and r.day == self.data.today
        )
        leave = await self.read(
            "get_leave_summary",
            user,
            {**args, "start_date": self.data.today, "end_date": self.data.today},
        )
        data = {
            "headcount": head["total"],
            "headcount_by_dept": head["departments"],
            "present_today": today_rows["present"]
            + today_rows["late"]
            + today_rows["half_day"],
            "late_today": today_rows["late"],
            "on_leave_today": len(leave["employees"]),
            "pending_approvals": sum(
                l.status == "pending" and l.employee_id in {e.id for e in employees}
                for l in self.data.leaves
            ),
            "context": context.model_dump(mode="json"),
        }
        if user.role == "admin":
            pay = await self.read(
                "get_payroll_summary",
                user,
                {"month": end.strftime("%Y-%m"), "department": context.department},
            )
            data.update(
                payroll_cost=pay["total_gross"], avg_salary=pay["average_salary"]
            )
        return data


class DemoOperations:
    """Ephemeral, bounded, per-process state, exclusively for this loopback playground."""

    def __init__(self):
        self.lock = asyncio.Lock()
        self.reservations = {}
        self.logs = deque(maxlen=100)

    async def reserve(self, user, feature, limit):
        async with self.lock:
            now = time.monotonic()
            q = self.reservations.setdefault(user.id, deque())
            while q and q[0] <= now - 3600:
                q.popleft()
            if len(q) >= limit:
                raise AIError(
                    "AI_RATE_LIMIT",
                    "Demo hourly limit reached. Wait or restart the playground.",
                    429,
                )
            q.append(now)
            return uuid4().hex

    async def complete(self, request_id, record):
        safe = {
            "attempts": record["attempts"],
            "tools_used": record["tools_called"],
            "latency_ms": record["latency_ms"],
            "success": record["success"],
        }
        self.logs.append(safe)
        current = CURRENT_RECORD.get()
        if current is not None:
            current.update(safe)
