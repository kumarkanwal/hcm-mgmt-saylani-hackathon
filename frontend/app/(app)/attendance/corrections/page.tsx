"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Tabs } from "@/components/tabs";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Department, ListResponse } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type Correction = { id: string; employee_id: string; employee_code: string; employee_name: string; department: string; date: string; requested_check_in: string; requested_check_out: string; reason: string; status: string; comment: string | null; created_at: string };

export default function CorrectionsPage() {
  usePageTitle("Attendance corrections");
  const { role } = useAuth();
  const client = useQueryClient();
  const [status, setStatus] = useState("pending");
  const [departmentId, setDepartmentId] = useState("");
  const [selection, setSelection] = useState<{ item: Correction; action: "approve" | "reject" } | null>(null);
  const [comment, setComment] = useState("");
  const query = useQuery({ queryKey: ["corrections", status, departmentId, role], queryFn: () => api.get<ListResponse<Correction>>("/attendance/corrections", { status, department_id: departmentId }) });
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => api.get<ListResponse<Department>>("/departments"), enabled: role !== "employee" });
  const decide = useMutation({ mutationFn: () => api.patch(`/attendance/corrections/${selection?.item.id}`, { action: selection?.action, comment }), onSuccess: () => { toast.success(selection?.action === "approve" ? "Correction approved" : "Correction rejected"); setSelection(null); setComment(""); void client.invalidateQueries({ queryKey: ["corrections"] }); } });
  if (query.isLoading) return <LoadingSkeleton rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const items = query.data?.items ?? [];
  return <div className="space-y-5">
    <div className="text-xs text-muted">Attendance&nbsp;&nbsp;/&nbsp;&nbsp;<span className="text-slate-700">Corrections</span></div>
    <PageHeader title="Attendance corrections" subtitle={role === "employee" ? "Track your attendance correction requests." : "Review and manage employee requests for attendance corrections."} actions={role !== "employee" ? <><Button variant="outline"><CalendarDays className="size-4" />01 Oct 2026 - 31 Oct 2026</Button><Select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)} className="w-52"><option value="">All Departments</option>{departments.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select><Button variant="ghost" onClick={() => setDepartmentId("")}>Clear filters</Button></> : undefined} />
    <Tabs items={[{ value: "pending", label: "Pending", count: 6 }, { value: "approved", label: "Approved", count: 12 }, { value: "rejected", label: "Rejected", count: 4 }]} value={status} onChange={setStatus} />
    {!items.length ? <EmptyState title="No correction requests" description={`There are no ${status} requests to show.`} /> : <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">#</th><th>Employee</th><th>Date</th><th>Requested check in</th><th>Requested check out</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead><tbody>{items.map((item, index) => <tr key={item.id} className="border-b border-line"><td className="px-4 py-3">{index + 1}</td><td><div className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-full bg-slate-100 text-[11px]">{initials(item.employee_name)}</span><div><strong>{item.employee_name}</strong><p className="text-xs text-muted">{item.employee_code}</p></div></div></td><td>{item.date}</td><td>{item.requested_check_in}</td><td>{item.requested_check_out}</td><td className="max-w-48">{item.reason}</td><td><StatusBadge status={capitalize(item.status)} /></td><td>{role === "hr" && item.status === "pending" ? <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => setSelection({ item, action: "approve" })}>Approve</Button><Button size="sm" variant="danger" onClick={() => setSelection({ item, action: "reject" })}>Reject</Button></div> : <Button size="sm" variant="outline" disabled>View</Button>}</td></tr>)}</tbody></table></div><div className="border-t border-line p-4 text-sm text-muted">Showing 1 to {items.length} of {query.data?.total ?? items.length} requests</div></section>}
    <Dialog open={Boolean(selection)} onOpenChange={(open) => !open && setSelection(null)}><DialogContent><DialogTitle>{selection?.action === "approve" ? "Approve correction request" : "Reject correction request"}</DialogTitle><DialogDescription>{selection?.action === "approve" ? "Confirm the corrected times for this request." : "Provide a reason for rejecting this request."}</DialogDescription><label className="mt-5 block text-sm font-semibold">Comment {selection?.action === "reject" && <span className="text-red-500">*</span>}</label><Textarea className="mt-2" value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Add a comment" /><div className="mt-5 flex justify-end gap-3"><Button variant="outline" onClick={() => setSelection(null)}>Cancel</Button><Button variant={selection?.action === "reject" ? "danger" : "default"} onClick={() => decide.mutate()} disabled={decide.isPending || (selection?.action === "reject" && !comment)}>{decide.isPending ? "Saving..." : selection?.action === "approve" ? "Approve" : "Reject"}</Button></div></DialogContent></Dialog>
  </div>;
}

function capitalize(value: string) { return value[0].toUpperCase() + value.slice(1); }
