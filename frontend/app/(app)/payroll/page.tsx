"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, LockKeyhole, MoreHorizontal, Play } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ListResponse } from "@/lib/types";
import { usePageTitle } from "@/hooks/use-page-title";

type PayrollRun = { id: string; month: string; status: string; employee_count: number; total_gross: number; total_deductions: number; total_tax: number; total_net: number; created_by: string; created_at: string };

export default function PayrollPage() {
  usePageTitle("Payroll");
  const { role } = useAuth();
  const router = useRouter();
  const client = useQueryClient();
  const [month, setMonth] = useState("2026-10");
  useEffect(() => { if (role === "employee") router.replace("/dashboard"); }, [role, router]);
  const query = useQuery({ queryKey: ["payroll-runs"], queryFn: () => api.get<ListResponse<PayrollRun>>("/payroll/runs"), enabled: role !== "employee" });
  const runPayroll = useMutation({ mutationFn: () => api.post<PayrollRun>("/payroll/runs", { month }), onSuccess: (run) => { toast.success("Payroll draft created"); void client.invalidateQueries({ queryKey: ["payroll-runs"] }); router.push(`/payroll/${run.id}`); } });
  if (role === "employee") return null;
  if (query.isLoading) return <LoadingSkeleton rows={5} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const items = query.data?.items ?? [];
  return <div className="space-y-5"><div className="text-xs text-muted">Payroll&nbsp;&nbsp;/&nbsp;&nbsp;Payroll runs</div><PageHeader title="Payroll" subtitle="Manage monthly payroll runs, view status and payroll summaries." actions={role === "hr" ? <><div className="relative"><CalendarDays className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" /><Input type="month" value={month} onChange={(event) => setMonth(event.target.value)} className="w-52 pl-10" /></div><Button onClick={() => runPayroll.mutate()} disabled={runPayroll.isPending}><Play className="size-4" />{runPayroll.isPending ? "Running..." : "Run payroll"}</Button></> : undefined} />{runPayroll.isError && <p className="text-sm text-red-600">{(runPayroll.error as ApiError).message}</p>}
    {!items.length ? <EmptyState title="No payroll runs" description="Create the first payroll draft for a month." /> : <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-4">#</th><th>Month</th><th>Status</th><th>Employees</th><th>Total gross (PKR)</th><th>Total net (PKR)</th><th>Created by</th><th>Actions</th></tr></thead><tbody>{items.map((item, index) => <tr key={item.id} className="border-b border-line last:border-0"><td className="px-4 py-5">{index + 1}</td><td><Link href={`/payroll/${item.id}`} className="font-semibold hover:text-primary">{monthLabel(item.month)}</Link></td><td><StatusBadge status={title(item.status)} />{item.status === "finalized" && <LockKeyhole className="ml-1 inline size-3 text-emerald-600" />}</td><td>{item.employee_count}</td><td>{item.total_gross.toLocaleString()}</td><td>{item.total_net.toLocaleString()}</td><td><strong>{item.created_by}</strong><p className="text-xs text-muted">{item.created_at.replace("T", " ").slice(0, 16)}</p></td><td><Button size="icon" variant="ghost" asChild><Link href={`/payroll/${item.id}`}><MoreHorizontal className="size-4" /></Link></Button></td></tr>)}</tbody></table></div></section>}
  </div>;
}
function monthLabel(month: string) { return new Intl.DateTimeFormat("en", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`)); }
function title(value: string) { return value[0].toUpperCase() + value.slice(1); }
