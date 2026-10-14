# CLAUDE.md

Starter de formación: Next 15 (App Router), React 19, TypeScript estricto, Tailwind v4, bun. UI en español (es-ES),
identificadores en inglés. La audiencia lo lee en 5 minutos: mantenlo pequeño y legible.

## Reglas

- **Todo lo que toca `@anyformat/sdk` vive en `src/lib/anyformat.ts`.** Los componentes solo conocen los tipos de
  `src/lib/types.ts`. Si necesitas un dato nuevo del run, añádelo a `normalize()` y al tipo, no leas el JSON crudo
  en la UI.
- La API key (`ANYFORMAT_API_KEY`) solo se lee en el servidor. Nunca la pases a un componente cliente.
- Rutas y server actions finos: validan la entrada y llaman a `src/lib/`.
- Ficheros pequeños (≲150 líneas) y un componente por fichero. Sin librerías de UI: Tailwind + las clases de
  `globals.css` (`btn`, `btn-primary`, `control`, `label`, `table`) y los tokens de Shift (`bg-surface`,
  `text-ink-2`, `rounded-card`, `shadow-card`, `bg-warning-soft`…).
- Antes de terminar: `bun run typecheck` y `bun run build`.

## SDK (@anyformat/sdk 1.9.0)

- `new Anyformat({ apiKey })`
- `af.iterWorkflows()` → `Workflow { id, name }` (también `af.listWorkflows({ limit, cursor })` → `{ items, nextCursor }`)
- `af.upload(workflowId, file, { onConflict: "rename" })` → `Upload`; `upload.run()` → `Run`
- `run.wait({ timeoutMs, pollMs })` → `Result`; `result.raw` es `ResultsResponseV3`
- `af.getRun(runId)` → `RunDetailV3` (para consultar un run más tarde)
- Errores: `APIError` (`status`, `errorCode`), `SDKTimeoutError`, `RunFailedError`
- Tipos en `node_modules/@anyformat/sdk/dist/index.d.ts`; léelos en vez de suponer.

## Contrato de datos (results de un run v3)

- `extractions[].fields[name]` = `{ value: string|null, confidence: 0–100|null, evidence: [{text, page_number}],
  value_override }`. `value_override` (corrección de un revisor) gana a `value`.
- Campo objeto = array de filas `Record<string, campo>`, un solo nivel.
- `extractions[].validations[]` = `{ rule_id, status: "pass"|"fail"|"inconclusive", severity, detail }`.
- `classifications[0].category` = tipo de documento (si hay nodo classify).
- `verification_url` = el documento en el espacio de revisión de anyformat.
- Ejemplo real: `../referencia/calas-luismi/run-ejemplo_pastrana-8b.json`.
