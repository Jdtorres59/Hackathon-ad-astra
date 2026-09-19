# Arquitectura — referencia compartida

Este archivo es el contrato entre los cuatro frentes. Si algo aquí cambia, se avisa en voz alta.

---

## Principio

**Supervisor determinista, especialistas con tope duro de llamadas, redactor sin herramientas.**

La rúbrica penaliza agentes que sobran y premia pocas iteraciones. Blend 360 midió que el 41,8% de los fallos en sistemas multiagente son de diseño y especificación, y el 36,9% desalineación entre agentes. Casi nunca es el modelo.

Cada agente tiene que poder justificarse en el pitch. Si no sabes explicar por qué existe, no existe.

---

## Los agentes

| Agente | LLM | Tools | Tope | Qué NO debe saber |
|---|---|---|---|---|
| `guardia` | no | — | — | — |
| `planner` | sí, barato | ninguna | 1 llamada | texto recuperado, tablero, presupuesto |
| `investigador` | sí | `buscar_corpus`, `expandir_entidad`, `perfil_documento` | 2 tool calls | historial, tono, presupuesto |
| `redactor` | sí, el mejor | ninguna | 1 llamada | cómo se encontró la evidencia |
| `analista` | sí | las 4 de analítica | 3 tool calls | texto de fragmentos |
| `narrador_visual` | sí | ninguna | 1 llamada | cómo se obtuvieron los números |
| `verificador` | sí, distinto del redactor | ninguna | 1 llamada, 1 reescritura | — |

`guardia` no usa modelo: hace filtro de dominio con `gazetteer_hits()`, lookup de caché y chequeo de presupuesto. Cuesta cero y es lo que hace que buena parte de los turnos de desarrollo sean gratis.

---

## Flujo

```
START → guardia
  ├─ fuera de dominio → plantilla sin LLM → END
  ├─ cache hit → END
  └─ → planner
        ├─ rama A (corpus):  investigador ──────────────→ redactor
        ├─ rama B (datos):   analista → narrador_visual → redactor
        └─ rama C (ambas):   [investigador ∥ analista] → narrador_visual → redactor
redactor → (flag y presupuesto) → verificador → END
```

El paralelo de la rama C es seguro porque `investigador` y `analista` escriben claves **disjuntas** del estado, y solo `redactor` escribe `respuesta`.

**Reto 1 = el mismo grafo con las ramas B y C apagadas por flag.** Cero fork de código entre las 08:00 y las 12:30.

`recursion_limit=12` global.

---

## Endpoints

```
GET  /health                         → {status, listo, progreso, componentes, version}
GET  /ready                          → 503 hasta que el Retriever esté caliente
POST /v1/chat            (SSE)       → asistente con streaming
POST /v1/chat/sync       (JSON)      → idéntico sin streaming, para DeepEval y el jurado
GET  /v1/analytics/overview          → KPIs
GET  /v1/analytics/alertas           → serie temporal y geo
GET  /v1/analytics/territorio        → coroplético por ADM1 o ADM2
GET  /v1/analytics/grafo/{entidad}   → subgrafo para Three.js
GET  /v1/documentos/{doc_id}         → metadata y fragmentos
GET  /v1/presupuesto                 → gasto acumulado
```

El endpoint que consuma el jurado se define en el handbook. Será un **adaptador fino sobre el mismo grafo**, en `routers/jurado.py`. No se rediseña nada para él.

---

## Request

```json
POST /v1/chat
{
  "mensaje": "¿Qué grupos armados operan en el trapecio amazónico?",
  "conversacion_id": "c_01H...",
  "filtros_tablero": {"fenomeno":[3], "anio":[2020,2026], "pcodes":["CO91"], "grupos":[]},
  "modo": "rapido"
}
```

`modo` es la palanca de costo expuesta a la interfaz:

- `rapido` — 1 encoder, sin grafo, sin verificador, modelo barato
- `profundo` — 3 encoders, con grafo, con verificador

---

## Eventos SSE

```
event: span.start    {"turno_id","span_id","padre","agente","t"}
event: span.end      {"span_id","agente","ms","tokens_in","tokens_out","costo_usd"}
event: tool.call     {"span_id","tool","args"}
event: tool.result   {"span_id","tool","ms","n_resultados"}
event: token         {"texto"}              ← SOLO del nodo redactor
event: citas         {"citas":[Cita]}
event: grafico       {"spec": {...}}
event: presupuesto   {"costo_turno_usd","costo_total_usd","restante_usd"}
event: done          {"turno_id","ruta":[...],"iteraciones","costo_usd"}
event: error         {"codigo","mensaje"}
```

`graph.astream_events(version="v2")` mapea casi uno a uno.

**Filtra los tokens por nodo** o el JSON del `planner` aparece en la burbuja del chat:

```python
if ev["event"] == "on_chat_model_stream" and ev["metadata"].get("langgraph_node") == "redactor":
```

---

## Respuesta sync

```json
{
  "turno_id": "t_...",
  "respuesta": "markdown con [F3-ALERTAS-032]",
  "citas": [{"doc_id","chunk_id","titulo","fenomeno","observatorio","texto"}],
  "graficos": [],
  "traza": [{"span_id","padre","agente","ms","tokens_in","tokens_out","costo_usd"}],
  "iteraciones": 3,
  "costo_usd": 0.0041
}
```

**El array `traza` es el input por spans de DeepEval.** Diséñalo bien a las 21:00. Retroajustarlo a las 06:00 es el desastre clásico.

---

## Arranque del backend

```python
import codefest  # PRIMERO, antes que faiss y torch
```

`lifespan` lanza `_calentar` en un hilo aparte y devuelve el control de inmediato:

1. `config.set_entrega_dir(os.environ["CODEFEST_ENTREGA_DIR"])` — obligatorio
2. `Retriever(slugs=["bge_m3"], use_graph=False, device="cpu")` — ~40 s
3. `search("prueba")` de calentamiento — ~15 s
4. `app.state.listo.set()`

`/ready` responde 503 hasta el paso 4. `/health` expone el progreso como texto legible.

Los 6,4 GB de `codefest/entrega/` se montan como volumen de solo lectura, no entran a la imagen.

---

## Por qué un solo encoder

`codefest/reports/ablacion.json`:

| Configuración | known_item | títulos | tiempo |
|---|---|---|---|
| solo `bge_m3` | 0,85 | 0,9167 | 8,1 s |
| fusión de los 3 | 0,85 | 0,9167 | 18,2 s |

Métricas idénticas, 2,25 veces el tiempo y el triple de RAM. Además `limitar_hilos_openmp()` deja torch en un hilo, así que tres encoders son tres forward passes monohilo por consulta.

**Es costo-efectividad medida, y eso es criterio de rúbrica.** Va en el pitch.
