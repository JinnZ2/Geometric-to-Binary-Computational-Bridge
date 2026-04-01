"""
Topological Photonics — Multi-Dimensional Light Geometry
========================================================
Topological edge states, polarization encoding, Chern number
computation, phase/depth modulation for 5D crystalline storage.

Extracted from experiments/topological_photonics.md
"""

import numpy as np
from dataclasses import dataclass
from typing import Tuple, List, Optional


# ── Stokes Vector (Polarization as 4D Data) ────────────────────────────

@dataclass
class StokesVector:
    """
    Stokes vector representation of light polarization.

    S0: total intensity
    S1: horizontal vs vertical (I_H - I_V)
    S2: diagonal vs anti-diagonal (I_45 - I_135)
    S3: right vs left circular (I_R - I_L)

    Each component encodes independent information channels,
    creating a 4D vector per beam.
    """
    S0: float  # Total intensity
    S1: float  # Linear horizontal-vertical
    S2: float  # Linear diagonal
    S3: float  # Circular polarization

    @property
    def vector(self) -> np.ndarray:
        return np.array([self.S0, self.S1, self.S2, self.S3])

    @property
    def degree_of_polarization(self) -> float:
        """DOP = sqrt(S1² + S2² + S3²) / S0"""
        if self.S0 <= 0:
            return 0.0
        return np.sqrt(self.S1**2 + self.S2**2 + self.S3**2) / self.S0

    @property
    def is_fully_polarized(self) -> bool:
        return abs(self.degree_of_polarization - 1.0) < 1e-6

    @classmethod
    def from_intensities(cls, I_H: float, I_V: float,
                         I_45: float, I_135: float,
                         I_R: float, I_L: float) -> 'StokesVector':
        """Construct from six intensity measurements."""
        return cls(
            S0=I_H + I_V,
            S1=I_H - I_V,
            S2=I_45 - I_135,
            S3=I_R - I_L,
        )

    @classmethod
    def linear_horizontal(cls, intensity: float = 1.0) -> 'StokesVector':
        return cls(S0=intensity, S1=intensity, S2=0, S3=0)

    @classmethod
    def linear_vertical(cls, intensity: float = 1.0) -> 'StokesVector':
        return cls(S0=intensity, S1=-intensity, S2=0, S3=0)

    @classmethod
    def circular_right(cls, intensity: float = 1.0) -> 'StokesVector':
        return cls(S0=intensity, S1=0, S2=0, S3=intensity)

    @classmethod
    def circular_left(cls, intensity: float = 1.0) -> 'StokesVector':
        return cls(S0=intensity, S1=0, S2=0, S3=-intensity)

    @classmethod
    def unpolarized(cls, intensity: float = 1.0) -> 'StokesVector':
        return cls(S0=intensity, S1=0, S2=0, S3=0)


# ── Phase operator ─────────────────────────────────────────────────────

def phase_operator(phi: float) -> complex:
    """
    Phase operator: U_phi = exp(i * phi)

    Controllable phase delays encode Z-axis/amplitude in the lattice.
    """
    return np.exp(1j * phi)


def phase_modulation_array(phases: np.ndarray) -> np.ndarray:
    """Apply phase operator to an array of phase values."""
    return np.exp(1j * phases)


# ── Berry phase / Chern number ─────────────────────────────────────────

def berry_connection(eigenstates: np.ndarray, dk: float = 0.01) -> np.ndarray:
    """
    Discrete Berry connection:
    A_n(k) = -Im(⟨u_n(k)|∇_k|u_n(k)⟩)

    Approximated via finite differences.
    eigenstates: array of shape (n_k, n_bands, n_basis)
    """
    n_k = eigenstates.shape[0]
    A = np.zeros(n_k)
    for i in range(n_k):
        j = (i + 1) % n_k
        overlap = np.vdot(eigenstates[i], eigenstates[j])
        A[i] = -np.imag(np.log(overlap / abs(overlap))) / dk
    return A


def chern_number_1d(berry_phases: np.ndarray) -> float:
    """
    Chern number from Berry phases along a 1D loop:
    C = (1/2π) * sum(Berry phases)

    Integer Chern number identifies topologically protected edge modes.
    """
    return float(np.sum(berry_phases)) / (2.0 * np.pi)


def chern_number_2d(berry_curvature: np.ndarray, dk: float = 0.01) -> float:
    """
    Chern number for 2D Brillouin zone:
    C = (1/2π) ∫_BZ Ω(k) d²k

    berry_curvature: 2D array of Berry curvature values Ω(kx, ky)
    dk: spacing in k-space
    """
    return float(np.sum(berry_curvature)) * dk**2 / (2.0 * np.pi)


# ── Topological edge states ────────────────────────────────────────────

def maxwell_eigenvalue_2d(epsilon: np.ndarray, mu: np.ndarray,
                           kx: float, ky: float) -> np.ndarray:
    """
    Simplified 2D photonic crystal eigenvalue problem.

    From Maxwell's equations in periodic media:
    ∇ × (1/μ(r)) ∇ × E(r) = (ω²/c²) ε(r) E(r)

    epsilon, mu: material parameters on grid
    kx, ky: Bloch wavevector components

    Returns eigenfrequencies ω² (simplified plane-wave expansion).
    """
    n = epsilon.shape[0]
    # Simplified: diagonal approximation
    eps_flat = epsilon.flatten()
    mu_flat = mu.flatten()

    # Approximate: ω² ~ c² * (kx² + ky²) / (ε * μ) for each site
    k_sq = kx**2 + ky**2
    omega_sq = k_sq / (eps_flat * mu_flat)
    return np.sort(omega_sq)


def magneto_optic_hall_current(E_field: np.ndarray,
                                sigma_hall: float) -> np.ndarray:
    """
    Magneto-optic Hall current:
    J_MO = sigma_Hall * E × z_hat

    Breaking time-reversal symmetry creates unidirectional edge channels.
    """
    z_hat = np.array([0, 0, 1])
    if E_field.shape[-1] == 2:
        E_3d = np.append(E_field, 0)
    else:
        E_3d = E_field
    return sigma_hall * np.cross(E_3d, z_hat)


# ── Integration with 5D crystalline storage ────────────────────────────

def storage_mapping(edge_position: Tuple[float, float],
                     stokes: StokesVector,
                     phase_delay: float,
                     void_depth: float) -> dict:
    """
    Map topological photonic state to 5D+ crystalline storage address.

    - Edge position → spatial index (X, Y)
    - Polarization → encoded state (1-4D via Stokes)
    - Phase delay → Z axis
    - Void depth → amplitude

    Topologically protected channels serve as read/write paths.
    """
    return {
        "x": edge_position[0],
        "y": edge_position[1],
        "polarization": stokes.vector.tolist(),
        "phase_z": phase_delay,
        "amplitude": void_depth,
        "dop": stokes.degree_of_polarization,
    }
