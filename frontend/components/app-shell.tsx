"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  Bell,
  Bot,
  Building2,
  CalendarCheck,
  ChevronDown,
  ClipboardCheck,
  FileClock,
  FileText,
  LayoutDashboard,
  LogOut,
  Megaphone,
  Menu,
  MessageCircle,
  Settings,
  ShieldCheck,
  UserCircle,
  Users,
  WalletCards,
  X,
  type LucideIcon,
} from "lucide-react";
import { toast } from "sonner";
import { Brand } from "@/components/brand";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { useAuth } from "@/lib/auth";
import { USE_MOCKS } from "@/lib/api";
import { cn, initials } from "@/lib/utils";
import type { Role } from "@/lib/types";

type NavigationItem = { label: string; href?: string; icon: LucideIcon };

const menus: Record<Role, NavigationItem[]> = {
  admin: [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Employees", href: "/employees", icon: Users },
    { label: "Attendance", icon: CalendarCheck },
    { label: "Leaves", icon: FileText },
    { label: "Payroll", icon: WalletCards },
    { label: "Announcements", icon: Megaphone },
    { label: "Company settings", icon: Settings },
    { label: "Organization", icon: Building2 },
    { label: "Users", icon: Users },
    { label: "Audit log", icon: ShieldCheck },
  ],
  hr: [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "Employees", href: "/employees", icon: Users },
    { label: "Attendance", icon: CalendarCheck },
    { label: "Corrections", icon: ClipboardCheck },
    { label: "Leaves", icon: FileText },
    { label: "Payroll", icon: WalletCards },
    { label: "Announcements", icon: Megaphone },
    { label: "Profile", icon: UserCircle },
  ],
  employee: [
    { label: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { label: "My attendance", icon: CalendarCheck },
    { label: "Leaves", icon: FileText },
    { label: "Payslips", icon: WalletCards },
    { label: "Announcements", icon: Megaphone },
    { label: "Profile", icon: UserCircle },
  ],
};

function displayName(role: Role, email?: string) {
  if (role === "hr") return "Sarah Ahmed";
  if (role === "employee") return "Ali Raza";
  return email?.split("@")[0].split(/[._]/).map((part) => part[0]?.toUpperCase() + part.slice(1)).join(" ") || "Ali Raza";
}

function Sidebar({ mobile, onClose }: { mobile?: boolean; onClose?: () => void }) {
  const pathname = usePathname();
  const { role = "hr", user, logout } = useAuth();
  const name = displayName(role ?? "hr", user?.email);
  return (
    <aside className={cn("flex h-full w-[230px] flex-col border-r border-line bg-white", mobile ? "w-[280px] shadow-2xl" : "fixed bottom-0 left-0 top-16 z-30 hidden md:flex")}>
      {mobile && (
        <div className="flex h-16 items-center justify-between border-b border-line px-5">
          <Brand />
          <Button variant="ghost" size="icon" onClick={onClose} aria-label="Close menu"><X className="size-5" /></Button>
        </div>
      )}
      <nav className="flex-1 space-y-1 overflow-y-auto p-3 pt-5">
        {menus[role ?? "hr"].map((item) => {
          const Icon = item.icon;
          const active = item.href ? pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href)) : false;
          const classes = cn(
            "flex h-11 w-full items-center gap-3 rounded-md px-3 text-sm font-medium transition-colors",
            active ? "bg-teal-50 text-primary" : "text-slate-600 hover:bg-slate-50",
            !item.href && "cursor-default",
          );
          return item.href ? (
            <Link key={item.label} href={item.href} className={classes} onClick={onClose}><Icon className="size-5" />{item.label}</Link>
          ) : (
            <div key={item.label} className={classes} aria-disabled="true"><Icon className="size-5" />{item.label}</div>
          );
        })}
      </nav>
      <div className="border-t border-line p-4">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">{initials(name)}</div>
          <div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink">{name}</p><p className="text-xs capitalize text-muted">{role}</p></div>
          <button onClick={logout} className="rounded p-2 text-slate-500 hover:bg-slate-100" aria-label="Sign out"><LogOut className="size-4" /></button>
        </div>
      </div>
    </aside>
  );
}

const routeTitles: Record<string, string> = { "/dashboard": "Dashboard", "/employees": "Employees", "/employees/new": "Register employee", "/employees/import": "Import employees" };

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { role = "hr", user, switchRole, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const name = displayName(role ?? "hr", user?.email);
  return (
    <div className="min-h-screen bg-page">
      <header className="fixed inset-x-0 top-0 z-40 flex h-16 items-center border-b border-line bg-white px-4 md:px-7">
        <button className="mr-3 rounded p-2 text-slate-600 hover:bg-slate-100 md:hidden" onClick={() => setMenuOpen(true)} aria-label="Open menu"><Menu className="size-5" /></button>
        <Brand className="hidden md:inline-flex" />
        <span className="text-base font-semibold text-ink md:hidden">{routeTitles[pathname] ?? "HCM Lite"}</span>
        <div className="ml-auto flex items-center gap-3">
          {USE_MOCKS && process.env.NODE_ENV !== "production" && (
            <Select value={role ?? "hr"} onChange={(event) => switchRole(event.target.value as Role)} className="hidden h-9 w-28 sm:block" aria-label="Preview role">
              <option value="admin">Admin</option><option value="hr">HR</option><option value="employee">Employee</option>
            </Select>
          )}
          <button className="relative rounded-full p-2 text-slate-600 hover:bg-slate-100" aria-label="Notifications"><Bell className="size-5" /><span className="absolute right-2 top-1.5 size-2 rounded-full bg-red-500 ring-2 ring-white" /></button>
          <details className="relative">
            <summary className="flex cursor-pointer list-none items-center gap-2 rounded-full py-1 pl-1 pr-2 hover:bg-slate-50">
              <span className="flex size-9 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">{initials(name)}</span>
              <span className="hidden text-left sm:block"><span className="block max-w-28 truncate text-sm font-semibold">{name}</span><span className="block text-xs capitalize text-muted md:hidden">{role}</span></span>
              <ChevronDown className="hidden size-4 text-slate-500 sm:block" />
            </summary>
            <div className="absolute right-0 mt-2 w-48 rounded-md border border-line bg-white p-1 shadow-lg">
              <div className="border-b border-line px-3 py-2"><p className="truncate text-xs text-muted">{user?.email}</p></div>
              <button className="flex w-full items-center gap-2 rounded px-3 py-2 text-sm text-slate-700 hover:bg-slate-50" onClick={logout}><LogOut className="size-4" />Sign out</button>
            </div>
          </details>
        </div>
      </header>
      <Sidebar />
      {menuOpen && <div className="fixed inset-0 z-50 bg-slate-900/35 md:hidden" onClick={() => setMenuOpen(false)}><div className="h-full w-fit" onClick={(event) => event.stopPropagation()}><Sidebar mobile onClose={() => setMenuOpen(false)} /></div></div>}
      <main className="min-h-screen pt-16 md:pl-[230px]">
        <div className="mx-auto max-w-[1536px] p-4 md:p-7">{children}</div>
      </main>
      <button
        className="fixed bottom-5 right-5 z-40 flex h-11 items-center gap-2 rounded-full bg-primary px-5 text-sm font-medium text-white shadow-lg transition hover:bg-[#087d74]"
        onClick={() => toast.info("The assistant will be connected in a later phase.")}
      >
        <MessageCircle className="size-4" /><span className="hidden sm:inline">Ask assistant</span><Bot className="size-4 sm:hidden" />
      </button>
    </div>
  );
}
