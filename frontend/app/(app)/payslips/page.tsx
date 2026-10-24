"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Download, Printer } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ListResponse } from "@/lib/types";
import { usePageTitle } from "@/hooks/use-page-title";

type Payslip = { id: string; month: string; status: string; pay_date: string; employee_code: string; employee_name: string; department: string; gross: number; attendance_deduction: number; tax: number; net: number };

export default function PayslipsPage() {
  usePageTitle("My payslips");
  const { role } = useAuth();
  const router = useRouter();
  const [selected, setSelected] = useState<Payslip | null>(null);
  useEffect(() => { if (role !== "employee") router.replace("/dashboard"); }, [role, router]);
  const query = useQuery({ queryKey: ["my-payslips"], queryFn: () => api.get<ListResponse<Payslip>>("/payslips/me"), enabled: role === "employee" });
  const download = useMutation({ mutationFn: async (payslip: Payslip) => ({ blob: await api.download(`/payslips/${payslip.id}/pdf`), payslip }), onSuccess: ({ blob, payslip }) => { const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = `payslip-${payslip.month}.pdf`; link.click(); URL.revokeObjectURL(url); toast.success("Payslip downloaded"); } });
  if (role !== "employee") return null;
  if (query.isLoading) return <LoadingSkeleton rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const items = query.data?.items ?? [];
  const preview = selected ?? items[0] ?? null;
  return <div className="space-y-5"><PageHeader title="My payslips" subtitle="View and download your monthly payslips." />{!items.length ? <EmptyState title="No payslips available" description="Finalized payslips will appear here." /> : <div className="grid gap-5 xl:grid-cols-[1.05fr_0.75fr]">
    <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-4">#</th><th>Month</th><th>Gross (PKR)</th><th>Deductions (PKR)</th><th>Tax (PKR)</th><th>Net pay (PKR)</th><th>Actions</th></tr></thead><tbody>{items.map((item, index) => <tr key={item.id} onClick={() => setSelected(item)} className={`cursor-pointer border-b border-line ${preview?.id === item.id ? "bg-teal-50" : "hover:bg-slate-50"}`}><td className="px-4 py-4">{index + 1}</td><td className="font-semibold">{monthLabel(item.month)}</td><td>{item.gross.toLocaleString()}</td><td>{item.attendance_deduction.toLocaleString()}</td><td>{item.tax.toLocaleString()}</td><td className="font-semibold">{item.net.toLocaleString()}</td><td><Button size="sm" variant="outline" onClick={(event) => { event.stopPropagation(); download.mutate(item); }} disabled={download.isPending}><Download className="size-4" />Download PDF</Button></td></tr>)}</tbody></table></div></section>
    {preview && <PayslipPreview payslip={preview} onDownload={() => download.mutate(preview)} />}
  </div>}</div>;
}

function PayslipPreview({ payslip, onDownload }: { payslip: Payslip; onDownload: () => void }) {
  return <aside className="rounded-lg bg-slate-800 p-3 shadow-xl"><div className="flex items-center justify-between px-3 pb-3 text-white"><span className="text-xs">1 / 1</span><div className="flex gap-2"><Button size="icon" variant="ghost" className="text-white hover:bg-white/10" onClick={onDownload}><Download className="size-4" /></Button><Button size="icon" variant="ghost" className="text-white hover:bg-white/10"><Printer className="size-4" /></Button></div></div><div className="min-h-[720px] bg-white p-7 text-xs text-slate-700"><div className="flex justify-between border-b-2 border-primary pb-4"><div><h2 className="text-3xl font-bold text-primary">HCM<span className="ml-1 text-ink">Lite</span></h2><strong className="mt-4 block">HCM Lite (Pvt.) Ltd.</strong><p>123 Business Avenue, Karachi, Pakistan</p></div><div className="text-right"><h3 className="text-xl font-bold text-ink">Monthly Payslip</h3><p className="mt-2 font-semibold">{monthLabel(payslip.month)}</p></div></div><div className="grid grid-cols-2 gap-2 py-5"><p>Employee Name: <strong>{payslip.employee_name}</strong></p><p>Pay Period: <strong>{monthLabel(payslip.month)}</strong></p><p>Employee Code: <strong>{payslip.employee_code}</strong></p><p>Pay Date: <strong>{payslip.pay_date}</strong></p><p>Department: <strong>{payslip.department}</strong></p><p>Employment Type: <strong>Full Time</strong></p></div><PreviewSection title="Earnings" rows={[["Gross pay", payslip.gross]]} totalLabel="Total Gross" total={payslip.gross} tone="teal" /><PreviewSection title="Deductions" rows={[["Attendance deductions", payslip.attendance_deduction]]} totalLabel="Total Deductions" total={payslip.attendance_deduction} tone="red" /><PreviewSection title="Tax" rows={[["Income Tax", payslip.tax]]} totalLabel="Total Tax" total={payslip.tax} tone="red" /><div className="mt-6 flex justify-between rounded bg-teal-100 p-4 text-lg font-bold text-ink"><span>Net Pay</span><span>{payslip.net.toLocaleString()}</span></div><p className="mt-5 text-[10px] text-muted">This is a system generated payslip and does not require a signature.</p></div></aside>;
}

function PreviewSection({ title, rows, totalLabel, total, tone }: { title: string; rows: [string, number][]; totalLabel: string; total: number; tone: "teal" | "red" }) { return <section className="mt-5"><h4 className="mb-2 text-base font-bold text-ink">{title}</h4><div className="border border-line"><div className="flex justify-between bg-slate-100 px-3 py-2 font-semibold"><span>Description</span><span>Amount (PKR)</span></div>{rows.map(([label, value]) => <div key={label} className="flex justify-between px-3 py-2"><span>{label}</span><span>{value.toLocaleString()}</span></div>)}<div className={`flex justify-between px-3 py-2 font-bold ${tone === "teal" ? "bg-teal-50" : "bg-red-50"}`}><span>{totalLabel}</span><span>{total.toLocaleString()}</span></div></div></section>; }
function monthLabel(month: string) { return new Intl.DateTimeFormat("en", { month: "long", year: "numeric", timeZone: "UTC" }).format(new Date(`${month}-01T00:00:00Z`)); }
