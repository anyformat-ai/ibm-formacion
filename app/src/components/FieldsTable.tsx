import { needsReview } from "@/lib/review";
import type { FieldValue, ScalarField, TableField } from "@/lib/types";
import { ConfidenceBadge } from "./ConfidenceBadge";

/** Campos simples: una fila por campo, con valor, confianza y evidencia. */
export function FieldsTable({ fields, threshold }: { fields: ScalarField[]; threshold: number }) {
  return (
    <table className="table">
      <thead>
        <tr>
          <th className="w-1/4">Campo</th>
          <th>Valor</th>
          <th className="w-20">Confianza</th>
          <th className="w-1/3">Evidencia</th>
        </tr>
      </thead>
      <tbody>
        {fields.map((f) => {
          const review = needsReview(f, threshold);
          return (
            <tr key={f.key} className={review ? "bg-warning-soft/60" : undefined}>
              <td className="text-ink-2">
                {f.label}
                {review && <Tag className="bg-warning-soft text-warning">a revisar</Tag>}
              </td>
              <td>
                <Value v={f} />
              </td>
              <td>
                <ConfidenceBadge confidence={f.confidence} threshold={threshold} />
              </td>
              <td>
                <EvidenceDetails v={f} />
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** Campo objeto (lista de filas) como sub-tabla. La evidencia de cada celda sale al pasar el ratón. */
export function ObjectTable({ field, threshold }: { field: TableField; threshold: number }) {
  return (
    <div className="flex flex-col gap-2">
      <h4 className="text-[13px] font-semibold">
        {field.label} <span className="font-normal text-ink-3">· {field.rows.length} {field.rows.length === 1 ? "fila" : "filas"}</span>
      </h4>
      <div className="overflow-x-auto rounded-control bg-surface shadow-card">
        <table className="table">
          <thead>
            <tr>
              {field.columns.map((c) => (
                <th key={c}>{c}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {field.rows.map((row, i) => (
              <tr key={i}>
                {field.columns.map((c) => {
                  const v = row[c];
                  if (!v) return <td key={c} />;
                  return (
                    <td key={c} className={needsReview(v, threshold) ? "bg-warning-soft/60" : undefined}>
                      <div className="flex items-start gap-2">
                        <Value v={v} />
                        <ConfidenceBadge confidence={v.confidence} threshold={threshold} />
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Value({ v }: { v: FieldValue }) {
  const hover = v.evidence.map((e) => `p. ${e.page}: ${e.text}`).join("\n");
  return (
    <span title={hover || undefined} className="font-mono text-[12.5px] break-words">
      {v.value ?? <span className="text-ink-4">—</span>}
      {v.corrected && <Tag className="bg-accent-soft text-accent">corregido</Tag>}
    </span>
  );
}

function EvidenceDetails({ v }: { v: FieldValue }) {
  if (v.evidence.length === 0) return <span className="text-ink-4">—</span>;
  return (
    <details className="text-[12.5px] text-ink-2">
      <summary className="cursor-pointer select-none text-ink-3">
        p. {[...new Set(v.evidence.map((e) => e.page))].join(", ")}
      </summary>
      {v.evidence.map((e, i) => (
        <p key={i} className="mt-1 whitespace-pre-wrap">
          «{e.text}»
        </p>
      ))}
    </details>
  );
}

function Tag({ className, children }: { className: string; children: React.ReactNode }) {
  return (
    <span className={`ml-2 inline-block rounded-badge px-1.5 py-px font-sans text-[11px] font-semibold ${className}`}>
      {children}
    </span>
  );
}
