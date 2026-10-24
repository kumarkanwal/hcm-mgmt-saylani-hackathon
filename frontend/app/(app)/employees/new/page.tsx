"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Check, Copy, Info } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { FormField } from "@/components/form-field";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Department, Designation, Employee, ListResponse } from "@/lib/types";
import { usePageTitle } from "@/hooks/use-page-title";

const schema = z.object({
  first_name: z.string().min(1, "Enter a first name."), last_name: z.string().min(1, "Enter a last name."),
  email: z.email("Enter a valid email address."), phone: z.string().min(7, "Enter a phone number."), gender: z.string().min(1, "Select a gender."),
  employee_code: z.string().min(1, "Enter an employee code."), department_id: z.string().min(1, "Select a department."), designation_id: z.string().min(1, "Select a designation."),
  join_date: z.string().min(1, "Select a join date."), basic_salary: z.number().positive("Enter a salary greater than zero."),
});
type FormValues = z.infer<typeof schema>;
type CreateResponse = { employee: Employee; temp_password: string };

export default function RegisterEmployeePage() {
  usePageTitle("Register employee");
  const router = useRouter();
  const { role } = useAuth();
  const [result, setResult] = useState<CreateResponse | null>(null);
  useEffect(() => { if (role !== "hr") router.replace("/dashboard"); }, [role, router]);
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => api.get<ListResponse<Department>>("/departments") });
  const designations = useQuery({ queryKey: ["designations"], queryFn: () => api.get<ListResponse<Designation>>("/designations") });
  const form = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { first_name: "", last_name: "", email: "", phone: "", gender: "", employee_code: "", department_id: "", designation_id: "", join_date: "", basic_salary: 0 } });
  const selectedDepartment = useWatch({ control: form.control, name: "department_id" });
  const basicSalary = Number(useWatch({ control: form.control, name: "basic_salary" })) || 0;
  const filteredDesignations = useMemo(() => designations.data?.items.filter((item) => !selectedDepartment || item.department_id === selectedDepartment) ?? [], [designations.data, selectedDepartment]);
  const createEmployee = useMutation({ mutationFn: (values: FormValues) => api.post<CreateResponse>("/employees", values), onSuccess: (response) => { setResult(response); toast.success("Employee registered"); } });
  if (role !== "hr") return null;
  if (departments.isLoading || designations.isLoading) return <LoadingSkeleton rows={8} />;
  if (departments.isError || designations.isError) return <ErrorState message={(departments.error ?? designations.error as Error).message} onRetry={() => { departments.refetch(); designations.refetch(); }} />;
  return (
    <div className="space-y-6">
      <div className="text-sm text-muted"><Link href="/employees" className="hover:text-primary">Employees</Link><span className="mx-2">/</span>Register employee</div>
      <PageHeader title="Register employee" subtitle="Add a new employee to your organization." />
      <form onSubmit={form.handleSubmit((values) => createEmployee.mutate(values))}>
        <div className="grid gap-5 lg:grid-cols-2">
          <section className="card space-y-5 p-6"><h2 className="text-lg font-semibold">Personal details</h2>
            <FormField label="First name" htmlFor="first_name" required error={form.formState.errors.first_name?.message}><Input id="first_name" {...form.register("first_name")} /></FormField>
            <FormField label="Last name" htmlFor="last_name" required error={form.formState.errors.last_name?.message}><Input id="last_name" {...form.register("last_name")} /></FormField>
            <FormField label="Email address" htmlFor="email" required error={form.formState.errors.email?.message}><Input id="email" type="email" {...form.register("email")} /></FormField>
            <FormField label="Phone number" htmlFor="phone" required error={form.formState.errors.phone?.message}><Input id="phone" {...form.register("phone")} /></FormField>
            <FormField label="Gender" htmlFor="gender" required error={form.formState.errors.gender?.message}><Select id="gender" {...form.register("gender")}><option value="">Select gender</option><option value="male">Male</option><option value="female">Female</option><option value="other">Other</option></Select></FormField>
          </section>
          <section className="card space-y-5 p-6"><h2 className="text-lg font-semibold">Job details</h2>
            <FormField label="Employee code" htmlFor="employee_code" required error={form.formState.errors.employee_code?.message}><Input id="employee_code" {...form.register("employee_code")} /></FormField>
            <div className="grid gap-4 sm:grid-cols-2"><FormField label="Department" htmlFor="department_id" required error={form.formState.errors.department_id?.message}><Select id="department_id" {...form.register("department_id")}><option value="">Select department</option>{departments.data?.items.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></FormField><FormField label="Designation" htmlFor="designation_id" required error={form.formState.errors.designation_id?.message}><Select id="designation_id" {...form.register("designation_id")}><option value="">Select designation</option>{filteredDesignations.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</Select></FormField></div>
            <FormField label="Join date" htmlFor="join_date" required error={form.formState.errors.join_date?.message}><Input id="join_date" type="date" {...form.register("join_date")} /></FormField>
            <FormField label="Basic salary (PKR)" htmlFor="basic_salary" required error={form.formState.errors.basic_salary?.message}><Input id="basic_salary" type="number" min="0" step="1000" {...form.register("basic_salary", { valueAsNumber: true })} /></FormField>
            <div className="rounded-lg bg-teal-50 p-5 text-sm"><h3 className="font-semibold">Salary preview (PKR)</h3><dl className="mt-4 space-y-3 text-slate-600"><div className="flex justify-between"><dt>Basic salary</dt><dd className="font-semibold text-ink">{basicSalary.toLocaleString()}</dd></div><div className="flex justify-between"><dt>House Rent Allowance (40%)</dt><dd className="font-semibold text-ink">{(basicSalary * 0.4).toLocaleString()}</dd></div><div className="flex justify-between"><dt>Medical Allowance (10%)</dt><dd className="font-semibold text-ink">{(basicSalary * 0.1).toLocaleString()}</dd></div><div className="flex justify-between border-t border-teal-100 pt-3"><dt className="font-semibold text-ink">Gross salary</dt><dd className="font-bold text-ink">{(basicSalary * 1.5).toLocaleString()}</dd></div></dl></div>
          </section>
        </div>
        {createEmployee.isError && <p className="mt-4 text-sm text-red-600">{(createEmployee.error as ApiError).message}</p>}
        <div className="card mt-5 flex justify-end gap-3 p-4"><Button variant="outline" type="button" asChild><Link href="/employees">Cancel</Link></Button><Button type="submit" disabled={createEmployee.isPending}>{createEmployee.isPending ? "Registering..." : "Register employee"}</Button></div>
      </form>
      <Dialog open={Boolean(result)} onOpenChange={(open) => { if (!open) { setResult(null); router.push("/employees"); } }}><DialogContent className="max-w-[520px] text-center"><div className="mx-auto flex size-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-700"><Check className="size-8" /></div><DialogTitle className="mt-4">Employee registered</DialogTitle><DialogDescription>The employee has been successfully registered.</DialogDescription><div className="mt-5 rounded-lg border border-line bg-slate-50 p-4 text-left"><p className="text-sm font-semibold">Temporary password</p><div className="mt-2 flex gap-2"><Input readOnly value={result?.temp_password ?? ""} /><Button variant="outline" onClick={() => { void navigator.clipboard.writeText(result?.temp_password ?? ""); toast.success("Password copied"); }}><Copy className="size-4" />Copy</Button></div><div className="mt-4 flex items-center gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900"><Info className="size-4 shrink-0" />The employee must change this password at first sign-in.</div></div><div className="mt-5 flex justify-end"><Button onClick={() => { setResult(null); router.push("/employees"); }}>Close</Button></div></DialogContent></Dialog>
    </div>
  );
}
