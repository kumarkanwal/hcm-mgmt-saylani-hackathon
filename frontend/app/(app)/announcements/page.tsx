"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CalendarDays, FileText, Megaphone, MoreHorizontal, Plus, Search, Users } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { EmptyState, ErrorState, LoadingSkeleton } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { ListResponse } from "@/lib/types";
import { initials } from "@/lib/utils";
import { usePageTitle } from "@/hooks/use-page-title";

type Announcement = { id: string; title: string; body: string; created_at: string; author_name?: string; author_role?: string };

export default function AnnouncementsPage() {
  usePageTitle("Announcements");
  const { role } = useAuth();
  const client = useQueryClient();
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const query = useQuery({ queryKey: ["announcements-page"], queryFn: () => api.get<ListResponse<Announcement>>("/announcements") });
  const post = useMutation({ mutationFn: () => api.post("/announcements", { title, body }), onSuccess: () => { toast.success("Announcement posted"); setOpen(false); setTitle(""); setBody(""); void client.invalidateQueries({ queryKey: ["announcements-page"] }); void client.invalidateQueries({ queryKey: ["announcements"] }); } });
  if (query.isLoading) return <LoadingSkeleton rows={5} />;
  if (query.isError) return <ErrorState message={query.error.message} onRetry={() => query.refetch()} />;
  const items = (query.data?.items ?? []).filter((item) => !search || `${item.title} ${item.body}`.toLowerCase().includes(search.toLowerCase()));
  const icons = [Megaphone, CalendarDays, FileText, Users];
  return <div className="space-y-5"><PageHeader title="Announcements" subtitle="Share important updates and information with your team." actions={<><div className="relative"><Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" /><Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search announcements..." className="w-64 pl-10" /></div>{role !== "employee" && <Button onClick={() => setOpen(true)}><Plus className="size-4" />New announcement</Button>}</>} />
    {!items.length ? <EmptyState title="No announcements" description={role === "employee" ? "Company updates will appear here." : "Post the first announcement for your team."} /> : <div className="space-y-3">{items.map((item, index) => { const Icon = icons[index % icons.length]; const author = item.author_name ?? (index === 0 ? "Sarah Ahmed" : "Bilal Ahmed"); return <article key={item.id} className="card flex gap-4 p-5"><span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-teal-50 text-primary"><Icon className="size-6" /></span><div className="min-w-0 flex-1"><div className="flex flex-col justify-between gap-2 sm:flex-row"><div><h2 className="font-semibold">{item.title}</h2><p className="mt-1 text-sm text-slate-600">{item.body}</p></div><time className="shrink-0 text-xs text-muted">{item.created_at.replace("T", " ").slice(0, 16)}</time></div><div className="mt-4 flex items-center justify-between"><span className="flex items-center gap-2 text-xs text-muted"><i className="flex size-7 items-center justify-center rounded-full bg-slate-100 not-italic">{initials(author)}</i>{author}</span><button className="rounded p-2 hover:bg-slate-50"><MoreHorizontal className="size-4" /></button></div></div></article>; })}</div>}
    <Dialog open={open} onOpenChange={setOpen}><DialogContent><DialogTitle>New announcement</DialogTitle><DialogDescription>Create a new announcement for all employees.</DialogDescription><div className="mt-5 space-y-4"><label className="block text-sm font-medium">Title<Input className="mt-2" value={title} onChange={(event) => setTitle(event.target.value)} /></label><label className="block text-sm font-medium">Message<Textarea className="mt-2 min-h-32" maxLength={500} value={body} onChange={(event) => setBody(event.target.value)} /></label><p className="text-right text-xs text-muted">{body.length}/500</p><div className="flex justify-end gap-3"><Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button><Button disabled={!title || !body || post.isPending} onClick={() => post.mutate()}>{post.isPending ? "Posting..." : "Post"}</Button></div></div></DialogContent></Dialog>
  </div>;
}
