"use client";

import { AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogTitle } from "@/components/ui/dialog";

export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel, danger, pending, onConfirm }: { open: boolean; onOpenChange: (open: boolean) => void; title: string; description: string; confirmLabel: string; danger?: boolean; pending?: boolean; onConfirm: () => void }) {
  return <Dialog open={open} onOpenChange={onOpenChange}><DialogContent><div className="flex gap-4"><span className="flex size-12 shrink-0 items-center justify-center rounded-full bg-amber-100 text-amber-700"><AlertTriangle className="size-6" /></span><div><DialogTitle>{title}</DialogTitle><DialogDescription>{description}</DialogDescription></div></div><div className="mt-6 flex justify-end gap-3"><Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button><Button variant={danger ? "danger" : "default"} disabled={pending} onClick={onConfirm}>{pending ? "Working..." : confirmLabel}</Button></div></DialogContent></Dialog>;
}
