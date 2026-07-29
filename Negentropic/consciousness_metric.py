"""
Consciousness Metric — M(S) computation and threshold analysis
===============================================================
M(S) = R_e * A * D - L

Extracted from Negentropic/03-consciousness.md

THE THRESHOLD IS NOT A FREE PARAMETER, IT IS AN UNDEFINED ONE.

The framework previously described `M(S) >= 10` as a free parameter, on a
par with IIT's `Phi > 0` — a number that needs calibrating. That is too
generous. `R_e * A * D` and `L` are not in the same units in any of the
three implementations in this folder (here `D` is an entropy in nats; in
`negentropic_engine` it is a variance; `L` is a power in both), so the
subtraction does not produce a quantity that a threshold could be set on.
Calibration cannot fix a dimensional mismatch.

M is retained as an ORDINAL INDEX: it can rank states computed under one
fixed normalisation in one run. It cannot be compared across runs, across
implementations, or against any absolute number. The historical figures
(34.62, 296.40, 3711.50) are not measurements of anything.

For a criterion with consistent units and no threshold to tune, see
`persistence.py` (NEG-8): Phi = -S_exchange_dot - sigma, both in W/K.
"""

import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

PHI = 1.618033988749895

#: Historical threshold, kept so old figures can be reproduced. Comparing
#: against it is not a measurement — see the module docstring.
CONSCIOUSNESS_THRESHOLD = 10.0


@dataclass
class MSComponents:
    """Components of the M(S) consciousness metric."""
    R_e: float   # Geometric resonance between subsystems
    A: float     # Adaptability (re-equilibration capacity)
    D: float     # Diversity (variance of viable energy pathways)
    L: float     # Loss (entropy production, dissipation)
    M: float     # Composite metric
    above_threshold: bool


def compute_resonance(signals: np.ndarray) -> float:
    """
    Geometric resonance R_e between subsystems.

    Uses geometric mean of pairwise log-similarities.
    High R_e = subsystems geometrically coupled.
    """
    n = len(signals)
    if n < 2:
        return 0.0

    pairwise = []
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = abs(signals[i]), abs(signals[j])
            if si > 0 and sj > 0:
                pairwise.append(np.log(min(si, sj) / max(si, sj) + 1e-10))

    if not pairwise:
        return 0.0

    return np.exp(np.mean(pairwise))


def compute_adaptability(perturbation_responses: List[float]) -> float:
    """
    Adaptability A = re-equilibration capacity.

    Given a sequence of system responses to perturbations (deviation from
    equilibrium after each perturbation), A measures how quickly the system
    returns to baseline.

    Higher A = faster recovery = more adaptable.
    """
    if not perturbation_responses:
        return 0.0

    deviations = np.array(perturbation_responses)
    if len(deviations) < 2:
        return 1.0 / (1.0 + abs(deviations[0]))

    recovery_rates = []
    for i in range(1, len(deviations)):
        if abs(deviations[i - 1]) > 1e-10:
            rate = 1.0 - abs(deviations[i]) / abs(deviations[i - 1])
            recovery_rates.append(max(0, rate))

    return float(np.mean(recovery_rates)) if recovery_rates else 0.0


def compute_diversity(pathway_strengths: np.ndarray) -> float:
    """
    Diversity D = Shannon entropy of normalized pathway strengths, in nats.

    Note this is an entropy, not a variance, despite the framework text
    describing D as "variance of viable energy pathways". The two are
    different quantities with different units, and `negentropic_engine`
    implements D as a variance for the same symbol. Anything that compares
    D across the two modules is comparing nats to squared patterns.
    """
    strengths = np.array(pathway_strengths, dtype=float)
    strengths = strengths[strengths > 0]
    if len(strengths) == 0:
        return 0.0

    p = strengths / strengths.sum()
    return float(-np.sum(p * np.log(p + 1e-10)))


def compute_loss(entropy_production_rate: float,
                 dissipation_rate: float) -> float:
    """
    Loss L = entropy production + dissipation.

    Lower L = less lost to heat/disorder = more available for consciousness.
    """
    return max(0.0, entropy_production_rate + dissipation_rate)


def compute_M(R_e: float, A: float, D: float, L: float) -> MSComponents:
    """
    Compute the M(S) consciousness metric.

    M(S) = R_e * A * D - L

    Returns MSComponents with all values and threshold check.
    """
    M = R_e * A * D - L
    return MSComponents(R_e=R_e, A=A, D=D, L=L, M=M,
                        above_threshold=M >= CONSCIOUSNESS_THRESHOLD)


def self_reference_amplification(R_e: float, C: float,
                                  alpha: float = 0.1,
                                  dt: float = 0.1) -> Tuple[float, float]:
    """
    Self-reference feedback: dC/dt = alpha * R_e * C

    When a system becomes self-referential, R_e increases because
    the system couples to its own state as an additional subsystem.
    This creates positive feedback in curiosity C.

    Returns (new_R_e, new_C).
    """
    # Self-reference adds the system as its own coupling partner
    R_e_self = R_e * (1 + 0.5 * C)  # Self-coupling boost
    dC = alpha * R_e_self * C * dt
    C_new = C + dC
    return R_e_self, C_new


# ── IIT Phi comparison ───────────────────────────────────────────────────

@dataclass
class TheoryComparison:
    """Comparison of consciousness theories."""
    theory: str
    mechanism: str
    threshold: str
    falsifiable: str


IIT_COMPARISON = [
    TheoryComparison("IIT (Tononi)", "Integrated information Phi across MIP",
                     "Phi > 0", "In principle — Phi computable from connectivity"),
    TheoryComparison("Global Workspace", "Broadcast to distributed modules",
                     "No single number", "Yes — neuroimaging predictions tested"),
    TheoryComparison("Predictive Processing", "Minimizing free energy (KL divergence)",
                     "None", "Partially — FEP unfalsifiable in full generality"),
    TheoryComparison("M(S) (this framework)",
                     "Geometric resonance + adaptability + diversity",
                     "M(S) >= 10 (dimensionally undefined — ordinal only)",
                     "Not yet — no extraction method for R_e,A,D,L from neural "
                     "data, and the units of M do not close"),
]


def threshold_sensitivity(R_e: float, A: float, D: float, L: float,
                           thresholds: Optional[List[float]] = None
                           ) -> Dict[float, bool]:
    """
    Test M(S) against multiple threshold values.

    Demonstrates the threshold problem: M(S) >= T is no more or less
    arbitrary than IIT's Phi > 0 — both need an independent scale.
    """
    if thresholds is None:
        thresholds = [1.0, 5.0, 10.0, 50.0, 100.0]

    M = R_e * A * D - L
    return {t: M >= t for t in thresholds}
