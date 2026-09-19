# Ramas y orden de merge

## Las ramas

| Rama | Dueño | Qué es |
|---|---|---|
| `main` | nadie commitea directo | Lo que despliega Coolify. **Desplegable en todo momento a partir de las 23:00.** Solo recibe merges. |
| `feat/plataforma` | Juanes | Docker, Coolify, `main.py`, contratos, cliente LLM, presupuesto, caché |
| `feat/agentes` | Jair | Agentes, grafo LangGraph, prompts, router de chat |
| `feat/herramientas` | Joseph | Tools, ETL, endpoints de analítica |
| `feat/frontend` | Juanda | Todo `frontend/` |
| `demo/respaldo` | — | Paracaídas. Se crea a las 07:30 y a las 12:00 desde el último estado bueno. **Nunca recibe merges.** |

---

## Orden de merge

Lo fuerza la cadena de dependencias: nadie puede avanzar sin el esqueleto, Jair no puede conectar agentes sin las firmas de las tools, y Juanda no puede conectar sin el SSE real.

```
21:00  Juanes  → esqueleto: contratos, main.py, deps, cliente LLM, Dockerfiles
                 TODOS rebasan inmediatamente

22:30  Joseph  → herramientas con firmas DEFINITIVAS
                 pueden devolver datos falsos; lo que importa es el contrato

23:30  Jair    → grafo de agentes contra las herramientas reales

00:30  Juanda  → frontend contra el backend real
```

Después de ese primer ciclo: **rebase sobre `main` cada 90 minutos**, y merge cuando tengas algo que funcione.

---

## Reglas

- **Merge a `main` solo con `docker compose build backend` en verde localmente.** Si rompes `main`, bloqueas a los cuatro.
- **Nada de teatro de revisión de PR.** Veinticuatro horas no lo permiten. En su lugar, pareja de cinco minutos en el momento del merge: quien mergea le muestra a otro qué cambió.
- **Los contratos son sagrados.** `backend/app/contratos.py` y `frontend/lib/contratos.ts` no se tocan sin anunciarlo en voz alta a todo el equipo. Son el único archivo que puede romper a los cuatro a la vez.
- `backend/app/main.py` es de Juanes. Si necesitas algo ahí, se lo pides.
- Cambios en `requirements.txt` o `package.json` pasan por Juanes, que es quien construye las imágenes.
- **`codefest/` no se toca.** Es el entregable de la Etapa 1 y sigue pendiente de retroalimentación. Se consume como librería con `pip install -e`.

---

## Tags

| Tag | Cuándo |
|---|---|
| `entrega-reto1` | 07:40 |
| `entrega-reto2` | 12:10 |

Se crean **antes** de la hora de entrega, no después. El tag marca exactamente lo que se entregó, que es lo que hay que poder reproducir si alguien pregunta.

---

## Commits

Mensajes en imperativo y en español, cortos. Nadie va a leer el historial esta noche, pero sí mañana cuando haya que explicar en el pitch qué se hizo.

```
Añadir tool buscar_corpus con filtro por fenómeno
Conectar el tablero a los filtros globales
Arreglar el derrame de tokens del planner en el chat
```

---

## Si algo se rompe a las 04:00

1. No arregles `main` a ciegas. `git log --oneline -10` primero.
2. Si el último merge rompió algo, `git revert` ese merge. Revertir es más rápido que depurar con sueño.
3. Si `main` está irrecuperable, `demo/respaldo` existe precisamente para eso.

---

## Al final

Lo que trabajemos nuevo (`backend/`, `frontend/`, `codefest/etapa2/`, `LICENSE`, `AGENTS.md`) se exporta al repositorio público que se entrega. **Con licencia permisiva**, que es criterio de descalificación si falta.
