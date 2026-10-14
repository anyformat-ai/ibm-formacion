#!/usr/bin/env python3
"""Puntúa runs de anyformat (calas y canalizaciones) contra ground_truth/calas.

Uso:
    python3 tools/score_calas.py results/calas/baseline
    python3 tools/score_calas.py results/calas/mejorado --md     # tablas markdown
    python3 tools/score_calas.py results/calas/mejorado --json   # resumen JSON

Cada fichero de resultados se llama <nombre-del-pdf-sin-.pdf>.json y contiene la
respuesta de GET /v3/runs/{run_id}/ (o un dict plano {campo: valor}). Si el
workflow tiene varios extract (p. ej. uno por tipo de documento) se fusionan
todos los `results.extractions[].fields`.

Reglas de comparación:
  * null / "" / "null" son "no consta". 0, 0.0, False y "1970-01-01" NO son null:
    si el documento no trae el dato y el workflow devuelve 0, cuenta como error.
  * Números: tolera formato español (2.092,38) y diferencias < 0.01.
  * Fechas: ISO o dd/mm/aaaa.
  * Texto: sin mayúsculas, tildes ni puntuación; abreviaturas de vía (C/, CL, Avda.).
  * Texto libre (descripción, motivo, gestión de residuos, ubicación...): acierto si
    uno contiene al otro o si >= 60 % de las palabras del GT aparecen en la salida.
  * {"any_of": [...]} en el GT acepta cualquiera de las opciones.
  * medidas_acera / medidas_calzada: se ignoran filas con largo 0/null; se exige el
    mismo número de filas y que cada fila del GT case por largo (y por ancho /
    tipo_pavimento solo cuando el GT los rellena).
  * direccion se puntúa por subcampo (direccion.tipo, direccion.nombre, ...).
"""
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GT_DIR = os.path.join(ROOT, "ground_truth", "calas")

FREE_TEXT = {"descripcion_de_la_obra", "gestion_residuos", "motivo_de_la_obra", "otras_unidades",
             "ubicacion_de_la_obra", "tipo_de_suministro"}
NUMERIC = {"plazo_de_ejecucion", "total_presupuesto", "profundidad_m", "duracion_dias", "presupuesto"}
DATES = {"fecha_inicio_prevista", "fecha_fin_prevista"}
BOOLS = {"gestores_autorizados"}
LISTS = {"medidas_acera", "medidas_calzada"}
DIR_SUBFIELDS = ["tipo", "nombre", "numero", "categoria_fiscal", "distrito", "barrio"]
VIA = {"c": "calle", "cl": "calle", "c/": "calle", "calle": "calle", "av": "avenida", "avda": "avenida",
       "avenida": "avenida", "pza": "plaza", "pl": "plaza", "plaza": "plaza", "po": "paseo", "pº": "paseo",
       "paseo": "paseo", "ctra": "carretera"}
HIGH_CONF = 90


def nfc(s):
    return unicodedata.normalize("NFC", s)


def strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def is_null(v):
    return v is None or (isinstance(v, str) and v.strip().lower() in ("", "null", "none", "n/a"))


def norm_text(v):
    s = strip_accents(str(v)).lower()
    s = re.sub(r"[^\w\s/]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def to_number(v):
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("€", "").replace(" ", "")
    m = re.match(r"^-?[\d.,]+", s)
    if not m:
        return None
    s = m.group(0)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        return None


def to_date(v):
    s = str(v).strip()
    m = re.match(r"^(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        return "%04d-%02d-%02d" % tuple(int(x) for x in m.groups())
    m = re.match(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{2,4})", s)
    if m:
        d, mo, y = (int(x) for x in m.groups())
        return "%04d-%02d-%02d" % (y + 2000 if y < 100 else y, mo, d)
    return s


def to_bool(v):
    if isinstance(v, bool):
        return v
    s = norm_text(v)
    if s in ("true", "si", "yes", "1", "verdadero"):
        return True
    if s in ("false", "no", "0", "falso"):
        return False
    return None


def num_unit(v):
    """'73,5 Kw' -> (73.5, 'kw')"""
    n = to_number(v)
    if n is None:
        return None
    unit = norm_text(re.sub(r"^-?[\d.,\s]+", "", str(v)))
    return n, unit


def text_match(gt, out, field):
    a, b = norm_text(gt), norm_text(out)
    if field == "direccion.tipo":
        a, b = VIA.get(a.rstrip("/"), VIA.get(a, a)), VIA.get(b.rstrip("/"), VIA.get(b, b))
    if a == b:
        return True
    nu_a, nu_b = num_unit(gt), num_unit(out)
    if nu_a and nu_b and abs(nu_a[0] - nu_b[0]) < 0.01 and nu_a[1] == nu_b[1]:
        return True
    if field in FREE_TEXT or field == "direccion.nombre":
        if (len(b) >= 4 and b in a) or a in b:
            return True
        if field in FREE_TEXT:
            ta, tb = set(a.split()), set(b.split())
            return bool(ta) and len(ta & tb) / len(ta) >= 0.6
    return False


def match_scalar(gt, out, field):
    if isinstance(gt, dict) and "any_of" in gt:
        return any(match_scalar(g, out, field) for g in gt["any_of"])
    if is_null(gt) or is_null(out):
        return is_null(gt) and is_null(out)
    base = field.split(".")[-1] if field.startswith("direccion.") else field
    if base in NUMERIC:
        a, b = to_number(gt), to_number(out)
        return a is not None and b is not None and abs(a - b) < 0.01
    if base in DATES:
        return to_date(gt) == to_date(out)
    if base in BOOLS:
        return to_bool(gt) == to_bool(out)
    return text_match(gt, out, field)


def clean_rows(rows):
    res = []
    for r in rows or []:
        largo = to_number(r.get("largo")) if not is_null(r.get("largo")) else None
        if largo:
            res.append(r)
    return res


def match_rows(gt_rows, out_rows):
    if isinstance(gt_rows, dict) and "any_of" in gt_rows:
        return any(match_rows(g, out_rows) for g in gt_rows["any_of"])
    gt_rows, out_rows = clean_rows(gt_rows), clean_rows(out_rows)
    if len(gt_rows) != len(out_rows):
        return False
    pending = list(out_rows)
    for g in gt_rows:
        for o in pending:
            ok = match_scalar(g["largo"], o.get("largo"), "profundidad_m")  # comparación numérica
            if ok and not is_null(g.get("ancho")):
                ok = match_scalar(g["ancho"], o.get("ancho"), "profundidad_m")
            if ok and not is_null(g.get("tipo_pavimento")):
                ok = match_scalar(g["tipo_pavimento"], o.get("tipo_pavimento"), "tipo_de_suministro")
            if ok:
                pending.remove(o)
                break
        else:
            return False
    return True


def unwrap(v):
    """Campo de la API -> (valor, confianza). Soporta listas de objetos anidados."""
    if isinstance(v, dict) and "value" in v:
        val = v.get("value_override") if not is_null(v.get("value_override")) else v.get("value")
        return val, v.get("confidence")
    if isinstance(v, list):
        rows, confs = [], []
        for item in v:
            row, row_conf = {}, {}
            for k, sub in (item or {}).items():
                row[k], row_conf[k] = unwrap(sub)
            row["_conf"] = row_conf
            rows.append(row)
            # confianza de la fila = la del largo (o la del primer subcampo con confianza)
            c = row_conf.get("largo")
            if c is None:
                c = next((x for x in row_conf.values() if x is not None), None)
            if c is not None:
                confs.append(c)
        return rows, (min(confs) if confs else None)
    return v, None


def load_output(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    res = data.get("results", data) if isinstance(data, dict) else {}
    field_sets = []
    if isinstance(res, dict) and res.get("extractions"):
        field_sets = [e.get("fields") or {} for e in res["extractions"]]
    elif isinstance(res, dict) and isinstance(res.get("extraction"), dict):
        field_sets = [res["extraction"]]
    else:
        field_sets = [res]
    merged = {}
    for fs in field_sets:
        for k, v in fs.items():
            val, conf = unwrap(v)
            if k not in merged or (is_null(merged[k][0]) or merged[k][0] == []) and not (is_null(val) or val == []):
                merged[k] = (val, conf)
    cls = [c.get("category") for c in (res.get("classifications") or [])] if isinstance(res, dict) else []
    return merged, cls


def score_doc(gt, out):
    rows = []
    for field, gval in gt["fields"].items():
        if field == "direccion":
            oval, conf = out.get("direccion", (None, None))
            orow = (oval[0] if isinstance(oval, list) and oval else oval) or {}
            sub_conf = orow.get("_conf", {}) if isinstance(orow, dict) else {}
            if gval is None:
                filled = {k: v for k, v in orow.items() if not is_null(v) and k not in ("_conf", "descripcion_ubicacion")} \
                    if isinstance(orow, dict) else {}
                rows.append(("direccion", None, filled or None, conf, not filled, "direccion" in out))
                continue
            for sub in DIR_SUBFIELDS:
                if sub not in gval:
                    continue
                o = orow.get(sub) if isinstance(orow, dict) else None
                rows.append(("direccion." + sub, gval[sub], o, sub_conf.get(sub, conf),
                             match_scalar(gval[sub], o, "direccion." + sub), "direccion" in out))
            continue
        present = field in out
        oval, conf = out.get(field, (None, None))
        if field in LISTS:
            ok = match_rows(gval, oval if isinstance(oval, list) else [])
        else:
            ok = match_scalar(gval, oval, field)
        rows.append((field, gval, oval, conf, ok, present))
    return rows


def fmt(v):
    if isinstance(v, dict) and "any_of" in v:
        return " \\| ".join("null" if x is None else fmt(x) for x in v["any_of"])
    if isinstance(v, list):
        r = clean_rows(v)
        return "[" + "; ".join("%s m%s" % (x.get("largo"), (" " + str(x["tipo_pavimento"])) if not is_null(x.get("tipo_pavimento")) else "") for x in r) + "]"
    if isinstance(v, dict):
        return ", ".join("%s=%s" % (k, x) for k, x in v.items() if k != "_conf")
    if v is None:
        return "null"
    s = str(v).replace("\n", " ").replace("|", "\\|")
    return s if len(s) <= 70 else s[:67] + "..."


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    rdir = argv[1]
    md, as_json = "--md" in argv, "--json" in argv
    gts = {}
    for fn in sorted(os.listdir(GT_DIR)):
        if fn.endswith(".json"):
            with open(os.path.join(GT_DIR, fn), encoding="utf-8") as f:
                gts[nfc(fn[:-5])] = json.load(f)
    outs = {nfc(fn[:-5]): os.path.join(rdir, fn) for fn in os.listdir(rdir) if fn.endswith(".json")}

    per_field, per_doc, high_conf_wrong, summary_docs = {}, [], [], {}
    for base, gt in gts.items():
        if base not in outs:
            per_doc.append((base, gt, None, None))
            continue
        out, cls = load_output(outs[base])
        rows = score_doc(gt, out)
        per_doc.append((base, gt, rows, cls))
        for field, g, o, conf, ok, present in rows:
            per_field.setdefault(field, [0, 0])
            per_field[field][0] += ok
            per_field[field][1] += 1
            if not ok and conf is not None and conf >= HIGH_CONF:
                high_conf_wrong.append((base, field, g, o, conf))
        summary_docs[base] = {"ok": sum(r[4] for r in rows), "total": len(rows), "clasificacion": cls}

    tot_ok = sum(v[0] for v in per_field.values())
    tot = sum(v[1] for v in per_field.values())

    if as_json:
        print(json.dumps({"accuracy": tot_ok / tot if tot else None, "ok": tot_ok, "total": tot,
                          "por_campo": {k: v[0] / v[1] for k, v in per_field.items()},
                          "por_documento": summary_docs,
                          "alta_confianza_erroneos": len(high_conf_wrong),
                          "sin_resultado": [b for b, _, r, _ in per_doc if r is None]},
                         ensure_ascii=False, indent=2))
        return 0

    for base, gt, rows, cls in per_doc:
        if rows is None:
            print("\n### %s  (tipo GT: %s) — sin resultado en %s\n" % (gt["file"], gt["tipo"], rdir) if md
                  else "\n== %s [%s]: SIN RESULTADO" % (gt["file"], gt["tipo"]))
            continue
        ok = sum(r[4] for r in rows)
        if md:
            print("\n### %s\n\nTipo (GT): **%s** · Clasificado como: **%s** · Aciertos: **%d/%d**\n"
                  % (gt["file"], gt["tipo"], ", ".join(cls) or "-", ok, len(rows)))
            print("| Campo | Ground truth | Workflow | Conf. | |\n|---|---|---|---|---|")
            for field, g, o, conf, good, present in rows:
                mark = "✅" if good else ("❌ ⚠️" if conf is not None and conf >= HIGH_CONF else "❌")
                print("| %s | %s | %s | %s | %s |" % (field, fmt(g), fmt(o) if present else "_(campo ausente)_",
                                                       "" if conf is None else int(conf), mark))
        else:
            print("\n== %s [%s] clasificado=%s  %d/%d" % (gt["file"], gt["tipo"], cls, ok, len(rows)))
            for field, g, o, conf, good, present in rows:
                if not good:
                    print("   ✗ %-24s GT=%-30s OUT=%-30s conf=%s" % (field, fmt(g)[:30], fmt(o)[:30], conf))

    print("\n## Precisión por campo\n" if md else "\n== Precisión por campo")
    if md:
        print("| Campo | Aciertos | % |\n|---|---|---|")
    for field, (k, n) in sorted(per_field.items(), key=lambda x: x[1][0] / x[1][1]):
        print(("| %s | %d/%d | %d%% |" if md else "   %-26s %2d/%-2d  %3d%%") % (field, k, n, round(100 * k / n)))
    print(("\n**Total: %d/%d = %.0f%%** · Errores con confianza ≥ %d: **%d**" if md
           else "\n== TOTAL %d/%d = %.0f%%   errores con confianza >= %d: %d")
          % (tot_ok, tot, 100 * tot_ok / tot if tot else 0, HIGH_CONF, len(high_conf_wrong)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
