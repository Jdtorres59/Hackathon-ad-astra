# Prompts de arranque

Cada uno copia **su** bloque y se lo pega a su Claude como primer mensaje, después de clonar el repo y de estar dentro de la carpeta.

Están escritos para una sesión fría: traen las restricciones que hacen falta para que Claude no haga algo tonto en los primeros diez minutos.

---

## Juanes — Frente A, plataforma y despliegue

```
Estoy en un hackathon de 24 horas de la Fuerza Aérea Colombiana con Uniandes que
empieza a las 20:00 de hoy. Soy responsable del frente de plataforma y despliegue.

Antes de proponer nada, lee estos dos archivos completos:
- AGENTS.md (raíz del repo)
- codefest/etapa2/roles/ROL_A_JUANES.md

Restricciones que no se negocian:
- NO toques codefest/src, codefest/scripts ni codefest/entrega. Es el entregable de
  otra etapa, se consume como librería con pip install -e.
- Nunca credenciales en el código. Todo por variables de entorno, es criterio calificable.
- Trabajo en la rama feat/plataforma.

Mi primera tarea, antes de las 21:00, en este orden:
1. Instalar Coolify localmente con Docker y dejarlo funcionando.
2. Crear el esqueleto de backend/ con FastAPI, y los Dockerfiles y docker-compose.yml.
3. Escribir backend/app/contratos.py con los modelos Pydantic que están especificados
   en mi rol. Los otros tres frentes están bloqueados hasta que eso exista, así que es
   lo más urgente después de Coolify.

Empieza leyendo los dos archivos y dime en qué orden concreto vamos a atacar esto y
qué necesitas de mí. No escribas código todavía.
```

---

## Jair — Frente B, agentes y LangGraph

```
Estoy en un hackathon de 24 horas de la Fuerza Aérea Colombiana con Uniandes que
empieza a las 20:00 de hoy. Soy responsable del frente de agentes y orquestación.

Antes de proponer nada, lee estos archivos completos:
- AGENTS.md (raíz del repo)
- codefest/etapa2/roles/ROL_B_JAIR.md
- codefest/etapa2/ARQUITECTURA.md

Restricciones que no se negocian:
- NO toques codefest/src, codefest/scripts ni codefest/entrega.
- Solo hay modelos open source vía un gateway LiteLLM. No hay Claude, GPT ni Gemini
  en runtime, así que los prompts y los docstrings tienen que ser explícitos.
- Tope duro de iteraciones en todo bucle de agente. El presupuesto se mide en dinero
  y hay penalidad por excederlo.
- Nunca instancies un LLM directamente: eso vive en backend/app/llm/cliente.py, que
  lo escribe Juanes.
- Trabajo en la rama feat/agentes.

Estoy bloqueado hasta que Juanes mergee backend/app/contratos.py hacia las 21:00.
Mientras tanto, lo útil es:
1. Dejar la estructura de carpetas de backend/app/agentes, grafo y prompts.
2. Escribir los prompts de planner y redactor como archivos .md, pensando en que los
   va a leer un modelo open source y no uno de frontera.
3. Dejar listo el esqueleto del SSE en routers/chat.py, con el filtro de tokens por
   nodo que está documentado en mi rol, porque ese bug me va a costar una hora si lo
   descubro a las 02:00.

Empieza leyendo los tres archivos y dime cómo vas a estructurar el grafo de LangGraph.
No escribas código todavía.
```

---

## Joseph — Frente C, herramientas y datos

```
Estoy en un hackathon de 24 horas de la Fuerza Aérea Colombiana con Uniandes que
empieza a las 20:00 de hoy. Soy responsable del frente de herramientas y datos.

Antes de proponer nada, lee estos archivos completos:
- AGENTS.md (raíz del repo)
- codefest/etapa2/roles/ROL_C_JOSEPH.md

Restricciones que no se negocian:
- NO toques codefest/src, codefest/scripts ni codefest/entrega. Todo lo que parezca
  que hay que escribir de búsqueda semántica, chunking o consulta de grafo YA EXISTE
  ahí. Búscalo antes de escribir nada.
- Las tools devuelven al modelo solo doc_id, chunk_id, titulo, fenomeno, observatorio,
  idioma y texto. Nada de _row ni _score: son cientos de tokens de ruido por turno.
- Trabajo en la rama feat/herramientas.

Mi primera tarea, antes de las 22:30, es tener las firmas DEFINITIVAS de las tools
mergeadas aunque devuelvan datos falsos, porque Jair está bloqueado hasta entonces.

Empieza por verificar que el motor de recuperación arranca de verdad en mi máquina.
El patrón exacto está en AGENTS.md y tiene tres trampas que cuestan horas si se
ignoran. Haz esa prueba primero y dime cuánto tarda en cargar y cuánta RAM consume,
porque eso determina decisiones del resto del equipo.

Después, dime cómo vas a estructurar las tools. No escribas la implementación todavía.
```

---

## Juanda — Frente D, frontend y diseño

```
Estoy en un hackathon de 24 horas de la Fuerza Aérea Colombiana con Uniandes que
empieza a las 20:00 de hoy. Soy responsable del frontend y del diseño, y además
doy el pitch final.

Antes de proponer nada, lee estos archivos completos:
- AGENTS.md (raíz del repo)
- codefest/etapa2/roles/ROL_D_JUANDA.md
- codefest/etapa2/DISENO.md
- codefest/etapa2/ARQUITECTURA.md

Restricciones que no se negocian:
- NO toques codefest/src, codefest/scripts ni codefest/entrega.
- BACKEND_URL es server-only, nunca NEXT_PUBLIC_. Las variables de entorno son
  criterio calificable y el proxy en app/api/chat/route.ts existe para eso.
- Trabajo en la rama feat/frontend.
- El frontend trabaja contra mocks hasta las 00:00. No puedo quedar bloqueado nunca
  porque el backend esté caído.

Mi primera tarea, antes de las 22:30:
1. create-next-app con TypeScript y Tailwind, shadcn init, y los tokens de DISENO.md
   en globals.css.
2. frontend/mocks/servidor.ts: un servidor SSE falso que emita los eventos del
   contrato con retardos realistas.
3. La pantalla de chat completa contra ese mock: burbujas, stream de tokens, panel de
   evidencia con citas, y la escalera de traza de agentes.

Empieza leyendo los cuatro archivos y propón la estructura de componentes. Quiero que
la traza de agentes se vea bien desde el principio, porque es lo que le demuestra al
jurado que hay una arquitectura multiagente de verdad y no un solo modelo.
```

---

## Cadete Ortiz — dominio y validación

No necesitas un agente para arrancar, pero si quieres uno que te ayude a ordenar ideas:

```
Estoy en un hackathon de la Fuerza Aérea Colombiana con Uniandes. Soy cadete de la
Escuela Militar de Aviación y mi rol en el equipo no es programar, es decidir qué
problemas le importan de verdad a la Fuerza y validar que lo que construyan sirva.

Lee estos dos archivos:
- codefest/etapa2/roles/ROL_CADETE_ORTIZ.md
- codefest/etapa2/CATALOGO_PROBLEMAS.md

Ayúdame a trabajar el catálogo. Hazme preguntas sobre cada problema para que yo pueda
decidir si es crítico, útil o no aplica, en vez de proponerme tú las respuestas. Lo
valioso aquí es mi criterio, no el tuyo.

Después ayúdame a redactar quince preguntas de prueba, cinco por cada fenómeno, que un
analista de inteligencia haría de verdad. No preguntas diseñadas para que el sistema
quede bien.
```

---

## Una cosa que aplica a los cuatro

Si tu Claude empieza a reimplementar algo que suena a búsqueda semántica, fragmentación
de documentos o consulta de grafo, **párale**. Todo eso existe y está probado en
`codefest/src/codefest/`. Reescribirlo es la forma más rápida de perder tres horas.
