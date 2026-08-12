#!/usr/bin/env python
"""Recodifica solo las filas cuyo texto cambió y reconstruye los índices.

Complemento de `02b_desguionizar.py`. Como la reparación de guiones no movió
ninguna frontera de fragmento, las 91.088 filas siguen en el mismo orden y con
el mismo chunk_id: basta con volver a codificar las 8.095 que cambiaron y
sustituir esas filas en la matriz guardada. Recodificar las 91.088 costaría
entre 50 y 100 minutos por encoder para cambiar el 8,9% de ellas.

El índice FAISS sí se reescribe entero, pero eso es una copia de memoria de un
`IndexFlatIP`: segundos, no minutos.

Uso:
    python scripts/03b_recodificar_filas.py [--encoders granite,bge_m3]
"""

from __future__ import annotations

import os

# Mismo motivo que en 03_embed_index.py: faiss y torch traen cada uno su libomp.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse  # noqa: E402
import gc  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.encoders import count_tokens, encode_texts, load_encoder  # noqa: E402
from codefest.index_build import verify_index, write_encoder_folder  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoders", default=",".join(e["slug"] for e in config.ENCODERS))
    parser.add_argument("--batch-size", type=int, default=config.EMBED_BATCH_SIZE)
    args = parser.parse_args()

    config.ensure_dirs()

    ruta_filas = config.DATA_DIR / "filas_recodificar.json"
    if not ruta_filas.exists():
        print(f"No existe {ruta_filas}: nada que recodificar. Corre 02b primero.")
        return 1
    with open(ruta_filas, encoding="utf-8") as fh:
        filas = sorted(set(json.load(fh)))

    with open(config.CHUNKS_JSONL, encoding="utf-8") as fh:
        chunks = [json.loads(linea) for linea in fh if linea.strip()]

    if not filas:
        print("Sin filas marcadas: nada que hacer.")
        return 0
    if filas[-1] >= len(chunks):
        print(f"ERROR: la fila {filas[-1]} no existe entre {len(chunks)} fragmentos.")
        return 1

    print(f"{len(filas):,} filas a recodificar de {len(chunks):,} ({len(filas)/len(chunks):.1%})")
    textos_nuevos = [chunks[i]["texto_embed"] for i in filas]
    textos_raw = [c["texto"] for c in chunks]

    for slug in [s.strip() for s in args.encoders.split(",") if s.strip()]:
        spec = config.ENCODERS_BY_SLUG[slug]
        print(f"\n=== {slug} :: {spec['hf_id']} ===")

        cache = config.VECTORS_DIR / f"{slug}.npy"
        if not cache.exists():
            print(f"  falta {cache}: hay que correr 03_embed_index.py entero.")
            return 1
        vectors = np.load(cache)
        if vectors.shape[0] != len(chunks):
            print(f"  {cache.name} tiene {vectors.shape[0]} filas y hay {len(chunks)} "
                  f"fragmentos: incompatible, corre 03_embed_index.py --recodificar.")
            return 1

        t0 = time.time()
        nuevos = encode_texts(
            slug, textos_nuevos, is_query=False, batch_size=args.batch_size, show_progress=True
        )
        print(f"  {len(filas):,} filas codificadas en {time.time() - t0:.0f}s")

        # Antes de pisar nada: la fila recodificada tiene que parecerse a la
        # anterior. Un coseno bajo significaría que se están escribiendo en el
        # sitio equivocado, y eso desalinea el índice entero en silencio.
        cos = np.einsum("ij,ij->i", vectors[filas], nuevos)
        print(f"  coseno con el vector previo: min={cos.min():.4f} media={cos.mean():.4f}")
        if cos.min() < 0.80:
            peor = filas[int(np.argmin(cos))]
            print(f"  !! fila {peor} ({chunks[peor]['chunk_id']}) cambió demasiado: revisar")

        vectors[filas] = nuevos
        np.save(cache, vectors)

        toks: list[int] = []
        for i in range(0, len(textos_raw), 2000):
            toks.extend(count_tokens(slug, textos_raw[i : i + 2000]))

        folder = write_encoder_folder(slug, chunks, vectors, toks)
        report = verify_index(slug, vectors=vectors)
        print(f"  escrito -> {folder}\n  verificación: {report}")
        if report["desalineados"] or report["campos_faltantes"]:
            print("  !! REVISAR: el índice no está alineado con la metadata")
            return 1

        del vectors, nuevos, toks
        load_encoder.cache_clear()
        gc.collect()

    print("\nListo. Falta recalcular centroides (06) y el grafo (04).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
