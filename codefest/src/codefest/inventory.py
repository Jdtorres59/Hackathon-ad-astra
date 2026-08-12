"""Inventario de documentos.

El corpus trae `Indice_Datos_Codefest.xlsx` con la hoja "Inventario de Archivos",
que mapea cada uno de los 1.826 archivos a un DOC_ID oficial. Ese archivo es la
fuente de verdad: define qué es un documento y qué identificador lleva.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

from . import config

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"

# Extensión de archivo -> valor del campo `formato` de la Tabla 2
FORMATO_POR_EXT = {
    ".pdf": "pdf",
    ".json": "json",
    ".csv": "csv",
    ".xlsx": "xlsx",
    ".txt": "txt",
    ".jpg": "imagen",
    ".jpeg": "imagen",
    ".png": "imagen",
    ".avif": "imagen",
    ".webp": "imagen",
    ".pbf": "pbf",
}


@dataclass
class DocRecord:
    """Un documento del corpus: un archivo con su identidad y procedencia."""

    doc_id: str  # el que se escribe en la salida (según DOC_ID_SCHEME)
    doc_id_inventario: str  # F1-AIINDEX-001
    doc_id_secuencial: str  # DOC-0001
    path: Path
    fuente: str  # nombre del archivo original
    ruta_relativa: str
    formato: str
    fenomeno: int  # 1, 2 o 3
    observatorio: str
    codigo_observatorio: str
    tipo_inventario: str
    titulo: str = ""
    idioma: str = ""
    fecha: str = ""
    url: str = ""
    extra: dict = field(default_factory=dict)


def _read_sheet(xlsx: Path, sheet_index: int) -> list[list[str]]:
    """Lee una hoja de un .xlsx sin depender de openpyxl."""
    z = zipfile.ZipFile(xlsx)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

    sheet_files = sorted(
        (n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
        key=lambda x: int(re.search(r"\d+", x.split("/")[-1]).group()),
    )
    root = ET.fromstring(z.read(sheet_files[sheet_index]))

    rows: list[list[str]] = []
    for row in root.iter(f"{_NS}row"):
        vals: list[str] = []
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
    return rows


def load_inventory(scheme: str | None = None) -> list[DocRecord]:
    """Devuelve los 1.826 documentos del corpus, en el orden del inventario."""
    scheme = scheme or config.DOC_ID_SCHEME
    rows = _read_sheet(config.INVENTORY_XLSX, sheet_index=2)
    header, data = rows[0], rows[1:]
    if header[:7] != [
        "Fenómeno",
        "Observatorio",
        "Código Observatorio",
        "DOC_ID",
        "Nombre estandarizado",
        "Carpeta",
        "Tipo",
    ]:
        raise ValueError(f"Cabecera inesperada en el inventario: {header[:7]}")

    docs: list[DocRecord] = []
    for i, row in enumerate(data, start=1):
        fen, obs, cod, doc_id_inv, nombre, carpeta, tipo = row[:7]
        if not doc_id_inv:
            continue
        path = config.CORPUS_DIR / carpeta / nombre
        doc_id_seq = f"DOC-{i:04d}"
        docs.append(
            DocRecord(
                doc_id=doc_id_inv if scheme == "inventario" else doc_id_seq,
                doc_id_inventario=doc_id_inv,
                doc_id_secuencial=doc_id_seq,
                path=path,
                fuente=nombre,
                ruta_relativa=f"{carpeta}/{nombre}",
                formato=FORMATO_POR_EXT.get(path.suffix.lower(), path.suffix.lower().lstrip(".")),
                fenomeno=int(fen.replace("F", "")),
                observatorio=obs,
                codigo_observatorio=cod,
                tipo_inventario=tipo,
            )
        )
    return docs


def check_inventory(docs: list[DocRecord]) -> dict:
    """Verifica que cada entrada del inventario exista en disco."""
    faltantes = [d.ruta_relativa for d in docs if not d.path.exists()]
    ids = [d.doc_id for d in docs]
    return {
        "total": len(docs),
        "faltantes": faltantes,
        "ids_duplicados": len(ids) - len(set(ids)),
        "por_formato": {f: sum(1 for d in docs if d.formato == f) for f in sorted({d.formato for d in docs})},
        "por_fenomeno": {f: sum(1 for d in docs if d.fenomeno == f) for f in (1, 2, 3)},
    }
