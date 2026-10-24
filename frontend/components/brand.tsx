import Link from "next/link";
import { cn } from "@/lib/utils";

export function Brand({ className }: { className?: string }) {
  return (
    <Link href="/dashboard" className={cn("inline-flex items-baseline text-[27px] font-bold tracking-[-1.2px] text-ink", className)}>
      <span className="text-primary">HCM</span><span className="ml-1 font-semibold">Lite</span>
    </Link>
  );
}
