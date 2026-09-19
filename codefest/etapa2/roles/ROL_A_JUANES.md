# Frente A — Plataforma y despliegue · Juanes

> Lee primero `AGENTS.md` en la raíz del repo. Este documento asume que ya lo leíste.

## Por qué te tocó este frente

Es el único que puede matar la entrega por sí solo. Si el asistente es brillante pero no está desplegado en Coolify a las 08:00, la nota es cero. Además, durante las primeras tres horas los otros tres frentes dependen de que tu esqueleto exista, así que necesitas desbloquear sin esperar a nadie.

## Tu regla de oro

**Despliega un hello-world por el pipeline completo antes de que exista un solo agente.** Coolify, Dockerfile, volumen montado, URL pública que responde. Si eso no está verde a las 23:00, el equipo entero cambia de plan y tú lo anuncias.

---

## Tus archivos

Nadie más los toca.

```
LICENSE                                  ← ya está creado
docker-compose.yml
Dockerfile.backend
Dockerfile.frontend
.env.example
backend/app/main.py                      ← lifespan, CORS, /health, /ready
backend/app/deps.py                      ← singleton del Retriever
backend/app/contratos.py                 ← los modelos Pydantic compartidos
backend/app/llm/cliente.py               ← el ÚNICO lugar donde se instancia un LLM
backend/app/observabilidad/contador.py
backend/app/observabilidad/presupuesto.py
backend/app/cache.py
backend/app/routers/jurado.py            ← cuando llegue el handbook
docs/CONTRATO_JURADO.md
```

---

## Orden de trabajo

### 20:00-21:00 · La hora del handbook

**No escribas código de agentes.** Lee el handbook completo y transcribe a `docs/CONTRATO_JURADO.md` exactamente esto:

- Ruta y método del endpoint que consume el jurado
- Esquema literal de request y de response
- IDs de los modelos disponibles en LiteLLM
- Precio por millón de tokens de entrada y de salida de cada uno
- Cifra del presupuesto asignado
- Definición del tono que evalúan
- Formato y canal de entrega

Aval Digital Labs lo advirtió textualmente: si el endpoint no cumple la guía al pie de la letra, no pueden evaluar la solución. Esta hora es la de mayor apalancamiento de las 24.

En paralelo, instala Coolify. Es lo único que sí puedes adelantar durante esta hora.

### 21:00 · Congela los contratos

`backend/app/contratos.py` es tu entregable más urgente. Todos los demás frentes se bloquean hasta que exista. Mínimo:

```python
class QueryPlan(BaseModel):
    intencion: Literal["factual","comparativa","entidad","analitica","fuera_de_dominio"]
    fenomenos: list[Literal[1,2,3]]
    consulta_reescrita: str
    entidades: list[str]
    idioma_respuesta: Literal["es","en"]
    necesita_grafo: bool
    necesita_datos: bool

class Cita(BaseModel):
    doc_id: str
    chunk_id: str
    titulo: str
    fenomeno: int
    observatorio: str
    texto: str

class Evidencia(BaseModel):
    fragmentos: list[Cita]
    documentos: list[str]
    entidades: list[str]
    notas: str = ""

class Span(BaseModel):
    span_id: str
    padre: str | None
    agente: str
    ms: int
    tokens_in: int
    tokens_out: int
    costo_usd: float

class RespuestaChat(BaseModel):
    turno_id: str
    respuesta: str
    citas: list[Cita]
    graficos: list[dict] = []
    traza: list[Span]
    iteraciones: int
    costo_usd: float
```

Avisa en voz alta cuando esté mergeado. Jair y Joseph rebasan inmediatamente.

### 21:00-22:30 · Arranque del backend

El orden dentro de `lifespan` importa:

```python
import codefest  # ESTA LÍNEA VA PRIMERA, antes que faiss y torch

@asynccontextmanager
async def lifespan(app):
    app.state.listo = asyncio.Event()
    app.state.progreso = "arrancando"
    asyncio.create_task(asyncio.to_thread(_calentar, app))
    yield
```

`_calentar`, en este orden exacto:

1. `config.set_entrega_dir(os.environ["CODEFEST_ENTREGA_DIR"])` — obligatorio
2. `Retriever(base_dir=..., slugs=["bge_m3"], use_graph=False, device="cpu")` — unos 40 s
3. Un `search("prueba")` de calentamiento que fuerza los pesos — unos 15 s
4. `app.state.listo.set()`

`/ready` devuelve 503 hasta que `listo` esté puesto. `/health` expone `app.state.progreso` como texto legible, tipo `"cargando índice bge_m3 · 38 s"`, para que el frontend muestre algo real en vez de una pantalla congelada.

### El volumen, no la imagen

Los 6,4 GB de `codefest/entrega/` **no entran a la imagen ni a git**. Coolify monta el directorio del host:

```yaml
volumes:
  - /Users/<host>/Hackathon ad astra/codefest/entrega:/data/entrega:ro
environment:
  CODEFEST_ENTREGA_DIR: /data/entrega
```

La imagen queda en ~1,5 GB. El backend instala la librería de la Etapa 1 sin duplicar código:
`COPY codefest/src codefest/pyproject.toml` y luego `pip install -e /app/codefest`.

Límites de memoria: 5 GB la API, 1,5 GB el contenedor de grafo si existe, 1 GB Next.js.

---

## El cliente LLM: un solo punto de estrangulamiento

`backend/app/llm/cliente.py::obtener_llm(rol: str)`. **Ningún otro archivo instancia un modelo.** LiteLLM es compatible con OpenAI, así que cambiar de modelo es cambiar un string.

```
LITELLM_BASE_URL=
LITELLM_API_KEY=
MODELO_PLANNER=              # el más barato del catálogo
MODELO_INVESTIGADOR=
MODELO_REDACTOR=             # el mejor que aguante el presupuesto
MODELO_ANALISTA=
MODELO_NARRADOR=
MODELO_VERIFICADOR=          # DISTINTO del redactor
PRESUPUESTO_TOTAL_USD=
PRESUPUESTO_AHORRO_PCT=0.85
PRESUPUESTO_CORTE_PCT=0.95
MAX_USD_POR_TURNO=0.05
MAX_ITERACIONES_POR_TURNO=6
MAX_TOOL_CALLS_INVESTIGADOR=2
MAX_TOOL_CALLS_ANALISTA=3
```

---

## Presupuesto: frenos en escalera

`observabilidad/contador.py` es un `BaseCallbackHandler` que lee `response.usage` de cada llamada y escribe en SQLite: `(turno_id, span_id, agente, modelo, tokens_in, tokens_out, usd, ts)`.

| Umbral | Acción |
|---|---|
| Por turno | Al exceder `MAX_USD_POR_TURNO` **no lanza excepción**: corta al redactor con la evidencia que haya. Degradar le gana a reventar. |
| 70% | Warning en logs, chip ámbar en la UI |
| 85% | Modo ahorro: fuerza `modo=rapido`, apaga verificador y grafo, baja `n_fragments` de 10 a 5 |
| 95% | Sirve solo desde caché; en miss, respuesta extractiva determinista sin LLM |

El sistema nunca se apaga: **se vuelve extractivo**. Es un modo de fallo honesto y se dice en el pitch como demostración de costo-efectividad.

**Reconcilia tu contador con el dashboard de LiteLLM a las 00:00 y a las 04:00.** Si divergen más del 15%, cree al dashboard y recalibra tus constantes.

---

## La caché es el ahorro de verdad

`cache.db` en SQLite, clave `sha256(mensaje_normalizado + filtros + modo + version_prompt)`.

Durante 16 horas cuatro personas van a machacar las mismas treinta preguntas cientos de veces. **Enciéndela a las 21:00, no a las 05:00.** Es probablemente la decisión que más dinero salva de todo el plan.

Aparte, `MODO_GRABACION=1` guarda cada par de request y stream completo en `grabaciones/`, y `MODO_REPRODUCCION=1` los reproduce. Sirve como ahorro mientras Juanda trabaja el frontend, y como **plan B de demo** si se cae la red durante el pitch.

---

## Tu checklist antes de cada deadline

1. `docker compose build backend` en verde
2. `curl /health` y `/ready` responden **desde el contenedor desplegado**, no en local
3. La URL de Coolify abre **desde un teléfono con datos móviles**, no desde el wifi del campus
4. Tag creado: `entrega-reto1` a las 07:40, `entrega-reto2` a las 12:10
5. Rama `demo/respaldo` creada a las 07:30 y a las 12:00

---

## Si Coolify no levanta

Tienes hasta las 23:00. Si a esa hora no hay un hello-world desplegado, **lo anuncias y el equipo cae a `docker compose` más un túnel**. Se documenta en el README y se dice en el pitch. Perder dos horas peleando con Coolify a las 02:00 es cómo se pierde este hackathon.
