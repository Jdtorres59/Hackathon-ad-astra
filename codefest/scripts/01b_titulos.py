#!/usr/bin/env python
"""Sanea los títulos de data/docs.jsonl in situ.

El título se antepone al texto de cada fragmento al codificarlo, así que un
título basura contamina todos los vectores de ese documento. Se ejecuta después
de 01_extract.py y antes de 02_chunk.py.

Uso:
    python scripts/01b_titulos.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.extract.titulos import es_titulo_malo, resolver_titulo  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--docs", default=str(config.DOCS_JSONL))
    args = parser.parse_args()

    with open(args.docs, encoding="utf-8") as fh:
        docs = [json.loads(line) for line in fh if line.strip()]

    origenes: Counter[str] = Counter()
    cambios: list[tuple[str, str, str, str]] = []

    for d in docs:
        antes = d.get("titulo", "")
        # Los JSON traen título propio del scraping y suelen ser buenos
        if d["formato"] == "json" and antes and not es_titulo_malo(antes):
            origenes["json_ok"] += 1
            continue
        nuevo, origen = resolver_titulo(antes, d.get("texto", ""), d["fuente"], d["formato"])
        origenes[origen] += 1
        if nuevo != antes:
            cambios.append((d["doc_id"], d["formato"], antes, nuevo))
            d["titulo"] = nuevo

    print(f"Documentos: {len(docs)}")
    print(f"Origen del título: {dict(origenes)}")
    print(f"Títulos cambiados: {len(cambios)}")

    random.seed(3)
    print("\n--- muestra de cambios ---")
    for doc_id, fmt, antes, nuevo in random.sample(cambios, min(20, len(cambios))):
        print(f"  {doc_id:16} [{fmt}]")
        print(f"     antes: {antes[:95]!r}")
        print(f"     ahora: {nuevo[:95]!r}")

    restantes = [d for d in docs if es_titulo_malo(d.get("titulo", ""))]
    print(f"\nTítulos que siguen siendo dudosos: {len(restantes)}")
    for d in restantes[:8]:
        print(f"  {d['doc_id']:16} {d['titulo'][:80]!r}")

    if args.dry_run:
        print("\n(dry-run: no se escribió nada)")
        return 0

    with open(args.docs, "w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"\nEscrito -> {args.docs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
