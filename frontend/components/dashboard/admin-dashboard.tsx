"use client";

import { Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CircleDollarSign, Coins, TrendingDown, Users } from "lucide-react";
import { format } from "date-fns";
import { AnnouncementsCard } from "@/components/dashboard/announcements-card";
import { ChartCard } from "@/components/dashboard/chart-card";
import { KpiCard } from "@/components/kpi-card";

export type AdminDashboardData = {
  headcount: number;
  attrition_ytd: number;
  payroll_cost: number;
  avg_salary: number;
  headcount_by_dept: { department: string; value: number }[];
  payroll_cost_by_dept: { department: string; value: number }[];
  gender: { name: string; value: number }[];
  tenure: { name: string; value: number }[];
  recent_audit: { id: string; created_at: string; actor: string; action: string; detail: string }[];
};

const money = (value: number) => `PKR ${value.toLocaleString("en-PK")}`;

export function AdminDashboard({ data }: { data: AdminDashboardData }) {
  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Headcount" value={data.headcount} detail="Total active employees" icon={Users} change="2%" />
        <KpiCard label="Attrition YTD" value={`${data.attrition_ytd}%`} detail="Employee turnover rate" icon={TrendingDown} tone="green" change="1.2%" changeDirection="down" />
        <KpiCard label="Payroll cost" value={money(data.payroll_cost)} detail="Total gross salary this month" icon={CircleDollarSign} tone="orange" change="3%" />
        <KpiCard label="Average salary" value={money(data.avg_salary)} detail="Average monthly gross salary" icon={Coins} tone="blue" change="2%" />
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.25fr_1.15fr_0.75fr]">
        <ChartCard title="Headcount by department"><div className="h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.headcount_by_dept}><CartesianGrid stroke="#e8edf2" vertical={false} /><XAxis dataKey="department" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} /><Tooltip /><Bar dataKey="value" fill="#159f95" radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer></div></ChartCard>
        <ChartCard title="Payroll cost by department"><div className="h-56"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.payroll_cost_by_dept}><CartesianGrid stroke="#e8edf2" vertical={false} /><XAxis dataKey="department" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 10 }} tickFormatter={(value) => `${(value / 1000000).toFixed(1)}M`} /><Tooltip formatter={(value) => money(Number(value))} /><Bar dataKey="value" fill="#42b5ac" radius={[2, 2, 0, 0]} /></BarChart></ResponsiveContainer></div></ChartCard>
        <div className="grid gap-4">
          <ChartCard title="Gender" filter={false}><div className="flex h-[88px] items-center"><ResponsiveContainer width="50%" height="100%"><PieChart><Pie data={data.gender} dataKey="value" innerRadius={27} outerRadius={42}>{data.gender.map((item, index) => <Cell key={item.name} fill={index === 0 ? "#0f9488" : "#59aaf5"} />)}</Pie></PieChart></ResponsiveContainer><div className="space-y-2 text-xs">{data.gender.map((item, index) => <p key={item.name}><i className="mr-2 inline-block size-2 rounded-full" style={{ backgroundColor: index === 0 ? "#0f9488" : "#59aaf5" }} />{item.name} <strong className="ml-2">{item.value}</strong></p>)}</div></div></ChartCard>
          <ChartCard title="Tenure" filter={false}><div className="h-[88px]"><ResponsiveContainer width="100%" height="100%"><BarChart data={data.tenure}><XAxis dataKey="name" tick={{ fontSize: 8 }} /><Tooltip /><Bar dataKey="value" fill="#159f95" /></BarChart></ResponsiveContainer></div></ChartCard>
        </div>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-[1.3fr_1fr]">
        <section className="card p-5">
          <div className="mb-3 flex justify-between"><h2 className="text-lg font-semibold">Recent activity</h2><button className="text-xs font-medium text-primary">View all</button></div>
          {data.recent_audit.length ? <div className="overflow-x-auto"><table className="w-full min-w-[650px] text-left text-xs"><thead className="text-muted"><tr><th className="pb-2">Date & time</th><th>User</th><th>Action</th><th>Details</th></tr></thead><tbody>{data.recent_audit.map((item, index) => <tr key={item.id} className="border-t border-line"><td className="py-2"><span className="mr-3 inline-block size-2 rounded-full" style={{ backgroundColor: ["#60a5fa", "#22c55e", "#0f9488", "#94a3b8"][index] }} />{format(new Date(item.created_at), "dd MMM yyyy, hh:mm a")}</td><td>{item.actor}</td><td>{item.action}</td><td>{item.detail}</td></tr>)}</tbody></table></div> : <p className="py-10 text-center text-sm text-muted">No recent activity.</p>}
        </section>
        <AnnouncementsCard />
      </div>
    </>
  );
}
