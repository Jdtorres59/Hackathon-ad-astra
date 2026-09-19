# Contexto para agentes de IA — Equipo AstroNova, CODEFEST AD ASTRA 2026

Si eres un asistente de IA trabajando en este repositorio durante el reto presencial, **lee este archivo completo antes de escribir código**. Está escrito para ti.

---

## Qué es esto

Hackathon de 24 horas de la Fuerza Aérea Colombiana con la Universidad de los Andes. Dos entregas con hora exacta:

- **Reto 1, sábado 08:00** — asistente conversacional con interfaz gráfica, mínimo 2 agentes orquestados.
- **Reto 2, sábado 12:30** — tablero de analítica visual conectado al asistente, mínimo 3 agentes.

**Un milisegundo tarde es cero.** Esto no es una figura retórica, lo dijeron textualmente.

Detalle completo del reto en `codefest/etapa2/RETO.md`. Contexto del ciclo de conferencias previo en `codefest/etapa2/BRIEFING.md`.

---

## Reglas que no se negocian

1. **No toques `codefest/src/`, `codefest/scripts/` ni `codefest/entrega/`.** Es el entregable de la Etapa 1, sigue pendiente de retroalimentación. Se consume como librería, no se modifica.
2. **Nunca escribas credenciales en el código.** Todo por variables de entorno. Esto es criterio calificable explícito de la rúbrica.
3. **Tope duro de iteraciones en todo bucle de agente.** Un agente que no encuentra lo que busca reintenta en silencio, no lanza excepción, no aparece en logs, y se come el presupuesto. Hay penalidad por excederlo.
4. **No inventes el contrato del endpoint del jurado.** Está en el handbook. Si aún no ha llegado, deja el adaptador marcado como pendiente y sigue con lo demás.
5. **Respeta tu frente.** Cada persona tiene archivos asignados en `codefest/etapa2/roles/`. Si necesitas tocar un archivo de otro frente, se avisa en voz alta primero.

---

## Restricciones de infraestructura

- **Solo modelos open source** vía un gateway **LiteLLM** sobre Amazon Bedrock. No hay Claude, GPT ni Gemini en runtime. El cliente LLM vive detrás de una sola abstracción configurable por entorno.
- **El presupuesto se mide en dinero, no en tokens.** Al agotarse, el agente deja de responder. Pedir más tiene penalidad.
- **El despliegue es en Coolify local.** Los jurados evalúan lo desplegado, no lo que corre en el portátil de alguien.
- **La evaluación usa DeepEval sobre la traza del agente por spans**, no solo la respuesta final. Menos iteraciones puntúa mejor. La costo-efectividad es criterio explícito.

---

## Lo que ya existe y hay que reutilizar

La Etapa 1 dejó un motor de recuperación completo y probado. **No lo reimplementes.**

```python
import codefest                      # PRIMERO, antes que faiss o torch
from codefest import config
config.set_entrega_dir("/ruta/a/codefest/entrega")   # OBLIGATORIO
from codefest.retrieve import Retriever

r = Retriever(base_dir=..., slugs=["bge_m3"], use_graph=False, device="cpu")
hits = r.search("minería ilegal en el Amazonas")
# -> {"documents": [{"rank","doc_id","_score"}],
#     "fragments": [{"rank","chunk_id","doc_id","text","_score","_row"}]}
```

`_row` indexa `r.meta` y da los 18 campos de metadata del fragmento.

**Tres trampas que cuestan horas si se ignoran:**

1. `import codefest` va **antes** que faiss y torch. Pone `KMP_DUPLICATE_LIB_OK`. Sin eso, SIGSEGV en CPU sin traza.
2. `config.set_entrega_dir()` es **obligatorio**, no opcional. `encoders.local_model_dir()` deriva de `ENTREGA_DIR`; sin eso el contenedor intenta bajar 4,8 GB de HuggingFace y se cuelga sin error claro.
3. El primer `search()` carga los pesos de los encoders. Construye el `Retriever` **una vez** al arrancar y compártelo. Nunca dejes que la primera pregunta del usuario dispare la carga.

### Otros activos listos

| Qué | Dónde |
|---|---|
| NER de consulta sin modelos, microsegundos | `codefest/src/codefest/graph/ner.py:86` → `gazetteer_hits(texto)` |
| Consulta del grafo de conocimiento | `codefest/src/codefest/graph/query.py:25` → `GraphRetriever` |
| Vecindad de una entidad (lógica lista para extraer) | `codefest/scripts/15_grafo_html.py:40` → `subgrafo()`, `podar_aristas()` |
| Métricas NDCG@10 y F1@3 | `codefest/src/codefest/evaluate.py:39` |
| Fusión RRF genérica | `codefest/src/codefest/fusion.py:23` |

### Los datos

91.088 fragmentos en `codefest/entrega/base_vectorial/encoder_*/metadata.jsonl`, con 18 campos:
`doc_id, chunk_id, fuente, formato, fenomeno (1|2|3), posicion, num_tokens, texto, observatorio, titulo, idioma, seccion, n_palabras, fecha, url, ruta_relativa, doc_id_inventario, doc_id_secuencial`

Distribuciones: fenómeno F1 29.295 / F2 34.306 / F3 27.487. Idioma en 69.710 / es 19.561 / pt 1.108. Veinte observatorios.

Grafo: 33.178 nodos, 331.721 aristas, **100% con evidencia trazable a `chunk_id`**.

Embeddings crudos en `codefest/data/vectors/*.npy`, forma `(91088, d)`. Sirven para UMAP y clustering sin recomputar nada.

**Ojo con `fecha`**: está vacía en el 96,5% de los fragmentos. No construyas nada que asuma que existe sin verificar antes.

---

## Decisión medida: un solo encoder

`codefest/reports/ablacion.json` tiene la medición. `bge_m3` solo da known_item 0.85 y títulos 0.9167 en 8,1 s. La fusión de los tres da exactamente lo mismo en 18,2 s y con el triple de RAM.

**Por defecto se usa `slugs=["bge_m3"]`.** No es una simplificación por pereza: es costo-efectividad respaldada por medición propia, y la costo-efectividad es criterio de rúbrica.

---

## Stack

- **Backend**: Python, FastAPI, LangGraph. En `backend/`.
- **Frontend**: Next.js 15 App Router, Tailwind, shadcn/ui, componentes de 21st.dev, Three.js, Motion. En `frontend/`.
- Dos contenedores, orquestados por `docker-compose.yml`, desplegados en Coolify.

---

## Cómo escribir tools para los agentes

El docstring de una tool **es el prompt que lee el modelo**. Con modelos open source esto es la diferencia entre 2 y 6 iteraciones. Cada tool necesita cuatro cosas:

1. Cuándo usarla
2. **Cuándo NO usarla**
3. Restricciones de los argumentos
4. Un ejemplo de una línea

Y cuando una búsqueda no encuentra nada, devuelve un resultado **terminal**, no una lista vacía:

```python
{"resultados": [], "mensaje": "Sin resultados. NO reintentes reformulando; informa al usuario de que no hay cobertura."}
```

El contador de llamadas es lo que de verdad lo enforcea, porque el modelo a veces ignora el mensaje.

---

## Higiene de tokens

`Retriever.search()` devuelve `_row` y `_score` en cada fragmento. **Las tools devuelven al modelo solo** `doc_id, chunk_id, titulo, fenomeno, observatorio, idioma, texto`. Lo demás se queda en la capa de aplicación. Son cientos de tokens de ruido por turno.

---

## Si vas tarde

Orden de sacrificio ya decidido, para no discutirlo a las 03:00:

1. Agente verificador
2. Globo 3D en Three.js → 2D
3. Contenedor de grafo → Parquet y DuckDB
4. Modo profundo con 3 encoders
5. Memoria conversacional multi-turno → turno único
6. Coroplético → barras por departamento

**Nunca se sacrifica**: el `LICENSE`, las variables de entorno, el contrato del endpoint del jurado, el despliegue en Coolify, y la traza en la respuesta.
