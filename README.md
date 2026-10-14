# anyformat × IBM Consulting: formación inicial

![Página → bloque → celda → campo: un parte escaneado se divide en bloques de maquetación, la extracción lee el número de póliza de la celda r13c1 y lo devuelve con confianza 89 y su posición en la página](docs/grounding.gif)

Formación práctica para el equipo IAM del Ayuntamiento de Madrid (IBM Consulting / Viewnext).
14 de octubre de 2026, 15:00–17:00, Patio Madrid + Google Meet.

En dos horas vamos a:
1. Crear un workflow en anyformat: **parse → classify → extract → validate → mensajes**.
2. Medirlo contra **ground truth** y mejorarlo con **Annie**, el asistente de la app.
3. Montar una **aplicación propia en minutos** con el SDK, Next.js/TypeScript y Claude Code.

Trabajamos con dos casos:
- **Calas y canalizaciones**: las PDFs reales de un expediente y el workflow que ya montó Luis Miguel.
- **Facturas y albaranes**: el cruce factura ↔ albarán, un caso clásico de "lectura + comprobación".

## Agenda

| Hora | Bloque | Guía |
|---|---|---|
| 15:00 | Qué es anyformat y cómo se montó Salta Madrid | — |
| 15:15 | Crear un workflow en Studio | [`docs/01-workflow.md`](docs/01-workflow.md) |
| 15:50 | Ground truth y Annie: medir y mejorar calas y canalizaciones | [`docs/02-ground-truth-annie.md`](docs/02-ground-truth-annie.md) |
| 16:20 | Descanso | |
| 16:30 | Una app ad-hoc con el SDK y Claude Code | [`docs/03-app.md`](docs/03-app.md) |
| 16:55 | Cierre y siguientes pasos | |

## Los workflows en anyformat

Están en la cuenta de la formación; los enlaces abren si tu usuario tiene acceso a ella.

| Workflow | Para qué | Bloque |
|---|---|---|
| [Formación IBM · Factura y albarán](https://app.anyformat.ai/workflows/06acf4a9-7264-763f-8000-c49a3c779210) | El sencillo: aprender parse, classify, extract y validate en Studio | 1 |
| [demo_facturas](https://app.anyformat.ai/workflows/06acf527-787f-7de5-8000-4c0a5f3a366f) | La versión de producción para facturas de proveedor; la usa la app | 1 y 3 |
| [Calas y canalizaciones](https://app.anyformat.ai/workflows/06a2bbef-6dfd-7c28-8000-52a06458ebc0) | El original de IBM (junio), sin tocar | 2 |
| [Formación IBM · Calas y canalizaciones (punto de partida)](https://app.anyformat.ai/workflows/06acf4a9-7b63-71c3-8000-09e272982895) | Copia del original para practicar con Annie | 2 |
| [Formación IBM · Calas y canalizaciones (v2)](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a) | La revisión: de 70 % a 97 % ([`docs/calas-v2.md`](docs/calas-v2.md)) | 2 |
| [Formación IBM · Facturas sencillas (para el optimizer)](https://app.anyformat.ai/workflows/06acf584-e287-77d1-8000-bd46d425a3b0) | Health y optimizer: 8 facturas ficticias en el dataset, evaluación de partida 83,5 % | 2 |

## Antes de empezar (10 minutos, mejor antes de la sesión)

1. **Una cuenta y una API key** en https://app.anyformat.ai (menú → API key).
2. **Node 22 y bun**:
   ```bash
   nvm install 22 && nvm use 22
   curl -fsSL https://bun.sh/install | bash
   ```
3. **Claude Code** (opcional, para el último bloque): https://claude.com/claude-code
4. **Clonar y arrancar la app**:
   ```bash
   git clone <este repo> && cd anyformat-ibm-formacion/app
   cp .env.example .env.local        # pega tu ANYFORMAT_API_KEY
   bun install && bun dev            # http://localhost:3000
   ```
5. **Skill y MCP de anyformat para Claude Code**:
   ```bash
   export ANYFORMAT_API_KEY=af_...   # .mcp.json ya apunta al servidor MCP de anyformat
   npx @anyformat/skill --project    # referencia de la API para el agente
   claude                            # desde la raíz del repo
   ```

Si la app abre, lista tus workflows y procesa un PDF de `samples/`, estás listo.

## Qué hay en el repo

| Ruta | Qué es |
|---|---|
| `app/` | La app de partida: Next 15 + TypeScript + Shift (el sistema de diseño de anyformat) + `@anyformat/sdk` |
| `samples/calas/` | PDFs de expedientes de calas y canalizaciones (memoria, planos, presupuesto, residuos…) |
| `samples/facturas/` | Facturas reales de proveedores, anonimizadas (1–91 páginas), y en `sencillas/` 8 ficticias para el dataset |
| `ground_truth/calas/` | La respuesta correcta de cada PDF de calas, campo a campo |
| `referencia/calas-luismi/` | El workflow de calas tal como está hoy en la cuenta de IBM, más una ejecución de ejemplo |
| `docs/` | Una guía por bloque, el informe de partida de calas (`calas-baseline.md`) y su revisión (`calas-v2.md`: de 70 % a 97 %) |
| `workflows/` | Los workflows en formato de la API: factura y albarán (para Studio), `demo_facturas` (producción, se importa desde la app), calas de partida y calas v2 |
| `tools/run_calas.py` · `tools/score_calas.py` | Ejecutan los PDFs de calas en un workflow y los puntúan contra el ground truth |
| `tools/build_calas_v2.py` | Genera `workflows/calas-v2.json` |
| `tools/make_facturas.py` · `tools/dataset_facturas.py` | Generan las facturas ficticias y las suben, con su ground truth, al dataset de un workflow |

`media/` no se sube al repo (está en `.gitignore`): ahí va el vídeo de la demo de Salta Madrid para
proyectarlo en local.

## Cómo funciona anyformat, en una tabla

| Nivel | Qué es | Dónde está en el resultado |
|---|---|---|
| Página | El documento tal como llega | `results.parse` |
| Bloque | Una región con caja, tipo y confianza | `results.parse.blocks[]` |
| Campo | El dato pedido, con confianza 0–100 y la evidencia de dónde se leyó | `results.extractions[].fields` |
| Validación | Una regla determinista: pasa, falla o no concluye | `results.extractions[].validations[]` |

- Cada `value` llega como texto o `null`: el tipo lo pones tú.
- Si un revisor corrige un valor en la app, llega en `value_override`. Ese manda.
- `verification_url` abre el documento en la vista de revisión, con cada campo resaltado sobre la página.

## Enlaces

- Documentación: https://docs.anyformat.ai
- SDK: `bun add @anyformat/sdk` (TypeScript) · `pip install anyformat` (Python)
- Servidor MCP: `https://api.anyformat.ai/mcp`
