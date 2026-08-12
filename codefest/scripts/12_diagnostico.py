#!/usr/bin/env python
"""Diagnóstico previo a la entrega: regresión, competitividad y aporte del grafo.

Pasa exactamente las mismas sondas a tres sistemas para que los números sean
comparables entre sí:

  denso+grafo   la configuración que hoy está en la entrega
  denso         la misma sin la lista del grafo en el RRF
  BM25          baseline léxico, sin ningún encoder

Responde a dos preguntas que no se pueden contestar de otra forma sin el ground
truth: si la parte densa aporta algo sobre una búsqueda por palabras clave, y si
el grafo aporta o resta.

Uso:
    python scripts/12_diagnostico.py [--probe-n 200]
"""

from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.evaluate import (  # noqa: E402
    f1_at_3,
    known_item_probe,
    load_mini_gold,
    match_docs_by_filename,
    ndcg_at_k,
    title_probe,
    token_recall,
)
from codefest.retrieve import Retriever  # noqa: E402


def mini_gold(sistema) -> dict:
    """F1@3 y NDCG@10 sobre las 8 preguntas etiquetadas del corpus."""
    gold = load_mini_gold()
    fuentes = {m["doc_id"]: m["fuente"] for m in sistema.meta}
    f1s, ndcgs, cobs = [], [], []
    for g in gold:
        relevantes = match_docs_by_filename(g["archivos"], fuentes)
        if not relevantes:
            continue
        hits = sistema.search(g["pregunta"])
        textos = [f["text"] for f in hits["fragments"]]
        f1s.append(f1_at_3([d["doc_id"] for d in hits["documents"]], relevantes))
        rel = [max((token_recall(gf, t) for gf in g["fragmentos"]), default=0.0)
               for t in textos[:10]]
        ndcgs.append(ndcg_at_k(rel, [1.0] * min(len(g["fragmentos"]), 10), k=10))
        cobs.extend(max((token_recall(gf, t) for t in textos), default=0.0)
                    for gf in g["fragmentos"])
    n = max(len(f1s), 1)
    return {
        "f1@3": sum(f1s) / n,
        "ndcg@10": sum(ndcgs) / max(len(ndcgs), 1),
        "cobertura": sum(cobs) / max(len(cobs), 1),
    }


def evaluar(nombre: str, sistema, probe_n: int) -> dict:
    t0 = time.time()
    ki = known_item_probe(sistema, n=probe_n)
    ti = title_probe(sistema, n=probe_n)
    mg = mini_gold(sistema)
    fila = {
        "sistema": nombre,
        "known_item_recall@3": round(ki["recall@3_doc"], 4),
        "known_item_mrr": round(ki["mrr_doc"], 4),
        "known_item_ndcg@10": round(ki["ndcg@10_frag"], 4),
        "titulos_recall@3": round(ti["recall@3_doc"], 4),
        "minigold_f1@3": round(mg["f1@3"], 4),
        "minigold_ndcg@10": round(mg["ndcg@10"], 4),
        "minigold_cobertura": round(mg["cobertura"], 4),
        "segundos": round(time.time() - t0, 1),
    }
    print(f"  {nombre:14} known={fila['known_item_recall@3']:.3f} "
          f"ndcg={fila['known_item_ndcg@10']:.3f} tit={fila['titulos_recall@3']:.3f} "
          f"gold_f1={fila['minigold_f1@3']:.3f} gold_ndcg={fila['minigold_ndcg@10']:.3f} "
          f"({fila['segundos']}s)", flush=True)
    return fila


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-n", type=int, default=200)
    parser.add_argument("--salida", default=None)
    args = parser.parse_args()

    config.ensure_dirs()
    slugs = [e["slug"] for e in config.ENCODERS
             if (config.BASE_VECTORIAL_DIR / f"encoder_{e['slug']}" / "index.faiss").exists()]
    filas = []

    print(f"\n=== Sondas ({args.probe_n} pruebas cada una) ===")

    r_grafo = Retriever(slugs=slugs, use_graph=True)
    filas.append(evaluar("denso+grafo", r_grafo, args.probe_n))
    meta = r_grafo.meta
    del r_grafo

    r = Retriever(slugs=slugs, use_graph=False)
    filas.append(evaluar("denso", r, args.probe_n))
    del r

    print("  construyendo el índice BM25...", flush=True)
    # Vive en scripts/ y no en src/codefest/ a propósito: `08_empaquetar.py`
    # copia la librería entera dentro de la entrega, y un BM25 ahí dentro daría
    # a entender que la recuperación usa un método que la Sección 8.3 excluye.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from baseline_bm25 import BM25Retriever
    t0 = time.time()
    bm = BM25Retriever(meta)
    print(f"  índice BM25 listo en {time.time() - t0:.0f}s "
          f"({len(bm.vocab):,} términos)", flush=True)
    filas.append(evaluar("BM25", bm, args.probe_n))

    salida = args.salida or (config.REPORTS_DIR / "diagnostico.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)
    print(f"\n-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
