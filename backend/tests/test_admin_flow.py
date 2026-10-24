def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_complete_admin_end_to_end_flow(client):
    assert client.get("/api/setup/status").json() == {"is_setup_done": False}
    setup = client.post(
        "/api/setup",
        json={
            "company_name": "End-to-End Company",
            "admin_email": "owner@e2e.example",
            "admin_password": "End-to-End-Admin-2026",
        },
    )
    assert setup.status_code == 201
    admin_login = client.post(
        "/api/auth/login",
        json={
            "email": "owner@e2e.example",
            "password": "End-to-End-Admin-2026",
        },
    )
    admin_headers = bearer(admin_login.json()["access_token"])
    assert client.get("/api/auth/me", headers=admin_headers).status_code == 200

    settings = client.get("/api/settings", headers=admin_headers).json()
    settings.update(
        {
            "company_name": "End-to-End Updated",
            "office_start": "08:45:00",
            "office_lat": 24.8607,
            "office_lng": 67.0011,
        }
    )
    assert (
        client.put("/api/settings", headers=admin_headers, json=settings).status_code
        == 200
    )

    department = client.post(
        "/api/departments", headers=admin_headers, json={"name": "People"}
    )
    assert department.status_code == 201
    designation = client.post(
        "/api/designations",
        headers=admin_headers,
        json={
            "name": "HR Manager",
            "department_id": department.json()["id"],
        },
    )
    assert designation.status_code == 201
    assert (
        client.post(
            "/api/holidays",
            headers=admin_headers,
            json={"date": "2026-12-25", "name": "Public Holiday"},
        ).status_code
        == 201
    )

    hr_created = client.post(
        "/api/users",
        headers=admin_headers,
        json={"email": "hr@e2e.example"},
    )
    assert hr_created.status_code == 201
    hr_id = hr_created.json()["user"]["id"]
    first_temp_password = hr_created.json()["temp_password"]
    assert first_temp_password
    hr_login = client.post(
        "/api/auth/login",
        json={"email": "hr@e2e.example", "password": first_temp_password},
    )
    hr_headers = bearer(hr_login.json()["access_token"])
    assert hr_login.json()["user"]["must_change_password"] is True
    assert client.get("/api/departments", headers=hr_headers).status_code == 403
    assert (
        client.post(
            "/api/auth/change-password",
            headers=hr_headers,
            json={
                "old_password": first_temp_password,
                "new_password": "End-to-End-HR-Permanent-2026",
            },
        ).status_code
        == 200
    )
    assert client.get("/api/auth/me", headers=hr_headers).status_code == 401
    hr_login = client.post(
        "/api/auth/login",
        json={
            "email": "hr@e2e.example",
            "password": "End-to-End-HR-Permanent-2026",
        },
    )
    hr_headers = bearer(hr_login.json()["access_token"])
    assert client.get("/api/departments", headers=hr_headers).status_code == 200
    assert client.get("/api/audit-logs", headers=hr_headers).status_code == 403
    assert client.get("/api/dashboard/admin", headers=hr_headers).status_code == 403

    reset = client.post(f"/api/users/{hr_id}/reset-password", headers=admin_headers)
    assert reset.status_code == 200
    reset_password = reset.json()["temp_password"]
    assert client.get("/api/auth/me", headers=hr_headers).status_code == 401
    reset_login = client.post(
        "/api/auth/login",
        json={"email": "hr@e2e.example", "password": reset_password},
    )
    reset_headers = bearer(reset_login.json()["access_token"])
    assert client.get("/api/auth/me", headers=reset_headers).status_code == 200

    deactivated = client.patch(f"/api/users/{hr_id}/deactivate", headers=admin_headers)
    assert deactivated.status_code == 200
    assert client.get("/api/auth/me", headers=reset_headers).status_code == 401

    audit = client.get("/api/audit-logs?page_size=100", headers=admin_headers)
    assert audit.status_code == 200
    actions = {item["action"] for item in audit.json()["items"]}
    assert {"create", "update", "login", "reset", "deactivate"}.issubset(actions)
    assert first_temp_password not in audit.text
    assert reset_password not in audit.text

    dashboard = client.get(
        "/api/dashboard/admin?from=2026-01-01&to=2026-12-31",
        headers=admin_headers,
    )
    assert dashboard.status_code == 200
    assert dashboard.json()["headcount"] == 0
    assert dashboard.json()["payroll_cost"] == {"gross": 0.0, "net": 0.0}
    assert client.get("/api/setup/status").json() == {"is_setup_done": True}
