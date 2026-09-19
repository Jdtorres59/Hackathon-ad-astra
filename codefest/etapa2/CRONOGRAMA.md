# Cronograma y puntos de control

Dos horas son absolutas: **08:00** y **12:30**. Un milisegundo tarde es cero, y lo dijeron textualmente.

---

## Antes de las 20:00

- `LICENSE` MIT en la raíz — hecho
- Esqueletos de `backend/` y `frontend/`, dependencias instaladas
- `docker compose build` una vez, para cachear capas
- Juanes empieza a instalar Coolify

---

## 20:00-21:00 · La hora del handbook

**Nadie escribe código de agentes.** Todos leen. Juanes transcribe lo vinculante a `docs/CONTRATO_JURADO.md`: ruta y esquema exactos del endpoint del jurado, IDs de modelo, precios por millón de tokens, cifra de presupuesto, definición de tono, formato de entrega.

Es la hora de mayor apalancamiento de las 24, y saltársela es cómo se pierden estos eventos. Aval Digital Labs lo advirtió: si el endpoint no cumple la guía al pie de la letra, no pueden evaluar la solución.

Ortiz, en paralelo: marca `CATALOGO_PROBLEMAS.md`.

**20:15** — ventana de intercambio de roles. Quien vea que su frente no le encaja lo dice ahora.
**20:30** — la asignación queda fija.

---

## Bloques

| Hora | Qué |
|---|---|
| 21:00 | Contratos congelados. Juanes mergea el esqueleto, todos rebasan. **Caché encendida.** |
| 21:00-22:30 | Juanes: Coolify verde con hello-world. Jair: `planner` y `redactor` con evidencia falsa, SSE de punta a punta. Joseph: `buscar_corpus` real. Juanda: chat contra mocks. |
| **22:30 · CP1** | **Un stream SSE llega al navegador.** Si no, Juanda sigue en mocks y Jair arregla el stream. |
| 22:30-00:30 | Jair: `investigador` y grafo real. Joseph: ETL a Parquet y `expandir_entidad`. Juanda: traza y citas. Juanes: backend real desplegado con el volumen montado. |
| **00:30 · CP2** | **Una pregunta real devuelve respuesta real con citas, en el contenedor desplegado.** El Reto 1 está técnicamente vivo. Si esto se pasa de la 01:30, se corta la rama de grafo y se entrega con 2 agentes. |
| 00:30-03:00 | Endurecimiento: guardia de presupuesto, topes, tono, las 15 preguntas golden, `/v1/chat/sync` para DeepEval. Juanda pule. |
| **03:00 · CP3** | **Las 15 golden pasan de punta a punta con costo medido.** Si alguna supera 0,02 USD, se arregla el prompt, no el modelo. |
| 03:00-05:00 | **Dormir por turnos, dos a la vez. No negociable.** |
| 05:00-07:00 | Pulido del Reto 1: estados vacíos, errores, móvil, grabación del plan B, README, documentación, capturas. |
| **07:00** | **Freeze Reto 1.** Deploy, verificar, tag `entrega-reto1`. Rama `demo/respaldo`. |
| **07:55** | **Enviar.** No 07:59:59. |
| 08:00 | Entrega 1. |
| 08:00-08:30 | Desayuno y retro de 15 minutos: qué queda realmente para el tablero. |
| 08:30-11:00 | Sprint Reto 2. Joseph: endpoints de analítica. Juanda: filtros, KPIs, mapa, globo. Jair: `analista` y `narrador_visual`. Enlace chat-tablero en los dos sentidos. |
| **10:00 · CP4** | **El tablero pinta con datos reales y el chat lee los filtros.** Si no, se corta Three.js y se entrega 2D. |
| **11:30** | **Freeze Reto 2.** Deploy, verificar, tag `entrega-reto2`. |
| **12:20** | Verificado desde un teléfono con datos móviles. |
| 12:30 | Entrega 2. |
| 12:30-14:00 | Deck de 7 láminas, dos ensayos cronometrados, video de demo de respaldo, preparar las tres preguntas predecibles. |
| **14:00** | Pitches, **orden aleatorio**. Hay que estar listos a las 14:00, no a las 16:00. |

---

## Orden de sacrificio

Decidido ahora para no discutirlo a las 03:00, cuando nadie va a estar en condiciones de decidir bien:

1. Agente `verificador`
2. Globo 3D en Three.js → 2D
3. Contenedor de grafo → Parquet y DuckDB, o eliminar `expandir_entidad`
4. Modo profundo con 3 encoders
5. Memoria conversacional multi-turno → turno único (esto además **sube** la nota en "menos iteraciones")
6. Coroplético → barras por departamento

## Nunca se sacrifica

`LICENSE`, variables de entorno, el contrato del endpoint del jurado, el despliegue en Coolify, y la traza en la respuesta.

---

## Regla de verificación antes de cada deadline

**Abrir la URL de Coolify desde un teléfono con datos móviles, diez minutos antes.** No desde un portátil en el wifi del campus, que puede estar resolviendo un DNS local viejo y mostrarte algo que el jurado no va a ver.
