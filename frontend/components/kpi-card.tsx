import type { LucideIcon } from "lucide-react";
import { ArrowDown, ArrowUp } from "lucide-react";
import { cn } from "@/lib/utils";

const tones = {
  teal: "bg-teal-50 text-teal-600",
  green: "bg-emerald-50 text-emerald-600",
  blue: "bg-blue-50 text-blue-600",
  orange: "bg-orange-50 text-orange-600",
  amber: "bg-amber-50 text-amber-600",
};

export function KpiCard({
  label,
  value,
  detail,
  icon: Icon,
  tone = "teal",
  change,
  changeDirection = "up",
}: {
  label: string;
  value: string | number;
  detail: string;
  icon: LucideIcon;
  tone?: keyof typeof tones;
  change?: string;
  changeDirection?: "up" | "down" | "flat";
}) {
  const ChangeIcon = changeDirection === "down" ? ArrowDown : ArrowUp;
  return (
    <div className="card min-h-36 p-4">
      <div className="flex gap-4">
        <div className={cn("flex size-12 shrink-0 items-center justify-center rounded-xl", tones[tone])}><Icon className="size-6" /></div>
        <div className="min-w-0 pt-1">
          <p className="text-sm font-medium text-slate-700">{label}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-[27px] font-bold leading-none tracking-tight text-ink">{value}</p>
            {change && (
              <span className={cn("inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold", changeDirection === "down" ? "bg-emerald-50 text-emerald-600" : changeDirection === "flat" ? "bg-amber-50 text-amber-600" : "bg-emerald-50 text-emerald-600")}>
                {changeDirection !== "flat" && <ChangeIcon className="mr-0.5 size-3" />}{change}
              </span>
            )}
          </div>
          <p className="mt-3 text-xs text-muted">{detail}</p>
        </div>
      </div>
    </div>
  );
}
