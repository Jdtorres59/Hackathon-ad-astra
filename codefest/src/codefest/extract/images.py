"""OCR de las 9 imágenes del corpus (Sección 2.1).

Son portadas y figuras de informes. Cuando contienen texto legible (infografías,
gráficos con etiquetas) el OCR lo recupera; cuando no, el documento queda con
texto mínimo pero conserva su doc_id y su entrada en el índice.
"""

from __future__ import annotations

from pathlib import Path

from .clean import clean_text, detect_language

OCR_LANGS = "spa+eng+por"


def extract_image(path) -> dict:
    path = Path(path)
    text = ""
    try:
        import pytesseract
        from PIL import Image

        with Image.open(path) as img:
            text = pytesseract.image_to_string(img.convert("RGB"), lang=OCR_LANGS)
    except Exception as exc:  # formato no soportado (avif) o OCR no disponible
        return {
            "text": clean_text(f"Imagen del corpus: {path.stem.replace('_', ' ').replace('-', ' ')}"),
            "titulo": path.stem,
            "idioma": "und",
            "extra": {"ocr_error": str(exc)},
        }

    text = clean_text(text)
    if len(text) < 20:
        text = clean_text(f"Imagen del corpus: {path.stem.replace('_', ' ').replace('-', ' ')}")

    return {
        "text": text,
        "titulo": path.stem,
        "idioma": detect_language(text),
        "extra": {"ocr": True},
    }
