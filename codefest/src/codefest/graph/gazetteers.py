"""Diccionarios de entidades del dominio, construidos desde el propio corpus.

El NER genérico reconoce personas, organizaciones y lugares, pero se pierde
precisamente las entidades que importan para estas consultas: los nombres de
los grupos armados, los municipios colombianos, y el vocabulario técnico
espacial y de defensa. Estos gazetteers los recuperan.

Los territoriales no están escritos a mano: salen de los datos estructurados que
el corpus ya trae (los campos `municipios` de las 363 alertas tempranas y las
columnas administrativas del CSV de Amazon Underworld).
"""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from functools import lru_cache

from .. import config

# --------------------------------------------------------------------------- #
# Listas curadas del dominio
# --------------------------------------------------------------------------- #

GRUPOS_ARMADOS = {
    "ELN": ["ELN", "Ejército de Liberación Nacional", "Eln"],
    "Clan del Golfo": ["Clan del Golfo", "AGC", "Autodefensas Gaitanistas", "Gulf Clan", "Urabeños"],
    "EMC": ["EMC", "Estado Mayor Central", "Estado Mayor Central de las FARC"],
    "Segunda Marquetalia": ["Segunda Marquetalia"],
    "EMBF": ["EMBF", "Estado Mayor de los Bloques y Frentes"],
    "FARC-EP": ["FARC", "FARC-EP", "Fuerzas Armadas Revolucionarias de Colombia"],
    "Disidencias FARC": ["disidencias de las FARC", "facciones disidentes", "GAOR", "grupos armados organizados residuales"],
    "GAO": ["GAO", "Grupos Armados Organizados", "Grupo Armado Organizado"],
    "GDO": ["GDO", "Grupos Delictivos Organizados", "Grupo Delictivo Organizado"],
    "Los Choneros": ["Los Choneros"],
    "Los Lobos": ["Los Lobos"],
    "Comando Vermelho": ["Comando Vermelho", "Comando Vermelo"],
    "PCC": ["PCC", "Primeiro Comando da Capital"],
    "Tren de Aragua": ["Tren de Aragua"],
    "Los Rastrojos": ["Los Rastrojos"],
    "Los Caparros": ["Los Caparros", "Caparrapos"],
    "Sinaloa": ["Cártel de Sinaloa", "Cartel de Sinaloa"],
    "Shining Path": ["Sendero Luminoso", "Shining Path"],
}

ECONOMIAS_ILICITAS = {
    "narcotráfico": ["narcotráfico", "narcotrafico", "drug trafficking", "tráfico de drogas", "cocaína", "coca"],
    "minería ilegal": ["minería ilegal", "mineria ilegal", "illegal mining", "garimpo", "extracción ilícita de minerales", "minería ilícita"],
    "minería de oro": ["minería de oro", "oro ilegal", "gold mining", "explotación aurífera"],
    "tala ilegal": ["tala ilegal", "deforestación", "illegal logging", "desmatamento"],
    "tráfico de armas": ["tráfico de armas", "arms trafficking", "contrabando de armas"],
    "trata de personas": ["trata de personas", "human trafficking", "tráfico de migrantes"],
    "extorsión": ["extorsión", "extorsion", "vacunas", "exaction"],
    "contrabando": ["contrabando", "smuggling"],
    "tráfico de fauna": ["tráfico de fauna", "wildlife trafficking", "tráfico de vida silvestre"],
}

TECNOLOGIAS_IA = {
    "inteligencia artificial": ["inteligencia artificial", "artificial intelligence", "inteligência artificial"],
    "aprendizaje automático": ["machine learning", "aprendizaje automático", "aprendizado de máquina"],
    "aprendizaje profundo": ["deep learning", "aprendizaje profundo", "redes neuronales"],
    "sistemas autónomos": ["sistemas autónomos", "autonomous systems", "sistemas de armas autónomos", "LAWS", "armas autónomas letales"],
    "drones": ["drone", "drones", "UAV", "UAS", "vehículo aéreo no tripulado", "sistemas no tripulados", "unmanned aerial"],
    "enjambres de drones": ["enjambre de drones", "drone swarm", "swarming"],
    "contradrón": ["contradrón", "counter-UAS", "C-UAS", "antidrón"],
    "guerra electrónica": ["guerra electrónica", "electronic warfare", "jamming", "interferencia"],
    "ciberseguridad": ["ciberseguridad", "cybersecurity", "ciberataque", "cyberattack", "cibernética"],
    "semiconductores": ["semiconductores", "semiconductors", "chips", "GPU", "microchips"],
    "targeting": ["targeting", "designación de objetivos"],
    "ISR": ["ISR", "inteligencia, vigilancia y reconocimiento", "intelligence, surveillance and reconnaissance"],
    "NBQR": ["NBQR", "CBRN", "nuclear, biológico, químico y radiológico", "armas químicas", "armas biológicas"],
}

ESPACIO = {
    "órbita baja terrestre": ["órbita baja", "low earth orbit", "LEO", "orbita baja terrestre"],
    "órbita geoestacionaria": ["órbita geoestacionaria", "geostationary", "GEO", "geosynchronous"],
    "basura espacial": ["basura espacial", "space debris", "desechos orbitales", "detritos espaciais", "escombros orbitales"],
    "ASAT": ["ASAT", "antisatélite", "anti-satellite", "arma antisatélite"],
    "RPO": ["RPO", "rendezvous and proximity operations", "maniobras de proximidad", "operaciones de proximidad"],
    "armas de energía dirigida": ["energía dirigida", "directed energy", "láser", "laser weapon", "high-power laser"],
    "spoofing": ["spoofing", "suplantación de señal", "GPS spoofing"],
    "servicio en órbita": ["on-orbit servicing", "servicio en órbita", "reabastecimiento en órbita", "OOS"],
    "constelaciones satelitales": ["constelación", "constellation", "Starlink", "megaconstelación"],
    "sostenibilidad espacial": ["sostenibilidad espacial", "space sustainability", "STM", "gestión del tráfico espacial"],
    "GNSS": ["GNSS", "GPS", "Galileo", "GLONASS", "BeiDou"],
}

ORGANIZACIONES = {
    "UNOOSA": ["UNOOSA", "Oficina de Asuntos del Espacio Ultraterrestre"],
    "ESA": ["ESA", "European Space Agency", "Agencia Espacial Europea"],
    "NASA": ["NASA"],
    "SIPRI": ["SIPRI", "Stockholm International Peace Research Institute"],
    "MAPP/OEA": ["MAPP/OEA", "MAPP-OEA", "Misión de Apoyo al Proceso de Paz", "OEA", "Organización de los Estados Americanos"],
    "Defensoría del Pueblo": ["Defensoría del Pueblo", "SAT", "Sistema de Alertas Tempranas"],
    "OTAN": ["OTAN", "NATO"],
    "ONU": ["ONU", "Naciones Unidas", "United Nations", "UN"],
    "Fuerza Aeroespacial Colombiana": ["Fuerza Aeroespacial Colombiana", "FAC", "Fuerza Aérea Colombiana"],
    "INPE": ["INPE", "Instituto Nacional de Pesquisas Espaciais"],
    "Secure World Foundation": ["Secure World Foundation", "SWF"],
    "CSIS": ["CSIS", "Center for Strategic and International Studies"],
    "CSET": ["CSET", "Center for Security and Emerging Technology"],
}

MARCOS_JURIDICOS = {
    "Derecho Internacional Humanitario": ["Derecho Internacional Humanitario", "DIH", "international humanitarian law", "IHL"],
    "Tratado del Espacio Ultraterrestre": ["Tratado del Espacio Ultraterrestre", "Outer Space Treaty", "OST"],
    "Convenio de Ginebra": ["Convenio de Ginebra", "Convenios de Ginebra", "Geneva Convention"],
    "Acuerdo de Paz": ["Acuerdo de Paz", "Acuerdo Final", "peace agreement"],
    "restitución de tierras": ["restitución de tierras", "land restitution", "Ley 1448"],
}

TIPOS = {
    "GRUPO_ARMADO": GRUPOS_ARMADOS,
    "ECONOMIA_ILICITA": ECONOMIAS_ILICITAS,
    "TECNOLOGIA": {**TECNOLOGIAS_IA, **ESPACIO},
    "ORGANIZACION": ORGANIZACIONES,
    "MARCO_JURIDICO": MARCOS_JURIDICOS,
}


# --------------------------------------------------------------------------- #
# Gazetteers territoriales derivados de los datos del corpus
# --------------------------------------------------------------------------- #

_PAREN = re.compile(r"\s*\(([^)]+)\)\s*$")


def _municipios_desde_alertas() -> dict[str, str]:
    """Lee `alerta_meta.municipios` de los 363 JSON de Alertas Tempranas.

    El formato es "Calamar, El Retorno, Miraflores, San José del Guaviare (Guaviare)":
    varios municipios y, entre paréntesis, su departamento.
    """
    out: dict[str, str] = {}
    base = config.CORPUS_DIR / "F3_Dinamicas_Territoriales" / "Alertas_Tempranas"
    if not base.exists():
        return out
    for path in base.rglob("*.json"):
        try:
            obj = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        campo = ((obj or {}).get("alerta_meta") or {}).get("municipios") or ""
        for bloque in campo.split(";"):
            bloque = bloque.strip()
            if not bloque:
                continue
            m = _PAREN.search(bloque)
            depto = m.group(1).strip() if m else ""
            if depto:
                out[depto] = "DEPARTAMENTO"
                bloque = _PAREN.sub("", bloque)
            for muni in bloque.split(","):
                muni = muni.strip()
                if len(muni) >= 4:
                    out.setdefault(muni, "MUNICIPIO")
    return out


def _territorios_desde_amazon() -> dict[str, str]:
    """Divisiones administrativas de la cuenca amazónica desde el CSV de Amazon Underworld."""
    out: dict[str, str] = {}
    path = (
        config.CORPUS_DIR
        / "F3_Dinamicas_Territoriales"
        / "Amazon_Underworld"
        / "AMAZONUW_amazonunderworld-data.csv"
    )
    if not path.exists():
        return out
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            for col, tipo in (
                ("b_ADM1_ES", "DEPARTAMENTO"), ("b_ADM1_PT", "DEPARTAMENTO"),
                ("au_level1", "DEPARTAMENTO"),
                ("b_ADM2_ES", "MUNICIPIO"), ("b_ADM2_PT", "MUNICIPIO"),
                ("au_level2", "MUNICIPIO"),
            ):
                val = (row.get(col) or "").strip()
                if len(val) >= 4:
                    out.setdefault(val, tipo)
            pais = (row.get("au_country") or "").strip()
            if pais:
                out[pais] = "PAIS"
    return out


def normalize(text: str) -> str:
    """Clave de comparación: sin tildes, sin puntuación, en minúsculas."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


GAZETTEER_FILE = "gazetteer.json"


def _construir_desde_corpus() -> dict[str, tuple[str, str]]:
    gaz: dict[str, tuple[str, str]] = {}

    for tipo, grupos in TIPOS.items():
        for canonico, alias in grupos.items():
            for a in alias:
                key = normalize(a)
                if len(key) >= 3:
                    gaz.setdefault(key, (canonico, tipo))

    for nombre, tipo in {**_territorios_desde_amazon(), **_municipios_desde_alertas()}.items():
        key = normalize(nombre)
        # Evita pisar entidades del dominio con topónimos homónimos
        if len(key) >= 4 and key not in gaz:
            gaz[key] = (nombre, tipo)

    return gaz


def guardar_gazetteer(destino) -> int:
    """Serializa el gazetteer dentro de la entrega.

    Sin esto, `generador.py` en la máquina del jurado reconstruiría el
    gazetteer leyendo el corpus —que allí no existe— y se quedaría solo con
    las listas curadas, perdiendo unos 1.800 topónimos. El resultado dejaría de
    ser reproducible. Con el archivo, la ejecución del jurado es idéntica a la
    nuestra.
    """
    from pathlib import Path

    gaz = _construir_desde_corpus()
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as fh:
        json.dump({k: list(v) for k, v in gaz.items()}, fh, ensure_ascii=False)
    return len(gaz)


def cargar_gazetteer(origen) -> dict[str, tuple[str, str]] | None:
    from pathlib import Path

    origen = Path(origen)
    if not origen.exists():
        return None
    with open(origen, encoding="utf-8") as fh:
        return {k: tuple(v) for k, v in json.load(fh).items()}


_GAZETTEER_CACHE: dict[str, tuple[str, str]] | None = None


def usar_gazetteer(path) -> bool:
    """Fija el gazetteer a partir de un archivo serializado. Devuelve si lo cargó."""
    global _GAZETTEER_CACHE
    cargado = cargar_gazetteer(path)
    if cargado:
        _GAZETTEER_CACHE = cargado
        return True
    return False


def build_gazetteer() -> dict[str, tuple[str, str]]:
    """{alias_normalizado: (nombre_canónico, tipo)}

    Prefiere el gazetteer serializado en la entrega; si no está, lo reconstruye
    desde el corpus.
    """
    global _GAZETTEER_CACHE
    if _GAZETTEER_CACHE is None:
        _GAZETTEER_CACHE = (
            cargar_gazetteer(config.GRAFO_DIR / GAZETTEER_FILE) or _construir_desde_corpus()
        )
    return _GAZETTEER_CACHE
