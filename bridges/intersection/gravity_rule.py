"""
GravityIntersectionRule — real-physics gravity adapter for the Mandala.

Wraps :func:`bridges.gravity_alternative_compute.gravity_full_alternative_diagnostic`
so the gravity domain participates in RESONATE as a first-class
contributor instead of a toy projector.

Physics → BasinSignature mapping
---------------------------------
* **Vector axis**: three-component ``(attract, null, repel)`` basis.
  Counts of ATTRACT / NULL / REPEL points from the ternary field
  analysis are normalised by the total point count. This places every
  gravity geometry on a simplex: one attractor-dominated field, a
  pure equilibrium (Lagrange-rich) field, and a repulsion-dominated
  field sit at the three corners.

* **Regime**: derived from entropy of the ternary distribution via
  :func:`bridges.probability_collapse.collapse_distribution`, so a
  gravity geometry with a single overwhelming attractor is ``FOCUSED``
  and an evenly-mixed three-body scenario is ``DIFFUSE``.

* **Confidence**: ``1 - normalised_entropy`` of the same
  distribution. High for a clearly dominant regime, low for a
  near-uniform ternary mix.

* **Scalar strength**: mean magnitude of the input gravity vectors.
  Zero if no vectors are supplied (rule still returns a valid NULL
  signature so the geometry is not silently dropped from
  resonate_many calls).

* **Metadata**: the upstream ``field_character`` label from the
  ternary diagnostic (``STABLE_MANIFOLD``, ``LAGRANGE_RICH``, …) plus
  a ``lagrange_fraction`` scalar drawn from the same analysis.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List

from bridges.gravity_alternative_compute import (
    GravityAlternativeDiagnostic,
    gravity_full_alternative_diagnostic,
)
from bridges.intersection.base import BasinSignature, IntersectionRule
from bridges.probability_collapse import (
    DistributionRegime,
    collapse_distribution,
)


class GravityIntersectionRule(IntersectionRule):
    """Intersection adapter for the gravity domain."""

    domain = "gravity"

    def signature(self, geometry: Dict[str, Any]) -> BasinSignature:
        diag: GravityAlternativeDiagnostic = gravity_full_alternative_diagnostic(
            geometry
        )
        self.last_diagnostic = diag

        analysis = diag.ternary_field_analysis or {}
        total = int(analysis.get("total_points", 0) or 0)
        attract = int(analysis.get("attract_count", 0) or 0)
        null_c = int(analysis.get("null_count", 0) or 0)
        repel = int(analysis.get("repel_count", 0) or 0)

        if total > 0:
            attract_frac = attract / total
            null_frac = null_c / total
            repel_frac = repel / total
        else:
            # No ternary data — fall back to a neutral basin so the
            # rule never drops a geometry silently.
            attract_frac = null_frac = repel_frac = 1.0 / 3.0

        # Probability vector lives on the (attract, null, repel) simplex.
        probs = [attract_frac, null_frac, repel_frac]
        collapse = collapse_distribution(probs)

        # Signed vector: place the three regime weights on the signed
        # 3-axis so dot products across domains carry directional
        # meaning. attract → -x axis, null → +y axis, repel → +x axis.
        vec = (
            repel_frac - attract_frac,   # x: net sign of directional forcing
            null_frac,                   # y: balanced-force occupancy
            # z: raw "certainty" — 1 - entropy, bounded in [0, 1]
            1.0 - collapse.normalised_entropy,
        )

        regime = collapse.regime
        confidence = 1.0 - collapse.normalised_entropy

        scalar_strength = _mean_vector_magnitude(
            geometry.get("vectors", []) or []
        )

        metadata = {
            "field_character": analysis.get("field_character"),
            "lagrange_fraction": null_frac,
            "dominant_state": collapse.dominant_index,  # 0=attract, 1=null, 2=repel
        }

        return BasinSignature(
            domain=self.domain,
            regime=regime,
            vector=vec,
            confidence=confidence,
            scalar_strength=scalar_strength,
            metadata=metadata,
        )


def _mean_vector_magnitude(vectors: List[List[float]]) -> float:
    """Mean Euclidean magnitude of a list of gravity vectors."""
    if not vectors:
        return 0.0
    total = 0.0
    n = 0
    for v in vectors:
        if not v:
            continue
        total += math.sqrt(sum(float(x) * float(x) for x in v))
        n += 1
    return total / n if n else 0.0


__all__ = ["GravityIntersectionRule"]
