"use client";

import { useMutation } from "@tanstack/react-query";
import { LockKeyhole } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

export default function ProfilePage() {
  usePageTitle("My profile");
  const { user, isLoading, refreshUser } = useAuth();
  if (isLoading) return <LoadingSkeleton rows={6} />;
  if (!user) return <ErrorState message="Your profile could not be loaded." onRetry={() => void refreshUser()} />;
  return <ProfileContent key={`${user.id}-${user.employee?.phone}`} />;
}

function ProfileContent() {
  const { user, role, refreshUser } = useAuth();
  const employee = user?.employee;
  const name = employee ? `${employee.first_name} ${employee.last_name}` : user?.email.split("@")[0] ?? "User";
  const [phone, setPhone] = useState(employee?.phone ?? "");
  const [address, setAddress] = useState(employee?.address ?? "");
  const save = useMutation({ mutationFn: () => api.patch("/employees/me", { phone, address }), onSuccess: async () => { await refreshUser(); toast.success("Contact details updated"); } });
  return <div className="space-y-5"><PageHeader title="My profile" subtitle="View your information and manage your account settings." /><div className="grid gap-5 xl:grid-cols-[1fr_1.05fr]"><section className="card p-6"><h2 className="text-xl font-semibold">Personal information</h2><p className="text-sm text-muted">Your basic information in the system.</p><div className="mt-7 flex items-center gap-6"><span className="flex size-28 items-center justify-center rounded-full bg-teal-50 text-3xl font-bold text-primary">{initials(name)}</span><div><h3 className="text-3xl font-bold">{name}</h3><p className="mt-1 text-lg text-muted">{employee?.designation ?? role}</p></div></div><dl className="mt-8 divide-y divide-line text-sm"><ProfileRow label="Employee code" value={employee?.employee_code ?? "-"} /><ProfileRow label="Department" value={employee?.department ?? "-"} /><ProfileRow label="Designation" value={employee?.designation ?? "-"} /><ProfileRow label="Join date" value={employee?.join_date ?? "-"} /></dl></section><div className="space-y-5"><section className="card p-6"><h2 className="text-xl font-semibold">Contact details</h2><p className="text-sm text-muted">Keep your contact information up to date.</p><label className="mt-6 block text-sm font-medium">Phone number<Input value={phone} disabled={role !== "employee"} onChange={(event) => setPhone(event.target.value)} className="mt-2" /></label><label className="mt-5 block text-sm font-medium">Address<Textarea value={address} disabled={role !== "employee"} onChange={(event) => setAddress(event.target.value)} className="mt-2" /></label>{role === "employee" && <div className="mt-5 flex justify-end"><Button onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending ? "Saving..." : "Save changes"}</Button></div>}</section><section className="card p-6"><h2 className="text-xl font-semibold">Security</h2><p className="text-sm text-muted">Manage your account password.</p><div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center"><span className="flex size-12 items-center justify-center rounded-full bg-teal-50 text-primary"><LockKeyhole className="size-6" /></span><div className="flex-1"><strong>Password</strong><p className="text-xs text-muted">Change your password regularly to keep your account secure.</p></div><Button variant="outline" asChild><Link href="/change-password">Change password</Link></Button></div></section></div></div></div>;
}
function ProfileRow({ label, value }: { label: string; value: string }) { return <div className="flex py-4"><dt className="flex-1 text-muted">{label}</dt><dd className="flex-1 font-medium">{value}</dd></div>; }
