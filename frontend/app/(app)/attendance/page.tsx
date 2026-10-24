"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarCheck, ChevronLeft, ChevronRight, Clock3, MoreVertical, Umbrella, UserRoundX, Users, X } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Department, ListResponse } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type BoardItem = { employee_id: string; employee_code: string; employee_name: string; department: string; check_in: string | null; check_out: string | null; hours_worked: string | null; status: string };
type BoardData = { date: string; summary: { present: number; late: number; absent: number; on_leave: number }; items: BoardItem[]; total: number; page: number; page_size: number };
type CalendarRecord = { date: string; status: string; check_in: string | null; check_out: string | null; hours_worked: string | null };
type CalendarData = { month: string; summary: { present: number; late: number; half_day: number; absent: number }; records: CalendarRecord[] };

export default function AttendancePage() {
  usePageTitle("Attendance");
  const { role } = useAuth();
  return role === "employee" ? <EmployeeAttendance /> : <AttendanceBoard />;
}

function AttendanceBoard() {
  const [date, setDate] = useState("2026-10-23");
  const [departmentId, setDepartmentId] = useState("");
  const query = useQuery({ queryKey: ["attendance-board", date, departmentId], queryFn: () => api.get<BoardData>("/attendance/board", { date, department_id: departmentId }) });
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => api.get<ListResponse<Department>>("/departments") });
  if (query.isLoading) return <LoadingSkeleton cards={4} rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (!query.data) return null;
  const data = query.data;
  return <div className="space-y-5">
    <div className="text-xs text-muted">Attendance&nbsp;&nbsp;/&nbsp;&nbsp;<span className="text-slate-700">Daily attendance board</span></div>
    <PageHeader title="Daily attendance board" subtitle="View employee attendance for the selected date." actions={<><Input type="date" value={date} onChange={(event) => setDate(event.target.value)} className="w-48" /><Select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)} className="w-52"><option value="">All Departments</option>{departments.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select><Button variant="ghost" onClick={() => { setDate("2026-10-23"); setDepartmentId(""); }}>Clear filters</Button></>} />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Summary icon={Users} label="Present" value={data.summary.present} tone="green" /><Summary icon={Clock3} label="Late" value={data.summary.late} tone="amber" /><Summary icon={UserRoundX} label="Absent" value={data.summary.absent} tone="red" /><Summary icon={Umbrella} label="On leave" value={data.summary.on_leave} tone="blue" /></div>
    {data.items.length ? <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">#</th><th>Employee</th><th>Department</th><th>Check in</th><th>Check out</th><th>Hours</th><th>Status</th><th /></tr></thead><tbody>{data.items.map((item, index) => <tr key={item.employee_id} className="border-b border-line last:border-0"><td className="px-4 py-3">{index + 1}</td><td><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-full bg-slate-100 text-[11px]">{initials(item.employee_name)}</span><div><strong>{item.employee_name}</strong><p className="text-xs text-muted">{item.employee_code}</p></div></div></td><td>{item.department}</td><td>{item.check_in ?? "-"}</td><td>{item.check_out ?? "-"}</td><td>{item.hours_worked ?? "-"}</td><td><StatusBadge status={formatStatus(item.status)} /></td><td><button className="p-2"><MoreVertical className="size-4" /></button></td></tr>)}</tbody></table></div><div className="flex items-center justify-between border-t border-line p-4 text-sm text-muted"><span>Showing 1 to {data.items.length} of {data.total} employees</span><div className="flex gap-2"><Button size="icon" variant="outline" disabled><ChevronLeft className="size-4" /></Button><Button size="icon">1</Button><Button size="icon" variant="outline"><ChevronRight className="size-4" /></Button></div></div></section> : <div className="card p-10 text-center text-sm text-muted">No attendance records for this date.</div>}
  </div>;
}

function EmployeeAttendance() {
  const client = useQueryClient();
  const [selected, setSelected] = useState<CalendarRecord | null>(null);
  const [checkIn, setCheckIn] = useState("09:00");
  const [checkOut, setCheckOut] = useState("18:00");
  const [reason, setReason] = useState("");
  const query = useQuery({ queryKey: ["attendance-me", "2026-10"], queryFn: () => api.get<CalendarData>("/attendance/me", { month: "2026-10" }) });
  const correction = useMutation({ mutationFn: () => api.post("/attendance/corrections", { date: selected?.date, requested_check_in: checkIn, requested_check_out: checkOut, reason }), onSuccess: () => { toast.success("Correction request submitted"); setSelected(null); setReason(""); void client.invalidateQueries({ queryKey: ["corrections"] }); } });
  if (query.isLoading) return <LoadingSkeleton cards={4} rows={7} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (!query.data) return null;
  const data = query.data;
  const records = new Map(data.records.map((record) => [Number(record.date.slice(-2)), record]));
  const cells = [...Array.from({ length: 4 }, () => null), ...Array.from({ length: 31 }, (_, index) => index + 1)];
  return <div className="space-y-5">
    <PageHeader title="My attendance" subtitle="View your attendance history and request corrections if needed." actions={<div className="flex items-center"><Button variant="outline" size="icon"><ChevronLeft className="size-4" /></Button><Button variant="outline" className="rounded-none"><CalendarCheck className="size-4" />October 2026</Button><Button variant="outline" size="icon"><ChevronRight className="size-4" /></Button></div>} />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Summary icon={CalendarCheck} label="Present" value={data.summary.present} tone="green" /><Summary icon={Clock3} label="Late" value={data.summary.late} tone="amber" /><Summary icon={CalendarCheck} label="Half day" value={data.summary.half_day} tone="orange" /><Summary icon={UserRoundX} label="Absent" value={data.summary.absent} tone="red" /></div>
    <div className={selected ? "grid gap-4 xl:grid-cols-[1fr_340px]" : "grid gap-4"}>
      <section className="card overflow-hidden"><div className="grid grid-cols-7 bg-slate-50 text-center text-xs font-semibold text-slate-600">{["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => <div key={day} className="p-4">{day}</div>)}</div><div className="grid grid-cols-7">{cells.map((day, index) => { const record = day ? records.get(day) : undefined; return <button key={index} disabled={!day} onClick={() => record && setSelected(record)} className={`min-h-24 border-r border-t border-line p-2 text-left align-top last:border-r-0 md:min-h-28 ${selected?.date === record?.date ? "bg-teal-50 ring-1 ring-inset ring-primary" : "hover:bg-slate-50"}`}><span className="text-xs font-medium text-slate-600">{day}</span>{record && <span className="mt-5 block"><StatusBadge status={formatStatus(record.status)} /></span>}</button>; })}</div><div className="flex flex-wrap gap-5 border-t border-line p-4 text-xs text-muted">{[["bg-emerald-500", "Present"], ["bg-amber-500", "Late"], ["bg-orange-500", "Half day"], ["bg-red-500", "Absent"], ["bg-blue-500", "On leave"], ["bg-violet-500", "Holiday"]].map(([color, label]) => <span key={label} className="flex items-center gap-2"><i className={`size-2.5 rounded-full ${color}`} />{label}</span>)}</div></section>
      {selected && <aside className="card p-5"><div className="flex items-center justify-between"><h2 className="font-semibold">{selected.date}</h2><button onClick={() => setSelected(null)}><X className="size-5" /></button></div><div className="mt-3"><StatusBadge status={formatStatus(selected.status)} /></div><div className="mt-5 grid grid-cols-2 gap-4 rounded-lg bg-slate-50 p-4 text-sm"><div><p className="text-xs text-muted">Check in</p><strong>{selected.check_in ? "09:12" : "-"}</strong></div><div><p className="text-xs text-muted">Check out</p><strong>{selected.check_out ? "17:35" : "-"}</strong></div><div className="col-span-2"><p className="text-xs text-muted">Total hours</p><strong>{selected.hours_worked ?? "-"}</strong></div></div><div className="my-5 border-t border-line" /><h3 className="font-semibold">Request correction</h3><p className="mt-1 text-xs text-muted">If your attendance is incorrect, you can request a correction.</p><label className="mt-4 block text-xs font-medium">Correct check-in time</label><Input type="time" value={checkIn} onChange={(event) => setCheckIn(event.target.value)} className="mt-2" /><label className="mt-4 block text-xs font-medium">Correct check-out time</label><Input type="time" value={checkOut} onChange={(event) => setCheckOut(event.target.value)} className="mt-2" /><label className="mt-4 block text-xs font-medium">Reason <span className="text-red-500">*</span></label><Textarea value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2" placeholder="Explain what should be corrected" /><div className="mt-4 flex gap-3"><Button variant="outline" className="flex-1" onClick={() => setSelected(null)}>Cancel</Button><Button className="flex-1" disabled={!reason || correction.isPending} onClick={() => correction.mutate()}>{correction.isPending ? "Submitting..." : "Submit request"}</Button></div></aside>}
    </div>
  </div>;
}

function Summary({ icon: Icon, label, value, tone }: { icon: typeof Users; label: string; value: number; tone: "green" | "amber" | "red" | "blue" | "orange" }) { const styles = { green: "bg-emerald-50 text-emerald-600", amber: "bg-amber-50 text-amber-600", red: "bg-red-50 text-red-600", blue: "bg-blue-50 text-blue-600", orange: "bg-orange-50 text-orange-600" }; return <div className="card flex items-center gap-5 p-4"><span className={`flex size-12 items-center justify-center rounded-full ${styles[tone]}`}><Icon className="size-6" /></span><div><p className="text-xs text-muted">{label}</p><strong className="text-2xl">{value}</strong></div></div>; }
function formatStatus(status: string) { return status.split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join(" "); }
