import type { ReactNode } from "react";
import { Brand } from "@/components/brand";
import { cn } from "@/lib/utils";

export function AuthCard({ title, subtitle, children, className }: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("w-full max-w-[600px] rounded-xl border border-line bg-white px-6 py-9 shadow-[0_16px_45px_rgba(15,23,42,0.08)] sm:px-10", className)}>
      <div className="text-center">
        <Brand className="pointer-events-none text-[34px]" />
        {subtitle && <p className="mt-0.5 text-xs text-muted">{subtitle}</p>}
        <h1 className="mt-5 text-[30px] font-bold tracking-tight text-ink">{title}</h1>
      </div>
      <div className="mt-7">{children}</div>
    </section>
  );
}
