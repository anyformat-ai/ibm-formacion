# Bloque 1 · Crear un workflow (15:15–15:50)

Dos partes:

1. **Construir en Studio** un workflow sencillo, nodo a nodo, para aprender las piezas: parse, classify,
   extract, validate y mensajes (*Formación IBM · Factura y albarán*).
2. **Ver la versión de producción**, `demo_facturas`: la misma idea afinada para facturas de proveedor
   largas y difíciles. Con esta se ejecutan las facturas de verdad y es la que usa la app del bloque 3.

Los documentos son **facturas reales de proveedores de recambios, anonimizadas** (`samples/facturas/`), de
1 a 91 páginas. Cada factura agrupa sus líneas por albarán.

## Parte 1 · El workflow sencillo, en Studio

```
parse → classify ─┬─ factura → extract_factura → validate
                  └─ albarán → extract_albaran
```

La versión terminada está en [`workflows/factura-albaran.json`](../workflows/factura-albaran.json),
en el formato de la API. Si algo se tuerce, créalo de golpe y sigue desde ahí:

```bash
curl -X POST https://api.anyformat.ai/v3/workflows/ \
  -H "Authorization: Bearer $ANYFORMAT_API_KEY" -H "Content-Type: application/json" \
  -d @workflows/factura-albaran.json
```

Para probarlo, `134900_anon.pdf` (1 página) o `133285_anon.pdf` (2 páginas).

## 1. Parse: leer el documento

Nuevo workflow → nodo **Parse**.

- **Standard**: OCR, maquetación, tablas y casillas. Es el que usamos.
- **Fast (lite)**: solo OCR, más barato. Va bien para documentos limpios y muy repetidos.

El parse devuelve **bloques** (texto, tabla, figura), cada uno con su caja en la página. Todo lo que se
extraiga después apunta a uno de ellos: por eso cada dato se puede resaltar en el original.

## 2. Classify: qué documento es

Nodo **Classify** con dos categorías. La descripción es lo que decide:

| Categoría | Descripción |
|---|---|
| Factura | Factura de un proveedor: tiene número de factura, base imponible, IVA y total a pagar. |
| Albarán | Albarán o nota de entrega: lista la mercancía entregada con cantidades, normalmente sin importes ni impuestos. |

Cada categoría abre una **rama**. Cada rama lleva su propio extract.

## 3. Extract: los campos

Un extract por rama. Reglas que funcionan:

- **Unos 20 campos por extract como mucho.** Los esquemas largos extraen peor.
- **La descripción es donde se gana precisión.** Di dónde está el dato, en qué formato lo quieres y
  cuándo es null. "Número de factura tal como aparece impreso" es mejor que "Número".
- **Tipos**: `string`, `integer`, `float`, `date`, `boolean` y `object`. `object` es una lista de
  filas (las líneas de la factura), con un solo nivel de anidación.
- **Un esquema por tipo de documento.** Pedirle "potencia eléctrica" a un presupuesto solo genera
  nulls o, peor, valores inventados. Lo veremos en calas.

Campos de la factura: `numero_factura`, `fecha_factura`, `proveedor_nombre`, `proveedor_nif`,
`cliente_nombre`, `cliente_nif`, `albaranes_referenciados`, `lineas` (**albarán**, número de pedido,
referencia, descripción, cantidad, precio unitario, importe), `base_imponible`, `iva_importe`, `total`.

El campo `lineas.albaran` es el que permite cruzar después: "el último encabezado de albarán por encima
de esta línea". Así se le dice al modelo dónde mirar.

Campos del albarán: `numero_albaran`, `fecha_entrega`, `proveedor_nombre`, `proveedor_nif`,
`cliente_nombre`, `numero_pedido`, `lineas` (referencia, descripción, cantidad), `firmado`.

## 4. Validate: reglas que no dependen del modelo

Nodo **Validate** detrás del extract de la factura. Dos tipos de regla:

| Regla | Tipo | Comprobación |
|---|---|---|
| Base + IVA = total | Determinista (expresión) | `data.base_imponible + data.iva_importe - data.total <= 0.02 && data.total - (data.base_imponible + data.iva_importe) <= 0.02` |
| Las líneas suman la base | IA | "La suma del importe de todas las filas de `lineas` debe ser igual a `base_imponible`, con un margen de 0,02." |

Las reglas **no paran** la ejecución: la etiquetan como `pass`, `fail` o `inconclusive`. Con eso se
decide qué va a revisión humana y qué pasa directo.

## 5. Mensajes: avisar cuando algo falla

Nodo **If/else** con la condición "cualquiera de las dos reglas en `fail`" y, en la rama `true`, un
nodo de aviso (por ejemplo **Slack alert**, con el canal de vuestro espacio de trabajo). No va en el JSON
porque depende del Slack conectado a cada cuenta: se añade en Studio. Su plantilla puede usar campos y
validaciones:

```
:warning: La factura ${field.numero_factura} de ${field.proveedor_nombre} no cuadra
Base ${field.base_imponible} + IVA ${field.iva_importe} vs total ${field.total}
```

## 6. Ejecutar y revisar

Sube los PDFs de `samples/facturas/` desde la pestaña **Data** del workflow.

- **Data**: una fila por documento y una columna por campo.
- Abre un documento: cada campo tiene su confianza. Al pinchar en uno, se resalta en la página.
- **Validación**: cada regla con su resultado y los valores que comparó.
- **Corregir** un valor lo marca como editado por una persona, y la API lo devuelve en
  `value_override`. **Aceptarlo** lo marca como verificado. Un documento verificado se puede
  añadir al dataset: ese es el ground truth del siguiente bloque.

## Para pensar

El cruce **factura ↔ albarán** (¿se ha facturado lo que se entregó?) no es una regla de un documento:
compara dos. Eso lo haremos en la app del bloque 3, con los dos resultados en la mano.

## Parte 2 · La versión de producción: `demo_facturas`

Es el workflow que usamos con este tipo de facturas en un cliente real. Está en la cuenta como
**demo_facturas** y en [`workflows/facturas-proveedor.json`](../workflows/facturas-proveedor.json).

| Pieza | Qué cambia respecto al sencillo |
|---|---|
| **Parse** | Un *prompt hint* de 16.000 caracteres: cómo convertir cada bloque de la factura en tablas fieles |
| **Extract** | Modo **max**. La descripción del workflow fija el contexto (quién es el proveedor, abonos en negativo) |
| **Campos** | 7 de cabecera (`total`, `ibruto`, `portes`, `idto`, tasas `tnfu`, `tsigaus`, `tgases`) y `lineas` con 9 por línea (`albaran`, `fechaalb`, `npedido`, `referencia`, `descripcion`, `cantidad`, `precio`, `importe`, `dto1`) |
| **Validate** | Una regla determinista: líneas + portes + tasas − descuento = base imponible, con tolerancia |

La descripción de `lineas` es lo que más trabaja: qué filas son líneas y cuáles no («Suma y sigue»,
subtotales, cabeceras repetidas), cómo arrastrar el albarán y el pedido de una página a la siguiente, y
una comprobación (`cantidad × precio × descuentos = importe`) antes de responder. Leedla en Studio.

`max` no se puede crear por la API (solo acepta `standard`, `agentic` o `lite`): este workflow se importa
desde la app.

### Las facturas, una a una

| PDF | Páginas | Qué tiene | Resultado con `demo_facturas` |
|---|---|---|---|
| `134900_anon.pdf` | 1 | Fácil | 7 líneas, 5 albaranes, validación `pass` |
| `133285_anon.pdf` · `136909_anon.pdf` | 2 · 16 | Fáciles | — |
| `137181_anon.pdf` | 7 | **«Suma y sigue»** entre páginas: no son líneas | 71 líneas, 25 albaranes, todas con pedido; validación `pass` |
| `133004_anon.pdf` | 12 | La que suele fallar en otras soluciones: **al final de la página 8 queda un pedido sin artículos** y sus líneas empiezan en la 9 | 284 líneas, 6 albaranes; la primera línea de la página 9 hereda bien el pedido 156458; validación `pass` |
| `132783_anon.pdf` | 39 | **La validación no pasa**: se cuela una línea inventada | 186 líneas que suman 7.302,11 € frente a una base de 7.236,64 €: **65,47 € de más**. Validación `fail`: va a revisión |
| `141067_anon.pdf` · `143492_anon.pdf` | 90 | Para ver cómo escala | — |

**El mensaje de la 132783:** ninguna extracción acierta el 100 %; en estas facturas estamos en torno al
92–94 % de líneas perfectas. Lo importante es que la regla de cuadre **caza** ese 6 % y manda la factura a
revisión en vez de dejarla pasar.

## Lo que pasó al probarlo (134900_anon.pdf, 1 página)

La ejecutamos dos veces en el mismo workflow. Las dos veces: clasificada como **Factura** (confianza 100),
las 7 líneas con su albarán (5622, 4758, 2211, 1654, 7352) y las dos reglas en `pass` (las líneas suman
5.585,96 € y base + IVA = 6.759,01 €).

Pero en la primera, **proveedor y cliente salieron cruzados**:

| Campo | 1.ª ejecución | 2.ª ejecución | Confianza (1.ª) |
|---|---|---|---|
| `proveedor_nombre` | IBERCLEAN PARTS, S.L. ✗ | NORTE LIMPIEZA S.L.U. ✓ | 91 |
| `cliente_nombre` | null ✗ | IBERCLEAN PARTS, S.L. ✓ | — |
| `cliente_nif` | B11223344 ✗ | — | 88 |

La factura pone el logo del proveedor arriba, el bloque del cliente donde suele ir el emisor y el CIF del
proveedor solo en el pie. Es un documento ambiguo, y el modelo no es determinista: **la misma factura,
dos respuestas, la mala con confianza 91.** Las reglas de totales no lo detectan, porque los importes
están bien.

El ejercicio: blindarlo para que no dependa de la suerte.
- **Descripción**: "el proveedor es quien emite la factura: su logo, su registro mercantil y su CIF en el
  pie; el cliente es el destinatario, IBERCLEAN PARTS".
- **Regla**: `data.proveedor_nif != data.cliente_nif`, o "el cliente siempre es B99887766".
