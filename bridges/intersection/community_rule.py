"""
CommunityIntersectionRule — real-physics community adapter for the Mandala.

Delegates to :func:`bridges.community_alternative_compute.community_alternative_diagnostic`
and projects the six-buffer ternary state onto the shared basin axes.

Physics → BasinSignature mapping
---------------------------------
* **Vector axis**: ``(net reserve, stable dwell, buffer diversity)``.

  - x-component: ``ABUNDANT - DEPLETE`` fraction across the six
    resilience buffers (food, energy, social, institutional,
    knowledge, infrastructure). Positive = net-surplus community,
    negative = net-depleted.
  - y-component: ``STABLE`` fraction — how many buffers are in
    equilibrium. A community with every buffer STABLE has high
    y, signalling monitor-mode.
  - z-component: ``1 - normalised_entropy`` of the buffer histogram,
    a proxy for "how many buffers agree on one regime." High =
    every buffer tells the same story; low = mixed signals.

* **Regime**: entropy over the six-buffer ternary histogram.

* **Confidence**: ``1 - normalised_entropy``.

* **Scalar strength**: mean of the numeric buffer values (days of
  reserve, etc.) exposed by each :func:`ternary_*_buffer` call.
"""

from __future__ import annotations

from typing import Any, Dict

from bridges.community_alternative_compute import (
    CommunityAlternativeDiagnostic,
    community_alternative_diagnostic,
)
from bridges.intersection.base import BasinSignature, IntersectionRule
from bridges.probability_collapse import collapse_distribution


class CommunityIntersectionRule(IntersectionRule):
    """Intersection adapter for the community domain."""

    domain = "community"

    def signature(self, geometry: Dict[str, Any]) -> BasinSignature:
        diag: CommunityAlternativeDiagnostic = community_alternative_diagnostic(
            geometry
        )
        self.last_diagnostic = diag

        # ternary_buffers: Dict[str, Tuple[TernaryBufferState, float, str]]
        buffers = dict(diag.ternary_buffers or {})
        total = len(buffers) or 1

        deplete = sum(1 for (s, *_rest) in buffers.values() if int(s) == -1)
        stable = sum(1 for (s, *_rest) in buffers.values() if int(s) == 0)
        abundant = sum(1 for (s, *_rest) in buffers.values() if int(s) == +1)

        d_frac = deplete / total
        s_frac = stable / total
        a_frac = abundant / total

        collapse = collapse_distribution([d_frac, s_frac, a_frac])

        vec = (
            a_frac - d_frac,                        # net reserve
            s_frac,                                  # stable dwell
            1.0 - collapse.normalised_entropy,       # buffer agreement
        )

        regime = collapse.regime
        confidence = 1.0 - collapse.normalised_entropy

        numeric_values = [
            float(v) for (_state, v, *_rest) in buffers.values()
            if isinstance(v, (int, float))
        ]
        scalar_strength = (
            sum(numeric_values) / len(numeric_values)
            if numeric_values else 0.0
        )

        metadata = {
            "deplete_fraction": d_frac,
            "stable_fraction": s_frac,
            "abundant_fraction": a_frac,
            "overall_stance": diag.overall_ternary_stance.name
                if hasattr(diag.overall_ternary_stance, "name") else None,
            "buffer_count": total,
        }

        return BasinSignature(
            domain=self.domain,
            regime=regime,
            vector=vec,
            confidence=confidence,
            scalar_strength=scalar_strength,
            metadata=metadata,
        )


__all__ = ["CommunityIntersectionRule"]
