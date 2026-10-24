"""Fictional deterministic records, imported only by the explicit local playground."""

from dataclasses import dataclass
from datetime import date, timedelta

DEPARTMENTS = ("Engineering", "Sales", "Human Resources", "Marketing", "Finance")


@dataclass(frozen=True)
class DemoEmployee:
    id: int
    name: str
    department: str
    designation: str
    gross: int


EMPLOYEES = (
    DemoEmployee(1, "Amina Noor", "Engineering", "Engineer", 150000),
    DemoEmployee(2, "Bilal Farooq", "Engineering", "QA Engineer", 120000),
    DemoEmployee(3, "Sara Naveed", "Engineering", "Designer", 135000),
    DemoEmployee(4, "Hamza Rauf", "Sales", "Sales Lead", 105000),
    DemoEmployee(5, "Zoya Ahmed", "Sales", "Sales Associate", 90000),
    DemoEmployee(6, "Omar Shah", "Sales", "Sales Associate", 85000),
    DemoEmployee(7, "Hina Malik", "Human Resources", "HR Manager", 125000),
    DemoEmployee(8, "Daniyal Ali", "Marketing", "Marketer", 95000),
    DemoEmployee(9, "Maira Khan", "Finance", "Accountant", 130000),
)


@dataclass(frozen=True)
class DemoAttendance:
    employee_id: int
    day: date
    status: str


@dataclass(frozen=True)
class DemoLeave:
    employee_id: int
    start_date: date
    end_date: date
    leave_type: str
    days: int
    status: str = "approved"


@dataclass(frozen=True)
class DemoPayslip:
    employee_id: int
    month: str
    gross: int
    net: int


class DemoData:
    def __init__(self, today: date):
        self.today = today
        self.employees = EMPLOYEES
        self.leaves = (
            DemoLeave(5, today, today, "casual", 1),
            DemoLeave(
                1, today - timedelta(days=10), today - timedelta(days=10), "sick", 1
            ),
            DemoLeave(
                2,
                today + timedelta(days=2),
                today + timedelta(days=2),
                "annual",
                1,
                "pending",
            ),
        )
        # Demo attendance uses actual weekdays in current and previous calendar months.
        start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        rows = []
        day = start
        while day <= today:
            if day.weekday() < 5:
                for e in self.employees:
                    on_leave = any(
                        l.employee_id == e.id
                        and l.start_date <= day <= l.end_date
                        and l.status == "approved"
                        for l in self.leaves
                    )
                    marker = (day.toordinal() + e.id) % 17
                    status = (
                        "on_leave"
                        if on_leave
                        else (
                            "absent"
                            if marker == 0
                            else "half_day"
                            if marker == 1
                            else "late"
                            if marker % 4 == 0
                            else "present"
                        )
                    )
                    rows.append(DemoAttendance(e.id, day, status))
            day += timedelta(days=1)
        self.attendance = tuple(rows)
        previous = (today.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
        self.payslips = tuple(
            DemoPayslip(e.id, m, e.gross, e.gross - 5000)
            for e in self.employees
            for m in (previous, today.strftime("%Y-%m"))
        )
