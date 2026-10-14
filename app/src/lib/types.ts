// El resultado normalizado que ve la UI. `src/lib/anyformat.ts` lo construye a partir del JSON
// crudo de un run (v3); los componentes solo conocen estos tipos.

export type WorkflowSummary = { id: string; name: string };

export type Evidence = { text: string; page: number };

/** Un valor extraído: lo que leyó el modelo, o la corrección de un revisor si existe. */
export type FieldValue = {
  value: string | null;
  /** 0–100, o null si el backend no dio confianza (p. ej. entrada manual). */
  confidence: number | null;
  evidence: Evidence[];
  /** true cuando el valor viene de `value_override` (corregido en anyformat). */
  corrected: boolean;
};

/** Campo simple: un valor. */
export type ScalarField = FieldValue & { kind: "scalar"; key: string; label: string };

/** Campo objeto: una lista de filas (p. ej. líneas de factura), un nivel de profundidad. */
export type TableField = {
  kind: "table";
  key: string;
  label: string;
  columns: string[];
  rows: Record<string, FieldValue>[];
};

export type Field = ScalarField | TableField;

export type Validation = {
  id: string;
  status: "pass" | "fail" | "inconclusive" | string;
  severity: string;
  detail: string | null;
};

export type DocumentResult = {
  fileName: string;
  runId: string;
  workflowId: string;
  /** Tipo de documento si el workflow tiene un nodo classify. */
  documentType: { category: string; confidence: number | null } | null;
  fields: Field[];
  validations: Validation[];
  verificationUrl: string | null;
};

/** Un documento en la sesión del navegador: su estado y, al terminar, su resultado o su error. */
export type Job = { id: string; fileName: string; startedAt: number } & (
  | { status: "processing" }
  | { status: "done"; result: DocumentResult }
  | { status: "error"; error: string }
);
