#!/usr/bin/env python
"""Codifica los fragmentos y construye el índice FAISS de cada encoder.

Escribe entrega/base_vectorial/encoder_<slug>/{index.faiss,metadata.jsonl} y
guarda una copia de los vectores en data/vectors/ para las ablaciones.

Uso:
    python scripts/03_embed_index.py [--encoders granite,bge_m3] [--batch-size 64]
"""

from __future__ import annotations

import os

# faiss y torch traen cada uno su propia copia de libomp. Cargarlas en el mismo
# proceso aborta con "OMP: Error #15". Hay que fijarlo ANTES de importar
# cualquiera de los dos, así que va arriba del todo. Ver nota en index_build.py.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse  # noqa: E402
import gc  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.encoders import count_tokens, encode_texts, load_encoder  # noqa: E402
from codefest.index_build import verify_index, write_encoder_folder  # noqa: E402


def load_chunks(path: str) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunks", default=str(config.CHUNKS_JSONL))
    parser.add_argument("--encoders", default=",".join(e["slug"] for e in config.ENCODERS))
    parser.add_argument("--batch-size", type=int, default=config.EMBED_BATCH_SIZE)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--recodificar", action="store_true",
                        help="ignorar los vectores guardados y volver a codificar")
    args = parser.parse_args()

    config.ensure_dirs()
    chunks = load_chunks(args.chunks)
    if args.limit:
        chunks = chunks[: args.limit]
    print(f"{len(chunks)} fragmentos")

    texts_embed = [c["texto_embed"] for c in chunks]
    texts_raw = [c["texto"] for c in chunks]

    for slug in [s.strip() for s in args.encoders.split(",") if s.strip()]:
        spec = config.ENCODERS_BY_SLUG[slug]
        print(f"\n=== {slug} :: {spec['hf_id']} ({spec['arquitectura']}, {spec['licencia']}) ===")

        # Codificar es lo caro (de 50 a 100 minutos por encoder). Si ya hay
        # vectores guardados de una corrida anterior se reutilizan: así un fallo
        # al construir el índice no obliga a repetir la codificación entera.
        cache = config.VECTORS_DIR / f"{slug}.npy"
        if cache.exists() and not args.recodificar:
            vectors = np.load(cache)
            if vectors.shape[0] == len(chunks):
                print(f"  vectores reutilizados de {cache.name} {vectors.shape}")
            else:
                print(f"  {cache.name} tiene {vectors.shape[0]} filas y hay {len(chunks)} "
                      f"fragmentos: se recodifica")
                del vectors
                cache.unlink()

        if not cache.exists() or args.recodificar:
            t0 = time.time()
            model = load_encoder(slug)
            print(f"  modelo cargado en {time.time() - t0:.0f}s, dispositivo={model.device}")

            t0 = time.time()
            vectors = encode_texts(
                slug, texts_embed, is_query=False, batch_size=args.batch_size, show_progress=True
            )
            dt = time.time() - t0
            print(f"  codificados {vectors.shape} en {dt:.0f}s ({len(chunks) / max(dt, 1):.0f} frag/s)")
            np.save(cache, vectors)

        # num_tokens de la Tabla 2, con el tokenizador de este mismo encoder
        t0 = time.time()
        toks: list[int] = []
        for i in range(0, len(texts_raw), 2000):
            toks.extend(count_tokens(slug, texts_raw[i : i + 2000]))
        print(f"  conteo de tokens en {time.time() - t0:.0f}s (media {np.mean(toks):.0f})")

        folder = write_encoder_folder(slug, chunks, vectors, toks)
        print(f"  escrito -> {folder}")

        report = verify_index(slug, vectors=vectors)
        print(f"  verificación: {report}")
        if report["desalineados"] or report["campos_faltantes"]:
            print("  !! REVISAR: el índice no está alineado con la metadata")

        # Los vectores de un encoder ocupan ~370 MB. Se liberan antes de cargar
        # el siguiente modelo para no sostener dos matrices a la vez.
        del vectors, toks
        load_encoder.cache_clear()
        gc.collect()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
