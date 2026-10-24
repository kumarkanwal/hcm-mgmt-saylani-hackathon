"use client";

import { useState } from "react";
import { Eye, EyeOff, LockKeyhole } from "lucide-react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function PasswordInput({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <LockKeyhole className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-slate-500" />
      <Input type={visible ? "text" : "password"} className={cn("px-10", className)} {...props} />
      <button type="button" className="absolute right-3 top-1/2 -translate-y-1/2 rounded p-1 text-slate-500 hover:text-slate-800" onClick={() => setVisible((value) => !value)} aria-label={visible ? "Hide password" : "Show password"}>
        {visible ? <Eye className="size-4" /> : <EyeOff className="size-4" />}
      </button>
    </div>
  );
}
