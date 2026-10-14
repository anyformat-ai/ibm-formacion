# Bloque 2 · Ground truth y Annie: medir y mejorar (15:50–16:20)

Un workflow que "parece que funciona" no está terminado hasta que se mide. Vamos a medir el workflow
de **calas y canalizaciones** que ya existe, ver dónde falla y arreglarlo con **Annie**, el asistente
de la app.

## El punto de partida

[`workflows/calas-punto-de-partida.json`](../workflows/calas-punto-de-partida.json) es el workflow de
calas tal como está hoy:

- **Parse** standard.
- **Classify** en cuatro tipos: Memoria, Plano, Presupuestos, Residuos/Acopio.
- **Un solo extract** de 22 campos para los cuatro tipos.
- **Sin validaciones.**

Si no lo tienes en tu cuenta, créalo:

```bash
curl -X POST https://api.anyformat.ai/v3/workflows/ \
  -H "Authorization: Bearer $ANYFORMAT_API_KEY" -H "Content-Type: application/json" \
  -d @workflows/calas-punto-de-partida.json
```

## 1. Ground truth: la respuesta correcta (5 min)

`ground_truth/calas/` tiene, para cada PDF de `samples/calas/`, el valor correcto de cada campo, o `null`
si el documento no lo trae. Ábrelo junto al PDF: por ejemplo `MEMORIA Calle SAN MATEO, 17.json`.

- Cada fichero tiene `notas`, que dicen dónde está cada dato en la página.
- `any_of` marca los campos con más de una respuesta aceptable.
- `revisar` marca los campos dudosos. En un proyecto real, ese repaso lo hace quien conoce el trámite.

Para documentos propios, el ground truth se prepara igual: un agente lo propone y una persona lo
revisa. En la app, cada documento revisado y verificado se puede añadir al **dataset** del workflow
(**Health → Datasets**).

## 2. Medir (10 min)

Ya hemos ejecutado el workflow sobre 11 de los 13 PDFs. El informe completo está en
[`calas-baseline.md`](calas-baseline.md):

```bash
python3 tools/score_calas.py results/calas/baseline        # precisión por documento y por campo
python3 tools/score_calas.py results/calas/baseline --md   # en tablas
```

**Resultado: 70 % de aciertos (196 de 282 campos).** Pero lo importante es dónde están los fallos:

| | Aciertos |
|---|---|
| El documento **trae** el dato | **90 %** (104/116) |
| El documento **no trae** el dato | **55 %** (92/166) |

Además, **68 de los 86 errores tienen confianza ≥ 90.** Tres patrones:

1. **Ceros donde debería haber null.** Un plano no tiene presupuesto, y el workflow devuelve
   `total_presupuesto = 0.0` con confianza 100. Pasa en 43 casos.
2. **Fechas inventadas.** Ninguno de los 13 PDFs trae fecha prevista de inicio o fin, y las 22 que
   devuelve están mal. En Pastrana puso el día en que se lanzó la ejecución. En San Mateo calculó
   "fecha de firma + 30 días de plazo".
3. **Planos mal leídos.** Una cota de 1.160 mm de un detalle constructivo se convierte en 11,6 m de
   profundidad. La empresa que dibujó el plano sale como subcontratista. El agua para amasar mortero
   aparece como "tipo de suministro: Agua".

¿Por qué? **Un solo esquema para cuatro documentos distintos.** Si a un plano le pides el presupuesto,
el modelo tiende a rellenar algo. Y las descripciones no dicen cuándo devolver null.

## 3. Mejorar con Annie (12 min)

Abre el workflow en la app y abre **Annie**. Pega estos prompts, de uno en uno. Después de cada uno,
mira en **Studio** qué ha cambiado.

1. > En el extract de este workflow, actualiza la descripción de todos los campos para que digan: "Si el documento no indica este dato de forma explícita, devuelve null. Nunca devuelvas 0, false ni una fecha por defecto."
2. > Divide el extract en cuatro, uno por cada rama del clasificador. Memoria: descripción, plazo de ejecución, ubicación, dirección, ID obra, motivo, contratista, medidas de acera y calzada, y profundidad. Presupuestos: total presupuesto, ID obra y ubicación. Plano: tipo de suministro, potencia, profundidad, medidas, ID obra y dirección. Residuos/Acopio: gestión de residuos, gestores autorizados y ubicación. Elimina los campos duplicados "Presupuesto" y "Duración (días)".
3. > Cambia las descripciones de "Fecha inicio prevista" y "Fecha fin prevista": solo deben extraerse si el documento indica literalmente la fecha prevista de inicio o de fin de la obra. La fecha de firma, del plano o del documento no cuenta, y no hay que calcularlas a partir del plazo. Añade validaciones: fecha fin >= fecha inicio.
4. > En "Medidas Acera", "Medidas Calzada" y "Profundidad (m)", aclara que van en metros y que las cotas de secciones tipo o detalles constructivos (en mm) no son medidas de la cala. Añade validaciones: profundidad entre 0,3 y 2 m, total presupuesto > 0, plazo de ejecución > 0.
5. > Añade al clasificador una categoría "Otro" para documentos que no sean memoria, plano, presupuesto ni gestión de residuos de una obra de cala o canalización, y que no pase a ningún extract.

El último prompt tiene un caso de prueba: `Datos Subcontratistas.pdf` es la captura de una
subcontrata de ascensores de Málaga y no tiene nada que ver con calas. Hoy el clasificador la mete
a la fuerza en uno de los cuatro tipos.

Cada cambio crea una **nueva versión** del workflow, y cada resultado guarda con qué versión se hizo.

**Otra vía, el optimizer:** con el dataset cargado, **Health → Optimizer** reescribe las
descripciones de forma automática y se queda con la versión que más acierta. Annie es para cambios de
estructura (dividir el esquema, añadir reglas). El optimizer, para afinar descripciones.

## 4. Volver a medir (3 min)

Ejecuta la versión nueva sobre los PDFs y vuelve a puntuar:

```bash
# guarda cada run (GET /v3/runs/{id}/) como results/calas/v2/<nombre del PDF sin .pdf>.json
python3 tools/score_calas.py results/calas/v2
```

El script funciona aunque el extract se haya dividido en cuatro. Fíjate sobre todo en la fila
"el documento no trae el dato": ahí es donde debe subir.

## Qué llevarse

- **Hay que medir antes de mejorar.** Sin ground truth, "funciona bien" es una impresión.
- **Una confianza alta no garantiza que el valor esté bien.** Las validaciones deterministas (fechas
  coherentes, importes positivos, rangos) cazan lo que la confianza no ve.
- **Un esquema por tipo de documento.** Pedir solo lo que el documento puede tener es la mejora más
  barata.
