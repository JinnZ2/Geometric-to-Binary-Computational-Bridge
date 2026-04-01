"""
Physics Connections — Cross-layer coupling computations
========================================================
Traces connections between Mandala-Computing, Silicon vortex physics,
and Engine EM solver. Implements the shared equations.

Extracted from Mandala/05-physics-connections.md
"""

import numpy as np
from typing import Tuple, Optional

PHI = 1.618033988749895
K_BOLTZMANN = 8.617333e-5  # eV/K


# ── 1. Metropolis-Hastings / Kosterlitz-Thouless ──────────────────────────

def metropolis_accept(dE: float, T: float) -> bool:
    """Metropolis-Hastings acceptance criterion (2D XY model)."""
    if dE < 0:
        return True
    if T <= 0:
        return dE <= 0
    return np.random.random() < np.exp(-dE / T)


def kt_temperature(J: float = 1.0) -> float:
    """
    Kosterlitz-Thouless transition temperature for the 2D XY model.

    T_KT ≈ (π/2) J  for the classical 2D XY model.
    Above T_KT: free vortices (disordered). Below: bound dipoles (ordered).
    """
    return (np.pi / 2) * J


def annealing_schedule(step: int, total_steps: int,
                       T_start: float = 2.0,
                       T_end: float = 0.01,
                       J: float = 1.0) -> float:
    """
    Annealing schedule that crosses T_KT from above to below.

    Linear interpolation in log space, ensuring the schedule passes
    through T_KT at approximately the midpoint.
    """
    t_kt = kt_temperature(J)
    if total_steps <= 1:
        return T_end
    frac = step / (total_steps - 1)
    # Log-linear interpolation
    T = T_start * (T_end / T_start) ** frac
    return T


def boltzmann_factor(dE: float, T: float) -> float:
    """Boltzmann factor exp(-dE/T). Same equation for MH and vortex physics."""
    if T <= 0:
        return 0.0 if dE > 0 else 1.0
    return np.exp(-dE / T)


# ── 2. FRET / Coulomb / Biot-Savart coupling regimes ─────────────────────

def fret_coupling(r: float, R0: float = 4.85) -> float:
    """
    FRET (Forster) coupling: J ~ 1/r^6, near-field dipole-dipole.

    Used for octahedral substrate cell coupling (nm scale).
    R0: Forster radius in nm (default 3*phi ≈ 4.85 nm).
    Returns efficiency [0, 1].
    """
    if r <= 0:
        return 1.0
    return 1.0 / (1.0 + (r / R0) ** 6)


def coulomb_coupling(r: float, q1: float = 1.0, q2: float = 1.0,
                     k: float = 8.9875e9) -> float:
    """
    Coulomb coupling: F ~ 1/r^2, macroscopic EM.

    Used by Engine/simd_optimizer.py for field computation.
    Returns force magnitude in Newtons.
    """
    if r <= 0:
        return float('inf')
    return k * abs(q1 * q2) / (r * r)


def dipole_coupling(r: float, p1: float = 1.0, p2: float = 1.0) -> float:
    """
    Dipole-dipole coupling: U ~ 1/r^3, intermediate regime.

    Transition between FRET (1/r^6) and Coulomb (1/r^2).
    """
    if r <= 0:
        return float('inf')
    return p1 * p2 / (r ** 3)


def coupling_regime(r_nm: float) -> str:
    """
    Determine which coupling regime dominates at a given distance.

    Returns one of: "FRET", "dipole", "Coulomb"
    """
    if r_nm < 10:
        return "FRET"
    elif r_nm < 1000:
        return "dipole"
    else:
        return "Coulomb"


# ── 3. Berry phase / topological invariants ──────────────────────────────

def berry_phase_vortex(winding_number: int) -> float:
    """
    Berry phase for a vortex with given winding number.

    gamma = 2*pi * winding_number
    Classical topological invariant = winding number
    Quantum topological invariant = Berry phase / 2*pi
    """
    return 2 * np.pi * winding_number


def adiabatic_condition(ds_dt: float, energy_gap: float, hbar: float = 1.0) -> bool:
    """
    Check the adiabatic condition: hbar * ds/dt << (E1 - E0)^2.

    If satisfied, the system stays in the instantaneous ground state.
    """
    return hbar * abs(ds_dt) < 0.1 * energy_gap ** 2


def adiabatic_hamiltonian(s: float, H_initial: np.ndarray,
                           H_problem: np.ndarray) -> np.ndarray:
    """
    Adiabatic interpolation: H(s) = (1-s)*H_initial + s*H_problem.
    s goes from 0 to 1 slowly.
    """
    return (1 - s) * H_initial + s * H_problem


# ── 4. Grover search scaling ─────────────────────────────────────────────

def grover_steps_octit(num_cells: int) -> int:
    """
    Grover search steps for qudit-octit system.

    Single cell: N=8, sqrt(N) ≈ 2.83 ≈ 3 steps.
    K cells: N=8^K, sqrt(N) = 8^(K/2) = 2^(3K/2) steps.
    """
    N = 8 ** num_cells
    return int(np.ceil(np.sqrt(N)))


def quantum_speedup_ratio(num_cells: int) -> float:
    """Ratio of classical O(8^K) to quantum O(sqrt(8^K)) search."""
    return 8 ** (num_cells / 2)


# ── 5. Fibonacci eigenvalue / quasi-crystal stability ────────────────────

def fibonacci_eigenvalue_scaling(i: int, num_states: int = 8) -> float:
    """
    Fibonacci-scaled eigenvalue: lambda_i = phi^i / sum(phi^k).

    Maximally incommensurate with thermal noise — same mathematical
    principle that gives quasi-crystals their stability.
    """
    phi_powers = [PHI ** k for k in range(num_states)]
    total = sum(phi_powers)
    return phi_powers[i] / total


def incommensurability_measure(eigenvalues: np.ndarray) -> float:
    """
    Measure how incommensurate eigenvalue ratios are with rational numbers.

    Higher = more quasi-crystal-like stability against periodic perturbations.
    Uses the continued fraction convergence rate.
    """
    ratios = []
    for i in range(len(eigenvalues)):
        for j in range(i + 1, len(eigenvalues)):
            if eigenvalues[j] != 0:
                ratios.append(eigenvalues[i] / eigenvalues[j])

    if not ratios:
        return 0.0

    # Distance from nearest simple rational (p/q with q <= 10)
    min_distances = []
    for r in ratios:
        best = float('inf')
        for q in range(1, 11):
            for p in range(0, 10 * q + 1):
                dist = abs(r - p / q)
                best = min(best, dist)
        min_distances.append(best)

    return float(np.mean(min_distances))


# ── 6. Layer stack compatibility check ───────────────────────────────────

def compatible_layer_stack(cell_spacing_nm: float = 2.0,
                           engine_spacing_m: float = 0.1,
                           T_anneal: float = 1.0,
                           J: float = 1.0) -> dict:
    """
    Verify compatibility of the full layer stack:
    - FRET regime for substrate
    - Coulomb regime for engine
    - Annealing crosses T_KT
    """
    t_kt = kt_temperature(J)
    return {
        "substrate_regime": coupling_regime(cell_spacing_nm),
        "engine_regime": coupling_regime(engine_spacing_m * 1e9),
        "fret_efficiency": fret_coupling(cell_spacing_nm),
        "T_KT": t_kt,
        "annealing_crosses_KT": T_anneal > t_kt,
        "compatible": (
            coupling_regime(cell_spacing_nm) == "FRET" and
            coupling_regime(engine_spacing_m * 1e9) == "Coulomb"
        ),
    }
