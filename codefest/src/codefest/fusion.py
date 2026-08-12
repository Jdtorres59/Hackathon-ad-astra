"""Combinación de múltiples bases vectoriales (Sección 8.4 de la especificación).

Tres estrategias, todas operando exclusivamente sobre puntuaciones y rangos:

- CombSUM: suma de similitudes coseno; cero si el fragmento no está en el top-k.
- CombMNZ: CombSUM multiplicado por el número de índices donde aparece.
- RRF:     suma de 1/(k0 + rango); robusto a diferencias de escala entre
           encoders, que es exactamente nuestro caso porque los tres producen
           distribuciones de similitud distintas.

RRF es el predeterminado por esa robustez. Las tres se comparan en la ablación.
"""

from __future__ import annotations

from collections import defaultdict

from . import config

RankedList = list[tuple[int, float]]  # [(idx_interno, puntuación), ...] ordenada


def rrf(lists: list[RankedList], k0: int | None = None, weights: list[float] | None = None) -> dict[int, float]:
    k0 = config.RRF_K0 if k0 is None else k0
    weights = weights or [1.0] * len(lists)
    scores: dict[int, float] = defaultdict(float)
    for lst, w in zip(lists, weights):
        for rank, (idx, _score) in enumerate(lst, start=1):
            scores[idx] += w / (k0 + rank)
    return dict(scores)


def _minmax(lst: RankedList) -> dict[int, float]:
    """Normaliza a [0,1] para que las escalas de distintos encoders sean comparables."""
    if not lst:
        return {}
    vals = [s for _, s in lst]
    lo, hi = min(vals), max(vals)
    span = hi - lo
    if span <= 1e-9:
        return {idx: 1.0 for idx, _ in lst}
    return {idx: (s - lo) / span for idx, s in lst}


def combsum(lists: list[RankedList], weights: list[float] | None = None, normalize: bool = True) -> dict[int, float]:
    weights = weights or [1.0] * len(lists)
    scores: dict[int, float] = defaultdict(float)
    for lst, w in zip(lists, weights):
        contrib = _minmax(lst) if normalize else dict(lst)
        for idx, s in contrib.items():
            scores[idx] += w * s
    return dict(scores)


def combmnz(lists: list[RankedList], weights: list[float] | None = None, normalize: bool = True) -> dict[int, float]:
    base = combsum(lists, weights, normalize)
    hits: dict[int, int] = defaultdict(int)
    for lst in lists:
        for idx, _ in lst:
            hits[idx] += 1
    return {idx: s * hits[idx] for idx, s in base.items()}


FUSIONS = {"rrf": rrf, "combsum": combsum, "combmnz": combmnz}


def fuse(lists: list[RankedList], method: str = "rrf", **kwargs) -> list[tuple[int, float]]:
    """Devuelve la lista unificada ordenada de mayor a menor puntuación."""
    if method not in FUSIONS:
        raise ValueError(f"método de fusión desconocido: {method}")
    scores = FUSIONS[method](lists, **kwargs)
    return sorted(scores.items(), key=lambda kv: -kv[1])
