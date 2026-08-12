"""Codificación semántica (Sección 4 de la especificación).

Los tres encoders son arquitectura ENCODER (familia BERT) con licencia
permisiva. La Sección 4.2 prohíbe explícitamente los decoders para generar
embeddings, lo que descarta a Qwen3-Embedding, gte-Qwen2 y e5-mistral pese a
sus buenos números en MTEB.

Todos los vectores se normalizan a norma unitaria, de modo que el producto
interno del índice FAISS equivale exactamente a la similitud coseno (Sección 8.2).
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

import numpy as np

from . import config


# Dispositivo en el que se codifican las CONSULTAS. Fijo a propósito, no
# autodetectado.
#
# `load_encoder` usa half precision en mps y cuda, y fp32 en CPU. Eso hace que el
# vector de una misma consulta dependa de la máquina, y con él el ranking: medido
# sobre las 50 consultas reales, codificar en cpu/fp32 en vez de mps/fp16 cambia
# la lista de fragmentos de 15 de las 50 y el top-3 de documentos de una. Es
# decir, el `resultados.jsonl` que entregamos no sería el que reproduce el
# jurado, que corre en CPU (`requirements.txt` fija `faiss-cpu`).
#
# CPU en fp32 es el único punto de operación que cualquier máquina puede
# reproducir. Entre arquitecturas quedan diferencias de ~1e-7, cuatro órdenes de
# magnitud por debajo de los ~2e-3 que separan fp16 de fp32, y muy por debajo de
# lo que mueve un ranking.
#
# No cuesta calidad. Sondas sobre 150 pruebas, mps/fp16 -> cpu/fp32:
# known-item@3 0,8867 -> 0,8867; MRR 0,8289 -> 0,8289; títulos@3 0,9133 ->
# 0,9133; NDCG@10 0,7912 -> 0,7931. Y son 50 consultas: el coste es de segundos.
#
# Solo afecta a la consulta. Los pasajes del índice se codificaron con el
# dispositivo autodetectado y viajan como dato fijo dentro de la entrega.
QUERY_DEVICE = "cpu"


def _device() -> str:
    """Mejor dispositivo disponible. Para indexar, no para consultar."""
    import torch

    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def local_model_dir(hf_id: str) -> Path:
    """Ruta local donde se cachean los pesos dentro de la entrega."""
    return config.ENTREGA_DIR / "modelos" / hf_id.replace("/", "__")


@lru_cache(maxsize=4)
def load_encoder(slug: str, device: str | None = None, half: bool | None = None):
    """Carga un encoder. Prefiere los pesos locales de la entrega si existen.

    En GPU se usa half precision: es ~2,8x más rápido y la diferencia con fp32
    es de 2e-4 en similitud coseno, irrelevante para el orden del ranking. En
    CPU se mantiene fp32, que es donde fp16 no aporta nada.
    """
    from sentence_transformers import SentenceTransformer

    spec = config.ENCODERS_BY_SLUG[slug]
    local = local_model_dir(spec["hf_id"])
    source = str(local) if local.exists() else spec["hf_id"]

    dev = device or _device()
    model = SentenceTransformer(source, device=dev, trust_remote_code=False)
    model.max_seq_length = spec["max_seq"]

    if half if half is not None else dev in ("mps", "cuda"):
        model = model.half()
    return model


def encode_texts(
    slug: str,
    texts: list[str],
    *,
    is_query: bool = False,
    batch_size: int | None = None,
    show_progress: bool = False,
    device: str | None = None,
) -> np.ndarray:
    """Devuelve una matriz float32 (n, d) con los vectores normalizados.

    Las consultas se codifican en `QUERY_DEVICE` salvo que se pida otro
    dispositivo explícitamente, para que la salida no dependa de la máquina.
    """
    spec = config.ENCODERS_BY_SLUG[slug]
    prefix = spec["query_prefix"] if is_query else spec["passage_prefix"]
    if prefix:
        texts = [prefix + t for t in texts]

    if device is None and is_query:
        device = QUERY_DEVICE

    model = load_encoder(slug, device=device)
    vectors = model.encode(
        texts,
        batch_size=batch_size or config.EMBED_BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=show_progress,
    )
    return np.asarray(vectors, dtype=np.float32)


def count_tokens(slug: str, texts: list[str]) -> list[int]:
    """Número de tokens por texto según el tokenizador del propio encoder.

    Es el valor que va al campo obligatorio `num_tokens` de la Tabla 2, y por eso
    cada encoder tiene su propio metadata.jsonl con su propio conteo.
    """
    model = load_encoder(slug)
    tok = model.tokenizer
    encoded = tok(texts, add_special_tokens=True, truncation=False)["input_ids"]
    return [len(ids) for ids in encoded]


def download_models(slugs: list[str] | None = None) -> None:
    """Descarga los pesos a entrega/modelos/ para que generador.py sea autónomo."""
    from sentence_transformers import SentenceTransformer

    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    for slug in slugs or [e["slug"] for e in config.ENCODERS]:
        spec = config.ENCODERS_BY_SLUG[slug]
        dest = local_model_dir(spec["hf_id"])
        if dest.exists():
            print(f"  ya está: {spec['hf_id']}")
            continue
        print(f"  descargando {spec['hf_id']} -> {dest}")
        dest.parent.mkdir(parents=True, exist_ok=True)
        SentenceTransformer(spec["hf_id"], device="cpu").save(str(dest))
