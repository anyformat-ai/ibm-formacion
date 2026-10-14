# Calas y canalizaciones: revisión del workflow (v2)

Revisión del workflow de calas que montó IBM en junio. Mismos PDFs, mismo motor y mismo ground truth;
lo que cambia es la configuración. El de partida está medido en [`calas-baseline.md`](calas-baseline.md).

- **Workflow v2** (cuenta de IBM): https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a
- **Definición**: [`workflows/calas-v2.json`](../workflows/calas-v2.json), generada por `tools/build_calas_v2.py`
- **Ejecuciones**: `results/calas/v2/`. Para reproducirlas: `python3 tools/run_calas.py <workflow_id> results/calas/v2`

## Resultado

Sobre los mismos 11 PDFs que tienen ejecución de partida:

| | Partida | v2 |
|---|---|---|
| **Total** | 196/282 = **70 %** | 273/282 = **97 %** |
| Campos que el documento **trae** | 104/116 = 90 % | 111/116 = 96 % |
| Campos que el documento **no trae** y se piden | 92/166 = 55 % | 81/85 = 95 % |
| Campos que ese tipo de documento ya no pide | — | 81/81 |
| **Errores con confianza ≥ 90** | **68** | **8** |

Con los 13 PDFs (se suman L4.032.12 y Datos Subcontratistas): 321/331 = 97 %. Datos Subcontratistas sale
como **Otro** y no pasa por ningún extract.

**Cómo leerlo, sin trampas:**
- Los 81 campos "que ese tipo ya no pide" cuentan como acierto porque el workflow no devuelve nada donde
  no hay nada. Sin contarlos, la v2 sigue en 192/201 = 96 %.
- Las descripciones nuevas se escribieron mirando los errores de estos mismos PDFs. Para dar un número
  definitivo hay que medir con expedientes que no se hayan usado para ajustar.
- Hay una sola ejecución por PDF, y el modelo no es determinista: la misma factura ha salido distinta en
  dos ejecuciones. Con más documentos, el número se moverá unos puntos.
- El ground truth lo preparó un agente y está pendiente de revisar con quien conoce el trámite (lista
  `revisar` de cada fichero).

## Qué se ha cambiado

| Cambio | Ataca |
|---|---|
| **Un extract por tipo de documento**, con los campos que ese tipo puede traer (memoria 22, plano 13, presupuesto 13, residuos 10) | Campos rellenados en documentos que no los tienen |
| **Cada descripción dice cuándo devolver null**: "nunca 0, false ni un valor por defecto" | Los 43 ceros y falses inventados |
| **Fechas previstas solo si están escritas**: ni la de firma ni calculadas con el plazo | Las 22 fechas inventadas |
| **Medidas y profundidad en metros**: las cotas de detalle no son tramos; "más de 2 m es casi seguro una cota mal leída" | 11,6 m de profundidad, tramos sacados de secciones tipo |
| **Tipo de suministro**: "el agua que se usa durante la obra no es el suministro" | "Agua" en el plan de acopios |
| **Subcontratista**: quien ejecuta, no el promotor, la distribuidora ni quien dibuja el plano | La empresa del plano como subcontratista |
| **Categoría Otro** en el clasificador, sin extract | Documentos que no son de calas |
| **Validaciones por rama**: fecha fin ≥ inicio, profundidad entre 0,2 y 3 m, presupuesto > 0, plazo > 0 | Avisar de lo que se cuele |

Los nombres de campo son los mismos que en el de partida, así que las integraciones que ya los lean no
cambian.

## Lo que todavía falla (10 campos)

| Documento | Campo | Salió | Correcto |
|---|---|---|---|
| PLANOS | id_obra | 45867 | 8570820 |
| PLANOS | ubicacion, tipo de suministro, motivo | MADRID, telecomunicaciones, nueva canalización | null (no lo pone el plano) |
| 8570820 (47 págs.) | id_proyecto_contratista | M.AZ: 45867 | null o 8570820 |
| 8570820 (47 págs.) | medidas_acera | tramos repetidos | 6,2 + 2,4 m o 8,6 m |
| Plano de permiso SP250600117588 | medidas_acera | pavimento "aglomerado asfáltico" | losetas especiales |
| Plano de permiso SP250600117588 | otras_unidades | Tierra | null |
| Plano San Mateo 17 | descripción | texto del cajetín del plano | texto de la solicitud |
| L4.032.12 | dirección.nombre | del Mar Bering | del Mar de Bering |

Varios de estos son discutibles más que errores: en PLANOS, "telecomunicaciones" es correcto aunque el
plano no lo diga literalmente. Conviene revisarlos con Luis Miguel al cerrar el ground truth.

## Ver cada documento en la app

| Documento | Revisión |
|---|---|
| MEMORIA Calle SAN MATEO, 17 | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4ad-a2f4-7c22-8000-e1eb603a30cd?versionId=pm8d3Iz-lw) |
| PRESUPUESTO Calle SAN MATEO, 17 | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4ad-f2bc-7850-8000-6080e0dd4e3d?versionId=pm8d3Iz-lw) |
| 9045838454 Calle SAN MATEO, 17 (plano) | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-ea19-75ac-8000-cc769db9a6c7?versionId=pm8d3Iz-lw) |
| GESTIÓN DE RESIDUOS Y DE ACOPIOS | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-e121-76ed-8000-7b3c67514aa0?versionId=pm8d3Iz-lw) |
| MA_Memoria y plazo de ejecución (Pastrana) | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-e2aa-7229-8000-286de2724ffb?versionId=pm8d3Iz-lw) |
| MA_Presupuesto Licencia | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4ac-a0e3-7553-8000-b6eb29c2b011?versionId=pm8d3Iz-lw) |
| Plano de permiso SP250600117588 | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-def6-74ee-8000-3bae928fe505?versionId=pm8d3Iz-lw) |
| Plan acopios y residuos | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4ae-5034-78bc-8000-004a0a29405f?versionId=pm8d3Iz-lw) |
| 8570820_4119522 (47 págs.) | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-ea36-7499-8000-7c4590f041c1?versionId=pm8d3Iz-lw) |
| GESTION RESIDUOS | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-e0b4-783d-8000-9f4be06fb4f1?versionId=pm8d3Iz-lw) |
| PLANOS | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4ad-a622-79b4-8000-75a6a76db859?versionId=pm8d3Iz-lw) |
| L4.032.12 | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-df60-7191-8000-c7c99dfe106c?versionId=pm8d3Iz-lw) |
| Datos Subcontratistas (sale como Otro) | [abrir](https://app.anyformat.ai/workflows/06acf4a9-8548-7384-8000-f0b4ea0c800a/files/06acf4aa-de6d-7163-8000-ead138b86433?versionId=pm8d3Iz-lw) |
