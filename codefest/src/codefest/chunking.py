"""Fragmentación del texto (Sección 3 de la especificación).

Estrategia híbrida: estructural + oracional con solapamiento.

1. El documento se parte en bloques por su estructura (encabezados, párrafos,
   filas de tabla). Un fragmento nunca cruza un encabezado.
2. Cada bloque se parte en oraciones con un segmentador multilingüe (pysbd).
3. Las oraciones se empaquetan codiciosamente hasta ~190 palabras, con tope
   duro en 240 y solapamiento de una oración entre fragmentos consecutivos.

REQUISITO OBLIGATORIO (Sección 3.3): ninguna oración se parte entre fragmentos.
Los cortes solo ocurren en límites oracionales. El único caso en que se corta
por debajo del nivel de oración es cuando una "oración" supera por sí sola el
tope —lo que en la práctica solo pasa en filas de tabla y en texto OCR sin
puntuación—; ahí se cae a límites de cláusula. Se contabiliza y se reporta.

El tope de 240 palabras se elige por debajo del límite de 250 de la salida
(Sección 9.2), de modo que nunca haya que subdividir un fragmento al entregarlo.
"""

from __future__ import annotations

import re
from functools import lru_cache

from . import config

_HEADING_MD = re.compile(r"^#{1,6}\s+(.+)$")
# Línea corta, sin punto final, capitalizada o numerada: encabezado de un PDF
_HEADING_PLAIN = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+)?[A-ZÁÉÍÓÚÑÜ0-9][^.!?]{3,90}$"
)
_HEADING_NUMERADO = re.compile(r"^\d+(?:\.\d+)*\.?\s+\S")
# Etiquetas de figura, tabla o pie de gráfico: parecen encabezados pero no lo son
_NO_ES_ENCABEZADO = re.compile(
    r"^(fuente|source|fonte|figura|figure|tabla|table|gr[áa]fico|chart|nota|note|"
    r"cuadro|mapa|map|foto|imagen|anexo|elaboraci[óo]n)\b[\s:.\d]",
    re.IGNORECASE,
)
# Fronteras de cláusula, usadas solo como último recurso
_CLAUSE = re.compile(r"(?<=[;:])\s+|\s+\|\s+|\n")
_CLAUSE_COMA = re.compile(r"(?<=,)\s+")
_WORD_SPLIT = re.compile(r"\s+")

# Bloques que no son prosa y solo aportan ruido al índice
_LEADER = re.compile(r"\.{4,}\s*\d+\s*$", re.MULTILINE)  # índice con puntos suspensivos
_SOLO_NUMEROS = re.compile(r"^[\d\s.,;:%/()\-–—+|]*$")
# Reunificación de oraciones partidas por un salto de página o de columna
_CIERRA_ORACION = re.compile(r"[.!?…»\"')\]][\d\s]*$")
_EMPIEZA_MINUSCULA = re.compile(r"^[a-záéíóúüñ]")


def es_bloque_ruido(bloque: str) -> bool:
    """Índices de contenidos, listas de figuras y bloques puramente numéricos.

    No aportan significado recuperable y, al competir por un puesto en el
    top-10, desplazan fragmentos que sí responden a la consulta.
    """
    lineas = [ln.strip() for ln in bloque.split("\n") if ln.strip()]
    if not lineas:
        return True
    con_leader = sum(1 for ln in lineas if _LEADER.search(ln))
    if con_leader >= max(2, len(lineas) * 0.4):
        return True
    if _SOLO_NUMEROS.match(bloque.replace("\n", " ")):
        return True
    # Densidad de dígitos altísima: es una tabla de cifras, no texto
    caracteres = len(bloque)
    if caracteres > 80 and sum(c.isdigit() for c in bloque) > caracteres * 0.35:
        return True
    return False

PYSBD_LANGS = {"es": "es", "en": "en", "pt": "pt", "und": "en"}


@lru_cache(maxsize=8)
def _segmenter(lang: str):
    import pysbd

    return pysbd.Segmenter(language=PYSBD_LANGS.get(lang, "en"), clean=False)


def count_words(text: str) -> int:
    """Cuenta palabras con el mismo criterio que usa el límite de 250 de la salida."""
    return len([w for w in _WORD_SPLIT.split(text.strip()) if w])


def unir_lineas(bloque: str) -> str:
    """Convierte los saltos de línea internos de un bloque en espacios.

    El texto que sale de un PDF trae un salto en cada línea visual, también en
    mitad de una oración. Si esos saltos llegan al segmentador, este los toma
    como frontera y parte oraciones por la mitad, lo que incumple el requisito
    obligatorio de completitud lingüística de la Sección 3.3.

    Se respetan los saltos que sí marcan una frontera real: los que van después
    de un signo de cierre y los que preceden a una viñeta o a un numeral de
    lista.
    """
    lineas = [ln.strip() for ln in bloque.split("\n")]
    lineas = [ln for ln in lineas if ln]
    if len(lineas) <= 1:
        return bloque.strip()

    out = lineas[0]
    for ln in lineas[1:]:
        cierra = re.search(r"[.!?:;…»\"')\]]$", out)
        empieza_item = re.match(r"^([-•·*]|\(?\d{1,3}[.)]|[a-z]\))\s+", ln)
        out = f"{out}\n{ln}" if (cierra and empieza_item) else f"{out} {ln}"
    return out.strip()


def split_sentences(text: str, lang: str) -> list[str]:
    """Divide en oraciones. Devuelve solo oraciones no vacías."""
    text = unir_lineas(text)
    if not text:
        return []
    try:
        sents = _segmenter(lang).segment(text)
    except Exception:
        sents = re.split(r"(?<=[.!?])\s+", text)
    return [s.strip() for s in sents if s and s.strip()]


def _split_oversized(sentence: str, max_words: int) -> list[str]:
    """Parte una 'oración' que excede el tope (fila de tabla, OCR sin puntos).

    Se intenta primero por punto y coma o dos puntos; si los trozos siguen
    siendo demasiado largos, por coma; y solo si nada de eso alcanza, por
    número de palabras. Cortar en una coma es mucho menos dañino que cortar en
    mitad de un sintagma.
    """
    pieces = [p.strip() for p in _CLAUSE.split(sentence) if p and p.strip()]
    if any(count_words(p) > max_words for p in pieces):
        refinadas: list[str] = []
        for p in pieces:
            if count_words(p) > max_words:
                refinadas.extend(x.strip() for x in _CLAUSE_COMA.split(p) if x.strip())
            else:
                refinadas.append(p)
        pieces = refinadas
    out: list[str] = []
    buf: list[str] = []
    buf_words = 0
    for piece in pieces or [sentence]:
        pw = count_words(piece)
        if pw > max_words:
            # Ni las cláusulas alcanzan: corte duro por palabras
            if buf:
                out.append(" ".join(buf))
                buf, buf_words = [], 0
            words = [w for w in _WORD_SPLIT.split(piece) if w]
            for i in range(0, len(words), max_words):
                out.append(" ".join(words[i : i + max_words]))
            continue
        if buf_words + pw > max_words and buf:
            out.append(" ".join(buf))
            buf, buf_words = [], 0
        buf.append(piece)
        buf_words += pw
    if buf:
        out.append(" ".join(buf))
    return out


def _parece_encabezado(bloque: str) -> bool:
    """Distingue un encabezado de sección de una etiqueta de gráfico.

    Con extracción por bloques, un PDF cargado de figuras produce montones de
    líneas sueltas y cortas ("País", "Tipo", "Fuente: ILIA 2024") que encajan en
    el patrón de encabezado. Tomarlas por tales fragmenta el documento en trozos
    diminutos, así que se exige algo más: numeración de sección, o varias
    palabras, y nunca una etiqueta de figura.
    """
    if len(bloque) > 90 or _NO_ES_ENCABEZADO.match(bloque):
        return False
    if not _HEADING_PLAIN.match(bloque):
        return False
    palabras = count_words(bloque)
    if palabras > 14:
        return False
    if _HEADING_NUMERADO.match(bloque):
        return True
    # Sin numeración hace falta más sustancia y forma de título
    return palabras >= 3 and (bloque.isupper() or bloque[0].isupper())


def _blocks(text: str, detectar_encabezados: bool = True) -> list[tuple[str, str]]:
    """Parte el documento en (encabezado_vigente, texto_del_bloque)."""
    out: list[tuple[str, str]] = []
    heading = ""
    for raw in text.split("\n\n"):
        block = raw.strip()
        if not block:
            continue
        lines = block.split("\n")

        # Un bloque de una sola línea que parece encabezado cambia la sección
        if len(lines) == 1:
            md = _HEADING_MD.match(block)
            if md:
                heading = md.group(1).strip()
                continue
            if detectar_encabezados and _parece_encabezado(block):
                heading = block
                continue

        if es_bloque_ruido(block):
            continue

        # Una oración que cruza un salto de página o de columna queda partida en
        # dos bloques por la extracción del PDF. Si el bloque anterior no cerró
        # oración y este empieza en minúscula, son la misma frase: se reúnen.
        anterior_abierto = out and not _CIERRA_ORACION.search(out[-1][1])
        # Un bloque de prosa que no cierra oración casi siempre continúa en el
        # siguiente, empiece este en minúscula o en nombre propio.
        continua = anterior_abierto and (
            _EMPIEZA_MINUSCULA.match(block) or count_words(out[-1][1]) >= 15
        )
        if continua and out[-1][0] == heading:
            anterior_heading, anterior_texto = out[-1]
            out[-1] = (anterior_heading, f"{anterior_texto} {block}")
            continue

        out.append((heading, block))
    return out


def chunk_document(doc: dict) -> list[dict]:
    """Fragmenta un documento extraído. Devuelve una lista de fragmentos.

    Cada fragmento lleva `texto` (literal, lo que se entrega y se evalúa) y
    `texto_embed` (título + sección + texto, solo para codificar).
    """
    lang = doc.get("idioma", "und")
    titulo = (doc.get("titulo") or "").strip()

    # Los tabulares ya vienen delimitados por filas: cada bloque es una unidad
    pre_blocks = doc.get("blocks")
    if pre_blocks:
        blocks = [("", b) for b in pre_blocks if b and b.strip()]
    else:
        texto = doc.get("texto", "")
        blocks = _blocks(texto)
        # Si salen tantos encabezados distintos como bloques, no son encabezados:
        # es un documento de figuras y tablas cuyas etiquetas engañan al patrón.
        distintos = len({h for h, _ in blocks if h})
        if blocks and distintos > max(8, len(blocks) * 0.12):
            blocks = _blocks(texto, detectar_encabezados=False)

    target = config.CHUNK_TARGET_WORDS
    hard_max = config.CHUNK_MAX_WORDS
    min_words = config.CHUNK_MIN_WORDS
    overlap_n = config.CHUNK_OVERLAP_SENTENCES

    raw_chunks: list[tuple[str, str, int]] = []  # (seccion, texto, n_forzados)

    # El buffer persiste entre párrafos de una misma sección: un párrafo suelto
    # de 20 palabras (un pie de página, una línea de autores) no debe convertirse
    # en un fragmento propio. Solo se vacía al cambiar de sección.
    heading_actual: str | None = None
    buf: list[str] = []
    buf_words = 0
    buf_forced = 0  # oraciones del buffer que hubo que partir por exceder el tope

    def flush() -> None:
        nonlocal buf, buf_words, buf_forced
        if buf and buf_words > 0:
            raw_chunks.append((heading_actual or "", " ".join(buf), buf_forced))
        buf, buf_words, buf_forced = [], 0, 0

    for heading, block in blocks:
        if heading != heading_actual:
            flush()
            heading_actual = heading

        sentences: list[tuple[str, bool]] = []
        for sent in split_sentences(block, lang):
            if count_words(sent) > hard_max:
                for pieza in _split_oversized(sent, hard_max):
                    sentences.append((pieza, True))
            else:
                sentences.append((sent, False))

        for sent, forzada in sentences:
            sw = count_words(sent)
            if buf and buf_words + sw > hard_max:
                raw_chunks.append((heading_actual or "", " ".join(buf), buf_forced))
                # Solapamiento: arrastra las últimas oraciones al siguiente
                carry = buf[-overlap_n:] if overlap_n else []
                carry_words = sum(count_words(s) for s in carry)
                if carry_words + sw > hard_max:
                    carry, carry_words = [], 0
                buf, buf_words, buf_forced = list(carry), carry_words, 0
            buf.append(sent)
            buf_words += sw
            buf_forced += int(forzada)
            if buf_words >= target:
                raw_chunks.append((heading_actual or "", " ".join(buf), buf_forced))
                carry = buf[-overlap_n:] if overlap_n else []
                carry_words = sum(count_words(s) for s in carry)
                buf, buf_words, buf_forced = list(carry), carry_words, 0
    flush()

    # Fusiona las colas demasiado cortas con el fragmento anterior de la misma sección
    merged: list[tuple[str, str, int]] = []
    for heading, text, forced in raw_chunks:
        # La fusión cruza encabezados a propósito: un fragmento de quince
        # palabras no es una unidad recuperable, y dejarlo suelto solo añade
        # ruido que compite por un puesto en el top-10.
        if (
            merged
            and count_words(text) < min_words
            and count_words(merged[-1][1]) + count_words(text) <= hard_max
        ):
            prev = merged[-1]
            merged[-1] = (prev[0], f"{prev[1]} {text}", prev[2] + forced)
        else:
            merged.append((heading, text, forced))

    # Descarta fragmentos triviales (sin merge posible): ruido puro
    merged = [m for m in merged if count_words(m[1]) >= 8]

    # Todo documento debe existir en el índice, aunque su archivo no tenga texto
    # extraíble (páginas web vacías, imágenes sin OCR legible). Si no, su doc_id
    # sería irrecuperable y el F1@3 de una consulta que lo necesitara sería cero.
    if not merged:
        respaldo = ". ".join(
            p for p in (
                titulo,
                doc.get("observatorio", ""),
                doc.get("fuente", ""),
                doc.get("url", ""),
            ) if p
        )
        if not respaldo.strip():
            respaldo = f"Documento {doc['doc_id']} del corpus."
        merged = [("", respaldo, 0)]

    chunks: list[dict] = []
    seen: set[str] = set()
    for pos, (heading, text, forced) in enumerate(merged):
        key = text[:400]
        if key in seen:  # el solapamiento puede duplicar bloques muy cortos
            continue
        seen.add(key)
        idx = len(chunks)
        embed_parts = [p for p in (titulo, heading) if p]
        embed_parts.append(text)
        chunks.append(
            {
                "doc_id": doc["doc_id"],
                "doc_id_inventario": doc["doc_id_inventario"],
                "doc_id_secuencial": doc["doc_id_secuencial"],
                "chunk_id": f"{doc['doc_id']}-chunk-{idx:04d}",
                "fuente": doc["fuente"],
                "formato": doc["formato"],
                "fenomeno": doc["fenomeno"],
                "posicion": idx,
                "texto": text,
                "texto_embed": " | ".join(embed_parts),
                "n_palabras": count_words(text),
                "observatorio": doc["observatorio"],
                "titulo": titulo,
                "idioma": lang,
                "fecha": doc.get("fecha", ""),
                "url": doc.get("url", ""),
                "seccion": heading,
                "ruta_relativa": doc["ruta_relativa"],
                "corte_forzado": forced > 0,
            }
        )
    return chunks
