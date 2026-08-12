"""Extracción de los 954 documentos JSON del corpus.

Los esquemas varían por observatorio (Sección 2.1: "interpretar el objeto y
seleccionar explícitamente los campos que contienen el texto"). Se detecta el
esquema por su forma, no por la ruta, para que un archivo mal ubicado no rompa
la extracción.

Los campos descriptivos (url, date, authors, tags) se conservan como metadata
del documento en vez de mezclarse con el cuerpo, como pide la especificación.
"""

from __future__ import annotations

import json

from .clean import clean_text, detect_language


def _as_text(value) -> str:
    """Aplana cualquier valor JSON a texto legible."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(p for p in (_as_text(v) for v in value) if p.strip())
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            t = _as_text(v)
            if t.strip():
                parts.append(f"{k}: {t}")
        return "\n".join(parts)
    return str(value)


def _join_body(obj: dict) -> str:
    """Cuerpo del artículo: prefiere body_text, cae a body_paragraphs."""
    body = obj.get("body_text")
    if isinstance(body, str) and len(body.strip()) > 40:
        return body
    paragraphs = obj.get("body_paragraphs")
    if isinstance(paragraphs, list) and paragraphs:
        return "\n\n".join(_as_text(p) for p in paragraphs)
    return _as_text(body)


def _sections_body(obj: dict) -> str:
    """Esquema CENIA: sections[].heading + paragraphs, más listas sueltas."""
    parts = []
    for sec in obj.get("sections") or []:
        if not isinstance(sec, dict):
            parts.append(_as_text(sec))
            continue
        heading = _as_text(sec.get("heading")).strip()
        if heading:
            parts.append(f"## {heading}")
        parts.append(_as_text(sec.get("paragraphs")))
    for item in obj.get("lists") or []:
        parts.append(_as_text(item))
    return "\n\n".join(p for p in parts if p.strip())


def _alerta_body(obj: dict) -> tuple[str, dict]:
    """Alertas Tempranas de la Defensoría (363 archivos).

    `alerta_meta` lleva el código, el tipo, la fecha y —crítico para el
    Fenómeno 3— los municipios y departamentos. Esos campos van al cuerpo del
    texto, porque las consultas preguntan por territorios concretos.
    """
    meta = obj.get("alerta_meta") or {}
    fields = obj.get("fields") or {}
    header = []
    if meta.get("codigo"):
        header.append(f"Alerta Temprana {meta['codigo']}")
    if meta.get("tipo"):
        header.append(f"Tipo de alerta: {meta['tipo']}")
    if meta.get("fecha_emision"):
        header.append(f"Fecha de emisión: {meta['fecha_emision']}")
    if meta.get("municipios"):
        header.append(f"Municipios y departamentos en riesgo: {meta['municipios']}")
    if meta.get("tema_clave"):
        header.append(f"Escenario de riesgo: {meta['tema_clave']}")
    if fields:
        header.append(_as_text(fields))

    body = "\n".join(header)
    paragraphs = _as_text(obj.get("body_paragraphs"))
    if paragraphs.strip():
        body += "\n\n" + paragraphs

    extra = {
        "codigo_alerta": meta.get("codigo", ""),
        "tipo_alerta": meta.get("tipo", ""),
        "municipios": meta.get("municipios", ""),
    }
    # El campo `title` de estos archivos suele ser "Mapa", inútil. El título real
    # es el código de alerta más los municipios, que es lo que buscan las consultas.
    titulo = " — ".join(
        p for p in (
            f"Alerta Temprana {meta['codigo']}" if meta.get("codigo") else "",
            meta.get("municipios", ""),
        ) if p
    )
    return body, extra, titulo


def _abstract_body(obj: dict) -> str:
    """Esquema CEEEP: solo título, resumen y palabras clave, sin cuerpo."""
    parts = [_as_text(obj.get("abstract"))]
    kw = _as_text(obj.get("keywords"))
    if kw.strip():
        parts.append(f"Palabras clave: {kw}")
    return "\n\n".join(p for p in parts if p.strip())


def extract_json(path) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            obj = json.load(fh)
    except Exception as exc:
        return {"text": "", "titulo": "", "idioma": "und", "extra": {}, "error": str(exc)}

    if isinstance(obj, list):
        # Feeds y manifiestos: una lista de registros homogéneos
        text = "\n\n".join(_as_text(o) for o in obj)
        return _finish(text, "", {}, {})

    if not isinstance(obj, dict):
        return _finish(_as_text(obj), "", {}, {})

    titulo = _as_text(obj.get("title") or obj.get("titulo") or obj.get("nombre") or "").strip()
    extra = {}

    if "alerta_meta" in obj:
        body, extra, titulo_alerta = _alerta_body(obj)
        if titulo_alerta:
            titulo = titulo_alerta
    elif "sections" in obj:
        body = _sections_body(obj)
    elif "abstract" in obj and "body_text" not in obj:
        body = _abstract_body(obj)
    elif "body_text" in obj or "body_paragraphs" in obj:
        body = _join_body(obj)
    else:
        # Manifiestos de descarga (DAIO, MAPP, RESDAL, RutaN, Defensa21, tiles):
        # no tienen cuerpo, se aplanan a "clave: valor".
        body = _as_text({k: v for k, v in obj.items() if k not in ("images", "links")})

    # El resumen aporta señal y suele no estar en el cuerpo
    excerpt = _as_text(obj.get("excerpt")).strip()
    if excerpt and excerpt not in body:
        body = f"{excerpt}\n\n{body}"

    meta = {
        "url": _as_text(obj.get("url") or obj.get("detail_url") or ""),
        "fecha": _as_text(obj.get("date") or obj.get("year") or ""),
        "autores": _as_text(obj.get("authors")),
        "temas": _as_text(obj.get("topics") or obj.get("tags") or obj.get("categories") or obj.get("keywords")),
    }
    return _finish(body, titulo, meta, extra)


def _finish(body: str, titulo: str, meta: dict, extra: dict) -> dict:
    text = clean_text(body)
    return {
        "text": text,
        "titulo": clean_text(titulo)[:300],
        "idioma": detect_language(f"{titulo} {text}"),
        "url": meta.get("url", ""),
        "fecha": meta.get("fecha", ""),
        "extra": {**extra, **{k: v for k, v in meta.items() if k in ("autores", "temas") and v}},
    }
