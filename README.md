# CODEFEST AD ASTRA 2026 — Reto Clasificatorio, Etapa 1

Motor de búsqueda semántica sobre 1.826 documentos de fuentes abiertas. Para cada
una de las 50 consultas devuelve los 3 documentos y los 10 fragmentos más
relevantes.

**Ningún modelo generativo interviene en ninguna etapa.** La recuperación opera
exclusivamente sobre vectores, puntuaciones de similitud coseno y metadata,
conforme a las Secciones 4.2 y 8.3 de la especificación.

## Ejecutar la entrega

La base vectorial no cabe en el repositorio: siete archivos superan el límite de
100 MB por archivo de GitHub. Está publicada como Release, en este mismo
repositorio.

```bash
git clone https://github.com/Jdtorres59/Hackathon-ad-astra.git
cd Hackathon-ad-astra/codefest/entrega
mkdir -p base_vectorial && cd base_vectorial

BASE=https://github.com/Jdtorres59/Hackathon-ad-astra/releases/download/base-vectorial-v1
for f in encoder_granite encoder_bge_m3 encoder_e5_large grafo; do
  curl -L -o "$f.tar" "$BASE/$f.tar" && tar -xf "$f.tar" && rm "$f.tar"
done

cd ..
pip install -r requirements.txt
python generador.py
```

Son 1,6 GB de descarga. `generador.py` sin argumentos lee `consultas.jsonl`,
consulta los índices y reescribe `resultados.jsonl`; al terminar valida su propia
salida contra el esquema de la Sección 9.3 y devuelve código distinto de cero si
algo no cumple. Tarda menos de un minuto una vez cargados los modelos.

Los pesos de los tres encoders no se incluyen en el Release porque cada
`model.safetensors` supera el límite de 2 GB por asset. `generador.py` los
descarga de HuggingFace la primera vez; son públicos y de licencia permisiva
(Apache 2.0 y MIT). Si se prefiere ejecutar sin conexión, basta con colocarlos en
`codefest/entrega/modelos/`.

## Qué hay en el repositorio

```
codefest/entrega/           la entrega
  resultados.jsonl          50 líneas, una por consulta
  generador.py              script de reproducción
  informe_tecnico.pdf       decisiones de diseño (6 páginas)
  consultas.jsonl           las 50 consultas de evaluación
  requirements.txt          dependencias con versiones fijadas
  base_vectorial/           no versionado: se rellena desde el Release

codefest/entrega/lib/       no versionado: es una copia de src/codefest que
                            genera 08_empaquetar.py. Al clonar no existe, y
                            generador.py usa src/codefest directamente.

codefest/src/codefest/      la librería
codefest/scripts/           el pipeline completo, de corpus a entrega
codefest/ESTADO.md          bitácora: decisiones, fallos encontrados y medidas
codefest/DIAGNOSTICO.md     diagnóstico previo a la entrega
```

## Reconstruir desde el corpus

```bash
bash codefest/scripts/run_all.sh                 # todo
bash codefest/scripts/run_all.sh --desde grafo   # desde un paso
```

Requiere el corpus original en `CORPUS CODEFEST AD ASTRA 2026/`, junto a
`codefest/`.

## Cómo se verificó

`bash codefest/scripts/11_prueba_jurado.sh` crea un entorno virtual limpio,
instala solo lo que declara `requirements.txt`, copia la entrega fuera del árbol
de desarrollo y ejecuta `python generador.py` sin argumentos. Después repite la
ejecución simulando una máquina sin GPU. La salida se reproduce byte a byte en
los dos casos.

Ese último paso no es decorativo: durante la revisión final se descubrió que la
entrega moría con SIGSEGV en CPU —los runtimes de OpenMP de `faiss` y `torch`
chocaban— y que, una vez viva, la media precisión de la GPU cambiaba el ranking
de 15 de las 50 consultas. Una prueba de reproducibilidad que corre en una sola
máquina no prueba reproducibilidad. Está contado en `codefest/ESTADO.md`.

## Identificador de documento

El campo `doc_id` de `resultados.jsonl` es el **DOC_ID oficial del inventario**
`Indice_Datos_Codefest.xlsx`, con la forma `F1-AIINDEX-001`. Cada línea de
`metadata.jsonl` lleva además `fuente` (nombre del archivo original),
`ruta_relativa`, `doc_id_inventario` y `doc_id_secuencial`, por si la evaluación
usa otra convención.
