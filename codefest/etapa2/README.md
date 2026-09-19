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

Cada uno tiene además un prompt de arranque listo para pegarle a su Claude en [`roles/PROMPTS_INICIALES.md`](roles/PROMPTS_INICIALES.md).

Antes que nada, lee [`../../AGENTS.md`](../../AGENTS.md) en la raíz del repo. Está escrito para que tu Claude lo lea y arranque con contexto.

## Leer primero, en este orden

1. [`CAMBIOS_TRAS_ESPECIFICACION.md`](CAMBIOS_TRAS_ESPECIFICACION.md) — **qué cambió cuando llegó la especificación técnica**. Léelo aunque ya hayas leído tu rol.
2. [`CONTRATO_JURADO.md`](CONTRATO_JURADO.md) — **lo vinculante**: formato de respuesta, ficha del agente, subdominios, modelos, presupuesto y cómo nos califican. Si el código contradice este archivo, gana este archivo.
3. [`especificacion/ESPECIFICACION_TECNICA.md`](especificacion/ESPECIFICACION_TECNICA.md) — la fuente original, con los dos anexos.

## Referencia compartida

| Documento | Para qué |
|---|---|
| [`RETO.md`](RETO.md) | Lo que se dijo en la apertura: horas, premios, código de honor |
| [`ARQUITECTURA.md`](ARQUITECTURA.md) | Agentes, flujo, contrato de API, eventos SSE. **El contrato entre los cuatro frentes** |
| [`CRONOGRAMA.md`](CRONOGRAMA.md) | Horas, puntos de control y orden de sacrificio |
| [`GIT.md`](GIT.md) | Ramas, orden de merge y qué hacer si algo se rompe |
| [`DISENO.md`](DISENO.md) | Sistema visual: color, tipografía, movimiento, estructura de pantallas |
| [`CATALOGO_PROBLEMAS.md`](CATALOGO_PROBLEMAS.md) | Quince problemas candidatos para que Ortiz filtre |
| [`BRIEFING.md`](BRIEFING.md) | Las cinco conferencias previas, con citas textuales |
| [`apertura/TRANSCRIPT_APERTURA.md`](apertura/TRANSCRIPT_APERTURA.md) | Transcript completo del acto de apertura |

## Lo que hay que recordar aunque no leas nada más

1. **08:00 y 12:30 son absolutas.** Un milisegundo tarde es cero.
2. **Ocho modelos open source** vía Amazon Bedrock, con **100 USD** de presupuesto. Al superarlo, la API Key deja de funcionar.
3. **Se evalúa lo desplegado en Coolify**, no lo que corre en tu portátil.
4. **El Reto 2 no es un dashboard con filtros**: un agente decide qué componentes activar. Eso vale el 55%.
5. **Seguridad vale 20%** y ADL lanza ataques de prompt injection contra nuestro endpoint.
6. **El repositorio del código es PRIVADO**, y el endpoint sigue evaluándose hasta las 12:30.
7. **Nunca credenciales en el código.** Es criterio calificable.
8. **`codefest/` no se toca.** Es el entregable de la Etapa 1 y se consume como librería.

## Pendiente

- **Confirmar con un mentor de ADL** por qué la especificación exige repositorio privado y la apertura dijo público con licencia permisiva.
- **Los subdominios y la API Key**, que ADL entrega el día del reto.
- **Bajar la base SQL** del Drive de ADL: `https://shorturl.at/YPQg0`
