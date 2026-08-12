#!/usr/bin/env python
"""Validación completa de la entrega antes de enviarla.

Comprueba, en este orden:
  1. estructura de directorios exigida por la Sección 1.4
  2. resultados.jsonl contra el esquema de la Sección 9.3
  3. cada índice FAISS: se carga con read_index() y cuadra con su metadata.jsonl
  4. los 8 campos obligatorios de la Tabla 2 en todas las líneas de metadata
  5. completitud lingüística de los fragmentos (Sección 3.3), por muestreo
  6. el grafo se carga con read_graphml()

Uso:
    python scripts/07_validar.py [--entrega RUTA]
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.index_build import CAMPOS_OBLIGATORIOS  # noqa: E402
from codefest.output import validate_results  # noqa: E402

# Un fragmento completo termina en signo de cierre y empieza en mayúscula,
# comilla, número o signo de apertura.
_FIN_OK = re.compile(r"[.!?…»\"')\]]\s*$")
_INICIO_OK = re.compile(r"^[¿¡\"'«(\[\d•A-ZÁÉÍÓÚÑÜ]")


class Informe:
    def __init__(self) -> None:
        self.errores: list[str] = []
        self.avisos: list[str] = []

    def error(self, msg: str) -> None:
        self.errores.append(msg)

    def aviso(self, msg: str) -> None:
        self.avisos.append(msg)

    def seccion(self, titulo: str) -> None:
        print(f"\n--- {titulo} ---")


def check_estructura(entrega: Path, inf: Informe) -> list[str]:
    inf.seccion("Estructura de la entrega (Sección 1.4)")
    slugs: list[str] = []

    for nombre in ("resultados.jsonl", "generador.py"):
        p = entrega / nombre
        print(f"  {'OK  ' if p.exists() else 'FALTA'} {nombre}")
        if not p.exists():
            inf.error(f"falta {nombre}")

    informe_pdf = entrega / "informe_tecnico.pdf"
    print(f"  {'OK  ' if informe_pdf.exists() else 'FALTA'} informe_tecnico.pdf")
    if not informe_pdf.exists():
        inf.error("falta informe_tecnico.pdf")

    base = entrega / "base_vectorial"
    if not base.exists():
        inf.error("falta base_vectorial/")
        return slugs

    for carpeta in sorted(base.glob("encoder_*")):
        slug = carpeta.name.removeprefix("encoder_")
        tiene_index = (carpeta / "index.faiss").exists()
        tiene_meta = (carpeta / "metadata.jsonl").exists()
        print(f"  {'OK  ' if tiene_index and tiene_meta else 'FALTA'} {carpeta.name}/ "
              f"(index.faiss={tiene_index}, metadata.jsonl={tiene_meta})")
        if tiene_index and tiene_meta:
            slugs.append(slug)
        else:
            inf.error(f"{carpeta.name} incompleto")

    if not slugs:
        inf.error("no hay ninguna carpeta encoder_* completa (la base vectorial es obligatoria)")

    grafo = base / "grafo" / "grafo.graphml"
    print(f"  {'OK  ' if grafo.exists() else '--  '} grafo/grafo.graphml (bonus)")
    return slugs


def check_resultados(entrega: Path, inf: Informe) -> None:
    inf.seccion("resultados.jsonl (Sección 9.3)")
    rep = validate_results(entrega / "resultados.jsonl")
    print(f"  líneas: {rep['n_lineas']}")
    print(f"  máximo de palabras en un fragmento: {rep.get('max_palabras_fragmento', 0)} (límite {config.MAX_WORDS_OUT})")
    for e in rep["errores"]:
        inf.error(f"resultados.jsonl: {e}")
    for a in rep["avisos"][:10]:
        inf.aviso(f"resultados.jsonl: {a}")
    print(f"  {'OK' if rep['ok'] else 'CON ERRORES'}")


def check_indices(entrega: Path, slugs: list[str], inf: Informe) -> None:
    import faiss

    inf.seccion("Índices FAISS y metadata (Secciones 1.4, 5.3 y Tabla 2)")
    for slug in slugs:
        carpeta = entrega / "base_vectorial" / f"encoder_{slug}"
        try:
            index = faiss.read_index(str(carpeta / "index.faiss"))
        except Exception as exc:
            inf.error(f"{slug}: faiss.read_index() falló: {exc}")
            continue

        with open(carpeta / "metadata.jsonl", encoding="utf-8") as fh:
            meta = [json.loads(line) for line in fh if line.strip()]

        print(f"  {slug}: {index.ntotal} vectores, dim={index.d}, {len(meta)} líneas de metadata, "
              f"tipo={type(index).__name__}")
        if index.ntotal != len(meta):
            inf.error(f"{slug}: {index.ntotal} vectores pero {len(meta)} líneas de metadata")

        faltantes = {c for rec in meta for c in CAMPOS_OBLIGATORIOS if c not in rec}
        if faltantes:
            inf.error(f"{slug}: faltan campos obligatorios en metadata: {sorted(faltantes)}")
        else:
            print(f"    campos obligatorios de la Tabla 2: OK en las {len(meta)} líneas")

        ids = [m["chunk_id"] for m in meta]
        if len(ids) != len(set(ids)):
            inf.error(f"{slug}: hay chunk_id duplicados")

        largos = [m for m in meta if len(m["texto"].split()) > config.MAX_WORDS_OUT]
        if largos:
            inf.aviso(f"{slug}: {len(largos)} fragmentos del índice superan las {config.MAX_WORDS_OUT} palabras "
                      f"(se recortan o expanden en la salida, no es un error del índice)")

        check_alineacion(slug, index, meta, inf)


def check_alineacion(slug: str, index, meta: list[dict], inf: Informe, n: int = 16) -> None:
    """Prueba de ida y vuelta: ¿el vector i es de verdad el fragmento de la línea i?

    Es el fallo más caro posible —un desfase de una sola línea invalida todos los
    resultados sin que nada más lo delate—, así que se comprueba de punta a punta y
    usando únicamente lo que viaja dentro de la entrega: se reconstruye el texto que
    se codificó a partir de los campos `titulo`, `seccion` y `texto` de la metadata,
    se vuelve a codificar y se compara con el vector que devuelve el índice.
    """
    import numpy as np

    from codefest.encoders import encode_texts

    rng = random.Random(1)
    filas = rng.sample(range(len(meta)), min(n, len(meta)))
    textos = [
        " | ".join(p for p in (meta[i].get("titulo", ""), meta[i].get("seccion", ""), meta[i]["texto"]) if p)
        for i in filas
    ]
    try:
        vecs = encode_texts(slug, textos, is_query=False, batch_size=8, show_progress=False)
    except Exception as exc:
        inf.aviso(f"{slug}: no se pudo recodificar para la prueba de alineación: {exc}")
        return

    cos = []
    for fila, v in zip(filas, vecs):
        recon = np.asarray(index.reconstruct(int(fila)), dtype=np.float32)
        v = v / (np.linalg.norm(v) or 1.0)
        cos.append(float(recon @ v))

    peor = min(cos)
    print(f"    alineación índice<->metadata: coseno medio {sum(cos) / len(cos):.4f}, peor {peor:.4f} "
          f"({len(filas)} filas recodificadas)")
    if peor < 0.98:
        desalineadas = [f for f, c in zip(filas, cos) if c < 0.98]
        inf.error(f"{slug}: el vector no corresponde al fragmento de su línea en {len(desalineadas)} "
                  f"de {len(filas)} filas (p. ej. línea {desalineadas[0]}, coseno {peor:.3f})")


def check_completitud(entrega: Path, slugs: list[str], inf: Informe, n: int = 400) -> None:
    inf.seccion("Completitud lingüística de los fragmentos (Sección 3.3)")
    if not slugs:
        return
    carpeta = entrega / "base_vectorial" / f"encoder_{slugs[0]}"
    with open(carpeta / "metadata.jsonl", encoding="utf-8") as fh:
        meta = [json.loads(line) for line in fh if line.strip()]

    rng = random.Random(0)
    muestra = rng.sample(meta, min(n, len(meta)))
    mal_final = [m for m in muestra if not _FIN_OK.search(m["texto"].strip())]
    mal_inicio = [m for m in muestra if not _INICIO_OK.match(m["texto"].strip())]

    print(f"  muestra de {len(muestra)} fragmentos")
    print(f"  sin signo de cierre al final: {len(mal_final)} ({len(mal_final) / len(muestra):.1%})")
    print(f"  sin inicio de oración válido: {len(mal_inicio)} ({len(mal_inicio) / len(muestra):.1%})")
    if len(mal_final) / len(muestra) > 0.25:
        inf.aviso("muchos fragmentos no terminan en signo de cierre; suele ser texto de tablas u OCR, revisar muestras")
    for m in mal_final[:3]:
        print(f"    ej. {m['chunk_id']}: ...{m['texto'][-70:]!r}")


def check_grafo(entrega: Path, inf: Informe) -> None:
    grafo = entrega / "base_vectorial" / "grafo" / "grafo.graphml"
    if not grafo.exists():
        return
    inf.seccion("Grafo de conocimiento (Sección 7)")
    try:
        import networkx as nx

        g = nx.read_graphml(grafo)
        print(f"  read_graphml() OK: {g.number_of_nodes()} nodos, {g.number_of_edges()} aristas")
        con_evidencia = sum(1 for _, _, d in g.edges(data=True) if d.get("evidencia_chunks"))
        print(f"  aristas con evidencia (doc_id/chunk_id): {con_evidencia}/{g.number_of_edges()}")
        if con_evidencia < g.number_of_edges() * 0.9:
            inf.aviso("hay aristas sin evidencia textual; la Sección 7.2 pide trazabilidad")
    except Exception as exc:
        inf.error(f"el grafo no se pudo cargar: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--entrega", default=str(config.ENTREGA_DIR))
    args = parser.parse_args()
    entrega = Path(args.entrega)

    print(f"Validando la entrega en {entrega}")
    inf = Informe()

    slugs = check_estructura(entrega, inf)
    if (entrega / "resultados.jsonl").exists():
        check_resultados(entrega, inf)
    if slugs:
        check_indices(entrega, slugs, inf)
        check_completitud(entrega, slugs, inf)
    check_grafo(entrega, inf)

    print("\n" + "=" * 70)
    if inf.errores:
        print(f"{len(inf.errores)} ERROR(ES) — la entrega NO está lista:")
        for e in inf.errores:
            print(f"  ✗ {e}")
    else:
        print("Sin errores bloqueantes.")
    if inf.avisos:
        print(f"\n{len(inf.avisos)} aviso(s):")
        for a in inf.avisos:
            print(f"  · {a}")
    return 1 if inf.errores else 0


if __name__ == "__main__":
    raise SystemExit(main())
