#!/usr/bin/env python
"""Consola para probar el buscador a mano y curiosear el grafo.

No forma parte de la entrega: es una herramienta para ver por dentro lo que el
sistema hace, escribiendo consultas propias en vez de las cincuenta oficiales.

Uso:
    python scripts/14_probar.py                          # modo interactivo
    python scripts/14_probar.py "minería ilegal en el Amazonas"
    python scripts/14_probar.py --grafo "Clan del Golfo" # vecinos de una entidad
    python scripts/14_probar.py --grafo-top              # entidades más conectadas
    python scripts/14_probar.py --sin-grafo "consulta"   # apagar el grafo en el RRF
"""

from __future__ import annotations

import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402

# Códigos ANSI: la salida es larga y sin resaltar cuesta leerla.
NEGRITA, APAGADO, CIAN, VERDE, AMARILLO, FIN = (
    "\033[1m", "\033[2m", "\033[36m", "\033[32m", "\033[33m", "\033[0m"
)


def puntaje(d: dict) -> float:
    """El campo interno lleva guion bajo porque se elimina antes de entregar."""
    return float(d.get("_score", d.get("score", 0.0)))


def mostrar(hits: dict, n_frag: int, dt: float) -> None:
    docs = hits["documents"]
    print(f"\n{NEGRITA}{'─' * 78}{FIN}")
    print(f"{NEGRITA}TOP-3 DOCUMENTOS{FIN}  {APAGADO}(esto es lo que puntúa F1@3){FIN}")
    for i, d in enumerate(docs, 1):
        print(f"  {VERDE}{i}. {d['doc_id']:<20}{FIN} RRF={puntaje(d):.5f}")

    print(f"\n{NEGRITA}TOP-{n_frag} FRAGMENTOS{FIN}  {APAGADO}(esto es lo que puntúa NDCG@10){FIN}")
    for f in hits["fragments"][:n_frag]:
        texto = " ".join(f["text"].split())
        corte = texto[:300] + ("…" if len(texto) > 300 else "")
        print(f"\n  {CIAN}#{f['rank']:<2} {f['doc_id']:<20}{FIN} "
              f"{APAGADO}{f['chunk_id']} · {len(f['text'].split())} palabras · "
              f"RRF={puntaje(f):.5f}{FIN}")
        print(f"     {corte}")
    print(f"\n{APAGADO}{len(hits['fragments'])} fragmentos en {dt:.2f}s{FIN}")


def explorar_grafo(entidad: str | None, top: bool) -> int:
    import networkx as nx

    ruta = config.GRAFO_DIR / "grafo.graphml"
    if not ruta.exists():
        print(f"No existe {ruta}")
        return 1
    print(f"{APAGADO}cargando el grafo…{FIN}")
    g = nx.read_graphml(ruta)
    print(f"{NEGRITA}{g.number_of_nodes():,} entidades · {g.number_of_edges():,} relaciones{FIN}\n")

    if top:
        por_grado = sorted(g.degree, key=lambda kv: -kv[1])[:30]
        print(f"{NEGRITA}Las 30 entidades más conectadas{FIN}")
        for nombre, grado in por_grado:
            tipo = g.nodes[nombre].get("tipo", "?")
            print(f"  {grado:>5} conexiones  {AMARILLO}{tipo:<14}{FIN} {nombre}")
        return 0

    # Búsqueda tolerante: rara vez se acierta la capitalización exacta.
    if entidad not in g:
        parecidas = [n for n in g.nodes if entidad.lower() in n.lower()]
        if not parecidas:
            print(f"No hay ninguna entidad que contenga «{entidad}».")
            return 1
        print(f"{APAGADO}coincidencias: {', '.join(parecidas[:8])}{FIN}\n")
        entidad = parecidas[0]

    datos = g.nodes[entidad]
    print(f"{NEGRITA}{entidad}{FIN}  ({datos.get('tipo', '?')}, "
          f"en {datos.get('n_fragmentos', '?')} fragmentos)\n")

    aristas = [(o, d, "→") for _, o, d in g.out_edges(entidad, data=True)]
    aristas += [(i, d, "←") for i, _, d in g.in_edges(entidad, data=True)]
    aristas.sort(key=lambda x: -int(x[1].get("peso", 0)))

    print(f"{NEGRITA}Relaciones más fuertes{FIN}  {APAGADO}(con su evidencia){FIN}")
    for otro, d, flecha in aristas[:20]:
        ev = (d.get("evidencia_chunks") or "").split(",")[0]
        print(f"  {flecha} {AMARILLO}{d.get('relacion', '?'):<16}{FIN} {otro:<42} "
              f"{APAGADO}peso={d.get('peso')} · {ev}{FIN}")
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("consulta", nargs="*", help="consulta; si se omite, modo interactivo")
    p.add_argument("--grafo", metavar="ENTIDAD", help="explorar los vecinos de una entidad")
    p.add_argument("--grafo-top", action="store_true", help="entidades más conectadas")
    p.add_argument("--sin-grafo", action="store_true", help="no usar el grafo en el RRF")
    p.add_argument("-n", "--n-fragmentos", type=int, default=5, help="fragmentos a mostrar")
    args = p.parse_args()

    if args.grafo or args.grafo_top:
        return explorar_grafo(args.grafo, args.grafo_top)

    from codefest.retrieve import Retriever

    slugs = [e["slug"] for e in config.ENCODERS
             if (config.BASE_VECTORIAL_DIR / f"encoder_{e['slug']}" / "index.faiss").exists()]
    print(f"{APAGADO}cargando {len(slugs)} encoders y el índice…{FIN}")
    t0 = time.time()
    r = Retriever(slugs=slugs, use_graph=not args.sin_grafo)
    print(f"{APAGADO}listo en {time.time() - t0:.0f}s · {len(r.meta):,} fragmentos · "
          f"grafo={'no' if args.sin_grafo else 'sí'}{FIN}")

    if args.consulta:
        q = " ".join(args.consulta)
        t0 = time.time()
        mostrar(r.search(q), args.n_fragmentos, time.time() - t0)
        return 0

    print(f"\n{APAGADO}Escribe una consulta y pulsa Enter. Ctrl-C o «salir» para terminar.{FIN}")
    while True:
        try:
            q = input(f"\n{NEGRITA}consulta>{FIN} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not q:
            continue
        if q.lower() in ("salir", "exit", "quit"):
            return 0
        t0 = time.time()
        mostrar(r.search(q), args.n_fragmentos, time.time() - t0)


if __name__ == "__main__":
    raise SystemExit(main())
