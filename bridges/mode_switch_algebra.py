"""
mode_switch_algebra — answer to recognition note open-question 3.

The note asks: *"is the spin-separation operator the same algebra as
the K⁺ mode-switch (allosteric basis change)?"* This module is the
honest answer.

**Short answer: no — they're two flavours of the same pattern, not
one algebra.** Both belong to the broader hidden-channel family
catalogued in :mod:`bridges.hidden_channel_detector`, but they
differ in *when* the scalar→shape projection becomes lossy.

* :data:`ModeSwitchPattern.THRESHOLD_CROSSING` — the substrate's
  scalar value crosses a threshold and the receiver's response basis
  *swaps*. Below threshold: scalar amplitude works. Above: shape
  channel dominates. **K⁺ as ligand** and **EDC × heat** are this
  flavour.

* :data:`ModeSwitchPattern.LATENT_BASIS` — the shape channel is
  *always* present alongside the scalar, and the scalar readout
  *always* undercounts the field's degrees of freedom. There is no
  threshold to cross — it's a basis-truncation that happens at every
  amplitude. **Vectorial spin-separation** is this flavour.

The runtime difference: a threshold-crossing mode switch has an
operating point near the crossing where leverage is maximal (the
"whisper redirects hurricane" regime). A latent-basis system has
*constant* hidden-channel content — no operating-point dependence.
This distinction matters for the audit engine (open-question 4):
the leverage scalar is meaningful for one flavour and trivially
constant for the other.

The module:

* :class:`ModeSwitchPattern` enum.
* :class:`ModeSwitch` frozen dataclass — the unified description
  (input scalar, output shape channel, pattern flavour,
  optional threshold).
* :data:`MODE_SWITCH_REGISTRY` — three concrete instances for the
  three known cases, grounded in their physics.
* :func:`classify_pattern` — heuristic that, given a callable that
  returns leverage as a function of operating point, picks
  THRESHOLD_CROSSING (leverage has a clear peak) or LATENT_BASIS
  (leverage is roughly flat).

The shared *algebra* across all three is just
:class:`bridges.hidden_channel_detector.ShapeChannel` itself —
that's already the unifying type. This module is the *taxonomy*
of how the projection-to-scalar fails in each case.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from bridges.hidden_channel_detector import (
    SHAPE_CHANNEL_REGISTRY,
    ShapeChannel,
)


# ----------------------------------------------------------------------
# Pattern enum
# ----------------------------------------------------------------------

class ModeSwitchPattern(str, Enum):
    """Two ways the scalar→shape projection becomes lossy."""

    THRESHOLD_CROSSING = "threshold_crossing"
    """Scalar substrate crosses a threshold; receiver basis *swaps*.
    Leverage has a clear peak near the threshold. Below: scalar
    amplitude is sufficient. Above: shape channel dominates.

    Examples: K⁺ ion-channel mode switch (DmAlka),
    EDC × heat receptor-pose mode switch."""

    LATENT_BASIS = "latent_basis"
    """Shape channel is always present; scalar readout always
    undercounts. No threshold; leverage is roughly flat across
    operating points. Examples: vectorial spin-separation in EM
    fields."""


# ----------------------------------------------------------------------
# ModeSwitch
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class ModeSwitch:
    """Unified description of one mode-switch instance.

    The same dataclass covers both flavours — the difference lives
    in :attr:`pattern` and whether :attr:`threshold` is meaningful
    (threshold-crossing pattern: yes; latent-basis: ``None``).
    """

    name: str
    """Stable identifier matching keys of
    :data:`MODE_SWITCH_REGISTRY`."""

    pattern: ModeSwitchPattern
    """Which flavour this is."""

    scalar_substrate: str
    """Name of the field's amplitude-channel readout
    (``"ion_concentration_M"``, ``"chemical_concentration_M"``,
    ``"intensity_W_m2"``)."""

    shape_channel: ShapeChannel
    """The orthogonal shape channel this scalar undercounts. Pulled
    from :data:`bridges.hidden_channel_detector.SHAPE_CHANNEL_REGISTRY`
    so the cross-reference stays stable."""

    threshold: Optional[float] = None
    """For ``THRESHOLD_CROSSING`` instances: the substrate value at
    which the response basis swaps. ``None`` for latent-basis
    instances (no meaningful single threshold)."""

    threshold_units: str = ""
    """Unit annotation for ``threshold``; empty for latent-basis."""

    leverage_peak: Optional[float] = None
    """Analytic peak of the d(response)/d(log substrate) sensitivity
    over the operating range. ``None`` if not analytically tractable
    or if pattern is ``LATENT_BASIS`` (where leverage is roughly
    flat)."""

    citation: str = ""
    """One-line literature anchor."""

    metadata: Mapping[str, Any] = field(default_factory=dict)


# ----------------------------------------------------------------------
# Three known instances
# ----------------------------------------------------------------------

# Reading order matches the recognition note: DmAlka first, EDC
# second, vector-spin third.
MODE_SWITCH_REGISTRY: Dict[str, ModeSwitch] = {
    "dmalka_k_plus": ModeSwitch(
        name="dmalka_k_plus",
        pattern=ModeSwitchPattern.THRESHOLD_CROSSING,
        scalar_substrate="ion_concentration_M",
        shape_channel=SHAPE_CHANNEL_REGISTRY["ion_coordination"],
        # The threshold is the [K⁺] at which the four-oxygen
        # coordination cage stably traps a K⁺ ion (~ µM in
        # representative literature). Pattern is binary: empty cage
        # vs. occupied cage. Treated here as a step.
        threshold=1e-6,
        threshold_units="M",
        leverage_peak=None,  # binary switch — leverage is a delta
        citation=(
            "DmAlka chloride-channel allosteric switching by K⁺ "
            "coordination geometry"
        ),
        metadata={"switch_kind": "binary_topological"},
    ),

    "edc_thermal": ModeSwitch(
        name="edc_thermal",
        pattern=ModeSwitchPattern.THRESHOLD_CROSSING,
        scalar_substrate="chemical_concentration_M",
        shape_channel=SHAPE_CHANNEL_REGISTRY["hormone_geometry"],
        # Threshold is apparent Kd — that's what crosses as
        # temperature shifts. The numerical value here is illustrative
        # (BPA at 25 °C, ER-α-shaped); per-EDC values come from
        # bridges/edc_thermal_coupling.py::apparent_Kd.
        threshold=5e-11,
        threshold_units="M",
        # ln(10)/4 — Hill-1 leverage analytic peak.
        leverage_peak=math.log(10.0) / 4.0,
        citation="npj Emerging Contaminants 2026 (DOI 10.1038/s44454-026-00032-6)",
        metadata={
            "switch_kind": "graded_dose_response",
            "module": "bridges.edc_thermal_coupling",
        },
    ),

    "vectorial_spin": ModeSwitch(
        name="vectorial_spin",
        pattern=ModeSwitchPattern.LATENT_BASIS,
        scalar_substrate="intensity_W_m2",
        shape_channel=SHAPE_CHANNEL_REGISTRY["spin_separation"],
        threshold=None,
        threshold_units="",
        leverage_peak=None,  # latent basis — no peak, by design
        citation="Light: Sci & Appl 2026 (DOI 10.1038/s41377-026-02278-6)",
        metadata={
            "switch_kind": "always_present_orthogonal_basis",
            "driver": "sensing.firmware.sensor_drivers.light_polarization",
        },
    ),
}


def get_mode_switch(name: str) -> ModeSwitch:
    """Return a registered :class:`ModeSwitch` or raise ``KeyError``."""
    if name not in MODE_SWITCH_REGISTRY:
        raise KeyError(
            f"No mode switch registered under {name!r}. "
            f"Known: {sorted(MODE_SWITCH_REGISTRY)}"
        )
    return MODE_SWITCH_REGISTRY[name]


def known_instances_by_pattern(
    pattern: ModeSwitchPattern,
) -> Sequence[ModeSwitch]:
    """All registered instances with the given pattern flavour."""
    return tuple(
        ms for ms in MODE_SWITCH_REGISTRY.values() if ms.pattern == pattern
    )


# ----------------------------------------------------------------------
# Pattern classifier
# ----------------------------------------------------------------------

def classify_pattern(
    leverage_at: Callable[[float], float],
    operating_points: Sequence[float],
    *,
    peak_to_baseline_ratio: float = 4.0,
) -> ModeSwitchPattern:
    """Classify an unknown system by its leverage profile.

    Parameters
    ----------
    leverage_at
        Callable returning leverage in [0, 1] for a given operating
        point (typically log-spaced substrate concentration / scalar
        amplitude).
    operating_points
        Where to sample. Use a wide log-spaced range — the test is
        whether leverage has a clear peak in there.
    peak_to_baseline_ratio
        How much the peak must exceed the median sample to count as
        a threshold-crossing pattern. Default 4× is conservative;
        leverage profiles under Hill-1 typically show a peak
        ratio > 6× across a 6-decade sweep.

    Returns
    -------
    ModeSwitchPattern
        ``THRESHOLD_CROSSING`` if the peak is clearly above the
        median; ``LATENT_BASIS`` otherwise.
    """
    if len(operating_points) < 3:
        raise ValueError(
            "need at least three operating points to classify"
        )
    levs = [max(0.0, float(leverage_at(x))) for x in operating_points]
    if all(L == 0.0 for L in levs):
        return ModeSwitchPattern.LATENT_BASIS
    peak = max(levs)
    baseline = statistics.median(levs)
    if baseline <= 0:
        # All near-zero with a single non-zero peak → threshold.
        return (
            ModeSwitchPattern.THRESHOLD_CROSSING
            if peak > 0 else ModeSwitchPattern.LATENT_BASIS
        )
    return (
        ModeSwitchPattern.THRESHOLD_CROSSING
        if peak / baseline >= peak_to_baseline_ratio
        else ModeSwitchPattern.LATENT_BASIS
    )


__all__ = [
    "ModeSwitchPattern",
    "ModeSwitch",
    "MODE_SWITCH_REGISTRY",
    "get_mode_switch",
    "known_instances_by_pattern",
    "classify_pattern",
]
