"use client";

import { useMutation } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Download, FileSpreadsheet, Upload, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { EmptyState } from "@/components/page-states";
import { PageHeader } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { usePageTitle } from "@/hooks/use-page-title";

type ImportError = { row: number; field: string; reason: string };
type DryRunResult = { valid_rows: number; errors: ImportError[] };
type ImportResult = { imported_rows: number; errors: ImportError[] };

export default function ImportEmployeesPage() {
  usePageTitle("Import employees");
  const router = useRouter();
  const { role } = useAuth();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<DryRunResult | null>(null);
  useEffect(() => { if (role !== "hr") router.replace("/dashboard"); }, [role, router]);
  const makeBody = () => { const body = new FormData(); if (file) body.append("file", file); return body; };
  const validate = useMutation({ mutationFn: () => api.post<DryRunResult>("/employees/import", makeBody(), { dry_run: true }), onSuccess: setResult });
  const importRows = useMutation({ mutationFn: () => api.post<ImportResult>("/employees/import", makeBody(), { dry_run: false }), onSuccess: (response) => { toast.success(`${response.imported_rows} employees imported`); router.push("/employees"); } });
  if (role !== "hr") return null;
  return (
    <div className="space-y-6">
      <div className="text-sm text-muted"><Link href="/employees" className="hover:text-primary">Employees</Link><span className="mx-2">/</span>Import CSV</div>
      <PageHeader title="Import employees" subtitle="Upload a CSV file, review validation results, then import valid rows." actions={<Button variant="outline" asChild><a href="/sample-employees.csv" download><Download className="size-4" />Download sample CSV</a></Button>} />
      <section className="card p-6">
        <h2 className="text-lg font-semibold">Upload employee data</h2><p className="mt-1 text-sm text-muted">CSV files up to 5 MB are supported. Use the sample file for the required columns.</p>
        {!file ? (
          <button type="button" className="mt-5 flex min-h-64 w-full flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 px-6 text-center transition hover:border-primary hover:bg-teal-50/40" onClick={() => fileInput.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); setFile(event.dataTransfer.files[0] ?? null); setResult(null); }}>
            <span className="flex size-14 items-center justify-center rounded-full bg-teal-50 text-primary"><Upload className="size-6" /></span><strong className="mt-4">Choose a CSV file or drag it here</strong><span className="mt-1 text-sm text-muted">The file is validated before anything is imported.</span>
          </button>
        ) : (
          <div className="mt-5 flex flex-col gap-4 rounded-lg border border-teal-200 bg-teal-50/50 p-5 sm:flex-row sm:items-center">
            <span className="flex size-12 shrink-0 items-center justify-center rounded-lg bg-white text-primary"><FileSpreadsheet className="size-6" /></span><div className="min-w-0 flex-1"><p className="truncate font-semibold">{file.name}</p><p className="text-xs text-muted">{(file.size / 1024).toFixed(1)} KB</p></div><Button variant="ghost" size="icon" onClick={() => { setFile(null); setResult(null); }} aria-label="Remove file"><X className="size-5" /></Button><Button onClick={() => validate.mutate()} disabled={validate.isPending}>{validate.isPending ? "Validating..." : "Validate CSV"}</Button>
          </div>
        )}
        <input ref={fileInput} type="file" accept=".csv,text/csv" className="hidden" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setResult(null); }} />
        {validate.isError && <p className="mt-4 text-sm text-red-600">{(validate.error as ApiError).message}</p>}
      </section>
      {!result ? <EmptyState title="No validation results" description="Upload a CSV file and select Validate CSV to review valid rows and errors." /> : (
        <section className="card overflow-hidden">
          <div className="grid gap-4 border-b border-line p-5 sm:grid-cols-2">
            <div className="flex items-center gap-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4"><CheckCircle2 className="size-8 text-emerald-600" /><div><p className="text-2xl font-bold">{result.valid_rows}</p><p className="text-sm text-emerald-800">Valid rows ready to import</p></div></div>
            <div className="flex items-center gap-4 rounded-lg border border-amber-200 bg-amber-50 p-4"><AlertTriangle className="size-8 text-amber-600" /><div><p className="text-2xl font-bold">{result.errors.length}</p><p className="text-sm text-amber-800">Rows need attention</p></div></div>
          </div>
          <div className="p-5"><h2 className="font-semibold">Validation errors</h2>{result.errors.length ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[620px] text-left text-sm"><thead className="bg-slate-50 text-xs text-muted"><tr><th className="px-4 py-3">Row</th><th className="px-4 py-3">Field</th><th className="px-4 py-3">Reason</th></tr></thead><tbody>{result.errors.map((error) => <tr key={`${error.row}-${error.field}`} className="border-b border-line"><td className="px-4 py-3">{error.row}</td><td className="px-4 py-3 font-medium">{error.field}</td><td className="px-4 py-3 text-red-600">{error.reason}</td></tr>)}</tbody></table></div> : <p className="mt-4 rounded-lg bg-emerald-50 p-4 text-sm text-emerald-700">All rows passed validation.</p>}</div>
          <div className="flex flex-col-reverse gap-3 border-t border-line p-4 sm:flex-row sm:justify-end"><Button variant="outline" onClick={() => { setFile(null); setResult(null); }}>Choose another file</Button><Button onClick={() => importRows.mutate()} disabled={importRows.isPending || result.valid_rows === 0}>{importRows.isPending ? "Importing..." : `Import ${result.valid_rows} valid rows`}</Button></div>
          {importRows.isError && <p className="px-5 pb-5 text-sm text-red-600">{(importRows.error as ApiError).message}</p>}
        </section>
      )}
    </div>
  );
}
