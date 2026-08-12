#!/usr/bin/env python
"""Construye el grafo de conocimiento (componente bonus, Sección 7).

Escribe entrega/base_vectorial/grafo/{grafo.graphml, entidad_fragmentos.json}.

Uso:
    python scripts/04_grafo.py [--workers N] [--limit N] [--sin-sintaxis]
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.graph.build import GraphBuilder, save_graph  # noqa: E402
from codefest.graph.ner import (  # noqa: E402
    entidades_reglas,
    entidades_spacy,
    gazetteer_hits,
    load_nlp,
    relaciones_sintacticas,
)

_SIN_SINTAXIS = False


def _init(sin_sintaxis: bool) -> None:
    global _SIN_SINTAXIS
    _SIN_SINTAXIS = sin_sintaxis
    os.environ.setdefault("OMP_NUM_THREADS", "1")


def _work(payload: tuple[int, str, str]) -> tuple[int, list, list]:
    """Devuelve (fila, entidades, tripletas). Se devuelven tuplas, no Docs de
    spaCy: serializar un Doc entre procesos cuesta más que volver a analizarlo."""
    row, texto, idioma = payload
    gaz = gazetteer_hits(texto)

    entidades = list(gaz)
    triples: list[tuple[str, str, str]] = []
    vistas = {n for n, _ in entidades}

    # `load_nlp` devuelve None en los idiomas sin modelo de licencia permisiva
    # (es, pt): ahí las entidades salen de reglas y no hay árbol de dependencias,
    # así que las relaciones de esos fragmentos quedan como co-ocurrencia.
    nlp = load_nlp(idioma)
    if nlp is None:
        entidades.extend((n, t) for n, t in entidades_reglas(texto) if n not in vistas)
        return row, entidades, triples

    try:
        doc = nlp(texto[:20000])
        spa = entidades_spacy(doc)
        entidades.extend((n, t) for n, t in spa if n not in vistas)
        if not _SIN_SINTAXIS:
            triples = relaciones_sintacticas(doc, {n for n, _ in entidades})
    except Exception:
        pass
    return row, entidades, triples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 4))
    parser.add_argument("--chunks", default=str(config.CHUNKS_JSONL))
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--sin-sintaxis", action="store_true", help="solo co-ocurrencia, sin dependencias")
    args = parser.parse_args()

    config.ensure_dirs()
    with open(args.chunks, encoding="utf-8") as fh:
        chunks = [json.loads(line) for line in fh if line.strip()]
    if args.limit:
        chunks = chunks[: args.limit]

    print(f"Construyendo el grafo sobre {len(chunks)} fragmentos con {args.workers} procesos")
    payloads = [(i, c["texto"], c["idioma"]) for i, c in enumerate(chunks)]

    builder = GraphBuilder()
    t0 = time.time()
    with mp.Pool(args.workers, initializer=_init, initargs=(args.sin_sintaxis,)) as pool:
        for n, (row, entidades, triples) in enumerate(
            pool.imap_unordered(_work, payloads, chunksize=64), start=1
        ):
            chunk = chunks[row]
            _register(builder, row, chunk, entidades, triples)
            if n % 5000 == 0 or n == len(payloads):
                print(
                    f"  {n}/{len(payloads)}  entidades={len(builder.freq_entidad)} "
                    f"tripletas={len(builder.tripletas)}  {time.time() - t0:.0f}s",
                    flush=True,
                )

    print("\nPodando y exportando...")
    graph = builder.build_graph()
    vivos = set(graph.nodes)
    stats = save_graph(graph, builder.entity_index(vivos), config.GRAFO_DIR)

    from codefest.graph.gazetteers import GAZETTEER_FILE, guardar_gazetteer

    n_alias = guardar_gazetteer(config.GRAFO_DIR / GAZETTEER_FILE)
    stats["gazetteer_alias"] = n_alias
    print(json.dumps(stats, ensure_ascii=False, indent=1))
    print(f"\nListo en {time.time() - t0:.0f}s -> {config.GRAFO_DIR}")
    return 0


def _register(builder: GraphBuilder, row: int, chunk: dict, entidades: list, triples: list) -> None:
    """Vuelca en el builder lo que calculó el worker."""
    from codefest.graph.build import MAX_ENTIDADES_POR_CHUNK

    dic: dict[str, str] = {}
    for nombre, tipo in entidades:
        dic.setdefault(nombre, tipo)
    if len(dic) > MAX_ENTIDADES_POR_CHUNK:
        dic = dict(list(dic.items())[:MAX_ENTIDADES_POR_CHUNK])

    for nombre, tipo in dic.items():
        builder.tipo_entidad.setdefault(nombre, tipo)
        builder.freq_entidad[nombre] += 1
        builder.entidad_chunks[nombre].append(row)

    nombres = sorted(dic)
    chunk_id, doc_id = chunk["chunk_id"], chunk["doc_id"]

    tipadas: set[tuple[str, str]] = set()
    for s, verbo, o in triples:
        if s in dic and o in dic:
            builder._add_triple(s, verbo, o, chunk_id, doc_id)
            tipadas.add((s, o))
            tipadas.add((o, s))

    for i, a in enumerate(nombres):
        for b in nombres[i + 1 :]:
            if (a, b) not in tipadas:
                builder._add_triple(a, "co_ocurre_con", b, chunk_id, doc_id)


if __name__ == "__main__":
    raise SystemExit(main())
