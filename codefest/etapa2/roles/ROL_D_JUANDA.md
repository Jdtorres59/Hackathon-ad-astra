# Frente D — Frontend y diseño · Juanda

> Actualizado tras la especificación técnica. Lee `AGENTS.md`, `CAMBIOS_TRAS_ESPECIFICACION.md`, `CONTRATO_JURADO.md`, `ARQUITECTURA.md` y `DISENO.md`.

## Lo que cambió, y es lo más grande del plan

**El Reto 2 no es un dashboard con filtros.** Es un tablero donde **un agente decide qué componentes mostrar** según lo que el usuario escribe en lenguaje natural.

> *"el sistema no debe limitarse a mostrar todos los componentes a la vez en un dashboard estático. El agente generador de visualizaciones debe decidir, a partir de la instrucción en lenguaje natural del usuario, cuál o cuáles componentes activar y con qué datos o filtros poblarlos."*

Y el peso lo confirma: **ejecución dinámica 55%**, propuesta de diseño 40%, código 5%.

El maestro-detalle con filtros globales y brushing-and-linking sigue siendo bueno, pero **deja de ser el eje**. El eje es que el usuario escriba *"cómo evolucionaron las alertas en Nariño"* y aparezca una línea de tiempo con un mapa, poblados, sin que nadie toque un selector.

**Además**: hay dos despliegues separados, `frontagent.` para el chat del Reto 1 y `dashboard.` para el Reto 2.

---

## El contrato que te define el trabajo

`agente_visualizacion` no dibuja. Devuelve una especificación y **tú la renderizas**:

```json
{
  "componentes": [
    {
      "tipo": "linea_tiempo",
      "titulo": "Alertas tempranas en Nariño, 2017-2026",
      "datos": {"endpoint": "/v1/analytics/alertas", "filtros": {"departamento": "Nariño"}},
      "trazabilidad": [{"doc_id": "F3-ALERTAS-032", "chunk_id": "..."}]
    }
  ],
  "justificacion": "..."
}
```

Tu trabajo es un **registro de componentes**: un mapa de `tipo` a componente de React. El agente elige la clave, tú garantizas que cada clave renderiza bien con cualquier dato válido.

**El catálogo se congela a las 21:00** con Jair y Joseph, porque es simultáneamente lo que el agente puede elegir, lo que tú sabes renderizar, y lo que hay que justificar por fenómeno en el documento de arquitectura que vale el 40%.

### Catálogo propuesto

| `tipo` | Qué es | Librería |
|---|---|---|
| `linea_tiempo` | Evolución temporal | Recharts |
| `mapa_coropletico` | Intensidad por territorio, con PCODEs | Leaflet o react-simple-maps |
| `mapa_puntos` | Ubicaciones concretas | Leaflet |
| `red_entidades` | Relaciones del grafo con evidencia | react-force-graph |
| `matriz_calor` | Cruce de dos categóricas | Recharts o SVG propio |
| `barras_comparacion` | Comparar pocas categorías | Recharts |
| `cuadrante` | Priorización por dos criterios | Recharts scatter |
| `panel_evidencia` | Fragmentos citados con doc_id | Propio |

El Anexo B advierte que **no hay que forzar un grafo o un mapa cuando la tarea es una comparación simple**. Por eso `barras_comparacion` tiene que verse tan bien como el mapa: si el agente elige barras y se ven pobres, parece que se equivocó.

---

## Tus archivos

```
frontend/app/(chat)/page.tsx                    ← frontagent.
frontend/app/(tablero)/page.tsx                 ← dashboard.
frontend/app/api/chat/route.ts                  ← proxy, deja BACKEND_URL server-only
frontend/components/chat/{Conversacion,Mensaje,Citas,TrazaAgentes}.tsx
frontend/components/viz/registro.ts             ← el mapa tipo → componente
frontend/components/viz/{LineaTiempo,MapaCoropletico,MapaPuntos,RedEntidades,
                          MatrizCalor,BarrasComparacion,Cuadrante,PanelEvidencia}.tsx
frontend/lib/{sse.ts,contratos.ts,api.ts}
frontend/mocks/servidor.ts
Dockerfile.frontend
```

Cada componente de `viz/` recibe la misma forma: `{titulo, datos, trazabilidad}`. Si todos cumplen esa interfaz, añadir un tipo nuevo es una línea en el registro.

---

## Trazabilidad: requisito, no adorno

> *"cualquier dato mostrado en un componente debe poder rastrearse hasta su `doc_id` y `chunk_id` de origen"*

Cada componente lleva un affordance para ver de dónde salieron sus datos. Lo más simple que funciona: un botón de "fuentes" que abre el `panel_evidencia` con los fragmentos.

Los expertos van a tirar de ese hilo. Es de las cosas que distinguen un tablero serio de una demo.

Y está **prohibido mostrar scores inventados**, tipo "índice de amenaza". Conteos y frecuencias sí.

---

## Orden de trabajo

### 21:00-22:30 · Esqueleto, mocks y chat

1. `create-next-app` con TypeScript y Tailwind, shadcn init, tokens de `DISENO.md`
2. `frontend/mocks/servidor.ts` con los eventos SSE **y** un spec de componentes de ejemplo
3. Pantalla de chat completa contra el mock

A las 22:30 debe verse una conversación creíble sin que exista un agente real.

### 22:30-00:30 · Conectar

Cambia la URL del mock por el proxy. Si el contrato se respetó, no cambia nada más.

Si ves JSON del orquestador derramándose en la burbuja, falta filtrar tokens por nodo. Avísale a Jair.

### 00:30-03:00 · Pulir el Reto 1

Estados vacíos, de carga y de error. Costo por turno al pie. Responsive a 390 px. Citas que abren el panel de evidencia. Progreso de arranque leyendo `/health`.

### 03:00-05:00 · Dormir

Turnos de dos. El pitch es a las 14:00 y lo das tú.

### 08:30-11:00 · El tablero

**Este es el orden, y no lo cambies:**

1. El **registro de componentes** y dos tipos funcionando de punta a punta con spec real del agente
2. `barras_comparacion` y `linea_tiempo`, que son los más probables y los más rápidos
3. `mapa_coropletico` con los PCODEs
4. `panel_evidencia`, que cierra la trazabilidad
5. `red_entidades` y `matriz_calor`
6. `cuadrante` y `mapa_puntos` si sobra

**Dos componentes que el agente activa bien valen más que ocho que no sabe cuándo usar.** El 55% es la ejecución dinámica, no la cantidad.

---

## Hitos

| Hora | Qué |
|---|---|
| 21:00 | Catálogo de componentes congelado con Jair y Joseph |
| **22:30** | Un stream SSE llega al navegador y se ve una conversación |
| **00:30** | Conectado al backend real, con citas y traza |
| 07:00 | Freeze Reto 1. Capturas para la documentación |
| **10:00** | El agente activa componentes reales con datos reales |
| 11:30 | Freeze Reto 2 |

Si a las 10:00 no hay ejecución dinámica funcionando, **corta tipos de componente, no el mecanismo**. Un tablero con tres componentes que el agente activa bien puntúa mucho más que ocho estáticos.

---

## Lo que también te toca

**El pitch lo das tú con el cadete Ortiz.** Cinco minutos más tres de preguntas, llamado aleatorio desde las 14:00.

La rúbrica del pitch tiene ocho aspectos: presentación del problema, arquitectura y metodología, resultados clave, demostración, reflexión sobre desafíos, aplicabilidad a cada fenómeno, identificación de patrones y hallazgos, y **verificación de fuentes**.

Ese último punto conecta directo con la trazabilidad: **enseña en vivo cómo un dato del tablero se rastrea hasta su fragmento**. Es el momento del pitch con mejor relación entre esfuerzo e impacto.

A las 12:30: deck de siete láminas, dos ensayos con cronómetro, y **grabar un video de la demo funcionando** como plan B si se cae la red.
