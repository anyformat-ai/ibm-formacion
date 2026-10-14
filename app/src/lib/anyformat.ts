// El único fichero que habla con anyformat. Solo se usa en el servidor: la API key nunca llega al navegador.
import { Anyformat, APIError, SDKTimeoutError, type Extraction, type ResultsResponseV3 } from "@anyformat/sdk";
import type { DocumentResult, Field, FieldValue, Validation, WorkflowSummary } from "./types";

/** Un documento de varias páginas puede tardar 1–3 min. Debe caber en el `maxDuration` de la ruta. */
const RUN_TIMEOUT_MS = 280_000;
const POLL_MS = 3_000;

function client(): Anyformat {
  const apiKey = process.env.ANYFORMAT_API_KEY;
  if (!apiKey) throw new Error("Falta ANYFORMAT_API_KEY en .env.local");
  return new Anyformat({ apiKey });
}

/** Todos los workflows de la cuenta de la API key, por nombre. */
export async function listWorkflows(): Promise<WorkflowSummary[]> {
  const workflows: WorkflowSummary[] = [];
  for await (const wf of client().iterWorkflows()) workflows.push({ id: wf.id, name: wf.name });
  return workflows.sort((a, b) => a.name.localeCompare(b.name, "es"));
}

/** Sube un documento a un workflow, lo ejecuta y espera al resultado. */
export async function runDocument(workflowId: string, file: File): Promise<DocumentResult> {
  const af = client();
  // `rename`: si ya subiste un fichero con ese nombre a este workflow, no falla con 409.
  const upload = await af.upload(workflowId, file, { onConflict: "rename" });
  const run = await upload.run();
  const result = await run.wait({ timeoutMs: RUN_TIMEOUT_MS, pollMs: POLL_MS });
  return normalize(result.raw, { fileName: file.name, runId: run.id, workflowId });
}

/** Mensaje legible para la UI a partir de un error del SDK. */
export function errorMessage(err: unknown): string {
  if (err instanceof SDKTimeoutError) return "El documento sigue procesándose; revisa el run en anyformat.";
  if (err instanceof APIError) {
    if (err.status === 401) return "API key no válida (revisa ANYFORMAT_API_KEY).";
    if (err.status === 402) return "Sin créditos en la cuenta de anyformat.";
    if (err.status === 404) return "No existe ese workflow en esta cuenta.";
    return `anyformat respondió ${err.status}: ${err.message}`;
  }
  return err instanceof Error ? err.message : String(err);
}

// --- Normalización del JSON crudo (GET /v3/runs/{id}/ → results) -------------------------------------

type RawField = Exclude<Extraction["fields"][string], unknown[]>;

export function normalize(
  raw: ResultsResponseV3,
  meta: { fileName: string; runId: string; workflowId: string },
): DocumentResult {
  const extractions = raw.extractions ?? [];
  const multi = extractions.length > 1;
  const classification = raw.classifications?.[0];

  return {
    ...meta,
    documentType: classification
      ? { category: classification.category, confidence: classification.confidence }
      : null,
    // Con varias extracciones (un workflow con splits), cada campo lleva delante el nombre de su parte.
    fields: extractions.flatMap((ex) =>
      Object.entries(ex.fields).map(([key, f]) =>
        toField(key, f, multi ? ex.split_name ?? ex.partition ?? null : null),
      ),
    ),
    validations: extractions.flatMap((ex) => (ex.validations ?? []).map(toValidation)),
    verificationUrl: raw.verification_url ?? null,
  };
}

function toField(key: string, raw: Extraction["fields"][string], prefix: string | null): Field {
  const label = (prefix ? `${prefix} · ` : "") + humanize(key);
  if (Array.isArray(raw)) {
    // Campo objeto: lista de filas, cada fila un mapa columna → campo.
    const columns = [...new Set(raw.flatMap((row) => Object.keys(row)))];
    const rows = raw.map((row) =>
      Object.fromEntries(Object.entries(row).map(([col, f]) => [col, toValue(f)])),
    );
    return { kind: "table", key, label, columns, rows };
  }
  return { kind: "scalar", key, label, ...toValue(raw) };
}

function toValue(f: RawField): FieldValue {
  // Si un revisor lo corrigió en anyformat, manda `value_override`.
  const corrected = f.value_override !== null && f.value_override !== undefined;
  return {
    value: asText(corrected ? f.value_override : f.value),
    confidence: f.confidence ?? null,
    evidence: (f.evidence ?? []).map((e) => ({ text: e.text, page: e.page_number })),
    corrected,
  };
}

function toValidation(v: NonNullable<Extraction["validations"]>[number]): Validation {
  return { id: v.rule_id, status: v.status, severity: v.severity, detail: v.detail ?? v.description ?? null };
}

/** `value` llega como string o null; por si acaso, cualquier otra cosa se pasa a texto. */
function asText(v: unknown): string | null {
  if (v === null || v === undefined || v === "") return null;
  return typeof v === "string" ? v : JSON.stringify(v);
}

/** "fecha_inicio_prevista" → "Fecha inicio prevista" */
export function humanize(key: string): string {
  const s = key.replace(/[_-]+/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}
