"use client";

import { flexRender, getCoreRowModel, useReactTable, type ColumnDef } from "@tanstack/react-table";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/page-states";

export function DataTable<T>({
  data,
  columns,
  total,
  page,
  pageSize,
  onPageChange,
  emptyTitle = "No records found",
  emptyDescription = "Try changing your search or filters.",
}: {
  data: T[];
  columns: ColumnDef<T>[];
  total: number;
  page: number;
  pageSize: number;
  onPageChange: (page: number) => void;
  emptyTitle?: string;
  emptyDescription?: string;
}) {
  const table = useReactTable({ data, columns, getCoreRowModel: getCoreRowModel() });
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const start = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const end = Math.min(page * pageSize, total);

  if (!data.length) return <EmptyState title={emptyTitle} description={emptyDescription} />;

  return (
    <>
      <div className="overflow-x-auto scrollbar-thin">
        <table className="w-full min-w-[920px] border-collapse text-left text-sm">
          <thead className="bg-slate-50 text-xs font-semibold text-slate-500">
            {table.getHeaderGroups().map((group) => (
              <tr key={group.id}>
                {group.headers.map((header) => <th key={header.id} className="h-11 px-4">{header.isPlaceholder ? null : flexRender(header.column.columnDef.header, header.getContext())}</th>)}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows.map((row) => (
              <tr key={row.id} className="border-b border-line last:border-0 hover:bg-slate-50/60">
                {row.getVisibleCells().map((cell) => <td key={cell.id} className="h-14 px-4 text-slate-700">{flexRender(cell.column.columnDef.cell, cell.getContext())}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-col gap-3 border-t border-line px-4 py-4 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
        <span>Showing {start} to {end} of {total} employees</span>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={() => onPageChange(page - 1)} disabled={page <= 1} aria-label="Previous page"><ChevronLeft className="size-4" /></Button>
          {Array.from({ length: Math.min(pages, 5) }, (_, index) => index + 1).map((number) => (
            <Button key={number} size="icon" variant={number === page ? "default" : "ghost"} onClick={() => onPageChange(number)}>{number}</Button>
          ))}
          <Button variant="outline" size="icon" onClick={() => onPageChange(page + 1)} disabled={page >= pages} aria-label="Next page"><ChevronRight className="size-4" /></Button>
        </div>
      </div>
    </>
  );
}
