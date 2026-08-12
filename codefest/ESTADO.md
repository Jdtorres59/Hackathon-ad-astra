# Estado del proyecto — CODEFEST AD ASTRA 2026, Etapa 1

Entrega: **13 de agosto de 2026, 23:59 (hora Bogotá)** por formulario
(https://forms.cloud.microsoft/r/ZNDzFvVxmX) registrando un enlace a carpeta
compartida. Va a Google Drive, no a GitHub: los `index.faiss` superan el límite
de 100 MB por archivo de GitHub. **Subir el 12, no el 13.**

## Qué está hecho

| Artefacto | Estado | Ruta |
|---|---|---|
| Inventario (1.826 docs, DOC_ID oficial) | listo | `src/codefest/inventory.py` |
| Corpus extraído (104,8 M car., 886 pág. por OCR) | listo | `data/docs.jsonl` |
| Fragmentos | listo, 91.088 | `data/chunks.jsonl` |
| Índices FAISS (3 encoders) | listos y verificados | `entrega/base_vectorial/encoder_*/` |
| Centroides de fenómeno y de documento | listos | `entrega/base_vectorial/encoder_*/` |
| Grafo (33.178 nodos, 331.721 aristas) | listo | `entrega/base_vectorial/grafo/` |
| `resultados.jsonl` | 50 líneas, validado | `entrega/resultados.jsonl` |
| `generador.py` | corre en venv limpio con y sin GPU, salida idéntica | `entrega/generador.py` |
| Informe técnico | listo, 6 páginas de 8 | `entrega/informe_tecnico.pdf` |

## Calidad medida

| Señal | Valor |
|---|---|
| Known-item recall@3 (200 pruebas) | 0,900 |
| Known-item MRR (200 pruebas) | 0,838 |
| Known-item NDCG@10 (200 pruebas) | 0,805 |
| Título → su documento (200 pruebas) | 0,920 |
| Cobertura del fragmento gold | 0,478 |
| Documento 1 en el fenómeno esperado | 84% |
| F1@3 sobre el mini gold (8 preguntas) | 0,09–0,18, sin resolución |

## Decisiones tomadas con datos

1. **Agregación a documento por máximo** (`DOC_AGG_TAIL_WEIGHT = 0.0`). Con RRF
   la cola hacía ganar a documentos largos y mediocres. Known-item 0,78 → 0,92;
   títulos 0,45 → 0,92.
2. **Poda de documentos duplicados** (`DOC_DEDUP_COS = 0.95`, acuerdo de los tres
   encoders sobre el centroide de documento). El corpus repite documentos con
   nombres distintos y traducidos. 18 → 14 consultas con duplicados en el top-3.
   A 0,92 empieza a descartar informes legítimamente distintos.
3. **Fusión RRF de los tres índices.** Mejora fragmentos (cobertura 0,444 →
   0,478), no documentos. Se mantiene porque NDCG@10 pesa la mitad del puntaje.
4. **Expansión a 245 palabras.** 250 no cambia nada: el techo lo impone no
   cortar oraciones (Sección 3.3), no el parámetro.

## Fallos encontrados y arreglados

- **Conflicto de OpenMP entre faiss y torch** (`OMP: Error #15`, SIGSEGV). Habría
  reventado `generador.py` en la máquina del jurado = exclusión. Resuelto en
  `codefest/__init__.py` + faiss a un hilo, verificado contra numpy puro.
- **Agregación a documento invertida** por el decaimiento plano de RRF.
- **Duplicados del corpus** ocupando huecos del top-3.
- **Licencias de los modelos de NER** (12 ago, a raíz del Q&A de los
  organizadores). El informe declaraba los tres modelos de spaCy como MIT. Falso:
  solo `en_core_web_md` lo es; `es_core_news_md` es GPL 3.0 y `pt_core_news_md`
  es CC BY-SA 4.0. Grafo reconstruido con inglés estadístico + reglas propias
  para es/pt. Ver "Licencias" abajo.
- **Artefactos del extractor tabular en el grafo** (12 ago). Los CSV del AI Index
  se aplanan a `columna: valor` con `|` entre filas, y el NER leía esas cadenas
  como nombres propios: 547 nodos que eran cabeceras de columna
  (`Journal/Book: J Urol`), fragmentos de listas de autores (`Li J. |`), URLs y
  encabezados de capítulo. Siete de ellos estaban entre los cien más conectados,
  o sea bien visibles. Filtrado con `es_ruido_tabular()` en `graph/ner.py`, que
  va dirigido a esas formas y no a los dos puntos en general: `ISO 24113:2023`,
  la norma de mitigación de basura orbital, es una entidad legítima y sobrevive.
- **SIGSEGV en cualquier máquina sin GPU** (12 ago, revisión final). `generador.py`
  moría con código 139 al codificar la consulta con torch en CPU. `faiss-cpu` y
  `torch` traen cada uno su `libomp`, y `KMP_DUPLICATE_LIB_OK=TRUE` solo silencia
  el aviso `OMP: Error #15`: los dos runtimes siguen levantando su pool de hilos
  y el segundo mata el proceso. No se veía porque en este Mac torch corre en mps
  y nunca levanta el pool — y la prueba del jurado, que corre aquí, daba
  «idéntico». **El jurado corre en CPU**: `requirements.txt` fija `faiss-cpu`.
  `OMP_NUM_THREADS=1` no basta (torch fija sus hilos al inicializar, después de
  leer la variable); hay que llamar a `torch.set_num_threads(1)`. Arreglado en
  `index_build.limitar_hilos_openmp()`, que antes solo cubría faiss.
- **La salida dependía del procesador** (12 ago, revisión final).
  `sentence-transformers` usa media precisión en mps/cuda y fp32 en CPU, así que
  el vector de la consulta cambiaba con la máquina. Medido sobre las 50 consultas
  reales: cpu/fp32 frente a mps/fp16 daba **15 de 50 listas de fragmentos
  distintas y 1 de 50 top-3 de documentos distinto**. El `resultados.jsonl`
  entregado no era el que iba a reproducir el jurado. La consulta se codifica
  ahora siempre en CPU/fp32 (`encoders.QUERY_DEVICE`). No cuesta calidad: con
  200 pruebas, known@3 0,900, MRR 0,838, NDCG@10 0,810, títulos@3 0,920 —
  idénticas a las de antes.
- **Palabras partidas por guion blando** (U+00AD). `clean.py` unía las cortadas
  por guion visible + salto de línea, pero no por guion blando + espacio, que es
  como PyMuPDF entrega el guionado de los informes a dos columnas. 8.095
  fragmentos de 182 documentos indexaban `align ment` en vez de `alignment`,
  incluidos SWF-121..124 (F2) y RESDAL-092 (F3). Arreglado en `clean.py` y
  reparado sobre los intermedios con `scripts/02b_desguionizar.py`, sin
  refragmentar, y recodificando solo las filas tocadas con
  `scripts/03b_recodificar_filas.py`.

## Licencias (verificadas contra el `meta.json` de cada artefacto, 12 ago)

Los organizadores dictaminaron por Q&A que **no puede usarse ningún componente
con licencia CC BY-NC-SA 4.0** ("es restrictiva"). Verificación completa:

| Componente | Licencia | Estado |
|---|---|---|
| granite-embedding-311m | Apache 2.0 | viaja en la entrega |
| bge-m3 | MIT | viaja en la entrega |
| multilingual-e5-large | MIT | viaja en la entrega |
| faiss, spaCy (librería), blingfire, NetworkX | MIT / BSD | ok |
| `en_core_web_md` | MIT | se usa (76,5% del corpus) |
| `es_core_news_md` | **GNU GPL 3.0** | **retirado** |
| `pt_core_news_md` | **CC BY-SA 4.0** | **retirado** |

Alternativas descartadas: `wikineural-multilingual-ner` es CC BY-NC-SA 4.0 (la
licencia del fallo) y `xlm-roberta-*-ner-hrl` es AFL-3.0. Español y portugués
pasan a `entidades_reglas()` en `graph/ner.py`: secuencias capitalizadas con sus
partículas, artículo inicial podado, descarte de romanos, abreviaturas de
citación y versalitas, tipado por pistas léxicas. Es código propio, sin licencia
de terceros. **Ningún modelo de NER viaja en la entrega ni corre en consulta**:
`generador.py` no importa spaCy y el grafo se consulta con el gazetteer.

## Hallazgos del corpus que conviene recordar

- El **fenómeno es la carpeta de origen, no el tema**: CEEEP y SIPRI están en
  `F3_Dinamicas_Territoriales` pero publican sobre IA militar (20 documentos).
  Por eso el prior temático no se sube: enterraría documentos correctos.
- Hay **documentos idénticos con nombres distintos** (`ILIA_documento-ilia-2025`
  e `ILIA_docuemnto-ilia-web`, coseno 1,000) y ediciones traducidas del mismo
  informe (`gcsr-2026-execsum-spa` / `-por` / `-fre`).
- Series de informes casi iguales entre ediciones (MAPP/OEA semestrales): el
  mini gold pide una edición concreta y recuperamos otra con el mismo texto.
  En una pregunta devolvemos el pasaje correcto al 93% atribuido a otro
  documento. Eso no lo arregla ningún ajuste de recuperación.
- **granite tiene el espacio muy comprimido**: 1.750 pares de documentos con
  coseno > 0,98 entre 1.826, frente a 175 de bge_m3. Es el peor en todas las
  sondas.

## Cómo reconstruir

```bash
bash scripts/run_all.sh                 # todo, de corpus a entrega
bash scripts/run_all.sh --desde grafo   # solo desde un paso
```

**Correr el grafo y la codificación en secuencia, no en paralelo.** Medido: en
paralelo se gana un 8% de reloj y se dobla el pico de memoria. Además,
`03_embed_index.py` reutiliza los vectores de `data/vectors/*.npy` si existen.

## Decisiones abiertas

1. **`doc_id`**: **cerrada**. Se usa el del inventario (`F1-AIINDEX-001`) y ahora
   se declara explícitamente en el README de la entrega, junto con `fuente`,
   `ruta_relativa` y los otros dos esquemas que viajan en la metadata, para que
   el evaluador pueda mapear si su ground truth usa otra convención. Sigue
   controlado por `CODEFEST_DOC_ID_SCHEME`.
2. **Reranker cross-encoder**: **cerrada, retirado del código**. No es
   generativo, pero puntúa leyendo el par consulta-texto y no el espacio
   vectorial, así que no opera «exclusivamente sobre vectores, puntuaciones de
   similitud y metadata» (Sección 8.3). Mismo criterio que dejó fuera el BM25.
   Era código muerto (`USE_RERANKER` por defecto 0), así que no cambia ningún
   resultado, y de paso quita una variable de entorno que podía alterar el
   comportamiento en la máquina del jurado.

## Estado tras la reconstrucción del 12 de agosto — COMPLETA

Todo el pipeline se volvió a correr después de los cambios de licencia y de
guion blando. Resultado verificado:

| Comprobación | Resultado |
|---|---|
| Índices FAISS | 3 × 91.088 vectores, 0 desalineados |
| Alineación índice↔metadata | coseno 1,0000 (peor caso) en los tres |
| Tabla 2 completa | OK en las 91.088 líneas × 3 |
| Grafo | 33.330 entidades / 333.332 relaciones, 100% con evidencia (luego se limpió el ruido tabular: 33.178 / 331.721) |
| `resultados.jsonl` | 50 líneas, máx. 245 palabras |
| **Prueba del jurado** | **byte a byte idéntico**, 51 s en venv limpio |
| Informe | 5 páginas de 8, declara las licencias reales |

Las cifras finales, tras la limpieza del grafo y la revisión final, están más
abajo.
| Paquete | 1,67 GB + 5,20 GB de modelos = 6,88 GB |

## Revisión final del 12 de agosto — COMPLETA

Última cacería de bugs antes de subir. Encontró dos fallos que ninguna prueba
anterior podía ver porque todas corrían en este Mac (ver arriba: SIGSEGV en CPU
y salida dependiente del procesador), más cinco arreglos menores.

| Comprobación | Resultado |
|---|---|
| `generador.py` en máquina fingida sin GPU | **exit 0, salida idéntica byte a byte** |
| Prueba del jurado en venv limpio | idéntico, 56 s |
| `07_validar.py` | sin errores bloqueantes |
| Sondas (200 pruebas) | known@3 0,900, MRR 0,838, NDCG@10 0,805, títulos@3 0,920 |
| Índices de contenidos entre los 500 fragmentos | 1 → **0** |
| Informe | 6 páginas de 8 |
| Paquete | 24 módulos, 1,67 GB + 5,20 GB de modelos |

`11_prueba_jurado.sh` tiene ahora un paso `[5/5]` que repite la ejecución con
torch forzado a CPU. Sin él, la prueba solo comprobaba determinismo en esta
máquina, no reproducibilidad.

Otros arreglos de esta pasada:

- **Índices de contenidos degradados en la selección de fragmentos.** Un índice
  de PDF contiene todos los términos de la consulta y ninguna respuesta; en q027
  ocupaba el puesto 1, el de más peso del NDCG@10. Se reconocen por dos o más
  líderes de puntos (1.115 de 91.088 fragmentos) y se mandan al final de la lista
  de candidatos, no se descartan: el Q&A permite conservarlos. La sonda de
  known-item baja 0,810 → 0,805, pero es artefacto de la propia sonda: 2 de sus
  200 semillas SON índices, y degradarlos es justo lo que se busca.
- **`query_id` inesperados pasan de error a aviso.** `consultas.py` acepta a
  propósito variantes de nombre de campo, pero `validate_results` exigía
  `q001..q050` y hacía que `generador.py` devolviera código 1 con una salida
  perfectamente válida. Las dos mitades se contradecían.
- **`doc_id` declarado en el README** de la entrega, con `fuente`,
  `ruta_relativa` y los dos esquemas alternativos. F1@3 es la mitad del puntaje
  y depende de que el evaluador pueda casar nuestro identificador con el suyo.
- **Reranker retirado** del código empaquetado (ver "Decisiones abiertas").
- **`requirements.txt`** decía "Probado en macOS arm64 y Linux x86_64". En Linux
  no se probó nunca; ahora declara lo que de verdad se probó.

Revisado y sin hallazgos: esquema de la Tabla 3, `doc_id`/`chunk_id` repetidos,
palabras por fragmento (máx. 245), integridad del texto expandido, orden de la
metadata en los tres encoders, contigüidad de `posicion`, índice del grafo,
basura tabular en la salida, guion blando y ligaduras, las 5 imágenes del Q&A, y
coherencia de fenómeno (las 9 «incoherentes» se explican por SIPRI y CEEEP, que
están en F3 y publican sobre IA militar).

## Diagnóstico del 12 de agosto → ver `DIAGNOSTICO.md`

Se midió NDCG@10 por primera vez (nunca se había invocado `ndcg_at_k`): **0,808**
known-item a escala, **0,906** sobre el mini gold. Sin regresión atribuible a la
reconstrucción. Se añadió un baseline BM25 (`src/codefest/baseline_bm25.py`) para
calibrar: el sistema denso gana 0,92 contra 0,72 en la sonda de títulos, que es la
que se parece a las consultas reales.

Dos cosas medidas y descartadas:
- **Híbrido denso+BM25**: duplicaría el F1@3 del mini gold, pero §8.3 exige operar
  "exclusivamente sobre vectores, puntuaciones de similitud y metadata". No se entrega.
- **Apagar el grafo**: diferencia de ~0,004 con n=500, indistinguible de cero. No se toca.

**No se recomienda ningún cambio a la entrega** por parte del diagnóstico. La
revisión final posterior sí encontró motivos, y están arriba.

## Pendiente

Solo queda subir `entrega/` a Drive con lectura pública y registrar el enlace en
https://forms.cloud.microsoft/r/ZNDzFvVxmX. **Lo hace Juan, no yo**: es una
acción externa a su nombre.

Antes de subir, decidir el `doc_id` (ver "Decisiones abiertas"): cambiarlo es
regenerar `resultados.jsonl` en segundos, sin reindexar.
