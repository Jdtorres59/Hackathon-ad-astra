#!/usr/bin/env bash
# Pipeline completo, de corpus a entrega.
#
#   bash scripts/run_all.sh [--desde PASO]
#
# Pasos: extraer, titulos, fragmentar, codificar, grafo, centroides,
#        generar, validar, informe, empaquetar
#
# La codificación y el grafo son lo lento (~4 h y ~25 min). El grafo usa CPU y
# la codificación la GPU, así que se lanzan en paralelo.

set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$AQUI/.venv/bin/python"
cd "$AQUI"

DESDE="${2:-extraer}"
PASOS=(extraer titulos fragmentar codificar grafo centroides generar validar informe empaquetar)

activo=0
toca() {
  [ "$1" = "$DESDE" ] && activo=1
  [ "$activo" = "1" ]
}

paso() { echo -e "\n\033[1m=== $* ===\033[0m"; }

toca extraer     && { paso "1/10 Extracción del corpus";        "$PY" scripts/01_extract.py --workers 8; }
toca titulos     && { paso "2/10 Saneamiento de títulos";       "$PY" scripts/01b_titulos.py | tail -5; }
toca fragmentar  && { paso "3/10 Fragmentación";                "$PY" scripts/02_chunk.py --workers 8 | tail -8; }

if toca codificar; then
  paso "4/10 Codificación y grafo (en paralelo: GPU y CPU)"
  "$PY" scripts/03_embed_index.py --encoders e5_large,bge_m3,granite > /tmp/embed.log 2>&1 &
  PID_EMBED=$!
  "$PY" scripts/04_grafo.py --workers 4 > /tmp/grafo.log 2>&1 &
  PID_GRAFO=$!
  echo "  codificación pid=$PID_EMBED (log /tmp/embed.log)"
  echo "  grafo        pid=$PID_GRAFO (log /tmp/grafo.log)"
  wait $PID_GRAFO && tail -20 /tmp/grafo.log
  wait $PID_EMBED && grep -aE "===|codificados|escrito|verificación" /tmp/embed.log
fi

toca centroides  && { paso "6/10 Centroides por fenómeno";      "$PY" scripts/06_centroides.py; }
toca generar     && { paso "7/10 Generación de resultados";     (cd entrega && "$PY" generador.py); }
toca validar     && { paso "8/10 Validación de la entrega";     "$PY" scripts/07_validar.py; }
toca informe     && { paso "9/10 Informe técnico";              "$PY" scripts/10_informe.py; }
toca empaquetar  && { paso "10/10 Empaquetado";                 "$PY" scripts/08_empaquetar.py; }

echo -e "\n\033[1mPipeline completo.\033[0m"
