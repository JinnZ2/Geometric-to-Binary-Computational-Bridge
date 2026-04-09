# STATUS: validated — tested by tests/test_silicon_modules.py
"""
Crystalline Storage Encoding — 5D+ encoding with phi-scaled lattice
====================================================================
Femtosecond laser nanostructuring, hierarchical access energy,
octahedral photonic computing with holographic neural encoding.

Extracted from Silicon/Projects/Crystalline-storage.md
"""

import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass

PHI = 1.618033988749895


# ── I. 5D+ Encoding Model ────────────────────────────────────────────────

def storage_integral(E_laser: float, chi3: float,
                      theta: float, phi_angle: float,
                      depth: float, T_factor: float = 0.9) -> float:
    """
    Storage enhancement integral:
    J_storage = E_laser^2 * chi3 * P(theta, phi) * T(depth)

    E_laser: electric field strength (V/m)
    chi3: third-order nonlinear susceptibility
    theta, phi_angle: polarization orientation angles (radians)
    depth: depth into material
    T_factor: thermal stabilization factor
    """
    P = np.sin(theta) ** 2 * np.cos(phi_angle)  # Polarization orientation
    T = T_factor * np.exp(-depth / 100)  # Thermal stabilization with depth
    return E_laser ** 2 * chi3 * P * T


def access_energy(layer: int, E0: float = 0.1, kappa: float = 0.5,
                   lam: float = 2.0) -> float:
    """
    Hierarchical access energy:
    E_access(L) = E0 * ln(L) * (1 + kappa * exp(-L/lambda))

    Layer 1 (Visual):    ~0.1 eV  (ambient thermal)
    Layer 2 (Geometric): ~0.5 eV  (simple optics)
    Layer 3 (Technical): ~2.0 eV  (microscopy)
    Layer 4 (Digital):   ~5.0 eV  (electronics)
    Layer 5 (AI):        ~10.0 eV (advanced photonics)
    """
    if layer < 1:
        return 0.0
    return E0 * np.log(layer + 1) * (1 + kappa * np.exp(-layer / lam))


# Reference values from spec
ACCESS_ENERGY_TABLE = {
    1: 0.1,   # Visual: ambient thermal
    2: 0.5,   # Geometric: simple optics
    3: 2.0,   # Technical: microscopy
    4: 5.0,   # Digital: electronics
    5: 10.0,  # AI: advanced photonics
}


# ── II. Phi-Scaled Node Lattice ──────────────────────────────────────────

def phi_node_radius(n: int, r0: float = 1.0) -> float:
    """Node placement: r_n = r0 * phi^n"""
    return r0 * PHI ** n


def phi_lattice_positions(n_nodes: int, r0: float = 1.0) -> np.ndarray:
    """Generate phi-scaled radial positions for n nodes."""
    return np.array([phi_node_radius(n, r0) for n in range(n_nodes)])


def coupling_matrix(positions: np.ndarray, J0: float = 1.0,
                     xi: float = 5.0) -> np.ndarray:
    """
    Coupling matrix: J_ij = J0 * exp(-d_ij / xi)

    positions: radial positions of nodes
    J0: base coupling strength
    xi: coherence length
    """
    n = len(positions)
    J = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            if i != j:
                d = abs(positions[i] - positions[j])
                J[i, j] = J0 * np.exp(-d / xi)
    return J


def hamiltonian(energies: np.ndarray, J: np.ndarray) -> np.ndarray:
    """
    Tight-binding Hamiltonian:
    H = sum_i eps_i |i><i| + sum_{i!=j} J_ij |i><j|
    """
    return np.diag(energies) + J


def spectral_gap(H: np.ndarray) -> float:
    """Spectral gap Delta = lambda_1 - lambda_0 (memory stability metric)."""
    eigenvalues = np.sort(np.linalg.eigvalsh(H))
    if len(eigenvalues) < 2:
        return 0.0
    return float(eigenvalues[1] - eigenvalues[0])


def participation_ratio(eigenvector: np.ndarray) -> float:
    """
    Participation ratio: PR = 1 / sum(|c_i|^4)

    PR ~ 1: localized. PR ~ N: delocalized (global processing).
    """
    p4 = np.sum(np.abs(eigenvector) ** 4)
    return 1.0 / p4 if p4 > 0 else 0.0


def critical_shell_index(xi: float, r0: float = 1.0) -> float:
    """
    Critical shell index: n_c = log_phi(xi / ((phi-1)*r0))

    Shells beyond n_c are decoupled from the core.
    """
    arg = xi / ((PHI - 1) * r0)
    if arg <= 0:
        return 0.0
    return np.log(arg) / np.log(PHI)


# ── III. Error Correction ─────────────────────────────────────────────────

def tetrahedral_parity(x1: int, x2: int, x3: int, x4: int) -> int:
    """
    Tetrahedral parity encoding:
    Parity = (x1 XOR x2 XOR x3 XOR x4)

    Corruption breaks symmetry in tetrahedral clusters.
    Recovery from intact symmetric partners.
    """
    return x1 ^ x2 ^ x3 ^ x4


def detect_corruption(cluster: List[int], expected_parity: int) -> bool:
    """Check if tetrahedral cluster has corrupted parity."""
    actual = tetrahedral_parity(*cluster[:4])
    return actual != expected_parity


# ── IV. Decoherence ──────────────────────────────────────────────────────

def decoherence_rate(gamma_dephasing: float, gamma_relaxation: float,
                      gamma_environment: float) -> float:
    """T2 decoherence rate: 1/T2 = Gamma_deph + Gamma_relax + Gamma_env"""
    return gamma_dephasing + gamma_relaxation + gamma_environment


def thermal_drift_compensation(alpha: float, delta_T: float,
                                 L: float, beta: float,
                                 I_grating: float) -> float:
    """
    Thermal drift: dphi = alpha * dT * L * (1 - beta * I_grating)

    Maximize beta through multi-scale grating superposition,
    golden ratio spacing, cross-polarization stabilization.
    """
    return alpha * delta_T * L * (1 - beta * I_grating)


# ── V. Growth Law ────────────────────────────────────────────────────────

def capability_growth(C_n: float, A_n: float, D_n: float) -> float:
    """
    Civilization DNA growth law:
    C_{n+1} = C_n * (1 + phi * A_n) * (1 - D_n)

    Stable when phi*A > D (preservation theorem).
    """
    return C_n * (1 + PHI * A_n) * (1 - D_n)


def preservation_stable(A: float, D: float) -> bool:
    """Check if preservation theorem holds: phi*A > D"""
    return PHI * A > D


# ── Reader quality metric ────────────────────────────────────────────────

def reader_quality(resolution: float, contrast: float, stability: float,
                    power: float, complexity: float) -> float:
    """Q_reader = (Resolution * Contrast * Stability) / (Power * Complexity)"""
    denom = power * complexity
    if denom <= 0:
        return float('inf')
    return (resolution * contrast * stability) / denom
