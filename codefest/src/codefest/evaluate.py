"""Arnés de evaluación sin ground truth.

El ground truth real no es público (Sección 10.1), así que la calidad se estima
con cuatro señales independientes:

1. `mini_gold`  — las ~11 preguntas etiquetadas que los organizadores dejaron
                  dentro del corpus en `FASE ORDENADA CODEFEST.xlsx`.
2. `known_item` — se usan fragmentos del propio corpus como pseudo-consultas y
                  se mide si el sistema recupera su documento de origen.
3. `title_probe`— se consulta con el título de cada documento y se mide su
                  posición. Es el proxy más directo de F1@3.
4. revisión manual del reporte HTML de las 50 consultas reales.

Además se implementan NDCG@10 y F1@3 tal como los define la Sección 10.2, para
poder puntuar contra cualquier conjunto etiquetado que tengamos.
"""

from __future__ import annotations

import math
import random
import re
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

from . import config

_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


# --------------------------------------------------------------------------- #
# Métricas oficiales (Sección 10.2)
# --------------------------------------------------------------------------- #


def dcg(relevancias: list[float]) -> float:
    return sum(r / math.log2(i + 1) for i, r in enumerate(relevancias, start=1))


def ndcg_at_k(relevancias: list[float], ideal: list[float], k: int = 10) -> float:
    """NDCG@k según las ecuaciones (8) y (9) de la especificación."""
    actual = dcg(relevancias[:k])
    best = dcg(sorted(ideal, reverse=True)[:k])
    return actual / best if best > 0 else 0.0


def f1_at_3(devueltos: list[str], relevantes: set[str], k: int = 3) -> float:
    """F1@3 según las ecuaciones (11)-(13). El denominador de R se limita a min(|D*|,k)."""
    devueltos = devueltos[:k]
    if not relevantes:
        return 0.0
    aciertos = len(set(devueltos) & relevantes)
    p = aciertos / max(len(devueltos), 1)
    r = aciertos / min(len(relevantes), k)
    return 2 * p * r / (p + r) if (p + r) > 0 else 0.0


# --------------------------------------------------------------------------- #
# Mini gold set dejado por los organizadores dentro del corpus
# --------------------------------------------------------------------------- #


def _read_sheets(xlsx: Path) -> list[list[list[str]]]:
    z = zipfile.ZipFile(xlsx)
    shared: list[str] = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{_NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{_NS}t")))

    sheets = []
    names = sorted(
        (n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n)),
        key=lambda x: int(re.search(r"\d+", x.split("/")[-1]).group()),
    )
    for sf in names:
        root = ET.fromstring(z.read(sf))
        rows = []
        for row in root.iter(f"{_NS}row"):
            vals = []
            for cell in row:
                t = cell.get("t")
                v = cell.find(f"{_NS}v")
                if v is not None:
                    vals.append(shared[int(v.text)] if t == "s" else (v.text or ""))
                elif cell.find(f"{_NS}is") is not None:
                    vals.append("".join(x.text or "" for x in cell.iter(f"{_NS}t")))
                else:
                    vals.append("")
            rows.append(vals)
        sheets.append(rows)
    return sheets


def load_mini_gold(path: Path | None = None) -> list[dict]:
    """[{'pregunta', 'fragmentos': [texto...], 'archivos': [nombre.pdf...]}, ...]

    Las filas del archivo llevan la pregunta solo en la primera de su grupo; las
    siguientes continúan la misma pregunta con más evidencia.
    """
    path = path or config.MINI_GOLD_XLSX
    if not Path(path).exists():
        return []

    out: list[dict] = []
    for rows in _read_sheets(Path(path)):
        if not rows:
            continue
        header = [c.strip().upper() for c in rows[0]]
        try:
            i_preg = header.index("PREGUNTA")
            i_frag = header.index("FRAGMENTO")
            i_doc = header.index("DOCUMENTO")
        except ValueError:
            continue

        # En la hoja F1 la columna de numeración no tiene nombre en la cabecera,
        # así que las filas traen una celda más y los índices van desplazados.
        ancho_filas = max((len(r) for r in rows[1:]), default=len(header))
        desfase = max(0, ancho_filas - len(header))
        i_preg += desfase
        i_frag += desfase
        i_doc += desfase

        actual: dict | None = None
        for row in rows[1:]:
            def cell(i: int) -> str:
                return row[i].strip() if i < len(row) else ""

            pregunta, fragmento, documento = cell(i_preg), cell(i_frag), cell(i_doc)
            if pregunta:
                if actual and actual["fragmentos"]:
                    out.append(actual)
                actual = {"pregunta": pregunta, "fragmentos": [], "archivos": []}
            if actual is None:
                continue
            if fragmento:
                actual["fragmentos"].append(fragmento)
            if documento:
                # La celda mezcla nombre de archivo y el chunk_id interno de los
                # organizadores, en líneas separadas
                for parte in documento.split("\n"):
                    parte = parte.strip()
                    if parte.lower().endswith((".pdf", ".json", ".csv", ".xlsx", ".txt")):
                        actual["archivos"].append(parte)
        if actual and actual["fragmentos"]:
            out.append(actual)
    return out


def normalize_filename(name: str) -> str:
    """Normaliza para comparar el nombre original con el estandarizado del corpus.

    Los organizadores citan `Informe-Semestral-36-MAPPOEA-1.pdf`; en disco está
    como `MAPPOEA_informe-semestral-36-mappoea-1.pdf`.
    """
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.lower().rsplit(".", 1)[0]
    return re.sub(r"[^a-z0-9]", "", name)


def match_docs_by_filename(archivos: list[str], meta_por_doc: dict[str, str]) -> set[str]:
    """Resuelve nombres de archivo citados a doc_id del corpus.

    `meta_por_doc` es {doc_id: nombre_de_archivo}.
    """
    normalizados = {doc_id: normalize_filename(f) for doc_id, f in meta_por_doc.items()}
    encontrados: set[str] = set()
    for archivo in archivos:
        objetivo = normalize_filename(archivo)
        if not objetivo:
            continue
        for doc_id, norm in normalizados.items():
            if norm.endswith(objetivo) or objetivo.endswith(norm) or objetivo in norm:
                encontrados.add(doc_id)
                break
    return encontrados


# --------------------------------------------------------------------------- #
# Solapamiento textual, para juzgar si un fragmento recuperado cubre el gold
# --------------------------------------------------------------------------- #

_TOKEN = re.compile(r"\w+", re.UNICODE)


def token_recall(gold: str, candidato: str) -> float:
    """Proporción de tokens del fragmento gold presentes en el candidato."""
    g = Counter(t.lower() for t in _TOKEN.findall(gold))
    c = Counter(t.lower() for t in _TOKEN.findall(candidato))
    if not g:
        return 0.0
    cubiertos = sum(min(n, c.get(t, 0)) for t, n in g.items())
    return cubiertos / sum(g.values())


# --------------------------------------------------------------------------- #
# Sondas automáticas
# --------------------------------------------------------------------------- #


def known_item_probe(retriever, n: int = 300, seed: int = 0, k: int = 3) -> dict:
    """Usa fragmentos del corpus como pseudo-consultas y mide si vuelve su documento.

    Detecta índices desalineados, encoders mal aplicados y prefijos olvidados.

    Además calcula un **NDCG@10 a nivel de fragmento**, que es la única
    aproximación con resolución estadística que podemos construir a la métrica
    con la que de verdad nos van a calificar: el ground truth no es público, y
    el mini gold tiene ocho preguntas. Aquí la relevancia es binaria y conocida
    —vale 1 el fragmento que originó la pseudo-consulta y 0 todos los demás—,
    así que el IDCG es el de un único acierto en la primera posición y el NDCG
    se reduce a 1/log2(posición+1). Mide exactamente lo que premia NDCG@10:
    colocar lo relevante arriba, no solo dentro de la lista.

    Ojo con lo que NO mide: una pseudo-consulta copiada del propio fragmento es
    mucho más fácil que una pregunta en lenguaje natural, así que el valor
    absoluto es optimista. Sirve para comparar configuraciones entre sí y para
    detectar roturas, no para pronosticar el puntaje.
    """
    rng = random.Random(seed)
    candidatos = [i for i, m in enumerate(retriever.meta) if m.get("n_palabras", 0) >= 60]
    muestra = rng.sample(candidatos, min(n, len(candidatos)))

    aciertos_doc = 0
    rr = 0.0
    ndcgs: list[float] = []
    aciertos_frag = 0
    for i in muestra:
        m = retriever.meta[i]
        consulta = " ".join(m["texto"].split()[:45])
        hits = retriever.search(consulta, n_documents=k, expand=False, use_fenomeno_prior=False)
        docs = [d["doc_id"] for d in hits["documents"]]
        if m["doc_id"] in docs:
            aciertos_doc += 1
            rr += 1.0 / (docs.index(m["doc_id"]) + 1)

        # Relevancia binaria: solo el fragmento de origen cuenta.
        relevancias = [1.0 if f["chunk_id"] == m["chunk_id"] else 0.0
                       for f in hits["fragments"][:10]]
        if any(relevancias):
            aciertos_frag += 1
        ndcgs.append(ndcg_at_k(relevancias, [1.0], k=10))

    total = len(muestra)
    return {
        "n": total,
        f"recall@{k}_doc": aciertos_doc / max(total, 1),
        "mrr_doc": rr / max(total, 1),
        "recall@10_frag": aciertos_frag / max(total, 1),
        "ndcg@10_frag": sum(ndcgs) / max(len(ndcgs), 1),
    }


def fenomeno_esperado(query_id: str) -> int | None:
    """Fenómeno al que pertenece cada consulta del extracto de 50.

    No es ground truth oficial: sale de leer las cincuenta preguntas, que están
    agrupadas por tema sin excepción (q001–q016 sobre IA y defensa, q017–q032
    sobre seguridad espacial, q033–q050 sobre dinámicas territoriales). Sirve
    como señal de coherencia: si los documentos recuperados para una consulta de
    órbita baja vienen del fenómeno de dinámicas territoriales, algo va mal.
    """
    try:
        n = int(query_id.lstrip("qQ"))
    except ValueError:
        return None
    if 1 <= n <= 16:
        return 1
    if 17 <= n <= 32:
        return 2
    if 33 <= n <= 50:
        return 3
    return None


def fenomeno_probe(retriever, consultas: list[dict]) -> dict:
    """Mide si los documentos recuperados caen en el fenómeno temático esperado."""
    fen_por_doc: dict[str, int] = {}
    for m in retriever.meta:
        fen_por_doc.setdefault(m["doc_id"], m["fenomeno"])

    aciertos_top1 = 0
    coincidencias = 0
    totales = 0
    discrepancias: list[tuple[str, int, list[int]]] = []

    for q in consultas:
        esperado = fenomeno_esperado(q["query_id"])
        if esperado is None:
            continue
        hits = retriever.search(q["texto"], expand=False)
        fens = [fen_por_doc.get(d["doc_id"], 0) for d in hits["documents"]]
        if not fens:
            continue
        totales += 1
        aciertos_top1 += int(fens[0] == esperado)
        coincidencias += sum(1 for f in fens if f == esperado) / len(fens)
        if fens[0] != esperado:
            discrepancias.append((q["query_id"], esperado, fens))

    return {
        "n": totales,
        "top1_en_fenomeno": aciertos_top1 / max(totales, 1),
        "proporcion_en_fenomeno": coincidencias / max(totales, 1),
        "discrepancias": discrepancias,
    }


def title_probe(retriever, n: int = 200, seed: int = 0, k: int = 3) -> dict:
    """Consulta con el título de cada documento y mide si el documento aparece en el top-k."""
    rng = random.Random(seed)
    titulos: dict[str, str] = {}
    for m in retriever.meta:
        t = (m.get("titulo") or "").strip()
        if len(t) >= 15 and m["doc_id"] not in titulos:
            titulos[m["doc_id"]] = t

    muestra = rng.sample(sorted(titulos), min(n, len(titulos)))
    aciertos = 0
    for doc_id in muestra:
        hits = retriever.search(titulos[doc_id], n_documents=k, expand=False, use_fenomeno_prior=False)
        if doc_id in {d["doc_id"] for d in hits["documents"]}:
            aciertos += 1
    return {"n": len(muestra), f"recall@{k}_doc": aciertos / max(len(muestra), 1)}
