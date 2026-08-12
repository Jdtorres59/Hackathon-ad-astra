"""Módulo de recuperación (Sección 8 de la especificación).

Flujo: consulta -> mismos encoders del índice -> búsqueda FAISS por índice ->
fusión de listas -> post-filtros sobre metadata -> dos niveles de resultado
(fragmentos y documentos).

En ninguna etapa interviene un modelo generativo. Todo opera sobre vectores,
puntuaciones de similitud y metadata, como exige la Sección 8.3.
"""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from . import config
from .fusion import fuse

CENTROIDS_FILE = "centroides_fenomeno.npy"
DOC_CENTROIDS_FILE = "centroides_documento.npy"
DOC_IDS_FILE = "documentos.json"


def word_count(text: str) -> int:
    """Mismo criterio que se aplica al límite de 250 palabras de la salida."""
    return len(text.split())


class Retriever:
    """Motor de recuperación sobre una o varias bases vectoriales."""

    def __init__(
        self,
        base_dir: Path | str | None = None,
        slugs: list[str] | None = None,
        *,
        use_graph: bool | None = None,
        device: str | None = None,
        verbose: bool = False,
    ):
        import faiss

        from .index_build import limitar_hilos_openmp

        limitar_hilos_openmp()

        self.base_dir = Path(base_dir) if base_dir else config.BASE_VECTORIAL_DIR
        self.verbose = verbose
        self.device = device

        available = [s for s in (slugs or [e["slug"] for e in config.ENCODERS])
                     if (self.base_dir / f"encoder_{s}" / "index.faiss").exists()]
        if not available:
            raise FileNotFoundError(f"No se encontró ningún índice en {self.base_dir}")
        self.slugs = available

        self.indexes: dict[str, "faiss.Index"] = {}
        self.centroids: dict[str, np.ndarray] = {}
        self.meta: list[dict] = []

        for i, slug in enumerate(self.slugs):
            folder = self.base_dir / f"encoder_{slug}"
            self.indexes[slug] = faiss.read_index(str(folder / "index.faiss"))
            if i == 0:
                with open(folder / "metadata.jsonl", encoding="utf-8") as fh:
                    self.meta = [json.loads(line) for line in fh if line.strip()]
            cpath = folder / CENTROIDS_FILE
            if cpath.exists():
                self.centroids[slug] = np.load(cpath)

        n = len(self.meta)
        for slug, index in self.indexes.items():
            if index.ntotal != n:
                raise ValueError(f"{slug}: {index.ntotal} vectores vs {n} fragmentos de metadata")

        # (doc_id, posicion) -> fila, para expandir fragmentos con sus vecinos
        self.by_doc_pos: dict[tuple[str, int], int] = {
            (m["doc_id"], m["posicion"]): i for i, m in enumerate(self.meta)
        }

        # Idioma mayoritario de cada documento: distingue una traducción de una
        # edición posterior, que a nivel de vector son indistinguibles (las dos
        # dan coseno 0,956).
        conteo_idioma: dict[str, Counter] = defaultdict(Counter)
        for m in self.meta:
            conteo_idioma[m["doc_id"]][m.get("idioma") or "und"] += 1
        self.doc_idioma: dict[str, str] = {
            d: c.most_common(1)[0][0] for d, c in conteo_idioma.items()
        }

        # Un vector por documento, para descartar copias y traducciones del mismo
        # contenido en el top-3. Se cargan los de todos los encoders y se exige
        # acuerdo entre ellos: la densidad del espacio varía mucho de un modelo a
        # otro (con umbral 0,98 granite marca 1.750 pares casi idénticos entre
        # 1.826 documentos y bge_m3 solo 175), así que fiarse de uno solo podaría
        # de más. Si los archivos no están, la poda se desactiva sola.
        self.doc_centroids: dict[str, np.ndarray] = {}
        self.doc_index: dict[str, int] = {}
        for slug in self.slugs:
            carpeta = self.base_dir / f"encoder_{slug}"
            dc, di = carpeta / DOC_CENTROIDS_FILE, carpeta / DOC_IDS_FILE
            if not (dc.exists() and di.exists()):
                continue
            self.doc_centroids[slug] = np.load(dc)
            if not self.doc_index:
                with open(di, encoding="utf-8") as fh:
                    self.doc_index = {d: k for k, d in enumerate(json.load(fh))}

        self.graph = None
        want_graph = config.USE_GRAPH if use_graph is None else use_graph
        if want_graph:
            self._load_graph()

    # ------------------------------------------------------------------ #
    # Carga perezosa de componentes opcionales
    # ------------------------------------------------------------------ #

    def _load_graph(self) -> None:
        graph_file = self.base_dir / "grafo" / "grafo.graphml"
        if not graph_file.exists():
            return
        try:
            from .graph.query import GraphRetriever

            self.graph = GraphRetriever(graph_file, self.meta)
            if self.verbose:
                print(f"  grafo cargado: {self.graph.n_nodes} entidades, {self.graph.n_edges} relaciones")
        except Exception as exc:  # el grafo es bonus: nunca debe tumbar la recuperación
            if self.verbose:
                print(f"  aviso: no se pudo cargar el grafo ({exc})")
            self.graph = None

    # ------------------------------------------------------------------ #
    # Recuperación
    # ------------------------------------------------------------------ #

    def _dense_lists(self, query: str, topk: int) -> tuple[list[list[tuple[int, float]]], dict[str, np.ndarray]]:
        from .encoders import encode_texts

        lists = []
        qvecs = {}
        for slug in self.slugs:
            qv = encode_texts(slug, [query], is_query=True, device=self.device)
            qvecs[slug] = qv[0]
            scores, ids = self.indexes[slug].search(qv, topk)
            lists.append([(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i >= 0])
        return lists, qvecs

    def _fenomeno_prior(self, qvecs: dict[str, np.ndarray]) -> dict[int, float] | None:
        """Peso por fenómeno a partir de la similitud consulta-centroide.

        Post-filtro suave sobre metadata, permitido por la Sección 8.7. Nunca
        descarta: algunas consultas cruzan fenómenos (q027, IA en operaciones
        espaciales, vive entre F1 y F2).
        """
        if not self.centroids or config.FENOMENO_BOOST <= 0:
            return None
        sims = np.zeros(3, dtype=np.float64)
        for slug, cents in self.centroids.items():
            qv = qvecs.get(slug)
            if qv is None or cents.shape[0] != 3:
                continue
            sims += cents @ qv
        if not sims.any():
            return None
        # softmax con temperatura baja: destaca el fenómeno dominante sin anular los otros
        exp = np.exp((sims - sims.max()) / 0.05)
        weights = exp / exp.sum()
        return {f: 1.0 + config.FENOMENO_BOOST * float(weights[f - 1]) for f in (1, 2, 3)}

    def search(
        self,
        query: str,
        *,
        topk: int | None = None,
        fusion_method: str = "rrf",
        n_documents: int | None = None,
        n_fragments: int | None = None,
        max_per_doc: int | None = None,
        expand: bool = True,
        expand_target: int | None = None,
        use_fenomeno_prior: bool = True,
        doc_tail_weight: float | None = None,
        doc_tail_n: int | None = None,
        doc_dedup_cos: float | None = None,
    ) -> dict:
        topk = topk or config.TOPK_PER_INDEX
        n_documents = n_documents or config.N_DOCUMENTS_OUT
        n_fragments = n_fragments or config.N_FRAGMENTS_OUT
        max_per_doc = config.MAX_CHUNKS_PER_DOC if max_per_doc is None else max_per_doc

        lists, qvecs = self._dense_lists(query, topk)
        weights = [1.0] * len(lists)

        if self.graph is not None:
            graph_list = self.graph.search(query, topk=config.GRAPH_MAX_CHUNKS)
            if graph_list:
                lists.append(graph_list)
                # El grafo aporta evidencia por entidades, no por semántica: pesa
                # menos que un índice denso para que no arrastre la fusión.
                weights.append(config.GRAPH_WEIGHT)

        fused = fuse(lists, method=fusion_method, weights=weights)

        prior = self._fenomeno_prior(qvecs) if use_fenomeno_prior else None
        if prior:
            fused = sorted(
                ((i, s * prior.get(self.meta[i]["fenomeno"], 1.0)) for i, s in fused),
                key=lambda kv: -kv[1],
            )

        documents = self._aggregate_documents(fused, n_documents, doc_tail_weight, doc_tail_n, doc_dedup_cos)
        fragments = self._select_fragments(fused, n_fragments, max_per_doc, expand, expand_target)
        return {"documents": documents, "fragments": fragments}

    def _aggregate_documents(self, fused: list[tuple[int, float]], n: int,
                            tail_weight: float | None = None,
                            tail_n: int | None = None,
                            dedup_cos: float | None = None) -> list[dict]:
        """Agregación de fragmentos a documento (Sección 8.6).

        Puntuación del mejor fragmento más una contribución decreciente de los
        siguientes: premia a los documentos con varios pasajes relevantes sin
        dejar que un documento largo gane solo por volumen.

        El peso de la cola es delicado con puntuaciones RRF, que decaen muy poco
        (0,0164 en el puesto 1 frente a 0,0091 en el 50): una cola demasiado
        pesada hace que un documento con cinco fragmentos mediocres supere a uno
        con un único fragmento excelente, que es lo contrario de lo que premia
        F1@3. El valor se fija por ablación, no a ojo.
        """
        peso = config.DOC_AGG_TAIL_WEIGHT if tail_weight is None else tail_weight
        cuantos = config.DOC_AGG_TAIL_N if tail_n is None else tail_n

        por_doc: dict[str, list[float]] = defaultdict(list)
        mejor_fila: dict[str, int] = {}
        for idx, score in fused:
            doc_id = self.meta[idx]["doc_id"]
            por_doc[doc_id].append(score)
            mejor_fila.setdefault(doc_id, idx)  # `fused` ya viene ordenado

        scored = []
        for doc_id, scores in por_doc.items():
            scores.sort(reverse=True)
            head = scores[0]
            tail = sum(scores[1 : 1 + cuantos])
            scored.append((doc_id, head + peso * tail))

        scored.sort(key=lambda kv: -kv[1])

        umbral = config.DOC_DEDUP_COS if dedup_cos is None else dedup_cos
        if umbral <= 0 or umbral >= 1:
            elegidos = [(d, s) for d, s in scored[:n]]
        else:
            elegidos = self._sin_duplicados(scored, n, mejor_fila, umbral)

        return [
            {"rank": r, "doc_id": doc_id, "_score": score}
            for r, (doc_id, score) in enumerate(elegidos, start=1)
        ]

    def _sin_duplicados(self, scored: list[tuple[str, float]], n: int,
                        mejor_fila: dict[str, int], umbral: float) -> list[tuple[str, float]]:
        """Top-n de documentos evitando copias del mismo contenido.

        El corpus trae el mismo documento bajo nombres distintos (ILIA_2025 y
        ILIA_docuemnto-ilia-web son idénticos, coseno 1,000) y las mismas
        ediciones traducidas a varios idiomas (gcsr-2026-execsum-spa / -por /
        -fre). Sin esta poda, 34 de las 50 consultas gastaban dos de sus tres
        huecos en el mismo contenido, y F1@3 premia acertar tres documentos
        distintos.

        Se compara el vector del mejor fragmento de cada documento, no su texto:
        una traducción no comparte palabras con su original pero sí ocupa casi
        el mismo punto del espacio de un encoder multilingüe. Opera solo sobre
        vectores, como exige la Sección 8.3.
        """
        index = self.indexes[self.slugs[0]]
        elegidos: list[tuple[str, float]] = []
        vectores: list[list[np.ndarray]] = []
        ya_elegidos: list[str] = []

        def vectores_de(doc_id: str) -> list[np.ndarray] | None:
            """Un centroide por encoder; si no se precalcularon, el mejor fragmento."""
            k = self.doc_index.get(doc_id)
            if k is not None and self.doc_centroids:
                return [c[k] for c in self.doc_centroids.values()]
            fila = mejor_fila.get(doc_id)
            if fila is None:
                return None
            v = np.asarray(index.reconstruct(int(fila)), dtype=np.float32)
            return [v / (np.linalg.norm(v) or 1.0)]

        umbral_trad = max(config.DOC_DEDUP_COS_TRADUCCION, 0.0)

        def es_copia(a: list[np.ndarray], b: list[np.ndarray],
                     doc_a: str, doc_b: str) -> bool:
            """Copia literal, o traducción del mismo documento.

            Se exige que TODOS los encoders vean el parecido: la densidad del
            espacio varía mucho de un modelo a otro. Y por debajo de `umbral` solo
            se descarta si además cambia el idioma, porque a igual coseno una
            edición posterior en el mismo idioma es un documento distinto que el
            gold puede marcar como relevante por separado.
            """
            if all(float(x @ y) > umbral for x, y in zip(a, b)):
                return True
            if umbral_trad <= 0 or umbral_trad >= umbral:
                return False
            idioma_a, idioma_b = self.doc_idioma.get(doc_a), self.doc_idioma.get(doc_b)
            if not idioma_a or not idioma_b or idioma_a == idioma_b:
                return False
            return all(float(x @ y) > umbral_trad for x, y in zip(a, b))

        for doc_id, score in scored:
            if len(elegidos) >= n:
                break
            v = vectores_de(doc_id)
            if v is None:
                elegidos.append((doc_id, score))
                continue
            if any(es_copia(v, p, doc_id, d) for d, p in zip(ya_elegidos, vectores)):
                continue
            elegidos.append((doc_id, score))
            ya_elegidos.append(doc_id)
            vectores.append(v)

        # Si la poda dejó menos de n, se rellena con los mejores descartados:
        # más vale un duplicado que un hueco vacío.
        if len(elegidos) < n:
            ya = {d for d, _ in elegidos}
            for doc_id, score in scored:
                if len(elegidos) >= n:
                    break
                if doc_id not in ya:
                    elegidos.append((doc_id, score))
        return elegidos[:n]

    def _select_fragments(
        self, fused: list[tuple[int, float]], n: int, max_per_doc: int, expand: bool,
        expand_target: int | None = None,
    ) -> list[dict]:
        candidatos = _indices_al_final(fused, self.meta)
        seen_doc: dict[str, int] = defaultdict(int)
        huellas: list[set[str]] = []
        out: list[dict] = []
        for idx, score in candidatos:
            m = self.meta[idx]
            if seen_doc[m["doc_id"]] >= max_per_doc:
                continue
            # El corpus repite portadas, avisos legales y encabezados entre
            # documentos de un mismo observatorio. Dos fragmentos casi idénticos
            # en el top-10 desperdician una posición del ranking.
            huella = _trigramas(m["texto"])
            if any(_solapamiento(huella, h) > 0.7 for h in huellas):
                continue
            huellas.append(huella)
            seen_doc[m["doc_id"]] += 1
            texto = self._expand(idx, expand_target) if expand else m["texto"]
            out.append(
                {
                    "rank": len(out) + 1,
                    "chunk_id": m["chunk_id"],
                    "doc_id": m["doc_id"],
                    "text": texto,
                    "_score": score,
                    "_row": idx,
                }
            )
            if len(out) >= n:
                break

        # Si el tope de diversidad dejó la lista corta, se rellena sin tope
        if len(out) < n:
            elegidos = {f["_row"] for f in out}
            for idx, score in candidatos:
                if idx in elegidos:
                    continue
                m = self.meta[idx]
                out.append(
                    {
                        "rank": len(out) + 1,
                        "chunk_id": m["chunk_id"],
                        "doc_id": m["doc_id"],
                        "text": self._expand(idx, expand_target) if expand else m["texto"],
                        "_score": score,
                        "_row": idx,
                    }
                )
                if len(out) >= n:
                    break
        return out

    def _expand(self, idx: int, target: int | None = None) -> str:
        """Concatena el fragmento con sus vecinos hasta acercarse a 250 palabras.

        La Sección 9.2.1 lo permite explícitamente ("puede concatenarse con el
        fragmento inmediatamente anterior o posterior") y el chunk_id reportado
        sigue siendo el del fragmento original del índice.
        """
        objetivo = config.EXPAND_TARGET_WORDS if target is None else target
        m = self.meta[idx]
        texto = m["texto"]
        total = word_count(texto)
        if total >= objetivo:
            return texto

        doc_id, pos = m["doc_id"], m["posicion"]
        antes, despues = [], []
        step_prev, step_next = 1, 1
        # Alterna posterior/anterior para mantener el fragmento original centrado
        while True:
            grew = False
            nxt = self.by_doc_pos.get((doc_id, pos + step_next))
            if nxt is not None:
                t = self.meta[nxt]["texto"]
                if total + word_count(t) <= objetivo:
                    despues.append(t)
                    total += word_count(t)
                    step_next += 1
                    grew = True
            prv = self.by_doc_pos.get((doc_id, pos - step_prev))
            if prv is not None:
                t = self.meta[prv]["texto"]
                if total + word_count(t) <= objetivo:
                    antes.insert(0, t)
                    total += word_count(t)
                    step_prev += 1
                    grew = True
            if not grew:
                break

        # Con el presupuesto casi lleno ya no cabe un vecino entero, pero sí sus
        # primeras o últimas oraciones. Se toman completas, nunca a medias.
        margen = objetivo - total
        if margen >= 25:
            nxt = self.by_doc_pos.get((doc_id, pos + step_next))
            if nxt is not None:
                parcial = _primeras_oraciones(self.meta[nxt]["texto"], margen)
                if parcial:
                    despues.append(parcial)
                    margen -= word_count(parcial)
            if margen >= 25:
                prv = self.by_doc_pos.get((doc_id, pos - step_prev))
                if prv is not None:
                    parcial = _ultimas_oraciones(self.meta[prv]["texto"], margen)
                    if parcial:
                        antes.insert(0, parcial)

        return _join_sin_solape([*antes, texto, *despues])


_FIN_ORACION = re.compile(r"(?<=[.!?…])\s+(?=[¿¡\"'«(\[A-ZÁÉÍÓÚÑÜ0-9])")


def _oraciones(texto: str) -> list[str]:
    """Separación ligera en oraciones, suficiente para recortar un vecino."""
    return [s for s in _FIN_ORACION.split(texto.strip()) if s.strip()]


def _primeras_oraciones(texto: str, max_palabras: int) -> str:
    out, total = [], 0
    for s in _oraciones(texto):
        n = word_count(s)
        if total + n > max_palabras:
            break
        out.append(s)
        total += n
    return " ".join(out)


def _ultimas_oraciones(texto: str, max_palabras: int) -> str:
    out, total = [], 0
    for s in reversed(_oraciones(texto)):
        n = word_count(s)
        if total + n > max_palabras:
            break
        out.insert(0, s)
        total += n
    return " ".join(out)


# Un índice de contenidos de PDF se reconoce por los líderes de puntos que unen
# el título con su número de página ("Challenges with SDA ........... 6"). Se
# piden dos o más: uno suelto aparece en texto corriente, dos ya son una tabla.
# En el corpus lo cumplen 1.115 de 91.088 fragmentos, todos índices reales.
_LIDER_DE_PUNTOS = re.compile(r"\.{4,}")


def _es_indice_de_contenidos(texto: str) -> bool:
    return len(_LIDER_DE_PUNTOS.findall(texto)) >= 2


def _indices_al_final(fused: list[tuple[int, float]], meta: list[dict]) -> list[tuple[int, float]]:
    """Manda los índices de contenidos al final de la lista de candidatos.

    Contienen todos los términos de la consulta y ninguna respuesta, así que la
    similitud los premia y el NDCG los castiga: en q027 uno de ellos ocupaba el
    puesto 1, que es el de mayor peso del NDCG@10.

    El Q&A de los organizadores permite conservarlos como parte del documento,
    así que no se descartan: se degradan. Si no hubiera diez fragmentos mejores,
    siguen estando disponibles al final.
    """
    normales, indices = [], []
    for par in fused:
        (indices if _es_indice_de_contenidos(meta[par[0]]["texto"]) else normales).append(par)
    return normales + indices if indices else fused


def _trigramas(texto: str) -> set[str]:
    palabras = texto.lower().split()
    return {" ".join(palabras[i : i + 3]) for i in range(max(len(palabras) - 2, 1))}


def _solapamiento(a: set[str], b: set[str]) -> float:
    """Coeficiente de solapamiento: |A∩B| / min(|A|,|B|).

    Se prefiere a Jaccard porque detecta que un fragmento corto esté
    íntegramente contenido en uno largo, que es el caso que nos interesa.
    """
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _join_sin_solape(pieces: list[str]) -> str:
    """Une fragmentos adyacentes eliminando la oración de solapamiento.

    El chunking arrastra una oración entre fragmentos consecutivos, así que
    concatenarlos tal cual duplicaría esa oración.
    """
    out = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if not out:
            out = piece
            continue
        # Busca el sufijo más largo de `out` que sea prefijo de `piece`
        limit = min(len(out), len(piece))
        cut = 0
        for k in range(limit, 20, -1):
            if out[-k:] == piece[:k]:
                cut = k
                break
        out = f"{out} {piece[cut:].lstrip()}".strip()
    return out
