# anyformat · Starter (Next.js)

El «hola mundo» de una app documental sobre anyformat: eliges un workflow, arrastras uno o varios PDFs y ves
lo extraído campo a campo, con su confianza, su evidencia y las validaciones. Funciona con cualquier workflow
(calas y canalizaciones, facturas, albaranes…).

## Puesta en marcha

```bash
nvm use                      # Node 22 (.nvmrc)
bun install
cp .env.example .env.local   # y pon tu ANYFORMAT_API_KEY
bun dev                      # http://localhost:3000
```

- `ANYFORMAT_API_KEY`: obligatoria, se crea en https://app.anyformat.ai/api-key. Solo se lee en el servidor.
- `ANYFORMAT_WORKFLOW_ID`: opcional, el workflow que sale seleccionado por defecto.

Comprobaciones: `bun run typecheck` y `bun run build`.

## Cómo funciona

1. `page.tsx` (servidor) lista los workflows de tu cuenta y pinta `DocumentApp`.
2. Al soltar PDFs, el navegador manda **cada fichero** a `POST /api/run` (multipart: `file`, `workflowId`).
3. La ruta llama a `runDocument()`: sube el fichero, lanza el run y espera el resultado (hasta ~5 min).
4. El JSON crudo del run se **normaliza** a `DocumentResult` (`src/lib/types.ts`) y la UI lo pinta.
5. El deslizador de umbral (85 por defecto) marca «a revisar» los campos con menos confianza.

## Mapa de ficheros

```
src/
├── lib/
│   ├── anyformat.ts      ← el ÚNICO fichero que usa @anyformat/sdk (listWorkflows, runDocument, normalize)
│   ├── types.ts          ← el resultado normalizado: Field, FieldValue, Validation, DocumentResult, Job
│   └── review.ts         ← la regla de «a revisar» (confianza < umbral)
├── app/
│   ├── page.tsx          ← carga los workflows (servidor)
│   ├── api/run/route.ts  ← POST /api/run: un PDF → DocumentResult
│   ├── layout.tsx        ← fuentes (Instrument Sans, Geist Mono)
│   └── globals.css       ← tokens de Shift (el sistema de diseño de anyformat) + primitivas
└── components/
    ├── DocumentApp.tsx   ← estado de la página: workflow, umbral, documentos
    ├── WorkflowPicker.tsx
    ├── Uploader.tsx      ← arrastrar y soltar / elegir PDFs
    ├── ResultCard.tsx    ← un documento: tipo, recuento a revisar, validaciones, enlace a anyformat
    ├── FieldsTable.tsx   ← campos simples y campos objeto (sub-tablas)
    └── ConfidenceBadge.tsx
```

## El dato que devuelve anyformat (v3)

- `results.extractions[].fields`: cada campo es `{ value, confidence, evidence[{text, page_number}], value_override }`.
  `value` siempre es string o null. Si `value_override` existe, es la corrección de un revisor y manda.
- Un campo objeto (líneas de factura, por ejemplo) llega como **lista de filas**, cada fila un mapa de campos.
- `results.extractions[].validations[]`: `{ rule_id, status: pass | fail | inconclusive, severity, detail }`.
- `results.classifications[]`: el tipo de documento, si el workflow tiene un nodo classify.
- `results.verification_url`: abre el documento en el espacio de revisión de anyformat.

## Prompts para Claude Code

Abre `claude` en esta carpeta y prueba:

1. «Añade una vista "Por albarán": agrupa las líneas de todas las facturas procesadas por su albarán, con el
   subtotal de cada uno, y marca en rojo los albaranes que aparezcan en dos facturas distintas (posible doble
   facturación).»
2. «Añade un botón "Exportar CSV" en cada documento que descargue los campos (campo, valor, confianza) y las
   filas de los campos objeto.»
3. «Guarda el histórico de documentos procesados en SQLite (bun:sqlite) y añade una página /historico que los
   liste con su número de campos a revisar.»
4. «Añade en cada campo un botón para aceptarlo o corregir su valor a mano; muestra los corregidos con la
   etiqueta "corregido" y excluye los aceptados del recuento a revisar.»
