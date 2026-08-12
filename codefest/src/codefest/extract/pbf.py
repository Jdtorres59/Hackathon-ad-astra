"""Extracción de los 73 tiles vectoriales PBF de Amazon Underworld.

La Sección 2.1 describe decodificar el PBF, recorrer capas y elementos, y leer
sus atributos como pares `atributo: valor`, quedándose con una sola versión de
cada elemento porque se repiten entre niveles de zoom.

No hace falta un decodificador de Mapbox Vector Tiles: el propio corpus incluye
`AMAZONUW_amazonunderworld-data.csv`, que es exactamente esa decodificación ya
hecha, indexada por (tile_zoom, tile_x, tile_y). Esas claves corresponden 1:1
con las rutas `tiles/{z}/{x}/AMAZONUW_{y}.pbf` (verificado: 68 de los 73 tiles).
Los 5 tiles sin filas en el CSV son tiles vacíos.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from .. import config
from .clean import clean_text

_TILE_PATH = re.compile(r"tiles/(\d+)/(\d+)/AMAZONUW_(\d+)\.pbf$")

_CSV_PATH = (
    config.CORPUS_DIR
    / "F3_Dinamicas_Territoriales"
    / "Amazon_Underworld"
    / "AMAZONUW_amazonunderworld-data.csv"
)

# Columnas de presencia por grupo -> nombre legible del grupo armado
_GRUPOS = {
    "grupo_EMC": "Estado Mayor Central (EMC, disidencias FARC)",
    "grupo_EMBF": "Estado Mayor de los Bloques y Frentes (EMBF)",
    "grupo_ELN": "Ejército de Liberación Nacional (ELN)",
    "grupo_CDF_AGC": "Clan del Golfo / Autodefensas Gaitanistas de Colombia (AGC)",
    "grupo_Seg_Marquetalia": "Segunda Marquetalia",
    "grupo_Los_Lobos": "Los Lobos",
    "grupo_Los_Choneros": "Los Choneros",
    "grupo_CV": "Comando Vermelho",
    "grupo_PCC": "Primeiro Comando da Capital (PCC)",
    "grupo_Others": "Otros grupos armados",
}


@lru_cache(maxsize=1)
def _rows_by_tile() -> dict[tuple[str, str, str], list[dict]]:
    index: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    if not _CSV_PATH.exists():
        return index
    with open(_CSV_PATH, encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            key = (row.get("tile_zoom", ""), row.get("tile_x", ""), row.get("tile_y", ""))
            index[key].append(row)
    return index


def _row_to_text(row: dict) -> str:
    """Un municipio/zona del mapa como texto con sus atributos."""
    pais = row.get("au_country") or ""
    adm1 = row.get("b_ADM1_ES") or row.get("au_level1") or row.get("b_ADM1_PT") or ""
    adm2 = row.get("b_ADM2_ES") or row.get("au_level2") or row.get("b_ADM2_PT") or ""

    donde = ", ".join(p for p in (adm2, adm1, pais) if p.strip())
    if not donde:
        return ""

    parts = [f"Territorio: {donde}"]
    if row.get("au_area_km2"):
        parts.append(f"área: {row['au_area_km2']} km2")
    if row.get("au_population"):
        parts.append(f"población: {row['au_population']}")

    presentes = [nombre for col, nombre in _GRUPOS.items() if (row.get(col) or "").strip().upper() == "SI"]
    if presentes:
        parts.append("presencia de grupos armados: " + "; ".join(presentes))
    detalle = row.get("grupos_detalle_ES") or row.get("grupos_detalle_EN") or row.get("grupos_detalle_PT")
    if detalle and detalle.strip():
        parts.append(f"detalle: {detalle.strip()}")
    if (row.get("au_invest_with_presence") or "").strip().upper() == "SI":
        parts.append("investigación periodística confirma presencia de economías ilícitas")

    return ". ".join(parts) + "."


def extract_pbf(path) -> dict:
    path = Path(path)
    match = _TILE_PATH.search(path.as_posix())
    if not match:
        return {"text": "", "titulo": path.stem, "idioma": "es", "extra": {}}

    z, x, y = match.groups()
    rows = _rows_by_tile().get((z, x, y), [])

    # Un mismo municipio aparece en varios niveles de zoom: se deduplica por
    # su código administrativo para no repetir la información.
    seen: set[str] = set()
    lines = []
    for row in rows:
        key = row.get("b_ADM2_PCODE") or row.get("au_ID_concatenated") or row.get("fid", "")
        if key in seen:
            continue
        seen.add(key)
        line = _row_to_text(row)
        if line:
            lines.append(line)

    header = (
        f"Mapa de presencia de grupos armados y economías ilícitas en la cuenca amazónica "
        f"(Amazon Underworld), tile de zoom {z}, columna {x}, fila {y}. "
        f"{len(lines)} territorios registrados."
    )
    text = clean_text(header + "\n\n" + "\n".join(lines)) if lines else clean_text(header)

    return {
        "text": text,
        "titulo": f"Amazon Underworld — mapa z{z}/x{x}/y{y}",
        "idioma": "es",
        "extra": {"tile_zoom": z, "tile_x": x, "tile_y": y, "n_territorios": len(lines)},
    }
