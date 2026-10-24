"use client";

import type { ColumnDef } from "@tanstack/react-table";
import { useQuery } from "@tanstack/react-query";
import { Download, MoreVertical, Plus, Search, Upload } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { DataTable } from "@/components/data-table";
import { ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { Department, Employee, ListResponse } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";
import { format } from "date-fns";

export default function EmployeesPage() {
  usePageTitle("Employees");
  const router = useRouter();
  const { role } = useAuth();
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  useEffect(() => { if (role === "employee") router.replace("/dashboard"); }, [role, router]);
  const query = useQuery({ queryKey: ["employees", search, departmentId, status, page], queryFn: () => api.get<ListResponse<Employee>>("/employees", { search, department_id: departmentId, status, page, page_size: 10 }) });
  const departments = useQuery({ queryKey: ["departments"], queryFn: () => api.get<ListResponse<Department>>("/departments") });
  const columns = useMemo<ColumnDef<Employee>[]>(() => [
    { header: "#", cell: ({ row }) => (page - 1) * 10 + row.index + 1 },
    { accessorKey: "employee_code", header: "Code" },
    { header: "Name", cell: ({ row }) => <Link href={`/employees/${row.original.id}`} className="flex items-center gap-3"><span className="flex size-9 items-center justify-center rounded-full bg-slate-100 text-[11px] text-slate-600">{initials(`${row.original.first_name} ${row.original.last_name}`)}</span><div><p className="font-semibold text-ink hover:text-primary">{row.original.first_name} {row.original.last_name}</p><p className="text-xs text-muted">{row.original.email}</p></div></Link> },
    { accessorKey: "department", header: "Department" },
    { accessorKey: "designation", header: "Designation" },
    { header: "Status", cell: ({ row }) => <StatusBadge status={row.original.status[0].toUpperCase() + row.original.status.slice(1)} /> },
    { header: "Join date", cell: ({ row }) => format(new Date(`${row.original.join_date}T12:00:00`), "dd MMM yyyy") },
    { id: "actions", header: "", cell: () => <button className="rounded p-1 text-slate-500 hover:bg-slate-100" aria-label="Employee actions"><MoreVertical className="size-4" /></button> },
  ], [page]);
  if (role === "employee") return null;
  return (
    <div className="space-y-6">
      <PageHeader title="Employees" subtitle="View and manage all employees in your organization." actions={role === "hr" ? <><Button variant="outline" asChild><Link href="/employees/import"><Upload className="size-4" />Import CSV</Link></Button><Button variant="outline" onClick={() => toast.success("Employee export prepared")}><Download className="size-4" />Export CSV</Button><Button asChild><Link href="/employees/new"><Plus className="size-4" />Register employee</Link></Button></> : undefined} />
      <section className="card overflow-hidden">
        <div className="grid gap-3 p-4 lg:grid-cols-[1.6fr_0.75fr_0.65fr_auto]">
          <div className="relative"><Search className="absolute left-3 top-1/2 size-5 -translate-y-1/2 text-slate-500" /><Input value={search} onChange={(event) => { setSearch(event.target.value); setPage(1); }} className="pl-10" placeholder="Search by name, code or email..." /></div>
          <Select value={departmentId} onChange={(event) => { setDepartmentId(event.target.value); setPage(1); }}><option value="">All Departments</option>{departments.data?.items.map((department) => <option key={department.id} value={department.id}>{department.name}</option>)}</Select>
          <Select value={status} onChange={(event) => { setStatus(event.target.value); setPage(1); }}><option value="">All Status</option><option value="active">Active</option><option value="probation">Probation</option><option value="inactive">Inactive</option></Select>
          <Button variant="ghost" onClick={() => { setSearch(""); setDepartmentId(""); setStatus(""); }}>Clear filters</Button>
        </div>
        {query.isLoading ? <div className="p-4"><LoadingSkeleton rows={7} /></div> : query.isError ? <div className="p-4"><ErrorState message={query.error.message} onRetry={() => query.refetch()} /></div> : query.data ? <DataTable data={query.data.items} columns={columns} total={query.data.total} page={query.data.page} pageSize={query.data.page_size} onPageChange={setPage} emptyTitle="No employees yet" emptyDescription="Register your first employee or adjust the current filters." /> : null}
      </section>
    </div>
  );
}
