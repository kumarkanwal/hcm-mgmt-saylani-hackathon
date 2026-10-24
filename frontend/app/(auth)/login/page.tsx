"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { AuthCard } from "@/components/auth-card";
import { FormField } from "@/components/form-field";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";
import { usePageTitle } from "@/hooks/use-page-title";

const schema = z.object({ email: z.email("Enter a valid email address."), password: z.string().min(1, "Enter your password.") });
type LoginValues = z.infer<typeof schema>;

export default function LoginPage() {
  usePageTitle("Sign in");
  const router = useRouter();
  const { login } = useAuth();
  const form = useForm<LoginValues>({ resolver: zodResolver(schema), defaultValues: { email: "", password: "" } });
  const mutation = useMutation({
    mutationFn: ({ email, password }: LoginValues) => login(email, password),
    onSuccess: (user) => router.push(user.must_change_password ? "/change-password" : "/dashboard"),
  });
  return (
    <AuthCard title="Sign in" className="max-w-[596px]">
      <form className="space-y-6" onSubmit={form.handleSubmit((values) => mutation.mutate(values))}>
        <FormField label="Email" htmlFor="email" error={form.formState.errors.email?.message}><Input id="email" type="email" {...form.register("email")} /></FormField>
        <FormField label="Password" htmlFor="password" error={form.formState.errors.password?.message}><Input id="password" type="password" {...form.register("password")} /></FormField>
        <Button className="w-full" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Signing in..." : "Sign in"}</Button>
        {mutation.isError && <p role="alert" className="text-sm text-red-600">{(mutation.error as ApiError).message}</p>}
      </form>
    </AuthCard>
  );
}
