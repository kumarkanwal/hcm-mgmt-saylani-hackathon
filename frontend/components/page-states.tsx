"use client";

import { AlertCircle, Inbox } from "lucide-react";
import { Button } from "@/components/ui/button";

export function LoadingSkeleton({ rows = 4, cards = 0 }: { rows?: number; cards?: number }) {
  return (
    <div className="space-y-4" aria-label="Loading" aria-busy="true">
      {cards > 0 && (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: cards }).map((_, index) => <div key={index} className="h-36 animate-pulse rounded-lg border border-line bg-white" />)}
        </div>
      )}
      <div className="card space-y-3 p-5">
        {Array.from({ length: rows }).map((_, index) => <div key={index} className="h-11 animate-pulse rounded-md bg-slate-100" />)}
      </div>
    </div>
  );
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: React.ReactNode }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-dashed border-slate-300 bg-white px-6 text-center">
      <div className="mb-3 rounded-full bg-teal-50 p-3 text-primary"><Inbox className="size-6" /></div>
      <h3 className="font-semibold text-ink">{title}</h3>
      <p className="mt-1 max-w-md text-sm text-muted">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex min-h-64 flex-col items-center justify-center rounded-lg border border-red-200 bg-red-50/40 px-6 text-center">
      <AlertCircle className="mb-3 size-7 text-red-600" />
      <h3 className="font-semibold text-ink">Unable to load this page</h3>
      <p className="mt-1 max-w-md text-sm text-slate-600">{message}</p>
      <Button className="mt-4" variant="outline" onClick={onRetry}>Try again</Button>
    </div>
  );
}
