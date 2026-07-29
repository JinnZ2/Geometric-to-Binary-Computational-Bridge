"""
The seventeen translation lenses, in one place.

Each lens maps the same four core quantities ``(R, A, D, L)`` into the
vocabulary of one tradition or discipline.  The claim these were written to
support is NEG-7: that seventeen worldviews are surface renderings of one
deep grammar, evidenced by every pair of lens trajectories correlating
above 0.88.

Read the coefficients below before believing that.  Fourteen of the
seventeen are literally the same function::

    M  =  (a*R) * (b*A + c) * (d*D + e)  -  f*L

with only the six constants changing, and all six drawn from narrow ranges.
Three deviate slightly: ``geometric`` raises ``R`` to 1.2, and ``bayesian``
and ``ai`` add a ``(1 - R)`` term to the loss.  A near-perfect correlation
between two affine reparameterisations of the same four numbers is
arithmetic, not evidence of a shared cosmology.

``lens_collapse_test.py`` is the falsifier: it draws random coefficients
from the same ranges, gives the fake lenses no cultural content at all, and
checks whether they reproduce the same correlation floor.  If they do, the
result is a property of the functional form and the named coefficients are
doing no work.

These functions were previously defined twice -- once in ``bridge.py``
(which was a paste dump that did not import) and once in
``lens_playground.py``.  This module is now the single definition; both
consumers import from here.

Stdlib only.
"""

from __future__ import annotations

from typing import Callable, Dict, Tuple

__all__ = [
    "LENS_REGISTRY",
    "LENS_COEFFICIENTS",
    "CANONICAL_FORM_EXCEPTIONS",
    "canonical_lens",
]

Lens = Callable[[float, float, float, float], float]


# ---------------------------------------------------------------------------
# Scientific / formal lenses
# ---------------------------------------------------------------------------

def lens_thermodynamic(R: float, A: float, D: float, L: float) -> float:
    """Constructive work minus waste and mis-tuning."""
    return (R * A * D) - L


def lens_geometric(R: float, A: float, D: float, L: float) -> float:
    """Curiosity-saturated: superlinear in coherence.

    Not in the canonical form -- ``R**1.2`` is the only nonlinearity in the
    whole registry.
    """
    return (R ** 1.2 * A * D) - L * 0.9


def lens_bayesian(R: float, A: float, D: float, L: float) -> float:
    """Accuracy * epistemic value * entropy, minus free energy.

    Not in the canonical form: the loss picks up a ``(1 - R)`` term, and the
    epistemic factor multiplies ``A`` by ``(1 + D)`` rather than adding an
    affine ``D`` factor.
    """
    accuracy = R
    epistemic = A * (1.0 + D)
    entropy = D * 0.5 + 0.5
    free_energy = L + (1.0 - R) * 0.5
    return (accuracy * epistemic * entropy) - free_energy


def lens_ai(R: float, A: float, D: float, L: float) -> float:
    """Alignment: coherence * plasticity * representational rank, minus penalty.

    Not in the canonical form -- collapse penalty adds ``(1 - R) * 0.3``.
    """
    coherence = R * 1.1
    plasticity = A * 1.3
    rank = D * 0.9 + 0.3
    return (coherence * plasticity * rank) - (L + (1.0 - R) * 0.3)


# ---------------------------------------------------------------------------
# Cultural lenses
#
# Every one of these is canonical form.  The vocabulary in the docstrings is
# the entire difference between them; the arithmetic differs only in six
# constants.  That is the point NEG-7 has to answer for.
# ---------------------------------------------------------------------------

def lens_indigenous(R: float, A: float, D: float, L: float) -> float:
    """Web health: obligation weight, role plasticity, relation types, ruptures."""
    return (R * 1.2) * (A * 0.8 + 0.2) * (D * 2.0 + 1.0) - L * 0.5


def lens_maori(R: float, A: float, D: float, L: float) -> float:
    """Mauri: spiritual ties, restoration capacity, domain breadth, tapu breach."""
    return (R * 1.5) * (A * 0.7 + 0.3) * (D * 1.8 + 1.0) - L * 0.6


def lens_iching(R: float, A: float, D: float, L: float) -> float:
    """Hexagram harmony: static lines, agility, trigram diversity, imbalance."""
    return (R * 0.8 + 0.2) * (A * 0.6 + 0.4) * (D * 2.5 + 0.5) - L * 0.7


def lens_aboriginal(R: float, A: float, D: float, L: float) -> float:
    """Songline resonance, mob mobility, Country diversity, disconnection."""
    return (R * 1.3) * (A * 0.9 + 0.1) * (D * 2.0 + 0.5) - L * 0.7


def lens_ubuntu(R: float, A: float, D: float, L: float) -> float:
    """Ubuntu density, council agility, clan variety, social fragmentation."""
    return (R * 1.4) * (A * 1.1) * (D * 1.5 + 1.0) - L * 0.8


def lens_sami(R: float, A: float, D: float, L: float) -> float:
    """Sielu balance, nomadic flexibility, seasonal richness, colonial disruption."""
    return (R * 1.2) * (A * 1.3) * (D * 1.7 + 0.5) - L * 0.9


def lens_ainu(R: float, A: float, D: float, L: float) -> float:
    """Kamuy connection, iomante flexibility, ecosystem variety, kamuy neglect."""
    return (R * 1.1) * (A * 1.0) * (D * 2.2 + 0.5) - L * 0.6


def lens_inuit(R: float, A: float, D: float, L: float) -> float:
    """Silap balance, ice mobility, prey variety, climate misalignment."""
    return (R * 1.3) * (A * 1.4) * (D * 1.9 + 0.5) - L * 1.1


def lens_taoist(R: float, A: float, D: float, L: float) -> float:
    """Ziran naturalness, yi change-agility, yin-yang contrast, wei forcing."""
    return (R * 1.0) * (A * 1.2 + 0.1) * (D * 1.6 + 0.5) - L * 0.8


def lens_buddhist(R: float, A: float, D: float, L: float) -> float:
    """Dharmakaya interconnection, upaya, dukkha variety, tanha."""
    return (R * 1.2) * (A * 1.1 + 0.1) * (D * 1.4 + 0.5) - L * 1.0


def lens_vedantic(R: float, A: float, D: float, L: float) -> float:
    """Rta cosmic order, yoga union, guna variety, maya obscuration."""
    return (R * 1.3) * (A * 1.0) * (D * 1.8 + 0.5) - L * 0.9


def lens_pueblo(R: float, A: float, D: float, L: float) -> float:
    """Kiva equilibrium, clan rotation, moiety variety, drought."""
    return (R * 1.1) * (A * 1.3) * (D * 1.5 + 0.5) - L * 1.2


def lens_celtic(R: float, A: float, D: float, L: float) -> float:
    """Tuath cohesion, imbas inspiration, Otherworld variety, Brehon breach."""
    return (R * 1.2) * (A * 1.4) * (D * 1.9 + 0.5) - L * 0.8


LENS_REGISTRY: Dict[str, Lens] = {
    "Thermodynamic": lens_thermodynamic,
    "Geometric": lens_geometric,
    "Bayesian": lens_bayesian,
    "Indigenous": lens_indigenous,
    "Māori": lens_maori,
    "I-Ching": lens_iching,
    "AI Alignment": lens_ai,
    "Aboriginal": lens_aboriginal,
    "Ubuntu": lens_ubuntu,
    "Sámi": lens_sami,
    "Ainu": lens_ainu,
    "Inuit": lens_inuit,
    "Taoist": lens_taoist,
    "Buddhist": lens_buddhist,
    "Vedantic": lens_vedantic,
    "Pueblo": lens_pueblo,
    "Celtic": lens_celtic,
}

#: Coefficients ``(a, b, c, d, e, f)`` of the canonical form
#: ``(a*R) * (b*A + c) * (d*D + e) - f*L``, for the lenses that are in it.
LENS_COEFFICIENTS: Dict[str, Tuple[float, float, float, float, float, float]] = {
    "Thermodynamic": (1.0, 1.0, 0.0, 1.0, 0.0, 1.0),
    "Indigenous": (1.2, 0.8, 0.2, 2.0, 1.0, 0.5),
    "Māori": (1.5, 0.7, 0.3, 1.8, 1.0, 0.6),
    "Aboriginal": (1.3, 0.9, 0.1, 2.0, 0.5, 0.7),
    "Ubuntu": (1.4, 1.1, 0.0, 1.5, 1.0, 0.8),
    "Sámi": (1.2, 1.3, 0.0, 1.7, 0.5, 0.9),
    "Ainu": (1.1, 1.0, 0.0, 2.2, 0.5, 0.6),
    "Inuit": (1.3, 1.4, 0.0, 1.9, 0.5, 1.1),
    "Taoist": (1.0, 1.2, 0.1, 1.6, 0.5, 0.8),
    "Buddhist": (1.2, 1.1, 0.1, 1.4, 0.5, 1.0),
    "Vedantic": (1.3, 1.0, 0.0, 1.8, 0.5, 0.9),
    "Pueblo": (1.1, 1.3, 0.0, 1.5, 0.5, 1.2),
    "Celtic": (1.2, 1.4, 0.0, 1.9, 0.5, 0.8),
}

#: Lenses that are not in the canonical form, and how they leave it.
#: Thirteen of seventeen are canonical; these four are the whole of the
#: structural variety in the registry, and three of the four differ only by
#: an added ``(1 - R)`` term in the loss.
CANONICAL_FORM_EXCEPTIONS: Dict[str, str] = {
    "Geometric": "R**1.2 instead of a*R",
    "Bayesian": "loss carries (1-R)*0.5; A multiplied by (1+D)",
    "AI Alignment": "loss carries (1-R)*0.3",
    "I-Ching": "affine in R (0.8*R + 0.2), not a bare a*R factor",
}


def canonical_lens(a: float, b: float, c: float,
                   d: float, e: float, f: float) -> Lens:
    """Build a lens from canonical-form coefficients.

    Used by the falsifier to construct lenses that have the same functional
    form as the named ones and no cultural content whatsoever.
    """
    def _lens(R: float, A: float, D: float, L: float) -> float:
        return (a * R) * (b * A + c) * (d * D + e) - f * L
    return _lens
