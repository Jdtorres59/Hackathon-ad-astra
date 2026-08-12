"""Rutas, modelos e hiperparámetros del pipeline.

Un único lugar para todo lo configurable. Los scripts no deben hardcodear rutas.
"""

from __future__ import annotations

import os
from pathlib import Path

# --------------------------------------------------------------------------- #
# Rutas
# --------------------------------------------------------------------------- #

PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT = PROJECT_ROOT.parent

CORPUS_DIR = WORKSPACE_ROOT / "CORPUS CODEFEST AD ASTRA 2026"
INVENTORY_XLSX = CORPUS_DIR / "Indice_Datos_Codefest.xlsx"
PREGUNTAS_PDF = CORPUS_DIR / "Extracto_Preguntas_50_v2.pdf"
MINI_GOLD_XLSX = CORPUS_DIR / "F3_Dinamicas_Territoriales" / "FASE ORDENADA CODEFEST.xlsx"

DATA_DIR = PROJECT_ROOT / "data"
REPORTS_DIR = PROJECT_ROOT / "reports"
ENTREGA_DIR = PROJECT_ROOT / "entrega"

DOCS_JSONL = DATA_DIR / "docs.jsonl"
CHUNKS_JSONL = DATA_DIR / "chunks.jsonl"
VECTORS_DIR = DATA_DIR / "vectors"
CONSULTAS_JSONL = DATA_DIR / "consultas.jsonl"

BASE_VECTORIAL_DIR = ENTREGA_DIR / "base_vectorial"
GRAFO_DIR = BASE_VECTORIAL_DIR / "grafo"
RESULTADOS_JSONL = ENTREGA_DIR / "resultados.jsonl"

# --------------------------------------------------------------------------- #
# Identificación de documentos
#
# El corpus trae DOC_IDs oficiales en Indice_Datos_Codefest.xlsx (F1-AIINDEX-001).
# La especificación dice que el doc_id lo asigna el equipo, pero el ground truth
# fue construido por los organizadores, así que el ID del inventario es la
# apuesta más segura. El pipeline guarda ambos y esta variable decide cuál se
# escribe en el campo `doc_id` de metadata.jsonl y resultados.jsonl.
# --------------------------------------------------------------------------- #

# "inventario" -> F1-AIINDEX-001   |   "secuencial" -> DOC-0001
DOC_ID_SCHEME = os.environ.get("CODEFEST_DOC_ID_SCHEME", "inventario")

# --------------------------------------------------------------------------- #
# Chunking
# --------------------------------------------------------------------------- #

CHUNK_TARGET_WORDS = 190  # objetivo por fragmento
CHUNK_MAX_WORDS = 240  # tope duro: deja margen bajo el límite de 250 de la salida
CHUNK_MIN_WORDS = 40  # por debajo de esto, se fusiona con el vecino
CHUNK_OVERLAP_SENTENCES = 1

# Los CSV masivos (PubMed, ClinicalTrials del AI Index) generarían decenas de
# miles de fragmentos de bajo valor. Se limitan por documento.
TABULAR_MAX_CHUNKS_PER_DOC = 300
TABULAR_ROWS_PER_CHUNK = 8

# --------------------------------------------------------------------------- #
# Encoders
#
# Los tres son arquitectura ENCODER (familia BERT) con licencia permisiva.
# Prohibido usar decoders (Qwen3-Embedding, gte-Qwen2, e5-mistral) por la
# Sección 4.2 / 8.3 de la especificación.
# --------------------------------------------------------------------------- #

ENCODERS: list[dict] = [
    {
        "slug": "granite",
        "hf_id": "ibm-granite/granite-embedding-311m-multilingual-r2",
        "licencia": "Apache 2.0",
        "arquitectura": "ModernBERT (encoder-only)",
        "dim": 768,
        "max_seq": 512,
        "query_prefix": "",
        "passage_prefix": "",
    },
    {
        "slug": "bge_m3",
        "hf_id": "BAAI/bge-m3",
        "licencia": "MIT",
        "arquitectura": "XLM-RoBERTa (encoder)",
        "dim": 1024,
        "max_seq": 512,
        "query_prefix": "",
        "passage_prefix": "",
    },
    {
        "slug": "e5_large",
        "hf_id": "intfloat/multilingual-e5-large",
        "licencia": "MIT",
        "arquitectura": "XLM-RoBERTa (encoder)",
        "dim": 1024,
        "max_seq": 512,
        "query_prefix": "query: ",
        "passage_prefix": "passage: ",
    },
]

ENCODERS_BY_SLUG = {e["slug"]: e for e in ENCODERS}

EMBED_BATCH_SIZE = 64

# --------------------------------------------------------------------------- #
# Recuperación
# --------------------------------------------------------------------------- #

TOPK_PER_INDEX = 200  # candidatos que pide cada índice FAISS
RRF_K0 = 60  # constante de suavizado del Reciprocal Rank Fusion
MAX_CHUNKS_PER_DOC = 3  # tope de diversidad en el top-10 de fragmentos
# Agregación de fragmentos a documento: 0.0 = solo el mejor fragmento.
#
# La intuición de premiar a los documentos con varios pasajes relevantes resulta
# ser falsa con puntuaciones RRF, que decaen muy poco a lo largo del ranking
# (0,0164 en el puesto 1 frente a 0,0091 en el 50). Con cola, un documento con
# cinco fragmentos mediocres superaba a uno con un único fragmento excelente.
# Medido sobre bge_m3, barriendo 0,0 / 0,05 / 0,10 / 0,20 / 0,35:
#   peso 0,00 -> F1@3 mini gold 0,175, known-item@3 0,980
#   peso 0,35 -> F1@3 mini gold 0,125, known-item@3 0,870
# Monótono y coincidente en las dos señales, así que se agrega por máximo.
DOC_AGG_TAIL_WEIGHT = 0.0
DOC_AGG_TAIL_N = 0

# Supresión de documentos duplicados en el top-3. El corpus trae el mismo
# documento bajo nombres distintos (coseno 1,000 entre ILIA_2025 e
# ILIA_docuemnto-ilia-web) y ediciones traducidas del mismo informe. Sin esto,
# 17 de las 50 consultas gastaban dos de sus tres huecos en el mismo contenido.
# Se compara el centroide del documento en los tres encoders y se descarta solo
# si los tres coinciden en verlo como copia.
#
# Un único umbral no sirve. Medido sobre los centroides de bge_m3:
#   - traducciones del mismo informe (gcsr-2026-execsum-spa vs -por):  0,956
#   - ediciones distintas del mismo informe (MAPP/OEA 35 vs 36):       0,956
# Son indistinguibles por coseno. Y no da igual confundirlas: el mini gold marca
# la 35 y la 36 como relevantes A LA VEZ para una misma pregunta, así que podar a
# 0,95 costaría un acierto real.
#
# El idioma sí las separa, y viaja en la metadata (Sección 8.7 permite
# post-filtrar por metadata). De ahí dos reglas:
#   1. copia literal      -> coseno > 0,98, sea cual sea el idioma
#      (ILIA_documento-ilia-2025 e ILIA_docuemnto-ilia-web dan 1,000)
#   2. traducción         -> coseno > 0,95 Y idioma distinto
# Una edición posterior en el mismo idioma no cumple ninguna: se conserva.
DOC_DEDUP_COS = 0.98
DOC_DEDUP_COS_TRADUCCION = 0.95
FENOMENO_BOOST = 0.15  # prior suave por fenómeno (0 = desactivado)

N_DOCUMENTS_OUT = 3
N_FRAGMENTS_OUT = 10
MAX_WORDS_OUT = 250
EXPAND_TARGET_WORDS = 245  # al expandir con vecinos, hasta dónde llenar

# Se probó un reranker cross-encoder y se descartó: la Sección 8.3 exige que la
# recuperación opere "exclusivamente sobre vectores, puntuaciones de similitud y
# metadata", y un cross-encoder puntúa leyendo el par consulta-texto, no el
# espacio vectorial. Ni el código ni los pesos viajan en la entrega, por el mismo
# criterio que dejó fuera el baseline léxico.

# --------------------------------------------------------------------------- #
# Grafo de conocimiento (bonus)
# --------------------------------------------------------------------------- #

USE_GRAPH = os.environ.get("CODEFEST_USE_GRAPH", "1") == "1"
GRAPH_MAX_CHUNKS = 200  # candidatos que aporta el grafo a la fusión
GRAPH_WEIGHT = 0.5  # peso de la lista del grafo en el RRF frente a un índice denso


def ensure_dirs() -> None:
    for d in (DATA_DIR, REPORTS_DIR, ENTREGA_DIR, VECTORS_DIR, BASE_VECTORIAL_DIR, GRAFO_DIR):
        d.mkdir(parents=True, exist_ok=True)


def set_entrega_dir(path: Path | str) -> None:
    """Reapunta las rutas derivadas de la entrega.

    `generador.py` la llama al arrancar, porque en la máquina del jurado la
    entrega está en otro sitio y las rutas calculadas al importar el módulo
    (modelos, base vectorial, grafo) ya no valen.
    """
    global ENTREGA_DIR, BASE_VECTORIAL_DIR, GRAFO_DIR, RESULTADOS_JSONL
    ENTREGA_DIR = Path(path)
    BASE_VECTORIAL_DIR = ENTREGA_DIR / "base_vectorial"
    GRAFO_DIR = BASE_VECTORIAL_DIR / "grafo"
    RESULTADOS_JSONL = ENTREGA_DIR / "resultados.jsonl"
