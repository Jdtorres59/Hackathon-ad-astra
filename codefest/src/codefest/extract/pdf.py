"""Extracción de texto de PDFs (Sección 2.1 de la especificación).

Preserva el orden de lectura, suprime cabeceras y pies repetidos, y cae a OCR
en las páginas que no tienen capa de texto. Alrededor del 14% de los PDFs del
corpus son escaneados —entre ellos los informes de Alertas Tempranas, que son
material central para el Fenómeno 3—, así que el OCR no es opcional.
"""

from __future__ import annotations

import io
import re

import pymupdf

from .clean import clean_text, detect_language, drop_repeated_lines

# Por debajo de esto una página se considera sin capa de texto útil
MIN_CHARS_PER_PAGE = 60
OCR_DPI = 220
# El OCR multilingüe es ~3x más lento; se usa solo para adivinar el idioma en
# las primeras páginas y luego se fija uno solo.
OCR_PROBE_LANGS = "spa+eng+por"
OCR_LANG_BY_CODE = {"es": "spa", "en": "eng", "pt": "por", "und": OCR_PROBE_LANGS}

_HEADING = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?[A-ZÁÉÍÓÚÑÜ][^\n]{2,90}$")


def _detectar_columnas(bloques: list, ancho: float) -> list[float] | None:
    """Devuelve las fronteras de columna, o None si la página es de una columna.

    Se proyectan los bloques sobre el eje horizontal y se busca una franja
    vertical sin texto que separe dos grupos con masa parecida. Ordenar esa
    página por coordenada vertical, como hace `sort=True`, entrelazaría las
    columnas y produciría frases sin sentido.
    """
    cuerpos = [b for b in bloques if b[4].strip() and (b[3] - b[1]) > 8]
    if len(cuerpos) < 6:
        return None

    # Solo cuentan los bloques que no cruzan de lado a lado (títulos, tablas)
    estrechos = [b for b in cuerpos if (b[2] - b[0]) < ancho * 0.62]
    if len(estrechos) < max(4, len(cuerpos) * 0.5):
        return None

    ocupado = [False] * 100
    for b in estrechos:
        desde = max(0, int(b[0] / ancho * 100))
        hasta = min(99, int(b[2] / ancho * 100))
        for i in range(desde, hasta + 1):
            ocupado[i] = True

    # Busca el hueco más ancho dentro de la zona central de la página
    mejor_inicio = mejor_largo = 0
    i = 20
    while i < 80:
        if not ocupado[i]:
            j = i
            while j < 80 and not ocupado[j]:
                j += 1
            if j - i > mejor_largo:
                mejor_inicio, mejor_largo = i, j - i
            i = j
        else:
            i += 1

    if mejor_largo < 4:
        return None

    corte = (mejor_inicio + mejor_largo / 2) / 100 * ancho
    izquierda = sum(1 for b in estrechos if (b[0] + b[2]) / 2 < corte)
    derecha = len(estrechos) - izquierda
    # Un reparto muy desigual significa que el hueco era un margen, no una columna
    if min(izquierda, derecha) < len(estrechos) * 0.25:
        return None
    return [corte]


def _page_text(page: pymupdf.Page) -> str:
    """Texto de una página respetando su orden de lectura real."""
    try:
        bloques = page.get_text("blocks")
    except Exception:
        return page.get_text("text") or ""

    bloques = [b for b in bloques if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()]
    if not bloques:
        return ""

    ancho = page.rect.width or 1.0
    cortes = _detectar_columnas(bloques, ancho)

    if not cortes:
        bloques.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
        return "\n\n".join(b[4].strip() for b in bloques)

    corte = cortes[0]

    def cruza(b) -> bool:
        """Bloque a todo el ancho: un título de sección, una tabla, un pie."""
        return b[0] < corte < b[2] and (b[2] - b[0]) > ancho * 0.62

    # La página se divide en franjas horizontales delimitadas por los bloques
    # que ocupan todo el ancho. Dentro de cada franja se lee columna a columna;
    # entre franjas se respeta el orden vertical. Así un título intermedio o una
    # tabla no se llevan por delante el orden de lectura de las columnas.
    bloques.sort(key=lambda b: (round(b[1], 1), round(b[0], 1)))
    franja = 0
    anotados = []
    for b in bloques:
        if cruza(b):
            franja += 1
            anotados.append((franja, 0, b))
            franja += 1
        else:
            columna = 1 if (b[0] + b[2]) / 2 < corte else 2
            anotados.append((franja, columna, b))

    anotados.sort(key=lambda t: (t[0], t[1], round(t[2][1], 1), round(t[2][0], 1)))
    return "\n\n".join(b[4].strip() for _, _, b in anotados)


def _ocr_page(page: pymupdf.Page, lang: str) -> str:
    import pytesseract
    from PIL import Image

    pix = page.get_pixmap(dpi=OCR_DPI)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    try:
        return pytesseract.image_to_string(img, lang=lang)
    except Exception:
        return ""


def extract_pdf(path, *, allow_ocr: bool = True, max_pages: int | None = None) -> dict:
    """Devuelve {'text', 'n_pages', 'n_ocr_pages', 'titulo', 'idioma'}."""
    try:
        doc = pymupdf.open(path)
    except Exception as exc:
        return {"text": "", "n_pages": 0, "n_ocr_pages": 0, "titulo": "", "idioma": "und", "error": str(exc)}

    n_pages = doc.page_count
    limit = n_pages if max_pages is None else min(n_pages, max_pages)

    raw_pages: list[str] = []
    needs_ocr: list[int] = []
    for i in range(limit):
        text = _page_text(doc[i])
        raw_pages.append(text)
        if allow_ocr and len(text.strip()) < MIN_CHARS_PER_PAGE:
            needs_ocr.append(i)

    n_ocr = 0
    if needs_ocr:
        # Adivina el idioma con las 2 primeras páginas que necesitan OCR y luego
        # fija ese idioma para el resto: spa+eng+por es ~3x más lento por página.
        probe_idx = needs_ocr[:2]
        probe_texts = {i: _ocr_page(doc[i], OCR_PROBE_LANGS) for i in probe_idx}
        lang = OCR_LANG_BY_CODE[detect_language("\n".join(probe_texts.values()))]

        for i in needs_ocr:
            text = probe_texts[i] if i in probe_texts else _ocr_page(doc[i], lang)
            if len(text.strip()) >= MIN_CHARS_PER_PAGE:
                raw_pages[i] = text
                n_ocr += 1

    titulo = (doc.metadata or {}).get("title", "") or ""
    doc.close()

    pages = drop_repeated_lines([clean_text(p) for p in raw_pages])
    text = clean_text("\n\n".join(p for p in pages if p.strip()))

    if not titulo.strip() or len(titulo.strip()) < 4:
        titulo = _guess_title(pages)

    return {
        "text": text,
        "n_pages": n_pages,
        "n_ocr_pages": n_ocr,
        "titulo": clean_text(titulo)[:300],
        "idioma": detect_language(text),
    }


def _guess_title(pages: list[str]) -> str:
    """Primera línea sustantiva de la primera página con contenido."""
    for page in pages[:3]:
        for line in page.split("\n"):
            line = line.strip()
            if 12 <= len(line) <= 160 and not line.isdigit() and _HEADING.match(line):
                return line
    return ""
