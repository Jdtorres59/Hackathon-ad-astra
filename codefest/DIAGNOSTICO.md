# Diagnóstico previo a la entrega — CODEFEST AD ASTRA 2026, Etapa 1

**Fecha:** 12 de agosto de 2026 · **Entrega:** 13 de agosto, 23:59 (Bogotá)

Motivo: el 12 de agosto se reconstruyó medio pipeline (8.095 vectores recodificados por el
arreglo de guion blando, grafo rehecho por licencias). Todas las medidas de calidad que
teníamos eran del 7 de agosto y describían un sistema que ya no existía. Esto lo corrige.

---

## 1. Con qué nos van a calificar

Leído de `Reto clasificatorio CODEFEST AD ASTRA 2026.pdf`, §10–11:

| Métrica | Nivel | Cómo |
|---|---|---|
| **NDCG@10** | fragmentos | media sobre 50 consultas; relevancia graduada; penaliza más el error arriba |
| **F1@3** | documentos | métrica de conjunto, sin orden; `R@3` divide por `mín(\|D*\|, 3)` |
| **Borda** | final | dos tablas independientes, puntos `N − posición`, suma. Empate → NDCG@10 |

Tres detalles que cambian cómo hay que interpretarlo:

1. **§10.2.1 — el `chunk_id` no es la clave de emparejamiento.** La relevancia de un fragmento
   se juzga sobre su **contenido textual**. Esto convierte el arreglo de guion blando de hoy
   (8.095 fragmentos que indexaban `align ment` en vez de `alignment`) en algo que afecta al
   puntaje, no en cosmética.
2. **El `doc_id` sí es clave** para F1@3. La especificación declara explícitamente interno el
   `chunk_id` y no dice nada equivalente del `doc_id`. Eso respalda mantener el DOC_ID del
   inventario oficial (`F1-AIINDEX-001`), que es el único identificador que publicaron.
3. **Borda es por posición, no por margen.** Basta con estar por delante. Eso penaliza arriesgar
   una configuración ya validada a cambio de mejoras marginales.

**No podemos conocer nuestro NDCG@10 ni nuestro F1@3 reales**: el ground truth no es público.
Todo lo que sigue son aproximaciones, y se reportan como tales.

---

## 2. Estado de la entrega: verificaciones duras

Todo comprobado **después** de la reconstrucción de hoy.

| Comprobación | Resultado |
|---|---|
| Índices FAISS | 3 × 91.088 vectores, **0 desalineados** |
| Alineación índice↔metadata | coseno **1,0000** en el peor caso, en los tres |
| Campos obligatorios (Tabla 2) | OK en las 91.088 líneas × 3 |
| Grafo | 33.330 entidades / 333.332 relaciones, **100% con evidencia** |
| `resultados.jsonl` | 50 líneas, q001–q050, máx. **245** palabras (límite 250) |
| Fragmentos por consulta | 10, de 7,5 documentos distintos de media |
| Documentos repetidos en un top-3 | **0 de 50** |
| **Prueba del jurado** | **byte a byte idéntico**, 51 s en venv limpio |
| Licencias | todos los componentes Apache 2.0 / MIT / BSD, verificado por artefacto |

---

## 3. Regresión frente al 7 de agosto

| Señal | 7 ago | 12 ago | Δ |
|---|---|---|---|
| Known-item recall@3 (documento) | 0,930 | 0,900 | −0,030 |
| Título → su documento | 0,930 | 0,920 | −0,010 |
| Cobertura del fragmento gold | 0,478 | 0,478 | 0 |
| F1@3 mini gold | 0,092 | 0,092 | 0 |
| Coherencia temática (doc 1 en su fenómeno) | 84% | 84% | 0 |

Con n=200, el error estándar del known-item es ≈0,021, así que −0,030 es ~1,4 desviaciones:
**dentro del ruido**, no una regresión demostrable. Las otras cuatro señales no se movieron.

---

## 4. Métricas nuevas: NDCG@10, medido por primera vez

`ndcg_at_k()` existía en el código desde el principio y no se invocaba desde ningún sitio. Es
la mitad del puntaje y nunca se había medido. Ahora sí:

| Proxy | Valor | Qué mide |
|---|---|---|
| **NDCG@10 known-item** (n=200) | **0,808** | relevancia binaria: el fragmento que originó la pseudo-consulta |
| **NDCG@10 mini gold vs. ideal** (n=8) | **0,906** | relevancia graduada por solapamiento de texto, ideal = cobertura total |
| NDCG@10 mini gold, solo orden | 0,801 | aísla la calidad del ranking |
| Recall@10 a nivel de fragmento | 0,870 | el fragmento correcto entra en el top-10 |

**Aviso de interpretación:** el known-item usa como consulta una copia literal de 45 palabras
del propio fragmento. Es mucho más fácil que una pregunta en lenguaje natural, así que 0,808
es optimista y **no es un pronóstico del puntaje**. Sirve para comparar configuraciones.

---

## 5. ¿Somos competitivos? Contraste con un baseline léxico

Sin el ground truth ni los resultados de otros equipos, la única forma honesta de calibrar es
preguntarse si el sistema denso bate a una búsqueda por palabras clave. Se implementó BM25
sobre los mismos 91.088 fragmentos (`src/codefest/baseline_bm25.py`) y se le pasaron las
mismas sondas.

| Sistema | Known-item rec@3 | Known-item NDCG@10 | **Títulos rec@3** | Mini gold F1@3 | Mini gold NDCG@10 |
|---|---|---|---|---|---|
| denso + grafo *(lo que se entrega)* | 0,900 | 0,808 | **0,920** | 0,092 | 0,906 |
| denso sin grafo | 0,900 | 0,816 | **0,925** | 0,092 | 0,906 |
| BM25 | **0,970** | **0,881** | 0,725 | **0,113** | **0,929** |

**BM25 gana en tres de las cinco señales. Hay que entender por qué antes de alarmarse.**

La sonda known-item está sesgada a su favor por construcción: la pseudo-consulta es una copia
literal de 45 palabras del propio fragmento, así que BM25 solo tiene que localizar una
coincidencia exacta de cadena. Es casi una prueba de `grep`, no de recuperación semántica.

**La sonda de títulos es la que se parece a la tarea real**: un título es una descripción
corta y parafraseada de un documento, no una copia de su texto — igual que las 50 preguntas.
Ahí el sistema denso gana **0,920 frente a 0,725**, un 27% relativo. Ese es el resultado que
importa, y dice que la parte densa está haciendo su trabajo.

### El híbrido: margen real que las reglas excluyen

Lo estándar sería fusionar ambos. Se midió (`scripts/13_hibrido.py`):

| Config | Known-item | NDCG@10 | **Títulos** | Mini gold F1@3 | Mini gold NDCG |
|---|---|---|---|---|---|
| solo denso | 0,905 | 0,816 | **0,940** | 0,092 | 0,906 |
| híbrido w=0,5 | 0,915 | 0,841 | 0,855 | **0,204** | 0,960 |
| híbrido w=1,0 | 0,930 | 0,863 | 0,835 | 0,163 | 0,924 |
| híbrido w=1,5 | 0,930 | 0,858 | 0,810 | 0,163 | 0,967 |

El híbrido **duplica el F1@3 del mini gold** (0,092 → 0,204) y sube el NDCG, a cambio de
degradar los títulos de forma monótona (0,940 → 0,810).

**No se entrega, y no por prudencia sino porque las reglas lo prohíben.** §8.3, pág. 17: *«La
recuperación debe operar exclusivamente sobre vectores, puntuaciones de similitud y
metadata»*; y pág. 19 sobre la fusión: *«opera exclusivamente sobre las puntuaciones numéricas
producidas por FAISS»*. Una puntuación BM25 se calcula sobre el texto crudo, no sobre vectores
ni metadata. Se deja documentado como margen conocido para la Etapa 2.

---

## 6. La única decisión de reajuste abierta: el grafo

El grafo entra al RRF como una lista más (§8.5). Se midió encendido y apagado con n=500, que
es el doble de muestra que el resto del diagnóstico:

| n=500 | Known-item rec@3 | NDCG@10 | Títulos rec@3 |
|---|---|---|---|
| Con grafo *(actual)* | **0,9100** | 0,8059 | **0,8940** |
| Sin grafo | 0,9080 | **0,8098** | 0,8900 |

Gana en dos señales y pierde en una, todas por ~0,004. Con n=500 el error estándar es ≈0,013,
así que **el efecto es indistinguible de cero** y ni siquiera la dirección es consistente.

**Decisión: no se toca.** Tres razones:

1. No hay daño medible, así que la regla de "dos señales independientes" no se cumple.
2. §8.5 describe la integración del grafo en la recuperación; tenerla activa la demuestra, y
   el grafo es componente bonus (§7).
3. La entrega está validada y se reproduce byte a byte. Cambiarla la víspera por una
   diferencia de ruido es un mal negocio, sobre todo con Borda, que puntúa por posición y no
   por margen.

---

## 7. Conclusión

**La entrega está sana y es defendible.** El sistema denso supera a un baseline léxico en la
única sonda que se parece a la tarea real (títulos: 0,92 contra 0,72), no hay regresión
atribuible a la reconstrucción de hoy, y por primera vez tenemos NDCG@10 medido: 0,81 en la
sonda de escala y 0,91 en el mini gold.

**Lo que no sabemos, y hay que decirlo:** no conocemos nuestro NDCG@10 ni nuestro F1@3 reales
—el ground truth no es público— ni los resultados de los demás equipos. Ninguna de estas
cifras predice una posición en el leaderboard.

**Los dos riesgos vivos, por orden de tamaño:**

1. **El `doc_id`.** Vale la mitad del puntaje. Se usa el del inventario oficial
   (`F1-AIINDEX-001`). La evidencia lo respalda: §10.2.1 declara interno el `chunk_id` y no
   dice nada equivalente del `doc_id`, lo que implica que este sí debe ser emparejable. Si el
   ground truth usara otro esquema, F1@3 daría cero. Cambiarlo son segundos, sin reindexar.
2. **El F1@3 del mini gold es bajo (0,092)** en términos absolutos. Pero son 8 preguntas y en
   varias el sistema devuelve el pasaje correcto atribuido a otra edición del mismo informe
   (las series semestrales de MAPP/OEA son casi idénticas entre ediciones). No es un fallo de
   recuperación que se arregle ajustando parámetros.

**No se recomienda ningún cambio a la entrega.**


