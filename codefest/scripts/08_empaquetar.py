#!/usr/bin/env python
"""Empaqueta la entrega: copia la librería, escribe requirements.txt y README.

`generador.py` tiene que correr en la máquina del jurado sin editar nada
(Sección 1.5). Para eso el código de la librería viaja dentro de la entrega, en
./lib, y generador.py lo añade a sys.path él solo.

Uso:
    python scripts/08_empaquetar.py [--con-modelos] [--zip]
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from codefest import config  # noqa: E402

REQUIREMENTS = """\
# Dependencias de generador.py (CODEFEST AD ASTRA 2026, Etapa 1).
# Probado con Python 3.12 en macOS arm64, con torch en CPU y en mps.
#
# generador.py no necesita spacy, pymupdf ni pysbd: esas solo hacen falta para
# reconstruir la base vectorial desde el corpus, no para consultarla. El
# reconocimiento de entidades del lado de la consulta usa el gazetteer
# serializado que viaja en base_vectorial/grafo/gazetteer.json.
faiss-cpu==1.15.0
sentence-transformers==5.7.0
torch==2.13.0
transformers==5.14.1
numpy==2.5.1
networkx==3.6.1
"""

README = """\
# CODEFEST AD ASTRA 2026 - Etapa 1

Base de conocimiento vectorial y modulo de recuperacion.

## Antes de ejecutar: rellenar base_vectorial/

Los indices no caben en GitHub (siete archivos pasan de 100 MB). Estan
publicados como Release en el mismo repositorio. Desde este directorio:

```
mkdir -p base_vectorial && cd base_vectorial
BASE=https://github.com/Jdtorres59/Hackathon-ad-astra/releases/download/base-vectorial-v1
for f in encoder_granite encoder_bge_m3 encoder_e5_large grafo; do
  curl -L -o "$f.tar" "$BASE/$f.tar" && tar -xf "$f.tar" && rm "$f.tar"
done
cd ..
```

Son 1,6 GB. Si `base_vectorial/` ya trae los tres directorios `encoder_*` y
`grafo/`, este paso sobra.

## Ejecucion

```
pip install -r requirements.txt
python generador.py
```

`generador.py` sin argumentos equivale a:

```
python generador.py --consultas consultas.jsonl \\
                    --base-vectorial ./base_vectorial \\
                    --salida resultados.jsonl
```

Lee `consultas.jsonl`, consulta los indices FAISS de `base_vectorial/` y escribe
`resultados.jsonl` con 50 lineas en el esquema de la Seccion 9.3. Al terminar
valida el archivo contra ese esquema y devuelve codigo de salida distinto de
cero si algo no cumple.

Las consultas se codifican siempre en CPU y en fp32, no en el mejor dispositivo
disponible. La razon esta en `lib/codefest/encoders.py`: half precision cambia
el vector de la consulta y con el el orden del ranking, asi que la salida
dependeria de la maquina. Con esto, `resultados.jsonl` es reproducible en
cualquier equipo.

## Identificador de documento

El campo `doc_id` que aparece en `resultados.jsonl` y en `metadata.jsonl` es el
**DOC_ID oficial del inventario del corpus** (`Indice_Datos_Codefest.xlsx`), con
la forma `F1-AIINDEX-001`. Se eligio ese y no uno propio porque el ground truth
lo construyeron los organizadores sobre ese mismo inventario.

Si la evaluacion usa otra convencion, el mapeo no hay que reconstruirlo: cada
linea de `metadata.jsonl` lleva tambien

```
fuente               nombre del archivo original, p.ej. SIPRI_laws-v-0.pdf
ruta_relativa        ruta dentro del corpus entregado
doc_id_inventario    el mismo DOC_ID del inventario
doc_id_secuencial    numeracion propia alternativa (DOC-0001)
```

## Contenido

```
resultados.jsonl        50 lineas, una por consulta (q001..q050)
generador.py            script de reproduccion
informe_tecnico.pdf     decisiones de diseno
consultas.jsonl         consultas usadas para generar resultados.jsonl
requirements.txt        dependencias con versiones fijadas
lib/codefest/           codigo de la libreria que usa generador.py
base_vectorial/
  encoder_<slug>/
    index.faiss         indice FAISS (faiss.read_index)
    metadata.jsonl      una linea por vector, en el orden de los IDs internos
    centroides_fenomeno.npy   3 centroides tematicos (prior suave)
    centroides_documento.npy  un centroide por documento, para podar duplicados
    documentos.json     doc_id en el orden de centroides_documento.npy
  grafo/
    grafo.graphml       grafo de conocimiento (networkx.read_graphml)
    entidad_fragmentos.json   indice entidad -> fragmentos
    gazetteer.json      alias de entidad usados al consultar el grafo
```

## Modelos

Si el directorio `modelos/` esta presente, los pesos se cargan desde ahi y
`generador.py` no necesita conexion a internet. No viajan en el Release de
GitHub porque cada `model.safetensors` supera el limite de 2 GB por asset, asi
que en una copia clonada del repositorio el script los descarga de HuggingFace
la primera vez. Son publicos y de licencia permisiva.

Encoders utilizados (todos arquitectura encoder, licencia permisiva):

- `ibm-granite/granite-embedding-311m-multilingual-r2` (Apache 2.0)
- `BAAI/bge-m3` (MIT)
- `intfloat/multilingual-e5-large` (MIT)
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sin-modelos", action="store_true",
                        help="excluir los pesos del paquete (el jurado tendría que descargarlos)")
    parser.add_argument("--zip", action="store_true")
    args = parser.parse_args()
    con_modelos = not args.sin_modelos

    entrega = config.ENTREGA_DIR
    entrega.mkdir(parents=True, exist_ok=True)

    # 1. Librería
    destino = entrega / "lib" / "codefest"
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(
        config.PROJECT_ROOT / "src" / "codefest",
        destino,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    print(f"  lib/codefest <- src/codefest ({sum(1 for _ in destino.rglob('*.py'))} módulos)")

    # 2. Consultas
    if config.CONSULTAS_JSONL.exists():
        shutil.copy(config.CONSULTAS_JSONL, entrega / "consultas.jsonl")
        print("  consultas.jsonl")

    # 3. Metadatos del paquete
    (entrega / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")
    (entrega / "README.md").write_text(README, encoding="utf-8")
    print("  requirements.txt, README.md")

    # 4. Modelos. La entrega va por enlace a carpeta compartida, sin límite de
    # tamaño, así que se incluyen: es la única forma de garantizar que
    # generador.py corra en la máquina del jurado sin conexión a internet, y la
    # Sección 1.4 excluye de la evaluación lo que no se pueda reproducir.
    modelos = entrega / "modelos"
    # Red de seguridad: el reranker cross-encoder se descartó por la Sección 8.3
    # y su código ya no existe, pero si sus pesos quedaran en disco de alguna
    # prueba anterior no deben viajar en la entrega.
    reranker = modelos / "BAAI__bge-reranker-v2-m3"
    if reranker.exists():
        tam = sum(f.stat().st_size for f in reranker.rglob("*") if f.is_file())
        shutil.rmtree(reranker)
        print(f"  pesos del reranker eliminados del paquete ({tam / 1e9:.1f} GB)")
    if modelos.exists() and not con_modelos:
        tam = sum(f.stat().st_size for f in modelos.rglob("*") if f.is_file())
        print(f"  AVISO: entrega/modelos ocupa {tam / 1e9:.1f} GB y se EXCLUYE del zip")

    # 5. Tamaño final
    def tamano(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    total = tamano(entrega)
    sin_modelos = total - (tamano(modelos) if modelos.exists() else 0)
    print(f"\n  tamaño de la entrega: {sin_modelos / 1e9:.2f} GB sin modelos, {total / 1e9:.2f} GB con modelos")
    for sub in sorted(entrega.iterdir()):
        if sub.is_dir():
            print(f"    {sub.name}/  {tamano(sub) / 1e6:.0f} MB")
        else:
            print(f"    {sub.name}  {sub.stat().st_size / 1e6:.1f} MB")

    if args.zip:
        salida = config.PROJECT_ROOT / "entrega_codefest.zip"
        print(f"\n  comprimiendo -> {salida} ...")
        cmd = ["zip", "-r", "-q", str(salida), entrega.name]
        if not con_modelos:
            cmd += ["-x", f"{entrega.name}/modelos/*"]
        subprocess.run(cmd, cwd=entrega.parent, check=True)
        print(f"  {salida.name}  {salida.stat().st_size / 1e9:.2f} GB")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
