"""
probability_collapse — ternary replacement for argmax-style collapse.

Every site in the repo that does ``np.argmax(probabilities)`` throws
away the full shape of the distribution — the second-most-likely
state, the tail mass, and the entropy. This module exposes one
dataclass, ``DistributionCollapse``, that keeps all of that and
provides a single integer compatible with the old ``argmax`` callers:
``collapse.dominant_index``.

That means an existing call site can be upgraded non-invasively:

    # before
    idx = int(np.argmax(probs))

    # after
    collapse = collapse_distribution(probs)
    idx = collapse.dominant_index             # same integer as before
    runner_up = collapse.runner_up_index      # new information
    entropy_bits = collapse.entropy_bits      # new information
    regime = collapse.regime                  # FOCUSED / MIXED / DIFFUSE

The regime classification is the ternary recovery the alternative
bridge cares about: a sharply peaked distribution (low entropy) and
a nearly uniform one (high entropy) are physically distinct even when
they share the same argmax.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Sequence, Tuple


class DistributionRegime(IntEnum):
    """Ternary classification of how concentrated a probability vector is."""

    FOCUSED = 1    # dominant mass ≥ focused_threshold     (sharp peak)
    MIXED   = 0    # neither focused nor diffuse             (transitional)
    DIFFUSE = -1   # dominant mass ≤ diffuse_threshold      (near-uniform)

    @property
    def symbol(self) -> str:
        return {self.FOCUSED: "●", self.MIXED: "◐", self.DIFFUSE: "○"}[self]


@dataclass
class DistributionCollapse:
    """
    Full-shape view over a probability vector.

    All fields are plain Python scalars so the dataclass is trivially
    JSON-serialisable.

    Attributes
    ----------
    dominant_index / dominant_probability
        Index and probability of the top state — matches
        ``int(np.argmax(probs))`` and ``float(probs[argmax])``.
    runner_up_index / runner_up_probability
        Second-place state. ``None`` when the input vector has length 1.
    margin
        ``dominant_probability - runner_up_probability``. Zero or near-
        zero values mean the collapse is effectively a coin-flip.
    entropy_bits
        Shannon entropy of the distribution in bits. Uniform over N
        states gives ``log2(N)``; a one-hot gives 0.
    normalised_entropy
        ``entropy_bits / log2(N)`` — fraction of the maximum possible
        entropy for the state count. 0 = fully focused, 1 = uniform.
    regime
        Ternary classification derived from ``normalised_entropy``.
    """

    probabilities: Tuple[float, ...]
    dominant_index: int
    dominant_probability: float
    runner_up_index: Optional[int]
    runner_up_probability: float
    margin: float
    entropy_bits: float
    normalised_entropy: float
    regime: DistributionRegime = field(default=DistributionRegime.MIXED)

    def top_k(self, k: int = 3) -> Tuple[Tuple[int, float], ...]:
        """Return the ``k`` highest (index, probability) pairs, descending."""
        indexed = sorted(
            enumerate(self.probabilities),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return tuple(indexed[:k])

    def summary(self) -> str:
        """Human-readable one-line description."""
        return (
            f"regime={self.regime.name} {self.regime.symbol} "
            f"idx={self.dominant_index} p={self.dominant_probability:.3f} "
            f"margin={self.margin:.3f} "
            f"H={self.entropy_bits:.3f} bits "
            f"(H_norm={self.normalised_entropy:.2f})"
        )


def collapse_distribution(
    probabilities: Sequence[float],
    focused_threshold: float = 0.35,
    diffuse_threshold: float = 0.75,
) -> DistributionCollapse:
    """
    Build a :class:`DistributionCollapse` from a probability vector.

    Parameters
    ----------
    probabilities
        Sequence of non-negative numbers. The function normalises them
        automatically; an all-zero vector is treated as uniform.
    focused_threshold
        Distributions whose normalised entropy is ≤ this value are
        classified as ``FOCUSED``. Default 0.35 (empirically "sharp").
    diffuse_threshold
        Distributions whose normalised entropy is ≥ this value are
        classified as ``DIFFUSE``. Default 0.75 ("near-uniform").
    """
    if not probabilities:
        raise ValueError("probabilities must be a non-empty sequence")

    values = [float(p) for p in probabilities]
    if any(p < 0 for p in values):
        raise ValueError("probabilities must be non-negative")

    total = sum(values)
    n = len(values)
    if total == 0.0:
        normalised = [1.0 / n] * n
    else:
        normalised = [p / total for p in values]

    # Dominant / runner-up via a single pass rather than a full sort —
    # argmax callers don't need the full ordering.
    dominant_idx = 0
    dominant_val = normalised[0]
    runner_idx: Optional[int] = None
    runner_val = -1.0
    for i, p in enumerate(normalised[1:], start=1):
        if p > dominant_val:
            runner_idx, runner_val = dominant_idx, dominant_val
            dominant_idx, dominant_val = i, p
        elif p > runner_val:
            runner_idx, runner_val = i, p

    if runner_idx is None:
        runner_val = 0.0

    # Shannon entropy, base-2, with the usual 0·log(0) = 0 convention.
    entropy_bits = 0.0
    for p in normalised:
        if p > 0.0:
            entropy_bits -= p * math.log2(p)

    max_entropy = math.log2(n) if n > 1 else 1.0
    normalised_entropy = entropy_bits / max_entropy if max_entropy > 0 else 0.0

    if normalised_entropy <= focused_threshold:
        regime = DistributionRegime.FOCUSED
    elif normalised_entropy >= diffuse_threshold:
        regime = DistributionRegime.DIFFUSE
    else:
        regime = DistributionRegime.MIXED

    return DistributionCollapse(
        probabilities=tuple(normalised),
        dominant_index=dominant_idx,
        dominant_probability=dominant_val,
        runner_up_index=runner_idx,
        runner_up_probability=float(runner_val),
        margin=dominant_val - float(runner_val),
        entropy_bits=entropy_bits,
        normalised_entropy=normalised_entropy,
        regime=regime,
    )


__all__ = [
    "DistributionRegime",
    "DistributionCollapse",
    "collapse_distribution",
]
