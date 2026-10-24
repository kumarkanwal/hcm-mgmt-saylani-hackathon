"use client";

import { useMutation } from "@tanstack/react-query";
import { CalendarCheck, Clock3, FileClock, Sparkles, Umbrella, Users } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { ChartCard } from "@/components/dashboard/chart-card";
import { KpiCard } from "@/components/kpi-card";
import { StatusBadge } from "@/components/status-badge";
import { api, USE_MOCKS } from "@/lib/api";
import { initials } from "@/lib/utils";

export type HrDashboardData = {
  headcount: number;
  present_today: number;
  on_leave_today: number;
  late_today: number;
  pending_approvals: number;
  attendance_trend: number[];
  absenteeism_by_dept: { department: string; value: number }[];
  leave_by_type: { name: string; value: number }[];
  top_late_comers: { employee: string; department: string; late_count: number }[];
  today_status: { check_in: string; check_out: string | null; work_duration: string; status: string };
};

const demoBullets = ["Attendance rate this month is 78%, a 6% improvement compared to last month.", "Operations department has the highest absenteeism with 8 employees.", "Annual Leave accounts for 47% of all leave requests.", "Late arrivals have decreased by 20% compared to last month."];

export function HrDashboard({ data }: { data: HrDashboardData }) {
  const summary = useMutation({ mutationFn: () => api.post<{ bullets: string[] }>("/ai/summary", { kpis: data }), onError: (error) => toast.error(error.message) });
  const bullets = summary.data?.bullets ?? (USE_MOCKS ? demoBullets : []);
  const trend = data.attendance_trend.map((value, index) => ({ day: index + 1, value }));
  const leaveColors = ["#0f9488", "#59aaf5", "#ff9d6b", "#9b72d7", "#cbd5e1"];
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Headcount" value={data.headcount} detail="Total active employees" icon={Users} change="2%" />
        <KpiCard label="Present today" value={data.present_today} detail="81% of total employees" icon={CalendarCheck} tone="green" change="5%" />
        <KpiCard label="On leave" value={data.on_leave_today} detail="Of total employees" icon={Umbrella} tone="blue" change="12%" />
        <KpiCard label="Late today" value={data.late_today} detail="Of present employees" icon={Clock3} tone="orange" change="7%" />
        <KpiCard label="Pending approvals" value={data.pending_approvals} detail="Leave or correction requests" icon={FileClock} tone="amber" change="-" changeDirection="flat" />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.25fr_1fr_1fr]">
        <ChartCard title="Attendance rate" filter="Last 30 days">
          <div className="h-52"><ResponsiveContainer width="100%" height="100%"><LineChart data={trend}><CartesianGrid stroke="#e8edf2" vertical={false} /><XAxis dataKey="day" tick={{ fontSize: 10 }} tickFormatter={(value) => `${value} Oct`} interval={4} /><YAxis domain={[0, 100]} tick={{ fontSize: 10 }} tickFormatter={(value) => `${value}%`} /><Tooltip /><Line type="monotone" dataKey="value" stroke="#0f9488" strokeWidth={2} dot={{ r: 3, fill: "#0f9488" }} /></LineChart></ResponsiveContainer></div>
        </ChartCard>
        <ChartCard title="Absenteeism by department">
          <div className="h-52"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.absenteeism_by_dept}><CartesianGrid stroke="#e8edf2" vertical={false} /><XAxis dataKey="department" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="value" fill="#159f95" radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer></div>
        </ChartCard>
        <ChartCard title="Leave by type">
          <div className="flex h-52 items-center"><ResponsiveContainer width="48%" height="100%"><PieChart><Pie data={data.leave_by_type} dataKey="value" innerRadius={44} outerRadius={72} paddingAngle={1}>{data.leave_by_type.map((item, index) => <Cell key={item.name} fill={leaveColors[index]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer><div className="min-w-0 flex-1 space-y-2">{data.leave_by_type.map((item, index) => <div key={item.name} className="flex items-center justify-between gap-2 text-[11px]"><span className="flex min-w-0 items-center gap-2"><i className="size-2.5 shrink-0 rounded-full" style={{ background: leaveColors[index] }} /><span className="truncate text-muted">{item.name}</span></span><strong>{item.value}</strong></div>)}</div></div>
        </ChartCard>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.1fr_1fr_0.8fr]">
        <ChartCard title="Top 5 late-comers" filter="This month">
          <div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="text-muted"><tr><th className="py-2">#</th><th>Employee</th><th>Department</th><th>Late Count</th></tr></thead><tbody>{data.top_late_comers.map((item, index) => <tr key={item.employee} className="border-t border-line"><td className="py-2">{index + 1}</td><td><span className="inline-flex items-center gap-2"><span className="flex size-7 items-center justify-center rounded-full bg-slate-100 text-[10px]">{initials(item.employee)}</span>{item.employee}</span></td><td>{item.department}</td><td className="font-semibold">{item.late_count}</td></tr>)}</tbody></table></div>
        </ChartCard>
        <ChartCard title="AI summary" filter={false}>
          <div className="min-h-48 rounded-lg bg-teal-50 p-4">
            <div className="mb-2 flex items-center justify-between"><Sparkles className="size-5 text-primary" /><span className="rounded-full bg-slate-200 px-2 py-1 text-[10px] text-slate-600">AI-generated</span></div>
            {summary.isPending ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-6 animate-pulse rounded bg-white/70" />)}</div> : bullets.length ? <ul className="space-y-2 text-xs leading-5 text-slate-700">{bullets.map((item) => <li key={item} className="flex gap-2"><span className="mt-2 size-1.5 shrink-0 rounded-full bg-primary" />{item}</li>)}</ul> : <p className="py-8 text-center text-xs text-muted">Select Summarize to create dashboard insights.</p>}
          </div>
        </ChartCard>
        <ChartCard title="My check-in" filter={false}>
          <div className="flex min-h-48 flex-col">
            <div className="flex items-center justify-center gap-3 rounded-lg bg-slate-50 p-3"><span className="text-2xl font-bold">09:12 AM</span><StatusBadge status="Checked in" dot /></div>
            <dl className="mt-4 space-y-2 text-xs"><div className="flex justify-between"><dt className="text-muted">Check-in time</dt><dd>09:12 AM</dd></div><div className="flex justify-between"><dt className="text-muted">Work duration</dt><dd>{data.today_status.work_duration}</dd></div><div className="flex justify-between"><dt className="text-muted">Status</dt><dd>{data.today_status.status}</dd></div></dl>
            <Button className="mt-auto" onClick={() => toast.success("Check-out request sent")}>Check out</Button>
          </div>
        </ChartCard>
      </div>
      <div className="mt-4 flex justify-end"><Button onClick={() => summary.mutate()} disabled={summary.isPending}><Sparkles className="size-4" />{summary.isPending ? "Summarizing..." : "Refresh summary"}</Button></div>
    </>
  );
}
