"""Reconocimiento de entidades y extracción de relaciones (Sección 7.2).

Tres fuentes complementarias de entidades:

1. Gazetteers del dominio construidos desde el propio corpus. Aportan lo que
   cualquier NER genérico se pierde: nombres de grupos armados, economías
   ilícitas, vocabulario espacial y de IA militar, y municipios colombianos.
2. NER estadístico con spaCy `en_core_web_md` para los fragmentos en inglés,
   que son el 76,5% del corpus.
3. Extractor de nombres propios por reglas para español y portugués.

La asimetría entre 2 y 3 es una restricción de licencia, no una decisión
técnica. Los organizadores dictaminaron que no puede usarse ningún componente
con licencia restrictiva, y las licencias que declaran los propios modelos en su
`meta.json` son:

    en_core_web_md   MIT             -> se usa
    es_core_news_md  GNU GPL 3.0     -> descartado
    pt_core_news_md  CC BY-SA 4.0    -> descartado

Las alternativas multilingües revisadas tampoco sirven: `wikineural-multilingual-ner`
es CC BY-NC-SA 4.0 (justamente la licencia sobre la que se emitió el fallo) y la
familia `xlm-roberta-*-ner-hrl` es AFL-3.0. Por eso el español y el portugués se
cubren con reglas propias, que no arrastran licencia de terceros.

Las relaciones se tipan por el verbo que conecta sujeto y objeto en el árbol de
dependencias, disponible solo donde hay modelo estadístico; cuando no hay una
conexión sintáctica clara se registra co-ocurrencia dentro del mismo fragmento.
"""

from __future__ import annotations

import re
from functools import lru_cache

from .gazetteers import build_gazetteer, normalize

# Etiquetas de spaCy que nos interesan, mapeadas a nuestros tipos
SPACY_TIPOS = {
    "PER": "PERSONA",
    "PERSON": "PERSONA",
    "ORG": "ORGANIZACION",
    "LOC": "LUGAR",
    "GPE": "LUGAR",
    "NORP": "ORGANIZACION",
    "FAC": "LUGAR",
    "EVENT": "EVENTO",
    "LAW": "MARCO_JURIDICO",
    "MISC": "OTRO",
}

# Solo los idiomas con modelo de licencia permisiva. El español y el portugués
# se resuelven con `entidades_reglas`; ver la nota de licencias en la cabecera.
MODELOS = {"en": "en_core_web_md", "und": "en_core_web_md"}

# Verbos que no aportan una relación informativa
VERBOS_VACIOS = {
    "ser", "estar", "haber", "tener", "hacer", "ir", "poder", "deber", "parecer",
    "be", "have", "do", "make", "get", "say", "go", "can", "will",
    "ser", "estar", "ter", "haver", "fazer", "poder", "dever",
}

MAX_LONGITUD_ENTIDAD = 60
MIN_LONGITUD_ENTIDAD = 3
_TOKEN_RE = re.compile(r"\w+", re.UNICODE)


@lru_cache(maxsize=4)
def load_nlp(lang: str):
    """Modelo estadístico del idioma, o None si no hay uno con licencia usable.

    Devolver None no es un fallo: es la señal de que ese idioma se procesa con
    `entidades_reglas`. Quien llame debe contemplar los dos casos.
    """
    import spacy

    nombre = MODELOS.get(lang)
    if nombre is None:
        return None
    try:
        return spacy.load(nombre, exclude=["lemmatizer", "textcat"])
    except OSError:
        return None


def gazetteer_hits(text: str, max_ngram: int = 6) -> list[tuple[str, str]]:
    """Busca alias del gazetteer en el texto. Devuelve [(canónico, tipo), ...]."""
    gaz = build_gazetteer()
    palabras = normalize(text).split()
    hits: dict[str, str] = {}
    n = len(palabras)
    for i in range(n):
        for size in range(min(max_ngram, n - i), 0, -1):
            key = " ".join(palabras[i : i + size])
            if len(key) < 3:
                continue
            hit = gaz.get(key)
            if hit:
                hits[hit[0]] = hit[1]
                break  # el n-grama más largo gana; no se solapan
    return sorted(hits.items())


def _limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip(" .,;:()[]\"'“”«»")


# --------------------------------------------------------------------------- #
# Ruido del extractor tabular
#
# Los CSV del AI Index (PubMed, ClinicalTrials) se aplanan a "columna: valor" y
# las filas se separan con "|". El NER lee esas cadenas como nombres propios, y
# acaban en el grafo entidades que no lo son: cabeceras de columna, fragmentos
# de listas de autores, URLs y encabezados de capítulo. Eran 635 nodos, siete de
# ellos entre los cien más conectados, o sea bien visibles en cualquier vista.
#
# El filtro va dirigido a esas formas y no a los dos puntos en general, porque
# hay entidades legítimas que los llevan: `ISO 24113:2023` es la norma de
# mitigación de basura orbital, material central del Fenómeno 2.
# --------------------------------------------------------------------------- #

_CABECERAS_TABULARES = (
    "columnas", "journal/book", "publication year", "pmid", "funded bys",
    "gender", "first author", "create date", "completion date", "last update",
    "enrollment", "sponsor", "other ids", "study type", "study desig",
    "primary completion", "start date", "citation", "conditions",
    "interventions", "locations", "phases", "outcome", "brief summary",
    "authors", "abstract", "affiliation", "doi", "issn", "keywords",
)

_RUIDO_TABULAR = re.compile(
    "|".join((
        r"^https?://",                            # URLs
        r"^\S+\s+[A-Z]{1,3}\.?\s*\|",             # "Li J. |": listas de autores
        r"^\s*\|", r"\|\s*$",                     # separador de fila suelto
        r"^(?i:chapter|cap[íi]tulo)\s+\d+\s*[:|]",  # encabezados de capítulo
        r"\d+\(\d+\):\d+",                        # "Jan;15(1):25-51": paginación
        r"(?i:" + "|".join(re.escape(c) for c in _CABECERAS_TABULARES) + r")\s*:",
    )),
    re.UNICODE,
)


def es_ruido_tabular(nombre: str) -> bool:
    """¿Es un artefacto del aplanado de tablas y no una entidad real?"""
    return bool(_RUIDO_TABULAR.search(nombre))


def entidades_spacy(doc) -> list[tuple[str, str]]:
    out: dict[str, str] = {}
    for ent in doc.ents:
        tipo = SPACY_TIPOS.get(ent.label_)
        if not tipo:
            continue
        nombre = _limpiar(ent.text)
        if not (MIN_LONGITUD_ENTIDAD <= len(nombre) <= MAX_LONGITUD_ENTIDAD):
            continue
        if nombre.isdigit() or not _TOKEN_RE.search(nombre):
            continue
        if es_ruido_tabular(nombre):
            continue
        out.setdefault(nombre, tipo)
    return sorted(out.items())


# --------------------------------------------------------------------------- #
# Extractor de nombres propios por reglas (español y portugués)
#
# Sustituye al NER estadístico en los idiomas cuyos modelos quedaron descartados
# por licencia. No pretende igualarlo: reconoce secuencias de palabras
# capitalizadas, que en prosa periodística e institucional —que es lo que hay en
# F3— cubren la mayoría de organizaciones y lugares. Las personas se pierden
# salvo que vengan precedidas de un título.
# --------------------------------------------------------------------------- #

_MAYUSCULA = r"[A-ZÁÉÍÓÚÝÑÜÀÂÃÄÊËÎÏÔÕÖÙÛÇ]"
_CUERPO = r"[\wÀ-ÿ’'\-]*"
_TOKEN_PROPIO = _MAYUSCULA + _CUERPO
# Partículas que pueden ir en minúscula dentro de un nombre propio compuesto:
# "Ejército de Liberación Nacional", "Universidade de São Paulo".
_CONECTOR = r"(?:de|del|de\s+la|de\s+los|de\s+las|da|do|das|dos|la|las|los|el|y|e|di|du|van|von)"
_NOMBRE_PROPIO_RE = re.compile(
    rf"{_TOKEN_PROPIO}(?:\s+(?:{_CONECTOR}\s+)?{_TOKEN_PROPIO})*", re.UNICODE
)
# Las viñetas abren renglón igual que un punto: sin tratarlas como frontera, el
# verbo capitalizado que las sigue ("• Encourager los candidatos") entra como
# entidad. Se parte por ellas y luego se limpia lo que quede al principio.
_FIN_ORACION_RE = re.compile(r"(?<=[.!?;:])\s+|\n+|\s*[•·▪◦‣]\s*")
_APERTURA_RE = re.compile(r"^[^\wÀ-ÿ]+")

# Palabras que abren oración y quedarían capitalizadas sin ser nombres propios.
_NO_ENTIDAD = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "este", "esta", "estos",
    "estas", "ese", "esa", "esos", "esas", "aquel", "aquella", "su", "sus", "mi",
    "y", "o", "pero", "sin", "con", "por", "para", "segun", "según", "desde",
    "hasta", "entre", "sobre", "tras", "durante", "mientras", "aunque", "porque",
    "como", "cuando", "donde", "que", "quien", "cual", "cuales", "si", "no",
    "tambien", "también", "ademas", "además", "asi", "así", "entonces", "luego",
    "ahora", "hoy", "ayer", "manana", "mañana", "todo", "toda", "todos", "todas",
    "otro", "otra", "otros", "otras", "mismo", "misma", "cada", "algun", "algún",
    "alguna", "ninguno", "ninguna", "mas", "más", "menos", "muy", "tanto", "tan",
    "os", "as", "um", "uma", "este", "esse", "aquele", "seu", "sua", "mas",
    "porem", "porém", "quando", "onde", "quem", "qual", "tambem", "também",
    "ainda", "entao", "então", "depois", "antes", "hoje", "ontem", "amanha",
    "amanhã", "tudo", "todo", "cada", "outro", "outra", "mesmo", "muito",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
    "septiembre", "setiembre", "octubre", "noviembre", "diciembre",
    "janeiro", "fevereiro", "março", "marco", "maio", "junho", "julho",
    "setembro", "outubro", "novembro", "dezembro",
    "lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sabado",
    "sábado", "domingo", "segunda", "terca", "terça", "quarta", "quinta", "sexta",
    "fuente", "fonte", "tabla", "tabela", "grafico", "gráfico", "figura", "cuadro",
    "nota", "notas", "anexo", "informe", "capitulo", "capítulo", "seccion",
    "sección", "pagina", "página", "resumen", "resumo", "introduccion",
    "introducción", "conclusion", "conclusión", "conclusiones", "bibliografia",
    "bibliografía", "referencias", "indice", "índice",
    # Abreviaturas de citación: el punto que las cierra hace de fin de oración,
    # así que llegan aquí sueltas ("Art." de "Art. 118, inc. 15").
    "art", "arts", "inc", "num", "núm", "no", "nro", "pag", "pág", "pp", "fig",
    "cap", "vol", "ed", "eds", "op", "cit", "et", "al", "ibid", "ss", "ref",
    "doc", "docs", "par", "párr", "parr", "tit", "lit", "ver", "vid",
    # El detector marca como `pt` los documentos en francés de UNOOSA y SWF.
    # Sus funcionales entran por la misma puerta y hay que cerrarla igual.
    "le", "les", "une", "des", "du", "ce", "cette", "ces", "leur", "leurs",
    "toutes", "tous", "tout", "toute", "aussi", "ainsi", "donc", "alors",
    "cependant", "pourtant", "lorsque", "puisque", "afin", "selon", "depuis",
    "pendant", "chaque", "autre", "autres", "meme", "même", "plus", "moins",
    "tres", "très", "bien", "encore", "deja", "déjà", "aujourd", "hier",
    "demain", "mettre", "fournir", "inclure", "traiter", "utiliser", "assurer",
    "encourager", "accroitre", "accroître", "elaboration", "élaboration",
}

_ORG_CLAVES = (
    "ministerio", "ministério", "ejercito", "ejército", "exercito", "exército",
    "fuerza", "forca", "força", "comando", "agencia", "agência", "instituto",
    "universidad", "universidade", "grupo", "frente", "bloque", "bloco",
    "comision", "comisión", "comissao", "comissão", "consejo", "conselho",
    "federacion", "federación", "federacao", "federação", "organizacion",
    "organización", "organizacao", "organização", "secretaria", "secretaría",
    "corporacion", "corporación", "corporacao", "corporação", "fundacion",
    "fundación", "fundacao", "fundação", "observatorio", "observatório",
    "tribunal", "corte", "fiscalia", "fiscalía", "policia", "policía", "polícia",
    "armada", "batallon", "batallón", "batalhao", "batalhão", "brigada",
    "division", "división", "divisao", "divisão", "empresa", "banco", "gobierno",
    "governo", "congreso", "congresso", "senado", "camara", "cámara", "câmara",
    "alcaldia", "alcaldía", "gobernacion", "gobernación", "defensoria",
    "defensoría", "procuraduria", "procuraduría", "contraloria", "contraloría",
    "registraduria", "registraduría", "departamento administrativo", "cartel",
    "cártel", "partido", "movimiento", "movimento", "sindicato", "asociacion",
    "asociación", "associacao", "associação", "camara de comercio", "red",
)

_TITULOS_PERSONA = (
    "presidente", "presidenta", "ministro", "ministra", "general", "coronel",
    "capitan", "capitán", "teniente", "almirante", "alcalde", "alcaldesa",
    "gobernador", "gobernadora", "senador", "senadora", "representante",
    "doctor", "doctora", "senor", "señor", "senora", "señora", "embajador",
    "embajadora", "director", "directora", "comandante", "secretario",
    "secretaria", "fiscal", "juez", "jueza", "papa", "rey", "reina", "diputado",
    "diputada", "concejal", "vicepresidente", "canciller", "procurador",
    "defensor", "obispo", "monsenor", "monseñor", "profesor", "profesora",
    "investigador", "investigadora", "analista", "periodista",
)

_TRIGGERS_LUGAR = (
    "departamento de", "municipio de", "município de", "corregimiento de",
    "vereda de", "ciudad de", "cidade de", "region de", "región de", "regiao de",
    "região de", "provincia de", "província de", "estado de", "estado do",
    "parque nacional", "resguardo de", "cuenca del", "cuenca de", "rio", "río",
    "golfo de", "bahia de", "bahía de", "sierra de", "valle del", "valle de",
    "frontera con", "subregion de", "subregión de", "localidad de",
)


def _tipo_por_contexto(nombre: str, antes: str) -> str:
    """Clasifica una entidad por pistas léxicas, sin modelo estadístico."""
    minusculas = nombre.lower()
    if any(clave in minusculas for clave in _ORG_CLAVES):
        return "ORGANIZACION"
    cola = antes[-40:].lower()
    if any(cola.rstrip().endswith(t) for t in _TITULOS_PERSONA):
        return "PERSONA"
    if any(cola.rstrip().endswith(t) for t in _TRIGGERS_LUGAR):
        return "LUGAR"
    return "OTRO"


_ARTICULOS_INICIALES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "le", "les", "un", "une", "des", "du",
}
_ROMANO_RE = re.compile(r"^[IVXLCDM]+$")


def _podar_articulo(nombre: str) -> str:
    """Quita el artículo inicial de un nombre compuesto.

    En posición de apertura de oración el artículo va capitalizado y el patrón
    se lo traga: "El Ejército", "La Résolution", "Le Cadre". Sin esto, la misma
    entidad genera dos nodos distintos según dónde aparezca en la frase.
    """
    palabras = nombre.split()
    if len(palabras) >= 2 and palabras[0].lower() in _ARTICULOS_INICIALES:
        return " ".join(palabras[1:])
    return nombre


def _candidato_valido(nombre: str) -> bool:
    if not (MIN_LONGITUD_ENTIDAD <= len(nombre) <= MAX_LONGITUD_ENTIDAD):
        return False
    if nombre.isdigit() or not _TOKEN_RE.search(nombre):
        return False
    if _ROMANO_RE.match(nombre):  # "XXI", "VIII": numeración, no entidad
        return False
    if es_ruido_tabular(nombre):
        return False
    palabras = [p for p in re.split(r"\s+", nombre) if p]
    # Todas las palabras significativas en la lista de descarte -> no es entidad
    if all(p.lower().strip(".,;:") in _NO_ENTIDAD for p in palabras):
        return False
    # Una sola palabra que además es un conector o artículo capitalizado
    if len(palabras) == 1 and palabras[0].lower() in _NO_ENTIDAD:
        return False
    return True


def entidades_reglas(texto: str) -> list[tuple[str, str]]:
    """Nombres propios de un fragmento en español o portugués, por reglas.

    Se recorre oración por oración porque la primera palabra de cada una está
    capitalizada por ortografía y no por ser nombre propio: un candidato de una
    sola palabra en esa posición se descarta. Los de varias palabras se
    conservan, porque "Estado Mayor Central anunció..." sí abre oración.
    """
    out: dict[str, str] = {}
    for oracion in _FIN_ORACION_RE.split(texto):
        oracion = _APERTURA_RE.sub("", (oracion or "").strip())
        if len(oracion) < 4:
            continue
        # Titulares y celdas de tabla vienen en versalitas y producen basura:
        # "ORBITAL DEBRIS CREATED BY ASAT TESTS" no son cuatro entidades.
        letras = [c for c in oracion if c.isalpha()]
        if letras and sum(c.isupper() for c in letras) / len(letras) > 0.6:
            continue

        for m in _NOMBRE_PROPIO_RE.finditer(oracion):
            nombre = _podar_articulo(_limpiar(m.group(0)))
            if not _candidato_valido(nombre):
                continue
            if m.start() == 0 and len(nombre.split()) == 1:
                continue
            out.setdefault(nombre, _tipo_por_contexto(nombre, oracion[: m.start()]))
    return sorted(out.items())


DEPS_SUJETO = {"nsubj", "nsubj:pass", "nsubjpass", "csubj", "expl:subj"}
DEPS_OBJETO = {"obj", "dobj", "obl", "iobj", "pobj", "obl:arg", "obl:agent", "nmod", "attr", "xcomp", "ccomp"}


def _entidades_en_span(span_text: str, normalizadas: dict[str, str]) -> list[str]:
    """Entidades conocidas que aparecen dentro de un fragmento de texto.

    Se busca por contención y no por igualdad exacta: el subárbol de un sujeto
    suele traer determinantes y modificadores ("las disidencias de las FARC en
    el Catatumbo"), y exigir coincidencia exacta descartaría casi todo.
    """
    objetivo = f" {normalize(span_text)} "
    return [nombre for clave, nombre in normalizadas.items() if f" {clave} " in objetivo]


def relaciones_sintacticas(doc, entidades_validas: set[str]) -> list[tuple[str, str, str]]:
    """Tripletas (sujeto, verbo, objeto) donde ambos extremos son entidades.

    Se recorre cada verbo del árbol de dependencias, se toman los subárboles de
    sus hijos con función de sujeto y de objeto, y se buscan entidades dentro.
    """
    if not entidades_validas:
        return []
    normalizadas = {normalize(e): e for e in entidades_validas if len(normalize(e)) >= 3}
    triples: list[tuple[str, str, str]] = []

    for token in doc:
        if token.pos_ not in ("VERB", "AUX"):
            continue
        verbo = (token.lemma_ or token.text).lower()
        if verbo in VERBOS_VACIOS or len(verbo) < 3 or not verbo.isalpha():
            continue

        sujetos: list[str] = []
        objetos: list[str] = []
        for hijo in token.children:
            if hijo.dep_ in DEPS_SUJETO:
                destino = sujetos
            elif hijo.dep_ in DEPS_OBJETO:
                destino = objetos
            else:
                continue
            span = doc[hijo.left_edge.i : hijo.right_edge.i + 1]
            destino.extend(_entidades_en_span(span.text, normalizadas))

        for s in dict.fromkeys(sujetos):
            for o in dict.fromkeys(objetos):
                if s != o:
                    triples.append((s, verbo, o))
    return triples
