"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, CalendarCheck, FileText, Megaphone } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api } from "@/lib/api";
import type { ListResponse } from "@/lib/types";

type Notification = { id: string; title: string; body: string; type: string; link: string; is_read: boolean; created_at: string };

export function NotificationsDropdown() {
  const [open, setOpen] = useState(false);
  const router = useRouter();
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["notifications"], queryFn: () => api.get<ListResponse<Notification>>("/notifications"), refetchInterval: 30_000 });
  const read = useMutation({ mutationFn: (id: string) => api.patch(`/notifications/${id}/read`), onSuccess: () => void client.invalidateQueries({ queryKey: ["notifications"] }) });
  const items = query.data?.items ?? [];
  const unread = items.filter((item) => !item.is_read).length;
  const openNotification = (item: Notification) => { if (!item.is_read) read.mutate(item.id); setOpen(false); router.push(item.link); };
  const markAllRead = async () => { await Promise.all(items.filter((item) => !item.is_read).map((item) => api.patch(`/notifications/${item.id}/read`))); void client.invalidateQueries({ queryKey: ["notifications"] }); };
  const icons = { leave: CalendarCheck, payslip: FileText, announcement: Megaphone };
  return <div className="relative"><button className="relative rounded-full p-2 text-slate-600 hover:bg-slate-100" onClick={() => setOpen((value) => !value)} aria-label="Notifications"><Bell className="size-5" />{unread > 0 && <span className="absolute -right-0.5 -top-0.5 flex size-5 items-center justify-center rounded-full bg-red-500 text-[10px] font-bold text-white ring-2 ring-white">{unread}</span>}</button>{open && <div className="fixed inset-x-3 top-16 z-50 overflow-hidden rounded-lg border border-line bg-white shadow-2xl sm:absolute sm:-right-24 sm:left-auto sm:top-12 sm:w-[420px]"><div className="flex items-center justify-between border-b border-line p-4"><h2 className="font-semibold">Notifications</h2><span className="text-xs text-muted">{unread} unread</span></div>{query.isLoading ? <div className="space-y-3 p-4">{[1, 2, 3].map((item) => <div key={item} className="h-14 animate-pulse rounded bg-slate-100" />)}</div> : query.isError ? <p className="p-6 text-center text-sm text-red-600">{query.error.message}</p> : !items.length ? <p className="p-8 text-center text-sm text-muted">No notifications.</p> : <div className="max-h-96 divide-y divide-line overflow-y-auto">{items.map((item) => { const Icon = icons[item.type as keyof typeof icons] ?? Bell; return <button key={item.id} onClick={() => openNotification(item)} className="flex w-full gap-3 p-4 text-left hover:bg-slate-50"><span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-teal-50 text-primary"><Icon className="size-5" /></span><span className="min-w-0 flex-1"><strong className="block text-sm">{item.title}</strong><span className="mt-1 block text-xs text-muted">{item.body}</span></span>{!item.is_read && <i className="mt-2 size-2 shrink-0 rounded-full bg-blue-500" />}</button>; })}</div>}{unread > 0 && <button className="w-full border-t border-line p-3 text-sm font-medium text-blue-600 hover:bg-slate-50" onClick={() => void markAllRead()}>Mark all as read</button>}</div>}</div>;
}
