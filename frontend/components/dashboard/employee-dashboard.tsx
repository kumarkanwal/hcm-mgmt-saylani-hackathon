"use client";

import { CalendarCheck, Clock3, FileClock, FileText, Send, Umbrella } from "lucide-react";
import { format } from "date-fns";
import { toast } from "sonner";
import { AnnouncementsCard } from "@/components/dashboard/announcements-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/status-badge";

export type EmployeeDashboardData = {
  today_status: { date: string; status: string; check_in: string; check_out: string | null; work_duration: string };
  hours_this_week: number;
  daily_hours: { day: string; hours: number }[];
  late_count: number;
  leave_balance: { leave_type: string; quota: number | null; used: number; pending: number; remaining: number | null }[];
  last_payslip: { id: string; month: string; gross: number; deductions: number; tax: number; net: number } | null;
};

const money = (value: number) => `PKR ${value.toLocaleString("en-PK")}`;
const leaveStyles = ["text-emerald-600 bg-emerald-50", "text-blue-600 bg-blue-50", "text-orange-600 bg-orange-50", "text-slate-600 bg-slate-50"];
const leaveIcons = [CalendarCheck, Umbrella, FileClock, FileText];

export function EmployeeDashboard({ data }: { data: EmployeeDashboardData }) {
  return (
    <>
      <div className="grid gap-4 xl:grid-cols-[1fr_1fr_0.52fr]">
        <section className="card p-5">
          <div className="flex items-center justify-between"><h2 className="text-lg font-semibold">Today&apos;s check-in</h2><StatusBadge status="Present" dot /></div>
          <div className="mt-3 flex items-center gap-3 text-sm text-muted"><span className="flex size-10 items-center justify-center rounded-lg bg-teal-50 text-primary"><CalendarCheck className="size-5" /></span>{format(new Date(`${data.today_status.date}T12:00:00`), "EEEE, d MMMM yyyy")}</div>
          <p className="my-5 text-center text-3xl font-bold">02:36 PM</p>
          <div className="grid gap-3 sm:grid-cols-2"><div className="rounded-lg bg-teal-50 p-4"><p className="text-xs text-muted">Check-in time</p><strong>08:57 AM</strong></div><div className="rounded-lg bg-slate-50 p-4"><p className="text-xs text-muted">Work duration</p><strong>{data.today_status.work_duration}</strong></div></div>
          <Button className="mt-5 w-full" onClick={() => toast.success("Check-out request sent")}>Check out</Button>
        </section>
        <section className="card p-5">
          <div className="flex justify-between"><h2 className="text-lg font-semibold">Hours this week</h2><span className="text-sm text-muted">{data.hours_this_week} of 40 hours</span></div>
          <div className="mt-6 h-4 overflow-hidden rounded-full bg-slate-200"><div className="h-full bg-primary" style={{ width: `${Math.min(100, data.hours_this_week / 40 * 100)}%` }} /></div>
          <div className="mt-7 grid grid-cols-5 divide-x divide-line border-t border-line pt-4">{data.daily_hours.map((item) => <div key={item.day} className="text-center"><p className="text-xs text-muted">{item.day}</p><strong className="mt-2 block text-sm">{item.hours ? `${item.hours}h` : "-"}</strong></div>)}</div>
        </section>
        <section className="card p-5">
          <div className="flex gap-4"><span className="flex size-12 items-center justify-center rounded-xl bg-orange-50 text-orange-600"><Clock3 className="size-6" /></span><div><h2 className="text-sm font-semibold">Late this month</h2><p className="mt-2 text-3xl font-bold">{data.late_count}</p></div></div>
          <p className="mt-3 text-xs text-muted">You were late {data.late_count} time this month.</p>
        </section>
      </div>
      <section className="card mt-4 p-5 xl:ml-[34%]">
        <div className="flex justify-between"><h2 className="text-lg font-semibold">Leave balance</h2><button className="text-xs text-blue-600">View all</button></div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">{data.leave_balance.map((item, index) => { const Icon = leaveIcons[index]; return <div key={item.leave_type} className="rounded-lg border border-line p-3"><div className="flex gap-3"><span className={`flex size-9 items-center justify-center rounded-lg ${leaveStyles[index]}`}><Icon className="size-5" /></span><div><p className="text-xs">{item.leave_type}</p><p className="mt-2 text-sm"><strong>{item.remaining ?? "Unlimited"}</strong>{item.quota !== null && ` of ${item.quota}`}</p></div></div><div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-200"><div className="h-full rounded-full bg-primary" style={{ width: item.quota ? `${(Number(item.remaining) / item.quota) * 100}%` : "0%" }} /></div></div>; })}</div>
      </section>
      <div className="mt-4 grid gap-4 xl:grid-cols-[0.9fr_0.9fr_1fr]">
        <section className="card p-5"><div className="flex justify-between"><h2 className="text-lg font-semibold">Last payslip</h2><button className="text-xs text-blue-600">View all</button></div>{data.last_payslip ? <><div className="mt-4 rounded-lg bg-teal-50 p-5"><p className="text-sm font-semibold">September 2026</p><p className="mt-2 text-2xl font-bold">{money(data.last_payslip.net)}</p><p className="mt-1 text-xs text-primary">Net pay</p></div><dl className="divide-y divide-line text-xs"><div className="flex justify-between py-3"><dt className="text-muted">Gross pay</dt><dd>{money(data.last_payslip.gross)}</dd></div><div className="flex justify-between py-3"><dt className="text-muted">Total deductions</dt><dd>{money(data.last_payslip.deductions)}</dd></div><div className="flex justify-between py-3"><dt className="text-muted">Tax</dt><dd>{money(data.last_payslip.tax)}</dd></div></dl><Button variant="outline" className="w-full"><FileText className="size-4" />Download PDF</Button></> : <p className="py-10 text-center text-sm text-muted">No finalized payslips yet.</p>}</section>
        <AnnouncementsCard />
        <section className="card p-5"><h2 className="text-lg font-semibold">Ask my assistant</h2><p className="mt-2 text-sm text-muted">Ask HR related questions or get quick information.</p><div className="relative mt-5"><Input placeholder="Type your question here..." className="pr-12" /><Button size="icon" className="absolute right-1 top-1 size-9" onClick={() => toast.info("The assistant will be connected in a later phase.")}><Send className="size-4" /></Button></div><p className="mt-5 text-xs text-muted">Try asking:</p><div className="mt-3 flex flex-wrap gap-2">{["How many leaves do I have left?", "What is the office timing?", "Show my attendance for this month", "How to apply for leave?"].map((item) => <button key={item} className="rounded-full border border-line px-3 py-2 text-xs text-slate-600 hover:bg-slate-50">{item}</button>)}</div></section>
      </div>
    </>
  );
}
