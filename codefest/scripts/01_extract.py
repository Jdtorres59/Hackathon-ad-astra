#!/usr/bin/env python
"""Extrae el texto de los 1.826 documentos del corpus a data/docs.jsonl.

Uso:
    python scripts/01_extract.py [--workers N] [--limit N] [--no-ocr] [--only FORMATO]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.extract import extract_document  # noqa: E402
from codefest.inventory import DocRecord, load_inventory  # noqa: E402

_ALLOW_OCR = True


def _init(allow_ocr: bool) -> None:
    global _ALLOW_OCR
    _ALLOW_OCR = allow_ocr
    # Cada worker es un proceso; evita que las librerías nativas se peleen por hilos
    os.environ.setdefault("OMP_NUM_THREADS", "1")


def _work(doc: DocRecord) -> dict:
    return extract_document(doc, allow_ocr=_ALLOW_OCR)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-ocr", action="store_true")
    parser.add_argument("--only", default=None, help="procesar solo un formato (pdf, json, csv...)")
    parser.add_argument("--out", default=str(config.DOCS_JSONL))
    args = parser.parse_args()

    config.ensure_dirs()
    docs = load_inventory()
    if args.only:
        docs = [d for d in docs if d.formato == args.only]
    if args.limit:
        docs = docs[: args.limit]

    # Los PDFs grandes primero: mejor reparto de carga entre workers
    docs.sort(key=lambda d: -(d.path.stat().st_size if d.path.exists() else 0))

    print(f"Extrayendo {len(docs)} documentos con {args.workers} procesos (OCR={'no' if args.no_ocr else 'sí'})")
    t0 = time.time()
    stats: Counter[str] = Counter()
    errores: list[tuple[str, str]] = []
    vacios: list[str] = []
    n_ocr_pages = 0

    with open(args.out, "w", encoding="utf-8") as out, mp.Pool(
        args.workers, initializer=_init, initargs=(not args.no_ocr,)
    ) as pool:
        for i, rec in enumerate(pool.imap_unordered(_work, docs, chunksize=1), start=1):
            out.write(json.dumps(rec, ensure_ascii=False) + "\n")
            stats[rec["formato"]] += 1
            n_ocr_pages += rec.get("n_ocr_pages", 0)
            if rec["error"]:
                errores.append((rec["doc_id"], rec["error"]))
            elif rec["n_chars"] < 200:
                vacios.append(f"{rec['doc_id']} ({rec['formato']}, {rec['n_chars']}c)")
            if i % 50 == 0 or i == len(docs):
                dt = time.time() - t0
                print(f"  {i}/{len(docs)}  {dt:6.0f}s  ({i / dt:.1f} doc/s)  ocr_pags={n_ocr_pages}", flush=True)

    print(f"\nListo en {time.time() - t0:.0f}s -> {args.out}")
    print(f"Por formato: {dict(stats)}")
    print(f"Páginas con OCR: {n_ocr_pages}")
    print(f"Documentos con error: {len(errores)}")
    for doc_id, err in errores[:15]:
        print(f"   ERROR {doc_id}: {err[:120]}")
    print(f"Documentos con <200 caracteres: {len(vacios)}")
    for v in vacios[:25]:
        print(f"   VACIO {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
