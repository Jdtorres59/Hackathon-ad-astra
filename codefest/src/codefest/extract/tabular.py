"""Extracción de CSV y XLSX (Sección 2.1 de la especificación).

Cada fila se convierte en una secuencia de pares `columna: valor`, de modo que
cada valor conserva el nombre de su columna como contexto. Las celdas vacías se
omiten. Cada fila es una unidad de fragmentación independiente.

Los CSV de PubMed/ClinicalTrials del AI Index tienen decenas de miles de filas
de títulos de papers: se limitan por documento para no inundar el índice.
"""

from __future__ import annotations

import csv
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from .. import config
from .clean import clean_text, detect_language

csv.field_size_limit(min(sys.maxsize, 2**31 - 1))

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def _row_to_text(header: list[str], row: list[str]) -> str:
    parts = []
    for col, val in zip(header, row):
        val = (val or "").strip()
        if not val or not col:
            continue
        parts.append(f"{col.strip()}: {val}")
    return " | ".join(parts)


def _sniff_dialect(sample: str) -> csv.Dialect | type[csv.Dialect]:
    try:
        return csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        return csv.excel


def _read_csv_rows(path: Path) -> tuple[list[str], list[list[str]]]:
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            with open(path, encoding=encoding, newline="") as fh:
                sample = fh.read(8192)
                fh.seek(0)
                reader = csv.reader(fh, _sniff_dialect(sample))
                rows = list(reader)
            break
        except UnicodeDecodeError:
            continue
    else:
        return [], []

    if not rows:
        return [], []
    return rows[0], rows[1:]


def _read_xlsx_rows(path: Path) -> list[tuple[str, list[str], list[list[str]]]]:
    """Devuelve [(nombre_hoja, cabecera, filas), ...]."""
    z = zipfile.ZipFile(path)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

    names = []
    try:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        names = [s.get("name", "") for s in wb.iter(f"{_NS}sheet")]
    except Exception:
        pass

    sheet_files = sorted(
        (n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
        key=lambda x: int(re.search(r"\d+", x.split("/")[-1]).group()),
    )

    out = []
    for idx, sf in enumerate(sheet_files):
        root = ET.fromstring(z.read(sf))
        rows: list[list[str]] = []
        for row in root.iter(f"{_NS}row"):
            vals = []
            for cell in row:
                t = cell.get("t")
                v = cell.find(f"{_NS}v")
                if v is not None:
                    vals.append(shared[int(v.text)] if t == "s" else (v.text or ""))
                elif cell.find(f"{_NS}is") is not None:
                    vals.append("".join(x.text or "" for x in cell.iter(f"{_NS}t")))
                else:
                    vals.append("")
            rows.append(vals)
        if not rows:
            continue
        name = names[idx] if idx < len(names) else f"Hoja {idx + 1}"
        out.append((name, rows[0], rows[1:]))
    return out


def _pack(header: list[str], rows: list[list[str]], prefix: str = "") -> list[str]:
    """Agrupa filas en bloques, respetando el tope por documento."""
    per_chunk = config.TABULAR_ROWS_PER_CHUNK
    max_rows = config.TABULAR_MAX_CHUNKS_PER_DOC * per_chunk
    blocks: list[str] = []
    for start in range(0, min(len(rows), max_rows), per_chunk):
        lines = [_row_to_text(header, r) for r in rows[start : start + per_chunk]]
        lines = [ln for ln in lines if ln.strip()]
        if not lines:
            continue
        blocks.append((prefix + "\n" if prefix else "") + "\n".join(lines))
    return blocks


def extract_tabular(path) -> dict:
    path = Path(path)
    blocks: list[str] = []
    n_rows = 0

    if path.suffix.lower() == ".csv":
        header, rows = _read_csv_rows(path)
        n_rows = len(rows)
        cabecera = "Columnas: " + ", ".join(c for c in header if c.strip())
        blocks = _pack(header, rows, cabecera)
    else:
        for sheet_name, header, rows in _read_xlsx_rows(path):
            n_rows += len(rows)
            cabecera = f"Hoja: {sheet_name}. Columnas: " + ", ".join(c for c in header if c.strip())
            blocks.extend(_pack(header, rows, cabecera))

    text = clean_text("\n\n".join(blocks))
    return {
        "text": text,
        "titulo": path.stem,
        "idioma": detect_language(text),
        "extra": {"n_filas": n_rows, "truncado": n_rows > config.TABULAR_MAX_CHUNKS_PER_DOC * config.TABULAR_ROWS_PER_CHUNK},
        "blocks": blocks,
    }
