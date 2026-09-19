# Cronograma y puntos de control

> Actualizado tras la especificación técnica.

Dos horas son absolutas: **08:00** y **12:30**. Y hay una tercera restricción que es fácil olvidar y más cara que las dos anteriores.

---

## La ventana de evaluación del Reto 1

**El Reto 1 se evalúa de 08:00 a 12:30 del sábado.** No es entregar y apagar: ADL consulta nuestro endpoint y le lanza ataques de prompt injection durante esas cuatro horas y media.

Eso significa que **el trabajo del Reto 2 ocurre mientras el Reto 1 está siendo evaluado en vivo**. Después de las 08:00:

- No se rompe `main`
- No se tumba el contenedor del agente
- El dashboard se despliega como recurso **separado**, nunca encima del agente

El Reto 2 se entrega a las 12:30 y no tiene hora de cierre fija: se extiende hasta que los expertos terminen de revisar a todos los equipos. El dashboard también debe seguir accesible.

---

## Antes de las 21:00

- **Repositorio privado creado** e invitados como colaboradores los evaluadores de ADL
- Juanes entra al Coolify que provee ADL y configura `agent.`, `frontagent.` y `dashboard.`
- Joseph baja la base SQL del Drive (`https://shorturl.at/YPQg0`) y reporta qué trae
- Esqueletos de `backend/` y `frontend/`
- Ortiz empieza `CATALOGO_PROBLEMAS.md`
- Juanes le pregunta a un mentor de ADL por la contradicción entre repositorio público y privado

---

## Bloques

| Hora | Qué |
|---|---|
| 21:00 | Contratos congelados, incluido el **catálogo de componentes de visualización**. Juanes mergea el esqueleto, todos rebasan. **Caché encendida.** |
| 21:00-22:30 | Juanes: hello-world desplegado en el Coolify de ADL. Jair: `orquestador` y `agente_corpus` con evidencia falsa, y `POST /chat` con el JSON exacto. Joseph: `buscar_corpus` real. Juanda: chat contra mocks. |
| **22:30 · CP1** | **`POST /chat` devuelve el JSON de la Sección 2.4 validado contra el esquema, desde el subdominio público.** Si no, todo lo demás da igual. |
| 22:30-00:30 | Jair: tools reales y tope de iteraciones. Joseph: ETL a Parquet y `expandir_entidad`. Juanda: traza y citas. Juanes: variables de entorno, contador y caché. |
| **00:30 · CP2** | **Una pregunta real devuelve respuesta real con citas, desplegado.** Si esto se pasa de la 01:30, se cortan extras y se entrega con los tres agentes mínimos. |
| 00:30-03:00 | Endurecimiento: prompt injection, topes, tono, las 15 preguntas golden. `agent_card.json` completo. |
| **03:00 · CP3** | **Las 15 golden pasan con costo medido por pregunta, y los ataques de inyección obvios están probados.** Si una pregunta supera 0,02 USD, se arregla el prompt, no el modelo. |
| 03:00-05:00 | **Dormir por turnos, dos a la vez. No negociable.** |
| 05:00-07:00 | Pulido: estados vacíos, errores, móvil, **README con instrucciones de despliegue y documento de arquitectura**, que valen el 20% de diseño. |
| **07:00** | **Freeze Reto 1.** Deploy, verificar desde el subdominio, tag `entrega-reto1`. |
| **07:55** | Entregar. No 07:59:59. |
| **08:00-12:30** | **Ventana de evaluación del Reto 1.** El endpoint del agente NO se toca. |
| 08:00-08:30 | Desayuno y retro de 15 minutos. |
| 08:30-11:00 | Sprint Reto 2, sobre recursos separados. Joseph: endpoints de analítica. Jair: `agente_visualizacion` y su prompt. Juanda: registro de componentes. |
| **10:00 · CP4** | **El agente activa componentes reales con datos reales.** Si no, se cortan tipos de componente, nunca el mecanismo dinámico. |
| **11:30** | **Freeze Reto 2.** Deploy, verificar, tag `entrega-reto2`. |
| **12:20** | Verificado desde un teléfono con datos móviles. Los tres subdominios. |
| 12:30 | Entrega 2. |
| 12:30-14:00 | Deck de 7 láminas, dos ensayos cronometrados, video de demo de respaldo. |
| **14:00** | Pitches, **orden aleatorio**. Listos a las 14:00, no a las 16:00. |

---

## Orden de sacrificio

Decidido de antemano para no discutirlo a las 03:00:

1. Agente `verificador`
2. Tipos de componente de visualización — **nunca el mecanismo dinámico**, que es el 55%
3. Grafo en memoria → Parquet y DuckDB
4. Modo profundo con 3 encoders
5. Memoria conversacional multi-turno → turno único, que además **sube** la nota en interacciones
6. `red_entidades` y `cuadrante` antes que `barras` y `linea_tiempo`

## Nunca se sacrifica

- El formato exacto de `POST /chat`
- `agent_card.json` con los modelos que de verdad se usan
- Los tres agentes mínimos
- La trazabilidad a `doc_id` y `chunk_id`
- Las variables de entorno
- **Que el endpoint siga arriba de 08:00 a 12:30**
- El README y el documento de arquitectura, que valen el 20% de diseño

---

## Regla de verificación

**Abrir los subdominios desde un teléfono con datos móviles, diez minutos antes de cada hito.** No desde un portátil en el wifi del campus.
