# Frente D — Frontend y diseño · Juanda

> Lee `AGENTS.md` en la raíz y `codefest/etapa2/DISENO.md` antes de escribir componentes.

## Por qué este frente

Es donde está el diferenciador del pitch, y es el único frente que puede avanzar sin depender de que el backend esté vivo. Esa segunda parte importa más de lo que parece: durante las primeras cuatro horas el backend va a estar roto la mitad del tiempo.

## Tu regla de oro

**Trabaja contra mocks hasta las 00:00.** Un servidor SSE falso de sesenta líneas que reproduce un stream grabado. El frontend no puede quedar bloqueado nunca porque alguien rompió el backend.

---

## Tus archivos

```
frontend/app/(chat)/page.tsx
frontend/app/(tablero)/tablero/page.tsx
frontend/app/api/chat/route.ts            ← proxy del stream, deja BACKEND_URL server-only
frontend/components/chat/Conversacion.tsx
frontend/components/chat/Mensaje.tsx
frontend/components/chat/TrazaAgentes.tsx
frontend/components/chat/Citas.tsx
frontend/components/tablero/MapaCoropletico.tsx
frontend/components/tablero/GloboTresD.tsx
frontend/components/tablero/SerieTemporal.tsx
frontend/components/tablero/FiltrosGlobales.tsx
frontend/components/tablero/PanelDetalle.tsx
frontend/lib/sse.ts
frontend/lib/contratos.ts                 ← espejo de backend/app/contratos.py
frontend/lib/api.ts
frontend/mocks/servidor.ts
```

---

## El detalle que es criterio calificable

`frontend/app/api/chat/route.ts` hace de proxy del stream del backend. Eso deja `BACKEND_URL` como variable **server-only** y nunca como `NEXT_PUBLIC_`.

Las variables de entorno son criterio explícito de la rúbrica. Que una URL interna aparezca en el bundle del navegador es exactamente lo que van a mirar.

---

## Orden de trabajo

### 20:00-21:00 · Handbook

Lee el handbook con el resto del equipo. Lo que te toca extraer: si especifican algo de la interfaz, del tono de las respuestas, o del formato de entrega de capturas o video.

### 21:00-22:30 · Esqueleto y mocks

1. `create-next-app` con Tailwind y TypeScript, shadcn init, tokens de `DISENO.md` en `globals.css`
2. `frontend/mocks/servidor.ts`: un endpoint que emite los eventos SSE del contrato con retardos realistas
3. La pantalla de chat completa contra el mock: burbujas, stream de tokens, panel de evidencia, escalera de traza

A las 22:30 debería verse una conversación creíble aunque no exista un solo agente real. Eso es lo que le permite a Jair depurar el SSE contra algo que ya funciona.

### 22:30-00:30 · Conectar

Cuando Jair tenga el stream real, cambia la URL del mock por la del proxy. Si el contrato se respetó, no debería cambiar nada más.

Aquí aparece el bug clásico: si ves JSON del `planner` derramándose en la burbuja del chat, es que falta filtrar los tokens por nodo. Avísale a Jair, está documentado en su rol.

### 00:30-03:00 · Pulir el Reto 1

Estados vacíos, de carga y de error. Progreso de arranque real leyendo `/health`. Costo por turno al pie de cada respuesta. Responsive a 390 px. Citas que abren el panel de evidencia.

### 03:00-05:00 · Dormir

Turnos de dos personas. No negociable: el pitch es a las 14:00 y lo das tú.

### 08:30-11:00 · Tablero

Filtros globales primero, luego KPIs, luego la visualización principal, y al final el globo. **Ese orden importa**: si a las 10:00 el globo no está, entregas 2D y no pasa nada. Si a las 10:00 no están los filtros, no hay tablero.

El enlace bidireccional con el chat es requisito, no adorno: la caja de pregunta hereda los filtros activos y los manda en `filtros_tablero`.

---

## Hitos

| Hora | Qué |
|---|---|
| **22:30 CP1** | Un stream SSE llega al navegador y se ve una conversación |
| **00:30 CP2** | Conectado al backend real, con citas y traza reales |
| 07:00 | Freeze Reto 1: capturas para la documentación |
| **10:00 CP4** | El tablero pinta con datos reales y el chat lee los filtros |
| 11:30 | Freeze Reto 2 |

---

## Lo que también te toca, y no es código

**El pitch lo das tú con el cadete Ortiz.** Cinco minutos más tres de preguntas, llamado aleatorio desde las 14:00.

A las 12:30, cuando cierre el Reto 2:

1. Deck de **siete láminas máximo**
2. **Dos ensayos con cronómetro.** Cinco minutos se pasan volando y cortar a mitad de frase se ve mal
3. **Grabar un video de la demo funcionando**, como plan B si se cae la red. Fue recomendación explícita de la charla de Bantor
4. Preparar las tres preguntas predecibles: costo por consulta, por qué estos agentes, qué harían con otra semana

Ortiz explica por qué el problema importa. Tú muestras el producto.
