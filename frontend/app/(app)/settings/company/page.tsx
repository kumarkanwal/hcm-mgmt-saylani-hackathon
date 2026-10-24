"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock3, Info, LocateFixed, MapPin } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Tabs } from "@/components/tabs";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Settings } from "@/lib/types";
import { usePageTitle } from "@/hooks/use-page-title";

export default function CompanySettingsPage() {
  usePageTitle("Company settings");
  const { role } = useAuth();
  const router = useRouter();
  useEffect(() => { if (role === "employee") router.replace("/dashboard"); }, [role, router]);
  const query = useQuery({ queryKey: ["settings"], queryFn: () => api.get<Settings>("/settings"), enabled: role !== "employee" });
  if (role === "employee") return null;
  if (query.isLoading) return <LoadingSkeleton rows={8} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  if (!query.data) return null;
  return <SettingsForm initial={query.data} readOnly={role === "hr"} />;
}

function SettingsForm({ initial, readOnly }: { initial: Settings; readOnly: boolean }) {
  const client = useQueryClient();
  const [values, setValues] = useState(initial);
  const save = useMutation({ mutationFn: () => api.put<Settings>("/settings", values), onSuccess: () => { toast.success("Company settings updated"); void client.invalidateQueries({ queryKey: ["settings"] }); } });
  const update = <K extends keyof Settings>(key: K, value: Settings[K]) => setValues((current) => ({ ...current, [key]: value }));
  const useLocation = () => navigator.geolocation.getCurrentPosition((position) => { update("office_lat", Number(position.coords.latitude.toFixed(6))); update("office_lng", Number(position.coords.longitude.toFixed(6))); }, (error) => toast.error(error.message));
  const weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
  return <div className="space-y-5"><PageHeader title="Company settings" subtitle={readOnly ? "View company information, working hours and office location." : "Manage your company information, working hours and office location."} /><Tabs items={[{ value: "company", label: "Company" }, { value: "attendance", label: "Attendance" }, { value: "leave", label: "Leave" }, { value: "payroll", label: "Payroll" }, { value: "notifications", label: "Notifications" }]} value="company" onChange={() => undefined} />
    <div className="grid gap-4 xl:grid-cols-2"><section className="card p-5"><h2 className="text-lg font-semibold">Company</h2><p className="text-sm text-muted">Basic information about your company.</p><label className="mt-5 block text-sm font-medium">Company name<Input value={values.company_name} disabled={readOnly} onChange={(event) => update("company_name", event.target.value)} className="mt-2" /></label><div className="mt-5 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-6 text-center"><strong className="text-2xl"><span className="text-primary">HCM</span> Lite</strong><p className="mt-2 text-xs text-muted">Company identity is shown throughout the portal.</p></div></section>
      <section className="card p-5"><h2 className="text-lg font-semibold">Working hours</h2><p className="text-sm text-muted">Set default working hours and attendance rules.</p><div className="mt-5 grid gap-4 sm:grid-cols-2"><label className="text-sm font-medium">Office start time<div className="relative mt-2"><Clock3 className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" /><Input type="time" value={values.office_start} disabled={readOnly} onChange={(event) => update("office_start", event.target.value)} className="pl-10" /></div></label><label className="text-sm font-medium">Grace time (minutes)<Input type="number" value={values.grace_minutes} disabled={readOnly} onChange={(event) => update("grace_minutes", Number(event.target.value))} className="mt-2" /></label><label className="text-sm font-medium">Half day if working less than (hours)<Input type="number" value={values.half_day_hours} disabled={readOnly} onChange={(event) => update("half_day_hours", Number(event.target.value))} className="mt-2" /></label></div><div className="mt-6"><p className="text-sm font-medium">Weekend days</p><div className="mt-3 flex flex-wrap gap-5">{weekdays.map((day, index) => <label key={day} className="flex items-center gap-2 text-sm"><input type="checkbox" className="size-4 accent-[#0f9488]" disabled={readOnly} checked={values.weekend_days.includes(index)} onChange={(event) => update("weekend_days", event.target.checked ? [...values.weekend_days, index] : values.weekend_days.filter((item) => item !== index))} />{day}</label>)}</div></div></section>
    </div>
    <section className="card grid gap-5 p-5 xl:grid-cols-[1fr_0.9fr]"><div><h2 className="text-lg font-semibold">Office location</h2><p className="text-sm text-muted">Set the office location for attendance and allowed check-in radius.</p><div className="mt-5 grid gap-4 sm:grid-cols-3"><label className="text-sm font-medium">Latitude<Input type="number" step="any" value={values.office_lat ?? ""} disabled={readOnly} onChange={(event) => update("office_lat", Number(event.target.value))} className="mt-2" /></label><label className="text-sm font-medium">Longitude<Input type="number" step="any" value={values.office_lng ?? ""} disabled={readOnly} onChange={(event) => update("office_lng", Number(event.target.value))} className="mt-2" /></label><label className="text-sm font-medium">Allowed radius (metres)<Input type="number" value={values.office_radius_m} disabled={readOnly} onChange={(event) => update("office_radius_m", Number(event.target.value))} className="mt-2" /></label></div>{!readOnly && <Button variant="outline" className="mt-5" onClick={useLocation}><LocateFixed className="size-4" />Use my current location</Button>}</div><div className="relative min-h-48 overflow-hidden rounded-lg bg-[linear-gradient(45deg,#e8eef0_25%,transparent_25%),linear-gradient(-45deg,#e8eef0_25%,transparent_25%),linear-gradient(45deg,transparent_75%,#e8eef0_75%),linear-gradient(-45deg,transparent_75%,#e8eef0_75%)] bg-[size:32px_32px]"><div className="absolute inset-0 bg-teal-50/40" /><div className="absolute left-1/2 top-1/2 flex size-32 -translate-x-1/2 -translate-y-1/2 items-center justify-center rounded-full border-2 border-primary bg-teal-100/60"><MapPin className="size-8 text-primary" /></div></div></section>
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"><p className="flex items-center gap-2 text-xs text-muted"><Info className="size-4" />Changes apply to new records only. Existing attendance data will not be modified.</p>{!readOnly && <Button onClick={() => save.mutate()} disabled={save.isPending}>{save.isPending ? "Saving..." : "Save changes"}</Button>}</div>
  </div>;
}
