export type Role = "admin" | "hr" | "employee";

export type User = {
  id: string;
  email: string;
  role: Role;
  employee_id: string | null;
  must_change_password: boolean;
  is_active?: boolean;
  created_at?: string;
  employee?: {
    first_name: string;
    last_name: string;
    employee_code: string;
    phone?: string;
    address?: string;
  } | null;
};

export type LoginResponse = { access_token: string; user: User };

export type ListResponse<T> = {
  items: T[];
  total: number;
  page: number;
  page_size: number;
};

export type Settings = {
  company_name: string;
  office_start: string;
  grace_minutes: number;
  half_day_hours: number;
  weekend_days: number[];
  office_lat: number | null;
  office_lng: number | null;
  office_radius_m: number;
};

export type Department = { id: string; name: string; employee_count?: number };
export type Designation = { id: string; name: string; department_id: string; department_name?: string };
export type LeaveType = {
  id: string;
  code: string;
  name: string;
  yearly_quota: number | null;
  is_paid: boolean;
};
export type Holiday = { id: string; date: string; name: string };
export type AuditLog = {
  id: string;
  created_at: string;
  actor_id: string;
  actor_email?: string;
  action: string;
  entity: string;
  entity_id?: string | null;
  before: Record<string, unknown> | null;
  after: Record<string, unknown> | null;
};

export type Employee = {
  id: string;
  employee_code: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  gender: string;
  department_id: string;
  department: string;
  designation_id: string;
  designation: string;
  join_date: string;
  basic_salary: number;
  status: string;
};
