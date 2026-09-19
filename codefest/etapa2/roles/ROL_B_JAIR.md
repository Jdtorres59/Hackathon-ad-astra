# Frente B — Agentes y LangGraph · Jair

> Lee primero `AGENTS.md` en la raíz del repo. Este documento asume que ya lo leíste.

## Por qué te tocó este frente

Es el corazón del reto y lo que evalúa DeepEval. También es el frente con más trabajo intelectual continuo y el que peor tolera interrupciones, así que ponte audífonos y que las preguntas de logística se las hagan a Juanes.

## Tu regla de oro

**Supervisor determinista, especialistas con tope duro de llamadas, redactor sin herramientas.** Nada de enjambre ReAct donde todos los agentes hablan con todos.

El dato que justifica esto, de la charla de Blend 360: **41,8% de los fallos en sistemas multiagente son de diseño y especificación, 36,9% son desalineación entre agentes.** Casi nunca es el modelo. Y la rúbrica premia pocas iteraciones.

---

## Tus archivos

```
backend/app/agentes/guardia.py
backend/app/agentes/planner.py
backend/app/agentes/investigador.py
backend/app/agentes/redactor.py
backend/app/agentes/analista.py           ← Reto 2
backend/app/agentes/narrador_visual.py    ← Reto 2
backend/app/agentes/verificador.py        ← extra, tras flag
backend/app/grafo/estado.py
backend/app/grafo/construir.py
backend/app/grafo/limites.py
backend/app/prompts/*.md                  ← los prompts como archivos, no literales
backend/app/routers/chat.py               ← el SSE
```

Los prompts van en archivos `.md` separados por dos razones: se diffean, y se pueden mostrar en el pitch.

---

## Los agentes

### `guardia` — sin LLM, coste cero

Filtro de dominio, lookup de caché, chequeo de presupuesto. Usa `gazetteer_hits()` de `codefest/src/codefest/graph/ner.py:86`, que corre en microsegundos sin cargar ningún modelo.

Existe por dos razones: hace que buena parte de los turnos durante el desarrollo cuesten cero, y cierra la puerta al prompt injection por dominio abierto, que Blend 360 nombró como antipatrón.

### `planner` — sin tools

Una sola llamada con salida estructurada. Devuelve `QueryPlan` (definido en `contratos.py`, lo escribe Juanes).

Recibe las entidades **ya detectadas por el gazetteer**, así que su trabajo es filtrar y clasificar, no inventar. Eso reduce alucinación de entidades y lo deja en una sola iteración. Usa el modelo más barato del catálogo.

**Qué NO debe saber**: texto recuperado, estado del tablero, presupuesto, nombres de herramientas.

### `investigador` — tope 2 tool calls

Tools: `buscar_corpus`, `expandir_entidad`, `perfil_documento`. Las escribe Joseph; tú consumes las firmas.

Recupera evidencia y la devuelve como `Evidencia`. **No redacta.**

**Qué NO debe saber**: historial de chat, tono pedido, presupuesto. Menos contexto es menos ruido.

### `redactor` — sin tools

Prosa con el tono que diga el handbook y citas inline tipo `[F3-ALERTAS-032]`. Se streamea token a token.

**Qué NO debe saber**: cómo se encontró la evidencia, esquemas de tools, presupuesto.

Que el redactor no tenga herramientas es la recomendación más concreta de la charla de Rubén Manrique: separar el nodo que busca del que redacta mejora la redacción de forma notable.

### Reto 2: `analista` — tope 3 tool calls

Decide **qué rebanada** de datos mirar. **Nunca calcula**: consume resultados deterministas de las tools de Joseph, que leen Parquet.

**Qué NO debe saber**: texto de fragmentos, eso es del investigador.

### Reto 2: `narrador_visual` — sin tools

Recibe los números del análisis como tabla compacta, máximo unas 40 filas, más los filtros activos del tablero. Devuelve 3 a 5 hallazgos, cada uno anclado a **una cifra y a un `doc_id`**.

Esto es literalmente lo que justifica el criterio "mejora el análisis que puede hacer un humano". No lo fusiones con `analista`: si el mismo agente elige la rebanada y la narra, elegirá la que ya sabe narrar.

### Extra: `verificador`

Una llamada, **modelo distinto del redactor** (recomendación explícita de Bantor: un modelo no debe ser juez de su propio trabajo). Entrada: borrador y lista de evidencia. Salida: `{ok, afirmaciones_sin_soporte}`. **Máximo una reescritura.** Detrás de `ENABLE_VERIFICADOR`, se apaga solo en modo ahorro.

---

## El grafo

```python
class EstadoAsistente(TypedDict):
    mensajes: Annotated[list[AnyMessage], add_messages]
    conversacion_id: str
    turno_id: str
    filtros_tablero: dict          # {fenomeno, anio, pcodes, grupos}
    modo: Literal["rapido","profundo"]
    plan: QueryPlan | None
    evidencia: Evidencia | None    # lo escribe SOLO investigador
    analisis: Analisis | None      # lo escribe SOLO analista
    respuesta: str                 # lo escribe SOLO redactor
    citas: list[Cita]
    spec_graficos: list[dict]
    iteraciones: int
    costo_usd: float
    ruta: list[str]                # los spans, para DeepEval
```

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

El fan-out paralelo de la rama C **es seguro** porque `investigador` y `analista` escriben claves disjuntas del estado, y solo `redactor` escribe `respuesta`. Así se esquiva el antipatrón de varios escritores en paralelo, que según Blend 360 nunca convergen.

**El mismo archivo compila el Reto 1** con las ramas B y C apagadas por flag. Cero fork de código entre las 08:00 y las 12:30. Esto es lo que te permite dormir entre las 03:00 y las 05:00.

Tope global: `graph.compile().with_config(recursion_limit=12)`.

---

## El SSE: la traza se streamea, no solo la respuesta

`routers/chat.py` expone `POST /v1/chat` en SSE y `POST /v1/chat/sync` en JSON. El segundo es el que consume DeepEval y probablemente el jurado.

```
event: span.start    {"turno_id","span_id","padre","agente":"planner","t":0.12}
event: span.end      {"span_id","agente","ms":840,"tokens_in","tokens_out","costo_usd"}
event: tool.call     {"span_id","tool":"buscar_corpus","args":{...}}
event: tool.result   {"span_id","tool","ms":1240,"n_resultados":10}
event: token         {"texto":"..."}          ← SOLO del nodo redactor
event: citas         {"citas":[...]}
event: grafico       {"spec": {...}}
event: presupuesto   {"costo_turno_usd","costo_total_usd","restante_usd"}
event: done          {"turno_id","ruta":[...],"iteraciones":3,"costo_usd":0.0041}
event: error         {"codigo","mensaje"}
```

`graph.astream_events(version="v2")` mapea casi uno a uno: `on_chain_start/end` a `span.*`, `on_tool_start/end` a `tool.*`, `on_chat_model_stream` a `token`.

**El bug que te va a costar una hora a las 02:00 si no lo previenes ahora:**

```python
if ev["event"] == "on_chat_model_stream" and ev["metadata"].get("langgraph_node") == "redactor":
```

Sin ese filtro, el JSON del `planner` se derrama en la burbuja del chat.

**Diseña bien el array `traza` a las 21:00.** Es literalmente el input por spans de DeepEval. Retroajustarlo a las 06:00 es el desastre clásico de estos eventos.

---

## Docstrings: es donde más rinde tu tiempo

Con modelos open source, el docstring de una tool es la diferencia entre 2 y 6 iteraciones. Joseph escribe las tools, pero **tú revisas sus docstrings** porque tú ves las trazas.

Cuatro cosas en cada uno: cuándo usarla, cuándo **no** usarla, restricciones de argumentos, y un ejemplo de una línea.

Y el bucle silencioso que quema presupuesto se mata así: cuando una búsqueda no encuentra nada, devuelve un resultado **terminal**, no una lista vacía.

```python
{"resultados": [], "mensaje": "Sin resultados. NO reintentes reformulando; informa al usuario de que no hay cobertura."}
```

Aun así, el contador de `pre_model_hook` es lo que de verdad lo enforcea, porque el modelo ignorará el mensaje a veces.

---

## Tus hitos

| Hora | Qué tiene que estar |
|---|---|
| 21:00 | Rebasado sobre los contratos de Juanes |
| **22:30 CP1** | `planner` y `redactor` con evidencia falsa, y un stream SSE llegando al navegador |
| 23:30 | Mergeas el grafo contra las herramientas reales de Joseph |
| **00:30 CP2** | Una pregunta real devuelve respuesta real con citas, en el contenedor desplegado |
| **03:00 CP3** | Las 15 preguntas golden pasan de punta a punta con costo medido por pregunta |

Si CP2 se pasa de la 01:30, **corta la rama de grafo y entrega con 2 agentes**. Cumplir el mínimo a tiempo vale infinitamente más que tres agentes que no llegan.

En CP3, si alguna pregunta supera 0,02 USD: **arregla el prompt, no cambies el modelo.**
