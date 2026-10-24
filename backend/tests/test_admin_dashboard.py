from datetime import date
from decimal import Decimal

from app.core.security import hash_password
from app.models import (
    Department,
    Designation,
    Employee,
    PayrollRun,
    Payslip,
    SalaryStructure,
    User,
)

ADMIN_PASSWORD = "Dashboard-Admin-Pass-2026"


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def setup_admin(client) -> dict[str, str]:
    assert (
        client.post(
            "/api/setup",
            json={
                "company_name": "Dashboard Company",
                "admin_email": "dashboard-admin@example.com",
                "admin_password": ADMIN_PASSWORD,
            },
        ).status_code
        == 201
    )
    login = client.post(
        "/api/auth/login",
        json={
            "email": "dashboard-admin@example.com",
            "password": ADMIN_PASSWORD,
        },
    )
    return bearer(login.json()["access_token"])


def test_admin_dashboard_empty_state_and_date_validation(client):
    headers = setup_admin(client)
    response = client.get(
        "/api/dashboard/admin?from=2026-01-01&to=2026-12-31", headers=headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["headcount"] == 0
    assert body["attrition_ytd"] == 0
    assert body["payroll_cost"] == {"gross": 0.0, "net": 0.0}
    assert body["avg_salary"] is None
    assert body["headcount_by_dept"] == []
    assert body["payroll_cost_by_dept"] == []
    assert body["gender"] == []
    assert body["tenure"] == [
        {"category": "under_1_year", "count": 0},
        {"category": "1_to_3_years", "count": 0},
        {"category": "over_3_years", "count": 0},
    ]
    assert len(body["recent_audit"]) > 0
    assert (
        client.get(
            "/api/dashboard/admin?from=2026-12-31&to=2026-01-01",
            headers=headers,
        ).status_code
        == 422
    )
    assert (
        client.get(
            "/api/dashboard/admin?department_id=99999", headers=headers
        ).status_code
        == 404
    )


def seed_dashboard_data(db_factory) -> tuple[int, int]:
    with db_factory() as session:
        admin = session.query(User).filter_by(role="admin").one()
        engineering = Department(name="Engineering")
        people = Department(name="People")
        engineer = Designation(name="Engineer", department=engineering)
        partner = Designation(name="Partner", department=people)
        session.add_all([engineering, people, engineer, partner])
        session.flush()
        active = Employee(
            employee_code="DASH-1",
            first_name="Active",
            last_name="Engineer",
            email="active@example.com",
            phone="03000000001",
            gender="male",
            department_id=engineering.id,
            designation_id=engineer.id,
            join_date=date(2026, 1, 1),
            status="active",
        )
        probation = Employee(
            employee_code="DASH-2",
            first_name="Senior",
            last_name="Partner",
            email="senior@example.com",
            phone="03000000002",
            gender="female",
            department_id=people.id,
            designation_id=partner.id,
            join_date=date(2022, 1, 1),
            status="probation",
        )
        exited = Employee(
            employee_code="DASH-3",
            first_name="Former",
            last_name="Engineer",
            email="former@example.com",
            phone="03000000003",
            gender="other",
            department_id=engineering.id,
            designation_id=engineer.id,
            join_date=date(2024, 1, 1),
            exit_date=date(2026, 6, 30),
            status="exited",
        )
        session.add_all([active, probation, exited])
        session.flush()
        session.add_all(
            [
                SalaryStructure(
                    employee_id=active.id,
                    basic=Decimal("100.00"),
                    hra=Decimal("40.00"),
                    medical=Decimal("10.00"),
                    effective_from=date(2026, 1, 1),
                ),
                SalaryStructure(
                    employee_id=probation.id,
                    basic=Decimal("200.00"),
                    hra=Decimal("80.00"),
                    medical=Decimal("20.00"),
                    effective_from=date(2022, 1, 1),
                ),
                SalaryStructure(
                    employee_id=exited.id,
                    basic=Decimal("300.00"),
                    hra=Decimal("120.00"),
                    medical=Decimal("30.00"),
                    effective_from=date(2024, 1, 1),
                ),
            ]
        )
        run = PayrollRun(
            month="2026-10",
            status="finalized",
            created_by=admin.id,
            finalized_by=admin.id,
            total_gross=Decimal("450.00"),
            total_net=Decimal("420.00"),
        )
        session.add(run)
        session.flush()
        session.add_all(
            [
                Payslip(
                    run_id=run.id,
                    employee_id=active.id,
                    basic=Decimal("100.00"),
                    hra=Decimal("40.00"),
                    medical=Decimal("10.00"),
                    gross=Decimal("150.00"),
                    working_days=20,
                    paid_days=Decimal("20.00"),
                    absent_days=Decimal("0.00"),
                    unpaid_days=Decimal("0.00"),
                    half_days=Decimal("0.00"),
                    deduction=Decimal("0.00"),
                    tax=Decimal("10.00"),
                    net=Decimal("140.00"),
                ),
                Payslip(
                    run_id=run.id,
                    employee_id=probation.id,
                    basic=Decimal("200.00"),
                    hra=Decimal("80.00"),
                    medical=Decimal("20.00"),
                    gross=Decimal("300.00"),
                    working_days=20,
                    paid_days=Decimal("20.00"),
                    absent_days=Decimal("0.00"),
                    unpaid_days=Decimal("0.00"),
                    half_days=Decimal("0.00"),
                    deduction=Decimal("0.00"),
                    tax=Decimal("20.00"),
                    net=Decimal("280.00"),
                ),
            ]
        )
        session.commit()
        return engineering.id, people.id


def test_admin_dashboard_aggregates_and_department_filter(client, db_factory):
    headers = setup_admin(client)
    engineering_id, _ = seed_dashboard_data(db_factory)
    response = client.get(
        "/api/dashboard/admin?from=2026-01-01&to=2026-12-31", headers=headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["headcount"] == 2
    assert body["attrition_ytd"] == 40.0
    assert body["payroll_cost"] == {"gross": 450.0, "net": 420.0}
    assert body["avg_salary"] == 225.0
    assert {
        item["department"]: item["headcount"] for item in body["headcount_by_dept"]
    } == {
        "Engineering": 1,
        "People": 1,
    }
    assert {item["category"]: item["count"] for item in body["gender"]} == {
        "female": 1,
        "male": 1,
    }
    assert {item["category"]: item["count"] for item in body["tenure"]} == {
        "under_1_year": 1,
        "1_to_3_years": 0,
        "over_3_years": 1,
    }
    assert len(body["payroll_cost_by_dept"]) == 2

    filtered = client.get(
        f"/api/dashboard/admin?from=2026-01-01&to=2026-12-31&department_id={engineering_id}",
        headers=headers,
    )
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["headcount"] == 1
    assert filtered_body["avg_salary"] == 150.0
    assert filtered_body["payroll_cost"] == {"gross": 150.0, "net": 140.0}
    assert len(filtered_body["headcount_by_dept"]) == 1
    assert filtered_body["headcount_by_dept"][0]["department_id"] == engineering_id


def test_admin_dashboard_excludes_draft_and_out_of_range_payroll(client, db_factory):
    headers = setup_admin(client)
    seed_dashboard_data(db_factory)
    with db_factory() as session:
        admin = session.query(User).filter_by(role="admin").one()
        employee = session.query(Employee).filter_by(employee_code="DASH-1").one()
        draft = PayrollRun(month="2026-11", status="draft", created_by=admin.id)
        old = PayrollRun(
            month="2025-12",
            status="finalized",
            created_by=admin.id,
            finalized_by=admin.id,
        )
        session.add_all([draft, old])
        session.flush()
        for run in (draft, old):
            session.add(
                Payslip(
                    run_id=run.id,
                    employee_id=employee.id,
                    basic=Decimal("100.00"),
                    hra=Decimal("40.00"),
                    medical=Decimal("10.00"),
                    gross=Decimal("999.00"),
                    working_days=20,
                    paid_days=Decimal("20.00"),
                    absent_days=Decimal("0.00"),
                    unpaid_days=Decimal("0.00"),
                    half_days=Decimal("0.00"),
                    deduction=Decimal("0.00"),
                    tax=Decimal("0.00"),
                    net=Decimal("999.00"),
                )
            )
        session.commit()
    response = client.get(
        "/api/dashboard/admin?from=2026-01-01&to=2026-12-31", headers=headers
    )
    assert response.status_code == 200
    assert response.json()["payroll_cost"] == {"gross": 450.0, "net": 420.0}


def test_admin_dashboard_rejects_non_admin_roles(client, db_factory):
    setup_admin(client)
    with db_factory() as session:
        session.add(
            User(
                email="dashboard-hr@example.com",
                password_hash=hash_password("Dashboard-HR-Pass-2026"),
                role="hr",
                must_change_password=False,
            )
        )
        session.commit()
    login = client.post(
        "/api/auth/login",
        json={
            "email": "dashboard-hr@example.com",
            "password": "Dashboard-HR-Pass-2026",
        },
    )
    assert (
        client.get(
            "/api/dashboard/admin", headers=bearer(login.json()["access_token"])
        ).status_code
        == 403
    )
