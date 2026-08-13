#!/usr/bin/env python3
"""
core.py -- GeometricNetwork: nodes, phi-scaled edges, and the constants.

=====================================================================
PROVENANCE  --  this file was NOT in the drop
=====================================================================
`integrity.py`, `resonance.py`, `__init__.py`, `README.md` and
`FIELD_GUIDE.md` arrived together and all import from `.core`, which did not.
`bridge.py` (network_to_claims / append_geo_claims), the test module and
`examples/demo.py` are also referenced and absent.

What is here is the part of core's contract that the supplied modules
*determine*: every attribute and method they actually call, with the only
semantics consistent with the worked examples in README.md and
FIELD_GUIDE.md (a `scale` edge multiplies by `factor`; the timber-frame
example's 600 / 970.8 / 1570.8 mm reproduce exactly).

What is NOT determined is refused rather than guessed:

    audit()    README calls it and reads `integrity_score` out of it.
    correct()  __init__'s docstring calls it "iterative error correction".

Both are described only by name. `audit` in particular is the headline
number of the whole package -- "if integrity_score is low, your design has an
internal contradiction. Fix the design before cutting wood" -- and a plausible
formula invented here would be a number a person cuts timber against. They
raise NotImplementedError naming what is missing, on the same principle as
`Silicon/fp4_autopilot.py`'s `ber_sweep()`: a synthetic curve in place of an
absent one is worse than the absence.

Everything below this line runs. `GI-*` and `GR-*` findings in
`integrity.py` and `resonance.py` were measured against it.

License: CC0. Stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

#: Golden ratio.
PHI = (1.0 + 5.0 ** 0.5) / 2.0
#: 1/phi. Equal to PHI - 1.
PHI_INV = 1.0 / PHI
#: phi^-9 ~ 0.013156. Used as the default residual tolerance -- 1.3 %.
PHI_INV_9 = PHI ** -9
#: phi^2 + 1 = phi + 2 ~ 3.618034.
#:
#: Named a "coherence bound" by README.md. Nothing in the supplied code
#: compares a quantity to it that can reach it: see GI-2 in integrity.py,
#: where `integrity` is a product of two fractions and is therefore <= 1,
#: while the clause tests it against 1.809. Kept at the value the drop
#: declares, and flagged where it is used rather than silently rescaled.
INTEGRITY_THRESHOLD = PHI ** 2 + 1.0

#: Edge kinds the supplied modules exercise. `_apply` must be defined for
#: every one of them, and `_inverse_apply` for every invertible one --
#: integrity.reconstruct() calls the inverse inside a bare
#: `except (ZeroDivisionError, OverflowError)`, so an unhandled kind would
#: surface as an AttributeError, not as a skipped edge.
EDGE_KINDS = ("scale", "offset", "compose")


@dataclass
class GeoNode:
    id: str
    value: float = 0.0
    meta: dict = None


@dataclass
class GeoEdge:
    source: str
    target: str
    kind: str = "scale"
    factor: float = 1.0

    def __post_init__(self):
        if self.kind not in EDGE_KINDS:
            raise ValueError(
                "unknown edge kind %r; core defines %s. An unknown kind would "
                "reach _apply and raise there instead of here."
                % (self.kind, ", ".join(EDGE_KINDS)))


class GeometricNetwork:
    """A directed graph whose edges carry a numeric relation between values.

    `scale`   target = source * factor
    `offset`  target = source + factor
    `compose` target = source * factor, applied without an inverse (the
              relation is declared non-invertible, so reconstruct() will not
              walk it backwards)
    """

    def __init__(self):
        self.nodes: Dict[str, GeoNode] = {}
        self.edges: List[GeoEdge] = []
        self._adj: Dict[str, List[GeoEdge]] = {}

    # -- construction --------------------------------------------------
    def add_node(self, node_id: str, value: float = 0.0, **meta) -> GeoNode:
        n = GeoNode(node_id, float(value), meta or None)
        self.nodes[node_id] = n
        self._adj.setdefault(node_id, [])
        return n

    def add_edge(self, source: str, target: str, kind: str = "scale",
                 factor: float = 1.0) -> GeoEdge:
        for end in (source, target):
            if end not in self.nodes:
                raise KeyError("%r is not a node; add_node it first" % end)
        e = GeoEdge(source, target, kind, float(factor))
        self.edges.append(e)
        self._adj.setdefault(source, []).append(e)
        return e

    # -- edge semantics ------------------------------------------------
    def _apply(self, edge: GeoEdge, value: float) -> float:
        if edge.kind in ("scale", "compose"):
            return value * edge.factor
        if edge.kind == "offset":
            return value + edge.factor
        raise ValueError("no _apply for edge kind %r" % edge.kind)

    def _inverse_apply(self, edge: GeoEdge, value: float) -> float:
        if edge.kind == "scale":
            return value / edge.factor          # ZeroDivisionError is caught
        if edge.kind == "offset":               # by integrity.reconstruct()
            return value - edge.factor
        raise ValueError(
            "edge kind %r is declared non-invertible" % edge.kind)

    # -- not determined by the drop ------------------------------------
    def audit(self, *_a, **_kw):
        raise NotImplementedError(
            "audit() was named by README.md and __init__.py but not supplied, "
            "and its output `integrity_score` is the number the field guide "
            "tells a reader to cut timber against ('if integrity_score is "
            "low, your design has an internal contradiction'). What it "
            "measures -- which cycles are enumerated, how a cycle's product "
            "is compared to identity, how per-cycle deviations combine into "
            "one score -- is not recoverable from the modules that call it. "
            "Open problem GI-8.")

    def correct(self, *_a, **_kw):
        raise NotImplementedError(
            "correct() was described only as 'iterative error correction'. "
            "What it minimises, what it is allowed to move, and what it "
            "converges to are unstated. Open problem GI-8.")
