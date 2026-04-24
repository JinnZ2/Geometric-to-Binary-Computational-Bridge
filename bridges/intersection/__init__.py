"""
Intersection layer — cross-domain coupling for the Mandala.

Why this layer exists
---------------------
The bridges package turns a single domain's geometry into a per-domain
diagnostic. The Mandala above it layers N of those diagnostics as N
independent channels. That is not sensor fusion — it is a wrapper around
parallel pipes that happens to share an envelope.

The intersection layer supplies the missing coupling: one
:class:`IntersectionRule` per domain distils that domain's diagnostic
into a compact :class:`BasinSignature`, and :func:`resonate` composes
two or more signatures into a *coupled* signature whose regime reflects
agreement or conflict between the source domains.

Design contract
---------------
* Every domain that participates in the Mandala exposes an
  ``IntersectionRule`` subclass and registers it in
  :data:`bridges.intersection.registry.DOMAIN_RULES`.
* Each rule's ``signature(geometry)`` returns a ``BasinSignature``
  grounded in the domain's real physics — not a toy projector. Rules
  delegate to the existing ``*_alternative_compute`` module so the
  ternary / quantum / stochastic analysis already done there is
  reused, not reimplemented.
* :func:`resonate` never runs a physics calculation of its own. It
  composes signatures, period. Any disagreement between two
  signatures is surfaced as the coupled signature's ``regime`` and
  ``coupling_strength``.

Public API:

    BasinSignature          — frozen dataclass carrying regime + vector
    IntersectionRule        — ABC; subclass per domain
    resonate                — pairwise or N-ary cross-domain coupling
    DOMAIN_RULES            — domain-name → IntersectionRule instance
"""

from bridges.intersection.base import (
    BasinSignature,
    CoupledSignature,
    IntersectionRule,
)
from bridges.intersection.resonate import resonate, resonate_many
from bridges.intersection.registry import (
    DOMAIN_RULES,
    get_rule,
    register_rule,
    registered_domains,
)

__all__ = [
    "BasinSignature",
    "CoupledSignature",
    "IntersectionRule",
    "resonate",
    "resonate_many",
    "DOMAIN_RULES",
    "get_rule",
    "register_rule",
    "registered_domains",
]
