#!/usr/bin/env python
"""Repara las palabras partidas por guion blando en el corpus ya procesado.

El limpiador original (`extract/clean.py`) unía las palabras cortadas por guion
visible seguido de salto de línea, pero no las cortadas por guion blando
(U+00AD) seguido de espacio, que es como PyMuPDF entrega el guionado de varios
informes maquetados a dos columnas. Resultado: 8.085 fragmentos de 182
documentos entraban al índice con "align ment" en vez de "alignment".

`clean.py` ya está corregido para cualquier reproceso desde cero. Este script
aplica el mismo arreglo sobre los intermedios ya calculados, que es mucho más
barato que volver a extraer y re-OCR-izar 2,9 GB de PDF.

Deliberadamente NO vuelve a fragmentar. La corrección solo borra caracteres
dentro de cada fragmento, así que las fronteras siguen cayendo donde caían —en
límite de oración, como exige la Sección 3.3— y los chunk_id, su número y su
orden se conservan. Eso permite recodificar únicamente las filas tocadas en vez
de las 91.088.

Uso:
    python scripts/02b_desguionizar.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.extract.clean import (  # noqa: E402
    _SOFT_HYPHEN_BREAK,
    _SOFT_HYPHEN_SUELTO,
)

CAMPOS_TEXTO = ("texto", "texto_embed", "titulo", "seccion")


def desguionizar(texto: str) -> str:
    if not texto or "\xad" not in texto:
        return texto
    return _SOFT_HYPHEN_SUELTO.sub("", _SOFT_HYPHEN_BREAK.sub(r"\1\2", texto))


def contar_palabras(texto: str) -> int:
    return len(texto.split())


def reparar_jsonl(ruta, campos: tuple[str, ...], recontar: bool, dry_run: bool) -> dict:
    filas_tocadas = 0
    total = 0
    salida = []
    ejemplos: list[tuple[str, str]] = []

    with open(ruta, encoding="utf-8") as fh:
        for linea in fh:
            if not linea.strip():
                continue
            reg = json.loads(linea)
            total += 1
            tocada = False
            for campo in campos:
                original = reg.get(campo)
                if not isinstance(original, str) or "\xad" not in original:
                    continue
                arreglado = desguionizar(original)
                if arreglado != original:
                    if len(ejemplos) < 5 and campo == "texto":
                        i = original.find("\xad")
                        ejemplos.append((original[max(0, i - 28):i + 28], reg.get("chunk_id", reg.get("doc_id", "?"))))
                    reg[campo] = arreglado
                    tocada = True
            if tocada:
                filas_tocadas += 1
                if recontar and isinstance(reg.get("texto"), str):
                    reg["n_palabras"] = contar_palabras(reg["texto"])
            salida.append(reg)

    if not dry_run and filas_tocadas:
        shutil.copy2(ruta, str(ruta) + ".pre_desguionizado")
        with open(ruta, "w", encoding="utf-8") as fh:
            for reg in salida:
                fh.write(json.dumps(reg, ensure_ascii=False) + "\n")

    return {"total": total, "tocadas": filas_tocadas, "ejemplos": ejemplos}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Reparando docs.jsonl ...")
    d = reparar_jsonl(config.DOCS_JSONL, ("texto", "titulo"), False, args.dry_run)
    print(f"  {d['tocadas']:,} de {d['total']:,} documentos")

    print("Reparando chunks.jsonl ...")
    c = reparar_jsonl(config.CHUNKS_JSONL, CAMPOS_TEXTO, True, args.dry_run)
    print(f"  {c['tocadas']:,} de {c['total']:,} fragmentos")

    for muestra, cid in c["ejemplos"]:
        print(f"    {cid:34} {muestra!r}")

    # Las filas tocadas son justo las que hay que recodificar. Se dejan escritas
    # para que 03_embed_index.py no tenga que volver a deducirlas.
    if not args.dry_run:
        filas = []
        with open(config.CHUNKS_JSONL, encoding="utf-8") as fh:
            previo = {}
            ruta_previa = str(config.CHUNKS_JSONL) + ".pre_desguionizado"
            if os.path.exists(ruta_previa):
                with open(ruta_previa, encoding="utf-8") as fh2:
                    for i, linea in enumerate(fh2):
                        if linea.strip():
                            previo[i] = json.loads(linea)["texto_embed"]
            for i, linea in enumerate(fh):
                if linea.strip() and previo.get(i) != json.loads(linea)["texto_embed"]:
                    filas.append(i)
        destino = config.DATA_DIR / "filas_recodificar.json"
        with open(destino, "w", encoding="utf-8") as fh:
            json.dump(filas, fh)
        print(f"\n{len(filas):,} filas cambiaron `texto_embed` -> {destino}")

    if args.dry_run:
        print("\n(dry-run: no se escribió nada)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
