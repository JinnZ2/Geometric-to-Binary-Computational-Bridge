"""
SoundIntersectionRule — real-physics sound adapter for the Mandala.

Delegates to :func:`bridges.sound_alternative_compute.sound_full_alternative_diagnostic`
and projects the ternary phase analysis plus harmonic entropy onto
the common three-axis basin space.

Physics → BasinSignature mapping
---------------------------------
* **Vector axis**: ``(pressure balance, equilibrium dwell, harmonic entropy)``.

  - x-component: ``COMPRESSION - RAREFACTION`` fraction — the
    signed net-pressure bias that binary phase encoding erases.
  - y-component: ``EQUILIBRIUM`` fraction — how much of the waveform
    lives at zero-crossing (the "air" of the sound).
  - z-component: ``1 - normalised_harmonic_entropy`` when a
    :class:`QuantumHarmonicSuperposition` is available, else 0.
    Captures whether a single harmonic dominates the spectrum.

* **Regime**: entropy over the ternary phase distribution.
  A sine wave near-equally split between compression and rarefaction
  lands in DIFFUSE; a heavily DC-biased waveform lands in FOCUSED.

* **Confidence**: ``1 - normalised_entropy`` of the phase histogram.

* **Scalar strength**: RMS of ``amplitude`` if present.
"""

from __future__ import annotations

import math
from typing import Any, Dict, Sequence

from bridges.intersection.base import BasinSignature, IntersectionRule
from bridges.probability_collapse import collapse_distribution
from bridges.sound_alternative_compute import (
    SoundAlternativeDiagnostic,
    sound_full_alternative_diagnostic,
)


def _rms(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return math.sqrt(sum(float(v) * float(v) for v in values) / len(values))


class SoundIntersectionRule(IntersectionRule):
    """Intersection adapter for the sound domain."""

    domain = "sound"

    def signature(self, geometry: Dict[str, Any]) -> BasinSignature:
        diag: SoundAlternativeDiagnostic = sound_full_alternative_diagnostic(
            geometry
        )
        self.last_diagnostic = diag

        td = diag.ternary_phase_distribution or {}
        fractions = td.get("ternary_fractions", {}) if isinstance(td, dict) else {}
        comp = float(fractions.get("COMPRESSION", 0.0))
        equi = float(fractions.get("EQUILIBRIUM", 0.0))
        rare = float(fractions.get("RAREFACTION", 0.0))

        if comp + equi + rare == 0.0:
            comp = equi = rare = 1.0 / 3.0

        collapse = collapse_distribution([rare, equi, comp])

        # Harmonic entropy contribution for the z-axis
        harmonic_certainty = 0.0
        harmonics = diag.quantum_harmonics
        if harmonics is not None:
            # QuantumHarmonicSuperposition exposes its amplitudes under
            # a few possible names across the module history; probe for
            # the first list-valued attribute that looks like a
            # probability distribution.
            for attr in ("probability_amplitudes", "amplitudes", "probabilities"):
                vals = getattr(harmonics, attr, None)
                if vals:
                    probs = [abs(v) for v in vals]
                    if sum(probs) > 0:
                        harmonic_certainty = (
                            1.0 - collapse_distribution(probs).normalised_entropy
                        )
                    break

        vec = (
            comp - rare,          # signed pressure balance
            equi,                 # equilibrium dwell
            harmonic_certainty,   # spectral focus
        )

        regime = collapse.regime
        confidence = 1.0 - collapse.normalised_entropy

        scalar_strength = _rms(geometry.get("amplitude", []) or [])

        metadata = {
            "compression_fraction": comp,
            "equilibrium_fraction": equi,
            "rarefaction_fraction": rare,
            "ternary_stance": td.get("ternary_stance"),
            "symmetry_score": td.get("symmetry_score"),
        }

        return BasinSignature(
            domain=self.domain,
            regime=regime,
            vector=vec,
            confidence=confidence,
            scalar_strength=scalar_strength,
            metadata=metadata,
        )


__all__ = ["SoundIntersectionRule"]
