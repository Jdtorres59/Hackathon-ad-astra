#!/usr/bin/env bash
# Prueba de reproducibilidad: simula lo que hará el jurado.
#
# Crea un entorno virtual limpio, instala solo lo que dice requirements.txt,
# copia la entrega a un directorio temporal (para descartar dependencias
# accidentales del árbol de desarrollo) y ejecuta `python generador.py` sin
# argumentos. Después compara la salida con la que se entregó.
#
# El paso [5/5] repite la ejecución fingiendo que la máquina no tiene GPU, y no
# es un extra: durante la revisión final se descubrió que la entrega moría con
# SIGSEGV en CPU y que, una vez viva, devolvía otro ranking en 15 de las 50
# consultas. Esta prueba corría solo en un Mac con mps y decía "IDÉNTICO" las dos
# veces. Una prueba de reproducibilidad que solo prueba una máquina no prueba
# reproducibilidad.
#
# Uso:  bash scripts/11_prueba_jurado.sh [ruta_entrega]

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENTREGA="${1:-$AQUI/entrega}"
TMP="$(mktemp -d)"
trap 'echo "  limpiando $TMP"; rm -rf "$TMP"' EXIT

echo "=== Prueba del jurado ==="
echo "  entrega: $ENTREGA"
echo "  sandbox: $TMP"

if [ ! -f "$ENTREGA/generador.py" ]; then
  echo "ERROR: no existe $ENTREGA/generador.py" >&2
  exit 1
fi

# 1. Copia la entrega fuera del árbol de desarrollo.
#    Los modelos se enlazan en vez de copiarse: son varios GB y lo que se está
#    probando es el código, no el copiado de pesos.
echo -e "\n[1/5] Copiando la entrega a un directorio limpio..."
mkdir -p "$TMP/entrega"
for item in "$ENTREGA"/*; do
  nombre="$(basename "$item")"
  if [ "$nombre" = "modelos" ]; then
    ln -s "$item" "$TMP/entrega/modelos"
  else
    cp -R "$item" "$TMP/entrega/$nombre"
  fi
done
rm -f "$TMP/entrega/resultados.jsonl"

# 2. Entorno virtual limpio con solo requirements.txt
echo -e "\n[2/5] Creando entorno virtual limpio e instalando requirements.txt..."
uv venv --python 3.12 "$TMP/venv" >/dev/null 2>&1
uv pip install --python "$TMP/venv/bin/python" -r "$TMP/entrega/requirements.txt" >/dev/null 2>&1
echo "  instalado: $("$TMP/venv/bin/python" -m pip list 2>/dev/null | wc -l | tr -d ' ') paquetes"

# 3. Ejecución exacta del contrato de invocación: sin argumentos
echo -e "\n[3/5] Ejecutando 'python generador.py' sin argumentos..."
INICIO=$(date +%s)
( cd "$TMP/entrega" && "$TMP/venv/bin/python" generador.py ) || {
  echo "ERROR: generador.py devolvió código distinto de cero" >&2
  exit 1
}
echo "  tardó $(( $(date +%s) - INICIO ))s"

# 4. Comparación con lo entregado
echo -e "\n[4/5] Comparando con el resultados.jsonl entregado..."
if [ ! -f "$ENTREGA/resultados.jsonl" ]; then
  echo "  (no hay resultados.jsonl previo con el que comparar)"
elif diff -q "$ENTREGA/resultados.jsonl" "$TMP/entrega/resultados.jsonl" >/dev/null; then
  echo "  IDÉNTICO: la salida se reproduce byte a byte"
else
  echo "  DIFIERE. Comparando por consulta:"
  "$TMP/venv/bin/python" - "$ENTREGA/resultados.jsonl" "$TMP/entrega/resultados.jsonl" <<'PY'
import json, sys
a = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
b = [json.loads(l) for l in open(sys.argv[2], encoding='utf-8') if l.strip()]
igual_docs = igual_frags = 0
for x, y in zip(a, b):
    if [d['doc_id'] for d in x['documents']] == [d['doc_id'] for d in y['documents']]:
        igual_docs += 1
    if [f['chunk_id'] for f in x['fragments']] == [f['chunk_id'] for f in y['fragments']]:
        igual_frags += 1
    else:
        print(f"    {x['query_id']}: documentos {[d['doc_id'] for d in x['documents']]} -> {[d['doc_id'] for d in y['documents']]}")
print(f"  consultas con los mismos 3 documentos:  {igual_docs}/{len(a)}")
print(f"  consultas con los mismos 10 fragmentos: {igual_frags}/{len(a)}")
PY
fi

# 5. La misma ejecución en una máquina fingida sin GPU. Es donde corre el jurado
#    (requirements.txt fija faiss-cpu) y donde estaban los dos fallos que ninguna
#    de las pruebas anteriores podía ver: el SIGSEGV de OpenMP y el cambio de
#    ranking por media precisión.
echo -e "\n[5/5] Repitiendo sin GPU (torch en CPU)..."
mv "$TMP/entrega/resultados.jsonl" "$TMP/con_gpu.jsonl"
( cd "$TMP/entrega" && "$TMP/venv/bin/python" -c "
import torch
torch.backends.mps.is_available = lambda: False
torch.cuda.is_available = lambda: False
import runpy, sys
sys.argv = ['generador.py', '--quiet']
runpy.run_path('generador.py', run_name='__main__')
" ) || {
  echo "  ERROR: sin GPU, generador.py devolvió código distinto de cero" >&2
  echo "  (código 139 = SIGSEGV: los runtimes de OpenMP de faiss y torch chocan)" >&2
  exit 1
}
if diff -q "$TMP/con_gpu.jsonl" "$TMP/entrega/resultados.jsonl" >/dev/null; then
  echo "  IDÉNTICO con y sin GPU: la salida no depende del procesador"
else
  echo "  DIFIERE segun haya GPU o no. La entrega no es reproducible." >&2
  "$TMP/venv/bin/python" - "$TMP/con_gpu.jsonl" "$TMP/entrega/resultados.jsonl" <<'PY'
import json, sys
a = [json.loads(l) for l in open(sys.argv[1], encoding='utf-8') if l.strip()]
b = [json.loads(l) for l in open(sys.argv[2], encoding='utf-8') if l.strip()]
d = sum(1 for x, y in zip(a, b)
        if [i['doc_id'] for i in x['documents']] != [i['doc_id'] for i in y['documents']])
f = sum(1 for x, y in zip(a, b)
        if [i['chunk_id'] for i in x['fragments']] != [i['chunk_id'] for i in y['fragments']])
print(f"    consultas con distinto top-3 documentos:  {d}/{len(a)}")
print(f"    consultas con distinto top-10 fragmentos: {f}/{len(a)}")
PY
  exit 1
fi

echo -e "\n=== Prueba completada ==="
