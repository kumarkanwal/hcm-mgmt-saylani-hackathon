from app.main import app

REQUIRED_NON_AI_ENDPOINTS = {
    "/api/setup/status": {"get"},
    "/api/setup": {"post"},
    "/api/auth/login": {"post"},
    "/api/auth/change-password": {"post"},
    "/api/auth/me": {"get"},
    "/api/settings": {"get", "put"},
    "/api/departments": {"get", "post"},
    "/api/departments/{department_id}": {"put", "delete"},
    "/api/designations": {"get", "post"},
    "/api/leave-types": {"get", "post"},
    "/api/leave-types/{leave_type_id}": {"put"},
    "/api/holidays": {"get", "post"},
    "/api/holidays/{holiday_id}": {"delete"},
    "/api/users": {"get", "post"},
    "/api/users/{user_id}/deactivate": {"patch"},
    "/api/users/{user_id}/reset-password": {"post"},
    "/api/employees": {"get", "post"},
    "/api/employees/{employee_id}": {"get", "patch"},
    "/api/employees/me": {"patch"},
    "/api/employees/import": {"post"},
    "/api/employees/export": {"get"},
    "/api/employees/{employee_id}/salary": {"get", "put"},
    "/api/attendance/check-in": {"post"},
    "/api/attendance/check-out": {"post"},
    "/api/attendance/today": {"get"},
    "/api/attendance/me": {"get"},
    "/api/attendance/board": {"get"},
    "/api/attendance": {"get"},
    "/api/attendance/corrections": {"get", "post"},
    "/api/attendance/corrections/{correction_id}": {"patch"},
    "/api/leaves/balance": {"get"},
    "/api/leaves": {"get", "post"},
    "/api/leaves/{leave_id}/cancel": {"post"},
    "/api/leaves/me": {"get"},
    "/api/leaves/{leave_id}/decision": {"patch"},
    "/api/payroll/runs": {"get", "post"},
    "/api/payroll/runs/{run_id}": {"get"},
    "/api/payroll/runs/{run_id}/recalculate": {"post"},
    "/api/payroll/runs/{run_id}/finalize": {"post"},
    "/api/payslips/me": {"get"},
    "/api/payslips/{payslip_id}/pdf": {"get"},
    "/api/dashboard/admin": {"get"},
    "/api/dashboard/hr": {"get"},
    "/api/dashboard/me": {"get"},
    "/api/announcements": {"get", "post"},
    "/api/notifications": {"get"},
    "/api/notifications/{notification_id}/read": {"patch"},
    "/api/audit-logs": {"get"},
}


def test_every_documented_non_ai_endpoint_is_registered():
    paths = app.openapi()["paths"]
    for path, methods in REQUIRED_NON_AI_ENDPOINTS.items():
        assert path in paths, f"Missing API path: {path}"
        registered = {method for method in paths[path] if method in methods}
        assert registered == methods, f"Method mismatch for {path}"


def test_new_phase3_endpoints_are_authenticated_in_openapi():
    paths = app.openapi()["paths"]
    for path, method in (
        ("/api/dashboard/me", "get"),
        ("/api/announcements", "get"),
        ("/api/announcements", "post"),
        ("/api/notifications", "get"),
        ("/api/notifications/{notification_id}/read", "patch"),
    ):
        assert paths[path][method]["security"]
