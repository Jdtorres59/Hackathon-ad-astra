#!/usr/bin/env python
"""Fragmenta data/docs.jsonl en data/chunks.jsonl.

Uso:
    python scripts/02_chunk.py [--workers N] [--docs RUTA] [--out RUTA]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import re
import statistics
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.chunking import chunk_document  # noqa: E402

_FIN_ORACION = re.compile(r"[.!?…»\"')\]][\d\s]*$")  # tolera el número de nota al pie
_INICIO_ORACION = re.compile(r"^[¿¡\"'«(\[\d•\-A-ZÁÉÍÓÚÑÜ]")


def _work(doc: dict) -> list[dict]:
    try:
        return chunk_document(doc)
    except Exception as exc:
        print(f"  ERROR fragmentando {doc.get('doc_id')}: {type(exc).__name__}: {exc}", flush=True)
        return []


def _iter_docs(path: str):
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    parser.add_argument("--docs", default=str(config.DOCS_JSONL))
    parser.add_argument("--out", default=str(config.CHUNKS_JSONL))
    args = parser.parse_args()

    config.ensure_dirs()
    docs = list(_iter_docs(args.docs))
    print(f"Fragmentando {len(docs)} documentos con {args.workers} procesos")

    t0 = time.time()
    total = 0
    forzados = 0
    cierran = 0
    abren = 0
    sin_chunks: list[str] = []
    tamanos: list[int] = []
    por_formato: Counter[str] = Counter()

    with open(args.out, "w", encoding="utf-8") as out, mp.Pool(args.workers) as pool:
        for i, chunks in enumerate(pool.imap(_work, docs, chunksize=4), start=1):
            if not chunks:
                sin_chunks.append(docs[i - 1]["doc_id"])
            for c in chunks:
                out.write(json.dumps(c, ensure_ascii=False) + "\n")
                tamanos.append(c["n_palabras"])
                por_formato[c["formato"]] += 1
                forzados += int(c["corte_forzado"])
                t = c["texto"].strip()
                cierran += bool(_FIN_ORACION.search(t))
                abren += bool(_INICIO_ORACION.match(t))
            total += len(chunks)
            if i % 200 == 0 or i == len(docs):
                print(f"  {i}/{len(docs)}  fragmentos={total}  {time.time() - t0:.0f}s", flush=True)

    print(f"\nListo en {time.time() - t0:.0f}s -> {args.out}")
    print(f"Fragmentos totales: {total}")
    if tamanos:
        print(
            f"Palabras por fragmento: media={statistics.mean(tamanos):.0f} "
            f"mediana={statistics.median(tamanos):.0f} "
            f"min={min(tamanos)} max={max(tamanos)} "
            f">240={sum(1 for t in tamanos if t > 240)} "
            f">250={sum(1 for t in tamanos if t > 250)}"
        )
    print(f"Fragmentos por formato: {dict(por_formato)}")
    print(f"Fragmentos con corte forzado (tabla/OCR sin puntuación): {forzados}")

    # Requisito obligatorio de la Sección 3.3: ningún fragmento puede cortar una
    # oración. Se comprueba aquí para que una regresión no pase inadvertida.
    print(
        f"Completitud lingüística: {cierran}/{total} terminan en signo de cierre "
        f"({cierran / max(total, 1):.1%}); {abren}/{total} empiezan en inicio de oración "
        f"({abren / max(total, 1):.1%})"
    )
    print(f"Documentos sin ningún fragmento: {len(sin_chunks)}")
    for d in sin_chunks[:20]:
        print(f"   SIN FRAGMENTOS {d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
