#!/usr/bin/env python
"""Arnés de evaluación: mini gold, sondas automáticas y reporte HTML de revisión.

Uso:
    python scripts/05_evaluar.py [--encoders granite,bge_m3] [--fusion rrf]
                                 [--skip-probes] [--probe-n 200]
"""

from __future__ import annotations

import argparse
import html
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.consultas import load_consultas  # noqa: E402
from codefest.evaluate import (  # noqa: E402
    f1_at_3,
    fenomeno_probe,
    known_item_probe,
    ndcg_at_k,
    load_mini_gold,
    match_docs_by_filename,
    title_probe,
    token_recall,
)
from codefest.retrieve import Retriever  # noqa: E402


def eval_mini_gold(retriever, fusion: str) -> dict:
    """Puntúa contra las 8 preguntas que los organizadores dejaron etiquetadas."""
    gold = load_mini_gold()
    if not gold:
        return {"n": 0}

    fuentes = {m["doc_id"]: m["fuente"] for m in retriever.meta}
    filas = []
    f1s, recalls_frag, ndcgs, ndcgs_orden = [], [], [], []

    for g in gold:
        relevantes = match_docs_by_filename(g["archivos"], fuentes)
        hits = retriever.search(g["pregunta"], fusion_method=fusion)
        docs = [d["doc_id"] for d in hits["documents"]]
        textos = [f["text"] for f in hits["fragments"]]

        f1 = f1_at_3(docs, relevantes) if relevantes else float("nan")
        if relevantes:
            f1s.append(f1)

        # ¿Alguno de los 10 fragmentos devueltos cubre el fragmento gold?
        cobertura = []
        for gf in g["fragmentos"]:
            mejor = max((token_recall(gf, t) for t in textos), default=0.0)
            cobertura.append(mejor)
            recalls_frag.append(mejor)

        # NDCG@10 con relevancia graduada. La Sección 10.2.1 dice que la
        # relevancia de un fragmento se juzga sobre su contenido textual y que el
        # chunk_id no es la clave de emparejamiento, así que la relevancia de
        # cada fragmento nuestro es cuánto del fragmento gold cubre.
        #
        # Se calculan dos lecturas porque miden cosas distintas y por separado
        # ninguna basta:
        #
        #   _orden  ideal = nuestra misma lista ordenada de mayor a menor. Aísla
        #           la calidad del ranking. Su punto ciego es que diez fragmentos
        #           mediocres perfectamente ordenados puntúan 1,0.
        #   _ideal  ideal = cobertura total de los fragmentos gold. Es el
        #           análogo honesto de la métrica real, donde el IDCG sale del
        #           ground truth y no de lo que devolvimos. Castiga tanto no
        #           encontrar como ordenar mal, y por eso es el que manda.
        rel = [max((token_recall(gf, t) for gf in g["fragmentos"]), default=0.0)
               for t in textos[:10]]
        ndcg_orden = ndcg_at_k(rel, sorted(rel, reverse=True), k=10)
        ndcg = ndcg_at_k(rel, [1.0] * min(len(g["fragmentos"]), 10), k=10)
        ndcgs.append(ndcg)
        ndcgs_orden.append(ndcg_orden)

        filas.append(
            {
                "pregunta": g["pregunta"],
                "relevantes": sorted(relevantes),
                "no_resueltos": [a for a in g["archivos"] if not relevantes],
                "devueltos": docs,
                "f1@3": f1,
                "ndcg@10": round(ndcg, 4),
                "cobertura_fragmentos": [round(c, 3) for c in cobertura],
            }
        )

    return {
        "n": len(gold),
        "f1@3_medio": sum(f1s) / len(f1s) if f1s else 0.0,
        "ndcg@10_vs_ideal": sum(ndcgs) / len(ndcgs) if ndcgs else 0.0,
        "ndcg@10_orden": sum(ndcgs_orden) / len(ndcgs_orden) if ndcgs_orden else 0.0,
        "cobertura_fragmento_media": sum(recalls_frag) / len(recalls_frag) if recalls_frag else 0.0,
        "cobertura_>0.5": sum(1 for r in recalls_frag if r > 0.5) / max(len(recalls_frag), 1),
        "filas": filas,
    }


def render_html(retriever, consultas, fusion: str, path) -> None:
    """Reporte de revisión manual: top-3 documentos y top-10 fragmentos por consulta."""
    meta_por_doc = {}
    for m in retriever.meta:
        meta_por_doc.setdefault(m["doc_id"], m)

    partes = [
        """<!doctype html><meta charset="utf-8">
<title>Revisión de recuperación — CODEFEST AD ASTRA 2026</title>
<style>
 body{font:15px/1.5 -apple-system,system-ui,sans-serif;margin:0;padding:2rem;max-width:1100px;color:#111}
 h1{font-size:1.5rem} h2{font-size:1.05rem;margin:2.5rem 0 .5rem;padding-top:1rem;border-top:2px solid #eee}
 .q{background:#f6f8fa;padding:.6rem .8rem;border-radius:6px;font-weight:600}
 .docs{margin:.8rem 0;padding:.6rem .8rem;background:#fffbe6;border-radius:6px}
 .doc{font-family:ui-monospace,monospace;font-size:.85rem}
 .obs{color:#555;font-weight:normal}
 details{margin:.35rem 0;border:1px solid #e5e7eb;border-radius:6px;padding:.4rem .6rem}
 summary{cursor:pointer;font-size:.87rem}
 .frag{font-size:.87rem;color:#333;margin-top:.4rem;white-space:pre-wrap}
 .meta{font-size:.75rem;color:#666;font-family:ui-monospace,monospace}
 .f1{background:#e7f5ff} .f2{background:#f3f0ff} .f3{background:#fff0f6}
</style>
<h1>Revisión de recuperación — CODEFEST AD ASTRA 2026</h1>
"""
    ]
    partes.append(f"<p class=meta>encoders: {', '.join(retriever.slugs)} · fusión: {fusion} · "
                  f"fragmentos indexados: {len(retriever.meta)} · grafo: {'sí' if retriever.graph else 'no'}</p>")

    for q in consultas:
        hits = retriever.search(q["texto"], fusion_method=fusion)
        partes.append(f"<h2>{q['query_id']}</h2>")
        partes.append(f"<div class=q>{html.escape(q['texto'])}</div>")

        partes.append("<div class=docs><b>Top-3 documentos</b><br>")
        for d in hits["documents"]:
            m = meta_por_doc.get(d["doc_id"], {})
            partes.append(
                f"<span class=doc>{d['rank']}. {html.escape(d['doc_id'])}</span> "
                f"<span class=obs>— {html.escape(str(m.get('observatorio', '')))} · "
                f"F{m.get('fenomeno', '?')} · {html.escape(str(m.get('titulo', ''))[:110])}</span><br>"
            )
        partes.append("</div>")

        for f in hits["fragments"]:
            m = meta_por_doc.get(f["doc_id"], {})
            fen = m.get("fenomeno", 0)
            partes.append(
                f"<details><summary class='f{fen}'>{f['rank']}. "
                f"<span class=meta>{html.escape(f['chunk_id'])}</span> — "
                f"{html.escape(str(m.get('observatorio', '')))} · "
                f"{html.escape(f['text'][:150])}…</summary>"
                f"<div class=frag>{html.escape(f['text'])}</div>"
                f"<div class=meta>{len(f['text'].split())} palabras</div></details>"
            )

    path.write_text("".join(partes), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoders", default=None)
    parser.add_argument("--fusion", default="rrf")
    parser.add_argument("--skip-probes", action="store_true")
    parser.add_argument("--probe-n", type=int, default=200)
    parser.add_argument("--no-html", action="store_true")
    args = parser.parse_args()

    config.ensure_dirs()
    slugs = [s.strip() for s in args.encoders.split(",")] if args.encoders else None
    retriever = Retriever(slugs=slugs, verbose=True)
    print(f"Encoders: {retriever.slugs} · fragmentos: {len(retriever.meta)} · grafo: {retriever.graph is not None}")

    print("\n--- Mini gold set (etiquetas dejadas por los organizadores) ---")
    t0 = time.time()
    mg = eval_mini_gold(retriever, args.fusion)
    if mg["n"]:
        print(f"  preguntas: {mg['n']}")
        print(f"  F1@3 medio (documentos): {mg['f1@3_medio']:.3f}")
        print(f"  NDCG@10 vs. cobertura ideal (fragmentos): {mg['ndcg@10_vs_ideal']:.3f}")
        print(f"  NDCG@10 solo orden del ranking: {mg['ndcg@10_orden']:.3f}")
        print(f"  cobertura media del fragmento gold: {mg['cobertura_fragmento_media']:.3f}")
        print(f"  fragmentos gold cubiertos >50%: {mg['cobertura_>0.5']:.1%}")
        for fila in mg["filas"]:
            estado = "OK " if fila["f1@3"] and fila["f1@3"] > 0 else "-- "
            print(f"   {estado} F1={fila['f1@3']:.2f} cob={fila['cobertura_fragmentos']} :: {fila['pregunta'][:65]}")
            print(f"        gold={fila['relevantes']} devueltos={fila['devueltos']}")
    print(f"  ({time.time() - t0:.0f}s)")

    if not args.skip_probes:
        print("\n--- Sonda known-item (fragmento como consulta -> su documento) ---")
        t0 = time.time()
        print(f"  {known_item_probe(retriever, n=args.probe_n)}  ({time.time() - t0:.0f}s)")

        print("\n--- Sonda de títulos (título como consulta -> su documento) ---")
        t0 = time.time()
        print(f"  {title_probe(retriever, n=args.probe_n)}  ({time.time() - t0:.0f}s)")

        print("\n--- Coherencia temática sobre las 50 consultas reales ---")
        t0 = time.time()
        fp = fenomeno_probe(retriever, load_consultas(config.CONSULTAS_JSONL))
        print(f"  documento 1 en el fenómeno esperado: {fp['top1_en_fenomeno']:.1%}")
        print(f"  proporción del top-3 en el fenómeno esperado: {fp['proporcion_en_fenomeno']:.1%}")
        for qid, esperado, fens in fp["discrepancias"][:12]:
            print(f"    {qid}: esperado F{esperado}, devueltos {fens}")
        print(f"  ({time.time() - t0:.0f}s)")

    if not args.no_html:
        consultas = load_consultas(config.CONSULTAS_JSONL)
        out = config.REPORTS_DIR / f"revision_{'_'.join(retriever.slugs)}_{args.fusion}.html"
        t0 = time.time()
        render_html(retriever, consultas, args.fusion, out)
        print(f"\nReporte de revisión manual -> {out}  ({time.time() - t0:.0f}s)")

    (config.REPORTS_DIR / "mini_gold.json").write_text(
        json.dumps(mg, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
