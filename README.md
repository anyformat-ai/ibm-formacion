# anyformat × IBM Consulting: formación inicial

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
| `samples/facturas/` | Facturas reales de proveedores, anonimizadas (1–91 páginas) |
| `ground_truth/calas/` | La respuesta correcta de cada PDF de calas, campo a campo |
| `referencia/calas-luismi/` | El workflow de calas tal como está hoy en la cuenta de IBM, más una ejecución de ejemplo |
| `docs/` | Una guía por bloque y el informe de partida de calas (`calas-baseline.md`) |
| `tools/score_calas.py` | Compara resultados con el ground truth y da la precisión por campo |

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
