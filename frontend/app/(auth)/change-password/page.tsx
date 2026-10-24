"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { Info } from "lucide-react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { PasswordInput } from "@/components/password-input";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePageTitle } from "@/hooks/use-page-title";

const schema = z.object({ old_password: z.string().min(1, "Enter your current password."), new_password: z.string().min(8, "Use at least 8 characters."), confirm_password: z.string() }).refine((data) => data.new_password === data.confirm_password, { path: ["confirm_password"], message: "Passwords do not match." });
type PasswordValues = z.infer<typeof schema>;

export default function ChangePasswordPage() {
  usePageTitle("Set your password");
  const router = useRouter();
  const { refreshUser } = useAuth();
  const form = useForm<PasswordValues>({ resolver: zodResolver(schema), defaultValues: { old_password: "", new_password: "", confirm_password: "" } });
  const mutation = useMutation({
    mutationFn: (values: PasswordValues) => api.post("/auth/change-password", { old_password: values.old_password, new_password: values.new_password }),
    onSuccess: async () => { await refreshUser(); toast.success("Password updated"); router.push("/dashboard"); },
  });
  return (
    <AuthCard title="Set your password" subtitle="People  |  Attendance  |  Payroll  |  Simplified" className="max-w-[680px]">
      <div className="mb-6 flex items-center gap-3 rounded-lg border border-teal-100 bg-teal-50 p-4 text-sm text-slate-700"><span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-primary text-white"><Info className="size-4" /></span>Please set your own password before continuing.</div>
      <form className="space-y-5" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <FormField label="Current password" htmlFor="old_password" error={form.formState.errors.old_password?.message}><PasswordInput id="old_password" placeholder="Enter current password" {...form.register("old_password")} /></FormField>
        <FormField label="New password" htmlFor="new_password" error={form.formState.errors.new_password?.message}><PasswordInput id="new_password" placeholder="Enter new password" {...form.register("new_password")} /></FormField>
        <FormField label="Confirm new password" htmlFor="confirm_password" error={form.formState.errors.confirm_password?.message}><PasswordInput id="confirm_password" placeholder="Confirm new password" {...form.register("confirm_password")} /></FormField>
        <Button className="mt-2 w-full" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Saving password..." : "Save password"}</Button>
        {mutation.isError && <p role="alert" className="text-sm text-red-600">{(mutation.error as ApiError).message}</p>}
      </form>
    </AuthCard>
  );
}
