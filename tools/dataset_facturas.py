#!/usr/bin/env python3
"""Sube las facturas de muestra con su ground truth al dataset de un workflow y lanza la evaluación.

    export ANYFORMAT_API_KEY=af_...
    uv run --python 3.12 --with anyformat python3 tools/dataset_facturas.py dataset <workflow_id>
    uv run --python 3.12 --with anyformat python3 tools/dataset_facturas.py eval <workflow_id>

El ground truth sale de ground_truth/facturas/<pdf>.json y se manda en el formato del
dataset: cada valor como texto (importes con dos decimales) y las líneas como lista de filas.
Después: Health → Datasets / Evaluations / Optimizer en la app.
"""
import json
import os
import sys
import time
from pathlib import Path

from anyformat.sdk import Client

ROOT = Path(__file__).resolve().parent.parent
PDFS = ROOT / "samples" / "facturas" / "sencillas"
GT = ROOT / "ground_truth" / "facturas"
FLOATS = {"total", "ibruto", "portes", "idto", "tnfu", "tsigaus", "tgases", "cantidad", "precio", "importe", "dto1"}


def texto(key, value):
    if value is None:
        return None
    if key in FLOATS:
        return f"{float(value):.2f}"
    return str(value)


def api_ground_truth(fields):
    out = {}
    for key, value in fields.items():
        if key == "lineas":
            out[key] = [{k: texto(k, v) for k, v in row.items()} for row in value]
        else:
            out[key] = texto(key, value)
    return out


def client():
    key = os.environ.get("ANYFORMAT_API_KEY")
    if not key:
        sys.exit("Falta ANYFORMAT_API_KEY")
    return Client(api_key=key, base_url="https://api.anyformat.ai", timeout=120)


def cmd_dataset(workflow_id):
    c = client()
    for pdf in sorted(PDFS.glob("*.pdf")):
        truth = json.loads((GT / f"{pdf.stem}.json").read_text())
        c.upload_to_dataset(workflow_id, pdf, ground_truth=api_ground_truth(truth["fields"]), on_conflict="rename")
        print(f"+ {pdf.name}", flush=True)
        time.sleep(1.5)


def cmd_eval(workflow_id):
    c = client()
    eval_id = c.launch_eval(workflow_id).eval_id
    print(f"Evaluación lanzada: https://app.anyformat.ai/workflows/{workflow_id}/evals/{eval_id}", flush=True)
    while True:
        e = c.get_eval(workflow_id, eval_id)
        if e.status in {"processed", "error"}:
            acc = f"{e.accuracy:.1%}" if e.accuracy is not None else "-"
            print(f"{e.status}: accuracy={acc} matched={e.matched} mismatched={e.mismatched}")
            return
        time.sleep(15)


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in {"dataset", "eval"}:
        sys.exit(__doc__)
    {"dataset": cmd_dataset, "eval": cmd_eval}[sys.argv[1]](sys.argv[2])
