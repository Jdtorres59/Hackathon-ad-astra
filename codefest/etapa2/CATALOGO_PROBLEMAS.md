# Catálogo de problemas candidatos

**Para el cadete Ortiz.** Quince problemas operacionales derivados de lo que el corpus realmente contiene. Tu trabajo no es resolverlos: es decirnos **cuáles le importan de verdad a la Fuerza y cuáles no**, para que no gastemos la noche construyendo algo que a nadie le sirve.

Marca cada uno con una de tres:

- **CRÍTICO** — esto es un dolor real, alguien en la Fuerza haría este análisis
- **ÚTIL** — no es urgente, pero se vería bien y tiene sentido
- **NO APLICA** — no es un problema, o la Fuerza no lo aborda así

Si algo está mal planteado, corrígelo. Si falta un problema obvio que no vemos, agrégalo al final. **Tu criterio aquí vale más que nuestra intuición de ingenieros.**

---

## Cómo leer la columna de datos

Cada problema dice con qué contamos realmente. Esto importa: hay preguntas excelentes que no podemos responder porque el corpus no las cubre, y preguntas mediocres que podemos responder muy bien. Lo ideal es un problema que sea **crítico para ti** y que además tenga **datos fuertes**.

| Señal | Qué significa |
|---|---|
| **Fuerte** | Hay volumen y el sistema va a responder bien |
| **Media** | Hay datos, pero parciales o dispersos |
| **Débil** | Hay poco; el sistema va a sonar vago |

---

# Fenómeno 1 — IA y capacidades estratégicas

Observatorios disponibles: AI Index de Stanford (13.608 fragmentos), CSET Georgetown (5.876), SIPRI (5.246), Atlantic Council (1.540), ILIA (4.587), DAIO (2.793), CENIA (484).

### P1. Vigilancia tecnológica: qué capacidades de IA militar están madurando y a qué ritmo

*Un oficial de planeación necesita saber qué tecnologías van a estar operativas en tres años para no comprar lo que quedará obsoleto.*

Datos: **Fuerte.** El AI Index trae series por año. SIPRI y CSET cubren adopción militar.
Marca: `[ ]`

### P2. Quién está adquiriendo qué en la región

*Comparar el estado de adopción de IA militar entre países de América Latina, y frente a actores extrarregionales con presencia aquí.*

Datos: **Media.** Hay cobertura de la región vía ILIA, CENIA y RESDAL, pero desigual por país.
Marca: `[ ]`

### P3. Marcos jurídicos y doctrina sobre autonomía en sistemas de armas

*Qué se está regulando internacionalmente y qué obligaciones podrían caerle a Colombia.*

Datos: **Media.** El gazetteer tiene 831 nodos de tipo `MARCO_JURIDICO`. SIPRI cubre bien el debate.
Marca: `[ ]`

### P4. Dependencia tecnológica: qué capacidades no se pueden desarrollar localmente

*El coronel Gutiérrez habló de soberanía y de no depender tecnológicamente. Esto lo aterriza.*

Datos: **Media.** Se infiere de la cadena de suministro y de los actores que dominan cada tecnología.
Marca: `[ ]`

### P5. Ciberseguridad de la industria aeronáutica

*La teniente coronel Zavala dedicó buena parte de su charla a incidentes cibernéticos en aviación entre 2015 y 2025, y al riesgo por terceros y cadena de suministro.*

Datos: **Media.** Aparece en el corpus pero no es el eje de ningún observatorio.
Marca: `[ ]`

---

# Fenómeno 2 — Seguridad espacial y órbita baja

Observatorios: CSIS Aerospace (17.435 fragmentos, el más grande del corpus), Secure World Foundation Counterspace (9.396), UNOOSA (3.960), ESA Space Debris (3.255).

### P6. Capacidades antisatélite: quién las tiene y de qué tipo

*Saber qué actores pueden degradar activos espaciales, y con qué medios: cinético, dirigido, ciber, guerra electrónica.*

Datos: **Fuerte.** El informe Counterspace de SWF es exactamente esto, y es anual, así que hay evolución temporal.
Marca: `[ ]`

### P7. Congestión y basura orbital en órbita baja

*Riesgo de colisión para cualquier activo espacial que Colombia opere o contrate.*

Datos: **Fuerte.** ESA Space Debris es el corpus de referencia mundial.
Marca: `[ ]`

### P8. Dependencia de servicios satelitales de terceros

*Qué pasa si se degrada el acceso a comunicaciones, posicionamiento u observación provistos por operadores extranjeros.*

Datos: **Media.** Se arma cruzando CSIS y UNOOSA, pero no hay un informe dedicado.
Marca: `[ ]`

### P9. Marco jurídico del espacio y obligaciones del Estado

*Qué registra Colombia ante UNOOSA, qué tratados la obligan, qué hace la región.*

Datos: **Fuerte.** UNOOSA es fuente primaria.
Marca: `[ ]`

### P10. Observación de la Tierra aplicada a misión

*Qué capacidades satelitales existen hoy para detectar deforestación, minería ilícita o cambios en infraestructura, que es lo que Zavala mencionó como caso de uso real.*

Datos: **Media.** INPE y CEOBS aportan; la charla de Telespazio del Día 5 da el marco conceptual.
Marca: `[ ]`

---

# Fenómeno 3 — Dinámicas territoriales

Observatorios: RESDAL (11.379 fragmentos), MAPP OEA (5.587), Alertas Tempranas de la Defensoría (3.234 más 363 alertas estructuradas), Amazon Underworld (333 más un CSV de 4.369 filas), CEOBS (1.614), INPE (260).

**Este fenómeno tiene los mejores datos de todo el corpus para visualización**, porque es el único con geografía y tiempo estructurados.

### P11. Dónde se concentran las alertas tempranas y cómo evolucionan

*Mapa de Colombia por municipio con las 363 alertas de la Defensoría entre 2017 y 2026, separadas en Inminencia y Estructural.*

Datos: **Fuerte.** 602 municipios, 33 departamentos, año decodificable del código de alerta. Es serie temporal georreferenciada lista.
Marca: `[ ]`

### P12. Presencia de grupos armados por territorio

*Qué grupo opera dónde, en seis países de la cuenca amazónica.*

Datos: **Fuerte.** Amazon Underworld trae presencia de 10 grupos (ELN, EMC, Clan del Golfo, PCC, Los Lobos, Los Choneros y otros) con códigos administrativos estándar en 662 filas. Coroplético inmediato.
Marca: `[ ]`

### P13. Economías ilícitas y corredores transfronterizos

*Minería ilegal, narcotráfico, trata, y cómo se mueven por fronteras porosas.*

Datos: **Fuerte.** El gazetteer tipifica economías ilícitas y el grafo conecta grupos con territorios y con actividades.
Marca: `[ ]`

### P14. Impacto ambiental como indicador de actividad ilícita

*Deforestación y afectación de fuentes hídricas como señal de minería ilegal, que es literalmente el ejemplo que puso Zavala.*

Datos: **Media.** INPE y CEOBS aportan, pero son los observatorios más pequeños del corpus.
Marca: `[ ]`

### P15. Zonas de frontera: convergencia de amenazas

*Dónde coinciden presencia armada, economía ilícita, alerta temprana vigente y baja presencia estatal.*

Datos: **Media a fuerte.** Requiere cruzar tres fuentes, pero las tres existen. **Es el análisis más difícil de hacer a mano y por eso el que mejor demuestra que el sistema aporta valor.**
Marca: `[ ]`

---

## Nuestra apuesta, si sirve de referencia

Sin tu criterio, iríamos por **P11, P12 y P15** como eje del tablero, y dejaríamos el asistente conversacional abierto a los tres fenómenos.

Razones: son los que tienen datos fuertes con geografía y tiempo, son los que se ven en un mapa, y P15 es el que un humano no puede hacer solo en una tarde, que es exactamente el criterio del Reto 2.

**Pero si nos dices que eso no es lo que le duele a la Fuerza, cambiamos.** Es mejor saberlo a las 20:30 que a las 11:00.

---

## Espacio para lo que falte

Si hay un problema que la Fuerza sí aborda y no está en esta lista, escríbelo aquí. Aunque el corpus no lo cubra bien, queremos saberlo: puede cambiar cómo presentamos el pitch.

1.
2.
3.
