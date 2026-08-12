"""Integración del grafo con la recuperación (Sección 8.5 de la especificación).

1. Se identifican las entidades de la consulta con el mismo componente NER que
   se usó al construir el grafo.
2. Se recuperan los fragmentos vinculados a esas entidades y a sus vecinos de
   primer orden.
3. Se puntúan por el número de relaciones relevantes encontradas.
4. La lista resultante entra al RRF como un índice más (Sección 8.4).
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from .gazetteers import GAZETTEER_FILE, usar_gazetteer
from .ner import gazetteer_hits

PESO_ENTIDAD_DIRECTA = 1.0
PESO_VECINO = 0.35
MAX_VECINOS = 12


class GraphRetriever:
    def __init__(self, graphml_path: Path, meta: list[dict]):
        import networkx as nx

        self.graph = nx.read_graphml(graphml_path)
        self.n_nodes = self.graph.number_of_nodes()
        self.n_edges = self.graph.number_of_edges()

        # El gazetteer viaja serializado junto al grafo: reconstruirlo requiere
        # el corpus, que la máquina del jurado no tiene.
        self.gazetteer_cargado = usar_gazetteer(Path(graphml_path).parent / GAZETTEER_FILE)

        index_path = Path(graphml_path).parent / "entidad_fragmentos.json"
        if index_path.exists():
            with open(index_path, encoding="utf-8") as fh:
                self.entidad_filas: dict[str, list[int]] = json.load(fh)
        else:
            # Sin el índice acompañante, se reconstruye desde la evidencia de las
            # aristas: más lento y menos completo, pero el grafo sigue sirviendo.
            self.entidad_filas = self._from_edges(meta)

        self.n_meta = len(meta)

    def _from_edges(self, meta: list[dict]) -> dict[str, list[int]]:
        fila_por_chunk = {m["chunk_id"]: i for i, m in enumerate(meta)}
        out: dict[str, set[int]] = defaultdict(set)
        for s, o, datos in self.graph.edges(data=True):
            for chunk_id in (datos.get("evidencia_chunks") or "").split(","):
                fila = fila_por_chunk.get(chunk_id.strip())
                if fila is not None:
                    out[s].add(fila)
                    out[o].add(fila)
        return {k: sorted(v) for k, v in out.items()}

    # ------------------------------------------------------------------ #

    def entidades_consulta(self, query: str) -> list[str]:
        """Entidades de la consulta que además existen como nodo del grafo."""
        candidatas = [nombre for nombre, _ in gazetteer_hits(query)]
        # Coincidencia laxa por si el nodo tiene otra capitalización
        por_minuscula = {n.lower(): n for n in self.graph.nodes}
        out = []
        for c in candidatas:
            if c in self.graph:
                out.append(c)
            elif c.lower() in por_minuscula:
                out.append(por_minuscula[c.lower()])
        return out

    def search(self, query: str, topk: int = 200) -> list[tuple[int, float]]:
        """Devuelve [(fila, puntuación), ...] ordenada, o [] si no hay entidades."""
        semillas = self.entidades_consulta(query)
        if not semillas:
            return []

        pesos: dict[str, float] = {}
        for s in semillas:
            pesos[s] = max(pesos.get(s, 0.0), PESO_ENTIDAD_DIRECTA)

            vecinos = []
            for _, o, datos in self.graph.out_edges(s, data=True):
                vecinos.append((o, float(datos.get("peso", 1))))
            for i, _, datos in self.graph.in_edges(s, data=True):
                vecinos.append((i, float(datos.get("peso", 1))))
            vecinos.sort(key=lambda kv: -kv[1])

            for vecino, _ in vecinos[:MAX_VECINOS]:
                pesos[vecino] = max(pesos.get(vecino, 0.0), PESO_VECINO)

        # Un fragmento vale más cuanto más entidades relevantes de la consulta
        # contiene, y más si son semillas directas que vecinos.
        puntajes: dict[int, float] = defaultdict(float)
        for entidad, peso in pesos.items():
            for fila in self.entidad_filas.get(entidad, ()):
                if 0 <= fila < self.n_meta:
                    puntajes[fila] += peso

        return sorted(puntajes.items(), key=lambda kv: -kv[1])[:topk]
