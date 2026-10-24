"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MoreHorizontal, Pencil, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Tabs } from "@/components/tabs";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Department, Designation, Holiday, LeaveType, ListResponse } from "@/lib/types";
import { usePageTitle } from "@/hooks/use-page-title";

type Editor = { kind: "department" | "designation" | "leave-type" | "holiday"; id?: string; name?: string; code?: string; department_id?: string; yearly_quota?: number | null; is_paid?: boolean; date?: string };

export default function OrganizationPage() {
  usePageTitle("Organization settings");
  const { role } = useAuth();
  const router = useRouter();
  const client = useQueryClient();
  const [tab, setTab] = useState("departments");
  const [editor, setEditor] = useState<Editor | null>(null);
  const [remove, setRemove] = useState<{ kind: "department" | "holiday"; id: string; name: string } | null>(null);
  useEffect(() => { if (role === "employee") router.replace("/dashboard"); }, [role, router]);
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => api.get<ListResponse<Department>>("/departments"), enabled: role !== "employee" });
  const designations = useQuery({ queryKey: ["designations"], queryFn: () => api.get<ListResponse<Designation>>("/designations"), enabled: role !== "employee" });
  const leaveTypes = useQuery({ queryKey: ["leave-types"], queryFn: () => api.get<ListResponse<LeaveType>>("/leave-types"), enabled: role !== "employee" });
  const holidays = useQuery({ queryKey: ["holidays"], queryFn: () => api.get<ListResponse<Holiday>>("/holidays"), enabled: role !== "employee" });
  const save = useMutation({ mutationFn: async () => { if (!editor) return; if (editor.kind === "department") return editor.id ? api.put(`/departments/${editor.id}`, { name: editor.name }) : api.post("/departments", { name: editor.name }); if (editor.kind === "designation") return api.post("/designations", { name: editor.name, department_id: editor.department_id }); if (editor.kind === "leave-type") { const body = { code: editor.code, name: editor.name, yearly_quota: editor.yearly_quota ?? null, is_paid: editor.is_paid ?? true }; return editor.id ? api.put(`/leave-types/${editor.id}`, body) : api.post("/leave-types", body); } return api.post("/holidays", { date: editor.date, name: editor.name }); }, onSuccess: () => { toast.success("Organization settings updated"); setEditor(null); void client.invalidateQueries(); } });
  const removeItem = useMutation({ mutationFn: () => api.delete(remove?.kind === "department" ? `/departments/${remove.id}` : `/holidays/${remove?.id}`), onSuccess: () => { toast.success("Record removed"); setRemove(null); void client.invalidateQueries(); } });
  if (role === "employee") return null;
  if ([departments, designations, leaveTypes, holidays].some((query) => query.isLoading)) return <LoadingSkeleton rows={7} />;
  const failed = [departments, designations, leaveTypes, holidays].find((query) => query.isError);
  if (failed) return <ErrorState message={(failed.error as Error).message} onRetry={() => { departments.refetch(); designations.refetch(); leaveTypes.refetch(); holidays.refetch(); }} />;
  const canEdit = role === "admin";
  const data = tab === "departments" ? departments.data?.items ?? [] : tab === "designations" ? designations.data?.items ?? [] : tab === "leave-types" ? leaveTypes.data?.items ?? [] : holidays.data?.items ?? [];
  const addLabel = tab === "departments" ? "Add department" : tab === "designations" ? "Add designation" : tab === "leave-types" ? "Add leave type" : "Add holiday";
  const add = () => setEditor(tab === "departments" ? { kind: "department", name: "" } : tab === "designations" ? { kind: "designation", name: "", department_id: "" } : tab === "leave-types" ? { kind: "leave-type", name: "", code: "", yearly_quota: null, is_paid: true } : { kind: "holiday", name: "", date: "" });
  return <div className="space-y-5"><PageHeader title="Organization settings" subtitle="Manage company structure, leave types, holidays and other organization settings." /><Tabs items={[{ value: "departments", label: "Departments" }, { value: "designations", label: "Designations" }, { value: "leave-types", label: "Leave types" }, { value: "holidays", label: "Holidays" }]} value={tab} onChange={setTab} />
    <section className="card overflow-hidden"><div className="flex items-start justify-between gap-4 p-5"><div><h2 className="text-lg font-semibold">{tab === "leave-types" ? "Leave types" : tab[0].toUpperCase() + tab.slice(1)}</h2><p className="text-sm text-muted">{tab === "departments" ? "Define the teams in your company." : tab === "designations" ? "Manage job titles by department." : tab === "leave-types" ? "Define leave types and yearly quotas." : "Manage company holidays."}</p></div>{canEdit && <Button onClick={add}><Plus className="size-4" />{addLabel}</Button>}</div>
      {!data.length ? <EmptyState title={`No ${tab.replace("-", " ")} yet`} description={`Use ${addLabel} to create the first record.`} /> : tab === "departments" ? <DepartmentsTable items={departments.data?.items ?? []} canEdit={canEdit} edit={(item) => setEditor({ kind: "department", id: item.id, name: item.name })} remove={(item) => setRemove({ kind: "department", id: item.id, name: item.name })} /> : tab === "designations" ? <DesignationsTable items={designations.data?.items ?? []} /> : tab === "leave-types" ? <LeaveTypesTable items={leaveTypes.data?.items ?? []} canEdit={canEdit} edit={(item) => setEditor({ kind: "leave-type", ...item })} /> : <HolidaysTable items={holidays.data?.items ?? []} canEdit={canEdit} remove={(item) => setRemove({ kind: "holiday", id: item.id, name: item.name })} />}
    </section>
    <Dialog open={Boolean(editor)} onOpenChange={(open) => !open && setEditor(null)}><DialogContent><DialogTitle>{editor?.id ? "Edit" : "Add"} {editor?.kind.replace("-", " ")}</DialogTitle><DialogDescription>Complete the fields below and save the record.</DialogDescription>{editor && <div className="mt-5 space-y-4"><label className="block text-sm font-medium">Name<Input className="mt-2" value={editor.name ?? ""} onChange={(event) => setEditor({ ...editor, name: event.target.value })} /></label>{editor.kind === "designation" && <label className="block text-sm font-medium">Department<Select className="mt-2" value={editor.department_id ?? ""} onChange={(event) => setEditor({ ...editor, department_id: event.target.value })}><option value="">Select department</option>{departments.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></label>}{editor.kind === "leave-type" && <><label className="block text-sm font-medium">Code<Input className="mt-2" value={editor.code ?? ""} onChange={(event) => setEditor({ ...editor, code: event.target.value.toUpperCase() })} /></label><label className="block text-sm font-medium">Yearly quota<Input className="mt-2" type="number" value={editor.yearly_quota ?? ""} placeholder="Empty means unlimited" onChange={(event) => setEditor({ ...editor, yearly_quota: event.target.value ? Number(event.target.value) : null })} /></label><label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={editor.is_paid ?? false} onChange={(event) => setEditor({ ...editor, is_paid: event.target.checked })} />Paid leave</label></>}{editor.kind === "holiday" && <label className="block text-sm font-medium">Date<Input className="mt-2" type="date" value={editor.date ?? ""} onChange={(event) => setEditor({ ...editor, date: event.target.value })} /></label>}<div className="flex justify-end gap-3"><Button variant="outline" onClick={() => setEditor(null)}>Cancel</Button><Button onClick={() => save.mutate()} disabled={!editor.name || save.isPending}>{save.isPending ? "Saving..." : "Save"}</Button></div></div>}</DialogContent></Dialog>
    <ConfirmDialog open={Boolean(remove)} onOpenChange={(open) => !open && setRemove(null)} title={`Delete ${remove?.name ?? "record"}?`} description="This action cannot be undone. The backend will refuse a department that still has employees." confirmLabel="Delete" danger pending={removeItem.isPending} onConfirm={() => removeItem.mutate()} />
  </div>;
}

function DepartmentsTable({ items, canEdit, edit, remove }: { items: Department[]; canEdit: boolean; edit: (item: Department) => void; remove: (item: Department) => void }) { return <Table headings={["#", "Name", "Employees", "Actions"]}>{items.map((item, index) => <tr key={item.id} className="border-t border-line"><Cell>{index + 1}</Cell><Cell strong>{item.name}</Cell><Cell>{item.employee_count ?? 0}</Cell><Cell>{canEdit && <div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => edit(item)}><Pencil className="size-4" />Edit</Button><Button size="icon" variant="ghost" onClick={() => remove(item)}><Trash2 className="size-4 text-red-600" /></Button></div>}</Cell></tr>)}</Table>; }
function DesignationsTable({ items }: { items: Designation[] }) { return <Table headings={["#", "Name", "Department", "Actions"]}>{items.map((item, index) => <tr key={item.id} className="border-t border-line"><Cell>{index + 1}</Cell><Cell strong>{item.name}</Cell><Cell>{item.department_name}</Cell><Cell><MoreHorizontal className="size-4" /></Cell></tr>)}</Table>; }
function LeaveTypesTable({ items, canEdit, edit }: { items: LeaveType[]; canEdit: boolean; edit: (item: LeaveType) => void }) { return <Table headings={["#", "Name", "Code", "Yearly quota (days)", "Paid", "Actions"]}>{items.map((item, index) => <tr key={item.id} className="border-t border-line"><Cell>{index + 1}</Cell><Cell strong>{item.name}</Cell><Cell>{item.code}</Cell><Cell>{item.yearly_quota ?? "Unlimited"}</Cell><Cell><span className={`rounded-full px-3 py-1 text-xs ${item.is_paid ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>{item.is_paid ? "Yes" : "No"}</span></Cell><Cell>{canEdit && <Button size="sm" variant="outline" onClick={() => edit(item)}><Pencil className="size-4" />Edit</Button>}</Cell></tr>)}</Table>; }
function HolidaysTable({ items, canEdit, remove }: { items: Holiday[]; canEdit: boolean; remove: (item: Holiday) => void }) { return <Table headings={["#", "Date", "Name", "Actions"]}>{items.map((item, index) => <tr key={item.id} className="border-t border-line"><Cell>{index + 1}</Cell><Cell>{item.date}</Cell><Cell strong>{item.name}</Cell><Cell>{canEdit && <Button size="icon" variant="ghost" onClick={() => remove(item)}><Trash2 className="size-4 text-red-600" /></Button>}</Cell></tr>)}</Table>; }
function Table({ headings, children }: { headings: string[]; children: React.ReactNode }) { return <div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr>{headings.map((heading) => <th key={heading} className="px-5 py-4">{heading}</th>)}</tr></thead><tbody>{children}</tbody></table></div>; }
function Cell({ children, strong }: { children: React.ReactNode; strong?: boolean }) { return <td className={`px-5 py-4 ${strong ? "font-semibold" : ""}`}>{children}</td>; }
