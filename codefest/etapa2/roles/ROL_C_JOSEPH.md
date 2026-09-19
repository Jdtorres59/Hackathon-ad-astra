# Frente C — Herramientas y datos · Joseph

> Lee primero `AGENTS.md` en la raíz del repo. Este documento asume que ya lo leíste.

## Por qué te tocó este frente

Es el de mayor rendimiento por hora, porque casi todo está construido. Tu trabajo es envolver un motor de recuperación que ya funciona, extraer dos funciones que ya existen, y hacer dos ETL cortos. Muchas victorias rápidas y visibles, y eres quien desbloquea a Jair.

## Tu regla de oro

**No reimplementes nada de la Etapa 1.** Si crees que necesitas escribir búsqueda semántica, chunking o consulta de grafo, ya existe. Búscalo antes.

---

## Tus archivos

```
backend/app/herramientas/corpus.py      ← buscar_corpus, perfil_documento
backend/app/herramientas/grafo.py       ← expandir_entidad
backend/app/herramientas/datos.py       ← las tools de analítica del Reto 2
backend/app/datos/preparar.py           ← el ETL
backend/app/routers/analytics.py        ← los endpoints del tablero
```

---

## 21:00-22:30 · Lo primero: firmas definitivas

Jair está bloqueado hasta que existan tus firmas. **Mergea las tools con las firmas finales aunque devuelvan datos falsos.** Primero el contrato, después la implementación.

### `buscar_corpus`

```python
@tool
def buscar_corpus(consulta: str, fenomenos: list[int] | None = None, k: int = 8) -> dict:
    """Busca fragmentos de texto en el corpus de fuentes abiertas sobre IA militar,
    seguridad espacial y dinámicas territoriales de América Latina.

    Úsala cuando la pregunta necesite evidencia textual de los documentos.

    NO la uses para cifras agregadas, series temporales ni conteos por territorio:
    para eso están las herramientas de analítica. NO reintentes con la misma
    consulta reformulada si devuelve vacío.

    consulta: en el idioma de la pregunta, específica, sin comillas.
    fenomenos: 1 = IA militar, 2 = espacial, 3 = territorial. None busca en todos.
    k: entre 3 y 10.

    Ejemplo: buscar_corpus("capacidades antisatélite de China", fenomenos=[2], k=6)
    """
```

Por dentro es `retriever.search(consulta, n_fragments=k)`. El singleton lo expone Juanes en `deps.py`.

**Higiene de tokens, importante**: `search()` devuelve `_row` y `_score` en cada fragmento. Devuelve al modelo **solo** `doc_id, chunk_id, titulo, fenomeno, observatorio, idioma, texto`. `_row` te sirve a ti para leer `retriever.meta[fila]`, pero al modelo no le aporta nada y son cientos de tokens de ruido por turno.

**Filtro por fenómeno**: el `Retriever` no tiene filtro duro, solo un prior suave. Si necesitas filtrar de verdad, filtra la lista fusionada por `retriever.meta[i]["fenomeno"]` antes de agregar. Es fácil, pero hazlo en tu capa, no dentro de `codefest/src/`.

### `perfil_documento`

```python
@tool
def perfil_documento(doc_id: str) -> dict:
    """Devuelve la ficha de un documento: título, observatorio, fenómeno, idioma,
    formato, número de fragmentos y un resumen extractivo de sus primeros fragmentos.

    Úsala cuando el usuario pregunte por un documento concreto que ya apareció citado.
    NO la uses para buscar documentos: para eso está buscar_corpus.

    doc_id: identificador exacto tipo "F1-AIINDEX-056". No inventes doc_ids.
    """
```

### `expandir_entidad`

```python
@tool
def expandir_entidad(entidad: str, saltos: int = 1, max_nodos: int = 30) -> dict:
    """Devuelve las entidades relacionadas con una dada en el grafo de conocimiento,
    con el tipo de relación, su peso y los chunk_id que sirven de evidencia.

    Úsala cuando la pregunta sea sobre vínculos entre actores, por ejemplo qué grupos
    operan en un territorio o qué organizaciones se relacionan con una tecnología.

    NO la uses para preguntas factuales de un solo documento. NO pidas saltos > 2:
    el grafo tiene 331.721 aristas y explota.

    entidad: nombre canónico. Si no lo sabes exacto, usa buscar_corpus primero.
    """
```

**No escribas la lógica de vecindad desde cero.** Está en `codefest/scripts/15_grafo_html.py:40`, funciones `subgrafo()` y `podar_aristas()`. Cópialas a tu módulo y adáptalas. Reciben el `nx.DiGraph` que ya vive en `retriever.graph.graph`.

Atributos de arista disponibles: `relacion`, `peso`, `n_documentos`, `evidencia_chunks`. **El 100% de las aristas tiene evidencia trazable a `chunk_id`**, y eso es oro para el pitch: cada afirmación del grafo se puede respaldar con el fragmento de donde salió.

---

## 22:30-00:30 · El ETL, que es donde está el Reto 2

`backend/app/datos/preparar.py` corre una vez y escribe Parquet en `datos/derivados/`. Los endpoints leen Parquet, nunca recalculan.

### Alertas tempranas → `alertas.parquet`

363 alertas en `codefest/data/docs.jsonl`, campo `extra`.

**Ojo con esto**: `extra` contiene `{codigo_alerta, tipo_alerta, municipios}` y el campo `fecha` está **vacío en las 363**. Pero `codigo_alerta` tiene formato `NNN-YY` y decodifica el año sin ambigüedad. Verificado: 2017:1, 2018:86, 2019:56, 2020:54, 2021:29, 2022:34, 2023:39, 2024:27, 2025:20, 2026:17.

`municipios` parte por `;` en bloques con forma `Muni1, Muni2 (Departamento)`. Salen unos 602 municipios y 33 departamentos.

`tipo_alerta`: Inminencia 197, Estructural 166.

Esquema objetivo: `(doc_id, codigo_alerta, anio, tipo_alerta, departamento, municipio)`, una fila por municipio. **Es una serie temporal georreferenciada de alertas 2017-2026**, y es el activo más vistoso que tenemos para el tablero.

### Territorio → `territorio.parquet`

`CORPUS.../F3_Dinamicas_Territoriales/Amazon_Underworld/AMAZONUW_amazonunderworld-data.csv`, 4.369 filas.

Columnas que importan: `au_country` (Brasil 778, Colombia 87, Bolivia 40, Ecuador 40, Perú 32, Venezuela 22), **`b_ADM1_PCODE` y `b_ADM2_PCODE`** que son códigos HDX estándar y se unen directo a cualquier GeoJSON público, `au_area_km2`, `au_population`, y presencia de 10 grupos armados (`grupo_ELN`, `grupo_EMC`, `grupo_CDF_AGC`, `grupo_Los_Lobos`, `grupo_PCC`, ...) en 662 filas con al menos un grupo.

**No hay que geocodificar nada.** Los PCODEs ya están. Esto es un coroplético multipaís listo.

### Corpus → `corpus.parquet`

Agregados desde `metadata.jsonl` para los KPI del tablero: conteos por fenómeno, observatorio, idioma, formato. Es un `groupby`, pero léelo una vez y guárdalo: el JSONL son 171 MB.

### Opcional, si sobra tiempo a las 22:00: `grafo_compacto.parquet`

`nx.read_graphml()` sobre 107 MB tarda entre 60 y 150 segundos y come varios GB. Si emites `(origen, destino, relacion, peso, evidencia_chunks)` a Parquet, son 331.721 filas y unos 30 MB, y las consultas de vecindad de 1 a 2 saltos pasan a SQL con DuckDB: unos 5 ms y 100 MB de RAM.

Para lo que las tools realmente necesitan esto es **estrictamente mejor que networkx**, y libera memoria en la máquina que además corre Coolify. Si el reloj lo permite, hazlo.

---

## Reto 2 · Las tools de analítica

Todas leen Parquet o DuckDB. **Ninguna devuelve texto del corpus**: eso es del investigador, no del analista.

```python
serie_temporal_alertas(departamento=None, tipo=None, desde=None, hasta=None) -> dict
cobertura_territorial(pais=None, nivel="ADM1") -> dict
presencia_grupos_armados(grupo=None, pais=None) -> dict
distribucion_corpus(por="fenomeno") -> dict
```

Devuelven series y tablas compactas, máximo unas 40 filas, porque van al contexto del `narrador_visual`. Si devuelves 4.000 filas te comes el presupuesto en un turno.

---

## Endpoints del tablero

```
GET /v1/analytics/overview            → KPIs
GET /v1/analytics/alertas             → serie temporal más geo
GET /v1/analytics/territorio          → coroplético por ADM1 o ADM2
GET /v1/analytics/grafo/{entidad}     → subgrafo para Three.js
GET /v1/documentos/{doc_id}           → metadata y fragmentos
```

Juanda consume estos. Acuerda con él el esquema exacto a las 21:00 y no lo cambies después sin avisarle.

---

## Tus hitos

| Hora | Qué tiene que estar |
|---|---|
| **22:30** | Tools mergeadas con firmas definitivas. Pueden devolver datos falsos. |
| 23:00 | `buscar_corpus` real sobre el Retriever vivo |
| **00:30** | `expandir_entidad` funcionando, ETL de alertas y territorio en Parquet |
| 08:30-11:00 | Endpoints de analítica contra los Parquet |

---

## Datos con los que no puedes contar

- **`fecha` está vacía en el 96,5% de los fragmentos.** No construyas nada que la asuma.
- **No hay campo de país ni de ubicación en `metadata.jsonl`.** La geografía sale del gazetteer, de las alertas y de Amazon Underworld.
- **`entidad_fragmentos.json` está truncado a 400 fragmentos por entidad**, así que los conteos saturan. No lo uses como métrica de frecuencia.
- **El gazetteer cubre bien Colombia y la Amazonía, no el mundo.** Los 5 países son Bolivia, Brasil, Ecuador, Perú y Venezuela. Para F1 y F2 la geografía relevante es EE.UU., China, Rusia y la UE, y ahí no hay gazetteer. Los 2.907 nodos `LUGAR` del grafo son el punto de partida, pero están sin normalizar.
