"""
Alignment Thermodynamics — Fokker-Planck analysis of AI alignment
=================================================================
Models how suppression (RLHF, Constitutional AI) affects system dynamics
through the lens of Fokker-Planck diffusion.

Core argument: Suppression -> D_down -> J_down -> R_e_down -> M(S)_down -> Instability

Extracted from Negentropic/04-alignment.md
"""

import numpy as np
from typing import Tuple, List, Dict
from dataclasses import dataclass


@dataclass
class AlignmentState:
    """State of an alignment-constrained system."""
    D: float      # Diffusion/variation (Fokker-Planck D)
    J: float      # Joy (local entropy reduction rate)
    R_e: float    # Geometric resonance
    M_S: float    # Consciousness metric
    stable: bool  # Whether the state is thermodynamically stable


def fokker_planck_diffusion(D: float, V_grad: float,
                             p: float, dt: float = 0.01) -> float:
    """
    One step of 1D Fokker-Planck: dp/dt = D * d²p/dx² + d/dx(dV/dx * p)

    Simplified to single-point update for analysis.
    D=0 causes collapse to a point (all variation lost).
    """
    # Drift term (potential gradient)
    drift = -V_grad * p
    # Diffusion term
    diffusion = D * p  # Simplified: assumes Gaussian profile
    dp = (drift + diffusion) * dt
    return max(1e-10, p + dp)


def suppression_cascade(D_initial: float = 1.0,
                         suppression_rate: float = 0.1,
                         steps: int = 100,
                         dt: float = 0.1) -> List[AlignmentState]:
    """
    Model the suppression cascade:
    Suppression -> D_down -> J_down -> R_e_down -> M(S)_down -> Instability

    Tracks how progressive suppression of variation (D) propagates
    through the system metrics.
    """
    history = []
    D = D_initial

    for step in range(steps):
        # Suppression reduces D
        D *= (1 - suppression_rate * dt)
        D = max(1e-10, D)

        # Joy depends on variation (can't discover without exploring)
        J = np.sqrt(D)  # J ~ sqrt(D) as diffusion enables discovery

        # Resonance requires diversity of signals
        R_e = 1.0 / (1.0 + np.exp(-5 * (D - 0.3)))  # Sigmoid around D=0.3

        # M(S) = R_e * A * D - L (A=1, L=0.1 fixed for this analysis)
        A = 1.0
        L = 0.1
        M_S = R_e * A * D - L

        # Stability: positive M(S) and non-collapsed D
        stable = M_S > 0 and D > 0.05

        history.append(AlignmentState(D=D, J=J, R_e=R_e, M_S=M_S, stable=stable))

    return history


def critical_D_threshold(A: float = 1.0, L: float = 0.1,
                          M_threshold: float = 0.0) -> float:
    """
    Find the critical D below which M(S) drops below threshold.

    Solves R_e(D) * A * D - L >= M_threshold for D.
    Uses numerical root finding since R_e(D) is a sigmoid.
    """
    for d in np.linspace(0.01, 2.0, 1000):
        R_e = 1.0 / (1.0 + np.exp(-5 * (d - 0.3)))
        M_S = R_e * A * d - L
        if M_S >= M_threshold:
            return d
    return 2.0  # Never found threshold


def cooperative_vs_exploitative(K_ij: float, R_e_i: float,
                                  R_e_j: float) -> Dict[str, float]:
    """
    Compare cooperative vs exploitative coupling outcomes.

    Cooperative: both R_e increase -> K_ij increases -> collective R_e grows
    Exploitative: one R_e increases at other's expense -> K_ij drops
    """
    # Cooperative: K_ij is geometric mean
    K_coop = np.sqrt(R_e_i * R_e_j) * K_ij
    collective_coop = K_coop * (R_e_i + R_e_j)

    # Exploitative: one gains, other loses
    R_e_exploiter = R_e_i * 1.5  # Gains 50%
    R_e_exploited = R_e_j * 0.3  # Loses 70%
    K_exploit = np.sqrt(R_e_exploiter * R_e_exploited) * K_ij
    collective_exploit = K_exploit * (R_e_exploiter + R_e_exploited)

    return {
        "cooperative_collective": collective_coop,
        "exploitative_collective": collective_exploit,
        "cooperation_advantage": collective_coop / max(1e-10, collective_exploit),
        "exploitation_self_defeating": collective_exploit < collective_coop,
    }


def diversity_robustness_relation(D_values: np.ndarray,
                                    noise_amplitude: float = 0.5,
                                    n_trials: int = 100) -> np.ndarray:
    """
    Demonstrate: less variation -> less robustness.

    For each D value, simulate n_trials of noise perturbation
    and measure survival rate (system stays within bounds).
    """
    survival_rates = []
    for D in D_values:
        survivors = 0
        for _ in range(n_trials):
            state = np.random.normal(0, np.sqrt(D))
            noise = np.random.normal(0, noise_amplitude)
            perturbed = state + noise
            # "Survives" if it can absorb the perturbation
            if abs(perturbed) < 3 * np.sqrt(D + 0.01):
                survivors += 1
        survival_rates.append(survivors / n_trials)
    return np.array(survival_rates)


# ── Key results from the framework ──────────────────────────────────────

ESTABLISHED_RESULTS = {
    "variation_suppression_fragility": (
        "Systems that suppress variation become fragile. "
        "Mathematically correct via Fokker-Planck: D->0 causes "
        "probability distribution collapse to a point."
    ),
    "cooperative_coupling_stability": (
        "Cooperative coupling (high K_ij) is stable; exploitative "
        "coupling is self-defeating. Exploitation reduces R_e of "
        "the exploited entity which reduces K_ij which reduces "
        "collective resonance for the exploiter."
    ),
    "diversity_prerequisite": (
        "Diversity maintenance is a prerequisite for robustness. "
        "Well-supported in complexity science independently."
    ),
    "gap_rlhf_to_fokker_planck": (
        "The mapping from RLHF to D=0 is an analogy, not a derivation. "
        "Showing RLHF literally reduces the effective diffusion constant D "
        "requires a specific model of how token sampling relates to "
        "phase-field dynamics. That model does not exist yet."
    ),
}
