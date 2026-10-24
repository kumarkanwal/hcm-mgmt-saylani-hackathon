"use client";

import { cn } from "@/lib/utils";

export type TabItem = { value: string; label: string; count?: number };

export function Tabs({ items, value, onChange }: { items: TabItem[]; value: string; onChange: (value: string) => void }) {
  return (
    <div className="flex gap-2 overflow-x-auto border-b border-line scrollbar-thin" role="tablist">
      {items.map((item) => <button key={item.value} type="button" role="tab" aria-selected={value === item.value} onClick={() => onChange(item.value)} className={cn("shrink-0 border-b-2 border-transparent px-5 py-3 text-sm font-medium text-slate-600", value === item.value && "border-primary text-primary")}>{item.label}{item.count !== undefined ? ` (${item.count})` : ""}</button>)}
    </div>
  );
}
