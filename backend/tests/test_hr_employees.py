import io

from sqlalchemy import func, select

from app.models import AuditLog, Employee, SalaryStructure, User


def employee_payload(context, **overrides):
    payload = {
        "employee_code": "EMP-002",
        "first_name": "Second",
        "last_name": "Employee",
        "email": "employee2@example.com",
        "phone": "03000000001",
        "gender": "female",
        "department_id": context["department_id"],
        "designation_id": context["designation_id"],
        "join_date": "2026-01-01",
        "basic_salary": "123456.78",
    }
    payload.update(overrides)
    return payload


def test_employee_registration_listing_360_salary_and_scope(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    employee_id = context["employee"]["id"]
    salary = client.get(
        f"/api/employees/{employee_id}/salary", headers=context["hr_headers"]
    )
    assert salary.status_code == 200
    assert salary.json() == {
        "employee_id": employee_id,
        "basic": 100000.0,
        "hra": 40000.0,
        "medical": 10000.0,
        "gross": 150000.0,
        "effective_from": "2026-01-01",
    }
    listing = client.get(
        "/api/employees?search=EMP-001&status=probation",
        headers=context["hr_headers"],
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    profile = client.get(
        f"/api/employees/{employee_id}", headers=context["employee_headers"]
    )
    assert profile.status_code == 200, profile.text
    assert profile.json()["employee"]["employee_code"] == "EMP-001"
    assert profile.json()["salary"]["gross"] == 150000.0
    assert (
        client.get(
            "/api/employees/99999", headers=context["employee_headers"]
        ).status_code
        == 403
    )
    assert (
        client.get(
            f"/api/employees/{employee_id}/salary", headers=context["employee_headers"]
        ).status_code
        == 403
    )

    update = client.patch(
        "/api/employees/me",
        headers=context["employee_headers"],
        json={"phone": "03111111111", "address": "Updated address"},
    )
    assert update.status_code == 200
    assert update.json()["phone"] == "03111111111"
    assert (
        client.patch(
            "/api/employees/me",
            headers=context["employee_headers"],
            json={"status": "active"},
        ).status_code
        == 422
    )
    assert (
        client.patch(
            "/api/employees/me",
            headers=context["employee_headers"],
            json={"phone": "   "},
        ).status_code
        == 422
    )

    revised = client.put(
        f"/api/employees/{employee_id}/salary",
        headers=context["hr_headers"],
        json={"basic": "123456.78"},
    )
    assert revised.status_code == 200
    assert revised.json()["hra"] == 49382.71
    assert revised.json()["medical"] == 12345.68
    assert revised.json()["gross"] == 185185.17
    with db_factory() as session:
        assert (
            session.scalar(
                select(func.count(AuditLog.id)).where(
                    AuditLog.entity == "salary_structures"
                )
            )
            == 2
        )
        assert (
            session.scalar(select(func.count(User.id)).where(User.role == "employee"))
            == 1
        )


def test_employee_registration_validation_atomicity_and_exit_deactivation(
    client, phase2_employee, db_factory
):
    context = phase2_employee
    duplicate = client.post(
        "/api/employees",
        headers=context["hr_headers"],
        json=employee_payload(context, employee_code="EMP-001"),
    )
    assert duplicate.status_code == 409
    invalid_salary = client.post(
        "/api/employees",
        headers=context["hr_headers"],
        json=employee_payload(context, employee_code="EMP-003", basic_salary=0),
    )
    assert invalid_salary.status_code == 422
    invalid_reference = client.post(
        "/api/employees",
        headers=context["hr_headers"],
        json=employee_payload(context, employee_code="EMP-004", department_id=99999),
    )
    assert invalid_reference.status_code == 404
    with db_factory() as session:
        assert session.scalar(select(func.count(Employee.id))) == 1
        assert session.scalar(select(func.count(SalaryStructure.id))) == 1

    employee_id = context["employee"]["id"]
    invalid_exit = client.patch(
        f"/api/employees/{employee_id}",
        headers=context["hr_headers"],
        json={"status": "exited", "exit_date": "2025-12-31"},
    )
    assert invalid_exit.status_code == 422
    assert invalid_exit.json()["detail"]["code"] == "INVALID_EXIT_DATE"
    exited = client.patch(
        f"/api/employees/{employee_id}",
        headers=context["hr_headers"],
        json={"status": "exited", "exit_date": "2026-10-01"},
    )
    assert exited.status_code == 200
    assert exited.json()["status"] == "exited"
    assert (
        client.get("/api/auth/me", headers=context["employee_headers"]).status_code
        == 401
    )


def test_csv_dry_run_import_export_and_sensitive_field_exclusion(
    client, phase2_context
):
    context = phase2_context
    csv_text = (
        "employee_code,first_name,last_name,email,phone,gender,department,designation,join_date,basic_salary\n"
        "CSV-001,CSV,Employee,csv1@example.com,03000000002,male,Engineering,Software Engineer,2026-01-01,80000\n"
        "CSV-001,Duplicate,Employee,csv2@example.com,03000000003,female,Engineering,Software Engineer,2026-01-01,90000\n"
    )
    dry_run = client.post(
        "/api/employees/import?dry_run=true",
        headers=context["hr_headers"],
        files={"file": ("employees.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert len(dry_run.json()["valid_rows"]) == 1
    assert dry_run.json()["errors"][0]["row"] == 3
    assert dry_run.json()["created"] == []

    actual = client.post(
        "/api/employees/import?dry_run=false",
        headers=context["hr_headers"],
        files={"file": ("employees.csv", io.BytesIO(csv_text.encode()), "text/csv")},
    )
    assert actual.status_code == 200, actual.text
    assert len(actual.json()["created"]) == 1
    assert actual.json()["created"][0]["temp_password"]
    exported = client.get("/api/employees/export", headers=context["hr_headers"])
    assert exported.status_code == 200
    assert exported.headers["content-type"].startswith("text/csv")
    assert "CSV-001" in exported.text
    assert "password" not in exported.text.lower()


def test_csv_rejects_bad_headers_encoding_and_oversize(client, phase2_context):
    headers = phase2_context["hr_headers"]
    bad_headers = client.post(
        "/api/employees/import",
        headers=headers,
        files={"file": ("bad.csv", b"name,email\nA,a@example.com\n", "text/csv")},
    )
    assert bad_headers.status_code == 422
    bad_utf8 = client.post(
        "/api/employees/import",
        headers=headers,
        files={"file": ("bad.csv", b"\xff\xfe\x00", "text/csv")},
    )
    assert bad_utf8.status_code == 422
    oversized = client.post(
        "/api/employees/import",
        headers=headers,
        files={"file": ("large.csv", b"x" * (2 * 1024 * 1024 + 1), "text/csv")},
    )
    assert oversized.status_code == 422
