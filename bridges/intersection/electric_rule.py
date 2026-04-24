"""
ElectricIntersectionRule — real-physics electric adapter for the Mandala.

Delegates to :func:`bridges.electric_alternative_compute.electric_full_alternative_diagnostic`
and projects the result onto the common three-axis basin space.

Physics → BasinSignature mapping
---------------------------------
* **Vector axis**: ``(net directional current, zero-dwell, charge net)``.
  The x-component sums the sign of the ternary *current* states
  (FORWARD=+1, ZERO=0, REVERSE=-1), normalised by sample count — a
  signed net-current fraction that survives AC zero-crossings. The
  y-component is the zero-dwell fraction (how much of the sample time
  the current spends at ZERO). The z-component is the sign of the
  ternary *charge* states — positive when the geometry is net POSITIVE.

* **Regime**: entropy collapse over the ternary *current* histogram.
  A clean AC waveform with balanced FORWARD / REVERSE fractions lands
  in DIFFUSE; a pinned-forward DC geometry lands in FOCUSED.

* **Confidence**: ``1 - normalised_entropy`` of the current histogram.

* **Scalar strength**: RMS of ``current_A`` in amps.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Sequence

from bridges.electric_alternative_compute import (
    ElectricAlternativeDiagnostic,
    TernaryChargeState,
    TernaryCurrentState,
    electric_full_alternative_diagnostic,
)
from bridges.intersection.base import BasinSignature, IntersectionRule
from bridges.probability_collapse import collapse_distribution


def _rms(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(float(v) * float(v) for v in values) / len(values))


def _ternary_histogram(states: List, enum_cls) -> Dict[int, int]:
    """Count how many samples land in each enum value of ``enum_cls``."""
    counts = {int(m): 0 for m in enum_cls}
    for s in states:
        counts[int(s)] = counts.get(int(s), 0) + 1
    return counts


class ElectricIntersectionRule(IntersectionRule):
    """Intersection adapter for the electric domain."""

    domain = "electric"

    def signature(self, geometry: Dict[str, Any]) -> BasinSignature:
        frequency_hz = geometry.get("frequency_hz")
        diag: ElectricAlternativeDiagnostic = electric_full_alternative_diagnostic(
            geometry, frequency_hz=frequency_hz,
        )
        self.last_diagnostic = diag

        # Current histogram (FORWARD=+1, ZERO=0, REVERSE=-1)
        current_hist = _ternary_histogram(
            diag.current_states, TernaryCurrentState,
        )
        n_current = sum(current_hist.values()) or 1
        fwd = current_hist.get(+1, 0) / n_current
        zero = current_hist.get(0, 0) / n_current
        rev = current_hist.get(-1, 0) / n_current

        # Charge histogram (POSITIVE=+1, NEUTRAL=0, NEGATIVE=-1)
        charge_hist = _ternary_histogram(
            diag.charge_states, TernaryChargeState,
        )
        n_charge = sum(charge_hist.values()) or 1
        q_pos = charge_hist.get(+1, 0) / n_charge
        q_neu = charge_hist.get(0, 0) / n_charge
        q_neg = charge_hist.get(-1, 0) / n_charge

        collapse = collapse_distribution([rev, zero, fwd])

        vec = (
            fwd - rev,           # x: net directional current (signed)
            zero,                # y: zero-dwell fraction
            q_pos - q_neg,       # z: net charge sign
        )

        regime = collapse.regime
        confidence = 1.0 - collapse.normalised_entropy

        scalar_strength = _rms(geometry.get("current_A", []) or [])

        metadata = {
            "forward_fraction": fwd,
            "zero_fraction": zero,
            "reverse_fraction": rev,
            "charge_balance": (q_pos, q_neu, q_neg),
            "ac_stance": (diag.ac_zero_crossing_analysis or {}).get(
                "ternary_stance"
            ),
        }

        return BasinSignature(
            domain=self.domain,
            regime=regime,
            vector=vec,
            confidence=confidence,
            scalar_strength=scalar_strength,
            metadata=metadata,
        )


__all__ = ["ElectricIntersectionRule"]
