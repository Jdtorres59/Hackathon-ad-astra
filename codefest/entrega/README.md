# CODEFEST AD ASTRA 2026 - Etapa 1

Base de conocimiento vectorial y modulo de recuperacion.

## Antes de ejecutar: rellenar base_vectorial/

Los indices no caben en GitHub (siete archivos pasan de 100 MB). Estan
publicados como Release en el mismo repositorio. Desde este directorio:

```
mkdir -p base_vectorial && cd base_vectorial
BASE=https://github.com/Jdtorres59/Hackathon-ad-astra/releases/download/base-vectorial-v1
for f in encoder_granite encoder_bge_m3 encoder_e5_large grafo; do
  curl -L -o "$f.tar" "$BASE/$f.tar" && tar -xf "$f.tar" && rm "$f.tar"
done
cd ..
```

Son 1,6 GB. Si `base_vectorial/` ya trae los tres directorios `encoder_*` y
`grafo/`, este paso sobra.

## Ejecucion

```
pip install -r requirements.txt
python generador.py
```

`generador.py` sin argumentos equivale a:

```
python generador.py --consultas consultas.jsonl \
                    --base-vectorial ./base_vectorial \
                    --salida resultados.jsonl
```

Lee `consultas.jsonl`, consulta los indices FAISS de `base_vectorial/` y escribe
`resultados.jsonl` con 50 lineas en el esquema de la Seccion 9.3. Al terminar
valida el archivo contra ese esquema y devuelve codigo de salida distinto de
cero si algo no cumple.

Las consultas se codifican siempre en CPU y en fp32, no en el mejor dispositivo
disponible. La razon esta en `lib/codefest/encoders.py`: half precision cambia
el vector de la consulta y con el el orden del ranking, asi que la salida
dependeria de la maquina. Con esto, `resultados.jsonl` es reproducible en
cualquier equipo.

## Identificador de documento

El campo `doc_id` que aparece en `resultados.jsonl` y en `metadata.jsonl` es el
**DOC_ID oficial del inventario del corpus** (`Indice_Datos_Codefest.xlsx`), con
la forma `F1-AIINDEX-001`. Se eligio ese y no uno propio porque el ground truth
lo construyeron los organizadores sobre ese mismo inventario.

Si la evaluacion usa otra convencion, el mapeo no hay que reconstruirlo: cada
linea de `metadata.jsonl` lleva tambien

```
fuente               nombre del archivo original, p.ej. SIPRI_laws-v-0.pdf
ruta_relativa        ruta dentro del corpus entregado
doc_id_inventario    el mismo DOC_ID del inventario
doc_id_secuencial    numeracion propia alternativa (DOC-0001)
```

## Contenido

```
resultados.jsonl        50 lineas, una por consulta (q001..q050)
generador.py            script de reproduccion
informe_tecnico.pdf     decisiones de diseno
consultas.jsonl         consultas usadas para generar resultados.jsonl
requirements.txt        dependencias con versiones fijadas
lib/codefest/           codigo de la libreria que usa generador.py
base_vectorial/
  encoder_<slug>/
    index.faiss         indice FAISS (faiss.read_index)
    metadata.jsonl      una linea por vector, en el orden de los IDs internos
    centroides_fenomeno.npy   3 centroides tematicos (prior suave)
    centroides_documento.npy  un centroide por documento, para podar duplicados
    documentos.json     doc_id en el orden de centroides_documento.npy
  grafo/
    grafo.graphml       grafo de conocimiento (networkx.read_graphml)
    entidad_fragmentos.json   indice entidad -> fragmentos
    gazetteer.json      alias de entidad usados al consultar el grafo
```

## Modelos

Si el directorio `modelos/` esta presente, los pesos se cargan desde ahi y
`generador.py` no necesita conexion a internet. No viajan en el Release de
GitHub porque cada `model.safetensors` supera el limite de 2 GB por asset, asi
que en una copia clonada del repositorio el script los descarga de HuggingFace
la primera vez. Son publicos y de licencia permisiva.

Encoders utilizados (todos arquitectura encoder, licencia permisiva):

- `ibm-granite/granite-embedding-311m-multilingual-r2` (Apache 2.0)
- `BAAI/bge-m3` (MIT)
- `intfloat/multilingual-e5-large` (MIT)
