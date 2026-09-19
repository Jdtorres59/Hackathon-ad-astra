# Frente C — Herramientas y datos · Joseph

> Actualizado tras la especificación técnica. Lee `AGENTS.md`, `CAMBIOS_TRAS_ESPECIFICACION.md` y `CONTRATO_JURADO.md`.

## Lo que cambió respecto de lo que leíste antes

1. **Hay una base de datos SQL que no teníamos.** ADL dispone un Drive con el corpus completo, los archivos fuente originales y **una base SQL específica para el Reto 2**: `https://shorturl.at/YPQg0`
2. **La trazabilidad a `doc_id` y `chunk_id` es requisito explícito**, no buena práctica. Todo dato mostrado en el tablero debe rastrearse a su origen.
3. **Prohibidos los datos simulados** en la versión desplegada para evaluación.
4. **Prohibido inventar scores.** Nada de "índice de amenaza" calculado ad hoc. Conteos, frecuencias y agregaciones sí.
5. Tus endpoints ya no alimentan un tablero con filtros: alimentan **componentes que un agente activa dinámicamente**.

---

## Lo primero, antes que nada

**Baja la base SQL del Drive y mírala.** `https://shorturl.at/YPQg0`

Puede hacer innecesaria la mitad del ETL que teníamos planeado, o puede traer la señal temporal y geográfica que al corpus le falta. Es quince minutos que pueden ahorrar tres horas.

Reporta al equipo: qué tablas trae, qué columnas, cuántas filas, y si tiene fechas y ubicaciones normalizadas.

## Lo segundo

**Verifica que el motor de recuperación arranca en tu máquina.** El patrón exacto está en `AGENTS.md` y tiene tres trampas que cuestan horas si se ignoran. Reporta cuánto tarda en cargar y cuánta RAM consume: eso determina decisiones del resto del equipo.

---

## Tus archivos

```
backend/app/herramientas/corpus.py      ← buscar_corpus, perfil_documento
backend/app/herramientas/grafo.py       ← expandir_entidad
backend/app/herramientas/datos.py       ← tools de analítica
backend/app/datos/preparar.py           ← ETL
backend/app/routers/analytics.py        ← endpoints que pueblan los componentes
```

---

## Tu regla de oro

**No reimplementes nada de la Etapa 1.** Búsqueda semántica, chunking y consulta de grafo ya existen en `codefest/src/codefest/`. Búscalo antes de escribir.

---

## 21:00-22:30 · Firmas definitivas

Jair está bloqueado hasta que existan. **Mergea con las firmas finales aunque devuelvan datos falsos.**

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

Por dentro es `retriever.search(consulta, n_fragments=k)`.

**Higiene de tokens**: devuelve al modelo solo `doc_id, chunk_id, titulo, fenomeno, observatorio, idioma, texto`. Nada de `_row` ni `_score`. Son cientos de tokens de ruido por turno, y los tokens son el 40% del bloque de eficiencia.

**El `texto` de cada fragmento es lo que va a `evaluacion.retrieval_context`** en la respuesta al evaluador. Que salga limpio.

### `expandir_entidad`

No escribas la vecindad desde cero. Está en `codefest/scripts/15_grafo_html.py:40`, funciones `subgrafo()` y `podar_aristas()`. Reciben el `nx.DiGraph` que ya vive en `retriever.graph.graph`.

**El 100% de las aristas tiene `evidencia_chunks`**, así que la trazabilidad sale gratis. Devuélvela siempre: ahora es requisito.

### `perfil_documento`

Ficha de un documento por `doc_id` exacto. Para cuando el usuario pregunta por algo que ya apareció citado.

---

## Las tools de analítica

Estas son las que usa `agente_visualizacion`, y lo que se evalúa es si activa el componente correcto **con los datos correctos**. Si tu tool devuelve mal los datos, el agente falla aunque elija bien.

```python
serie_temporal(metrica, fenomeno=None, departamento=None, desde=None, hasta=None) -> dict
cobertura_territorial(pais=None, nivel="ADM1", metrica=...) -> dict
presencia_grupos_armados(grupo=None, pais=None) -> dict
distribucion_corpus(por="fenomeno") -> dict
matriz_coocurrencia(eje_x, eje_y, top_n=20) -> dict
```

Todas devuelven tablas compactas, **máximo unas 40 filas**, porque van al contexto del agente. Si devuelves 4.000 filas te comes el presupuesto en un turno.

Y todas devuelven **trazabilidad**: la lista de `doc_id` y `chunk_id` que sustentan los números.

---

## El ETL

`backend/app/datos/preparar.py` corre una vez y escribe Parquet en `datos/derivados/`. Los endpoints leen Parquet, nunca recalculan.

**Decide primero si la base SQL de ADL ya trae esto.** Si lo trae, sáltate lo que corresponda.

### Alertas tempranas

363 alertas en `codefest/data/docs.jsonl`, campo `extra`.

Ojo: `extra` trae `{codigo_alerta, tipo_alerta, municipios}` y **`fecha` está vacío en las 363**. Pero `codigo_alerta` tiene formato `NNN-YY` y decodifica el año. Verificado: 2017:1, 2018:86, 2019:56, 2020:54, 2021:29, 2022:34, 2023:39, 2024:27, 2025:20, 2026:17.

`municipios` parte por `;` en bloques `Muni1, Muni2 (Departamento)`. Salen unos 602 municipios y 33 departamentos. `tipo_alerta`: Inminencia 197, Estructural 166.

Esquema: `(doc_id, chunk_id, codigo_alerta, anio, tipo_alerta, departamento, municipio)`. **Incluye `doc_id` y `chunk_id` desde el principio**, porque la trazabilidad es requisito.

### Territorio

`CORPUS.../F3_Dinamicas_Territoriales/Amazon_Underworld/AMAZONUW_amazonunderworld-data.csv`, 4.369 filas.

`au_country` (6 países), **`b_ADM1_PCODE` y `b_ADM2_PCODE`** que son códigos HDX estándar unibles a GeoJSON público, `au_area_km2`, `au_population`, y presencia de 10 grupos armados en 662 filas. **No hay que geocodificar nada.**

### Corpus

Agregados desde `metadata.jsonl` para las distribuciones. Es un `groupby`, pero léelo una vez: son 171 MB.

### Grafo compacto, si hay tiempo

`nx.read_graphml()` sobre 107 MB tarda 60-150 s y come varios GB. Emitir `(origen, destino, relacion, peso, evidencia_chunks)` a Parquet son 331.721 filas, unos 30 MB, y las consultas de vecindad pasan a SQL con DuckDB: unos 5 ms. Para lo que las tools necesitan es estrictamente mejor.

---

## Lo que está prohibido

- **Datos simulados** en la versión desplegada. Ni de ejemplo, ni de relleno.
- **Scores inventados.** Nada de "índice de riesgo" o "nivel de amenaza" calculado ad hoc: la especificación lo llama *aparentar una autoridad analítica que el equipo no tiene*. Conteos, frecuencias y agregaciones sí son medibles y sí se muestran.

---

## Datos con los que no puedes contar

- **`fecha` está vacía en el 96,5% de los fragmentos.** No construyas nada que la asuma sin verificar.
- **No hay campo de país ni ubicación en `metadata.jsonl`.** La geografía sale del gazetteer, las alertas y Amazon Underworld. Y quizá de la base SQL de ADL.
- **`entidad_fragmentos.json` está truncado a 400 por entidad**: los conteos saturan. No lo uses como métrica de frecuencia.
- **El gazetteer cubre Colombia y la Amazonía, no el mundo.** Para F1 y F2 la geografía relevante es EE.UU., China, Rusia y la UE, y ahí no hay gazetteer.

---

## Hitos

| Hora | Qué |
|---|---|
| 20:30 | Base SQL descargada y reportada al equipo |
| 21:00 | Retriever verificado, tiempo y RAM reportados. Catálogo de componentes acordado |
| **22:30** | Tools mergeadas con firmas definitivas |
| 23:00 | `buscar_corpus` real |
| **00:30** | `expandir_entidad` y ETL en Parquet |
| 08:30-11:00 | Endpoints de analítica que pueblan los componentes |
