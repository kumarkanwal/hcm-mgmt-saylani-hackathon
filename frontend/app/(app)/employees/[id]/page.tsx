"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { BriefcaseBusiness, CalendarCheck, ChevronLeft, CreditCard, FileText, Pencil, Plane, UserRound } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Tabs } from "@/components/tabs";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Employee } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type Salary = { basic: number; hra: number; medical: number; gross: number };
type Employee360 = { employee: Employee & { address: string; cnic: string; reporting_manager: string; employment_type: string; shift: string; location: string }; salary: Salary; attendance_summary: { month: string; present: number; late: number; half_day: number; absent: number }; leave_balance: { leave_type: string; quota: number | null; used: number; pending: number; remaining: number | null }[]; payslips: { id: string; month: string; net: number; pay_date: string }[] };
const money = (value: number) => `PKR ${value.toLocaleString("en-PK")}`;

export default function EmployeeDetailPage() {
  usePageTitle("Employee 360");
  const { id } = useParams<{ id: string }>();
  const { role } = useAuth();
  const client = useQueryClient();
  const [tab, setTab] = useState("overview");
  const [salaryOpen, setSalaryOpen] = useState(false);
  const [basic, setBasic] = useState(0);
  const query = useQuery({ queryKey: ["employee", id], queryFn: () => api.get<Employee360>(`/employees/${id}`) });
  const saveSalary = useMutation({ mutationFn: () => api.put<Salary>(`/employees/${id}/salary`, { basic }), onSuccess: () => { toast.success("Salary updated"); setSalaryOpen(false); void client.invalidateQueries({ queryKey: ["employee", id] }); } });
  if (query.isLoading) return <LoadingSkeleton cards={3} rows={6} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (!query.data) return null;
  const data = query.data;
  const employee = data.employee;
  const name = `${employee.first_name} ${employee.last_name}`;
  const details = [{ label: "Email", value: employee.email }, { label: "Phone", value: employee.phone }, { label: "Gender", value: employee.gender }, { label: "Address", value: employee.address }, { label: "CNIC", value: employee.cnic }];
  const job = [{ label: "Join date", value: employee.join_date }, { label: "Reporting manager", value: employee.reporting_manager }, { label: "Employment type", value: employee.employment_type }, { label: "Shift", value: employee.shift }, { label: "Location", value: employee.location }];
  return (
    <div className="space-y-5">
      <PageHeader title="Employee 360" subtitle="View complete information, attendance, leave and payroll details." actions={<Button variant="outline" asChild><Link href="/employees"><ChevronLeft className="size-4" />Back to Employees</Link></Button>} />
      <section className="card flex flex-col gap-5 p-6 lg:flex-row lg:items-center">
        <div className="flex min-w-0 flex-1 items-center gap-5"><span className="flex size-20 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xl font-semibold text-slate-500">{initials(name)}</span><div><h2 className="text-2xl font-bold">{name}</h2><p className="mt-1 text-muted">{employee.employee_code}</p></div></div>
        <div className="grid flex-[2] grid-cols-2 gap-5 sm:grid-cols-3"><div><p className="text-xs text-muted">Department</p><strong className="mt-1 block">{employee.department}</strong></div><div><p className="text-xs text-muted">Designation</p><strong className="mt-1 block">{employee.designation}</strong></div><div><p className="text-xs text-muted">Status</p><span className="mt-1 block"><StatusBadge status="Active" /></span></div></div>
        {role === "hr" && <Button><Pencil className="size-4" />Edit</Button>}
      </section>
      <Tabs items={[{ value: "overview", label: "Overview" }, { value: "salary", label: "Salary" }, { value: "attendance", label: "Attendance" }, { value: "leave", label: "Leave" }, { value: "payslips", label: "Payslips" }]} value={tab} onChange={setTab} />
      {tab === "overview" && <div className="grid gap-4 xl:grid-cols-3">
        <InfoCard title="Personal Details" icon={UserRound} rows={details} />
        <InfoCard title="Job Details" icon={BriefcaseBusiness} rows={job} />
        <section className="card p-5"><div className="flex items-center gap-3"><CreditCard className="size-5 text-slate-500" /><h3 className="font-semibold">Salary Summary</h3></div><dl className="mt-4 divide-y divide-line text-sm"><Row label="Basic Salary" value={money(data.salary.basic)} /><Row label="House Rent Allowance (HRA)" value={money(data.salary.hra)} /><Row label="Medical Allowance" value={money(data.salary.medical)} /><div className="mt-3 flex justify-between rounded-lg bg-teal-50 p-4 font-bold text-primary"><dt>Gross Salary</dt><dd>{money(data.salary.gross)}</dd></div></dl></section>
        <section className="card p-5"><h3 className="flex items-center gap-3 font-semibold"><CalendarCheck className="size-5 text-slate-500" />This Month Attendance</h3><div className="mt-5 grid grid-cols-2 gap-3">{[["Present", data.attendance_summary.present, "bg-emerald-50 text-emerald-700"], ["Late", data.attendance_summary.late, "bg-amber-50 text-amber-700"], ["Half day", data.attendance_summary.half_day, "bg-orange-50 text-orange-700"], ["Absent", data.attendance_summary.absent, "bg-red-50 text-red-700"]].map(([label, value, style]) => <div key={String(label)} className={`rounded-lg p-4 ${style}`}><strong className="text-xl">{value}</strong><p className="text-xs">{label}</p></div>)}</div></section>
        <section className="card p-5"><h3 className="flex items-center gap-3 font-semibold"><Plane className="size-5 text-slate-500" />Leave Balance</h3><div className="mt-5 grid grid-cols-2 gap-3">{data.leave_balance.map((item) => <div key={item.leave_type} className="rounded-lg bg-slate-50 p-3"><p className="text-xs">{item.leave_type}</p><strong className="mt-1 block text-lg">{item.remaining ?? "Unlimited"}</strong><p className="text-[11px] text-muted">days remaining</p></div>)}</div></section>
        <section className="card p-5"><h3 className="flex items-center gap-3 font-semibold"><FileText className="size-5 text-slate-500" />Last 3 Payslips</h3><div className="mt-4 divide-y divide-line">{data.payslips.map((item) => <div key={item.id} className="flex items-center gap-3 py-3"><FileText className="size-5 text-slate-500" /><div className="flex-1"><strong className="text-sm">{item.month}</strong><p className="text-xs text-muted">{item.pay_date}</p></div><strong className="text-sm">{money(item.net)}</strong><Button variant="outline" size="sm">View</Button></div>)}</div></section>
      </div>}
      {tab === "salary" && <section className="card max-w-2xl p-6"><div className="flex items-start justify-between"><div><h2 className="text-lg font-semibold">Salary structure</h2><p className="text-sm text-muted">Amounts returned by the payroll service.</p></div>{role === "hr" && <Button onClick={() => { setBasic(data.salary.basic); setSalaryOpen(true); }}><Pencil className="size-4" />Change basic</Button>}</div><dl className="mt-5 divide-y divide-line"><Row label="Basic salary" value={money(data.salary.basic)} /><Row label="House rent allowance" value={money(data.salary.hra)} /><Row label="Medical allowance" value={money(data.salary.medical)} /><Row label="Gross salary" value={money(data.salary.gross)} /></dl></section>}
      {tab === "attendance" && <section className="card p-6"><h2 className="font-semibold">This month&apos;s attendance</h2><div className="mt-5 grid gap-4 sm:grid-cols-4"><Metric label="Present" value={data.attendance_summary.present} /><Metric label="Late" value={data.attendance_summary.late} /><Metric label="Half day" value={data.attendance_summary.half_day} /><Metric label="Absent" value={data.attendance_summary.absent} /></div></section>}
      {tab === "leave" && <section className="card p-6"><h2 className="font-semibold">Leave balance</h2><div className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{data.leave_balance.map((item) => <Metric key={item.leave_type} label={item.leave_type} value={item.remaining ?? "Unlimited"} />)}</div></section>}
      {tab === "payslips" && <section className="card p-6"><h2 className="font-semibold">Recent payslips</h2><div className="mt-4 divide-y divide-line">{data.payslips.map((item) => <div key={item.id} className="flex items-center gap-4 py-4"><span className="flex size-10 items-center justify-center rounded-lg bg-teal-50 text-primary"><FileText className="size-5" /></span><strong className="flex-1">{item.month}</strong><span>{money(item.net)}</span><Button variant="outline">View</Button></div>)}</div></section>}
      <Dialog open={salaryOpen} onOpenChange={setSalaryOpen}><DialogContent><DialogTitle>Update basic salary</DialogTitle><DialogDescription>The backend will calculate all salary components.</DialogDescription><Input className="mt-5" type="number" value={basic} onChange={(event) => setBasic(Number(event.target.value))} /><div className="mt-5 flex justify-end gap-3"><Button variant="outline" onClick={() => setSalaryOpen(false)}>Cancel</Button><Button onClick={() => saveSalary.mutate()} disabled={saveSalary.isPending}>{saveSalary.isPending ? "Saving..." : "Save salary"}</Button></div></DialogContent></Dialog>
    </div>
  );
}

function InfoCard({ title, icon: Icon, rows }: { title: string; icon: typeof UserRound; rows: { label: string; value: string }[] }) { return <section className="card p-5"><h3 className="flex items-center gap-3 font-semibold"><Icon className="size-5 text-slate-500" />{title}</h3><dl className="mt-4 divide-y divide-line text-sm">{rows.map((row) => <Row key={row.label} label={row.label} value={row.value} />)}</dl></section>; }
function Row({ label, value }: { label: string; value: string }) { return <div className="flex gap-4 py-3"><dt className="flex-1 text-muted">{label}</dt><dd className="flex-1 font-medium text-slate-800">{value}</dd></div>; }
function Metric({ label, value }: { label: string; value: string | number }) { return <div className="rounded-lg border border-line bg-slate-50 p-5"><p className="text-sm text-muted">{label}</p><strong className="mt-2 block text-2xl">{value}</strong></div>; }
