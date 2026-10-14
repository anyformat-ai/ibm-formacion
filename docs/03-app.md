# Bloque 3 · Una app ad-hoc con el SDK y Claude Code (16:30–16:55)

Salta Madrid se montó en días porque anyformat ya resuelve lo difícil: leer el documento, situar cada
dato en la página, darle una confianza y validarlo. Lo que queda es **la app del cliente**: su
pantalla, sus reglas de negocio, su integración. Eso es lo que vamos a hacer ahora.

## 1. Arrancar la app (5 min)

```bash
cd app
nvm use && bun install
cp .env.example .env.local   # ANYFORMAT_API_KEY y, si quieres, ANYFORMAT_WORKFLOW_ID
bun dev                      # http://localhost:3000
```

Elige el workflow **demo_facturas** (o el de calas), suelta `samples/facturas/134900_anon.pdf` y espera
un minuto. Verás:

- El tipo de documento con su confianza.
- Cada campo con su valor, su confianza y la evidencia (el texto y la página de donde salió).
- Las líneas como subtabla, cada una con su albarán, su fecha y su pedido.
- Las validaciones, y el enlace **Revisar en anyformat**.
- El deslizador de umbral: por debajo, el campo se marca **a revisar**.

## 2. Cómo está hecha (5 min)

Unas 575 líneas en total. Lo importante:

| Fichero | Qué hace |
|---|---|
| `src/lib/anyformat.ts` | El **único** fichero que usa el SDK |
| `src/app/api/run/route.ts` | `POST /api/run`: un PDF entra, un resultado normalizado sale |
| `src/lib/types.ts` | La forma del resultado que pinta la UI |
| `src/app/globals.css` | Los tokens de **Shift**, el sistema de diseño de anyformat |

El SDK, entero:

```ts
import { Anyformat } from "@anyformat/sdk";

const af = new Anyformat({ apiKey: process.env.ANYFORMAT_API_KEY });

for await (const wf of af.iterWorkflows()) { /* wf.id, wf.name */ }

const upload = await af.upload(workflowId, file, { onConflict: "rename" });
const run = await upload.run();
const result = await run.wait({ timeoutMs: 280_000, pollMs: 3_000 });
result.raw.extractions[0].fields; // { value, confidence, evidence, value_override }
result.raw.verification_url;      // el documento en la vista de revisión de anyformat
```

`onConflict: "rename"` evita el error de "ya existe un fichero con ese nombre" al subir dos veces el
mismo PDF.

## 3. Extenderla con Claude Code (15 min)

Desde la raíz del repo (así coge `.mcp.json` y la skill):

```bash
export ANYFORMAT_API_KEY=af_...
npx @anyformat/skill --project    # una vez
claude
```

Haremos el primero juntos en directo. Los demás, por parejas:

1. **Vista por albarán.** «Añade una vista "Por albarán": agrupa las líneas de todas las facturas
   procesadas por su albarán (`lineas.albaran`), con su fecha (`fechaalb`), su pedido (`npedido`) y el
   subtotal de `importe`, y marca en rojo los albaranes que aparezcan en dos facturas distintas (posible
   doble facturación).» Probadlo con `134900`, `137181` y `133004` procesadas.
2. **Exportar.** «Añade un botón "Exportar CSV" en cada documento que descargue los campos y las filas
   de los campos objeto.»
3. **Histórico.** «Guarda los documentos procesados en SQLite (bun:sqlite) y añade una página
   /historico con su número de campos a revisar.»
4. **Revisión.** «Añade en cada campo un botón para aceptarlo o corregirlo a mano; los aceptados salen
   del recuento a revisar.»
5. **Calas.** «Con el workflow de calas, muestra una ficha por expediente que junte memoria, presupuesto,
   plano y residuos de la misma dirección, y avise si las fechas o el presupuesto no coinciden entre
   documentos.»

Con el MCP, Claude Code también puede **consultar y cambiar el workflow**: «lista mis workflows», «enséñame
el esquema del extract de factura», «añade una regla a Factura y albarán que falle si proveedor_nif = cliente_nif».

## Qué llevarse

- **anyformat es el motor de lectura; la app es vuestra.** Pantalla, reglas, integraciones (SAP, gestor
  documental, colas de revisión): con el SDK son horas, no semanas.
- **La confianza decide el flujo.** Por encima del umbral, directo al sistema. Por debajo, o con una
  validación en `fail`, a revisión humana. Y cada corrección es ground truth para mejorar el workflow.
