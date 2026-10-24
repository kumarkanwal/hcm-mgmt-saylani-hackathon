"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, Infinity as InfinityIcon, Leaf, Sparkles, Stethoscope } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Tabs } from "@/components/tabs";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Department, LeaveType, ListResponse } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type Balance = { leave_type: string; quota: number | null; used: number; pending: number; remaining: number | null };
type LeaveRequest = { id: string; employee_id: string; employee_code: string; employee_name: string; department: string; leave_type_id: string; leave_type: string; start_date: string; end_date: string; working_days: number; reason: string; status: string; comment: string | null; created_at: string };
type SmartLeave = { leave_type: string; start_date: string; end_date: string; reason: string };

export default function LeavesPage() {
  usePageTitle("Leaves");
  const { role } = useAuth();
  return role === "employee" ? <EmployeeLeaves /> : <LeaveInbox role={role ?? "hr"} />;
}

function LeaveInbox({ role }: { role: string }) {
  const client = useQueryClient();
  const [status, setStatus] = useState("pending");
  const [departmentId, setDepartmentId] = useState("");
  const [selection, setSelection] = useState<{ item: LeaveRequest; action: "approve" | "reject" } | null>(null);
  const [comment, setComment] = useState("");
  const query = useQuery({ queryKey: ["leaves", status, departmentId], queryFn: () => api.get<ListResponse<LeaveRequest>>("/leaves", { status, department_id: departmentId }) });
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => api.get<ListResponse<Department>>("/departments") });
  const decision = useMutation({ mutationFn: () => api.patch(`/leaves/${selection?.item.id}/decision`, { action: selection?.action, comment }), onSuccess: () => { toast.success(selection?.action === "approve" ? "Leave approved" : "Leave rejected"); setSelection(null); setComment(""); void client.invalidateQueries({ queryKey: ["leaves"] }); } });
  if (query.isLoading) return <LoadingSkeleton rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const items = query.data?.items ?? [];
  return <div className="space-y-5"><div className="text-xs text-muted">Leaves&nbsp;&nbsp;/&nbsp;&nbsp;Leave requests</div><PageHeader title="Leave requests" subtitle="Review and manage employee leave requests." actions={<><Button variant="outline"><CalendarDays className="size-4" />01 Oct 2026 - 31 Oct 2026</Button><Select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)} className="w-52"><option value="">All Departments</option>{departments.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select><Button variant="ghost" onClick={() => setDepartmentId("")}>Clear filters</Button></>} /><Tabs items={[{ value: "pending", label: "Pending", count: 5 }, { value: "approved", label: "Approved", count: 12 }, { value: "rejected", label: "Rejected", count: 3 }, { value: "all", label: "All", count: 20 }]} value={status} onChange={setStatus} />
    {!items.length ? <EmptyState title="No leave requests" description={`There are no ${status} leave requests.`} /> : <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[1100px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">#</th><th>Employee</th><th>Department</th><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Reason</th><th>Status</th><th>Actions</th></tr></thead><tbody>{items.map((item, index) => <tr key={item.id} className="border-b border-line"><td className="px-4 py-3">{index + 1}</td><td><div className="flex items-center gap-2"><span className="flex size-8 items-center justify-center rounded-full bg-slate-100 text-[10px]">{initials(item.employee_name)}</span><div><strong>{item.employee_name}</strong><p className="text-xs text-muted">{item.employee_code}</p></div></div></td><td>{item.department}</td><td><span className="rounded-full bg-blue-50 px-3 py-1 text-xs text-blue-700">{item.leave_type}</span></td><td>{item.start_date}</td><td>{item.end_date}</td><td>{item.working_days}</td><td className="max-w-44">{item.reason}</td><td><StatusBadge status={title(item.status)} /></td><td>{role === "hr" && item.status === "pending" ? <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => setSelection({ item, action: "approve" })}>Approve</Button><Button size="sm" variant="danger" onClick={() => setSelection({ item, action: "reject" })}>Reject</Button></div> : <Button size="sm" variant="outline" disabled>View</Button>}</td></tr>)}</tbody></table></div><div className="border-t border-line p-4 text-sm text-muted">Showing 1 to {items.length} of {query.data?.total ?? items.length} requests</div></section>}
    <Dialog open={Boolean(selection)} onOpenChange={(open) => !open && setSelection(null)}><DialogContent><DialogTitle>{selection?.action === "approve" ? "Approve leave request" : "Reject leave request"}</DialogTitle><DialogDescription>{selection?.item.employee_name} requested {selection?.item.working_days} day(s) of {selection?.item.leave_type} leave.</DialogDescription><div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm"><p><span className="text-muted">Leave period:</span> {selection?.item.start_date} - {selection?.item.end_date}</p><p className="mt-2"><span className="text-muted">Reason:</span> {selection?.item.reason}</p></div><label className="mt-4 block text-sm font-semibold">{selection?.action === "approve" ? "Approval comment (optional)" : "Rejection comment"}</label><Textarea className="mt-2" value={comment} onChange={(event) => setComment(event.target.value)} /><div className="mt-5 flex justify-end gap-3"><Button variant="outline" onClick={() => setSelection(null)}>Cancel</Button><Button variant={selection?.action === "reject" ? "danger" : "default"} disabled={decision.isPending || (selection?.action === "reject" && !comment)} onClick={() => decision.mutate()}>{decision.isPending ? "Saving..." : title(selection?.action ?? "approve")}</Button></div></DialogContent></Dialog>
  </div>;
}

function EmployeeLeaves() {
  const client = useQueryClient();
  const [smartText, setSmartText] = useState("");
  const [aiFilled, setAiFilled] = useState(false);
  const [leaveTypeId, setLeaveTypeId] = useState("");
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [reason, setReason] = useState("");
  const balance = useQuery({ queryKey: ["leave-balance"], queryFn: () => api.get<Balance[]>("/leaves/balance") });
  const history = useQuery({ queryKey: ["my-leaves"], queryFn: () => api.get<ListResponse<LeaveRequest>>("/leaves/me") });
  const leaveTypes = useQuery({ queryKey: ["leave-types"], queryFn: () => api.get<ListResponse<LeaveType>>("/leave-types") });
  const smart = useMutation({ mutationFn: () => api.post<SmartLeave>("/ai/smart-leave", { text: smartText }), onSuccess: (data) => { const type = leaveTypes.data?.items.find((item) => item.code === data.leave_type); setLeaveTypeId(type?.id ?? ""); setStartDate(data.start_date); setEndDate(data.end_date); setReason(data.reason); setAiFilled(true); }, onError: () => { setLeaveTypeId(""); setStartDate(""); setEndDate(""); setReason(""); setAiFilled(false); toast.info("The request could not be parsed. Complete the form manually."); } });
  const apply = useMutation({ mutationFn: () => api.post("/leaves", { leave_type_id: leaveTypeId, start_date: startDate, end_date: endDate, reason }), onSuccess: () => { toast.success("Leave request submitted"); setLeaveTypeId(""); setStartDate(""); setEndDate(""); setReason(""); setAiFilled(false); void client.invalidateQueries({ queryKey: ["my-leaves"] }); } });
  const cancel = useMutation({ mutationFn: (id: string) => api.post(`/leaves/${id}/cancel`), onSuccess: () => { toast.success("Leave request cancelled"); void client.invalidateQueries({ queryKey: ["my-leaves"] }); } });
  if (balance.isLoading || history.isLoading || leaveTypes.isLoading) return <LoadingSkeleton cards={4} rows={6} />;
  if (balance.isError || history.isError || leaveTypes.isError) { const error = balance.error ?? history.error ?? leaveTypes.error; return <ErrorState message={(error as Error).message} onRetry={() => { balance.refetch(); history.refetch(); leaveTypes.refetch(); }} />; }
  const icons = [Leaf, Stethoscope, CalendarDays, InfinityIcon];
  return <div className="space-y-5"><PageHeader title="Leaves" subtitle="Apply for leave, view your balance and track your leave history." />
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{balance.data?.map((item, index) => { const Icon = icons[index]; return <div key={item.leave_type} className="card p-4"><div className="flex items-center gap-4"><span className="flex size-12 items-center justify-center rounded-full bg-teal-50 text-primary"><Icon className="size-6" /></span><div><p className="text-xs text-muted">{item.leave_type}</p><strong className="text-xl">{item.remaining === null ? "Unlimited" : `${item.remaining} / ${item.quota}`}</strong><p className="text-xs text-muted">{item.remaining === null ? "No yearly limit" : "days remaining"}</p></div></div><div className="mt-4 h-2 rounded-full bg-slate-200"><div className="h-full rounded-full bg-primary" style={{ width: item.quota ? `${(Number(item.remaining) / item.quota) * 100}%` : "0%" }} /></div></div>; })}</div>
    <section className="card bg-gradient-to-r from-teal-50 to-white p-5"><div className="flex items-start gap-4"><Sparkles className="mt-1 size-6 text-primary" /><div className="flex-1"><h2 className="font-semibold">Smart leave</h2><p className="text-xs text-muted">Describe your leave in simple words and let AI fill the form for you.</p><div className="mt-3 flex flex-col gap-3 sm:flex-row"><Input value={smartText} onChange={(event) => setSmartText(event.target.value)} placeholder="Need next Monday and Tuesday off for a family event" /><Button disabled={!smartText || smart.isPending} onClick={() => smart.mutate()}>{smart.isPending ? "Filling..." : "Fill form"}</Button></div></div></div></section>
    <section className="card p-5"><div className="flex items-center justify-between"><h2 className="font-semibold">Apply for leave</h2>{aiFilled && <span className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-600">AI-generated draft, please review</span>}</div><div className="mt-4 grid gap-4 md:grid-cols-3"><label className="text-sm font-medium">Leave type<Select value={leaveTypeId} onChange={(event) => setLeaveTypeId(event.target.value)} className="mt-2"><option value="">Select leave type</option>{leaveTypes.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label><label className="text-sm font-medium">From date<Input type="date" value={startDate} onChange={(event) => setStartDate(event.target.value)} className="mt-2" /></label><label className="text-sm font-medium">To date<Input type="date" value={endDate} onChange={(event) => setEndDate(event.target.value)} className="mt-2" /></label></div><label className="mt-4 block text-sm font-medium">Reason<Textarea value={reason} onChange={(event) => setReason(event.target.value)} className="mt-2" /></label>{apply.isError && <p className="mt-3 text-sm text-red-600">{(apply.error as ApiError).message}</p>}<div className="mt-4 flex justify-end gap-3"><Button variant="outline" onClick={() => { setLeaveTypeId(""); setStartDate(""); setEndDate(""); setReason(""); }}>Cancel</Button><Button disabled={!leaveTypeId || !startDate || !endDate || !reason || apply.isPending} onClick={() => apply.mutate()}>{apply.isPending ? "Applying..." : "Apply"}</Button></div></section>
    <section className="card overflow-hidden"><h2 className="p-5 font-semibold">My leave history</h2>{history.data?.items.length ? <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">#</th><th>Type</th><th>From</th><th>To</th><th>Days</th><th>Reason</th><th>Status</th><th>Applied on</th><th>Action</th></tr></thead><tbody>{history.data.items.map((item, index) => <tr key={item.id} className="border-t border-line"><td className="px-4 py-3">{index + 1}</td><td>{item.leave_type}</td><td>{item.start_date}</td><td>{item.end_date}</td><td>{item.working_days}</td><td>{item.reason}</td><td><StatusBadge status={title(item.status)} /></td><td>{item.created_at.slice(0, 10)}</td><td>{item.status === "pending" ? <button className="font-medium text-primary" onClick={() => cancel.mutate(item.id)}>Cancel</button> : "-"}</td></tr>)}</tbody></table></div> : <EmptyState title="No leave history" description="Your leave requests will appear here." />}</section>
  </div>;
}

function title(value: string) { return value ? value[0].toUpperCase() + value.slice(1) : value; }
