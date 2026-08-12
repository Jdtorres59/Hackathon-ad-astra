"""Despachador de extracción: enruta cada documento a su extractor por formato."""

from __future__ import annotations

from ..inventory import DocRecord
from .clean import clean_text, detect_language
from .images import extract_image
from .jsonsrc import extract_json
from .pbf import extract_pbf
from .pdf import extract_pdf
from .tabular import extract_tabular

__all__ = ["extract_document", "clean_text", "detect_language"]


def extract_document(doc: DocRecord, *, allow_ocr: bool = True) -> dict:
    """Devuelve un registro de documento extraído, listo para serializar."""
    fmt = doc.formato
    try:
        if fmt == "pdf":
            res = extract_pdf(doc.path, allow_ocr=allow_ocr)
        elif fmt == "json":
            res = extract_json(doc.path)
        elif fmt in ("csv", "xlsx"):
            res = extract_tabular(doc.path)
        elif fmt == "pbf":
            res = extract_pbf(doc.path)
        elif fmt == "imagen":
            res = extract_image(doc.path)
        elif fmt == "txt":
            raw = doc.path.read_text(encoding="utf-8", errors="replace")
            text = clean_text(raw)
            res = {"text": text, "titulo": doc.path.stem, "idioma": detect_language(text), "extra": {}}
        else:
            res = {"text": "", "titulo": doc.path.stem, "idioma": "und", "extra": {"formato_no_soportado": fmt}}
    except Exception as exc:
        res = {"text": "", "titulo": doc.path.stem, "idioma": "und", "extra": {}, "error": f"{type(exc).__name__}: {exc}"}

    titulo = (res.get("titulo") or "").strip() or doc.fuente
    return {
        "doc_id": doc.doc_id,
        "doc_id_inventario": doc.doc_id_inventario,
        "doc_id_secuencial": doc.doc_id_secuencial,
        "fuente": doc.fuente,
        "ruta_relativa": doc.ruta_relativa,
        "formato": doc.formato,
        "fenomeno": doc.fenomeno,
        "observatorio": doc.observatorio,
        "titulo": titulo,
        "idioma": res.get("idioma", "und"),
        "fecha": res.get("fecha", ""),
        "url": res.get("url", ""),
        "texto": res.get("text", ""),
        "n_chars": len(res.get("text", "")),
        "n_pages": res.get("n_pages", 0),
        "n_ocr_pages": res.get("n_ocr_pages", 0),
        "blocks": res.get("blocks"),  # tabulares: bloques ya delimitados por filas
        "extra": res.get("extra", {}),
        "error": res.get("error", ""),
    }
