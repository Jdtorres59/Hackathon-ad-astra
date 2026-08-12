"""Construcción y persistencia del índice FAISS (Sección 5 de la especificación).

`IndexFlatIP` sobre vectores normalizados: búsqueda exacta por producto interno,
que con norma unitaria equivale a similitud coseno (Sección 8.2). Con ~10^5
fragmentos la búsqueda exhaustiva tarda milisegundos, así que no hay razón para
sacrificar exactitud con IVF o HNSW.

Requisito de la Sección 1.4: el orden de las líneas de metadata.jsonl debe
coincidir con los identificadores internos que FAISS asigna al indexar. Como
`IndexFlatIP` los asigna secuencialmente en el orden de inserción, basta con
escribir la metadata en ese mismo orden — y `verify_index` lo comprueba.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from . import config

# `codefest/__init__.py` pone KMP_DUPLICATE_LIB_OK; aquí se completa el arreglo
# dejando un solo hilo a cada runtime de OpenMP. Ver `limitar_hilos_openmp`.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

_HILOS_FIJADOS = False


def limitar_hilos_openmp() -> None:
    """Deja faiss y torch con un hilo cada uno. Llamar antes de usar cualquiera.

    `KMP_DUPLICATE_LIB_OK=TRUE` permite que las dos copias de `libomp` que
    empaquetan faiss y torch convivan en el proceso, pero solo silencia el aviso
    `OMP: Error #15`: los dos runtimes siguen levantando su propio pool de hilos
    y el segundo en arrancar aborta el intérprete con SIGSEGV.

    En una máquina con GPU no se ve, porque torch trabaja en mps o cuda y nunca
    llega a levantar su pool. En CPU sí, que es justo donde corre el jurado:
    `requirements.txt` fija `faiss-cpu`. Medido en este equipo, con faiss ya
    cargado y torch en CPU:

        sin nada                    -> exit 139 (SIGSEGV)
        OMP_NUM_THREADS=1           -> exit 139 (SIGSEGV)
        torch.set_num_threads(1)    -> exit 0

    La variable de entorno no basta porque torch fija su número de hilos al
    inicializar su propio runtime, después de leerla. Hay que decírselo por API.

    Idempotente.
    """
    global _HILOS_FIJADOS
    if _HILOS_FIJADOS:
        return
    import faiss
    import torch

    faiss.omp_set_num_threads(1)
    torch.set_num_threads(1)
    _HILOS_FIJADOS = True

# Campos obligatorios de la Tabla 2, en orden
CAMPOS_OBLIGATORIOS = (
    "doc_id",
    "chunk_id",
    "fuente",
    "formato",
    "fenomeno",
    "posicion",
    "num_tokens",
    "texto",
)
# Campos adicionales permitidos (Sección 3.4: "los equipos pueden añadir campos")
CAMPOS_EXTRA = (
    "doc_id_inventario",
    "doc_id_secuencial",
    "observatorio",
    "titulo",
    "idioma",
    "fecha",
    "url",
    "seccion",
    "ruta_relativa",
    "n_palabras",
)


def encoder_dir(slug: str, base: Path | None = None) -> Path:
    return (base or config.BASE_VECTORIAL_DIR) / f"encoder_{slug}"


def build_index(vectors: np.ndarray) -> "faiss.Index":  # noqa: F821
    import faiss

    limitar_hilos_openmp()
    vectors = np.ascontiguousarray(vectors.astype(np.float32))
    # Reasegura la norma unitaria: si un vector llegara sin normalizar, el
    # producto interno dejaría de ser coseno.
    faiss.normalize_L2(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    return index


def metadata_record(chunk: dict, num_tokens: int) -> dict:
    """Registro de metadata de un fragmento, con los obligatorios primero."""
    rec = {
        "doc_id": chunk["doc_id"],
        "chunk_id": chunk["chunk_id"],
        "fuente": chunk["fuente"],
        "formato": chunk["formato"],
        "fenomeno": chunk["fenomeno"],
        "posicion": chunk["posicion"],
        "num_tokens": num_tokens,
        "texto": chunk["texto"],
    }
    for k in CAMPOS_EXTRA:
        if k in chunk:
            rec[k] = chunk[k]
    return rec


def write_encoder_folder(
    slug: str,
    chunks: list[dict],
    vectors: np.ndarray,
    num_tokens: list[int],
    base: Path | None = None,
) -> Path:
    """Escribe index.faiss + metadata.jsonl de un encoder."""
    import faiss

    if not (len(chunks) == vectors.shape[0] == len(num_tokens)):
        raise ValueError(
            f"desalineado: {len(chunks)} fragmentos, {vectors.shape[0]} vectores, {len(num_tokens)} conteos"
        )

    out = encoder_dir(slug, base)
    out.mkdir(parents=True, exist_ok=True)

    index = build_index(vectors)
    faiss.write_index(index, str(out / "index.faiss"))

    with open(out / "metadata.jsonl", "w", encoding="utf-8") as fh:
        for chunk, nt in zip(chunks, num_tokens):
            fh.write(json.dumps(metadata_record(chunk, nt), ensure_ascii=False) + "\n")

    return out


def load_encoder_folder(slug: str, base: Path | None = None) -> tuple["faiss.Index", list[dict]]:  # noqa: F821
    import faiss

    limitar_hilos_openmp()
    folder = encoder_dir(slug, base)
    index = faiss.read_index(str(folder / "index.faiss"))
    with open(folder / "metadata.jsonl", encoding="utf-8") as fh:
        meta = [json.loads(line) for line in fh if line.strip()]
    if index.ntotal != len(meta):
        raise ValueError(f"{slug}: {index.ntotal} vectores vs {len(meta)} líneas de metadata")
    return index, meta


def verify_index(slug: str, vectors: np.ndarray | None = None, base: Path | None = None, n_probe: int = 100) -> dict:
    """Comprueba la correspondencia entre IDs internos de FAISS y metadata.jsonl.

    Reconstruye vectores del índice y confirma que el vector i es el del
    fragmento de la línea i. Es la verificación que exige la Sección 5.3.
    """
    index, meta = load_encoder_folder(slug, base)
    report = {
        "slug": slug,
        "ntotal": index.ntotal,
        "n_meta": len(meta),
        "dim": index.d,
        "campos_faltantes": [],
        "desalineados": 0,
    }

    faltantes = {c for rec in meta[:2000] for c in CAMPOS_OBLIGATORIOS if c not in rec}
    report["campos_faltantes"] = sorted(faltantes)

    if vectors is not None and index.ntotal:
        rng = np.random.default_rng(0)
        idx = rng.choice(index.ntotal, size=min(n_probe, index.ntotal), replace=False)
        for i in idx:
            recon = index.reconstruct(int(i))
            ref = vectors[int(i)] / (np.linalg.norm(vectors[int(i)]) or 1.0)
            if not np.allclose(recon, ref, atol=1e-4):
                report["desalineados"] += 1

    return report
