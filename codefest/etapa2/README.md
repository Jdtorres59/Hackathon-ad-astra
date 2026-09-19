# Etapa 2 — Reto final · Equipo AstroNova

Todo lo que el equipo necesita para las 24 horas del 18 y 19 de septiembre de 2026.

## Empieza por tu rol

| Persona | Frente | Documento |
|---|---|---|
| **Juanes** | Plataforma y despliegue | [`roles/ROL_A_JUANES.md`](roles/ROL_A_JUANES.md) |
| **Jair** | Agentes y LangGraph | [`roles/ROL_B_JAIR.md`](roles/ROL_B_JAIR.md) |
| **Joseph** | Herramientas y datos | [`roles/ROL_C_JOSEPH.md`](roles/ROL_C_JOSEPH.md) |
| **Juanda** | Frontend y diseño | [`roles/ROL_D_JUANDA.md`](roles/ROL_D_JUANDA.md) |
| **Cadete Ortiz** | Dominio, validación y pitch | [`roles/ROL_CADETE_ORTIZ.md`](roles/ROL_CADETE_ORTIZ.md) |

Antes que nada, lee [`../../AGENTS.md`](../../AGENTS.md) en la raíz del repo. Está escrito para que tu Claude lo lea y arranque con contexto.

## Referencia compartida

| Documento | Para qué |
|---|---|
| [`RETO.md`](RETO.md) | Qué hay que entregar, a qué hora, con qué reglas y qué premios |
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | Agentes, flujo, contrato de API, eventos SSE. **El contrato entre los cuatro frentes** |
| [`CRONOGRAMA.md`](CRONOGRAMA.md) | Horas, puntos de control y orden de sacrificio |
| [`GIT.md`](GIT.md) | Ramas, orden de merge y qué hacer si algo se rompe |
| [`DISENO.md`](DISENO.md) | Sistema visual: color, tipografía, movimiento, estructura de pantallas |
| [`CATALOGO_PROBLEMAS.md`](CATALOGO_PROBLEMAS.md) | Quince problemas candidatos para que Ortiz filtre |
| [`BRIEFING.md`](BRIEFING.md) | Las cinco conferencias previas, con citas textuales |
| [`apertura/TRANSCRIPT_APERTURA.md`](apertura/TRANSCRIPT_APERTURA.md) | Transcript completo del acto de apertura |

## Lo que hay que recordar aunque no leas nada más

1. **08:00 y 12:30 son absolutas.** Un milisegundo tarde es cero.
2. **Solo modelos open source** vía LiteLLM, con presupuesto en dinero y penalidad por excederlo.
3. **Se evalúa lo desplegado en Coolify**, no lo que corre en tu portátil.
4. **Evalúan la traza del agente por spans**, no solo la respuesta. Menos iteraciones puntúa mejor.
5. **Nunca credenciales en el código.** Es criterio calificable.
6. **`codefest/` no se toca.** Es el entregable de la Etapa 1 y se consume como librería.

## Pendiente

El **handbook técnico** con especificaciones, rúbrica y proceso de entrega. Cuando llegue, lo vinculante se transcribe a `docs/CONTRATO_JURADO.md` antes de escribir código que dependa de ello.
