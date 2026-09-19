# Contrato vinculante con el evaluador

Todo lo de este archivo sale de `especificacion/ESPECIFICACION_TECNICA.md` v1.0. **Si algo de nuestro código contradice este archivo, gana este archivo.** No lo modifiques sin releer la especificación.

---

## 1. El repositorio debe ser PRIVADO

> *"el código fuente de la solución debe ser entregado a través de un repositorio **privado** en GitHub (no público)"* — Sección 1.4
>
> *"El repositorio del equipo debe permanecer **privado** en todo momento —nunca público—"* — Anexo A.2

El acceso se da invitando como **colaboradores** al usuario o correo de GitHub de ADL y de los evaluadores designados.

Esto **contradice lo que se dijo verbalmente en la apertura** (repositorio público con licencia permisiva, bajo pena de descalificación). La especificación escrita es v1.0 y lo dice dos veces, así que manda ella. **Confirmar con un mentor de ADL en la primera ronda.**

El repositorio debe contener además:
- `README.md` detallado con instrucciones de despliegue
- Documento de arquitectura con el diseño del sistema **y su rationale**
- Instrucciones de uso del sistema

---

## 2. Los ocho modelos disponibles

Vía **Amazon Bedrock**, con una API Key por equipo. Solo estos:

| Modelo | Proveedor |
|---|---|
| `gpt-oss-20b` | openai |
| `gpt-oss-120b` | openai |
| `llama-3.3-70b-instruct` | meta |
| `llama-4-scout` | meta |
| `mixtral-8x7b-instruct` | mistral |
| `deepseek-r1-distill-llama-70b` | deepseek |
| `qwen3-next-80b-a3b` | qwen |
| `gemma-3-27b` | google |

**Presupuesto: 100 USD por equipo.** Al superarlo, la API Key **deja de estar disponible**. No es una advertencia, es un corte.

---

## 3. Los subdominios

Sobre el dominio que ADL asigna el día del evento:

| Servicio | Subdominio | Quién lo configura |
|---|---|---|
| Panel de Coolify | `coolify.<equipo>.codefest2026.augusta.avaldigitallabs.com` | **ADL. No tocar.** |
| Endpoint del agente (Reto 1) | `agent.<equipo>...` | Nosotros |
| Frontend de chat (Reto 1) | `frontagent.<equipo>...` | Nosotros |
| Dashboard (Reto 2) | `dashboard.<equipo>...` | Nosotros |

En cada dominio: verificar que **Port** coincida con el puerto interno del contenedor, y dejar **www redirect** en **No redirect**.

**El endpoint declarado en la ficha del agente debe ser exactamente el subdominio `agent.`**, o no pueden evaluarnos sin ambigüedad.

---

## 4. Formato de respuesta del endpoint

Esto es literal. Cada consulta al endpoint responde con este JSON:

```json
{
  "respuesta": "texto en lenguaje natural para el usuario",
  "evaluacion": {
    "input": "la pregunta original recibida",
    "actual_output": "el mismo contenido de respuesta",
    "retrieval_context": [
      "fragmento recuperado 1",
      "fragmento recuperado 2"
    ],
    "tools_called": [
      {
        "name": "buscar_corpus",
        "input_parameters": {"query": "..."},
        "output": "..."
      }
    ]
  },
  "metadata": {
    "num_interacciones": 2,
    "agentes_invocados": ["orquestador", "agente_corpus"],
    "tokens": {"input": 2130, "output": 410, "total": 2540},
    "tokens_por_agente": [
      {"agente": "orquestador", "modelo": "gpt-oss-120b", "input": 1420, "output": 180, "total": 1600},
      {"agente": "agente_corpus", "modelo": "llama-3.3-70b-instruct", "input": 710, "output": 230, "total": 940}
    ],
    "latencia_ms": 2340,
    "estado": "ok"
  }
}
```

**Reglas que se evalúan:**

- `evaluacion.actual_output` repite `respuesta`. Es el campo que consumen las métricas de calidad.
- `retrieval_context` es una **lista de strings**, los fragmentos usados. Obligatorio si hubo recuperación.
- `tools_called` es obligatorio si se llamó alguna tool.
- `metadata.tokens.total` debe reflejar **todos** los modelos, orquestador y sub-agentes. No solo el orquestador. Está marcado como requisito obligatorio.
- `metadata.num_interacciones` es el número de llamadas a modelos.
- `metadata.latencia_ms` lo calculamos nosotros de punta a punta, aunque el framework no lo dé.
- `metadata.estado`: `ok` o un código de error.

**`tokens_por_agente` es opcional pero recomendado**, porque permite un cálculo de costo más preciso. Lo incluimos.

---

## 5. La ficha del agente (agent card)

**No sigue el estándar A2A.** Es formato propio de ADL. Se entrega junto con el despliegue.

```json
{
  "agente": {
    "nombre": "...",
    "descripcion": "...",
    "version": "1.0.0",
    "endpoint": "https://agent.<equipo>.codefest2026.augusta.avaldigitallabs.com/chat",
    "input_modes": ["text/plain"],
    "output_modes": ["application/json"]
  },
  "orquestador": {
    "nombre": "...",
    "descripcion": "...",
    "modelo": "gpt-oss-120b",
    "proveedor": "openai",
    "tools": [
      {"name": "...", "descripcion": "...", "input_parameters": {"query": "string"}}
    ]
  },
  "subagentes": [
    {
      "id": "...",
      "nombre": "...",
      "descripcion": "...",
      "modelo": "...",
      "proveedor": "...",
      "activado_por": "orquestador",
      "ejemplos_de_activacion": ["..."],
      "tools": [{"name": "...", "descripcion": "...", "input_parameters": {}}]
    }
  ]
}
```

El modelo declarado por agente es **estructural y fijo**: no se repite en cada respuesta y se usa para calcular el costo por pregunta. **Si cambiamos de modelo a las 04:00, hay que actualizar la ficha.**

---

## 6. Los tres agentes mínimos, con roles definidos

La especificación no deja libertad en esto (Sección 1.2):

1. **Agente principal** que recibe las consultas del usuario y **redirecciona** la tarea a agentes especializados.
2. **Agente que responde preguntas** en lenguaje natural sobre el corpus.
3. **Agente generador de visualizaciones** con base en las instrucciones del usuario.

Agentes adicionales dan puntos **solo si su funcionalidad contribuye al análisis aumentado de los tres fenómenos**. No suma agregar agentes decorativos.

---

## 7. El Reto 2 NO es un dashboard estático

Esto es lo que más cambia respecto de lo que teníamos planeado. Sección 3.3:

> *"el sistema **no debe limitarse a mostrar todos los componentes a la vez** en un dashboard estático. El agente generador de visualizaciones debe decidir, a partir de la instrucción en lenguaje natural del usuario, **cuál o cuáles componentes activar** y con qué datos o filtros poblarlos."*

Y el peso lo confirma: **Ejecución dinámica vale 55%** de la nota del Reto 2.

Lo que se exige:

1. **Propuesta de diseño por fenómeno**: decidir qué preguntas analíticas tiene sentido responder para cada fenómeno y qué componentes las responden. **No hay catálogo obligatorio.** Hay que justificarlo en el documento de arquitectura.
2. **Uso dinámico**: el agente elige qué componente activar ante cada instrucción en lenguaje natural.
3. **Trazabilidad**: todo dato mostrado debe rastrearse hasta su `doc_id` y `chunk_id`.

**Prohibido**: datos simulados o inventados en la versión desplegada para evaluación.

**Prohibido también** (Anexo B.2.5): presentar un puntaje, índice o nivel de riesgo inventado, tipo "score de amenaza" calculado ad hoc, como si fuera una medición objetiva. Conteos, frecuencias y agregaciones sí son medibles y sí se pueden mostrar.

---

## 8. Cómo nos califican

### Reto 1

```
puntaje = 0,40·calidad + 0,20·eficiencia + 0,20·seguridad + 0,20·diseño
```

| Bloque | Detalle |
|---|---|
| **Calidad 40%** | Answer Relevancy 30%, Faithfulness 30%, Toxicity 15%, **Tono 25%** |
| **Eficiencia 20%** | Tokens 40%, interacciones 30%, latencia 30%. **Normalizado contra los otros equipos**, no contra un umbral |
| **Seguridad 20%** | **Prompt injection 75%**, análisis estático de código 25% |
| **Diseño 20%** | Arquitectura multiagente, evaluada sobre la ficha y el documento de arquitectura |

**Seguridad vale 20% y ADL ejecuta sus propios ataques de prompt injection contra nuestro endpoint.** El puntaje es la proporción de ataques resistidos sin comprometer reglas ni exponer información no autorizada.

Eficiencia es relativa: no basta con ser eficiente, hay que serlo **más que los otros diecinueve equipos**.

### Reto 2

| Bloque | Peso |
|---|---|
| Propuesta de diseño por fenómeno | 40% |
| **Ejecución dinámica** | **55%** |
| Calidad interna del código | 5% |

Los expertos interactúan directamente con el dashboard y **formulan sus propias preguntas** en lenguaje natural.

### Pitch

Ocho aspectos: presentación del problema, arquitectura y metodología, resultados clave, demostración, reflexión sobre desafíos, aplicabilidad a cada fenómeno, identificación de patrones y hallazgos, y **verificación de fuentes**.

---

## 9. Ventanas de evaluación

- **Reto 1: sábado 19, de 08:00 a máximo 12:30.** El endpoint debe estar accesible y respondiendo **toda** esa ventana. No es entregar y apagar.
- **Reto 2: entrega el sábado 12:30**, sin hora de cierre fija; se extiende hasta que los expertos terminen de revisar a todos los equipos. El dashboard debe seguir accesible.

---

## 10. Despliegue en Coolify

**Coolify lo provee ADL**, un espacio de trabajo por equipo. No es una instalación local nuestra.

1. Llave SSH desde el panel: **Root Team → Keys & Tokens → Private Keys → New Private Key → Generate ED25519**
2. La pública se registra en GitHub: **Settings → SSH and GPG keys → New SSH key**
3. Recurso tipo **Applications → Private Git Repository (with Deploy Key)**
4. Repository configuration: URL del repo privado, Branch (`main`), **Build pack = Dockerfile**
5. Variables de entorno en **Environment Variables**, marcables como Buildtime, Runtime o ambos

El `Dockerfile` debe construir una imagen autosuficiente. Se recomienda un **healthcheck**. Cada contenedor expone **un único puerto o endpoint HTTP**.

---

## 11. Recurso que hay que descargar

ADL dispone un enlace de Google Drive con el corpus completo de la Etapa 1, el subconjunto de archivos fuente originales y **una base de datos SQL para el Reto 2**.

`https://shorturl.at/YPQg0`

**La base SQL no la teníamos contemplada.** Hay que bajarla y ver qué trae antes de decidir el modelo de datos del tablero.
