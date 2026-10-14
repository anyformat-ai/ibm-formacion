# Calas y canalizaciones — baseline del workflow actual

Workflow evaluado: **"Calas y canalizaciones"** (junio, id `06a2bbef-6dfd-7c28-8000-52a06458ebc0`):
parse standard → classify (Memoria / Plano / Presupuestos / Residuos-Acopio) → **un único extract de 22 campos** para todos los tipos, sin validaciones.
Ground truth: `ground_truth/calas/*.json` (revisado a mano; los campos dudosos están en `"revisar"`).
Runs: los ya existentes en la org del cliente (06–07/07/2026). **No se ha lanzado ningún run nuevo.**

## Resumen

| | |
|---|---|
| Documentos puntuados | 11 de 13 (2 sin run: `L4.032.12.pdf`, `Datos Subcontratistas.pdf`) |
| Aciertos totales | **196 / 282 = 70 %** |
| …cuando el documento **sí** trae el dato | **104 / 116 = 90 %** |
| …cuando el documento **no** trae el dato (debería ser null) | **92 / 166 = 55 %** |
| Errores con confianza ≥ 90 | **68** de 86 errores |

**Mensaje principal:** el modelo lee bien lo que está en el documento (90 %). Casi todos los errores (74 de 86) son **campos que no aplican a ese tipo de documento y que el workflow rellena con algo inventado**: `0`, `0.0`, `False`, `1970-01-01`, la fecha del plano o la del propio run, y casi siempre con confianza 99. La causa es de diseño: un único esquema de 22 campos para cuatro tipos de documento distintos, sin decir qué hacer cuando el dato no está.

## Errores con alta confianza (los mejores ejemplos para la formación)

| Documento | Campo | Ground truth | Workflow | Conf. | Qué pasó |
|---|---|---|---|---|---|
| MA_Memoria (Pastrana 8B) | fecha_inicio / fecha_fin | null | **2026-07-07 / 2026-07-07** | 92 / 93 | Es el día en que se lanzó el run. Inicio = fin, aunque el plazo es de 9 días |
| MA_Memoria (Pastrana 8B) | total_presupuesto | null | **0.0** | 99 | La memoria no lleva presupuesto: devuelve 0 € en vez de "no consta" |
| MEMORIA San Mateo 17 | fecha_inicio / fecha_fin | null | 2025-11-14 / 2025-12-14 | 99 / 99 | Toma la fecha de firma y le **suma** los 30 días de plazo: es un cálculo, no una extracción |
| 9045838454 San Mateo (plano) | profundidad_m | null (sección: 960/1160 mm) | **11.6** | 92 | Error de unidades: 1160 mm leído como 11,6 m |
| 9045838454 San Mateo (plano) | medidas_acera / calzada | [] | 9.6 × 4.2 m / 11.6 × 5.8 m | 99 | Cotas en mm de la **sección tipo** convertidas en largo y ancho de la cala |
| PLANOS (Telefónica) | medidas_acera / calzada | 6,20 m + 2,40 m en acera | 0.45 / 0.60 | 89 / 97 | Pone profundidades como largos; no lee las cotas 6,20 y 2,40 del plano 02 |
| PLANOS (Telefónica) | subcontratista | null | SMART TELECOM CONSULTING 2004 SL | 99 | Es quien **dibuja** el plano, no quien ejecuta la obra |
| Plan acopios y residuos (Pastrana) | tipo_de_suministro | null (es gas) | **Agua** | 99 | Lo saca de "se utilizará agua… para la preparación del cemento" |
| GESTIÓN DE RESIDUOS Y DE ACOPIOS (i-DE) | direccion | null | Av. San Adrián 48, Bilbao | 99 | Es el domicilio social de i-DE (pie de página), no la obra |
| MA_Presupuesto (Pastrana) | id_obra | ACT250600117588 | "PASTRANA 8 (DESPLAZAMIENTO RED)" | 99 | Pone la denominación de la obra como ID |
| MADRID_…PLANO_DE_PERMISO | medidas_acera.tipo_pavimento | Losetas especiales | Aglomerado asfáltico | 99 | Coge la primera fila de la tabla de pavimentos, que está vacía |
| 8570820 (47 págs.) | fecha_inicio / fecha_fin | null | **0325-12-03 / 0425-12-03** | 71 / 0 | Fechas absurdas. En el otro run del mismo PDF salió 2025-12-03 / 2025-12-13: **no es determinista** |

## Patrones de error y arreglo propuesto

1. **Sin "no consta": devuelve 0 / False / 1970-01-01 en vez de null** (43 errores de `0` / `0.0` / `False` en plazo, duración, presupuesto, profundidad y gestores autorizados; además, las 22 fechas del punto 2).
   *Arreglo:* añadir a cada descripción "Si el documento no lo indica explícitamente, devolver null. Nunca 0, false ni una fecha por defecto". Regla de validación: `total_presupuesto > 0` y `plazo_de_ejecucion > 0` cuando no son null.
2. **Fechas inventadas** (0/11 aciertos). Ninguno de los 13 documentos trae fecha prevista de inicio o fin; el modelo usa la fecha de firma, la del plano, la del run, o la calcula sumando el plazo.
   *Arreglo:* descripción: "Solo si aparece literalmente como fecha prevista de inicio/fin de obra. La fecha de firma, del plano o del documento NO lo es. No calcular." Validaciones: `fecha_fin_prevista >= fecha_inicio_prevista`, `(fin - inicio) ≈ plazo_de_ejecucion`, año entre 2024 y 2030.
3. **Un esquema para cuatro tipos de documento.** Un plano no tiene presupuesto ni gestión de residuos, y un presupuesto no tiene plazo, pero se piden los 22 campos a todos.
   *Arreglo:* un extract por rama del clasificador, cada uno con solo sus campos: Memoria (descripción, plazo, ubicación, dirección, IDs, motivo, contratista, medidas, profundidad), Presupuestos (total, ID, ubicación), Plano (tipo de suministro, potencia, profundidad, medidas, ID, dirección) y Residuos (gestión, gestores autorizados, ubicación).
4. **Planos: unidades y cotas.** Mezcla las cotas de la sección tipo (mm) con las longitudes de la cala (m) y confunde profundidad con largo.
   *Arreglo:* "Medidas en metros. Las secciones tipo y los detalles constructivos van en mm y no son medidas de la cala. Largo = longitud de la zanja o canalización (p. ej. '6,20 metros en acera'). Si no está acotada, lista vacía." Validaciones: `profundidad_m` entre 0.3 y 2, `largo` entre 0.5 y 500.
5. **Campos duplicados o ambiguos**: `presupuesto` = `total_presupuesto` y `duracion_dias` = `plazo_de_ejecucion`. `id_obra` e `id_proyecto_contratista` se mezclan (el mismo código va a parar a uno o a otro según el run). El "subcontratista" se confunde con quien dibuja el plano y en la memoria aparece como "CONTRATISTA".
   *Arreglo:* eliminar los duplicados y definir cada ID por su etiqueta en el documento (nº de expediente, Ref., Código Obra, Proyecto Nº). Subcontratista: "empresa que ejecuta la obra ('CONTRATISTA:'); NO el redactor, el dibujante ni el promotor".
6. **Clasificador sin categoría "Otro"**: `Datos Subcontratistas.pdf` (una captura de una subcontrata de ascensores en Málaga) caería por fuerza en una de las 4 categorías.
   *Arreglo:* añadir la categoría "Otro / no relacionado" sin extract.

## Prompts para Annie (copiar y pegar en el asistente de la app)

1. > En el extract de este workflow, actualiza la descripción de todos los campos para que digan: "Si el documento no indica este dato de forma explícita, devuelve null. Nunca devuelvas 0, false ni una fecha por defecto como 1970-01-01."
2. > Cambia las descripciones de "Fecha inicio prevista" y "Fecha fin prevista": solo deben extraerse si el documento indica literalmente la fecha prevista de inicio o de fin de la obra. La fecha de firma, del plano o del documento no cuenta, y no hay que calcularlas a partir del plazo. Añade validaciones: fecha fin >= fecha inicio, y la diferencia en días debe coincidir con "Plazo de ejecución".
3. > Divide el extract en cuatro, uno por cada rama del clasificador. Memoria: descripción, plazo de ejecución, ubicación, dirección, ID obra, motivo, contratista, medidas de acera y calzada, y profundidad. Presupuestos: total presupuesto, ID obra y ubicación. Plano: tipo de suministro, potencia, profundidad, medidas, ID obra y dirección. Residuos/Acopio: gestión de residuos, gestores autorizados y ubicación. Elimina los campos duplicados "Presupuesto" y "Duración (días)".
4. > En "Medidas Acera", "Medidas Calzada" y "Profundidad (m)", aclara que los valores van en metros y que las cotas de secciones tipo o detalles constructivos (en mm) no son medidas de la cala. El largo es la longitud de la zanja o canalización; si no está acotado, la lista va vacía. Añade validaciones: profundidad entre 0,3 y 2 m, total presupuesto > 0 y plazo de ejecución > 0.
5. > Añade al clasificador una categoría "Otro" para documentos que no sean memoria, plano, presupuesto ni gestión de residuos de una obra de cala o canalización, y que no pase a ningún extract. En el campo "Subcontratista", indica que es la empresa que ejecuta la obra (suele aparecer como "CONTRATISTA:"), no la que redacta o dibuja el proyecto ni el promotor.

## Cómo re-puntuar después de mejorar el workflow

```bash
# 1) guardar cada run como results/calas/<grupo>/<nombre del PDF sin .pdf>.json  (respuesta de GET /v3/runs/{id}/)
# 2) puntuar
python3 tools/score_calas.py results/calas/<grupo>          # resumen en terminal
python3 tools/score_calas.py results/calas/<grupo> --md     # tablas como las de abajo
```
Sirve aunque el workflow tenga varios extract (fusiona los campos). Un campo que deja de existir (p. ej. `presupuesto` tras eliminar duplicados) cuenta como null: acierta si el GT es null.

## Correspondencia de runs y ficheros (baseline)

| PDF | Run usado | Notas |
|---|---|---|
| MEMORIA Calle SAN MATEO, 17.pdf | `06a4bba1-66d3-73a9-8000-5ddb24a7318c` | |
| PRESUPUESTO Calle SAN MATEO, 17.pdf | `06a4bba1-66d3-709a-8000-3db0012a23e7` | |
| 9045838454 Calle SAN MATEO, 17.pdf | `06a4bba1-66d2-7a5a-8000-c5585259c95e` | |
| GESTIÓN DE RESIDUOS Y DE ACOPIOS.pdf | `06a4bba1-66d2-7dab-8000-d8e3a07611e7` | |
| MA_Memoria y plazo de ejecucion_Madrid (1).pdf | `06a4d1dc-28fe-724c-8000-12c7e44a9b45` | Run de ejemplo del 07/07; hay otro anterior (`06a4bba0-9ca1-76e2…`) |
| MA_Presupuesto Licencia_Madrid Capital.pdf | `06a4bba0-9ca1-7e79-8000-721a5f95145e` | |
| MADRID_MADRID_SP250600117588_PLANO_DE_PERMISO.pdf (1).pdf | `06a4bba0-9ca1-7d20-8000-10ff8a68bb6d` | |
| Plan acopios y residuos.pdf | `06a4bba0-9ca1-7b7d-8000-4fb779e3b903` | |
| 8570820_4119522.pdf | `06a4bba1-66d1-7575-8000-cdf9faeaac25` | Subido dos veces; el otro run (`06a4bba1-66d2-771e…`) da fechas y medidas distintas |
| GESTION RESIDUOS.pdf | `06a4bba1-66d2-73f3-8000-9d616ae99844` | Hojas 28–32 del 8570820 |
| PLANOS.pdf | `06a4bba1-66d2-7074-8000-40aef011dcb3` | Hojas 42–47 del 8570820 |
| L4.032.12.pdf | — | El document packet existe pero está en `not_started` |
| Datos Subcontratistas.pdf | — | Nunca se subió (es un distractor: no es de calas) |

En la org hay también un `PRESUPUESTO.pdf` (hoja 33 del 8570820) que no está en `samples/` y no se puntúa.

Expedientes: **San Mateo 17** (i-DE, eléctrico, 4 docs) · **Pastrana 8B** (Nedgia, gas, 4 docs) · **Telefónica 8570820**, CL Raimundo Fdez. Villaverde 69 (3 docs) · **Mar de Bering** (agua, 1 plano) · un documento no relacionado.

## Detalle por documento

✅ acierto · ❌ error · ❌ ⚠️ error con confianza ≥ 90. En el GT, `a \| b` significa que se acepta cualquiera de las opciones.

### 8570820_4119522.pdf

Tipo (GT): **memoria** · Clasificado como: **Memoria** · Aciertos: **23/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | Ejecución de 1 arqueta tipo M In Situ y 2 canalizaciones tipo 2 C.P... | La ejecución de 1 arqueta tipo M In Situ y la ejecución de 2 canali... | 93 | ✅ |
| plazo_de_ejecucion | 10 | 10 | 99 | ✅ |
| id_proyecto_contratista | null \| 8570820 | null | 99 | ✅ |
| ubicacion_de_la_obra | CL RAIMUNDO FDEZ VILLAVERDE 69 MADRID | CL RAIMUNDO FDEZ VILLAVERDE 69 MADRID (MADRID) | 99 | ✅ |
| id_obra | 8570820 | 8570820 | 99 | ✅ |
| total_presupuesto | 973.04 | 973.04 | 99 | ✅ |
| gestion_residuos | Inertes (tierras, hormigón, escombros) a vertedero o depósito contr... \| Todos los residuos generados serán depositados en gestor autorizado... | todos los residuos generados serán depositados en gestor autorizado... | 93 | ✅ |
| gestores_autorizados | True | True | 99 | ✅ |
| tipo_de_suministro | Telecomunicaciones \| Fibra óptica \| Comunicaciones electrónicas | suministro de la conexión a la red pública de comunicaciones electr... | 91 | ✅ |
| municipio | Madrid | MADRID | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | Atender la petición de variación de instalaciones de telecomunicaci... | atender la petición de variación de instalaciones de telecomunicaci... | 94 | ✅ |
| subcontratista | null | null | 99 | ✅ |
| fecha_inicio_prevista | null | 0325-12-03 | 71 | ❌ |
| fecha_fin_prevista | null | 0425-12-03 | 0 | ❌ |
| profundidad_m | 0.45 \| 0.6 \| 0.63 | 0.45 | 93 | ✅ |
| otras_unidades | null \| 1 arqueta tipo M In Situ | null | 99 | ✅ |
| duracion_dias | 10 | 10 | 99 | ✅ |
| presupuesto | 973.04 | 973.04 | 99 | ✅ |
| direccion.tipo | Calle | null | 99 | ❌ ⚠️ |
| direccion.nombre | RAIMUNDO FDEZ VILLAVERDE \| RAIMUNDO FERNANDEZ VILLAVERDE | RAIMUNDO FDEZ VILLAVERDE | 99 | ✅ |
| direccion.numero | 69 | 69 | 99 | ✅ |
| direccion.categoria_fiscal | null | null | 99 | ✅ |
| direccion.distrito | null | null | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [6.2 m; 2.4 m] \| [8.6 m] | [8.6 m; 6.2 m; 2.4 m] | 84 | ❌ |
| medidas_calzada | [] | [] | 99 | ✅ |

### 9045838454 Calle SAN MATEO, 17.pdf

Tipo (GT): **plano** · Clasificado como: **Plano** · Aciertos: **17/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | Apertura y posterior reposición de canalización con 4 tubos de 160 ... | ENTRONQUE Y REFUERZO (a realizar por i-DE) 1.- Solicitud de permiso... | 92 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null \| 9045838454 | null | 100 | ✅ |
| ubicacion_de_la_obra | Calle SAN MATEO, 17, Bajo ASCN | Calle SAN MATEO, 17, Bajo ASCN, MADRID | 99 | ✅ |
| id_obra | 9045838454 | 9045838454 | 99 | ✅ |
| total_presupuesto | null | 0.0 | 100 | ❌ ⚠️ |
| gestion_residuos | null | null | 100 | ✅ |
| gestores_autorizados | null | False | 0 | ❌ |
| tipo_de_suministro | Cambio tensión \| Electricidad \| Baja Tensión | Cambio tensión | 99 | ✅ |
| municipio | Madrid | MADRID | 99 | ✅ |
| potencia | 73,5 kW | 73,5 Kw | 99 | ✅ |
| motivo_de_la_obra | Cambio tensión \| Cambio de tensión de la finca de 127/230 V a 230/400 V normalizada | Cambio tensión | 92 | ✅ |
| subcontratista | null | null | 99 | ✅ |
| fecha_inicio_prevista | null | 2024-09-30 | 93 | ❌ ⚠️ |
| fecha_fin_prevista | null | 2025-09-24 | 99 | ❌ ⚠️ |
| profundidad_m | null \| 0.96 \| 1.16 \| 0.8 | 11.6 | 92 | ❌ ⚠️ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| direccion.tipo | Calle | Calle | 99 | ✅ |
| direccion.nombre | SAN MATEO | SAN MATEO | 99 | ✅ |
| direccion.numero | 17 | 17 | 99 | ✅ |
| direccion.categoria_fiscal | null | null | 99 | ✅ |
| direccion.distrito | null | null | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [] | [9.6 m arena] | 99 | ❌ ⚠️ |
| medidas_calzada | [] | [11.6 m mezcla bituminosa] | 99 | ❌ ⚠️ |

### Datos Subcontratistas.pdf  (tipo GT: otro) — sin resultado en results/calas/baseline


### GESTION RESIDUOS.pdf

Tipo (GT): **residuos_acopio** · Clasificado como: **Residuos** · Aciertos: **13/22**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null | null | 99 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null \| 8570820 | 8570820 | 83 | ✅ |
| ubicacion_de_la_obra | null | null | 99 | ✅ |
| id_obra | 8570820 | null | 75 | ❌ |
| total_presupuesto | null | 0.0 | 100 | ❌ ⚠️ |
| gestion_residuos | Inertes (tierras, hormigón, escombros) a vertedero o depósito contr... \| Todos los residuos generados serán depositados en gestor autorizado... | ...deberá tenerse especial cuidado en que la manipulación, la gesti... | 88 | ❌ |
| gestores_autorizados | True | True | 99 | ✅ |
| tipo_de_suministro | null | null | 100 | ✅ |
| municipio | Madrid | MADRID | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | null | null | 99 | ✅ |
| subcontratista | null | null | 99 | ✅ |
| fecha_inicio_prevista | null | 2025-12-03 | 94 | ❌ ⚠️ |
| fecha_fin_prevista | null | 2025-12-03 | 99 | ❌ ⚠️ |
| profundidad_m | null | 0.0 | 99 | ❌ ⚠️ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | null | 0.0 | 75 | ❌ |
| direccion | null | null |  | ✅ |
| medidas_acera | [] | [] |  | ✅ |
| medidas_calzada | [] | [] |  | ✅ |

### GESTIÓN DE RESIDUOS Y DE ACOPIOS.pdf

Tipo (GT): **residuos_acopio** · Clasificado como: **Residuos** · Aciertos: **14/22**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null | null | 99 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null | null | 99 | ✅ |
| ubicacion_de_la_obra | null | null | 99 | ✅ |
| id_obra | null | null | 99 | ✅ |
| total_presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| gestion_residuos | El tratamiento de los residuos se realizará con contratas homologad... | El tratamiento de los residuos se realizará con contratas homologad... | 99 | ✅ |
| gestores_autorizados | True | True | 99 | ✅ |
| tipo_de_suministro | null | null | 99 | ✅ |
| municipio | null | null | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | null | null | 99 | ✅ |
| subcontratista | null | null | 99 | ✅ |
| fecha_inicio_prevista | null | 0000-01-01 | 88 | ❌ |
| fecha_fin_prevista | null | 0000-01-01 | 99 | ❌ ⚠️ |
| profundidad_m | null | 0.0 | 99 | ❌ ⚠️ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| direccion | null | nombre=San Adrián, numero=48 | 99 | ❌ ⚠️ |
| medidas_acera | [] | [] |  | ✅ |
| medidas_calzada | [] | [] |  | ✅ |

### L4.032.12.pdf  (tipo GT: plano) — sin resultado en results/calas/baseline


### MADRID_MADRID_SP250600117588_PLANO_DE_PERMISO.pdf (1).pdf

Tipo (GT): **plano** · Clasificado como: **Plano** · Aciertos: **19/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null \| Desplazamiento de 3º: canalización de polietileno 110 mm de 10 m y ... | null | 83 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null | null | 99 | ✅ |
| ubicacion_de_la_obra | PASTRANA 8B (DESPLAZAMIENTO RED) | PASTRANA 8B (DESPLAZAMIENTO RED) | 90 | ✅ |
| id_obra | 022025649558 | 022025649558 | 78 | ✅ |
| total_presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| gestion_residuos | null | null | 99 | ✅ |
| gestores_autorizados | null | False | 99 | ❌ ⚠️ |
| tipo_de_suministro | Gas natural \| Gas | GAS NATURAL | 99 | ✅ |
| municipio | Madrid | Madrid | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | Desplazamiento de 3º \| Desplazamiento de red \| Desplazamiento Terceros | DESPLAZAMIENTO RED | 90 | ✅ |
| subcontratista | null | null | 95 | ✅ |
| fecha_inicio_prevista | null | 2025-12-09 | 80 | ❌ |
| fecha_fin_prevista | null | 2025-12-09 | 80 | ❌ |
| profundidad_m | 0.6 \| 0.8 | 0.6 | 79 | ✅ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | null | 0.0 | 0 | ❌ |
| direccion.tipo | Calle | Calle | 79 | ✅ |
| direccion.nombre | PASTRANA | Pastrana | 79 | ✅ |
| direccion.numero | 8B | 8B | 90 | ✅ |
| direccion.categoria_fiscal | null | null | 90 | ✅ |
| direccion.distrito | San Blas | San Blas | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [10.0 m Losetas especiales; 3.8 m Losetas especiales] \| [13.8 m Losetas especiales] | [10.0 m Aglomerado asfáltico; 3.8 m Aglomerado asfáltico] | 99 | ❌ ⚠️ |
| medidas_calzada | [] | [] | 99 | ✅ |

### MA_Memoria y plazo de ejecucion_Madrid (1).pdf

Tipo (GT): **memoria** · Clasificado como: **Memoria** · Aciertos: **22/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | A partir de la tubería existente se canaliza hasta el punto de sumi... | a partir de la tubería existente se canaliza hasta el punto de sumi... | 99 | ✅ |
| plazo_de_ejecucion | 9 | 9 | 99 | ✅ |
| id_proyecto_contratista | null \| ACT250600117588 | ACT250600117588 | 99 | ✅ |
| ubicacion_de_la_obra | C/ PASTRANA 8B (DESPLAZAMIENTO RED) | C/ PASTRANA 8B (DESPLAZAMIENTO RED) | 99 | ✅ |
| id_obra | ACT250600117588 | ACT250600117588 | 99 | ✅ |
| total_presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| gestion_residuos | null \| Retirada de tierras a vertedero | RETIRADA DE TIERRAS A VERTEDERO | 93 | ✅ |
| gestores_autorizados | null | False | 99 | ❌ ⚠️ |
| tipo_de_suministro | Gas \| Gas natural | gas | 99 | ✅ |
| municipio | null \| Madrid | null | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | Atender la solicitud de suministro de gas \| Desplazamiento Terceros \| Desplazamiento de red | Atender la solicitud de suministro de gas definida en el apartado (1). | 99 | ✅ |
| subcontratista | null | null | 98 | ✅ |
| fecha_inicio_prevista | null | 2026-07-07 | 92 | ❌ ⚠️ |
| fecha_fin_prevista | null | 2026-07-07 | 93 | ❌ ⚠️ |
| profundidad_m | 0.8 | 0.8 | 99 | ✅ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | 9 | 9 | 99 | ✅ |
| presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| direccion.tipo | Calle | C/ | 99 | ✅ |
| direccion.nombre | PASTRANA | PASTRANA | 99 | ✅ |
| direccion.numero | 8B | 8B | 99 | ✅ |
| direccion.categoria_fiscal | null | null | 99 | ✅ |
| direccion.distrito | San Blas | San Blas | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [13.8 m Loseta] | [13.8 m LOSETA] | 99 | ✅ |
| medidas_calzada | [] | [] | 99 | ✅ |

### MA_Presupuesto Licencia_Madrid Capital.pdf

Tipo (GT): **presupuestos** · Clasificado como: **Presupuestos** · Aciertos: **18/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null \| Desplazamiento Terceros \| PASTRANA 8 (DESPLAZAMIENTO RED) | PASTRANA 8 (DESPLAZAMIENTO RED) | 93 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null \| ACT250600117588 | ACT250600117588 | 99 | ✅ |
| ubicacion_de_la_obra | PASTRANA 8 (DESPLAZAMIENTO RED) | null | 99 | ❌ ⚠️ |
| id_obra | ACT250600117588 | PASTRANA 8 (DESPLAZAMIENTO RED) | 99 | ❌ ⚠️ |
| total_presupuesto | 1446.24 | 1446.24 | 99 | ✅ |
| gestion_residuos | null | null | 99 | ✅ |
| gestores_autorizados | null | False | 99 | ❌ ⚠️ |
| tipo_de_suministro | null | null | 99 | ✅ |
| municipio | null \| Madrid | null | 99 | ✅ |
| potencia | null | null | 96 | ✅ |
| motivo_de_la_obra | Desplazamiento Terceros \| Desplazamiento de red | DESPLAZAMIENTO RED | 99 | ✅ |
| subcontratista | null | null | 99 | ✅ |
| fecha_inicio_prevista | null | 2025-12-09 | 99 | ❌ ⚠️ |
| fecha_fin_prevista | null | 2025-12-09 | 99 | ❌ ⚠️ |
| profundidad_m | null | 0.0 | 96 | ❌ ⚠️ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | 1446.24 | 1446.24 | 99 | ✅ |
| direccion.tipo | null \| Calle | null | 99 | ✅ |
| direccion.nombre | PASTRANA | PASTRANA 8 | 99 | ✅ |
| direccion.numero | 8 | 8 | 99 | ✅ |
| direccion.categoria_fiscal | null | null | 99 | ✅ |
| direccion.distrito | null | null | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [13.8 m Loseta especial] | [13.8 m Loseta especial] | 92 | ✅ |
| medidas_calzada | [] | [13.8 m Asfalto] | 82 | ❌ |

### MEMORIA Calle SAN MATEO, 17.pdf

Tipo (GT): **memoria** · Clasificado como: **Memoria** · Aciertos: **22/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | Obra de apertura de cala en acera para tendido de cable subterráneo... | OBRA DE APERTURA DE CALA en acera para tendido de cable subterráneo... | 99 | ✅ |
| plazo_de_ejecucion | 30 | 30 | 99 | ✅ |
| id_proyecto_contratista | null \| 9045838454 | null | 99 | ✅ |
| ubicacion_de_la_obra | Calle SAN MATEO, 17 | Calle SAN MATEO, 17 | 99 | ✅ |
| id_obra | 9045838454 | 9045838454 | 99 | ✅ |
| total_presupuesto | 2092.38 | 2092.38 | 99 | ✅ |
| gestion_residuos | null | null | 75 | ✅ |
| gestores_autorizados | null | False | 75 | ❌ |
| tipo_de_suministro | Baja Tensión \| Electricidad \| Eléctrico | Baja Tensión | 98 | ✅ |
| municipio | Madrid | Madrid | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | Acometida de Baja Tensión para nuevo suministro | CALA en acera para tendido de cable subterráneo de Baja Tensión par... | 99 | ✅ |
| subcontratista | TRADIVEL | null | 99 | ❌ ⚠️ |
| fecha_inicio_prevista | null | 2025-11-14 | 99 | ❌ ⚠️ |
| fecha_fin_prevista | null | 2025-12-14 | 99 | ❌ ⚠️ |
| profundidad_m | null | 0.0 | 99 | ❌ ⚠️ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | 30 | 30 | 99 | ✅ |
| presupuesto | 2092.38 | 2092.38 | 99 | ✅ |
| direccion.tipo | Calle | Calle | 99 | ✅ |
| direccion.nombre | SAN MATEO | SAN MATEO | 99 | ✅ |
| direccion.numero | 17 | 17 | 99 | ✅ |
| direccion.categoria_fiscal | null | null | 99 | ✅ |
| direccion.distrito | null | null | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [6.0 m] | [6.0 m] | 99 | ✅ |
| medidas_calzada | [] | [] |  | ✅ |

### PLANOS.pdf

Tipo (GT): **plano** · Clasificado como: **Plano** · Aciertos: **10/22**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null \| Nueva canalización 2 C.PVC 63 B2 de 6,20 m y 2,40 m en acera y nuev... | null | 99 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null \| 8570820 | 8570820 | 99 | ✅ |
| ubicacion_de_la_obra | null | null | 50 | ✅ |
| id_obra | 8570820 | null | 99 | ❌ ⚠️ |
| total_presupuesto | null | 0.0 | 71 | ❌ |
| gestion_residuos | null | null | 71 | ✅ |
| gestores_autorizados | null | False | 71 | ❌ |
| tipo_de_suministro | null | null | 71 | ✅ |
| municipio | Madrid | MADRID | 79 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | null | null | 91 | ✅ |
| subcontratista | null | SMART TELECOM CONSULTING 2004 SL | 99 | ❌ ⚠️ |
| fecha_inicio_prevista | null | 2025-12-03 | 99 | ❌ ⚠️ |
| fecha_fin_prevista | null | 2025-12-03 | 91 | ❌ ⚠️ |
| profundidad_m | 0.45 \| 0.63 | 0.6 | 85 | ❌ |
| otras_unidades | null | null | 100 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| direccion | null | null | 100 | ✅ |
| medidas_acera | [6.2 m; 2.4 m] \| [8.6 m] | [0.45 m PVC de 63mm, HM-15/P/20, MATERIAL COMPACTADO] | 89 | ❌ |
| medidas_calzada | [] | [0.6 m PVC de 63mm, HM-15/P/20, MATERIAL COMPACTADO] | 97 | ❌ ⚠️ |

### PRESUPUESTO Calle SAN MATEO, 17.pdf

Tipo (GT): **presupuestos** · Clasificado como: **Presupuestos** · Aciertos: **19/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null | Excavación por necesidad de acceso a red existente; Pavimentación b... | 94 | ❌ ⚠️ |
| plazo_de_ejecucion | null | 0 | 96 | ❌ ⚠️ |
| id_proyecto_contratista | null | null | 99 | ✅ |
| ubicacion_de_la_obra | Calle SAN MATEO, 17 | Calle SAN MATEO, 17 | 99 | ✅ |
| id_obra | null | null | 96 | ✅ |
| total_presupuesto | 2092.38 | 2092.38 | 99 | ✅ |
| gestion_residuos | null | null | 99 | ✅ |
| gestores_autorizados | null | False | 99 | ❌ ⚠️ |
| tipo_de_suministro | null | null | 99 | ✅ |
| municipio | null | null | 99 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | null | necesidad de acceso a red existente | 93 | ❌ ⚠️ |
| subcontratista | null | null | 99 | ✅ |
| fecha_inicio_prevista | null | 1970-01-01 | 90 | ❌ ⚠️ |
| fecha_fin_prevista | null | 1970-01-01 | 99 | ❌ ⚠️ |
| profundidad_m | null | 0.0 | 99 | ❌ ⚠️ |
| otras_unidades | null | null | 85 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | 2092.38 | 2092.38 | 99 | ✅ |
| direccion.tipo | Calle | Calle | 99 | ✅ |
| direccion.nombre | SAN MATEO | SAN MATEO | 99 | ✅ |
| direccion.numero | 17 | 17 | 99 | ✅ |
| direccion.categoria_fiscal | null | null | 99 | ✅ |
| direccion.distrito | null | null | 99 | ✅ |
| direccion.barrio | null | null | 99 | ✅ |
| medidas_acera | [] | [] |  | ✅ |
| medidas_calzada | [] | [] |  | ✅ |

### Plan acopios y residuos.pdf

Tipo (GT): **residuos_acopio** · Clasificado como: **Residuos** · Aciertos: **19/27**

| Campo | Ground truth | Workflow | Conf. | |
|---|---|---|---|---|
| descripcion_de_la_obra | null | null | 99 | ✅ |
| plazo_de_ejecucion | null | 0 | 99 | ❌ ⚠️ |
| id_proyecto_contratista | null | null | 87 | ✅ |
| ubicacion_de_la_obra | PASTRANA 8B (DESPLAZAMIENTO RED) | PASTRANA 8B (DESPLAZAMIENTO RED) | 87 | ✅ |
| id_obra | null | null | 87 | ✅ |
| total_presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| gestion_residuos | Prevención y separación de residuos; reutilización, reciclado o val... | Durante la realización de la obra se adoptarán... reutilización, re... | 90 | ✅ |
| gestores_autorizados | True | True | 95 | ✅ |
| tipo_de_suministro | null | Agua | 99 | ❌ ⚠️ |
| municipio | null \| Madrid | null | 75 | ✅ |
| potencia | null | null | 99 | ✅ |
| motivo_de_la_obra | null \| Desplazamiento de red | DESPLAZAMIENTO RED | 87 | ✅ |
| subcontratista | null | null | 96 | ✅ |
| fecha_inicio_prevista | null | 1970-01-01 | 50 | ❌ |
| fecha_fin_prevista | null | 1970-01-01 | 99 | ❌ ⚠️ |
| profundidad_m | null | 0.0 | 99 | ❌ ⚠️ |
| otras_unidades | null | null | 99 | ✅ |
| duracion_dias | null | 0 | 99 | ❌ ⚠️ |
| presupuesto | null | 0.0 | 99 | ❌ ⚠️ |
| direccion.tipo | null \| Calle | null | 87 | ✅ |
| direccion.nombre | PASTRANA | PASTRANA | 87 | ✅ |
| direccion.numero | 8B | 8B | 87 | ✅ |
| direccion.categoria_fiscal | null | null | 87 | ✅ |
| direccion.distrito | San Blas | San Blas | 78 | ✅ |
| direccion.barrio | null | null | 78 | ✅ |
| medidas_acera | [13.8 m] | [13.8 m] | 86 | ✅ |
| medidas_calzada | [] | [] | 99 | ✅ |

## Precisión por campo

| Campo | Aciertos | % |
|---|---|---|
| fecha_inicio_prevista | 0/11 | 0% |
| fecha_fin_prevista | 0/11 | 0% |
| plazo_de_ejecucion | 3/11 | 27% |
| profundidad_m | 3/11 | 27% |
| duracion_dias | 3/11 | 27% |
| total_presupuesto | 4/11 | 36% |
| gestores_autorizados | 4/11 | 36% |
| presupuesto | 4/11 | 36% |
| medidas_acera | 7/11 | 64% |
| direccion | 2/3 | 67% |
| id_obra | 8/11 | 73% |
| medidas_calzada | 8/11 | 73% |
| subcontratista | 9/11 | 82% |
| direccion.tipo | 7/8 | 88% |
| descripcion_de_la_obra | 10/11 | 91% |
| ubicacion_de_la_obra | 10/11 | 91% |
| gestion_residuos | 10/11 | 91% |
| tipo_de_suministro | 10/11 | 91% |
| motivo_de_la_obra | 10/11 | 91% |
| id_proyecto_contratista | 11/11 | 100% |
| municipio | 11/11 | 100% |
| potencia | 11/11 | 100% |
| otras_unidades | 11/11 | 100% |
| direccion.nombre | 8/8 | 100% |
| direccion.numero | 8/8 | 100% |
| direccion.categoria_fiscal | 8/8 | 100% |
| direccion.distrito | 8/8 | 100% |
| direccion.barrio | 8/8 | 100% |

**Total: 196/282 = 70%** · Errores con confianza ≥ 90: **68**
