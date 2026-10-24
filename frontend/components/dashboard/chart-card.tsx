import type { ReactNode } from "react";
import { Select } from "@/components/ui/select";

export function ChartCard({ title, children, filter = "This month", className = "" }: { title: string; children: ReactNode; filter?: string | false; className?: string }) {
  return (
    <section className={`card min-w-0 p-4 ${className}`}>
      <div className="mb-4 flex items-center justify-between gap-3">
        <h2 className="font-semibold text-ink">{title}</h2>
        {filter && <Select defaultValue={filter} className="h-9 w-auto min-w-28 text-xs"><option>{filter}</option></Select>}
      </div>
      {children}
    </section>
  );
}
