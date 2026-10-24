import type { Department, Designation, Employee, ListResponse, Role, User } from "@/lib/types";

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
  hr: { id: "user-hr", email: "sarah.ahmed@company.pk", role: "hr", employee_id: "emp-2", must_change_password: false, is_active: true, employee: { first_name: "Sarah", last_name: "Ahmed", employee_code: "EMP002", phone: "+92 300 1234567", address: "45 Main Boulevard, Lahore", department: "HR", designation: "HR Officer", join_date: "2024-03-05" } },
  employee: { id: "user-employee", email: "ali.raza@company.pk", role: "employee", employee_id: "emp-1", must_change_password: false, is_active: true, employee: { first_name: "Ali", last_name: "Raza", employee_code: "EMP001", phone: "+92 321 7654321", address: "123 Business Avenue, Karachi, Pakistan", department: "Operations", designation: "Operations Executive", join_date: "2024-03-15" } },
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

const employee360Mock = {
  employee: {
    ...employees[3],
    address: "House 123, Street 4, F-10/2, Islamabad",
    cnic: "37405-1234567-8",
    reporting_manager: "Bilal Ahmed (Sales Director)",
    employment_type: "Permanent",
    shift: "Morning (9:00 AM - 6:00 PM)",
    location: "Islamabad Office",
  },
  salary: { basic: 80000, hra: 24000, medical: 8000, gross: 112000 },
  attendance_summary: { month: "2026-10", present: 18, late: 2, half_day: 1, absent: 1 },
  leave_balance: [
    { leave_type: "Annual Leave", quota: 14, used: 2, pending: 0, remaining: 12 },
    { leave_type: "Sick Leave", quota: 8, used: 0, pending: 0, remaining: 8 },
    { leave_type: "Casual Leave", quota: 10, used: 6, pending: 0, remaining: 4 },
    { leave_type: "Unpaid Leave", quota: null, used: 0, pending: 0, remaining: null },
  ],
  payslips: [
    { id: "slip-1", month: "2026-10", net: 112000, pay_date: "2026-10-28" },
    { id: "slip-2", month: "2026-09", net: 112000, pay_date: "2026-09-28" },
    { id: "slip-3", month: "2026-08", net: 112000, pay_date: "2026-08-31" },
  ],
};

const boardStatuses = ["present", "late", "half_day", "on_leave", "missing_checkout", "present", "late", "present", "on_leave", "present"];
const attendanceBoardMock = {
  date: "2026-10-23",
  summary: { present: 34, late: 3, absent: 0, on_leave: 5 },
  items: employees.map((employee, index) => ({
    employee_id: employee.id,
    employee_code: employee.employee_code,
    employee_name: `${employee.first_name} ${employee.last_name}`,
    department: employee.department,
    check_in: boardStatuses[index] === "on_leave" ? null : ["09:02", "09:21", "09:05", null, "08:57", "09:15", "09:28", "09:00", null, "09:12"][index],
    check_out: ["17:35", "17:10", "12:30", null, null, "17:05", "17:40", "17:20", null, "17:30"][index],
    hours_worked: ["8h 33m", "7h 49m", "3h 25m", null, null, "7h 50m", "8h 12m", "8h 20m", null, "8h 18m"][index],
    status: boardStatuses[index],
  })),
  total: 42,
  page: 1,
  page_size: 10,
};

const attendanceCalendarMock = {
  month: "2026-10",
  summary: { present: 15, late: 1, half_day: 1, absent: 0 },
  records: [
    ["2026-10-01", "present"], ["2026-10-02", "present"], ["2026-10-05", "present"], ["2026-10-06", "present"], ["2026-10-07", "late"], ["2026-10-08", "present"], ["2026-10-09", "present"], ["2026-10-12", "present"], ["2026-10-13", "half_day"], ["2026-10-14", "present"], ["2026-10-15", "holiday"], ["2026-10-16", "present"], ["2026-10-19", "present"], ["2026-10-20", "present"], ["2026-10-21", "present"], ["2026-10-22", "present"], ["2026-10-23", "present"], ["2026-10-26", "present"], ["2026-10-27", "present"], ["2026-10-28", "present"],
  ].map(([date, status]) => ({ date, status, check_in: status === "holiday" ? null : "2026-10-26T09:12:00Z", check_out: status === "holiday" ? null : "2026-10-26T17:35:00Z", hours_worked: status === "holiday" ? null : "8h 23m" })),
};

const correctionMocks = employees.map((employee, index) => ({
  id: `correction-${index + 1}`,
  employee_id: employee.id,
  employee_code: employee.employee_code,
  employee_name: `${employee.first_name} ${employee.last_name}`,
  department: employee.department,
  date: `2026-10-${String(14 - index).padStart(2, "0")}`,
  requested_check_in: ["09:30", "09:10", "09:00", "08:55", "09:20", "09:05", "09:15", "09:00", "09:25", "09:10"][index],
  requested_check_out: ["18:15", "17:20", "17:30", "18:00", "17:45", "17:10", "18:00", "17:40", "18:00", "17:30"][index],
  reason: ["Was in a client meeting offsite.", "Traffic due to road closure.", "Left early for medical appointment.", "Forgot to check in.", "Client visit.", "Worked from branch office.", "System marked half day incorrectly.", "Forgot to check out.", "Was at bank for official work.", "Forgot to check-in."][index],
  status: index < 6 ? "pending" : index === 7 ? "rejected" : "approved",
  comment: index === 7 ? "Supporting information was not sufficient." : null,
  created_at: "2026-10-15T10:00:00Z",
}));

const leaveTypeMocks = [
  { id: "leave-annual", code: "ANNUAL", name: "Annual Leave", yearly_quota: 14, is_paid: true },
  { id: "leave-sick", code: "SICK", name: "Sick Leave", yearly_quota: 8, is_paid: true },
  { id: "leave-casual", code: "CASUAL", name: "Casual Leave", yearly_quota: 10, is_paid: true },
  { id: "leave-unpaid", code: "UNPAID", name: "Unpaid Leave", yearly_quota: null, is_paid: false },
];

const leaveBalanceMocks = [
  { leave_type: "Annual Leave", quota: 14, used: 2, pending: 0, remaining: 12 },
  { leave_type: "Sick Leave", quota: 8, used: 2, pending: 0, remaining: 6 },
  { leave_type: "Casual Leave", quota: 10, used: 1, pending: 0, remaining: 9 },
  { leave_type: "Unpaid Leave", quota: null, used: 0, pending: 0, remaining: null },
];

const leaveRequestMocks = employees.map((employee, index) => ({
  id: `leave-request-${index + 1}`,
  employee_id: employee.id,
  employee_code: employee.employee_code,
  employee_name: `${employee.first_name} ${employee.last_name}`,
  department: employee.department,
  leave_type_id: index % 3 === 1 ? "leave-annual" : index % 3 === 2 ? "leave-sick" : "leave-casual",
  leave_type: index % 3 === 1 ? "Annual" : index % 3 === 2 ? "Sick" : "Casual",
  start_date: `2026-10-${String(20 + (index % 8)).padStart(2, "0")}`,
  end_date: `2026-10-${String(21 + (index % 8)).padStart(2, "0")}`,
  working_days: index % 3 + 1,
  reason: ["Family function.", "Vacation trip.", "Fever and flu.", "Personal work.", "Family visit.", "Medical appointment.", "Conference.", "Sister's wedding.", "Personal work.", "Not feeling well."][index],
  status: index < 5 || index === 8 ? "pending" : index === 6 ? "rejected" : "approved",
  comment: index === 6 ? "Leave quota is not available." : null,
  created_at: "2026-10-20T10:00:00Z",
}));

const payrollRunMocks = [
  { id: "run-oct-2026", month: "2026-10", status: "draft", employee_count: 42, total_gross: 2856000, total_deductions: 342700, total_tax: 303250, total_net: 2210050, created_by: "Sara Ahmed", created_at: "2026-10-20T10:24:00Z" },
  { id: "run-sep-2026", month: "2026-09", status: "finalized", employee_count: 41, total_gross: 2784500, total_deductions: 326200, total_tax: 300000, total_net: 2158300, created_by: "Sara Ahmed", created_at: "2026-09-30T18:10:00Z" },
  { id: "run-aug-2026", month: "2026-08", status: "finalized", employee_count: 40, total_gross: 2701200, total_deductions: 310000, total_tax: 294600, total_net: 2096600, created_by: "Ayesha Malik", created_at: "2026-08-31T17:05:00Z" },
];

const payrollDetailMock = {
  ...payrollRunMocks[0],
  payslips: employees.map((employee, index) => {
    const gross = [75000, 68000, 72000, 80000, 65000, 70000, 78000, 60000, 68000, 62000][index];
    const deduction = [9000, 8500, 9000, 10000, 8000, 8700, 9300, 7500, 8500, 7800][index];
    const tax = [7500, 6800, 7200, 8000, 6500, 7000, 7800, 6000, 6800, 6200][index];
    return { id: `payslip-${index + 1}`, employee_id: employee.id, employee_code: employee.employee_code, employee_name: `${employee.first_name} ${employee.last_name}`, department: employee.department, gross, working_days: 22 - (index % 3), absent_days: index % 4 === 3 ? 2 : 0, unpaid_leave_days: index % 5 === 4 ? 1 : 0, half_days: index % 3 === 2 ? 1 : 0, attendance_deduction: deduction, tax, net: gross - deduction - tax };
  }),
};

const myPayslipMocks = payrollDetailMock.payslips.map((payslip, index) => ({
  ...payslip,
  id: `my-payslip-${index + 1}`,
  month: `2026-${String(10 - index).padStart(2, "0")}`,
  status: "finalized",
  pay_date: `2026-${String(10 - index).padStart(2, "0")}-28`,
}));

const settingsMock = { company_name: "HCM Lite (Pvt.) Ltd.", office_start: "09:00", grace_minutes: 15, half_day_hours: 5, weekend_days: [5, 6], office_lat: 24.8607, office_lng: 67.0011, office_radius_m: 150 };
const holidayMocks = [
  { id: "holiday-1", date: "2026-11-09", name: "Iqbal Day" },
  { id: "holiday-2", date: "2026-12-25", name: "Christmas Day" },
  { id: "holiday-3", date: "2027-01-01", name: "New Year's Day" },
];
const userMocks: Array<User & { name: string }> = [
  { ...mockUsers.admin, name: "Ali Raza", created_at: "2026-10-10T09:12:00Z" },
  { ...mockUsers.hr, name: "Sarah Ahmed", created_at: "2026-10-12T14:30:00Z" },
  { id: "user-hr-2", email: "hr2@hcmlite.com", name: "Bilal Ahmed", role: "hr", employee_id: "emp-5", must_change_password: false, is_active: true, created_at: "2026-10-15T11:05:00Z" },
  { ...mockUsers.employee, name: "Ali Raza", created_at: "2026-10-18T16:20:00Z" },
];
const auditLogMocks = [
  { id: "audit-1", created_at: "2026-10-24T10:32:00Z", actor_id: "user-admin", actor_email: "ali.raza@company.pk", actor_name: "Ali Raza", actor_role: "admin", action: "update", entity: "employee", entity_id: "EMP001", before: { phone: "+92 300 1234567", department: "Operations", designation: "Assistant Manager", address: "Old address, Karachi" }, after: { phone: "+92 321 7654321", department: "Operations", designation: "Operations Executive", address: "123 Business Avenue, Karachi" } },
  { id: "audit-2", created_at: "2026-10-24T09:15:00Z", actor_id: "user-hr", actor_email: "sarah.ahmed@company.pk", actor_name: "Sarah Ahmed", actor_role: "hr", action: "create", entity: "leave_request", entity_id: "LR-2026-015", before: null, after: { status: "pending" } },
  { id: "audit-3", created_at: "2026-10-23T16:48:00Z", actor_id: "user-hr-2", actor_email: "hr2@hcmlite.com", actor_name: "Bilal Ahmed", actor_role: "hr", action: "approve", entity: "leave_request", entity_id: "LR-2026-014", before: { status: "pending" }, after: { status: "approved" } },
  { id: "audit-4", created_at: "2026-10-23T14:21:00Z", actor_id: "user-hr", actor_email: "sarah.ahmed@company.pk", actor_name: "Sarah Ahmed", actor_role: "hr", action: "update", entity: "attendance", entity_id: "ATT-2026-1023", before: { check_in: "09:30" }, after: { check_in: "09:00" } },
  { id: "audit-5", created_at: "2026-10-22T11:03:00Z", actor_id: "user-admin", actor_email: "ali.raza@company.pk", actor_name: "Admin", actor_role: "admin", action: "finalize", entity: "payroll", entity_id: "October 2026", before: { status: "draft" }, after: { status: "finalized" } },
];
const notificationMocks = [
  { id: "notification-1", title: "Your leave for 26 to 27 Oct was approved", body: "Your casual leave request was approved.", type: "leave", link: "/leaves", is_read: false, created_at: "2026-10-24T08:00:00Z" },
  { id: "notification-2", title: "Your payslip for September 2026 is ready", body: "Download your finalized payslip.", type: "payslip", link: "/payslips", is_read: false, created_at: "2026-10-24T05:00:00Z" },
  { id: "notification-3", title: "New announcement: Office closed on 9 November", body: "Read the latest company announcement.", type: "announcement", link: "/announcements", is_read: false, created_at: "2026-10-23T10:00:00Z" },
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
  if (route === "/auth/me" && method === "GET") return mockUsers[getRoleFromToken(token ?? null)] as T;
  if (route === "/auth/change-password" && method === "POST") return { message: "Password changed" } as T;
  if (route === "/dashboard/admin") return dashboardMocks.admin as T;
  if (route === "/dashboard/hr") return dashboardMocks.hr as T;
  if (route === "/dashboard/me") return dashboardMocks.employee as T;
  if (route === "/announcements" && method === "GET") return list(announcementMocks) as T;
  if (route === "/announcements" && method === "POST") {
    const item = { id: `announcement-${Date.now()}`, ...(body as { title: string; body: string }), created_at: new Date().toISOString(), author_name: "Sarah Ahmed", author_role: "HR" };
    announcementMocks.unshift(item);
    return item as T;
  }
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
  const employeeMatch = route.match(/^\/employees\/([^/]+)$/);
  if (employeeMatch && method === "GET") return { ...employee360Mock, employee: { ...employee360Mock.employee, id: employeeMatch[1] } } as T;
  if (employeeMatch && method === "PATCH") return { ...employee360Mock.employee, ...(body as object) } as T;
  const salaryMatch = route.match(/^\/employees\/([^/]+)\/salary$/);
  if (salaryMatch && method === "GET") return employee360Mock.salary as T;
  if (salaryMatch && method === "PUT") return { ...employee360Mock.salary, ...(body as object) } as T;
  if (route === "/employees/import" && method === "POST") {
    const dryRun = url.searchParams.get("dry_run") === "true";
    return (dryRun
      ? { valid_rows: 18, errors: [{ row: 4, field: "email", reason: "Email address is already in use" }, { row: 11, field: "department", reason: "Department does not exist" }] }
      : { imported_rows: 18, errors: [] }) as T;
  }
  if (route === "/attendance/check-out" && method === "POST") return { status: "present", check_out: "2026-10-23T16:40:00Z" } as T;
  if (route === "/attendance/board" && method === "GET") return attendanceBoardMock as T;
  if (route === "/attendance/me" && method === "GET") return attendanceCalendarMock as T;
  if (route === "/attendance/corrections" && method === "GET") {
    const status = url.searchParams.get("status");
    const visible = getRoleFromToken(token ?? null) === "employee" ? correctionMocks.slice(0, 3) : correctionMocks;
    return list(status && status !== "all" ? visible.filter((item) => item.status === status) : visible, visible.length, 1, 20) as T;
  }
  if (route === "/attendance/corrections" && method === "POST") return { id: `correction-${Date.now()}`, ...(body as object), status: "pending", created_at: new Date().toISOString() } as T;
  const correctionMatch = route.match(/^\/attendance\/corrections\/([^/]+)$/);
  if (correctionMatch && method === "PATCH") {
    const decision = body as { action: "approve" | "reject"; comment?: string };
    return { ...correctionMocks.find((item) => item.id === correctionMatch[1]), status: decision.action === "approve" ? "approved" : "rejected", comment: decision.comment ?? null } as T;
  }
  if (route === "/leave-types" && method === "GET") return list(leaveTypeMocks) as T;
  if (route === "/leaves/balance" && method === "GET") return leaveBalanceMocks as T;
  if (route === "/leaves/me" && method === "GET") return list(leaveRequestMocks.slice(0, 5)) as T;
  if (route === "/leaves" && method === "GET") {
    const status = url.searchParams.get("status");
    const visible = status && status !== "all" ? leaveRequestMocks.filter((item) => item.status === status) : leaveRequestMocks;
    return list(visible, status ? visible.length : 20, 1, 20) as T;
  }
  if (route === "/leaves" && method === "POST") return { id: `leave-request-${Date.now()}`, ...(body as object), status: "pending", created_at: new Date().toISOString() } as T;
  const leaveCancelMatch = route.match(/^\/leaves\/([^/]+)\/cancel$/);
  if (leaveCancelMatch && method === "POST") return { ...leaveRequestMocks.find((item) => item.id === leaveCancelMatch[1]), status: "cancelled" } as T;
  const leaveDecisionMatch = route.match(/^\/leaves\/([^/]+)\/decision$/);
  if (leaveDecisionMatch && method === "PATCH") {
    const decision = body as { action: "approve" | "reject"; comment?: string };
    return { ...leaveRequestMocks.find((item) => item.id === leaveDecisionMatch[1]), status: decision.action === "approve" ? "approved" : "rejected", comment: decision.comment ?? null } as T;
  }
  if (route === "/ai/smart-leave" && method === "POST") return { leave_type: "CASUAL", start_date: "2026-10-26", end_date: "2026-10-27", reason: "Sister's wedding" } as T;
  if (route === "/payroll/runs" && method === "GET") return list(payrollRunMocks) as T;
  if (route === "/payroll/runs" && method === "POST") return { ...payrollRunMocks[0], month: (body as { month: string }).month, id: `run-${Date.now()}` } as T;
  const payrollRunMatch = route.match(/^\/payroll\/runs\/([^/]+)$/);
  if (payrollRunMatch && method === "GET") return { ...payrollDetailMock, id: payrollRunMatch[1], status: payrollRunMatch[1].includes("oct") ? "draft" : "finalized" } as T;
  const payrollActionMatch = route.match(/^\/payroll\/runs\/([^/]+)\/(recalculate|finalize)$/);
  if (payrollActionMatch && method === "POST") return { ...payrollDetailMock, id: payrollActionMatch[1], status: payrollActionMatch[2] === "finalize" ? "finalized" : "draft" } as T;
  if (route === "/payslips/me" && method === "GET") return list(myPayslipMocks) as T;
  if (route === "/settings" && method === "GET") return settingsMock as T;
  if (route === "/settings" && method === "PUT") return Object.assign(settingsMock, body) as T;
  if (route === "/departments" && method === "POST") { const item = { id: `dept-${Date.now()}`, ...(body as { name: string }) }; departments.push(item); return item as T; }
  const departmentMatch = route.match(/^\/departments\/([^/]+)$/);
  if (departmentMatch && method === "PUT") { const item = departments.find((entry) => entry.id === departmentMatch[1]); if (!item) fail(404, "NOT_FOUND", "Department not found."); Object.assign(item, body); return item as T; }
  if (departmentMatch && method === "DELETE") return { deleted: true } as T;
  if (route === "/designations" && method === "POST") { const input = body as { name: string; department_id: string }; const item = { id: `des-${Date.now()}`, ...input, department_name: departments.find((entry) => entry.id === input.department_id)?.name }; designations.push(item); return item as T; }
  if (route === "/leave-types" && method === "POST") { const item = { id: `leave-${Date.now()}`, ...(body as { code: string; name: string; yearly_quota: number | null; is_paid: boolean }) }; leaveTypeMocks.push(item); return item as T; }
  const leaveTypeMatch = route.match(/^\/leave-types\/([^/]+)$/);
  if (leaveTypeMatch && method === "PUT") { const item = leaveTypeMocks.find((entry) => entry.id === leaveTypeMatch[1]); if (!item) fail(404, "NOT_FOUND", "Leave type not found."); Object.assign(item, body); return item as T; }
  if (route === "/holidays" && method === "GET") return list(holidayMocks) as T;
  if (route === "/holidays" && method === "POST") { const item = { id: `holiday-${Date.now()}`, ...(body as { date: string; name: string }) }; holidayMocks.push(item); return item as T; }
  const holidayMatch = route.match(/^\/holidays\/([^/]+)$/);
  if (holidayMatch && method === "DELETE") return { deleted: true } as T;
  if (route === "/users" && method === "GET") return list(userMocks) as T;
  if (route === "/users" && method === "POST") { const input = body as { email: string; password: string }; const item: User & { name: string } = { id: `user-${Date.now()}`, email: input.email, name: input.email.split("@")[0], role: "hr", employee_id: null, must_change_password: true, is_active: true, created_at: new Date().toISOString() }; userMocks.push(item); return { user: item, temp_password: input.password } as T; }
  const deactivateMatch = route.match(/^\/users\/([^/]+)\/deactivate$/);
  if (deactivateMatch && method === "PATCH") return { ...userMocks.find((item) => item.id === deactivateMatch[1]), is_active: false } as T;
  const resetMatch = route.match(/^\/users\/([^/]+)\/reset-password$/);
  if (resetMatch && method === "POST") return { temp_password: "H7k9@Lm2" } as T;
  if (route === "/audit-logs" && method === "GET") return list(auditLogMocks, 42, 1, 20) as T;
  if (route === "/employees/me" && method === "PATCH") { const role = getRoleFromToken(token ?? null); const current = mockUsers[role]; if (current.employee) Object.assign(current.employee, body); return current.employee as T; }
  if (route === "/ai/chat" && method === "POST") return { answer: "Based on the current HR records, 5 employees are on leave today. Three are on casual leave and two are on sick leave.", tools_used: ["get_leave_summary"], ai_generated: true } as T;
  if (route === "/notifications" && method === "GET") return list(notificationMocks) as T;
  const notificationMatch = route.match(/^\/notifications\/([^/]+)\/read$/);
  if (notificationMatch && method === "PATCH") { const item = notificationMocks.find((entry) => entry.id === notificationMatch[1]); if (item) item.is_read = true; return item as T; }
  fail(404, "NOT_FOUND", `No mock response is configured for ${method} ${route}.`);
}

export function mockUserForRole(role: Role) {
  return mockUsers[role];
}
