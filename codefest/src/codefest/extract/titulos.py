"""Saneamiento de títulos de documento.

El título de cada documento se antepone al texto de todos sus fragmentos a la
hora de codificarlos, así que un título malo contamina el vector de cada
fragmento del documento. Y los títulos que trae la metadata de los PDFs son
malos con frecuencia: nombres de archivo de InDesign o Word, direcciones
postales de la imprenta, códigos internos, o el encabezado de una carta.

Este módulo detecta esos casos y busca un título mejor en el propio texto.
"""

from __future__ import annotations

import re

# Restos de la cadena de producción del documento
_PREFIJOS_BASURA = re.compile(
    r"^(microsoft word\s*[-–]\s*|adobe indesign\s*[-–]\s*|untitled\s*[-–]?\s*|"
    r"print\s*[-–]\s*|final\s*[-–]\s*|copy of\s+)",
    re.IGNORECASE,
)
_EXT_ARCHIVO = re.compile(r"\.(indd|docx?|pdf|pptx?|qxd|ai|eps|pages|pub|xlsx?)\s*$", re.IGNORECASE)
_SOLO_CODIGO = re.compile(r"^[A-Z]{2,}[-_ ]?[\dA-Z\-_.]{2,}$")
_DIRECCION = re.compile(r"\b(strasse|straße|street|avenue|calle|carrera|apartado|p\.?o\.? box)\b", re.IGNORECASE)
_ENCABEZADO_CARTA = re.compile(r"^(bogot[áa]|lima|quito|caracas|madrid|washington)\s*[,.]?\s*d?\.?\s*c?\.?\s*[,.]?\s*\d*$", re.IGNORECASE)
_ETIQUETA_MAQUETA = re.compile(r"^(cover photo|foto de portada|photo credit|cr[ée]ditos?|portada|contents?|índice|table of contents)\s*[:.]?\s*$", re.IGNORECASE)
# Créditos de imagen y firmas que se cuelan como primera línea de una portada
_CREDITO = re.compile(r"^(photo|foto|image|imagen|illustration|ilustraci[óo]n|cover)\s+(by|de|por|credit)\b", re.IGNORECASE)
_MUCHOS_GUIONES = re.compile(r"^[^\s]{12,}$")  # una sola palabra larga = nombre de archivo

# Líneas del cuerpo que sí pueden ser un título
_CANDIDATO = re.compile(r"^[\"'«¿¡(\[]?[A-ZÁÉÍÓÚÑÜ0-9][^\n]{14,150}$")
_TERMINA_EN_PUNTO = re.compile(r"[.;:]\s*$")


def _humanizar(nombre_archivo: str) -> str:
    """Último recurso: el nombre del archivo convertido en algo legible."""
    base = re.sub(r"\.[a-z0-9]{1,5}$", "", nombre_archivo, flags=re.IGNORECASE)
    base = re.sub(r"^[A-Z]{2,12}_", "", base)  # prefijo del observatorio
    base = re.sub(r"[-_]+", " ", base).strip()
    base = re.sub(r"\s+", " ", base)
    return base[:180]


def parece_nombre_de_archivo(titulo: str) -> bool:
    """El título es en realidad el nombre del archivo de maquetación.

    Se trata aparte porque estos nombres suelen ser informativos —
    `AD_2016_ING_Cap_22_Nicaragua.indd` dice de qué país trata el capítulo— y
    conviene humanizarlos en vez de descartarlos.
    """
    t = (titulo or "").strip()
    return bool(_EXT_ARCHIVO.search(t) or _PREFIJOS_BASURA.match(t) or _MUCHOS_GUIONES.match(t))


def es_titulo_malo(titulo: str) -> bool:
    t = (titulo or "").strip()
    if len(t) < 8:
        return True
    if _CREDITO.match(t):
        return True
    if parece_nombre_de_archivo(t):
        return True
    if _SOLO_CODIGO.match(t) or _DIRECCION.search(t):
        return True
    if _ENCABEZADO_CARTA.match(t) or _ETIQUETA_MAQUETA.match(t):
        return True
    if sum(c.isdigit() for c in t) > len(t) * 0.4:
        return True
    # Se aceptan títulos en cualquier escritura: el corpus tiene documentos de
    # UNOOSA en chino y árabe, y su título original es perfectamente válido.
    if not re.search(r"[^\W\d_]{3,}", t, re.UNICODE):
        return True
    return False


def limpiar_titulo(titulo: str) -> str:
    t = (titulo or "").strip()
    t = _PREFIJOS_BASURA.sub("", t)
    t = _EXT_ARCHIVO.sub("", t)
    t = t.strip(" •·-–—_\t")
    # Los títulos largos se recortan, no se descartan: el de una alerta temprana
    # lleva la lista de municipios, que es justo lo que buscan las consultas de F3.
    return re.sub(r"\s+", " ", t).strip()[:240]


def titulo_desde_texto(texto: str, max_lineas: int = 40) -> str:
    """Busca la primera línea del cuerpo que parezca un título de verdad."""
    for linea in texto.split("\n")[:max_lineas]:
        linea = linea.strip()
        if not _CANDIDATO.match(linea) or _TERMINA_EN_PUNTO.search(linea):
            continue
        if es_titulo_malo(linea) or _CREDITO.match(linea):
            continue
        # Un título no suele ser una oración completa con verbo conjugado y punto
        if linea.count(" ") < 2:
            continue
        return linea[:200]
    return ""


def resolver_titulo(titulo_metadata: str, texto: str, fuente: str, formato: str = "") -> tuple[str, str]:
    """Devuelve (titulo, origen) con origen en {metadata, maqueta, texto, archivo}.

    Orden de preferencia:
      1. el título de la metadata, si es utilizable;
      2. si ese título es un nombre de archivo de maquetación, su versión
         humanizada — suele llevar el país o el capítulo, que es información real;
      3. la primera línea del cuerpo que parezca un título;
      4. el nombre del archivo en disco, humanizado.
    """
    limpio = limpiar_titulo(titulo_metadata)

    # Los tabulares no tienen título en el cuerpo: la primera fila son columnas
    if formato in ("csv", "xlsx"):
        return _humanizar(titulo_metadata or fuente), "archivo"

    if limpio and not es_titulo_malo(limpio):
        return limpio, "metadata"

    if titulo_metadata and parece_nombre_de_archivo(titulo_metadata):
        humanizado = _humanizar(limpiar_titulo(titulo_metadata) or titulo_metadata)
        if len(humanizado) >= 8 and re.search(r"[^\W\d_]{3,}", humanizado, re.UNICODE):
            return humanizado, "maqueta"

    del_texto = titulo_desde_texto(texto)
    if del_texto:
        return del_texto, "texto"

    return _humanizar(fuente), "archivo"
