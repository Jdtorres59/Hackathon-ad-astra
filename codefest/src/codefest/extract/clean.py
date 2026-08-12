"""Limpieza y normalización de texto (Sección 2.2 de la especificación).

- eliminación de caracteres de control y espacios redundantes
- normalización de codificación a UTF-8 (NFC)
- desguionizado de palabras cortadas por salto de línea
- detección del idioma predominante
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

# Caracteres de control salvo tab y salto de línea
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
# Ligaduras y comillas tipográficas que confunden a los tokenizadores
_REPLACEMENTS = {
    "ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl",
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "…": "...", " ": " ",
    "​": "", "‌": "", "‍": "", "﻿": "",
}
_HYPHEN_BREAK = re.compile(r"(\w)[-‐‑]\s*\n\s*(\w)")
# El guion blando (U+00AD) es una marca de guionado discrecional del PDF, nunca
# contenido: donde aparece, la palabra está partida. PyMuPDF a veces convierte el
# salto de línea que lo seguía en un espacio, así que `_HYPHEN_BREAK` no lo veía
# y el índice acababa con "align ment" y "contribu tions" en 182 documentos.
# A diferencia del guion visible, este se une siempre: "two- and three-dimensional"
# lleva guion normal y debe conservarse, pero un U+00AD jamás es legítimo.
_SOFT_HYPHEN_BREAK = re.compile(r"(\w)\xad\s*(\w)")
_SOFT_HYPHEN_SUELTO = re.compile(r"\xad")
_MULTI_SPACE = re.compile(r"[^\S\n]+")  # espacios en blanco salvo el salto de línea
_MULTI_NEWLINE = re.compile(r"\n{3,}")
_SPACE_BEFORE_NEWLINE = re.compile(r"[ \t]+\n")


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    for src, dst in _REPLACEMENTS.items():
        text = text.replace(src, dst)
    text = _CONTROL.sub("", text)
    text = _HYPHEN_BREAK.sub(r"\1\2", text)
    text = _SOFT_HYPHEN_BREAK.sub(r"\1\2", text)
    text = _SOFT_HYPHEN_SUELTO.sub("", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = _SPACE_BEFORE_NEWLINE.sub("\n", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    return text.strip()


# --------------------------------------------------------------------------- #
# Detección de idioma
#
# El corpus es es/en/pt. Un clasificador por palabras funcionales es suficiente,
# rapidísimo y sin dependencias — y evita los falsos positivos de langdetect en
# textos cortos o con mucha jerga técnica.
# --------------------------------------------------------------------------- #

_STOPWORDS = {
    "es": {
        "de", "la", "que", "el", "en", "y", "a", "los", "del", "se", "las", "por", "un",
        "para", "con", "no", "una", "su", "al", "es", "lo", "como", "más", "pero", "sus",
        "ha", "o", "este", "sí", "porque", "esta", "entre", "cuando", "muy", "sobre",
        "también", "hasta", "hay", "donde", "quien", "desde", "todo", "nos", "durante",
    },
    "en": {
        "the", "of", "and", "to", "in", "a", "is", "that", "for", "it", "as", "was",
        "with", "be", "by", "on", "not", "he", "this", "are", "or", "his", "from", "at",
        "which", "but", "have", "an", "they", "you", "were", "their", "has", "will",
        "been", "would", "there", "we", "these", "its", "also", "more", "can", "such",
    },
    "pt": {
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não",
        "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "ao",
        "ele", "das", "à", "seu", "sua", "ou", "quando", "muito", "nos", "já", "eu",
        "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "depois", "sem",
    },
}
# Marcadores ortográficos: presencia fuerte de estos caracteres desempata es/pt
_PT_MARKERS = re.compile(r"[ãõâêô]")
_ES_MARKERS = re.compile(r"[ñ¿¡]")
_WORD = re.compile(r"[a-záéíóúüñàâãêôõçè]+", re.IGNORECASE)


def detect_language(text: str) -> str:
    """Devuelve 'es', 'en', 'pt' o 'und' si no hay evidencia suficiente."""
    sample = text[:20000].lower()
    words = _WORD.findall(sample)
    if len(words) < 15:
        return "und"
    counts = Counter(words)
    scores = {
        lang: sum(counts[w] for w in sw) / len(words)
        for lang, sw in _STOPWORDS.items()
    }
    # es y pt comparten muchas palabras funcionales; los marcadores desempatan
    pt_marks = len(_PT_MARKERS.findall(sample)) / max(len(sample), 1)
    es_marks = len(_ES_MARKERS.findall(sample)) / max(len(sample), 1)
    scores["pt"] += pt_marks * 12
    scores["es"] += es_marks * 12

    best = max(scores, key=scores.get)
    return best if scores[best] > 0.02 else "und"


# --------------------------------------------------------------------------- #
# Supresión de cabeceras y pies repetidos (boilerplate)
# --------------------------------------------------------------------------- #

_PAGE_NUM = re.compile(r"^\s*(?:p[áa]g(?:ina)?\.?\s*)?[-–—|]?\s*\d{1,4}\s*[-–—|]?\s*$", re.IGNORECASE)


def drop_repeated_lines(pages: list[str], min_ratio: float = 0.3, band: int = 3) -> list[str]:
    """Elimina líneas que se repiten en la parte alta o baja de muchas páginas.

    Una línea que aparece en la primera o última `band` líneas de al menos
    `min_ratio` de las páginas es cabecera o pie, no contenido.
    """
    if len(pages) < 4:
        return [_strip_page_numbers(p) for p in pages]

    counter: Counter[str] = Counter()
    for page in pages:
        lines = [ln.strip() for ln in page.split("\n") if ln.strip()]
        candidates = set(lines[:band]) | set(lines[-band:])
        counter.update(candidates)

    threshold = max(3, int(len(pages) * min_ratio))
    boiler = {ln for ln, c in counter.items() if c >= threshold and len(ln) < 200}

    out = []
    for page in pages:
        lines = [ln for ln in page.split("\n") if ln.strip() not in boiler]
        out.append(_strip_page_numbers("\n".join(lines)))
    return out


def _strip_page_numbers(page: str) -> str:
    return "\n".join(ln for ln in page.split("\n") if not _PAGE_NUM.match(ln))
