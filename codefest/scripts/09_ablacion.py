#!/usr/bin/env python
"""Ablaciones sobre las decisiones de recuperación.

Barre encoders individuales frente a la fusión, los tres métodos de combinación
de la Sección 8.4, el tope de diversidad por documento y el prior por fenómeno.
Los resultados alimentan la tabla de ablación del informe técnico.

Uso:
    python scripts/09_ablacion.py [--probe-n 150]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.evaluate import (  # noqa: E402
    f1_at_3,
    known_item_probe,
    load_mini_gold,
    match_docs_by_filename,
    title_probe,
    token_recall,
)
from codefest.retrieve import Retriever  # noqa: E402


def puntuar(retriever, gold, fusion="rrf", max_per_doc=None, prior=True, expand=True,
            expand_target=None, doc_tail_weight=None, doc_tail_n=None,
            doc_dedup_cos=None, consultas=None) -> dict:
    fuentes = {m["doc_id"]: m["fuente"] for m in retriever.meta}
    f1s, cobs, palabras = [], [], []
    for g in gold:
        relevantes = match_docs_by_filename(g["archivos"], fuentes)
        if not relevantes:
            continue
        hits = retriever.search(
            g["pregunta"], fusion_method=fusion, max_per_doc=max_per_doc,
            use_fenomeno_prior=prior, expand=expand, expand_target=expand_target,
            doc_tail_weight=doc_tail_weight, doc_tail_n=doc_tail_n,
            doc_dedup_cos=doc_dedup_cos,
        )
        docs = [d["doc_id"] for d in hits["documents"]]
        textos = [f["text"] for f in hits["fragments"]]
        f1s.append(f1_at_3(docs, relevantes))
        palabras.extend(len(t.split()) for t in textos)
        for gf in g["fragmentos"]:
            cobs.append(max((token_recall(gf, t) for t in textos), default=0.0))
    return {
        "f1@3": round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
        "cobertura": round(sum(cobs) / len(cobs), 4) if cobs else 0.0,
        "palabras": round(sum(palabras) / len(palabras)) if palabras else 0,
        "n": len(f1s),
    }


def duplicados_en_top3(retriever, consultas, referencia=None, umbral: float = 0.93, **kw) -> float:
    """Fracción de las 50 consultas reales con dos documentos casi iguales en el top-3.

    El mini gold tiene 8 preguntas y no distingue configuraciones; esta métrica sí,
    porque se calcula sobre las 50 consultas que de verdad se van a evaluar. Mide
    desperdicio: un hueco del top-3 ocupado por contenido ya presente en otro.
    """
    import numpy as np

    if referencia is None or not consultas:
        return 0.0
    # La referencia es SIEMPRE la misma (bge_m3), venga de donde venga el
    # retriever de la fila: es el encoder con el espacio menos comprimido (175
    # pares de documentos por encima de 0,98, frente a 1.750 de granite). Medir
    # cada fila con sus propios centroides haría la columna incomparable.
    cents, idx = referencia
    afectadas = 0
    for q in consultas:
        docs = [d["doc_id"] for d in retriever.search(q, **kw)["documents"]]
        vs = [cents[idx[d]] for d in docs if d in idx]
        if any(float(vs[a] @ vs[b]) > umbral for a in range(len(vs)) for b in range(a + 1, len(vs))):
            afectadas += 1
    return round(afectadas / len(consultas), 4)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-n", type=int, default=150)
    parser.add_argument("--salida", default=None)
    args = parser.parse_args()

    config.ensure_dirs()
    gold = load_mini_gold()
    from codefest.consultas import load_consultas
    consultas = [c["texto"] for c in load_consultas(config.CONSULTAS_JSONL)]

    # Referencia fija para medir duplicados, común a todas las filas.
    referencia = None
    ref_dir = config.BASE_VECTORIAL_DIR / "encoder_bge_m3"
    if (ref_dir / "centroides_documento.npy").exists():
        import numpy as np

        from codefest.retrieve import DOC_CENTROIDS_FILE, DOC_IDS_FILE
        with open(ref_dir / DOC_IDS_FILE, encoding="utf-8") as fh:
            referencia = (np.load(ref_dir / DOC_CENTROIDS_FILE),
                          {d: k for k, d in enumerate(json.load(fh))})
    disponibles = [
        e["slug"] for e in config.ENCODERS
        if (config.BASE_VECTORIAL_DIR / f"encoder_{e['slug']}" / "index.faiss").exists()
    ]
    print(f"Encoders disponibles: {disponibles}")

    resultados: list[dict] = []

    def registrar(nombre: str, retriever, **kw) -> None:
        t0 = time.time()
        fila = {"config": nombre, **puntuar(retriever, gold, **kw)}
        fila["known_item"] = round(known_item_probe(retriever, n=args.probe_n)["recall@3_doc"], 4)
        fila["titulos"] = round(title_probe(retriever, n=args.probe_n)["recall@3_doc"], 4)
        solo_busqueda = {k: v for k, v in kw.items()
                         if k in ("fusion_method", "max_per_doc", "expand", "expand_target",
                                  "doc_tail_weight", "doc_tail_n", "doc_dedup_cos")}
        if "fusion" in kw:
            solo_busqueda["fusion_method"] = kw["fusion"]
        solo_busqueda["use_fenomeno_prior"] = kw.get("prior", True)
        fila["duplicados"] = duplicados_en_top3(retriever, consultas, referencia, **solo_busqueda)
        fila["segundos"] = round(time.time() - t0, 1)
        resultados.append(fila)
        print(f"  {nombre:38} F1@3={fila['f1@3']:.3f}  cob={fila['cobertura']:.3f}  "
              f"pal={fila['palabras']:3d}  known={fila['known_item']:.3f}  "
              f"titulos={fila['titulos']:.3f}  dup={fila['duplicados']:.2f}  ({fila['segundos']}s)")

    print("\n=== Encoders por separado (sin grafo, sin prior) ===")
    for slug in disponibles:
        r = Retriever(slugs=[slug], use_graph=False)
        registrar(f"solo {slug}", r, prior=False)

    if len(disponibles) > 1:
        print("\n=== Fusión de los tres índices (sin grafo) ===")
        r = Retriever(slugs=disponibles, use_graph=False)
        for metodo in ("rrf", "combsum", "combmnz"):
            registrar(f"fusión {metodo}", r, fusion=metodo, prior=False)

        print("\n=== Prior por fenómeno, diversidad y expansión ===")
        registrar("rrf + prior fenómeno", r, fusion="rrf", prior=True)
        registrar("rrf sin expansión de vecinos", r, fusion="rrf", prior=False, expand=False)
        # Cuánto presupuesto de las 250 palabras conviene apurar. Expandir sube la
        # probabilidad de contener el pasaje gold, pero diluye el fragmento; que lo
        # decida la cobertura medida, no la intuición.
        for objetivo in (200, 225, 245, 250):
            registrar(f"rrf, expansión a {objetivo} palabras", r, fusion="rrf", prior=False,
                      expand_target=objetivo)
        # Poda de documentos duplicados. La métrica que importa aquí no es F1@3
        # —el mini gold no tiene resolución para 8 preguntas— sino cuántas de las
        # 50 consultas reales gastan dos de sus tres huecos en el mismo contenido.
        for umbral in (0.0, 0.98, 0.95, 0.92):
            etiqueta = "sin poda de duplicados" if umbral == 0 else f"poda duplicados cos>{umbral}"
            registrar(etiqueta, r, fusion="rrf", prior=False, doc_dedup_cos=umbral)

        # Agregación a documento: cuánto deben pesar los fragmentos secundarios.
        for w, tn in ((0.0, 0), (0.05, 4), (0.15, 4), (0.35, 4)):
            registrar(f"rrf, cola doc peso {w} n={tn}", r, fusion="rrf", prior=False,
                      doc_tail_weight=w, doc_tail_n=tn)
        for cap in (2, 3, 4, 10):
            registrar(f"rrf, máx {cap} frag/doc", r, fusion="rrf", max_per_doc=cap, prior=False)

    if (config.GRAFO_DIR / "grafo.graphml").exists() and len(disponibles) > 1:
        print("\n=== Con grafo de conocimiento ===")
        rg = Retriever(slugs=disponibles, use_graph=True)
        registrar("rrf + grafo", rg, fusion="rrf", prior=False)
        registrar("rrf + grafo + prior", rg, fusion="rrf", prior=True)

    salida = args.salida or (config.REPORTS_DIR / "ablacion.json")
    with open(salida, "w", encoding="utf-8") as fh:
        json.dump(resultados, fh, ensure_ascii=False, indent=1)
    print(f"\n-> {salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
