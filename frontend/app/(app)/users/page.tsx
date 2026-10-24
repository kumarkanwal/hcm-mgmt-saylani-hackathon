"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Copy, Plus, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ListResponse, User } from "@/lib/types";
import { usePageTitle } from "@/hooks/use-page-title";

type LoginUser = User & { name?: string };

export default function UsersPage() {
  usePageTitle("Users");
  const { role } = useAuth();
  const router = useRouter();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [tempPassword, setTempPassword] = useState<string | null>(null);
  const [deactivate, setDeactivate] = useState<LoginUser | null>(null);
  useEffect(() => { if (role !== "admin") router.replace("/dashboard"); }, [role, router]);
  const query = useQuery({ queryKey: ["users"], queryFn: () => api.get<ListResponse<LoginUser>>("/users"), enabled: role === "admin" });
  const create = useMutation({ mutationFn: () => api.post<{ user: LoginUser; temp_password: string }>("/users", { email, password }), onSuccess: (response) => { setCreateOpen(false); setTempPassword(response.temp_password); setEmail(""); setPassword(""); void client.invalidateQueries({ queryKey: ["users"] }); } });
  const reset = useMutation({ mutationFn: (id: string) => api.post<{ temp_password: string }>(`/users/${id}/reset-password`), onSuccess: (response) => setTempPassword(response.temp_password) });
  const deactivateUser = useMutation({ mutationFn: () => api.patch(`/users/${deactivate?.id}/deactivate`), onSuccess: () => { toast.success("User deactivated"); setDeactivate(null); void client.invalidateQueries({ queryKey: ["users"] }); } });
  if (role !== "admin") return null;
  if (query.isLoading) return <LoadingSkeleton rows={7} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const users = (query.data?.items ?? []).filter((item) => !search || `${item.name} ${item.email}`.toLowerCase().includes(search.toLowerCase()));
  return <div className="space-y-5"><PageHeader title="Users" subtitle="Manage system users and their access to HCM Lite." actions={<><div className="relative"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" /><Input className="w-64 pl-10" placeholder="Search users..." value={search} onChange={(event) => setSearch(event.target.value)} /></div><Button onClick={() => setCreateOpen(true)}><Plus className="size-4" />Create HR login</Button></>} />
    {!users.length ? <EmptyState title="No users found" description="Create an HR login or change the search term." /> : <section className="card overflow-hidden"><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-5 py-4">#</th><th>Email</th><th>Name</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead><tbody>{users.map((item, index) => <tr key={item.id} className="border-b border-line"><td className="px-5 py-4">{index + 1}</td><td>{item.email}</td><td>{item.name ?? "-"}</td><td><span className="rounded-full bg-blue-100 px-3 py-1 text-xs capitalize text-blue-700">{item.role}</span></td><td><StatusBadge status={item.is_active === false ? "Inactive" : "Active"} /></td><td>{item.created_at?.replace("T", " ").slice(0, 16)}</td><td><div className="flex gap-2"><Button size="sm" variant="outline" onClick={() => reset.mutate(item.id)} disabled={reset.isPending}>Reset password</Button><Button size="sm" variant="danger" onClick={() => setDeactivate(item)} disabled={item.is_active === false}>Deactivate</Button></div></td></tr>)}</tbody></table></div></section>}
    <Dialog open={createOpen} onOpenChange={setCreateOpen}><DialogContent><DialogTitle>Create HR login</DialogTitle><DialogDescription>Create an account with the HR role. The user must change this password at first sign-in.</DialogDescription><div className="mt-5 space-y-4"><label className="block text-sm font-medium">Email<Input className="mt-2" type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label><label className="block text-sm font-medium">Temporary password<Input className="mt-2" type="password" value={password} onChange={(event) => setPassword(event.target.value)} /></label>{create.isError && <p className="text-sm text-red-600">{create.error.message}</p>}<div className="flex justify-end gap-3"><Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button><Button disabled={!email || password.length < 8 || create.isPending} onClick={() => create.mutate()}>{create.isPending ? "Creating..." : "Create login"}</Button></div></div></DialogContent></Dialog>
    <Dialog open={Boolean(tempPassword)} onOpenChange={(open) => !open && setTempPassword(null)}><DialogContent><div className="mx-auto flex size-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><Check className="size-7" /></div><DialogTitle className="mt-3 text-center">Temporary password generated</DialogTitle><DialogDescription className="text-center">Share it securely and ask the user to change it after first login.</DialogDescription><div className="mt-5 flex gap-2 rounded-lg bg-slate-50 p-4"><Input readOnly value={tempPassword ?? ""} /><Button variant="outline" onClick={() => { void navigator.clipboard.writeText(tempPassword ?? ""); toast.success("Password copied"); }}><Copy className="size-4" />Copy</Button></div><div className="mt-5 flex justify-end"><Button onClick={() => setTempPassword(null)}>Done</Button></div></DialogContent></Dialog>
    <ConfirmDialog open={Boolean(deactivate)} onOpenChange={(open) => !open && setDeactivate(null)} title="Deactivate this login?" description={`${deactivate?.email ?? "This user"} will no longer be able to sign in.`} confirmLabel="Deactivate" danger pending={deactivateUser.isPending} onConfirm={() => deactivateUser.mutate()} />
  </div>;
}
