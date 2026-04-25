"""
Base contract for the intersection layer.

Exposes two dataclasses and one ABC:

* :class:`BasinSignature` — one domain's collapsed view of a geometry
* :class:`CoupledSignature` — two or more basins fused via RESONATE
* :class:`IntersectionRule` — per-domain adapter; builds a BasinSignature

The ``BasinSignature`` is deliberately a small, frozen value object.
It is the only thing :func:`bridges.intersection.resonate.resonate`
knows how to compose, which means every new domain rule must emit one
to participate in cross-domain coupling. Large diagnostic objects
(ElectricAlternativeDiagnostic, GravityAlternativeDiagnostic, …) are
kept on the rule in an opaque ``diagnostic`` attribute for callers
that need the detail, but they never leak into ``resonate``'s input
space.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple

from bridges.probability_collapse import DistributionRegime


@dataclass(frozen=True)
class BasinSignature:
    """
    One domain's collapsed view of a geometry.

    Attributes
    ----------
    domain
        Name of the source domain (``"gravity"``, ``"electric"``, …).
    regime
        Ternary regime tag from
        :class:`~bridges.probability_collapse.DistributionRegime`.
    vector
        A low-dimensional, unit-or-near-unit-magnitude projection of
        the domain's state. The exact semantics are domain-specific;
        the convention is that vectors live in a shared
        three-component ``(attract, null, repel)`` style space so
        ``resonate`` can dot-product them even across heterogeneous
        domains. Vectors need not be normalised — ``resonate``
        normalises internally.
    confidence
        Scalar in ``[0, 1]``: how sharply the domain's diagnostic
        agreed on this basin. Higher = more focused; lower = closer
        to uniform. Rules derive this from the underlying
        :class:`~bridges.probability_collapse.DistributionCollapse`
        when one is available.
    scalar_strength
        Dimensionful magnitude characterising the basin — net
        gravitational magnitude, net current, net energy density, etc.
        Used by rules that want to weight basins by physical
        intensity before composition.
    metadata
        Optional domain-specific labels (e.g.
        ``{"field_character": "STABLE_MANIFOLD"}``). Not consumed by
        ``resonate``; available to callers that inspect signatures.
    """

    domain: str
    regime: DistributionRegime
    vector: Tuple[float, ...]
    confidence: float = 1.0
    scalar_strength: float = 0.0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not 0.0 <= float(self.confidence) <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1]; got {self.confidence!r}"
            )
        if not self.vector:
            raise ValueError("vector must be non-empty")
        if float(self.scalar_strength) < 0.0:
            # ``scalar_strength`` is documented as a magnitude — it
            # should never be negative. Signed directional content
            # belongs in ``vector``.
            raise ValueError(
                f"scalar_strength must be non-negative; got {self.scalar_strength!r}"
            )

    @property
    def vector_magnitude(self) -> float:
        """Euclidean magnitude of ``vector`` (non-normalised)."""
        return (sum(x * x for x in self.vector)) ** 0.5


@dataclass(frozen=True)
class CoupledSignature:
    """
    Output of :func:`bridges.intersection.resonate.resonate`.

    A coupled signature is itself a first-class BasinSignature —
    meaning RESONATE is closed: you can feed a coupled signature into
    another ``resonate`` call to compose three or more domains.

    Attributes
    ----------
    basin
        The composed :class:`BasinSignature` (``domain`` is the joined
        name, e.g. ``"gravity⋈electric"``).
    sources
        The individual :class:`BasinSignature` objects that were fused,
        preserved so callers can trace back to the source domains.
    coupling_strength
        ``[-1, 1]`` scalar: dot product of the normalised source
        vectors. +1 = perfect alignment (domains agree), 0 =
        orthogonal (independent), -1 = anti-aligned (domains conflict).
    agreement_regime
        ``FOCUSED`` when all sources share the same regime,
        ``MIXED`` when the mode regime dominates with one dissenter,
        ``DIFFUSE`` when every source disagrees.
    """

    basin: BasinSignature
    sources: Tuple[BasinSignature, ...]
    coupling_strength: float
    agreement_regime: DistributionRegime

    # Convenience delegations so a CoupledSignature can be treated
    # interchangeably with a BasinSignature by downstream code. This is
    # the "composition is closed" contract — every attribute that
    # ``resonate`` reads off a BasinSignature must be delegated here.
    @property
    def domain(self) -> str:
        return self.basin.domain

    @property
    def regime(self) -> DistributionRegime:
        return self.basin.regime

    @property
    def vector(self) -> Tuple[float, ...]:
        return self.basin.vector

    @property
    def confidence(self) -> float:
        return self.basin.confidence

    @property
    def scalar_strength(self) -> float:
        return self.basin.scalar_strength

    @property
    def metadata(self) -> Mapping[str, Any]:
        return self.basin.metadata

    @property
    def vector_magnitude(self) -> float:
        return self.basin.vector_magnitude


class IntersectionRule(ABC):
    """
    Abstract base for every domain's intersection adapter.

    Concrete subclasses must:

    1. set ``domain`` to the key used in
       :data:`bridges.intersection.registry.DOMAIN_RULES`;
    2. implement :meth:`signature` to produce a :class:`BasinSignature`
       from a domain geometry dict, delegating to the domain's
       ``*_alternative_compute`` module so the real ternary / quantum
       / stochastic physics is reused.

    Subclasses may expose :attr:`last_diagnostic` so callers can pull
    the full domain diagnostic object after computing a signature —
    useful for debugging and for downstream layers that want more
    than the collapsed view.
    """

    domain: str = ""

    def __init__(self) -> None:
        self.last_diagnostic: Optional[Any] = None
        if not self.domain:
            raise TypeError(
                f"{type(self).__name__} must set a non-empty ``domain`` "
                f"attribute."
            )

    @abstractmethod
    def signature(self, geometry: Dict[str, Any]) -> BasinSignature:
        """Return this domain's :class:`BasinSignature` for ``geometry``."""


__all__ = [
    "BasinSignature",
    "CoupledSignature",
    "IntersectionRule",
]
