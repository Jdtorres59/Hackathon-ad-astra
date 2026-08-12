"""Construcción y validación del archivo de resultados (Sección 9).

El esquema de la Tabla 3 es estricto: exactamente 3 documentos y 10 fragmentos
por consulta, y ningún fragmento por encima de 250 palabras. La especificación
advierte que los objetos mal formados "serán penalizados o descartados durante
la evaluación automática", así que aquí se construye y se verifica.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from . import config

_SENT_END = re.compile(r"[.!?…][\"'»)\]]*\s")


def word_count(text: str) -> int:
    return len(text.split())


def truncate_to_words(text: str, max_words: int) -> str:
    """Recorta a `max_words` cortando en el último final de oración que quepa.

    Red de seguridad: con el tope de fragmento en 240 palabras esto no debería
    dispararse nunca, pero si se disparara respeta la completitud lingüística
    de la Sección 3.3 en lugar de cortar a mitad de frase.
    """
    words = text.split()
    if len(words) <= max_words:
        return text
    recorte = " ".join(words[:max_words])
    ends = list(_SENT_END.finditer(recorte + " "))
    if ends and ends[-1].end() > len(recorte) * 0.5:
        return recorte[: ends[-1].end()].strip()
    return recorte.strip()


def build_result(query_id: str, hits: dict) -> dict:
    """Convierte la salida del Retriever en el objeto JSON de la Tabla 3."""
    documents = [
        {"rank": d["rank"], "doc_id": d["doc_id"]}
        for d in hits["documents"][: config.N_DOCUMENTS_OUT]
    ]
    fragments = []
    for f in hits["fragments"][: config.N_FRAGMENTS_OUT]:
        fragments.append(
            {
                "rank": f["rank"],
                "chunk_id": f["chunk_id"],
                "doc_id": f["doc_id"],
                "text": truncate_to_words(f["text"], config.MAX_WORDS_OUT),
            }
        )
    return {"query_id": query_id, "documents": documents, "fragments": fragments}


def write_results(results: list[dict], path: Path | str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in results:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- #
# Validación
# --------------------------------------------------------------------------- #


def validate_results(path: Path | str, *, n_expected: int = 50) -> dict:
    """Comprueba el archivo contra el esquema de la Sección 9.3. Devuelve un informe."""
    path = Path(path)
    errores: list[str] = []
    avisos: list[str] = []

    if not path.exists():
        return {"ok": False, "errores": [f"no existe {path}"], "avisos": [], "n_lineas": 0}

    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    if len(lines) != n_expected:
        errores.append(f"el archivo tiene {len(lines)} líneas, se esperaban exactamente {n_expected}")

    max_words = 0
    query_ids: list[str] = []

    for i, line in enumerate(lines, start=1):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            errores.append(f"línea {i}: JSON inválido ({exc})")
            continue

        for campo in ("query_id", "documents", "fragments"):
            if campo not in obj:
                errores.append(f"línea {i}: falta el campo '{campo}'")
        if "query_id" not in obj:
            continue
        query_ids.append(obj["query_id"])

        docs = obj.get("documents", [])
        if not isinstance(docs, list) or len(docs) != config.N_DOCUMENTS_OUT:
            errores.append(f"línea {i} ({obj['query_id']}): documents tiene {len(docs)} elementos, se esperaban {config.N_DOCUMENTS_OUT}")
        for j, d in enumerate(docs, start=1):
            if not isinstance(d, dict) or set(d) != {"rank", "doc_id"}:
                errores.append(f"línea {i}: documents[{j}] debe tener exactamente rank y doc_id, tiene {sorted(d) if isinstance(d, dict) else type(d)}")
            elif d["rank"] != j:
                errores.append(f"línea {i}: documents[{j}] tiene rank={d['rank']}, se esperaba {j}")

        frags = obj.get("fragments", [])
        if not isinstance(frags, list) or len(frags) != config.N_FRAGMENTS_OUT:
            errores.append(f"línea {i} ({obj['query_id']}): fragments tiene {len(frags)} elementos, se esperaban {config.N_FRAGMENTS_OUT}")
        vistos_doc = set()
        for j, f in enumerate(frags, start=1):
            if not isinstance(f, dict) or set(f) != {"rank", "chunk_id", "doc_id", "text"}:
                errores.append(f"línea {i}: fragments[{j}] debe tener exactamente rank, chunk_id, doc_id y text")
                continue
            if f["rank"] != j:
                errores.append(f"línea {i}: fragments[{j}] tiene rank={f['rank']}, se esperaba {j}")
            wc = word_count(f["text"])
            max_words = max(max_words, wc)
            if wc > config.MAX_WORDS_OUT:
                errores.append(f"línea {i}: fragments[{j}] tiene {wc} palabras (máximo {config.MAX_WORDS_OUT})")
            if wc < 10:
                avisos.append(f"línea {i}: fragments[{j}] tiene solo {wc} palabras")
            vistos_doc.add(f["doc_id"])
        if frags and len(vistos_doc) == 1:
            avisos.append(f"línea {i} ({obj['query_id']}): los 10 fragmentos vienen del mismo documento")

    # Los query_id se copian tal cual del archivo de consultas: si el jurado usa
    # otra nomenclatura (`Q001`, `q1`, `pregunta_1`), la salida sigue siendo
    # válida y no debe devolver código de error. `consultas.py` ya acepta esas
    # variantes a propósito; sería contradictorio rechazarlas aquí. Lo que sí es
    # error es repetir un id, porque entonces hay una consulta sin respuesta.
    repetidos = sorted({q for q in query_ids if query_ids.count(q) > 1})
    if repetidos:
        errores.append(f"query_id repetidos: {repetidos[:5]}")

    esperados = [f"q{i:03d}" for i in range(1, n_expected + 1)]
    if query_ids and query_ids != esperados and not repetidos:
        avisos.append(
            "los query_id no siguen el orden q001..q050; se conservaron los del "
            f"archivo de consultas (primero: {query_ids[0]!r})"
        )

    return {
        "ok": not errores,
        "errores": errores,
        "avisos": avisos,
        "n_lineas": len(lines),
        "max_palabras_fragmento": max_words,
    }
