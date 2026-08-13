"""
integrity.py -- measurement validation and protected reconstruction.

Given a geometric network and a set of measurements: check whether the
measurements are consistent with the network, reconstruct missing values from
the consistent subset, and say which parts can be trusted.

=====================================================================
AUDIT  --  read before trusting a verdict from this module
=====================================================================
Behaviour below is UNCHANGED from the file as supplied. The findings are
recorded, not patched: each fix changes what a verdict means, and a verdict
here is what a reader cuts timber against. `full_report()` now carries the
two degeneracies in its own output, so a caller cannot read either as a
confirmation -- the same remedy used for the AISS flat merit weights and for
`bridges/non_local_sensor.py`'s inferred scale.

GI-1   Measurements do not propagate. This is the load-bearing one.
       `predict_from(source, target)` seeds its walk with
       `self.net.nodes[source_id].value` -- the DESIGN value -- not
       `self.measurements[source_id]`. So `add_measurement` on a source has
       no effect on any prediction, and every "prediction" is the design
       value propagated along a path.

       Measured: a brace whose design length is 600 mm and whose measured
       length is 400 mm predicts its neighbour at 970.8 mm either way, to
       every digit. The field guide's stated purpose -- catch the mis-cut
       part before you weld -- is exactly the case that does not work, since
       a 200 mm error travels nowhere.

       The one-line change is `self.measurements.get(source_id, ...)`, and it
       is not made here because it re-decides every verdict the ledger already
       holds. `full_report()` reports `predictions_use_measurements: False`.

GI-2   `passes` has a clause no input can satisfy.
       `integrity = coverage * (trusted_count / total_measured)` is a product
       of two quantities each in [0, 1], so integrity <= 1.0 always. The
       clause tests `integrity >= INTEGRITY_THRESHOLD * 0.5`, which is
       1.809017. `passes` is therefore decided entirely by its first clause,
       `trusted_count == total_measured and coverage >= 0.5`, and phi^2 + 1
       does no work anywhere in the module. Same shape as `GLY-1`, found by
       the same screen: enumerate what the outputs can be before trusting the
       label. `full_report()` reports `threshold_clause_reachable: False`.

GI-3   The search over sources searches nothing, until the design is wrong.
       `check()` runs a BFS from every other measured node and keeps the
       minimum-error prediction. On a path-consistent design every source
       yields the SAME value (a consequence of GI-1), so the O(N^2) walk is
       redundant. On a design with two paths of different product -- the
       contradiction `audit()` exists to find -- it silently keeps whichever
       path agrees best with the measurement, and reports residual 0.000 %,
       trusted. Measured: a network where one route gives phi^3 = 4.2361 and
       another gives 3.2361 returns "trusted" for a measurement of 3.2361.
       A design contradiction is resolved in the measurement's favour and
       nothing in the report says a choice was made.

GI-4   `reconstruct()` does not do what its docstring says.
       The docstring promises "if multiple trusted paths give different
       values, average them weighted by path confidence (product of edge
       weights)". No averaging and no weights are in the body: the guard is
       `if edge.target not in reconstructed`, so the FIRST edge to reach a
       node wins and the answer depends on the order edges were added.
       Measured: two edges a->x with factors 2.0 and 5.0 give x = 2.0 or
       x = 5.0 according to insertion order alone.

GI-5   `IntegrityReport.reconstructed` is declared and never assigned.
       It is `Optional[float] = None` on the dataclass, `check()` builds every
       report without it, and `full_report()` looks the value up from a
       separate dict. The field is `None` on every report the module produces.

GI-6   The field guide's emergency procedure returns nothing from one
       measurement. "If you lose a measurement ... recon = monitor.
       reconstruct()" -- but a lone measured node has no OTHER measured node
       to predict it, so it falls to the isolated-node branch, which sets
       `trusted=False` unconditionally, and `reconstruct()` seeds only from
       trusted nodes. One good measurement of a three-node chain returns
       `{}`. Two good measurements reconstruct the third correctly. The
       procedure works from two, not from one, and the guide says one.

       That branch also computes `residual` against a different reference
       from the connected branch (the node's own declared value rather than a
       propagated prediction), so one field carries two meanings.

License: CC0. Stdlib only.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass

from .core import GeometricNetwork, GeoEdge, PHI_INV_9, INTEGRITY_THRESHOLD


@dataclass
class IntegrityReport:
    node_id: str
    predicted: float
    measured: float
    residual: float      # |predicted - measured| / |predicted|
    trusted: bool        # residual <= PHI_INV_9 ?
    reconstructed: Optional[float] = None


class IntegrityMonitor:
    """
    Monitor a geometric network against external measurements.
    """

    def __init__(self, network: GeometricNetwork):
        self.net = network
        self.measurements: Dict[str, float] = {}

    def add_measurement(self, node_id: str, value: float):
        """Record a measured value for a node."""
        self.measurements[node_id] = value

    def predict_from(self, source_id: str, target_id: str) -> Optional[float]:
        """
        Predict target value by following the shortest path
        from source, applying edge transforms.
        """
        # BFS for shortest path
        from collections import deque
        queue = deque([(source_id, self.net.nodes[source_id].value)])
        visited = {source_id}

        while queue:
            current, val = queue.popleft()
            if current == target_id:
                return val
            for edge in self.net._adj.get(current, []):
                if edge.target not in visited:
                    visited.add(edge.target)
                    new_val = self.net._apply(edge, val)
                    queue.append((edge.target, new_val))
        return None

    def check(self, tol: float = PHI_INV_9) -> List[IntegrityReport]:
        """
        Check all measured nodes against network predictions.
        For each measured node, find the best prediction from
        any other measured node.
        """
        reports = []
        measured_ids = list(self.measurements.keys())

        for target in measured_ids:
            best_pred = None
            best_source = None
            best_err = float('inf')

            for source in measured_ids:
                if source == target:
                    continue
                pred = self.predict_from(source, target)
                if pred is None:
                    continue
                err = abs(pred - self.measurements[target]) / max(abs(pred), 1e-12)
                if err < best_err:
                    best_err = err
                    best_pred = pred
                    best_source = source

            if best_pred is not None:
                reports.append(IntegrityReport(
                    node_id=target,
                    predicted=best_pred,
                    measured=self.measurements[target],
                    residual=best_err,
                    trusted=best_err <= tol
                ))
            else:
                # Isolated node — can't verify, mark untrusted
                reports.append(IntegrityReport(
                    node_id=target,
                    predicted=self.net.nodes[target].value,
                    measured=self.measurements[target],
                    residual=abs(self.measurements[target] - self.net.nodes[target].value) / max(abs(self.net.nodes[target].value), 1e-12),
                    trusted=False
                ))

        return reports

    def reconstruct(self, tol: float = PHI_INV_9) -> Dict[str, float]:
        """
        Reconstruct all node values using only trusted measurements.

        Algorithm:
        1. Identify trusted measurements (residual <= tol)
        2. Propagate values through the network from trusted nodes
        3. If multiple trusted paths give different values, average
           them weighted by path confidence (product of edge weights)
        """
        reports = self.check(tol)
        trusted_ids = {r.node_id for r in reports if r.trusted}

        # Also trust nodes that weren't measured but are consistent
        # with the trusted subgraph
        reconstructed = {}

        # Initialize with measured values for trusted nodes
        for nid in trusted_ids:
            reconstructed[nid] = self.measurements[nid]

        # Propagate to neighbors iteratively
        changed = True
        iterations = 0
        max_iter = len(self.net.nodes) * 2

        while changed and iterations < max_iter:
            changed = False
            iterations += 1
            for edge in self.net.edges:
                if edge.source in reconstructed and edge.target not in reconstructed:
                    pred = self.net._apply(edge, reconstructed[edge.source])
                    reconstructed[edge.target] = pred
                    changed = True
                # Reverse propagation if edge is invertible
                if edge.target in reconstructed and edge.source not in reconstructed:
                    try:
                        rev = self.net._inverse_apply(edge, reconstructed[edge.target])
                        reconstructed[edge.source] = rev
                        changed = True
                    except (ZeroDivisionError, OverflowError):
                        pass

        return reconstructed

    def full_report(self, tol: float = PHI_INV_9) -> Dict:
        """
        Complete integrity report.
        """
        reports = self.check(tol)
        reconstructed = self.reconstruct(tol)

        trusted_count = sum(1 for r in reports if r.trusted)
        total_measured = len(reports)
        total_nodes = len(self.net.nodes)

        # Integrity score: fraction of network that is trusted + reconstructed
        covered = set(reconstructed.keys())
        coverage = len(covered) / total_nodes if total_nodes else 0.0

        # Compare to threshold
        integrity = coverage * (trusted_count / max(total_measured, 1))

        return {
            # GI-1 / GI-2. Reported beside every score so a caller cannot
            # read either degeneracy as a confirmation. See the module audit.
            "predictions_use_measurements": False,
            "threshold_clause_reachable": INTEGRITY_THRESHOLD * 0.5 <= 1.0,
            "n_nodes": total_nodes,
            "n_measured": total_measured,
            "n_trusted": trusted_count,
            "n_untrusted": total_measured - trusted_count,
            "n_reconstructed": len(reconstructed),
            "coverage": round(coverage, 4),
            "integrity_score": round(integrity, 6),
            "threshold": INTEGRITY_THRESHOLD,
            "passes": (trusted_count == total_measured and coverage >= 0.5) or integrity >= INTEGRITY_THRESHOLD * 0.5,
            "node_reports": [
                {
                    "node": r.node_id,
                    "predicted": round(r.predicted, 6),
                    "measured": round(r.measured, 6),
                    "residual_pct": round(r.residual * 100, 4),
                    "trusted": r.trusted,
                    "reconstructed": round(reconstructed.get(r.node_id, r.predicted), 6)
                }
                for r in reports
            ],
            "untrusted_nodes": [
                r.node_id for r in reports if not r.trusted
            ],
            "reconstructed_values": {
                k: round(v, 6) for k, v in reconstructed.items()
            }
        }
