# El reto — extraído del acto de apertura

Fuente: `apertura/TRANSCRIPT_APERTURA.md`, 18 de septiembre de 2026, edificio Mario Laserna.
Presentado por el subteniente de reserva Mario Linares Vásquez, profesor asociado de Uniandes.

---

## Lo que hay que construir

Una solución con **arquitectura de inteligencia artificial multiagente** que permita analizar datos relacionados con tres fenómenos, sobre el corpus curado que ya tenemos indexado de la Etapa 1.

> *"Ustedes están aquí porque son los 20 equipos mejores en generar esa base de conocimiento vectorial y de grafo que van a utilizar como base para construir ese asistente conversacional."*

### Los tres fenómenos

Los nombres cambiaron ligeramente respecto a la Etapa 1. Como los dijo Linares:

1. **Inteligencia artificial y capacidades estratégicas**
2. **Seguridad espacial**
3. **Amenazas regionales**

Como los amplió el coronel Gutiérrez en su discurso:

1. IA aplicada en entornos militares
2. Seguridad del dominio espacial y amenazas asociadas a la **órbita terrestre baja**
3. **Dinámicas territoriales estratégicas** de América Latina y el Caribe

En `metadata.jsonl` siguen siendo el campo `fenomeno` con valores 1, 2 y 3.

---

## Los dos entregables

### Reto 1 — sábado 08:00

> *"la creación de un asistente conversacional con interfaz gráfica que mínimo tenga dos agentes orquestados a través del esquema arquitectural que ustedes definan, que permitan responder preguntas interesantes para resolver los fenómenos mencionados con el corpus que ya le entregamos"*

- Asistente conversacional
- **Con interfaz gráfica** (no es un endpoint pelado)
- **Mínimo 2 agentes orquestados**
- La arquitectura de orquestación la define cada equipo
- Sobre el corpus ya entregado

### Reto 2 — sábado 12:30

> *"construir un tablero de analítica visual que permita mejorar el análisis que puede hacer un humano para responder preguntas asociadas a los tres fenómenos... debe estar conectado con el asistente conversacional, lo cual nos lleva a tener un mínimo de tres agentes trabajando en una arquitectura multiagente"*

- Tablero de analítica visual
- El criterio es **mejorar el análisis que puede hacer un humano**, no solo mostrar datos
- **Conectado con el asistente conversacional**
- Eso eleva el mínimo a **3 agentes**

### Puntos extra

> *"cualquier análisis adicional que implementen con cualquier agente adicional, o cualquier feature que la creatividad de ustedes va a ser bonificado con puntos extra"*

Confirmado dos veces: los análisis y agentes adicionales tienen **bonificación explícita en la rúbrica**.

---

## Documentación: no es opcional

> *"El diseño y uso de cada componente debe estar correctamente documentado, porque somos rigurosos en la calidad. De nada nos sirve un producto funcional si no lo documentamos bien, si no está bien diseñado."*

El handbook detalla qué documentación exactamente. Se entrega junto con la solución.

---

## Los tiempos son absolutos

> *"Si hay un milisegundo después de la hora de entrega, hora legal, no se los podemos recibir."*
> *"No hagan envíos a último minuto."*

| Hora | Evento |
|---|---|
| 17:00 | Inauguración |
| 18:00 | Cóctel (invitados) / equipos se ubican en pisos 5 y 6 |
| 19:00 | Cena |
| **20:00** | **Inicia el reto** |
| 23:00 | Primera ronda de mentores (pasan desde las 20:00) |
| 01:00 | Refrigerio |
| 07:30 | Desayuno |
| **08:00** | **Entrega Reto 1** |
| 10:00 | Refrigerio |
| **12:30** | **Entrega Reto 2** e inicia preparación del pitch |
| 13:00 | Almuerzo |
| 14:00 | Pitches, **llamado en orden aleatorio** |
| 16:30 | Deliberación del jurado |
| 17:00 | Anuncio de ganadores |

El orden aleatorio importa: **hay que estar listos a las 14:00**, no a las 16:00.

---

## El pitch

- **5 minutos de presentación + 3 de preguntas.**
- Ante **jurado de la FAC y expertos de las empresas patrocinadoras**, no ante profesores de Uniandes. Linares lo dijo explícitamente: evitan conflicto de interés, y advirtió que *"los oficiales de la Fuerza Aérea que van a ser jurados y los expertos de las empresas son más exigentes que nosotros como profesores"*.
- Hay mentores disponibles para ayudar con el pitch después de las 12:30.

---

## Recursos disponibles durante el reto

**Mentores de empresas**, desde las 20:00, rondas formales a las 23:00:
- **ADL** (Aval Digital Labs) — son los que montaron la infraestructura, LiteLLM y Coolify
- **Conecto** — agentic RAG, tools, MCP
- **Blend 360** — arquitectura multiagente, observabilidad

**Personal de la FAC** presente durante todo el evento para dudas sobre los fenómenos:

> *"si a ustedes les ocurre algo respecto a cómo quieren mostrar esa información, apóyense en los cadetes, y apóyense también en el personal de expertos de la Fuerza Aérea que van a estar acá para ayudarlos con eso"*

**El cadete del equipo** es un recurso, no un adorno. Linares insistió: *"Aprovechen los cadetes."*

**Sala de descanso** dispuesta, con ubicación por enviar. Recomendación explícita de hacer turnos de media hora a dos horas.

---

## Código de honor

El equipo se comprometió de pie a:
- Respetar emblemas, símbolos, instalaciones y propiedad de la FAC y de Uniandes
- Actuar buscando el bien común por encima del interés personal
- Mantener las instalaciones como se encontraron
- **Actuar con honestidad, sin recibir ni brindar ayuda no permitida**
- Cumplir con dedicación los compromisos adquiridos
- Colaborar para que los demás participantes respeten el código

---

## Premios

**Los tres primeros equipos**: visitas geoestratégicas a tres bases de la FAC, con acceso a aeronaves, posibilidad de subir a algunas, y uso de los simuladores reales.

| Puesto | Premio por integrante |
|---|---|
| 1º | iPad Air + voucher de certificación Google AI Generative Leader + hoodies y goodies |
| 2º | Dron DJI Neo + vouchers de certificación + hoodies y goodies |
| 3º | Reloj Garmin + hoodies y goodies |

Además, un patrocinador sin revelar dará un regalo a **todos** los participantes el sábado.

---

## Contexto institucional que sirve para el pitch

El coronel Gutiérrez definió el propósito de esta edición:

> *"el COEFES tiene como propósito el diseño de un modelo de innovación para la inteligencia multidominio... el desafío consistirá en desarrollar un ecosistema de cooperación civil-militar orientado a la generación de capacidades de inteligencia aérea, espacial y ciberespacial"*

Y el marco del problema:

> *"el volumen de datos crece a un ritmo exponencial y su recolección, procesamiento, análisis y aprovechamiento constituyen un factor diferencial y una ventaja estratégica para las naciones"*

Este es el primer ejercicio operacional del **Comando de Inteligencia Aérea, Espacial y Ciberespacial** de la FAC. Hay delegaciones observadoras de Argentina, Brasil, Chile, Estados Unidos, Perú e Italia.

Ediciones anteriores, útil para situar la ambición: 2022 Atenea AI (procesamiento de imágenes satelitales), 2023 Eagle View AI (reconocimiento de objetos en video aerotransportado), 2024 cifrado de activos espaciales.

**101 equipos** en la fase virtual, **20 clasificados** de **12 instituciones**.

---

## Pendiente

El **handbook técnico** con especificaciones, **rúbrica de evaluación** y proceso de entrega llega por los canales de comunicación del equipo. Contiene el contrato exacto del endpoint, los IDs de modelo, los precios por millón de tokens y la cifra de presupuesto.

Cuando llegue: transcribir lo vinculante a `CONTRATO_JURADO.md` antes de escribir código que dependa de ello.
