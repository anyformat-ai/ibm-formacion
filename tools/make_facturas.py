#!/usr/bin/env python3
"""Genera facturas sencillas de muestra (datos ficticios) y su ground truth.

    uv run --with reportlab python3 tools/make_facturas.py

Escribe samples/facturas/sencillas/*.pdf y ground_truth/facturas/*.json, con los mismos
campos que el workflow demo_facturas. Todas van dirigidas a IBERCLEAN PARTS, S.L. (el
cliente ficticio de las facturas anonimizadas), con las líneas agrupadas por albarán.
Casos: dos albaranes, tasa SIGAUS y portes, tasa NFU y descuento, base mal impresa (la
validación debe fallar), abono en negativo, dos páginas con «suma y sigue», escaneada y
torcida, y tres albaranes con tasa de gases fluorados.
"""
import json
import os
import random
import subprocess
import tempfile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_PDF = os.path.join(ROOT, "samples", "facturas", "sencillas")
OUT_GT = os.path.join(ROOT, "ground_truth", "facturas")
CLIENTE = ("IBERCLEAN PARTS, S.L.", "B99887766", "Av. de la Industria, 100", "28080 Getafe (Madrid)")

FACTURAS = [
    {
        "archivo": "muestra_01_dos_albaranes",
        "proveedor": ("RECAMBIOS FICTICIOS DEL LEVANTE, S.L.", "B00000017", "C/ Inventada, 12", "46000 Valencia"),
        "numero": "FL-2026/0412", "fecha": "2026-02-03",
        "albaranes": [
            ("AL-7781", "2026-01-27", "PED-160021", [
                ("FL-1001", "PASTILLA FRENO DELANTERA", 4, 18.50, 0),
                ("FL-1044", "DISCO FRENO VENTILADO 280MM", 2, 42.90, 0),
                ("FL-2210", "LIQUIDO FRENOS DOT4 1L", 6, 7.25, 0),
            ]),
            ("AL-7795", "2026-01-30", "PED-160058", [
                ("FL-3307", "ESCOBILLA LIMPIAPARABRISAS 600MM", 10, 6.80, 10),
                ("FL-3310", "ESCOBILLA TRASERA 350MM", 5, 5.40, 0),
            ]),
        ],
        "portes": 0.0, "idto": 0.0, "tasas": {},
    },
    {
        "archivo": "muestra_02_aceite_sigaus_portes",
        "proveedor": ("LUBRICANTES DE MUESTRA DEL NORTE, S.A.", "A00000025", "Pol. Ind. Ejemplo, nave 3", "48000 Bilbao"),
        "numero": "LN-26-00087", "fecha": "2026-02-05",
        "albaranes": [
            ("ALB-55120", "2026-02-04", "PED-161002", [
                ("LN-5W30-5", "ACEITE MOTOR 5W30 SINTETICO 5L", 12, 31.20, 5),
                ("LN-ATF-1", "ACEITE TRANSMISION ATF 1L", 8, 9.90, 0),
                ("LN-REF-5", "ANTICONGELANTE 50% 5L", 6, 11.40, 0),
            ]),
        ],
        "portes": 12.50, "idto": 0.0, "tasas": {"tsigaus": 4.76},
    },
    {
        "archivo": "muestra_03_neumaticos_nfu_descuento",
        "proveedor": ("NEUMATICOS EJEMPLO DEL SUR, S.L.", "B00000033", "Av. de los Ejemplos, 7", "41000 Sevilla"),
        "numero": "NS/2026/1199", "fecha": "2026-02-10",
        "albaranes": [
            ("NS-A-3301", "2026-02-06", "PED-161340", [
                ("NS-20555R16", "NEUMATICO 205/55 R16 91V", 8, 58.00, 0),
                ("NS-22545R17", "NEUMATICO 225/45 R17 94W", 4, 79.50, 0),
            ]),
            ("NS-A-3318", "2026-02-09", "PED-161340", [
                ("NS-VALV-01", "VALVULA CAUCHO TR414", 12, 0.95, 0),
            ]),
        ],
        "portes": 0.0, "idto": 15.00, "tasas": {"tnfu": 16.68},
    },
    {
        "archivo": "muestra_04_base_mal_impresa",
        "proveedor": ("FRENOS DE PRUEBA DEL CENTRO, S.L.", "B00000041", "C/ de la Prueba, 21", "45000 Toledo"),
        "numero": "FC-0000391", "fecha": "2026-02-12",
        "albaranes": [
            ("FC-ALB-901", "2026-02-11", "PED-161511", [
                ("FC-PZ-118", "ZAPATA FRENO TRASERA", 6, 24.10, 0),
                ("FC-KT-022", "KIT EMBRAGUE 3 PIEZAS", 1, 186.00, 0),
                ("FC-SN-410", "SENSOR ABS DELANTERO", 2, 33.75, 0),
            ]),
        ],
        "portes": 0.0, "idto": 0.0, "tasas": {},
        "error_base": 50.00,  # la base impresa lleva 50 € de más: la validación debe fallar
    },
    {
        "archivo": "muestra_05_abono",
        "proveedor": ("RECAMBIOS FICTICIOS DEL LEVANTE, S.L.", "B00000017", "C/ Inventada, 12", "46000 Valencia"),
        "numero": "FL-R-2026/0019", "fecha": "2026-02-14", "abono": True,
        "albaranes": [
            ("DEV-0233", "2026-02-13", "PED-160021", [
                ("FL-1044", "DEVOLUCION DISCO FRENO VENTILADO 280MM", 1, 42.90, 0),
                ("FL-2210", "DEVOLUCION LIQUIDO FRENOS DOT4 1L", 2, 7.25, 0),
            ]),
        ],
        "portes": 0.0, "idto": 0.0, "tasas": {},
    },
    {
        "archivo": "muestra_06_dos_paginas_suma_y_sigue",
        "proveedor": ("DISTRIBUCIONES DE PRUEBA DEL ESTE, S.L.", "B00000058", "Ctra. Ficticia, km 4", "08000 Barcelona"),
        "numero": "DE-2026-00733", "fecha": "2026-02-16",
        "albaranes": [
            ("DE-AL-2201", "2026-02-12", "PED-161700", [
                (f"DE-{100 + i:04d}", d, q, p, dto) for i, (d, q, p, dto) in enumerate([
                    ("FILTRO ACEITE", 10, 4.35, 0), ("FILTRO AIRE", 8, 7.90, 0), ("FILTRO HABITACULO", 8, 6.10, 0),
                    ("FILTRO COMBUSTIBLE", 6, 12.40, 5), ("BUJIA IRIDIO", 16, 8.95, 0), ("BOBINA ENCENDIDO", 2, 38.60, 0),
                    ("CORREA ACCESORIOS 6PK", 4, 14.20, 0), ("TENSOR CORREA", 2, 29.80, 0), ("BOMBA AGUA", 1, 64.50, 10),
                    ("TERMOSTATO", 3, 11.70, 0), ("MANGUITO RADIADOR", 5, 9.30, 0), ("TAPON RADIADOR", 6, 3.90, 0),
                    ("LAMPARA H7 12V", 20, 2.15, 0), ("LAMPARA H4 12V", 20, 2.40, 0), ("LAMPARA W5W", 50, 0.38, 0),
                    ("FUSIBLE 15A PACK 10", 10, 1.95, 0), ("RELE 4 PINES", 6, 4.80, 0), ("ESCOBILLA 550MM", 8, 6.20, 0),
                ])
            ]),
            ("DE-AL-2209", "2026-02-14", "PED-161700", [
                (f"DE-{300 + i:04d}", d, q, p, dto) for i, (d, q, p, dto) in enumerate([
                    ("AMORTIGUADOR DELANTERO", 2, 54.90, 0), ("AMORTIGUADOR TRASERO", 2, 46.30, 0),
                    ("COPELA AMORTIGUADOR", 2, 18.75, 0), ("BIELETA ESTABILIZADORA", 4, 12.60, 0),
                    ("ROTULA DIRECCION", 2, 16.40, 0), ("TERMINAL DIRECCION", 2, 13.95, 0),
                    ("SILENTBLOCK TRAPECIO", 4, 9.80, 0), ("BRAZO SUSPENSION", 1, 72.30, 5),
                    ("KIT DISTRIBUCION", 1, 118.00, 0), ("RETEN CIGUENAL", 2, 6.45, 0),
                    ("JUNTA TAPA BALANCINES", 1, 15.20, 0), ("TORNILLO RUEDA", 20, 0.85, 0),
                    ("TUERCA RUEDA", 20, 0.70, 0), ("SPRAY LIMPIA FRENOS 500ML", 12, 3.10, 0),
                    ("GRASA LITIO 400G", 4, 5.60, 0), ("BRIDA PLASTICO PACK 100", 5, 2.90, 0),
                    ("CINTA AISLANTE", 10, 0.95, 0), ("GUANTES NITRILO CAJA 100", 3, 7.40, 0),
                ])
            ]),
        ],
        "portes": 18.00, "idto": 0.0, "tasas": {},
    },
    {
        "archivo": "muestra_07_escaneada",
        "proveedor": ("NEUMATICOS EJEMPLO DEL SUR, S.L.", "B00000033", "Av. de los Ejemplos, 7", "41000 Sevilla"),
        "numero": "NS/2026/1243", "fecha": "2026-02-18", "escaneada": True,
        "albaranes": [
            ("NS-A-3402", "2026-02-17", "PED-161805", [
                ("NS-19565R15", "NEUMATICO 195/65 R15 91H", 6, 49.90, 0),
                ("NS-21560R16", "NEUMATICO 215/60 R16 99H", 4, 66.40, 5),
                ("NS-VALV-01", "VALVULA CAUCHO TR414", 10, 0.95, 0),
            ]),
        ],
        "portes": 0.0, "idto": 0.0, "tasas": {"tnfu": 13.90},
    },
    {
        "archivo": "muestra_08_tres_albaranes_gases",
        "proveedor": ("CLIMATIZACION FICTICIA DEL OESTE, S.L.", "B00000066", "C/ del Ejemplo, 88", "06000 Badajoz"),
        "numero": "CO-26/0158", "fecha": "2026-02-20",
        "albaranes": [
            ("CO-901", "2026-02-16", "PED-161900", [
                ("CO-R1234-5", "GAS REFRIGERANTE R1234YF 5KG", 1, 289.00, 0),
                ("CO-ACE-PAG", "ACEITE COMPRESOR PAG 46 250ML", 4, 11.80, 0),
            ]),
            ("CO-907", "2026-02-18", "PED-161900", [
                ("CO-FIL-DES", "FILTRO DESHIDRATADOR A/C", 3, 21.40, 0),
                ("CO-VAL-EXP", "VALVULA EXPANSION A/C", 1, 47.60, 10),
            ]),
            ("CO-913", "2026-02-19", "PED-161955", [
                ("CO-CND-01", "CONDENSADOR A/C", 1, 132.00, 0),
            ]),
        ],
        "portes": 9.50, "idto": 0.0, "tasas": {"tgases": 60.69},
    },
]

TASAS_ETIQUETA = {"tsigaus": "Tasa SIGAUS", "tnfu": "Ecotasa NFU", "tgases": "Tasa gases fluorados"}


def r2(x):
    return round(x + 1e-9, 2)


def eur(x):
    s = f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def signo(f):
    return -1 if f.get("abono") else 1


def lineas(f):
    out = []
    for alb, fecha, pedido, items in f["albaranes"]:
        for ref, desc, cant, precio, dto in items:
            out.append({"albaran": alb, "fechaalb": fecha, "npedido": pedido, "referencia": ref,
                        "descripcion": desc, "cantidad": float(cant), "precio": precio,
                        "importe": r2(signo(f) * cant * precio * (1 - dto / 100)), "dto1": float(dto)})
    return out


def totales(f):
    suma = r2(sum(l["importe"] for l in lineas(f)))
    tasas = sum(f["tasas"].values())
    base = r2(suma + f["portes"] + tasas - f["idto"])
    impresa = r2(base + f.get("error_base", 0.0))
    return base, impresa, r2(impresa * 0.21), r2(impresa * 1.21)


def cabecera(c, f, pagina, paginas):
    w, h = A4
    nombre, cif, dir1, dir2 = f["proveedor"]
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 15); c.drawString(20 * mm, h - 25 * mm, nombre)
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 31 * mm, f"{dir1} · {dir2}")
    c.drawString(20 * mm, h - 36 * mm, f"CIF: {cif}")
    titulo = "FACTURA RECTIFICATIVA (ABONO)" if f.get("abono") else "FACTURA"
    c.setFont("Helvetica-Bold", 14 if f.get("abono") else 20); c.drawRightString(w - 20 * mm, h - 25 * mm, titulo)
    c.setFont("Helvetica", 10)
    c.drawRightString(w - 20 * mm, h - 32 * mm, f"Nº {f['numero']}")
    y, m, d = f["fecha"].split("-")
    c.drawRightString(w - 20 * mm, h - 37 * mm, f"Fecha: {d}/{m}/{y}")
    c.setFont("Helvetica", 8); c.drawRightString(w - 20 * mm, h - 42 * mm, f"Página {pagina} de {paginas}")
    c.setStrokeColor(colors.HexColor("#999999")); c.rect(110 * mm, h - 70 * mm, 80 * mm, 24 * mm)
    c.setFont("Helvetica", 8); c.drawString(113 * mm, h - 51 * mm, "CLIENTE")
    c.setFont("Helvetica-Bold", 10); c.drawString(113 * mm, h - 56 * mm, CLIENTE[0])
    c.setFont("Helvetica", 9)
    c.drawString(113 * mm, h - 60.5 * mm, CLIENTE[2]); c.drawString(113 * mm, h - 64.5 * mm, CLIENTE[3])
    c.drawString(113 * mm, h - 68.5 * mm, f"CIF: {CLIENTE[1]}")
    y0 = h - 82 * mm
    c.setFillColor(colors.HexColor("#E8ECF2")); c.rect(18 * mm, y0 - 2 * mm, 174 * mm, 7 * mm, fill=1, stroke=0)
    c.setFillColor(colors.black); c.setFont("Helvetica-Bold", 8.5)
    for x, t in zip(COLS, ["Referencia", "Descripción", "Cant.", "Precio", "Dto %"]):
        c.drawString(x * mm, y0, t)
    c.drawRightString(190 * mm, y0, "Importe")
    return y0 - 8 * mm


def pie(c, f):
    nombre, cif = f["proveedor"][:2]
    c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#666666"))
    c.drawString(20 * mm, 22 * mm, "Forma de pago: transferencia a 60 días.")
    c.drawString(20 * mm, 17 * mm, f"{nombre} · CIF {cif} · Inscrita en un registro mercantil ficticio.")
    c.setFillColor(colors.HexColor("#B42318"))
    c.drawString(20 * mm, 12 * mm, "DOCUMENTO DE MUESTRA PARA FORMACIÓN · TODOS LOS DATOS SON FICTICIOS")
    c.setFillColor(colors.black)


COLS = [20, 45, 120, 140, 160, 175]  # mm: ref, descripción, cant, precio, dto, importe (derecha a 190)
LIMITE = 75 * mm  # por debajo, «Suma y sigue» y página nueva


def pinta(f, path):
    # Primera pasada para contar páginas; la segunda pinta.
    for paso in ("contar", "pintar"):
        c = canvas.Canvas(path if paso == "pintar" else os.devnull, pagesize=A4)
        pagina = 1
        paginas = pinta.paginas if paso == "pintar" else 1
        yy = cabecera(c, f, pagina, paginas)
        acumulado = 0.0
        for alb, fecha, pedido, items in f["albaranes"]:
            ya, ma, da = fecha.split("-")
            c.setFont("Helvetica-Oblique", 8.5)
            c.drawString(20 * mm, yy, f"Albarán {alb} de {da}/{ma}/{ya} · Su pedido {pedido}")
            yy -= 6 * mm
            for ref, desc, cant, precio, dto in items:
                if yy < LIMITE:
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(COLS[1] * mm, yy, "SUMA Y SIGUE"); c.drawRightString(190 * mm, yy, eur(acumulado))
                    pie(c, f); c.showPage(); pagina += 1
                    yy = cabecera(c, f, pagina, paginas)
                    c.setFont("Helvetica-Bold", 9)
                    c.drawString(COLS[1] * mm, yy, "SUMA ANTERIOR"); c.drawRightString(190 * mm, yy, eur(acumulado))
                    yy -= 7 * mm
                imp = r2(signo(f) * cant * precio * (1 - dto / 100))
                acumulado = r2(acumulado + imp)
                c.setFont("Helvetica", 9)
                c.drawString(COLS[0] * mm, yy, ref); c.drawString(COLS[1] * mm, yy, desc)
                c.drawRightString((COLS[2] + 12) * mm, yy, str(cant))
                c.drawRightString((COLS[3] + 14) * mm, yy, eur(precio))
                c.drawRightString((COLS[4] + 9) * mm, yy, eur(dto) if dto else "")
                c.drawRightString(190 * mm, yy, eur(imp))
                yy -= 5.5 * mm
            yy -= 2 * mm
        if yy < LIMITE + 20 * mm:
            pie(c, f); c.showPage(); pagina += 1
            yy = cabecera(c, f, pagina, paginas)
        base, impresa, iva, total = totales(f)
        filas = [("Suma líneas", acumulado)]
        if f["portes"]: filas.append(("Portes", f["portes"]))
        for k, v in f["tasas"].items(): filas.append((TASAS_ETIQUETA[k], v))
        if f["idto"]: filas.append(("Descuento pronto pago", -f["idto"]))
        filas += [("BASE IMPONIBLE", impresa), ("IVA 21%", iva), ("TOTAL FACTURA", total)]
        ty = yy - 6 * mm
        c.line(120 * mm, ty + 5 * mm, 190 * mm, ty + 5 * mm)
        for label, val in filas:
            bold = label in ("BASE IMPONIBLE", "TOTAL FACTURA")
            c.setFont("Helvetica-Bold" if bold else "Helvetica", 10 if bold else 9)
            c.drawString(122 * mm, ty, label); c.drawRightString(190 * mm, ty, f"{eur(val)} €")
            ty -= 6 * mm
        pie(c, f)
        c.save()
        pinta.paginas = pagina
    if f.get("escaneada"):
        escanea(path)


def escanea(path):
    """Convierte el PDF en una imagen de escáner: gris, algo torcida, con ruido y un poco borrosa."""
    from PIL import Image, ImageFilter
    random.seed(7)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "150", "-gray", "-png", path, os.path.join(tmp, "p")], check=True)
        paginas = []
        for png in sorted(os.listdir(tmp)):
            img = Image.open(os.path.join(tmp, png)).convert("L")
            img = img.rotate(1.3, resample=Image.BICUBIC, expand=False, fillcolor=245)
            img = img.filter(ImageFilter.GaussianBlur(0.6))
            px = img.load()
            for _ in range(img.width * img.height // 60):
                x, y = random.randrange(img.width), random.randrange(img.height)
                px[x, y] = random.choice((90, 160, 200))
            paginas.append(img.point(lambda v: min(255, int(v * 0.93 + 12))))
        paginas[0].save(path, save_all=True, append_images=paginas[1:], resolution=150)


def ground_truth(f):
    base, impresa, iva, total = totales(f)
    fields = {"total": total, "ibruto": impresa, "portes": f["portes"], "idto": f["idto"],
              "tnfu": f["tasas"].get("tnfu", 0.0), "tsigaus": f["tasas"].get("tsigaus", 0.0),
              "tgases": f["tasas"].get("tgases", 0.0), "lineas": lineas(f)}
    gt = {"file": f["archivo"] + ".pdf", "proveedor": f["proveedor"][0], "fields": fields,
          "validacion_esperada": "fail" if f.get("error_base") else "pass"}
    if f.get("error_base"):
        gt["notas"] = {"ibruto": f"La base impresa ({eur(impresa)} €) lleva {eur(f['error_base'])} € de más: "
                                 f"las líneas suman {eur(base)} €. La validación de cuadre debe fallar."}
    return gt


def main():
    os.makedirs(OUT_PDF, exist_ok=True); os.makedirs(OUT_GT, exist_ok=True)
    for f in FACTURAS:
        pinta(f, os.path.join(OUT_PDF, f["archivo"] + ".pdf"))
        with open(os.path.join(OUT_GT, f["archivo"] + ".json"), "w") as fh:
            json.dump(ground_truth(f), fh, ensure_ascii=False, indent=2)
        base, impresa, iva, total = totales(f)
        print(f"{f['archivo']}: {len(lineas(f))} líneas, base {impresa}, total {total}")


if __name__ == "__main__":
    main()
