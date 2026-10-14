#!/usr/bin/env python3
"""Ejecuta los PDFs de samples/calas en un workflow y guarda cada run para puntuarlo.

    export ANYFORMAT_API_KEY=af_...
    python3 tools/run_calas.py <workflow_id> results/calas/v2 [pdf ...]
    python3 tools/score_calas.py results/calas/v2

Guarda la respuesta de GET /v3/runs/{id}/ como <dir>/<nombre del PDF sin .pdf>.json.
Solo usa la biblioteca estándar y curl.
"""
import concurrent.futures
import glob
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.anyformat.ai/v3"
KEY = os.environ.get("ANYFORMAT_API_KEY")


def curl(*args):
    proc = subprocess.run(["curl", "-s", "-H", f"Authorization: Bearer {KEY}", *args],
                          capture_output=True, text=True)
    if proc.returncode:
        raise RuntimeError(f"curl salió con código {proc.returncode}")
    return json.loads(proc.stdout)


def run_one(workflow_id, pdf, out_dir):
    name = os.path.splitext(os.path.basename(pdf))[0]
    sub = curl("-X", "POST", "-F", f'file=@"{pdf}"', f"{API}/workflows/{workflow_id}/upload/run/?on_conflict=rename")
    run_id = sub.get("run_id")
    if not run_id:
        return name, f"error al subir: {sub}"
    started = time.time()
    while time.time() - started < 900:
        run = curl(f"{API}/runs/{run_id}/")
        if run.get("status") in ("processed", "failed", "error"):
            with open(os.path.join(out_dir, f"{name}.json"), "w") as fh:
                json.dump(run, fh, ensure_ascii=False, indent=2)
            return name, f"{run['status']} en {time.time() - started:.0f} s ({run_id})"
        time.sleep(5)
    return name, f"sin terminar tras 15 min ({run_id})"


def main():
    if not KEY or len(sys.argv) < 3:
        sys.exit(__doc__)
    workflow_id, out_dir = sys.argv[1], sys.argv[2]
    pdfs = sys.argv[3:] or sorted(glob.glob(os.path.join(ROOT, "samples", "calas", "*.pdf")))
    os.makedirs(out_dir, exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        for name, status in pool.map(lambda p: run_one(workflow_id, p, out_dir), pdfs):
            print(f"{name}: {status}", flush=True)


if __name__ == "__main__":
    main()
