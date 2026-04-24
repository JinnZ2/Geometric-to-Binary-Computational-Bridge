"""
RESONATE — cross-domain coupling for BasinSignatures.

``resonate(sig_a, sig_b)`` composes two basin signatures into a single
:class:`~bridges.intersection.base.CoupledSignature`. It is pure
arithmetic — no physics runs here. The individual
:class:`~bridges.intersection.base.IntersectionRule` subclasses are
responsible for grounding their signatures in real domain physics;
``resonate`` only asks whether those grounded signatures agree.

Composition rules
-----------------
* **Vector**: the coupled vector is the confidence-weighted sum of
  the source vectors, re-normalised. Heterogeneous vector lengths are
  zero-padded to the longest input so three-axis gravity and
  two-axis community bases can still be dot-producted.

* **Regime**: majority vote over the source regimes, with ties
  broken toward ``MIXED`` — when two domains disagree in opposite
  directions the coupled basin should not silently claim either one.

* **Coupling strength**: dot product of the two unit-normalised source
  vectors. +1 is agreement; -1 is conflict; 0 is independence.

* **Confidence**: the geometric mean of the source confidences,
  multiplied by ``(coupling_strength + 1) / 2`` so that a highly
  confident but strongly-conflicting pair collapses into a low
  coupled confidence — sensor fusion should get *less* certain when
  its inputs fight, not more.

* **Scalar strength**: weighted harmonic-style combination —
  ``2 * a * b / (a + b)`` — so a pair where one domain is near-zero
  contributes little, matching the intuition that a silent channel
  cannot amplify its neighbour.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, List, Sequence, Tuple

from bridges.intersection.base import (
    BasinSignature,
    CoupledSignature,
)
from bridges.probability_collapse import DistributionRegime


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------

def _pad(vec: Sequence[float], length: int) -> Tuple[float, ...]:
    """Zero-pad ``vec`` on the right to reach ``length`` elements."""
    return tuple(vec) + (0.0,) * max(0, length - len(vec))


def _normalise(vec: Sequence[float]) -> Tuple[float, ...]:
    mag = math.sqrt(sum(x * x for x in vec))
    if mag == 0.0:
        return tuple(vec)
    return tuple(x / mag for x in vec)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return sum(ax * bx for ax, bx in zip(a, b))


def _harmonic(a: float, b: float) -> float:
    """Harmonic-style combination; returns 0 when either input is 0."""
    if a <= 0 or b <= 0:
        return 0.0
    return 2.0 * a * b / (a + b)


# ---------------------------------------------------------------------------
# Regime aggregation
# ---------------------------------------------------------------------------

def _combine_regimes(
    regimes: Sequence[DistributionRegime],
) -> DistributionRegime:
    """
    Majority-vote regime with MIXED as the tiebreaker.

    Two-domain special case: two opposite regimes (FOCUSED vs DIFFUSE)
    collapse to MIXED. Otherwise the shared regime wins, or MIXED if
    there is no majority.
    """
    if not regimes:
        return DistributionRegime.MIXED

    counts = Counter(regimes)
    top_count = max(counts.values())
    winners = [r for r, c in counts.items() if c == top_count]

    if len(winners) == 1:
        return winners[0]
    # Tie: if the tied regimes bracket MIXED (FOCUSED + DIFFUSE), return
    # MIXED. If they include MIXED, prefer MIXED. Otherwise fall back to
    # MIXED as the conservative default.
    return DistributionRegime.MIXED


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def resonate(
    sig_a: BasinSignature,
    sig_b: BasinSignature,
) -> CoupledSignature:
    """
    Compose two :class:`BasinSignature` objects into a coupled signature.

    The output is itself wrapped in a :class:`BasinSignature` so the
    coupled result can be fed into further ``resonate`` calls —
    composition is associative in the weighted-mean sense.

    Raises
    ------
    ValueError
        If either signature's vector is empty (enforced by
        :class:`BasinSignature`, re-checked here for robustness).
    """
    if not sig_a.vector or not sig_b.vector:
        raise ValueError("cannot resonate signatures with empty vectors")

    length = max(len(sig_a.vector), len(sig_b.vector))
    va = _pad(sig_a.vector, length)
    vb = _pad(sig_b.vector, length)

    wa = float(sig_a.confidence)
    wb = float(sig_b.confidence)
    w_sum = wa + wb if (wa + wb) > 0 else 1.0

    fused_vec = tuple(
        (wa * va_i + wb * vb_i) / w_sum
        for va_i, vb_i in zip(va, vb)
    )

    coupling = _dot(_normalise(va), _normalise(vb))
    # dot product may overshoot ±1 by floating-point noise
    coupling = max(-1.0, min(1.0, coupling))

    regime = _combine_regimes([sig_a.regime, sig_b.regime])
    agreement_regime = (
        sig_a.regime if sig_a.regime == sig_b.regime
        else DistributionRegime.MIXED
    )

    base_confidence = math.sqrt(wa * wb) if wa * wb > 0 else 0.0
    alignment_factor = (coupling + 1.0) / 2.0
    confidence = max(0.0, min(1.0, base_confidence * alignment_factor))

    scalar = _harmonic(sig_a.scalar_strength, sig_b.scalar_strength)

    coupled_basin = BasinSignature(
        domain=f"{sig_a.domain}⋈{sig_b.domain}",
        regime=regime,
        vector=fused_vec,
        confidence=confidence,
        scalar_strength=scalar,
        metadata={
            "coupling_strength": coupling,
            "agreement": agreement_regime.name,
            "source_domains": (sig_a.domain, sig_b.domain),
        },
    )

    return CoupledSignature(
        basin=coupled_basin,
        sources=(sig_a, sig_b),
        coupling_strength=coupling,
        agreement_regime=agreement_regime,
    )


def resonate_many(
    signatures: Iterable[BasinSignature],
) -> CoupledSignature:
    """
    Compose three or more signatures by left-folding :func:`resonate`.

    The fold order is deterministic — whatever the caller iterates in.
    Because :func:`resonate` is commutative in the pair sense (its
    output depends only on the two inputs, not their order), the
    fold is effectively N-ary even though each step is binary.

    Unlike the pairwise :func:`resonate`, the returned coupled
    signature's ``sources`` tuple is **flat** — it contains every
    original :class:`BasinSignature` that participated in the fold,
    so callers can trace the full lineage without walking the binary
    reduction tree.
    """
    sigs: List[BasinSignature] = list(signatures)
    if len(sigs) < 2:
        raise ValueError(
            "resonate_many needs at least two signatures; "
            f"got {len(sigs)}."
        )

    acc = resonate(sigs[0], sigs[1])
    for nxt in sigs[2:]:
        acc = resonate(acc.basin, nxt)

    # Replace the binary-tree sources tuple with the original flat list
    # so downstream code sees every contributor.
    return CoupledSignature(
        basin=acc.basin,
        sources=tuple(sigs),
        coupling_strength=acc.coupling_strength,
        agreement_regime=acc.agreement_regime,
    )


__all__ = ["resonate", "resonate_many"]
