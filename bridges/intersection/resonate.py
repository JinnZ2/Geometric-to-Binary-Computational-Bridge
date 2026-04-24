"""
RESONATE — cross-domain coupling for BasinSignatures.

``resonate(sig_a, sig_b)`` composes two basin signatures into a single
:class:`~bridges.intersection.base.CoupledSignature`. It is pure
arithmetic — no physics runs here. The individual
:class:`~bridges.intersection.base.IntersectionRule` subclasses are
responsible for grounding their signatures in real domain physics;
``resonate`` only asks whether those grounded signatures agree.

Two-signature composition rules
-------------------------------
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

* **Scalar strength**: harmonic combination ``2ab / (a + b)`` — a pair
  where one domain is near-zero contributes little, matching the
  intuition that a silent channel cannot amplify its neighbour.

N-ary composition (``resonate_many``)
-------------------------------------
The N ≥ 3 path is a *direct* weighted mean across all inputs, not an
iterative left-fold. The pair formulas above generalise straight to
their N-ary analogs (single weighted mean, mean of pairwise dot
products, N-ary geometric / harmonic means). The result is genuinely
independent of the iteration order of the input sequence. See
``resonate_many`` for the exact rules.
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
    Compose three or more signatures into a coupled basin.

    Computed as a *direct N-ary operation*, not an iterative fold.
    An iterative left-fold is order-dependent (the intermediate
    confidence of step ``k`` reweights step ``k+1``) and would produce
    different outputs for different input orderings. The N-ary formula
    uses a single weighted mean over all inputs at once, which makes
    the result genuinely order-independent modulo floating-point tie
    handling in the regime vote.

    Composition rules for N signatures:

    * **Vector** — confidence-weighted mean across all N input vectors,
      zero-padded to the longest input.
    * **Coupling strength** — mean of all :math:`\\binom{N}{2}` pairwise
      dot products of unit-normalised input vectors. Reduces to the
      pairwise ``resonate`` definition when N = 2.
    * **Regime** — majority vote across all N regimes, with MIXED as
      the tiebreaker.
    * **Agreement regime** — the single shared regime if all N agree,
      otherwise MIXED.
    * **Confidence** — geometric mean of the N input confidences,
      multiplied by the alignment factor ``(mean_coupling + 1) / 2``.
    * **Scalar strength** — N-ary harmonic mean of the N input
      scalars (returns 0 if any input is zero, matching the pairwise
      rule that a silent channel cannot amplify its neighbours).

    The returned coupled signature's ``sources`` tuple is a flat list
    of every original :class:`BasinSignature` that participated, in
    iteration order.

    Parameters
    ----------
    signatures
        Iterable of at least two :class:`BasinSignature` objects.
        Elements may themselves be :class:`CoupledSignature` — every
        BasinSignature attribute is delegated, so re-feeding coupled
        outputs is a valid form of tree composition.

    Raises
    ------
    ValueError
        If fewer than two signatures are supplied, or any signature
        has an empty vector.
    """
    sigs: List[BasinSignature] = list(signatures)
    n = len(sigs)
    if n < 2:
        raise ValueError(
            "resonate_many needs at least two signatures; "
            f"got {n}."
        )
    if n == 2:
        # Delegate so the two-signature path matches ``resonate`` exactly
        # (and inherits its source-tuple semantics for pair composition).
        return resonate(sigs[0], sigs[1])

    for s in sigs:
        if not s.vector:
            raise ValueError(
                "cannot resonate signatures with empty vectors"
            )

    # --- Vectors (padded + confidence-weighted mean) ---
    length = max(len(s.vector) for s in sigs)
    padded = [_pad(s.vector, length) for s in sigs]
    weights = [float(s.confidence) for s in sigs]
    w_sum = sum(weights)
    if w_sum <= 0.0:
        # All-zero confidence degenerates to an unweighted mean so the
        # result is still well-defined.
        weights = [1.0] * n
        w_sum = float(n)

    fused_vec = tuple(
        sum(w * v[i] for w, v in zip(weights, padded)) / w_sum
        for i in range(length)
    )

    # --- Coupling strength (mean of pairwise dot products) ---
    units = [_normalise(v) for v in padded]
    pair_dots: List[float] = []
    for i in range(n):
        for j in range(i + 1, n):
            pair_dots.append(_dot(units[i], units[j]))
    mean_coupling = sum(pair_dots) / len(pair_dots) if pair_dots else 0.0
    mean_coupling = max(-1.0, min(1.0, mean_coupling))

    # --- Regimes ---
    regimes = [s.regime for s in sigs]
    regime = _combine_regimes(regimes)
    all_agree = all(r == regimes[0] for r in regimes)
    agreement_regime = regimes[0] if all_agree else DistributionRegime.MIXED

    # --- Confidence (geometric mean × alignment) ---
    w_product = 1.0
    for w in weights:
        w_product *= max(0.0, w)
    base_confidence = w_product ** (1.0 / n) if w_product > 0.0 else 0.0
    alignment_factor = (mean_coupling + 1.0) / 2.0
    confidence = max(0.0, min(1.0, base_confidence * alignment_factor))

    # --- Scalar strength (N-ary harmonic mean) ---
    strengths = [float(s.scalar_strength) for s in sigs]
    if all(x > 0.0 for x in strengths):
        scalar = n / sum(1.0 / x for x in strengths)
    else:
        scalar = 0.0

    composed_name = "⋈".join(s.domain for s in sigs)

    coupled_basin = BasinSignature(
        domain=composed_name,
        regime=regime,
        vector=fused_vec,
        confidence=confidence,
        scalar_strength=scalar,
        metadata={
            "coupling_strength": mean_coupling,
            "agreement": agreement_regime.name,
            "source_domains": tuple(s.domain for s in sigs),
            "pair_dot_products": tuple(pair_dots),
        },
    )

    return CoupledSignature(
        basin=coupled_basin,
        sources=tuple(sigs),
        coupling_strength=mean_coupling,
        agreement_regime=agreement_regime,
    )


__all__ = ["resonate", "resonate_many"]
