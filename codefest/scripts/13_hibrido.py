#!/usr/bin/env python
"""¿Fusionar BM25 con los índices densos mejora, o solo mueve el problema?

El diagnóstico dejó un empate incómodo: BM25 gana en las sondas de solapamiento
léxico y el sistema denso gana en la de títulos, que es la que se parece a las
consultas reales. La respuesta estándar en recuperación es fusionar los dos, y
esto lo comprueba con las mismas sondas antes de tocar la entrega.

La fusión es la misma RRF de la Sección 8.4 que ya usan los tres encoders: la
lista de BM25 entra como una más, con su peso.

Uso:
    python scripts/13_hibrido.py [--probe-n 200]
"""

from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from collections import defaultdict  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.retrieve import Retriever  # noqa: E402

sys.path.insert(0, os.path.dirname(__file__))
from importlib import import_module  # noqa: E402

_diag = import_module("12_diagnostico")


class Hibrido:
    """RRF entre la lista fusionada densa y la lista léxica de BM25."""

    def __init__(self, denso, bm25, peso_bm25: float = 1.0, k0: int = None):
        self.denso = denso
        self.bm25 = bm25
        self.peso = peso_bm25
        self.k0 = k0 or config.RRF_K0
        self.meta = denso.meta

    def search(self, query: str, *, n_documents=None, n_fragments=None, **kw) -> dict:
        n_documents = n_documents or config.N_DOCUMENTS_OUT
        n_fragments = n_fragments or config.N_FRAGMENTS_OUT

        # Se piden más candidatos de los que se van a devolver: la fusión solo
        # puede reordenar lo que le llega, y con diez de cada lado no hay margen.
        d = self.denso.search(query, n_fragments=60, max_per_doc=99, **kw)
        b = self.bm25.search(query, n_fragments=60, max_per_doc=99)

        puntos: defaultdict[str, float] = defaultdict(float)
        info: dict[str, dict] = {}
        for lista, peso in ((d["fragments"], 1.0), (b["fragments"], self.peso)):
            for rango, f in enumerate(lista, start=1):
                puntos[f["chunk_id"]] += peso / (self.k0 + rango)
                info.setdefault(f["chunk_id"], f)

        orden = sorted(puntos.items(), key=lambda kv: -kv[1])

        frags, por_doc = [], defaultdict(int)
        for cid, _ in orden:
            f = info[cid]
            if por_doc[f["doc_id"]] >= config.MAX_CHUNKS_PER_DOC:
                continue
            por_doc[f["doc_id"]] += 1
            frags.append({**f, "rank": len(frags) + 1})
            if len(frags) >= n_fragments:
                break

        mejor: dict[str, float] = {}
        for cid, p in orden:
            doc = info[cid]["doc_id"]
            mejor[doc] = max(mejor.get(doc, 0.0), p)
        top = sorted(mejor.items(), key=lambda kv: -kv[1])[:n_documents]

        return {"documents": [{"doc_id": x, "score": s} for x, s in top], "fragments": frags}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-n", type=int, default=200)
    args = parser.parse_args()

    config.ensure_dirs()
    slugs = [e["slug"] for e in config.ENCODERS
             if (config.BASE_VECTORIAL_DIR / f"encoder_{e['slug']}" / "index.faiss").exists()]

    denso = Retriever(slugs=slugs, use_graph=False)
    from baseline_bm25 import BM25Retriever  # en scripts/, fuera de la entrega
    print("  construyendo BM25...", flush=True)
    bm = BM25Retriever(denso.meta)

    filas = []
    print(f"\n=== Híbrido denso+BM25 ({args.probe_n} pruebas) ===")
    for peso in (0.0, 0.5, 1.0, 1.5):
        nombre = "solo denso" if peso == 0 else f"híbrido w={peso}"
        filas.append(_diag.evaluar(nombre, Hibrido(denso, bm, peso_bm25=peso), args.probe_n))

    salida = config.REPORTS_DIR / "hibrido.json"
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(filas, fh, ensure_ascii=False, indent=1)
    print(f"\n-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
