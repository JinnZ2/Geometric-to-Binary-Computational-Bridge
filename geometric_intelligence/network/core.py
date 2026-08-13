"""
core.py -- GeometricNetwork: nodes, geometric relations, cycle audit.

phi = (1 + sqrt5)/2; phi^-9 ~ 0.01315 is the cycle-closure tolerance;
phi^2 + 1 ~ 3.618 is named the coherence threshold. A network is
"self-consistent" when traversing any cycle returns a value within phi^-9 of
where it started.

=====================================================================
AUDIT
=====================================================================
Behaviour is UNCHANGED from the file as supplied. This file arrived in a
second drop, after `integrity.py` and `resonance.py`; the interim
reconstruction that stood here is gone, and what it got wrong is recorded in
`README.md` because guessing a contract is a method worth scoring.

audit() PASSES the null harness, which is worth saying first because most of
what follows is negative. Randomising every edge factor -- destroying the
geometry while leaving the graph and the weights intact -- drops
`integrity_score` from 2.000 to a mean of 0.014 over 200 draws. The score is
responding to the geometry, not to the shape of the network.

GI-11  Cycle closure is probed at exactly one point, x = 1.
       `find_cycles` composes each cycle into an affine map x -> a*x + b and
       scores it as `abs(a * 1.0 + b - 1.0)`. Any affine map with a + b = 1
       fixes x = 1 without being the identity. Measured: a cycle of
       `compose(factor=2, offset=-1)` then `scale(1.0)` -- the map x -> 2x - 1
       -- reports closure error 0.000000, is counted CONSISTENT, and gives
       integrity 2.0000, while returning -1 for an input of 0 and 19 for an
       input of 10.

       Pure-`scale` cycles have b = 0 and are unaffected, which is why the
       demos and the shipped tests never see it: every cycle they build is
       pure scale. The `compose` edge kind is exactly the one that breaks it.
       Two probe points, or testing (a, b) against (1, 0) directly, closes it.
       This is P-FIXED-PROBE, already in the archive from FCL-4.

GI-12  `integrity_score` is part geometry and part author declaration.
       `integrity = base_score * (1 + mean_edge_weight)`, where `base_score`
       is the fraction of cycles that close and `weight` is documented as
       "confidence / certainty" and is set by whoever built the network.

       Three consequences, measured on the demo's nautilus network:
         * weight only ever ADDS. Declaring every edge weight 0.0 -- no
           confidence at all -- still scores 1.0000, the full consistency
           fraction. Declaring 1.0 scores 2.0000.
         * randomising weights in [0, 1] with the geometry untouched moves
           the score across 1.2298 to 1.7248, a 25 % spread on declarations
           alone.
         * with weights in [0, 1] the ceiling is 2.0, so INTEGRITY_THRESHOLD
           = 3.618 is unreachable here too -- reaching it needs weight
           >= 2.618, outside the documented range of a confidence.

       And the name collides: `integrity.py`'s `full_report()` returns a
       DIFFERENT `integrity_score`, bounded by 1.0, and compares it to the
       same INTEGRITY_THRESHOLD. Two quantities, one name, one constant, two
       incompatible ranges. See GI-2.

GI-13  correct() reaches consistency without restoring the correct value.
       It nudges every edge in every inconsistent cycle by
       `phi^-9 * (a_total - 1) / len(cycle)`, which balances the error across
       the cycle rather than removing it from the edge that carries it.

       Measured on the demo's own injected defect -- c2->c3 set to 2.0 where
       phi = 1.618034, an error of +23.6 %. After `correct(max_iter=500)`:
       c2->c3 = 1.810679 (+11.9 %) and its inverse partner c3->c2 = 0.559531
       (-9.5 %), the other eight edges untouched, and `audit()` reports 5/5
       cycles consistent, integrity 2.0000. The defect is not removed, it is
       split between two edges until their product closes. A network that has
       been through correct() is self-consistent and no longer matches the
       geometry it was built to express.

       At the demo's `max_iter=5` the step is ~0.66 % of the error per edge
       per pass, so `integrity_score` is 1.600000 before and 1.600000 after,
       while the demo prints "Edges modified: 10" between the two. `modified`
       counts edge-adjustments, not distinct edges.

GI-14  `_inverse_apply` returns float('inf') where its only caller expects an
       exception. `integrity.reconstruct()` walks edges backwards inside
       `except (ZeroDivisionError, OverflowError)`, which is the right guard
       for a zero factor -- but core returns `float('inf')` instead of
       raising, so the guard never fires and `inf` is written into the
       reconstruction as if it were a value. Measured: a network with one
       `scale(factor=0.0)` edge reconstructs `{'b': 1.618, 'a': 1.0,
       'c': inf}`.

GI-15  `hash()` is documented as a hash of "network topology and relations"
       and is also a hash of insertion order. `to_dict()` lists nodes and
       edges in the order they were added, so the same network built in a
       different order hashes differently. The shipped test calls `hash()`
       twice on one unchanged object, which cannot fail; the property the
       docstring claims is the one that is false.

License: CC0. Stdlib only.
"""
from __future__ import annotations

import math
import json
import hashlib
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field

PHI = (1.0 + math.sqrt(5.0)) / 2.0
PHI_INV = 1.0 / PHI
PHI_SQUARED = PHI * PHI
PHI_INV_9 = PHI_INV ** 9          # ≈ 0.01315
INTEGRITY_THRESHOLD = PHI_SQUARED + 1.0  # ≈ 3.618


@dataclass
class GeoNode:
    """A node in the geometric network."""
    id: str
    value: float = 1.0
    meta: Dict = field(default_factory=dict)


@dataclass  
class GeoEdge:
    """
    Directed edge with a geometric relation.

    relation types:
      "scale"   -> target = source * factor
      "rotate"  -> target = source + angle (mod 2π)
      "compose" -> target = source * factor + offset
    """
    source: str
    target: str
    rel_type: str      # "scale", "rotate", "compose"
    factor: float = 1.0
    offset: float = 0.0
    weight: float = 1.0  # confidence / certainty


class GeometricNetwork:
    """
    Self-consistency network.

    Build it by adding nodes and edges, then call .audit()
    to find cycles where the geometric product deviates from
    identity by more than PHI_INV_9.
    """

    def __init__(self):
        self.nodes: Dict[str, GeoNode] = {}
        self.edges: List[GeoEdge] = []
        self._adj: Dict[str, List[GeoEdge]] = {}  # source -> edges

    def add_node(self, node_id: str, value: float = 1.0, **meta) -> GeoNode:
        n = GeoNode(id=node_id, value=value, meta=meta)
        self.nodes[node_id] = n
        self._adj[node_id] = []
        return n

    def add_edge(self, source: str, target: str, rel_type: str = "scale",
                 factor: float = 1.0, offset: float = 0.0, weight: float = 1.0) -> GeoEdge:
        if source not in self.nodes:
            self.add_node(source)
        if target not in self.nodes:
            self.add_node(target)
        e = GeoEdge(source, target, rel_type, factor, offset, weight)
        self.edges.append(e)
        self._adj[source].append(e)
        return e

    def _apply(self, edge: GeoEdge, value: float) -> float:
        """Apply edge relation to a value."""
        if edge.rel_type == "scale":
            return value * edge.factor
        elif edge.rel_type == "rotate":
            return value + edge.factor  # factor used as angle
        elif edge.rel_type == "compose":
            return value * edge.factor + edge.offset
        else:
            return value

    def _inverse_apply(self, edge: GeoEdge, value: float) -> float:
        """Reverse the edge relation."""
        if edge.rel_type == "scale":
            return value / edge.factor if edge.factor != 0 else float('inf')
        elif edge.rel_type == "rotate":
            return value - edge.factor
        elif edge.rel_type == "compose":
            return (value - edge.offset) / edge.factor if edge.factor != 0 else float('inf')
        else:
            return value

    def _edge_transform(self, edge: GeoEdge) -> Tuple[float, float]:
        """
        Represent edge as an affine transform x -> a*x + b.
        Returns (a, b).
        """
        if edge.rel_type == "scale":
            return (edge.factor, 0.0)
        elif edge.rel_type == "rotate":
            return (1.0, edge.factor)
        elif edge.rel_type == "compose":
            return (edge.factor, edge.offset)
        return (1.0, 0.0)

    def _compose_transforms(self, edges: List[GeoEdge]) -> Tuple[float, float]:
        """
        Compose a chain of affine transforms.
        If each edge is x -> a_i*x + b_i, the composition is:
          x -> (Π a_i)*x + Σ b_j * Π_{k>j} a_k
        """
        a_total = 1.0
        b_total = 0.0
        for edge in edges:
            a, b = self._edge_transform(edge)
            b_total = b_total * a + b
            a_total *= a
        return (a_total, b_total)

    def find_cycles(self, max_depth: int = 8) -> List[Tuple[List[GeoEdge], float]]:
        """
        Find all directed cycles up to max_depth edges.
        Returns list of (edge_list, closure_error) where closure_error
        is |expected - actual| / |expected| for a unit test value.
        """
        cycles = []
        visited = set()

        def dfs(current: str, start: str, path: List[GeoEdge], depth: int):
            if depth > max_depth:
                return
            for edge in self._adj.get(current, []):
                new_path = path + [edge]
                if edge.target == start and len(new_path) >= 2:
                    # Found a cycle — compute closure error
                    a, b = self._compose_transforms(new_path)
                    # For a cycle, applying the transform to the start value
                    # should return approximately the start value.
                    # closure_error = |a*1 + b - 1| / 1  (using unit test value)
                    closure = abs(a * 1.0 + b - 1.0)
                    cycles.append((new_path, closure))
                elif edge.target not in visited:
                    visited.add(edge.target)
                    dfs(edge.target, start, new_path, depth + 1)
                    visited.discard(edge.target)

        for node_id in self.nodes:
            visited.clear()
            visited.add(node_id)
            dfs(node_id, node_id, [], 0)

        # Deduplicate cycles that are rotations of each other
        seen = set()
        unique = []
        for cycle, err in cycles:
            key = tuple(e.source + "->" + e.target for e in cycle)
            # Normalize by rotating to smallest lex edge
            min_idx = min(range(len(key)), key=lambda i: key[i])
            norm = tuple(key[(min_idx + i) % len(key)] for i in range(len(key)))
            if norm not in seen:
                seen.add(norm)
                unique.append((cycle, err))
        return unique

    def audit(self, tol: float = PHI_INV_9) -> Dict:
        """
        Full network audit.

        Returns dict with:
          n_nodes, n_edges, n_cycles, 
          consistent_cycles, inconsistent_cycles,
          integrity_score (0 to INTEGRITY_THRESHOLD),
          violations (list of inconsistent cycles)
        """
        cycles = self.find_cycles()
        consistent = []
        inconsistent = []

        for cycle, err in cycles:
            if err <= tol:
                consistent.append((cycle, err))
            else:
                inconsistent.append((cycle, err))

        # Integrity score: ratio of consistent cycles to total,
        # scaled by average edge weight in consistent cycles.
        # Bounded by INTEGRITY_THRESHOLD.
        if cycles:
            base_score = len(consistent) / len(cycles)
            # Weight bonus: high-confidence edges give higher score
            weight_sum = 0.0
            weight_count = 0
            for cycle, _ in consistent:
                for e in cycle:
                    weight_sum += e.weight
                    weight_count += 1
            weight_factor = (weight_sum / weight_count) if weight_count else 0.0
            integrity = base_score * (1.0 + weight_factor)
            integrity = min(integrity, INTEGRITY_THRESHOLD)
        else:
            integrity = 0.0

        return {
            "n_nodes": len(self.nodes),
            "n_edges": len(self.edges),
            "n_cycles": len(cycles),
            "consistent_cycles": len(consistent),
            "inconsistent_cycles": len(inconsistent),
            "integrity_score": round(integrity, 6),
            "threshold": INTEGRITY_THRESHOLD,
            "violations": [
                {
                    "cycle": " -> ".join(e.source + "-" + e.target for e in cyc),
                    "closure_error": round(err, 8),
                    "exceeds_tol_by": round(err / tol, 2) if tol else float('inf')
                }
                for cyc, err in inconsistent
            ]
        }

    def correct(self, tol: float = PHI_INV_9, max_iter: int = 10) -> int:
        """
        Iterative error correction.

        For each inconsistent cycle, nudge edge factors toward
        consistency using φ⁻⁹-scaled adjustments. Returns number of
        edges modified.
        """
        modified = 0
        for _ in range(max_iter):
            cycles = self.find_cycles()
            bad = [(c, e) for c, e in cycles if e > tol]
            if not bad:
                break
            for cycle, err in bad:
                # Distribute the correction across edges proportionally
                # to their inverse weight (lower confidence = more correction)
                a_total, b_total = self._compose_transforms(cycle)
                # We want a_total ≈ 1, b_total ≈ 0 for identity
                # Adjust each edge slightly toward that goal
                for edge in cycle:
                    a, b = self._edge_transform(edge)
                    # Scale correction by φ⁻⁹ to avoid oscillation
                    if edge.rel_type == "scale":
                        edge.factor *= (1.0 - PHI_INV_9 * (a_total - 1.0) / len(cycle))
                        modified += 1
                    elif edge.rel_type == "compose":
                        edge.factor *= (1.0 - PHI_INV_9 * (a_total - 1.0) / len(cycle))
                        edge.offset -= PHI_INV_9 * b_total / len(cycle)
                        modified += 1
        return modified

    def to_dict(self) -> Dict:
        return {
            "nodes": [{"id": n.id, "value": n.value, "meta": n.meta} 
                      for n in self.nodes.values()],
            "edges": [{"source": e.source, "target": e.target,
                       "rel_type": e.rel_type, "factor": e.factor,
                       "offset": e.offset, "weight": e.weight}
                      for e in self.edges]
        }

    @classmethod
    def from_dict(cls, d: Dict) -> "GeometricNetwork":
        net = cls()
        for n in d.get("nodes", []):
            net.add_node(n["id"], n.get("value", 1.0), **n.get("meta", {}))
        for e in d.get("edges", []):
            net.add_edge(e["source"], e["target"], e.get("rel_type", "scale"),
                        e.get("factor", 1.0), e.get("offset", 0.0),
                        e.get("weight", 1.0))
        return net

    def hash(self) -> str:
        """Stable hash of network topology and relations."""
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()[:16]
