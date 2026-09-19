# Frente A — Plataforma y despliegue · Juanes

> Actualizado tras la especificación técnica. Lee `AGENTS.md`, `CAMBIOS_TRAS_ESPECIFICACION.md` y `CONTRATO_JURADO.md`.

## Por qué te tocó este frente

Es el único que puede matar la entrega por sí solo. Y ahora además tienes dos requisitos que nadie más puede cubrir: el repositorio privado y los tres subdominios en el Coolify de ADL.

---

## Lo que cambió respecto de lo que leíste antes

1. **Coolify lo provee ADL**, no lo instalas tú. Hay un espacio de trabajo por equipo con panel en `coolify.<equipo>.codefest2026.augusta.avaldigitallabs.com`. El correo previo sobre instalación local era práctica. **Esto te quita de encima el mayor riesgo del plan anterior.**
2. **El repositorio debe ser PRIVADO.** No público. Es lo contrario de lo que dijeron en la apertura.
3. **Presupuesto: 100 USD.** Ya no es un placeholder.
4. **Ocho modelos concretos** vía Amazon Bedrock con una API Key.
5. **Tres subdominios** que configuras tú.

---

## Tu primera hora, en este orden

### 1. Crear el repositorio privado

El repo actual `Hackathon-ad-astra` es público y es el entregable de la Etapa 1, que sigue pendiente de retroalimentación. **No lo vuelvas privado**: rompería esa entrega.

Crea uno nuevo, privado, para la Etapa 2. Invita como colaboradores al usuario o correo de GitHub de ADL y de los evaluadores en cuanto te den los datos.

**Pregúntale a un mentor de ADL en la primera ronda** por qué la especificación dice privado y la apertura dijo público con licencia permisiva. Es una contradicción real y más vale resolverla temprano.

### 2. Los subdominios

| Servicio | Subdominio | Quién |
|---|---|---|
| Panel de Coolify | `coolify.<equipo>...` | **ADL. No tocar.** |
| Endpoint del agente | `agent.<equipo>...` | Tú |
| Frontend de chat | `frontagent.<equipo>...` | Tú |
| Dashboard | `dashboard.<equipo>...` | Tú |

En cada uno: **Port** igual al puerto interno del contenedor, y **www redirect** en **No redirect**.

### 3. El despliegue

1. Llave SSH **desde el panel de Coolify**: Root Team → Keys & Tokens → Private Keys → New Private Key → Generate ED25519
2. La pública se registra en GitHub: Settings → SSH and GPG keys → New SSH key
3. Recurso tipo **Applications → Private Git Repository (with Deploy Key)**
4. Repository configuration: URL del repo privado, Branch `main`, **Build pack = Dockerfile**
5. Variables de entorno en **Environment Variables**, marcables Buildtime, Runtime o ambos

`Dockerfile` autosuficiente, **healthcheck** recomendado, **un único puerto HTTP** por contenedor.

**Despliega un hello-world por el pipeline completo antes de que exista un solo agente.** Si no está verde a las 23:00, avisa y el equipo cambia de plan.

---

## Tus archivos

```
Dockerfile.agent
Dockerfile.frontend
docker-compose.yml                       ← solo para desarrollo local
.env.example
backend/app/main.py                      ← lifespan, /health, CORS
backend/app/deps.py                      ← singleton del Retriever
backend/app/contratos.py                 ← modelos Pydantic compartidos
backend/app/llm/cliente.py               ← el ÚNICO lugar donde se instancia un modelo
backend/app/observabilidad/contador.py
backend/app/observabilidad/presupuesto.py
backend/app/cache.py
backend/app/routers/jurado.py            ← POST /chat, el contrato con ADL
agent_card.json                          ← la ficha, en la raíz del repo
README.md                                ← instrucciones de despliegue
docs/ARQUITECTURA.md                     ← diseño y rationale, vale 20% del Reto 1
```

---

## Los contratos, a las 21:00

Todos los demás frentes están bloqueados hasta que exista `backend/app/contratos.py`. Es tu entregable más urgente después de Coolify.

Lo crítico son los modelos que producen el JSON de la Sección 2.4, porque ese es el contrato con el evaluador:

```python
class ToolCall(BaseModel):
    name: str
    input_parameters: dict
    output: str

class Evaluacion(BaseModel):
    input: str
    actual_output: str
    retrieval_context: list[str] = []
    tools_called: list[ToolCall] = []

class TokensAgente(BaseModel):
    agente: str
    modelo: str
    input: int
    output: int
    total: int

class Tokens(BaseModel):
    input: int
    output: int
    total: int

class MetadataRespuesta(BaseModel):
    num_interacciones: int
    agentes_invocados: list[str]
    tokens: Tokens
    tokens_por_agente: list[TokensAgente] = []
    latencia_ms: int
    estado: str = "ok"

class RespuestaJurado(BaseModel):
    respuesta: str
    evaluacion: Evaluacion
    metadata: MetadataRespuesta
```

`metadata.tokens.total` debe sumar **todos** los modelos, orquestador y sub-agentes. Está marcado como requisito obligatorio y es de las cosas que más fácil se implementan mal.

---

## La ficha del agente

`agent_card.json` en la raíz. Formato propio de ADL, **no es el estándar A2A**. Está literal en `CONTRATO_JURADO.md` sección 5.

Vale el 20% del Reto 1 junto con el documento de arquitectura. Dos cosas que se olvidan:

- El `endpoint` debe ser exactamente el subdominio `agent.` configurado.
- **Si Jair cambia un modelo a las 04:00, la ficha hay que actualizarla.** El modelo declarado es estructural y se usa para calcular nuestro costo por pregunta.

---

## El cliente LLM

`backend/app/llm/cliente.py::obtener_llm(rol)`. Ningún otro archivo instancia un modelo.

```
BEDROCK_API_KEY=
BEDROCK_BASE_URL=
MODELO_ORQUESTADOR=gpt-oss-20b
MODELO_CORPUS=gpt-oss-120b
MODELO_VISUALIZACION=gpt-oss-120b
MODELO_VERIFICADOR=llama-3.3-70b-instruct
PRESUPUESTO_TOTAL_USD=100
PRESUPUESTO_AHORRO_PCT=0.85
PRESUPUESTO_CORTE_PCT=0.95
MAX_USD_POR_TURNO=0.05
MAX_ITERACIONES_POR_TURNO=6
```

Los ocho modelos disponibles están en `CONTRATO_JURADO.md` sección 2.

---

## Presupuesto: ahora hay una cifra

**100 USD.** Al superarlos, la API Key deja de estar disponible. No es una advertencia, es un corte.

Además, la eficiencia se normaliza **contra los otros diecinueve equipos**, no contra un umbral. Ser eficiente no basta: hay que serlo más que ellos.

| Umbral | Acción |
|---|---|
| Por turno | Al exceder `MAX_USD_POR_TURNO` no lanza excepción: corta y responde con lo que haya |
| 70% (70 USD) | Warning ruidoso, chip ámbar en la interfaz |
| 85% | Modo ahorro: apaga verificador, baja `n_fragments`, modelo barato en todo |
| 95% | Solo caché; en miss, respuesta extractiva sin LLM |

**La caché desde las 21:00.** Cuatro personas machacando las mismas treinta preguntas durante dieciséis horas es de donde sale el gasto real.

---

## La ventana que es fácil olvidar

**El Reto 1 se evalúa de 08:00 a 12:30 del sábado.** No es entregar y apagar: ADL consulta el endpoint y le lanza ataques de prompt injection durante esas cuatro horas y media.

Eso significa que el trabajo del Reto 2 ocurre **mientras el Reto 1 está siendo evaluado en vivo**. Después de las 08:00:

- No se rompe `main`
- No se tumba el contenedor del agente
- Si hay que desplegar el dashboard, se despliega como recurso **separado**

Es la restricción operativa más cara de las que se olvidan.

---

## Checklist antes de cada hito

1. `docker build` en verde
2. `/health` responde **desde el subdominio público**, no en local
3. `POST /chat` devuelve el JSON exacto de la Sección 2.4, validado contra el esquema
4. `agent_card.json` actualizado con los modelos que de verdad se están usando
5. La URL abre **desde un teléfono con datos móviles**
6. README con instrucciones de despliegue y documento de arquitectura en el repo
