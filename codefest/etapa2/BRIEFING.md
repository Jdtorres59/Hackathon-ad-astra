# Ciclo de conferencias previo al reto final — CODEFEST AD ASTRA 2026

Extraído de los cinco streamings del 7 al 11 de septiembre de 2026, canal
*Ingeniería de Sistemas y Computación - Uniandes*. El equipo no asistió en vivo;
esto se reconstruyó desde los subtítulos automáticos.

Los transcripts completos están en `transcripts/`. Todo lo que aparece entre
comillas en este documento es cita textual verificable ahí.

| Día | Video | Duración | Contenido |
|---|---|---|---|
| 1 | `Sm8laSap9Z0` | 1h 19m | TC Alexandra Zavala (FAC) + **Aval Digital Labs: arquitectura de la infraestructura** |
| 2 | `1hCMyJaTd7E` | 2h 01m | Blend 360: sistemas multiagente. Google: ADK |
| 3 | `HA5B18F46VE` | 2h 01m | Rubén Manrique: LangChain y LangGraph. Tito Neira: estrategia de datos |
| 4 | `jf2-G--7ouc` | 0h 59m | Camilo Escobar: visualización georreferenciada y longitudinal |
| 5 | `XicYEgF417o` | 2h 46m | Telespazio: geointeligencia. Bantor: AI harness. Conecto: agentic RAG |

**Nota sobre el Día 1**: el enlace que circuló originalmente (`R9PdFhjW8yo`) está
caído. El video vive en `Sm8laSap9Z0`. Es el más importante de los cinco.

---

## 1. Reglas con consecuencia

Todo esto es del Día 5 salvo donde se indique. Lo que aparece aquí tiene
descalificación o penalidad asociada.

- **Repositorio público de GitHub con licencia open source permisiva.** Textual:
  *"Los repositorios con licencias restrictivas, o sea, que no se pueda acceder,
  serán descalificados."* Código abierto a perpetuidad, modificable, preservando
  atribución. Las librerías de terceros deben tener licencias compatibles.
- **Los cuatro integrantes deben asistir presencialmente.** La inasistencia
  injustificada de uno o más puede implicar descalificación, a criterio del comité.
- **Mínimo dos portátiles operativos por equipo.**
- **Asistencia obligatoria al ciclo de conferencias** (Día 1). Los organizadores
  reconocieron explícitamente que muchos equipos las ven en diferido.
- Prohibido: interferir con otros equipos, suplantar identidades, código malicioso,
  información falsa o engañosa, violar propiedad intelectual de terceros, contenido
  que incite a violencia o discriminación, licencias incompatibles con el requisito
  de código abierto, y contenido publicitario o político ajeno a los organizadores.

### Entregables

1. Presentación con diapositivas **o** demostración en vivo.
2. Repositorio público con el código fuente bajo licencia permisiva.
3. Documentación técnica, que puede ir dentro del repositorio.

### Formato del pitch

**5 minutos de presentación + 3 minutos de preguntas.** Ocho minutos en total.

---

## 2. Logística

- **Viernes 18 de septiembre, 5:00 PM**, campus Uniandes, **edificio Mario Laserna**.
- **Llegar a las 4:00 PM o antes.** Repetido en los días 4 y 5. Registro más entrega
  de kit de bienvenida; 20 equipos de 4 personas, calculan 10 a 15 minutos solo en
  eso. Los espacios están abiertos desde las 4. Hay stands de las empresas aliadas.
- **El reto y el handbook técnico se revelan al inicio de la jornada.** No antes.
- **Jornada continua de 24 horas.** Premiación el 19.
- 20 equipos clasificados de 11 universidades y 7 ciudades, sobre 110 inscritos.
  Hay 3 equipos de backup notificados.

**Sobre dormir**: ninguno de los cinco videos menciona zonas de descanso,
alimentación, refrigerios ni si se puede salir y volver a entrar al campus. La
jornada continua de 24 horas desde las 5 PM del viernes implica pasar la noche en
el campus. Lo demás probablemente está en el handbook o en el kit de bienvenida.

---

## 3. Infraestructura del reto

Día 1, Aval Digital Labs (Steven Jerena, Diego Alejandro Buitrago). **Esta es la
sección que más cambia las decisiones de diseño.**

### Solo modelos open source

> *"los modelos que fueron definidos para el reto son los modelos open source...
> por algunas condiciones de los entornos militares es de gran importancia que los
> modelos a utilizar no sean los comerciales"*

Se sirven desde **Amazon Bedrock**, pero la restricción es dura. Nada de Claude,
GPT ni Gemini. Los IDs concretos van en la guía de usuario que entregan el día del
reto.

**Implicación**: todo lo que dijeron sobre docstrings, límites de iteración y
especificaciones explícitas deja de ser buena práctica y pasa a ser condición de
que la solución funcione.

### LiteLLM como gateway, presupuesto en dinero

- Cada equipo recibe **endpoint, API key propia e IDs de modelo**. Un solo formato
  de invocación para todos, así que cambiar de modelo es cambiar un string.
- **El presupuesto se asigna en dinero, no en tokens**, y se calcula sobre el costo
  del modelo fundacional. Cuando se agota, el agente deja de responder.
- Conseguir tokens extra *"puede llegar a tener algún tipo de penalidad dentro
  del reto"*.
- Hay **dashboard de consumo casi en tiempo real** por API key.
- En la guía dan el costo por millón de tokens de cada modelo.

### Coolify para despliegue

Este año **no hay ambientes cloud provistos**, a diferencia de ediciones pasadas.
Se desarrolla en las máquinas propias y se despliega en Coolify.

- Se genera una llave SSH desde Coolify y se carga en el repositorio de GitHub.
  Coolify apunta a una rama, lee el Dockerfile y despliega.
- Catálogo de servicios listo para usar: Postgres, Redis, MariaDB, **bases de datos
  vectoriales**, front, back.
- Cada aplicación desplegada recibe una URL.
- Logs de despliegue y de ejecución. Existe un **MCP de Coolify** para depurar con
  un agente.
- **Las variables de entorno son calificables.** Textual: *"la calidad del código es
  muy importante y este tema de las variables de entorno pues es un apoyo grande"*.
  No quemar credenciales en el código.
- **Los jurados evalúan la solución desplegada en Coolify, no la local.**

---

## 4. Cómo evalúan

Framework: **DeepEval**. No evalúan solo la respuesta final.

- Evalúan **la traza del agente por spans**, es decir cada paso de la ejecución.
- Cada pregunta tiene **una ruta ideal específica** que el agente debería recorrer.
- Miden además toxicidad, comprensibilidad y **tono**. El tono se define en la guía
  de usuario.
- **Menos iteraciones es mejor**: *"la idea es que haya la menor iteración cuando
  haya un input requerido por el usuario"*.
- Después hay una **evaluación humana**.
- **La costo-efectividad es criterio explícito**: *"todo lo podemos hacer con el
  modelo más potente, pero eso ya con complicaciones a nivel de consumo. El saber
  cómo crear una solución que sea costo-efectiva también es un criterio importante
  de evaluación"*.

### La advertencia que más puede costar

> *"cualquier cosa de que el endpoint no esté bien definido o que no vaya de acorde
> a esas reglas que están en el documento, esto va a traer ciertos inconvenientes o
> ciertas fricciones en ese proceso de poder evaluar las soluciones"*

El pipeline del jurado consume el endpoint del equipo. Si no cumple la guía al pie
de la letra, no pueden evaluar la solución. Mismo patrón que en la Etapa 1 con el
esquema de salida: conformarse al contrato pesa más que ser brillante.

---

## 5. Qué es el reto

Nadie lo dijo explícitamente, pero queda delineado.

**Confirmado** (Día 2, moderador): *"el reto final se desarrollará alrededor de la
implementación el diseño de sistemas multiagentes para análisis de datos"*.

**Confirmado** (Día 3): *"buscamos obtener una solución de una arquitectura
multiagente de inteligencia artificial"*.

**Se construye sobre la entrega de la Etapa 1.** Repetido los cuatro días:
*"es muy posible que trabajen sobre esas fuentes de datos, son los modelos
vectoriales o de grafos que ya tienen"*. Recomendaron mejorarlos antes de llegar.

**Hay componente de visualización** (Día 1, Aval Digital Labs): *"ustedes van a
tener un reto en donde la idea es que hagan todo el tema de la visualización de la
información"*. El Día 4 completo fue sobre visualización georreferenciada y líneas
de tiempo, y el moderador insinuó bastante: *"¿Será que van a tener que lidiar en el
reto con datos georreferenciados? Podría ser interesante"*.

Prometieron enviar por correo **diez fuentes de datos geoespaciales** (NASA
Earthdata Search, Copernicus Data Space, Sentinel, MODIS, VIIRS, ECOSTRESS).

**Los tres fenómenos siguen siendo los mismos**: IA en entornos militares, seguridad
espacial y órbita baja terrestre, dinámicas territoriales en Latinoamérica y el
Caribe.

**El propósito de fondo**, TC Alexandra Zavala: *"los datos heterogéneos se pueden
presentar hacia eventos estructurados, que es lo que buscamos poder madurar y
presentar con las arquitecturas multiagente que se van a desarrollar durante la
fase presencial"*. Extraer actores, eventos, lugares y relaciones para anticipar.
Mostró un caso de Palantir en respuesta a desastre natural como referencia de
producto. Insistió en soberanía tecnológica y en no depender de lo que ya existe.

---

## 6. Playbook técnico

### Lo de mayor retorno

**El docstring de la tool es el prompt** (Rubén Manrique, Día 3):

> *"El docstring no es documentación. El nombre de la función, la firma con sus
> anotaciones de tipo y el docstring son literalmente el texto que el modelo va a
> leer para decidir si llama esta herramienta y con qué argumentos. No hay nada
> más."*

> *"mejorar un docstring rinde más que cambiar el modelo"*

Con modelos open source esto es determinante.

**El error que quema el presupuesto sin avisar**:

> *"un agente que no encuentra en una base de datos lo que busca puede estar
> reintentando indefinidamente... esa es la clase de error que no da una excepción
> porque no es un error de código. No da error tampoco en los logs. Y ya se van a
> dar cuenta cuando le llega la factura"*

Límite duro de iteraciones desde la primera línea. Con presupuesto fijo y penalidad
por excederlo, un bucle silencioso puede acabar el reto de madrugada.

### Diseño de la arquitectura

- `create_react_agent` de LangGraph son tres líneas y **cubre el 70% de los casos**
  según Manrique. Bajar al grafo explícito solo cuando algo se quede corto.
- La diferencia entre flujo y agente **no es cuántas veces se llama al modelo, es
  quién decide el orden de los pasos**. Un pipeline con 10 llamadas sigue siendo un
  flujo, y está bien que lo sea.
- Blend 360: **41,8% de los fallos en sistemas multiagente son de diseño y
  especificación; 36,9% son desalineación entre agentes.** Casi nunca es el modelo.
- Por cada agente definir: propósito, entrada, salida, criterios de éxito, autoridad.
  Y una sexta que casi todos olvidan, **qué NO debe saber**. Menos contexto es menos
  ruido.
- **Más memoria es más varianza, y más varianza es más alucinaciones** (Tito Neira).
- Partir en agentes especialistas reduce varianza.
- Si algo se puede calcular de forma determinista, que el agente **consuma el
  resultado** en vez de calcularlo.
- **Nodo de redacción separado**, con su propio prompt y sin herramientas. Redacta
  mucho mejor que si se mezcla búsqueda y generación.
- El estado solo lleva lo que alguna arista o nodo lee.

### Antipatrones (Blend 360)

- Multiagente por defecto: *"15x tokens sin ganancia"*.
- **Varios escritores en paralelo**: nunca llegan a consenso y se quedan en bucle.
- Handoffs con pérdida de contexto.
- Aprobación humana única al final, sobre un plan opaco en vez de sobre la acción real.
- Sin límites de dominio: abre la puerta a prompt injection.

### Observabilidad

- **Langfuse**: open source, docker compose, agnóstico al framework vía
  OpenTelemetry, se integra con decoradores. *"Instrumentar observabilidad puede
  costar mínimo 20 minutos."* Un ID de correlación por ejecución, propagado a cada
  llamada del modelo, cada tool y cada contexto extraído.
- Golden set de **cinco casos revisados a mano** para arrancar.
- LangSmith es la alternativa, con la salvedad de que envía las trazas a un tercero.

### El arnés

Jofre Manchola, Bantor, Día 5:

> *"lo apropiado sería que llevaran ya un arnés construido... que ya tengan claro
> herramientas, skills, agentes y hooks"*

- Agents, skills, tools, hooks.
- Hooks concretos suyos: uno que **valida que no se filtren secretos en cada commit**,
  y otros que **exigen confirmación humana** antes de borrar archivos o de cualquier
  acción que cueste dinero.
- Modelo fuerte para arquitectura y decisiones, modelo barato para implementar, y
  **el verificador debe ser un modelo distinto del que escribió el código**.
- Dejó **consultas y respuestas pregrabadas** por si durante la demo se caía el API
  o el internet. Con 8 minutos de pitch tras 24 horas, un plan B para la demo vale
  mucho.
- Alternativas gratuitas si no hay licencias: Open Code con Open Chamber.

### RAG y chunking (Conecto, Día 5)

- **Combinar varias estrategias de chunking**: por tokens, por página, por jerarquía,
  tablas fila a fila repitiendo encabezado, semántico y contextual. *"Puede que
  combinen incluso hasta cuatro formas."*
- Heurística para el semántico: cortar por signos de puntuación.
- Métricas de recuperación: **context recall, context precision, hit rate@k**.
- Evaluar en cuatro capas: retrieval, generación, decisiones del agente y golden
  dataset.
- **Recomendaron reranking con cross-encoder.** Nota para nosotros: lo retiramos en
  la Etapa 1 por la Sección 8.3, que exigía operar exclusivamente sobre vectores.
  Esa restricción era de la Etapa 1 y aquí no aplica.
- Recursos gratuitos que mencionaron: modelos de layout para tablas en NVIDIA, y
  VLMs gratuitos en NVIDIA y Google AI Studio.

### Visualización (Camilo Escobar, Día 4)

- Tres tipos: **mapa de puntos** (dónde está algo), **coroplético** (comparar
  regiones), **mapa de calor** (densidad).
- Librerías: Leaflet, Mapbox GL JS.
- **Maestro-detalle** es el patrón que recomendó para este reto: mapa grande más
  lista de detalles, estilo Airbnb.
- **Filtros globales y brushing and linking**: al filtrar en una vista, reaccionan
  todas.
- Trampas reales: **normalizar formatos de fecha** (cada observatorio publica
  distinto según el país) y **mantener siempre la relación con el doc_id y el
  chunk_id de origen** para poder citar la fuente. Lo segundo ya está resuelto desde
  la Etapa 1.
- Accesibilidad: revisar contraste entre colores de la escala, y no poner las
  leyendas en medio del mapa.
- Riesgo de representación falsa: unir puntos con líneas rectas sugiere crecimiento
  lineal donde no lo hubo.

---

## 7. Pendientes verificables

- **El repositorio de la Etapa 1 no tiene archivo LICENSE.** Verificado el 18 de
  septiembre de 2026. Para el reto final el repositorio debe tener licencia
  permisiva o hay descalificación.
- **Revisar el correo del capitán de equipo.** Mencionaron al menos tres envíos: las
  diez fuentes geoespaciales, el notebook de LangChain y LangGraph de Rubén Manrique,
  y respuestas a preguntas de equipos. La charla de Tomás Acosta que se cayó el Día 4
  también iba a reponerse.
- **Correo de contacto de los organizadores**: `codefest.adastra@fac.mil.co`
  (transcrito con errores en los subtítulos; verificar antes de usar).

---

## 8. Lectura de conjunto

Con 24 horas, presupuesto limitado y modelos open source, lo que separa no va a ser
la arquitectura más ingeniosa. Son tres cosas aburridas:

1. Cumplir el contrato del endpoint exactamente como dice la guía.
2. Tener límites de iteración para que el presupuesto llegue vivo al final.
3. Llegar con el arnés ya armado.

Las tres se pueden preparar antes de saber cuál es el reto.
