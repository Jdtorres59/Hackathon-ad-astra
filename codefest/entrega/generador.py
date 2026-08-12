#!/usr/bin/env python
"""Genera resultados.jsonl a partir de la base vectorial entregada.

Contrato de invocación (Sección 1.5 de la especificación técnica):

    python generador.py --consultas consultas.jsonl \
                        --base-vectorial ./base_vectorial \
                        --salida resultados.jsonl

Los tres argumentos son opcionales y sus valores por defecto corresponden a la
estructura del directorio de entrega, de modo que

    python generador.py

sin argumentos, ejecutado desde la raíz de la entrega, produce el mismo
resultado.

No interviene ningún modelo generativo en ninguna etapa (Sección 8.3): la
recuperación opera exclusivamente sobre vectores, puntuaciones de similitud
coseno y metadata.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent

# El código de la librería viaja dentro de la entrega en ./lib. En el repositorio
# de desarrollo se cae a ../src, para ejecutar exactamente el mismo generador.
for candidate in (HERE / "lib", HERE.parent / "src"):
    if (candidate / "codefest").is_dir():
        sys.path.insert(0, str(candidate))
        break

from codefest import config  # noqa: E402
from codefest.consultas import load_consultas  # noqa: E402
from codefest.output import build_result, validate_results, write_results  # noqa: E402
from codefest.retrieve import Retriever  # noqa: E402

# Reapunta modelos, base vectorial y grafo a la ubicación real de esta entrega
config.set_entrega_dir(HERE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Recuperación sobre la base vectorial de CODEFEST AD ASTRA 2026")
    parser.add_argument("--consultas", default=str(HERE / "consultas.jsonl"))
    parser.add_argument("--base-vectorial", default=str(HERE / "base_vectorial"))
    parser.add_argument("--salida", default=str(HERE / "resultados.jsonl"))
    parser.add_argument("--fusion", default="rrf", choices=("rrf", "combsum", "combmnz"))
    parser.add_argument("--sin-grafo", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    verbose = not args.quiet

    consultas_path = Path(args.consultas)
    if not consultas_path.exists():
        print(f"ERROR: no se encontró el archivo de consultas: {consultas_path}", file=sys.stderr)
        return 2

    consultas = load_consultas(consultas_path)
    if verbose:
        print(f"Consultas: {len(consultas)} desde {consultas_path}")

    t0 = time.time()
    retriever = Retriever(
        base_dir=args.base_vectorial,
        use_graph=not args.sin_grafo,
        verbose=verbose,
    )
    if verbose:
        print(f"Base vectorial: {len(retriever.slugs)} encoder(s) {retriever.slugs}, "
              f"{len(retriever.meta)} fragmentos, cargada en {time.time() - t0:.0f}s")

    t0 = time.time()
    resultados = []
    for i, q in enumerate(consultas, start=1):
        hits = retriever.search(q["texto"], fusion_method=args.fusion)
        resultados.append(build_result(q["query_id"], hits))
        if verbose and (i % 10 == 0 or i == len(consultas)):
            print(f"  {i}/{len(consultas)}  {time.time() - t0:.0f}s", flush=True)

    write_results(resultados, args.salida)
    if verbose:
        print(f"Escrito {args.salida} ({len(resultados)} líneas) en {time.time() - t0:.0f}s")

    informe = validate_results(args.salida, n_expected=len(consultas))
    if informe["errores"]:
        print("\nEL ARCHIVO DE RESULTADOS NO CUMPLE EL ESQUEMA:", file=sys.stderr)
        for e in informe["errores"][:20]:
            print(f"  - {e}", file=sys.stderr)
        return 1
    if verbose:
        print(f"Validación OK: {informe['n_lineas']} líneas, "
              f"máximo {informe['max_palabras_fragmento']} palabras por fragmento")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
