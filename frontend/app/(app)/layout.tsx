"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { LoadingSkeleton } from "@/components/page-states";
import { useAuth } from "@/lib/auth";
import { USE_MOCKS } from "@/lib/api";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (!isLoading && !user && !USE_MOCKS) router.replace("/login");
  }, [isLoading, router, user]);
  if (isLoading) return <div className="p-8"><LoadingSkeleton cards={4} /></div>;
  if (!user && !USE_MOCKS) return null;
  return <AppShell>{children}</AppShell>;
}
