# Qué cambia ahora que llegó la especificación

**Léelo aunque ya hayas leído tu rol.** Los roles se actualizaron, pero esto explica por qué.

La especificación técnica está en `especificacion/ESPECIFICACION_TECNICA.md` y lo vinculante está resumido en `CONTRATO_JURADO.md`.

---

## 1. El repositorio tiene que ser PRIVADO · afecta a todos

La especificación lo dice dos veces: *"repositorio privado en GitHub (no público)"* y *"debe permanecer privado en todo momento —nunca público—"*. El acceso a ADL y a los evaluadores se da invitándolos como colaboradores.

**Contradice lo que dijeron en la apertura**, que fue repositorio público con licencia permisiva bajo pena de descalificación. La especificación escrita v1.0 manda, pero **hay que confirmarlo con un mentor de ADL en la primera ronda**.

Consecuencia práctica: el repo actual `Hackathon-ad-astra` es público y es el entregable de la Etapa 1, que sigue pendiente de retroalimentación. **No se puede volver privado sin romper esa entrega.** El código de la Etapa 2 va a un repositorio nuevo y privado.

El `LICENSE` MIT que añadimos deja de ser un requisito, pero no estorba. Se queda.

---

## 2. Coolify lo pone ADL · afecta sobre todo a Juanes

El correo previo sobre desplegar Coolify localmente era **preparación**, para familiarizarse. El despliegue real es sobre el espacio de trabajo que ADL asigna a cada equipo, con el panel en `coolify.<equipo>.codefest2026.augusta.avaldigitallabs.com`.

**Esto elimina el mayor riesgo del plan anterior**: ya no hay que correr Coolify, Docker, el Retriever de 5 GB y el dev server en la misma máquina. La máquina de nadie hospeda el despliegue.

Lo que sí hay que hacer: generar la llave SSH desde el panel de Coolify, registrarla en GitHub, crear el recurso como **Private Git Repository (with Deploy Key)**, dejar el build pack en **Dockerfile**, y configurar tres subdominios.

---

## 3. El Reto 2 no es un dashboard con filtros · afecta a Juanda y a Jair

Esto es el cambio más grande.

Teníamos planeado un tablero maestro-detalle con filtros globales y brushing-and-linking. **La especificación pide otra cosa**:

> *"el sistema no debe limitarse a mostrar todos los componentes a la vez en un dashboard estático. El agente generador de visualizaciones debe decidir, a partir de la instrucción en lenguaje natural del usuario, cuál o cuáles componentes activar y con qué datos o filtros poblarlos."*

Y el peso lo confirma: **ejecución dinámica vale 55%** de la nota del Reto 2. Propuesta de diseño 40%. Código 5%.

Es decir: el usuario escribe *"muéstrame cómo evolucionaron las alertas en Nariño"* y el agente decide que eso se responde con una línea de tiempo más un mapa, y los puebla. No es una pantalla con todo encendido y unos selectores.

Los filtros globales y el brushing-and-linking siguen siendo buenos, pero **dejan de ser el eje**. El eje es que el agente elija bien el componente.

---

## 4. Los tres agentes tienen roles definidos · afecta a Jair

La especificación no deja libertad:

1. Agente principal que recibe consultas y **redirecciona** a especializados
2. Agente que **responde preguntas** sobre el corpus
3. Agente **generador de visualizaciones**

Nuestro diseño de `guardia`, `planner`, `investigador`, `redactor`, `analista` y `narrador_visual` sigue siendo válido por dentro, pero **la ficha del agente tiene que leerse en los términos de la especificación**, porque el 20% de diseño se evalúa sobre esa ficha. Los nombres se realinean.

---

## 5. Seguridad vale 20% y lo habíamos subestimado · afecta a todos

**ADL ejecuta sus propios ataques de prompt injection contra nuestro endpoint desplegado.** El puntaje es la proporción de ataques resistidos. Es el 75% del bloque de seguridad, que a su vez es el 20% de la nota del Reto 1.

En el plan anterior esto era una línea sobre "límites de dominio". Ahora es un frente de trabajo con nombre propio, y el nodo `guardia` pasa de ser un ahorro de costo a ser una defensa calificada.

El 25% restante es análisis estático del código: buenas prácticas, manejo de errores, organización, ausencia de vulnerabilidades evidentes.

---

## 6. Ya sabemos los modelos y el presupuesto · afecta a Juanes y a Jair

Ocho modelos por Amazon Bedrock: `gpt-oss-20b`, `gpt-oss-120b`, `llama-3.3-70b-instruct`, `llama-4-scout`, `mixtral-8x7b-instruct`, `deepseek-r1-distill-llama-70b`, `qwen3-next-80b-a3b`, `gemma-3-27b`.

**Presupuesto: 100 USD.** Al superarlo la API Key deja de funcionar.

La eficiencia se normaliza **contra los otros equipos**, no contra un umbral. Ser eficiente no basta: hay que serlo más que los otros diecinueve.

---

## 7. El formato de respuesta está especificado al detalle · afecta a Jair

El endpoint devuelve un JSON con tres bloques: `respuesta`, `evaluacion` y `metadata`. Está literal en `CONTRATO_JURADO.md` sección 4.

Lo que hay que notar: `metadata.tokens.total` debe sumar **todos** los modelos, no solo el orquestador, y está marcado como requisito obligatorio. Y `latencia_ms` la calculamos nosotros de punta a punta aunque el framework no la dé.

Nuestro diseño de traza por spans sigue sirviendo: es de donde salen estos números. Solo cambia la forma de presentarlos.

---

## 8. Hay una base de datos SQL que no teníamos · afecta a Joseph

ADL dispone un Drive con el corpus completo, los archivos fuente originales y **una base de datos SQL específica para el Reto 2**: `https://shorturl.at/YPQg0`

**Hay que bajarla y mirarla antes de decidir el modelo de datos del tablero.** Puede hacer innecesario parte del ETL que teníamos planeado, o puede traer la señal temporal y geográfica que nos falta.

---

## 9. La ventana de evaluación del Reto 1 es de cuatro horas y media

No es entregar a las 08:00 y apagar. **El endpoint debe seguir accesible y respondiendo de 08:00 a 12:30**, mientras ADL lo evalúa y le lanza los ataques.

Eso significa que el trabajo del Reto 2 ocurre **mientras el Reto 1 está siendo evaluado en vivo**. No se puede romper `main` ni tumbar el contenedor del agente durante esa ventana.

Es probablemente la restricción operativa más fácil de olvidar y la más cara.

---

## Lo que NO cambia

- La arquitectura interna de agentes, con supervisor determinista y redactor sin herramientas
- Un solo encoder `bge_m3` por defecto, con la ablación medida como argumento
- Trabajar contra mocks en el frontend hasta tener backend real
- El reparto en cuatro frentes y el orden de merge
- Los puntos de control y el orden de sacrificio
- La trazabilidad a `doc_id` y `chunk_id`, que ahora además es requisito explícito
