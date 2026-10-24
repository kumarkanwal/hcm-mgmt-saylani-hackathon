"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Coins, FileText, LockKeyhole, MoreHorizontal, RefreshCcw, WalletCards } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type Payslip = { id: string; employee_id: string; employee_code: string; employee_name: string; department: string; gross: number; working_days: number; absent_days: number; unpaid_leave_days: number; half_days: number; attendance_deduction: number; tax: number; net: number };
type PayrollDetail = { id: string; month: string; status: string; employee_count: number; total_gross: number; total_deductions: number; total_tax: number; total_net: number; payslips: Payslip[] };
const money = (value: number) => `PKR ${value.toLocaleString("en-PK")}`;

export default function PayrollDetailPage() {
  const { id } = useParams<{ id: string }>();
  usePageTitle("Payroll run");
  const { role } = useAuth();
  const client = useQueryClient();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const query = useQuery({ queryKey: ["payroll-run", id], queryFn: () => api.get<PayrollDetail>(`/payroll/runs/${id}`) });
  const recalculate = useMutation({ mutationFn: () => api.post(`/payroll/runs/${id}/recalculate`), onSuccess: () => { toast.success("Payroll recalculated"); void client.invalidateQueries({ queryKey: ["payroll-run", id] }); } });
  const finalize = useMutation({ mutationFn: () => api.post(`/payroll/runs/${id}/finalize`), onSuccess: () => { toast.success("Payroll finalized"); setConfirmOpen(false); void client.invalidateQueries({ queryKey: ["payroll-run", id] }); } });
  if (query.isLoading) return <LoadingSkeleton cards={4} rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (!query.data) return null;
  const data = query.data;
  return <div className="space-y-5"><div className="text-xs text-muted">Payroll&nbsp;&nbsp;/&nbsp;&nbsp;Payroll runs&nbsp;&nbsp;/&nbsp;&nbsp;{monthLabel(data.month)}</div><PageHeader title={`Payroll run - ${monthLabel(data.month)}`} subtitle="Review employee payslips and finalize the payroll for this month." actions={<div className="flex gap-3">{data.status === "draft" && role === "hr" && <Button variant="outline" onClick={() => recalculate.mutate()} disabled={recalculate.isPending}><RefreshCcw className="size-4" />{recalculate.isPending ? "Recalculating..." : "Recalculate"}</Button>}{data.status === "draft" && role === "admin" && <Button onClick={() => setConfirmOpen(true)}><LockKeyhole className="size-4" />Finalize payroll</Button>}<StatusBadge status={title(data.status)} /></div>} />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><Total icon={Coins} label="Total gross" value={money(data.total_gross)} tone="green" /><Total icon={WalletCards} label="Total deductions" value={money(data.total_deductions)} tone="red" /><Total icon={FileText} label="Total tax" value={money(data.total_tax)} tone="amber" /><Total icon={WalletCards} label="Total net" value={money(data.total_net)} tone="green" /></div>
    {!data.payslips.length ? <EmptyState title="No payslips" description="Recalculate this run after employees and attendance are available." /> : <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[1150px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">#</th><th>Employee</th><th>Gross (PKR)</th><th>Working days</th><th>Absent</th><th>Unpaid</th><th>Half days</th><th>Deduction (PKR)</th><th>Tax (PKR)</th><th>Net (PKR)</th><th /></tr></thead><tbody>{data.payslips.map((item, index) => <tr key={item.id} className="border-b border-line"><td className="px-4 py-3">{index + 1}</td><td><div className="flex items-center gap-2"><span className="flex size-8 items-center justify-center rounded-full bg-slate-100 text-[10px]">{initials(item.employee_name)}</span><div><strong>{item.employee_name}</strong><p className="text-xs text-muted">{item.employee_code}</p></div></div></td><td>{item.gross.toLocaleString()}</td><td>{item.working_days}</td><td>{item.absent_days}</td><td>{item.unpaid_leave_days}</td><td>{item.half_days}</td><td>{item.attendance_deduction.toLocaleString()}</td><td>{item.tax.toLocaleString()}</td><td className="font-semibold">{item.net.toLocaleString()}</td><td><MoreHorizontal className="size-4" /></td></tr>)}</tbody></table></div><div className="border-t border-line p-4 text-sm text-muted">Showing 1 to {data.payslips.length} of {data.employee_count} employees</div></section>}
    <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}><DialogContent><div className="flex gap-4"><span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700"><LockKeyhole className="size-6" /></span><div><DialogTitle>Finalize {monthLabel(data.month)}?</DialogTitle><DialogDescription>This will lock the month and all payslips cannot be changed. Confirm that you want to finalize this payroll.</DialogDescription></div></div><div className="mt-6 flex justify-end gap-3"><Button variant="outline" onClick={() => setConfirmOpen(false)}>Cancel</Button><Button onClick={() => finalize.mutate()} disabled={finalize.isPending}><LockKeyhole className="size-4" />{finalize.isPending ? "Finalizing..." : "Finalize payroll"}</Button></div></DialogContent></Dialog>
  </div>;
}
function Total({ icon: Icon, label, value, tone }: { icon: typeof Coins; label: string; value: string; tone: "green" | "red" | "amber" }) { const style = { green: "bg-emerald-50 text-emerald-600", red: "bg-red-50 text-red-600", amber: "bg-amber-50 text-amber-600" }[tone]; return <div className="card flex items-center gap-4 p-4"><span className={`flex size-12 items-center justify-center rounded-full ${style}`}><Icon className="size-6" /></span><div><p className="text-xs text-muted">{label}</p><strong className="mt-1 block text-xl">{value}</strong></div></div>; }
function monthLabel(month: string) { return new Intl.DateTimeFormat("en", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`)); }
function title(value: string) { return value[0].toUpperCase() + value.slice(1); }
