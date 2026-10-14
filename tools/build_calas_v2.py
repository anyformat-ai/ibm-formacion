#!/usr/bin/env python3
"""Genera workflows/calas-v2.json: el workflow de calas revisado.

Cambios frente al de partida (workflows/calas-punto-de-partida.json):
  * Un extract por tipo de documento, con solo los campos que ese tipo puede traer.
  * Cada descripción dice cuándo devolver null (nunca 0, false ni una fecha por defecto).
  * Fechas previstas solo si están escritas; medidas y profundidad en metros, sin cotas de detalle.
  * Categoría "Otro" en el clasificador, sin extract.
  * Validaciones deterministas por rama.

Los nombres de campo son los mismos que en el de partida, para poder puntuar con tools/score_calas.py.

    python3 tools/build_calas_v2.py
"""
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NULL = " Si el documento no lo indica de forma explícita, devuelve null: nunca 0, false ni un valor por defecto."


def f(name, data_type, description, nested=None):
    field = {"name": name, "data_type": data_type, "description": description}
    if nested:
        field["nested_fields"] = nested
    return field


def medidas(donde, pavimento_ej):
    return f(
        f"Medidas {donde.capitalize()}", "object",
        f"Cada tramo de cala o zanja en {donde} con su longitud en metros (p. ej. 'cala de 6 m en {donde}'), una fila "
        "por tramo. Las cotas de secciones tipo o detalles constructivos (normalmente en mm o cm) NO son tramos de la "
        f"cala. Si el documento no da longitudes de {donde}, la lista va vacía.",
        [
            f("Largo", "float", "Longitud del tramo en metros (convierte cm o mm a metros)."),
            f("Ancho", "float", "Ancho del tramo en metros, si se indica; null si no."),
            f("Tipo pavimento", "string", f"Pavimento del tramo (p. ej. {pavimento_ej}), si se indica; null si no."),
        ],
    )


CAMPOS = {
    "descripcion": f("Descripción de la obra", "string",
                     "Objeto de la obra tal como lo redacta el documento: qué se hace (cala, canalización, acometida…), "
                     "dónde y para qué. Copia la frase principal sin resumirla." + NULL),
    "plazo": f("Plazo de ejecución", "integer",
               "Plazo de ejecución de la obra en días, como número entero (p. ej. 'PLAZO DE EJECUCIÓN: 30 días' → 30)."
               + NULL),
    "duracion": f("Duración (días)", "integer",
                  "Duración de la obra en días. Es el mismo dato que 'Plazo de ejecución': el número entero de días "
                  "que indica el documento." + NULL),
    "id_proyecto": f("Id Proyecto contratista", "string",
                     "Código interno del proyecto que asigna el contratista o la distribuidora (nº de proyecto, nº de "
                     "solicitud), cuando es distinto del ID de obra. Si el documento solo trae un código, va en "
                     "'ID Obra' y este campo es null."),
    "ubicacion": f("Ubicación de la obra", "string",
                   "Dirección donde se hace la obra, calle y número tal como aparece (p. ej. 'Calle SAN MATEO, 17')."
                   + NULL),
    "id_obra": f("ID Obra", "string",
                 "Número que identifica el expediente u obra: nº de expediente, de solicitud o de obra (p. ej. "
                 "'9045838454', 'SP250600117588'). Cópialo como texto exacto, sin quitar letras, barras ni guiones."
                 + NULL),
    "total": f("Total Presupuesto", "float",
               "Importe total del presupuesto de la obra en euros, con sus decimales (p. ej. 2.092,38 € → 2092.38). "
               "Solo si el documento contiene un importe de presupuesto. Si no hay importe, null: nunca 0."),
    "presupuesto": f("Presupuesto", "float",
                     "Mismo dato que 'Total Presupuesto': el importe total de la obra en euros, con decimales. "
                     "Si el documento no trae importe, null: nunca 0."),
    "residuos": f("Gestion residuos", "string",
                  "Cómo se tratan los residuos de la obra: tipos de residuo (tierras, hormigón, asfalto…), transporte "
                  "y destino (vertedero, planta de reciclaje, gestor). Resume lo que dice el documento." + NULL),
    "gestores": f("Gestores Autorizados", "boolean",
                  "true si el documento dice que los residuos se entregan a un gestor autorizado; false solo si dice "
                  "expresamente que no. Si no menciona gestores, null."),
    "suministro": f("Tipo de suministro", "string",
                    "Servicio que se canaliza o al que da servicio la obra: electricidad (baja o media tensión), gas, "
                    "agua o telecomunicaciones. El agua que se usa durante la obra (amasado, riego, limpieza) NO es el "
                    "suministro." + NULL),
    "municipio": f("Municipio", "string", "Municipio donde está la obra (p. ej. 'Madrid')." + NULL),
    "potencia": f("Potencia", "string",
                  "Potencia eléctrica con su unidad, tal como figura (p. ej. '3,45 kW'). Solo en obras eléctricas que "
                  "la indiquen." + NULL),
    "motivo": f("Motivo de la obra", "string",
                "Por qué se hace la obra: nueva acometida, avería, renovación o desplazamiento de red, nuevo "
                "suministro…" + NULL),
    "subcontratista": f("Subcontratista", "string",
                        "Empresa que ejecuta materialmente la obra (suele figurar como 'Contratista', 'Empresa "
                        "instaladora' o 'Subcontrata'). No es el promotor ni la distribuidora (i-DE, Nedgia, "
                        "Telefónica…), ni quien redacta o dibuja el proyecto." + NULL),
    "inicio": f("Fecha inicio prevista", "date",
                "Fecha prevista de inicio de la obra (YYYY-MM-DD), solo si el documento la escribe literalmente como "
                "fecha de inicio. La fecha de firma, del documento o del plano no cuenta, y no se calcula a partir del "
                "plazo. Si no figura, null."),
    "fin": f("Fecha fin prevista", "date",
             "Fecha prevista de fin de la obra (YYYY-MM-DD), solo si el documento la escribe literalmente como fecha "
             "de fin. No se calcula a partir del plazo ni de otras fechas. Si no figura, null."),
    "profundidad": f("Profundidad (m)", "float",
                     "Profundidad de la zanja o cala en metros, cuando el documento la indica para esta obra. Si viene "
                     "en mm o cm, conviértela (1160 mm = 1.16). Una zanja de calas no suele pasar de 2 m: un valor "
                     "mayor es casi seguro una cota mal leída." + NULL),
    "otras": f("Otras unidades", "string",
               "Otras superficies afectadas distintas de acera y calzada (zonas verdes, aparcamiento, terrizo…), si "
               "el documento las menciona." + NULL),
    "direccion": f("Dirección", "object",
                   "Dirección principal de la obra, una sola fila aunque el documento cite varias ubicaciones.",
                   [
                       f("Tipo", "string", "Tipo de vía (Calle, Avenida, Plaza, Paseo…)."),
                       f("Nombre", "string", "Nombre de la vía, sin el tipo."),
                       f("Número", "string", "Número de portal. Null si no tiene."),
                       f("Categoría fiscal", "string", "Categoría fiscal de la vía, solo si figura; null si no."),
                       f("Distrito", "string", "Distrito, solo si figura; null si no."),
                       f("Barrio", "string", "Barrio, solo si figura; null si no."),
                       f("Descripción ubicación", "string", "Referencias extra (tramo, cruce, frente a…), si las hay."),
                   ]),
    "acera": medidas("acera", "baldosa hidráulica, adoquín, terrazo"),
    "calzada": medidas("calzada", "aglomerado asfáltico, mezcla bituminosa, adoquín"),
}

RAMAS = {
    "memoria": {
        "name": "Memoria",
        "description": "Memoria descriptiva o técnica de la obra: describe el objeto, la ubicación, el plazo y las "
                       "unidades de obra. Puede incluir un resumen del presupuesto.",
        "campos": ["descripcion", "plazo", "duracion", "id_proyecto", "ubicacion", "id_obra", "total", "presupuesto",
                   "suministro", "municipio", "potencia", "motivo", "subcontratista", "inicio", "fin", "direccion",
                   "acera", "calzada", "profundidad", "otras", "residuos", "gestores"],
    },
    "plano": {
        "name": "Plano",
        "description": "Plano o documentación gráfica de la obra: situación, trazado, secciones tipo o detalles.",
        "campos": ["descripcion", "id_proyecto", "ubicacion", "id_obra", "suministro", "municipio", "potencia",
                   "motivo", "direccion", "acera", "calzada", "profundidad", "otras"],
    },
    "presupuestos": {
        "name": "Presupuestos",
        "description": "Presupuesto o valoración económica de la obra: partidas, mediciones e importe total.",
        "campos": ["descripcion", "id_proyecto", "ubicacion", "id_obra", "total", "presupuesto", "municipio",
                   "motivo", "direccion", "acera", "calzada", "plazo", "duracion"],
    },
    "residuos_acopio": {
        "name": "Residuos/Acopio",
        "description": "Plan o estudio de gestión de residuos y acopio de materiales de la obra.",
        "campos": ["residuos", "gestores", "id_proyecto", "id_obra", "municipio", "ubicacion", "motivo",
                   "direccion", "acera", "calzada"],
    },
}

OTRO = {"id": "otro", "name": "Otro",
        "description": "Cualquier documento que no sea memoria, plano, presupuesto ni gestión de residuos o acopios "
                       "de una obra de cala o canalización (fichas de empresa, capturas, certificados, facturas…)."}


def reglas(campos):
    out = []
    if "inicio" in campos:
        out.append({"id": "fechas_coherentes", "name": "Fecha fin ≥ fecha inicio", "kind": "deterministic",
                    "severity": "error", "check": {"type": "expression", "expression":
                    "data.fecha_inicio_prevista == null || data.fecha_fin_prevista == null || "
                    "data.fecha_fin_prevista >= data.fecha_inicio_prevista"}})
    if "profundidad" in campos:
        out.append({"id": "profundidad_razonable", "name": "Profundidad entre 0,2 y 3 m", "kind": "deterministic",
                    "severity": "warning", "check": {"type": "expression", "expression":
                    "data.profundidad_m == null || (data.profundidad_m >= 0.2 && data.profundidad_m <= 3.0)"}})
    if "total" in campos:
        out.append({"id": "presupuesto_positivo", "name": "Presupuesto > 0", "kind": "deterministic",
                    "severity": "error", "check": {"type": "expression", "expression":
                    "data.total_presupuesto == null || data.total_presupuesto > 0.0"}})
    if "plazo" in campos:
        out.append({"id": "plazo_positivo", "name": "Plazo > 0", "kind": "deterministic",
                    "severity": "error", "check": {"type": "expression", "expression":
                    "data.plazo_de_ejecucion == null || data.plazo_de_ejecucion > 0"}})
    return out


def build():
    nodes = [
        {"id": "parse", "type": "parse", "mode": "standard", "figure_enhancement": True,
         "effort": "mid", "ocr_effort": "high", "scanned_pages": "ocr"},
        {"id": "classify", "type": "classify",
         "user_prompt": "Cada documento es de un solo tipo: uno de los cuatro que el Ayuntamiento exige en una "
                        "solicitud de calas y canalizaciones, u 'Otro' si no es ninguno de ellos.",
         "categories": [{"id": k, "name": v["name"], "description": v["description"]} for k, v in RAMAS.items()]
                       + [OTRO]},
    ]
    edges = [{"source": "parse", "target": "classify", "branch": None}]
    for rama, cfg in RAMAS.items():
        nodes.append({"id": f"extract_{rama}", "type": "extract", "mode": "standard",
                      "extraction_schema": {"fields": [CAMPOS[c] for c in cfg["campos"]]}})
        edges.append({"source": "classify", "target": f"extract_{rama}", "branch": rama})
        rules = reglas(cfg["campos"])
        if rules:
            nodes.append({"id": f"validate_{rama}", "type": "validate", "rules": rules})
            edges.append({"source": f"extract_{rama}", "target": f"validate_{rama}", "branch": None})
    return {
        "name": "Formación IBM · Calas y canalizaciones (v2)",
        "description": "Revisión del workflow de calas: un extract por tipo de documento, null cuando el dato no "
                       "está, fechas solo literales, categoría 'Otro' y validaciones.",
        "nodes": nodes,
        "edges": edges,
    }


if __name__ == "__main__":
    path = os.path.join(ROOT, "workflows", "calas-v2.json")
    with open(path, "w") as fh:
        json.dump(build(), fh, ensure_ascii=False, indent=2)
    print(path)
