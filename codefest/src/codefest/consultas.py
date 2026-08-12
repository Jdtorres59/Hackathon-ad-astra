"""Lectura del archivo de consultas.

La especificación (Tabla 1) dice que `generador.py` recibe `consultas.jsonl`
pero no fija el nombre de sus campos. Este lector acepta las variantes
razonables para que el script del jurado no falle por una diferencia de nombre.
También acepta un JSON array en vez de JSON Lines.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ID_KEYS = ("query_id", "queryid", "id", "qid", "consulta_id", "pregunta_id")
TEXT_KEYS = ("query", "texto", "text", "consulta", "pregunta", "question", "enunciado")


def _pick(obj: dict, keys: tuple[str, ...]) -> str:
    for k in keys:
        for actual in obj:
            if actual.lower() == k:
                val = obj[actual]
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return ""


def load_consultas(path: str | Path) -> list[dict]:
    """Devuelve [{'query_id': 'q001', 'texto': '¿...?'}, ...] en orden de archivo."""
    raw = Path(path).read_text(encoding="utf-8")

    objs: list[dict] = []
    stripped = raw.lstrip()
    if stripped.startswith("["):
        objs = json.loads(raw)
    else:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                objs.append(obj)

    out: list[dict] = []
    for i, obj in enumerate(objs, start=1):
        if not isinstance(obj, dict):
            continue
        qid = _pick(obj, ID_KEYS) or f"q{i:03d}"
        texto = _pick(obj, TEXT_KEYS)
        if not texto:
            # Objeto con un solo campo de texto y nombre inesperado
            candidates = [v for v in obj.values() if isinstance(v, str) and len(v) > 20]
            texto = candidates[0].strip() if candidates else ""
        out.append({"query_id": qid, "texto": texto})
    return out


# --------------------------------------------------------------------------- #
# Construcción del archivo de consultas a partir del PDF del corpus
# --------------------------------------------------------------------------- #

_Q_MARK = re.compile(r"\bq0*(\d{1,3})\b", re.IGNORECASE)


def parse_preguntas_pdf(pdf_path: str | Path) -> list[dict]:
    """Extrae q001..q050 de `Extracto_Preguntas_50_v2.pdf`."""
    import pymupdf

    doc = pymupdf.open(pdf_path)
    text = "\n".join(page.get_text("text", sort=True) for page in doc)
    doc.close()

    # Las preguntas van pegadas: se corta en cada marcador qNNN
    marks = list(_Q_MARK.finditer(text))
    out: list[dict] = []
    for i, m in enumerate(marks):
        start = m.end()
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        body = " ".join(text[start:end].split()).strip()
        if not body:
            continue
        out.append({"query_id": f"q{int(m.group(1)):03d}", "texto": body})

    # Deduplica por id conservando la primera aparición
    seen: set[str] = set()
    dedup = []
    for q in out:
        if q["query_id"] in seen:
            continue
        seen.add(q["query_id"])
        dedup.append(q)
    return sorted(dedup, key=lambda q: q["query_id"])
