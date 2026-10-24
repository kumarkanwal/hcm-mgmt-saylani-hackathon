import { cn } from "@/lib/utils";

const styles: Record<string, string> = {
  active: "bg-emerald-100 text-emerald-700",
  present: "bg-emerald-100 text-emerald-700",
  approved: "bg-emerald-100 text-emerald-700",
  late: "bg-amber-100 text-amber-700",
  probation: "bg-amber-100 text-amber-700",
  pending: "bg-amber-100 text-amber-700",
  "half day": "bg-orange-100 text-orange-700",
  absent: "bg-red-100 text-red-700",
  rejected: "bg-red-100 text-red-700",
  "on leave": "bg-blue-100 text-blue-700",
  finalized: "bg-blue-100 text-blue-700",
  "missing checkout": "bg-slate-100 text-slate-600",
  inactive: "bg-slate-100 text-slate-600",
  draft: "bg-slate-100 text-slate-600",
};

export function StatusBadge({ status, dot = false }: { status: string; dot?: boolean }) {
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold", styles[status.toLowerCase()] ?? "bg-slate-100 text-slate-700")}>
      {dot && <span className="size-2 rounded-full bg-current" />}
      {status}
    </span>
  );
}
