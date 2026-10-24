"use client";

import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { AuditLog, ListResponse } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type AuditEntry = AuditLog & { actor_name: string; actor_role: string };

export default function AuditPage() {
  usePageTitle("Audit log");
  const { role } = useAuth();
  const router = useRouter();
  const [entity, setEntity] = useState("");
  const [actorId, setActorId] = useState("");
  const [selected, setSelected] = useState<AuditEntry | null>(null);
  useEffect(() => { if (role !== "admin") router.replace("/dashboard"); }, [role, router]);
  const query = useQuery({ queryKey: ["audit-logs", entity, actorId], queryFn: () => api.get<ListResponse<AuditEntry>>("/audit-logs", { entity, actor_id: actorId, from: "2026-10-01", to: "2026-10-24" }), enabled: role === "admin" });
  if (role !== "admin") return null;
  if (query.isLoading) return <LoadingSkeleton rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const items = query.data?.items ?? [];
  return <div className={selected ? "grid gap-5 xl:grid-cols-[1fr_420px]" : "grid gap-5"}><div className="space-y-5"><PageHeader title="Audit log" subtitle="Track important actions performed in the system." /><div className="grid gap-4 sm:grid-cols-3"><label className="text-sm font-medium">Entity<Select className="mt-2" value={entity} onChange={(event) => setEntity(event.target.value)}><option value="">All Entities</option><option value="employee">Employee</option><option value="leave_request">Leave Request</option><option value="attendance">Attendance</option><option value="payroll">Payroll</option></Select></label><label className="text-sm font-medium">User<Select className="mt-2" value={actorId} onChange={(event) => setActorId(event.target.value)}><option value="">All users</option><option value="user-admin">Ali Raza</option><option value="user-hr">Sarah Ahmed</option></Select></label><label className="text-sm font-medium">Date range<div className="mt-2 flex h-11 items-center rounded-md border border-slate-300 bg-white px-3 text-sm">01 Oct 2026&nbsp;&nbsp;-&nbsp;&nbsp;24 Oct 2026</div></label></div>
      {!items.length ? <EmptyState title="No audit records" description="No records match the selected filters." /> : <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[780px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">#</th><th>Time</th><th>User</th><th>Action</th><th>Entity</th><th>Record</th></tr></thead><tbody>{items.map((item, index) => <tr key={item.id} onClick={() => setSelected(item)} className={`cursor-pointer border-b border-line hover:bg-slate-50 ${selected?.id === item.id ? "bg-teal-50" : ""}`}><td className="px-4 py-3">{index + 1}</td><td>{item.created_at.replace("T", " ").slice(0, 16)}</td><td><div className="flex items-center gap-2"><span className="flex size-8 items-center justify-center rounded-full bg-slate-100 text-[10px]">{initials(item.actor_name)}</span><div><strong>{item.actor_name}</strong><p className="text-xs capitalize text-muted">{item.actor_role}</p></div></div></td><td><ActionBadge action={item.action} /></td><td>{label(item.entity)}</td><td>{item.entity_id}</td></tr>)}</tbody></table></div><div className="border-t border-line p-4 text-sm text-muted">Showing 1 to {items.length} of {query.data?.total ?? items.length} records</div></section>}
    </div>{selected && <aside className="card h-fit p-6 xl:sticky xl:top-20"><div className="flex items-center justify-between"><h2 className="text-xl font-bold">Audit details</h2><button onClick={() => setSelected(null)}><X className="size-5" /></button></div><div className="mt-5 flex items-center justify-between"><ActionBadge action={selected.action} /><time className="text-xs text-muted">{selected.created_at.replace("T", " ").slice(0, 16)}</time></div><dl className="mt-4 space-y-3 rounded-lg bg-slate-50 p-4 text-sm"><div className="flex"><dt className="w-28 text-muted">User</dt><dd>{selected.actor_name} ({selected.actor_role})</dd></div><div className="flex"><dt className="w-28 text-muted">Entity</dt><dd>{label(selected.entity)}</dd></div><div className="flex"><dt className="w-28 text-muted">Record</dt><dd>{selected.entity_id}</dd></div></dl><h3 className="mt-6 font-semibold">Changes</h3><div className="mt-3 grid gap-3 sm:grid-cols-2 xl:grid-cols-2"><ChangeSet title="Before" values={selected.before} /><ChangeSet title="After" values={selected.after} after /></div></aside>}</div>;
}

function ActionBadge({ action }: { action: string }) { const styles: Record<string, string> = { update: "bg-emerald-100 text-emerald-700", create: "bg-blue-100 text-blue-700", approve: "bg-emerald-100 text-emerald-700", finalize: "bg-violet-100 text-violet-700" }; return <span className={`rounded-full px-3 py-1 text-xs capitalize ${styles[action] ?? "bg-slate-100 text-slate-700"}`}>{action}</span>; }
function ChangeSet({ title, values, after }: { title: string; values: Record<string, unknown> | null; after?: boolean }) { return <div className="overflow-hidden rounded-lg border border-line"><h4 className={after ? "bg-teal-50 px-3 py-2 text-sm font-semibold text-primary" : "bg-slate-100 px-3 py-2 text-sm font-semibold"}>{title}</h4>{values ? Object.entries(values).map(([key, value]) => <div key={key} className="border-t border-line p-3 text-xs"><p className="capitalize text-muted">{label(key)}</p><strong className="mt-1 block break-words">{String(value)}</strong></div>) : <p className="p-3 text-xs text-muted">No previous values</p>}</div>; }
function label(value: string) { return value.split("_").map((word) => word[0].toUpperCase() + word.slice(1)).join(" "); }
