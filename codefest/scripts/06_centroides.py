#!/usr/bin/env python
"""Calcula los centroides por fenómeno de cada encoder.

Son tres vectores por encoder (uno por fenómeno temático) que el módulo de
recuperación usa como prior suave: si la consulta se parece mucho al centroide
del Fenómeno 2, los fragmentos de ese fenómeno reciben un pequeño impulso.

Es un post-filtro sobre metadata, explícitamente permitido por la Sección 8.7, y
nunca descarta candidatos: solo reordena.

Uso:
    python scripts/06_centroides.py [--encoders granite,bge_m3,e5_large]
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.index_build import encoder_dir  # noqa: E402
from codefest.retrieve import CENTROIDS_FILE, DOC_CENTROIDS_FILE, DOC_IDS_FILE  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoders", default=",".join(e["slug"] for e in config.ENCODERS))
    args = parser.parse_args()

    for slug in [s.strip() for s in args.encoders.split(",") if s.strip()]:
        folder = encoder_dir(slug)
        vec_path = config.VECTORS_DIR / f"{slug}.npy"
        if not folder.exists() or not vec_path.exists():
            print(f"  {slug}: falta el índice o los vectores, se omite")
            continue

        vectors = np.load(vec_path)
        with open(folder / "metadata.jsonl", encoding="utf-8") as fh:
            meta = [json.loads(line) for line in fh if line.strip()]
        fenomenos = np.array([m["fenomeno"] for m in meta])

        if len(fenomenos) != vectors.shape[0]:
            print(f"  {slug}: desalineado ({len(fenomenos)} vs {vectors.shape[0]}), se omite")
            continue

        centroides = np.zeros((3, vectors.shape[1]), dtype=np.float32)
        for f in (1, 2, 3):
            sel = vectors[fenomenos == f]
            if len(sel) == 0:
                continue
            c = sel.mean(axis=0)
            centroides[f - 1] = c / (np.linalg.norm(c) or 1.0)

        np.save(folder / CENTROIDS_FILE, centroides)
        sep = centroides @ centroides.T
        print(f"  {slug}: centroides guardados. Similitud entre fenómenos: "
              f"F1-F2={sep[0, 1]:.3f} F1-F3={sep[0, 2]:.3f} F2-F3={sep[1, 2]:.3f}")

        centroides_documento(slug, folder, vectors, meta)
    return 0


def centroides_documento(slug, folder, vectors, meta) -> None:
    """Un vector por documento, para detectar copias y traducciones.

    El corpus repite documentos bajo nombres distintos y traducidos a varios
    idiomas. Comparar el mejor fragmento no basta: dos ediciones del mismo
    informe pueden responder con secciones distintas. El centroide del documento
    entero sí las identifica, y en un encoder multilingüe una traducción cae
    prácticamente sobre su original.
    """
    import json as _json
    from collections import defaultdict

    filas = defaultdict(list)
    for i, m in enumerate(meta):
        filas[m["doc_id"]].append(i)

    doc_ids = sorted(filas)
    cents = np.zeros((len(doc_ids), vectors.shape[1]), dtype=np.float32)
    for k, doc_id in enumerate(doc_ids):
        c = vectors[filas[doc_id]].mean(axis=0)
        cents[k] = c / (np.linalg.norm(c) or 1.0)

    np.save(folder / DOC_CENTROIDS_FILE, cents)
    with open(folder / DOC_IDS_FILE, "w", encoding="utf-8") as fh:
        _json.dump(doc_ids, fh)

    sim = cents @ cents.T
    np.fill_diagonal(sim, 0.0)
    casi = int((sim > 0.98).sum() // 2)
    print(f"  {slug}: {len(doc_ids)} centroides de documento, {casi} pares con coseno > 0,98")


if __name__ == "__main__":
    raise SystemExit(main())
