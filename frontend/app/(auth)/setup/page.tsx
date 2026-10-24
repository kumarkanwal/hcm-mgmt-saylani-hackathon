"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api, ApiError } from "@/lib/api";
import { usePageTitle } from "@/hooks/use-page-title";

const schema = z.object({
  company_name: z.string().min(2, "Enter the company name."),
  admin_email: z.email("Enter a valid email address."),
  admin_password: z.string().min(8, "Use at least 8 characters."),
  confirm_password: z.string(),
}).refine((data) => data.admin_password === data.confirm_password, { path: ["confirm_password"], message: "Passwords do not match." });
type SetupValues = z.infer<typeof schema>;

export default function SetupPage() {
  usePageTitle("Set up your company");
  const router = useRouter();
  const status = useQuery({ queryKey: ["setup-status"], queryFn: () => api.get<{ is_setup_done: boolean }>("/setup/status") });
  const form = useForm<SetupValues>({ resolver: zodResolver(schema), defaultValues: { company_name: "", admin_email: "", admin_password: "", confirm_password: "" } });
  const setup = useMutation({
    mutationFn: (values: SetupValues) => api.post("/setup", { company_name: values.company_name, admin_email: values.admin_email, admin_password: values.admin_password }),
    onSuccess: () => { toast.success("Company created"); router.push("/login"); },
  });
  if (status.isLoading) return <div className="w-full max-w-[600px]"><LoadingSkeleton rows={5} /></div>;
  if (status.isError) return <div className="w-full max-w-[600px]"><ErrorState message={(status.error as Error).message} onRetry={() => status.refetch()} /></div>;
  return (
    <AuthCard title="Set up your company" className="max-w-[600px]">
      <form className="space-y-5" onSubmit={form.handleSubmit((values) => setup.mutate(values))}>
        <FormField label="Company name" htmlFor="company_name" error={form.formState.errors.company_name?.message}><Input id="company_name" {...form.register("company_name")} /></FormField>
        <FormField label="Admin email" htmlFor="admin_email" error={form.formState.errors.admin_email?.message}><Input id="admin_email" type="email" {...form.register("admin_email")} /></FormField>
        <FormField label="Password" htmlFor="admin_password" error={form.formState.errors.admin_password?.message}><Input id="admin_password" type="password" {...form.register("admin_password")} /></FormField>
        <FormField label="Confirm password" htmlFor="confirm_password" error={form.formState.errors.confirm_password?.message}><Input id="confirm_password" type="password" {...form.register("confirm_password")} /></FormField>
        <Button className="mt-1 w-full" type="submit" disabled={setup.isPending}>{setup.isPending ? "Creating company..." : "Create company"}</Button>
        {setup.isError && <p role="alert" className="text-sm text-red-600">{(setup.error as ApiError).message}</p>}
        <p className="text-center text-xs text-muted">This runs only once.</p>
      </form>
    </AuthCard>
  );
}
