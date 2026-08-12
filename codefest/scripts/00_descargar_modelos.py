#!/usr/bin/env python
"""Descarga los encoders a entrega/modelos/ para que generador.py sea autónomo.

El jurado ejecuta `python generador.py` sin editar nada (Sección 1.5). Si los
pesos viajan dentro de la entrega, el script no depende de que la máquina del
jurado tenga red ni caché de HuggingFace.

Uso:
    python scripts/00_descargar_modelos.py [--encoders granite,bge_m3]
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402
from codefest.encoders import download_models  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--encoders", default=None)
    args = parser.parse_args()

    config.ensure_dirs()
    slugs = [s.strip() for s in args.encoders.split(",")] if args.encoders else None
    download_models(slugs)

    base = config.ENTREGA_DIR / "modelos"
    if base.exists():
        total = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
        print(f"\nTamaño total de los modelos: {total / 1e9:.2f} GB en {base}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
