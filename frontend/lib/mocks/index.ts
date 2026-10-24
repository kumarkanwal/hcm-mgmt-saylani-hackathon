import type { Department, Designation, Employee, ListResponse, LoginResponse, Role, User } from "@/lib/types";

const departments: Department[] = [
  { id: "dept-1", name: "Operations" },
  { id: "dept-2", name: "Sales" },
  { id: "dept-3", name: "IT" },
  { id: "dept-4", name: "Finance" },
  { id: "dept-5", name: "HR" },
  { id: "dept-6", name: "Marketing" },
];

const designations: Designation[] = [
  { id: "des-1", name: "Operations Executive", department_id: "dept-1", department_name: "Operations" },
  { id: "des-2", name: "Sales Executive", department_id: "dept-2", department_name: "Sales" },
  { id: "des-3", name: "Software Engineer", department_id: "dept-3", department_name: "IT" },
  { id: "des-4", name: "Accounts Officer", department_id: "dept-4", department_name: "Finance" },
  { id: "des-5", name: "HR Officer", department_id: "dept-5", department_name: "HR" },
  { id: "des-6", name: "Marketing Executive", department_id: "dept-6", department_name: "Marketing" },
];

const employees: Employee[] = [
  ["emp-1", "EMP001", "Ali", "Raza", "ali.raza@company.pk", "Operations", "Operations Executive", "active", "2024-01-12", "male"],
  ["emp-2", "EMP002", "Sarah", "Khan", "sarah.khan@company.pk", "HR", "HR Officer", "active", "2024-03-05", "female"],
  ["emp-3", "EMP003", "Umair", "Sheikh", "umair.sheikh@company.pk", "IT", "Software Engineer", "probation", "2026-08-18", "male"],
  ["emp-4", "EMP004", "Ayesha", "Malik", "ayesha.malik@company.pk", "Finance", "Accounts Officer", "active", "2024-02-25", "female"],
  ["emp-5", "EMP005", "Bilal", "Ahmed", "bilal.ahmed@company.pk", "Sales", "Sales Executive", "active", "2024-04-10", "male"],
  ["emp-6", "EMP006", "Fatima", "Noor", "fatima.noor@company.pk", "Marketing", "Marketing Executive", "probation", "2026-09-01", "female"],
  ["emp-7", "EMP007", "Hassan", "Zaidi", "hassan.zaidi@company.pk", "IT", "System Administrator", "active", "2023-11-14", "male"],
  ["emp-8", "EMP008", "Nimra", "Zafar", "nimra.zafar@company.pk", "HR", "Recruitment Officer", "active", "2024-05-22", "female"],
  ["emp-9", "EMP009", "Taha", "Khan", "taha.khan@company.pk", "Operations", "Team Lead", "active", "2024-01-03", "male"],
  ["emp-10", "EMP010", "Maham", "Ali", "maham.ali@company.pk", "Finance", "Finance Executive", "probation", "2026-07-20", "female"],
].map(([id, employee_code, first_name, last_name, email, department, designation, status, join_date, gender], index) => {
  const dept = departments.find((item) => item.name === department) ?? departments[0];
  const des = designations.find((item) => item.name === designation);
  return {
    id,
    employee_code,
    first_name,
    last_name,
    email,
    phone: "0301 2345678",
    gender,
    department_id: dept.id,
    department,
    designation_id: des?.id ?? `des-extra-${index}`,
    designation,
    join_date,
    basic_salary: 120000,
    status,
  } as Employee;
});

const mockUsers: Record<Role, User> = {
  admin: { id: "user-admin", email: "ali.raza@company.pk", role: "admin", employee_id: null, must_change_password: false, is_active: true },
  hr: { id: "user-hr", email: "sarah.ahmed@company.pk", role: "hr", employee_id: "emp-2", must_change_password: false, is_active: true, employee: { first_name: "Sarah", last_name: "Ahmed", employee_code: "EMP002" } },
  employee: { id: "user-employee", email: "ali.raza@company.pk", role: "employee", employee_id: "emp-1", must_change_password: false, is_active: true, employee: { first_name: "Ali", last_name: "Raza", employee_code: "EMP001" } },
};

export const dashboardMocks = {
  admin: {
    headcount: 42,
    attrition_ytd: 4.8,
    payroll_cost: 6420000,
    avg_salary: 152800,
    headcount_by_dept: departments.map((department, index) => ({ department: department.name, value: [10, 8, 7, 6, 5, 4][index] })),
    payroll_cost_by_dept: departments.map((department, index) => ({ department: department.name, value: [1800000, 1400000, 1000000, 900000, 600000, 500000][index] })),
    gender: [{ name: "Male", value: 24 }, { name: "Female", value: 18 }],
    tenure: [{ name: "< 1 year", value: 12 }, { name: "1-3 years", value: 14 }, { name: "3-5 years", value: 10 }, { name: "5+ years", value: 6 }],
    recent_audit: [
      { id: "a1", created_at: "2026-10-23T10:24:00Z", actor: "Sara Ahmed", action: "Updated employee", detail: "Changed salary for Umar Khan" },
      { id: "a2", created_at: "2026-10-22T16:15:00Z", actor: "Ali Raza", action: "Approved leave", detail: "Leave request for Ayesha Malik" },
      { id: "a3", created_at: "2026-10-22T11:03:00Z", actor: "Fatima Noor", action: "Added employee", detail: "New employee Bilal Ahmed" },
      { id: "a4", created_at: "2026-10-21T15:40:00Z", actor: "Usman Ali", action: "Updated settings", detail: "Company details updated" },
    ],
  },
  hr: {
    headcount: 42,
    present_today: 34,
    on_leave_today: 5,
    late_today: 3,
    pending_approvals: 4,
    attendance_trend: [74, 66, 75, 64, 61, 69, 64, 71, 77, 70, 76, 71, 82, 75, 80, 74, 82, 75],
    absenteeism_by_dept: [{ department: "Operations", value: 8 }, { department: "Sales", value: 5 }, { department: "Finance", value: 4 }, { department: "HR", value: 3 }, { department: "IT", value: 2 }],
    leave_by_type: [{ name: "Annual Leave", value: 7 }, { name: "Sick Leave", value: 4 }, { name: "Casual Leave", value: 2 }, { name: "Maternity Leave", value: 1 }, { name: "Others", value: 1 }],
    top_late_comers: [
      { employee: "Ali Raza", department: "Sales", late_count: 6 },
      { employee: "Sarah Khan", department: "Operations", late_count: 5 },
      { employee: "Umair Sheikh", department: "IT", late_count: 4 },
      { employee: "Ayesha Malik", department: "Finance", late_count: 4 },
      { employee: "Bilal Ahmed", department: "Operations", late_count: 3 },
    ],
    today_status: { check_in: "2026-10-23T09:12:00Z", check_out: null, work_duration: "7h 28m", status: "Working" },
  },
  employee: {
    today_status: { date: "2026-10-23", status: "present", check_in: "2026-10-23T08:57:00Z", check_out: null, work_duration: "5h 39m" },
    hours_this_week: 31,
    daily_hours: [{ day: "Mon", hours: 8 }, { day: "Tue", hours: 8 }, { day: "Wed", hours: 7 }, { day: "Thu", hours: 8 }, { day: "Fri", hours: 0 }],
    late_count: 1,
    leave_balance: [
      { leave_type: "Annual Leave", quota: 14, used: 2, pending: 0, remaining: 12 },
      { leave_type: "Sick Leave", quota: 8, used: 2, pending: 0, remaining: 6 },
      { leave_type: "Casual Leave", quota: 10, used: 1, pending: 0, remaining: 9 },
      { leave_type: "Unpaid Leave", quota: null, used: 0, pending: 0, remaining: null },
    ],
    last_payslip: { id: "pay-1", month: "2026-09", gross: 152800, deductions: 24350, tax: 10000, net: 118450 },
  },
};

export const announcementMocks = [
  { id: "n1", title: "Office Closed on 9 November", body: "The office will remain closed on Monday, 9 November.", created_at: "2026-10-20" },
  { id: "n2", title: "Annual Health Check-up", body: "Health check-up sessions are scheduled for all employees.", created_at: "2026-10-15" },
  { id: "n3", title: "New Leave Policy", body: "Please read the updated leave policy available on the portal.", created_at: "2026-10-10" },
];

function list<T>(items: T[], total = items.length, page = 1, pageSize = 20): ListResponse<T> {
  return { items, total, page, page_size: pageSize };
}

function fail(status: number, code: string, message: string): never {
  throw { status, detail: { code, message } };
}

function getRoleFromToken(token: string | null): Role {
  if (token?.includes("admin")) return "admin";
  if (token?.includes("employee")) return "employee";
  return "hr";
}

export async function mockRequest<T>(method: string, path: string, body?: unknown, token?: string | null): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, 280));
  const url = new URL(path, "http://mock.local");
  const route = url.pathname;

  if (route === "/setup/status" && method === "GET") return { is_setup_done: false } as T;
  if (route === "/setup" && method === "POST") return { created: true } as T;
  if (route === "/auth/login" && method === "POST") {
    const credentials = body as { email: string; password: string };
    if (!credentials.email || credentials.password.toLowerCase() === "wrong") fail(401, "INVALID_CREDENTIALS", "Invalid email or password.");
    const role: Role = credentials.email.toLowerCase().includes("admin") ? "admin" : credentials.email.toLowerCase().includes("employee") ? "employee" : "hr";
    return { access_token: `mock-token-${role}`, user: mockUsers[role] } as T;
  }
  if (route === "/auth/me" && method === "GET") return mockUsers[getRoleFromToken(token)] as T;
  if (route === "/auth/change-password" && method === "POST") return { message: "Password changed" } as T;
  if (route === "/dashboard/admin") return dashboardMocks.admin as T;
  if (route === "/dashboard/hr") return dashboardMocks.hr as T;
  if (route === "/dashboard/me") return dashboardMocks.employee as T;
  if (route === "/announcements") return list(announcementMocks) as T;
  if (route === "/ai/summary" && method === "POST") return { bullets: ["Attendance rate this month is 78%, a 6% improvement compared to last month.", "Operations has the highest absenteeism with 8 employees.", "Annual Leave accounts for 47% of all leave requests.", "Late arrivals have decreased by 20% compared to last month."] } as T;
  if (route === "/departments" && method === "GET") return list(departments) as T;
  if (route === "/designations" && method === "GET") return list(designations) as T;
  if (route === "/employees" && method === "GET") {
    const search = (url.searchParams.get("search") ?? "").toLowerCase();
    const departmentId = url.searchParams.get("department_id") ?? "";
    const status = url.searchParams.get("status") ?? "";
    const page = Number(url.searchParams.get("page") ?? 1);
    const pageSize = Number(url.searchParams.get("page_size") ?? 10);
    const filtered = employees.filter((employee) => {
      const matchesSearch = !search || `${employee.first_name} ${employee.last_name} ${employee.email} ${employee.employee_code}`.toLowerCase().includes(search);
      return matchesSearch && (!departmentId || employee.department_id === departmentId) && (!status || employee.status === status);
    });
    return list(filtered.slice((page - 1) * pageSize, page * pageSize), search || departmentId || status ? filtered.length : 42, page, pageSize) as T;
  }
  if (route === "/employees" && method === "POST") {
    const input = body as Omit<Employee, "id" | "status" | "department" | "designation">;
    const employee = { ...input, id: `emp-${Date.now()}`, status: "active" };
    return { employee, temp_password: "HcM@2026#7K" } as T;
  }
  if (route === "/employees/import" && method === "POST") {
    const dryRun = url.searchParams.get("dry_run") === "true";
    return (dryRun
      ? { valid_rows: 18, errors: [{ row: 4, field: "email", reason: "Email address is already in use" }, { row: 11, field: "department", reason: "Department does not exist" }] }
      : { imported_rows: 18, errors: [] }) as T;
  }
  if (route === "/attendance/check-out" && method === "POST") return { status: "present", check_out: "2026-10-23T16:40:00Z" } as T;
  fail(404, "NOT_FOUND", `No mock response is configured for ${method} ${route}.`);
}

export function mockUserForRole(role: Role) {
  return mockUsers[role];
}
