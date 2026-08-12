"""Construcción del grafo de conocimiento (Sección 7 de la especificación).

G = (E, R, T) donde E son entidades, R tipos de relación y T las tripletas
(sujeto, relación, objeto). Cada tripleta guarda su evidencia textual —doc_id y
chunk_id de origen— como exige la Sección 7.2.

El grafo se exporta a GraphML con NetworkX. Además se guarda un índice
entidad -> fragmentos, que es lo que consume el módulo de recuperación para
aportar candidatos por camino de relaciones (Sección 8.5).
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

from .ner import entidades_spacy, gazetteer_hits, load_nlp, relaciones_sintacticas

MAX_EVIDENCIAS = 8  # chunk_ids guardados por arista
MIN_FREQ_ENTIDAD = 3  # entidades vistas en menos fragmentos que esto se podan
MIN_PESO_ARISTA = 2
MAX_ENTIDADES_POR_CHUNK = 12  # evita explosión combinatoria de co-ocurrencias


class GraphBuilder:
    def __init__(self) -> None:
        self.tipo_entidad: dict[str, str] = {}
        self.freq_entidad: Counter[str] = Counter()
        self.entidad_chunks: dict[str, list[int]] = defaultdict(list)
        # (sujeto, relación, objeto) -> {"peso": n, "evidencia": [chunk_id...]}
        self.tripletas: dict[tuple[str, str, str], dict] = defaultdict(
            lambda: {"peso": 0, "evidencia": [], "docs": set()}
        )

    # ------------------------------------------------------------------ #

    def add_chunk(self, row: int, chunk: dict, doc) -> None:
        """Registra las entidades y relaciones de un fragmento ya procesado."""
        gaz = gazetteer_hits(chunk["texto"])
        spa = entidades_spacy(doc) if doc is not None else []

        entidades: dict[str, str] = {}
        for nombre, tipo in gaz:  # el gazetteer manda: es específico del dominio
            entidades[nombre] = tipo
        for nombre, tipo in spa:
            entidades.setdefault(nombre, tipo)

        if len(entidades) > MAX_ENTIDADES_POR_CHUNK:
            # Se conservan las del dominio y se recortan las genéricas
            del_dominio = {n: t for n, t in entidades.items() if (n, t) in gaz}
            resto = [n for n in entidades if n not in del_dominio]
            entidades = {**del_dominio, **{n: entidades[n] for n in resto[: MAX_ENTIDADES_POR_CHUNK - len(del_dominio)]}}

        for nombre, tipo in entidades.items():
            self.tipo_entidad.setdefault(nombre, tipo)
            self.freq_entidad[nombre] += 1
            self.entidad_chunks[nombre].append(row)

        nombres = sorted(entidades)
        chunk_id, doc_id = chunk["chunk_id"], chunk["doc_id"]

        # Relaciones tipadas por el verbo que conecta las entidades
        tipadas: set[tuple[str, str]] = set()
        if doc is not None:
            for s, verbo, o in relaciones_sintacticas(doc, set(nombres)):
                self._add_triple(s, verbo, o, chunk_id, doc_id)
                tipadas.add((s, o))
                tipadas.add((o, s))

        # Co-ocurrencia en el mismo fragmento para los pares sin relación sintáctica
        for i, a in enumerate(nombres):
            for b in nombres[i + 1 :]:
                if (a, b) in tipadas:
                    continue
                self._add_triple(a, "co_ocurre_con", b, chunk_id, doc_id)

    def _add_triple(self, s: str, r: str, o: str, chunk_id: str, doc_id: str) -> None:
        if s == o:
            return
        entry = self.tripletas[(s, r, o)]
        entry["peso"] += 1
        entry["docs"].add(doc_id)
        if len(entry["evidencia"]) < MAX_EVIDENCIAS:
            entry["evidencia"].append(chunk_id)

    # ------------------------------------------------------------------ #

    def build_graph(self):
        """Poda y construye el DiGraph de NetworkX."""
        import networkx as nx

        vivos = {e for e, f in self.freq_entidad.items() if f >= MIN_FREQ_ENTIDAD}

        g = nx.DiGraph()
        for entidad in vivos:
            g.add_node(
                entidad,
                tipo=self.tipo_entidad.get(entidad, "OTRO"),
                frecuencia=int(self.freq_entidad[entidad]),
                n_fragmentos=len(self.entidad_chunks.get(entidad, ())),
            )

        for (s, r, o), datos in self.tripletas.items():
            if s not in vivos or o not in vivos:
                continue
            # Las co-ocurrencias necesitan evidencia repetida; las relaciones
            # sintácticas se conservan aunque aparezcan una sola vez.
            if r == "co_ocurre_con" and datos["peso"] < MIN_PESO_ARISTA:
                continue
            if g.has_edge(s, o) and g[s][o].get("relacion") != r:
                # GraphML no admite multigrafo simple: se conserva la relación
                # más frecuente y se anotan las demás.
                if datos["peso"] <= g[s][o].get("peso", 0):
                    otras = g[s][o].get("otras_relaciones", "")
                    g[s][o]["otras_relaciones"] = ";".join(filter(None, [otras, r]))
                    continue
            g.add_edge(
                s,
                o,
                relacion=r,
                peso=int(datos["peso"]),
                n_documentos=len(datos["docs"]),
                evidencia_chunks=",".join(datos["evidencia"]),
                evidencia_docs=",".join(sorted(datos["docs"])[:MAX_EVIDENCIAS]),
            )
        return g

    def entity_index(self, vivos: set[str] | None = None) -> dict[str, list[int]]:
        """entidad -> filas del índice donde aparece (deduplicadas y acotadas)."""
        out = {}
        for entidad, filas in self.entidad_chunks.items():
            if self.freq_entidad[entidad] < MIN_FREQ_ENTIDAD:
                continue
            if vivos is not None and entidad not in vivos:
                continue
            out[entidad] = sorted(set(filas))[:400]
        return out


def save_graph(graph, entity_index: dict[str, list[int]], out_dir: Path) -> dict:
    import networkx as nx

    out_dir.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, out_dir / "grafo.graphml")
    with open(out_dir / "entidad_fragmentos.json", "w", encoding="utf-8") as fh:
        json.dump(entity_index, fh, ensure_ascii=False)

    tipos = Counter(d.get("tipo", "OTRO") for _, d in graph.nodes(data=True))
    relaciones = Counter(d.get("relacion", "?") for _, _, d in graph.edges(data=True))
    return {
        "nodos": graph.number_of_nodes(),
        "aristas": graph.number_of_edges(),
        "tipos_entidad": dict(tipos.most_common()),
        "relaciones_top": dict(relaciones.most_common(15)),
    }
