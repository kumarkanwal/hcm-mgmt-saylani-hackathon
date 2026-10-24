"use client";

import { useQuery } from "@tanstack/react-query";
import { BellRing, Database, FileText } from "lucide-react";
import { format } from "date-fns";
import { api } from "@/lib/api";
import type { ListResponse } from "@/lib/types";

type Announcement = { id: string; title: string; body: string; created_at: string };

export function AnnouncementsCard() {
  const query = useQuery({ queryKey: ["announcements"], queryFn: () => api.get<ListResponse<Announcement>>("/announcements") });
  return (
    <section className="card min-w-0 p-5">
      <div className="mb-3 flex items-center justify-between"><h2 className="text-lg font-semibold">Announcements</h2><button className="text-xs font-medium text-blue-600">View all</button></div>
      {query.isLoading ? <div className="space-y-3">{[1, 2, 3].map((item) => <div key={item} className="h-14 animate-pulse rounded bg-slate-100" />)}</div> : query.isError ? <p className="py-8 text-center text-sm text-red-600">{query.error.message}</p> : !query.data?.items.length ? <p className="py-8 text-center text-sm text-muted">No announcements yet.</p> : (
        <div className="divide-y divide-line">
          {query.data.items.slice(0, 3).map((item, index) => {
            const Icon = [BellRing, Database, FileText][index % 3];
            return (
              <article key={item.id} className="flex gap-3 py-3 first:pt-1">
                <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-teal-50 text-primary"><Icon className="size-4" /></span>
                <div className="min-w-0 flex-1"><div className="flex justify-between gap-2"><h3 className="truncate text-sm font-semibold">{item.title}</h3><time className="shrink-0 text-[11px] text-muted">{format(new Date(item.created_at), "dd MMM yyyy")}</time></div><p className="mt-1 line-clamp-2 text-xs leading-5 text-muted">{item.body}</p></div>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
