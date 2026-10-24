"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Sparkles } from "lucide-react";
import { AdminDashboard, type AdminDashboardData } from "@/components/dashboard/admin-dashboard";
import { EmployeeDashboard, type EmployeeDashboardData } from "@/components/dashboard/employee-dashboard";
import { HrDashboard, type HrDashboardData } from "@/components/dashboard/hr-dashboard";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePageTitle } from "@/hooks/use-page-title";

type DashboardData = AdminDashboardData | HrDashboardData | EmployeeDashboardData;

export default function DashboardPage() {
  usePageTitle("Dashboard");
  const { role = "hr" } = useAuth();
  const endpoint = role === "admin" ? "/dashboard/admin" : role === "employee" ? "/dashboard/me" : "/dashboard/hr";
  const query = useQuery({ queryKey: ["dashboard", role], queryFn: () => api.get<DashboardData>(endpoint) });
  const subtitle = role === "admin" ? "Overview of your company's people, payroll and activity." : role === "hr" ? "Overview of your company's people, attendance and leave activity." : "Welcome back, Ali Raza. Here is your overview.";
  return (
    <div className="space-y-6">
      <PageHeader title="Dashboard" subtitle={subtitle} actions={role !== "employee" ? <><Button variant="outline"><CalendarDays className="size-4" />01 Oct 2026&nbsp; - &nbsp;31 Oct 2026</Button><Select defaultValue="all" className="w-48"><option value="all">All Departments</option></Select><Button><Sparkles className="size-4" />Summarize</Button></> : <div className="text-right text-sm text-muted"><p>Today</p><p className="font-medium text-slate-700">Thu, 23 Oct 2026</p></div>} />
      {query.isLoading ? <LoadingSkeleton cards={role === "hr" ? 5 : 4} rows={5} /> : query.isError ? <ErrorState message={query.error.message} onRetry={() => query.refetch()} /> : role === "admin" ? <AdminDashboard data={query.data as AdminDashboardData} /> : role === "employee" ? <EmployeeDashboard data={query.data as EmployeeDashboardData} /> : <HrDashboard data={query.data as HrDashboardData} />}
    </div>
  );
}
