# Bloque 1 · Crear un workflow (15:15–15:50)

Vamos a montar en Studio un workflow que recibe **facturas y albaranes** mezclados, los separa,
extrae los datos de cada uno, comprueba que la factura cuadra y avisa cuando no.

Los documentos son **facturas reales de proveedores de recambios, anonimizadas** (`samples/facturas/`).
Cada factura agrupa sus líneas por albarán, así que el extract lee también **a qué albarán pertenece
cada línea**. Van de 1 a 91 páginas. Para ir rápido en directo, usad estas:

| PDF | Páginas | Por qué |
|---|---|---|
| `134900_anon.pdf` | 1 | Un albarán, una línea: la más sencilla |
| `133285_anon.pdf` | 2 | Formato distinto, con destino de mercancía y de factura |
| `137181_anon.pdf` | 7 | Muchos albaranes en una factura |
| `133004_anon.pdf` | 12 | Proveedor italiano, factura bilingüe |

Las de 39–91 páginas son para ver cómo escala, no para esperar en directo.

```
parse → classify ─┬─ factura → extract_factura → validate → ¿falla? → aviso (Slack)
                  └─ albarán → extract_albaran
```

La versión terminada está en [`workflows/factura-albaran.json`](../workflows/factura-albaran.json),
en el formato de la API. Si algo se tuerce, créalo de golpe y sigue desde ahí:

```bash
curl -X POST https://api.anyformat.ai/v3/workflows/ \
  -H "Authorization: Bearer $ANYFORMAT_API_KEY" -H "Content-Type: application/json" \
  -d @workflows/factura-albaran.json
```

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
nodo **Slack alert**. Su plantilla puede usar campos y validaciones:

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

## Lo que pasó al probarlo (134900_anon.pdf, 1 página)

Clasificada como **Factura** con confianza 100. Las dos reglas pasan: las 7 líneas suman la base
(5.585,96 €) y base + IVA = total (6.759,01 €). Cada línea sale con su albarán (5622, 4758, 2211,
1654, 7352).

Pero:

| Campo | Salió | Correcto | Confianza |
|---|---|---|---|
| `proveedor_nombre` | IBERCLEAN PARTS, S.L. | NORLIM Distribuciones | 91 |
| `proveedor_nif` | B99887766 | B11223344 (el del pie) | 91 |
| `cliente_nombre` | null | IBERCLEAN PARTS, S.L. | — |
| `cliente_nif` | B11223344 | B99887766 | 88 |

**Proveedor y cliente se han cruzado, con confianza alta.** La factura pone el logo del proveedor
arriba, el bloque del cliente en la zona donde suele ir el emisor, y el CIF del proveedor solo en el
pie. Las reglas de totales no lo detectan, porque los importes están bien.

Ese es el ejercicio: arreglarlo con la descripción ("el proveedor es quien emite la factura: su logo,
su registro mercantil y su CIF en el pie; el cliente es el destinatario, IBERCLEAN PARTS") o con una
regla (`proveedor_nif != cliente_nif`, o "el cliente siempre es B99887766"). Después, volver a ejecutar.
