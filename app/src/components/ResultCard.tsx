"use client";

import { useEffect, useState } from "react";
import { countToReview } from "@/lib/review";
import type { Job, ScalarField, TableField, Validation } from "@/lib/types";
import { FieldsTable, ObjectTable } from "./FieldsTable";

/** La tarjeta de un documento: mientras se procesa, el tiempo; al terminar, todo lo extraído. */
export function ResultCard(job: Job & { threshold: number }) {
  const { threshold } = job;
  const result = job.status === "done" ? job.result : null;
  const scalars = result?.fields.filter((f): f is ScalarField => f.kind === "scalar") ?? [];
  const tables = result?.fields.filter((f): f is TableField => f.kind === "table") ?? [];
  const toReview = result ? countToReview(result.fields, threshold) : 0;

  return (
    <article className="rounded-card bg-surface shadow-card">
      <header className="flex flex-wrap items-center gap-3 border-b border-hair px-5 py-3">
        <h3 className="min-w-0 truncate text-[14.5px] font-semibold">{job.fileName}</h3>
        {result?.documentType && (
          <Chip className="bg-accent-soft text-accent">
            {result.documentType.category}
            {result.documentType.confidence !== null && ` · ${Math.round(result.documentType.confidence)}`}
          </Chip>
        )}
        <div className="ml-auto flex items-center gap-3">
          {job.status === "processing" && (
            <span className="text-[12.5px] text-ink-3">
              Procesando… <Elapsed since={job.startedAt} />
            </span>
          )}
          {result && (
            <Chip className={toReview ? "bg-warning-soft text-warning" : "bg-success-soft text-success"}>
              {toReview ? `${toReview} campos a revisar` : "Todo por encima del umbral"}
            </Chip>
          )}
          {result?.verificationUrl && (
            <a className="btn" href={result.verificationUrl} target="_blank" rel="noreferrer">
              Revisar en anyformat ↗
            </a>
          )}
        </div>
      </header>

      {job.status === "error" && <p className="px-5 py-4 text-[13px] text-danger">{job.error}</p>}

      {result && (
        <div className="flex flex-col gap-6 px-5 py-4">
          {result.validations.length > 0 && <Validations items={result.validations} />}
          {scalars.length > 0 && <FieldsTable fields={scalars} threshold={threshold} />}
          {tables.map((t) => (
            <ObjectTable key={t.key} field={t} threshold={threshold} />
          ))}
          {result.fields.length === 0 && <p className="text-[13px] text-ink-3">Este workflow no extrae campos.</p>}
        </div>
      )}
    </article>
  );
}

const STATUS_STYLE: Record<string, string> = {
  pass: "bg-success-soft text-success",
  fail: "bg-danger-soft text-danger",
  inconclusive: "bg-warning-soft text-warning",
};

function Validations({ items }: { items: Validation[] }) {
  return (
    <ul className="flex flex-col gap-1.5">
      {items.map((v, i) => (
        <li key={`${v.id}-${i}`} className="flex items-baseline gap-2 text-[13px]">
          <Chip className={STATUS_STYLE[v.status] ?? "bg-well text-ink-2"}>{v.status}</Chip>
          <span className="font-mono text-[12.5px]">{v.id}</span>
          {v.detail && <span className="text-ink-2">{v.detail}</span>}
        </li>
      ))}
    </ul>
  );
}

function Chip({ className, children }: { className: string; children: React.ReactNode }) {
  return <span className={`rounded-badge px-2 py-0.5 text-[12px] font-semibold ${className}`}>{children}</span>;
}

/** Cronómetro m:ss desde `since`. */
function Elapsed({ since }: { since: number }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  const s = Math.max(0, Math.floor((now - since) / 1000));
  return <span className="font-mono">{`${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`}</span>;
}
