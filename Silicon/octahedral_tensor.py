# STATUS: validated — tested by tests/test_silicon_modules.py
"""
Octahedral tensor computation module.

Implements SP3 orbital vector basis, tensor field construction,
8-position octahedral mapping, occupation weight functions,
spectral decomposition, and tensor eigenvalue computation
for all 8 diamond cubic vertex positions.

Reference: Silicon/Octahedral-computation.md
"""

from typing import Tuple, List, Dict
import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SP3 orbital vectors (tetrahedral vertices, normalised)
V1: NDArray[np.float64] = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
V2: NDArray[np.float64] = np.array([1.0, -1.0, -1.0]) / np.sqrt(3.0)
V3: NDArray[np.float64] = np.array([-1.0, 1.0, -1.0]) / np.sqrt(3.0)
V4: NDArray[np.float64] = np.array([-1.0, -1.0, 1.0]) / np.sqrt(3.0)

SP3_VECTORS: NDArray[np.float64] = np.array([V1, V2, V3, V4])

# Tetrahedral angle (degrees) -- foundational constant
TETRAHEDRAL_ANGLE_DEG: float = 109.47

# Silicon lattice constant (angstroms)
LATTICE_CONSTANT_A: float = 5.43

# Diamond cubic 8 vertex positions (fractional coordinates)
VERTEX_POSITIONS: NDArray[np.float64] = np.array([
    [0.0,  0.0,  0.0],    # Position 0
    [0.5,  0.5,  0.0],    # Position 1
    [0.5,  0.0,  0.5],    # Position 2
    [0.0,  0.5,  0.5],    # Position 3
    [0.25, 0.25, 0.25],   # Position 4
    [0.75, 0.75, 0.25],   # Position 5
    [0.75, 0.25, 0.75],   # Position 6
    [0.25, 0.75, 0.75],   # Position 7
])

# Bohr magneton (eV/T)
BOHR_MAGNETON: float = 5.788e-5

# Electron g-factor
G_ELECTRON: float = 2.0023

# Elastic constant beta for Si (eV/rad^2)
BETA_SI: float = 5.0

# Phonon attempt frequency for Si (Hz)
NU_0: float = 1.0e13

# Boltzmann constant (eV/K)
K_B: float = 8.617e-5


# ---------------------------------------------------------------------------
# Occupation weight functions
# ---------------------------------------------------------------------------

def occupation_weight(
    r_vertex: NDArray[np.float64],
    v_orbital: NDArray[np.float64],
    sigma: float = 1.0,
) -> float:
    """Compute occupation weight w_i(n) for orbital *v_orbital* at vertex *r_vertex*.

    w_i(n) = exp(-|r_n - v_i|^2 / sigma^2) * (1 + v_i . r_hat_n) / 2

    Parameters
    ----------
    r_vertex : (3,) position vector of the vertex.
    v_orbital : (3,) sp3 orbital direction (unit-normalised).
    sigma : localisation parameter.

    Returns
    -------
    Scalar occupation weight (float).
    """
    diff = r_vertex - v_orbital
    r_norm = np.linalg.norm(r_vertex)
    r_hat = r_vertex / r_norm if r_norm > 1e-12 else np.zeros(3)
    gaussian = np.exp(-np.dot(diff, diff) / (sigma * sigma))
    angular = (1.0 + np.dot(v_orbital, r_hat)) / 2.0
    return float(gaussian * angular)


def compute_weights(
    r_vertex: NDArray[np.float64],
    sigma: float = 1.0,
) -> NDArray[np.float64]:
    """Return the four occupation weights for a given vertex position.

    Parameters
    ----------
    r_vertex : (3,) fractional coordinate of the vertex.
    sigma : localisation parameter.

    Returns
    -------
    (4,) array of occupation weights [w1, w2, w3, w4].
    """
    weights = np.array([
        occupation_weight(r_vertex, v, sigma) for v in SP3_VECTORS
    ])
    w_sum = weights.sum()
    if w_sum > 1e-12:
        weights /= w_sum  # normalise so sum = 1
    else:
        weights = np.full(4, 0.25)  # fallback: equal weights
    return weights


# ---------------------------------------------------------------------------
# Tensor field construction
# ---------------------------------------------------------------------------

def orbital_tensor(weights: NDArray[np.float64]) -> NDArray[np.float64]:
    """Construct the 3x3 symmetric orbital tensor T = sum_i w_i (v_i (x) v_i).

    Parameters
    ----------
    weights : (4,) occupation weights for each sp3 orbital.

    Returns
    -------
    (3, 3) symmetric tensor.
    """
    T = np.zeros((3, 3), dtype=np.float64)
    for w, v in zip(weights, SP3_VECTORS):
        T += w * np.outer(v, v)
    return T


def tensor_for_position(
    position_index: int,
    sigma: float = 1.0,
) -> NDArray[np.float64]:
    """Compute the orbital tensor for one of the 8 diamond cubic positions.

    Parameters
    ----------
    position_index : int in [0..7].
    sigma : localisation parameter.

    Returns
    -------
    (3, 3) orbital tensor.
    """
    if not 0 <= position_index <= 7:
        raise ValueError(f"position_index must be 0-7, got {position_index}")
    r = VERTEX_POSITIONS[position_index]
    w = compute_weights(r, sigma)
    return orbital_tensor(w)


# ---------------------------------------------------------------------------
# Spectral decomposition / eigenvalue analysis
# ---------------------------------------------------------------------------

def spectral_decomposition(
    T: NDArray[np.float64],
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Return sorted eigenvalues and eigenvectors of a 3x3 symmetric tensor.

    Parameters
    ----------
    T : (3, 3) symmetric tensor.

    Returns
    -------
    eigenvalues : (3,) sorted in descending order.
    eigenvectors : (3, 3) columns are the corresponding eigenvectors.
    """
    vals, vecs = np.linalg.eigh(T)
    idx = np.argsort(vals)[::-1]
    return vals[idx], vecs[:, idx]


def eigenvalue_triplet(
    position_index: int,
    sigma: float = 1.0,
) -> NDArray[np.float64]:
    """Return the eigenvalue triplet (lambda_1, lambda_2, lambda_3) for a position.

    Parameters
    ----------
    position_index : int in [0..7].
    sigma : localisation parameter.

    Returns
    -------
    (3,) eigenvalues sorted descending.
    """
    T = tensor_for_position(position_index, sigma)
    vals, _ = spectral_decomposition(T)
    return vals


def all_eigenvalue_triplets(
    sigma: float = 1.0,
) -> NDArray[np.float64]:
    """Compute eigenvalue triplets for all 8 vertex positions.

    Returns
    -------
    (8, 3) array where row *n* holds the sorted eigenvalues of position *n*.
    """
    return np.array([eigenvalue_triplet(i, sigma) for i in range(8)])


# ---------------------------------------------------------------------------
# Tensor observables
# ---------------------------------------------------------------------------

def tensor_trace(T: NDArray[np.float64]) -> float:
    """Trace of tensor: Tr(T) = lambda_1 + lambda_2 + lambda_3."""
    return float(np.trace(T))


def anisotropy(eigenvalues: NDArray[np.float64]) -> float:
    """Anisotropy measure: Delta = lambda_1 - (lambda_2 + lambda_3) / 2."""
    return float(eigenvalues[0] - (eigenvalues[1] + eigenvalues[2]) / 2.0)


def principal_direction(T: NDArray[np.float64]) -> NDArray[np.float64]:
    """Eigenvector corresponding to the largest eigenvalue."""
    _, vecs = spectral_decomposition(T)
    return vecs[:, 0]


# ---------------------------------------------------------------------------
# Magnetic coupling
# ---------------------------------------------------------------------------

def magnetic_energy(
    T: NDArray[np.float64],
    B: NDArray[np.float64],
) -> float:
    """Magnetic coupling energy E_mag = -T_zz * B0^2 (generalised to arbitrary B).

    E_mag = - (B^T T B) / |B|^2  * |B|^2 = - B^T T B

    Parameters
    ----------
    T : (3, 3) tensor.
    B : (3,) external field vector.

    Returns
    -------
    Energy (arbitrary units proportional to Bohr magneton coupling).
    """
    return float(-B @ T @ B)


def transition_tensor(
    pos_from: int,
    pos_to: int,
    sigma: float = 1.0,
) -> NDArray[np.float64]:
    """Compute the transition tensor Delta_T = T^m - T^n."""
    T_n = tensor_for_position(pos_from, sigma)
    T_m = tensor_for_position(pos_to, sigma)
    return T_m - T_n


def optimal_field_direction(
    pos_from: int,
    pos_to: int,
    sigma: float = 1.0,
) -> NDArray[np.float64]:
    """Return the optimal external field direction for the n -> m transition.

    This is the principal eigenvector of the transition tensor (largest
    absolute eigenvalue), maximising barrier suppression.
    """
    dT = transition_tensor(pos_from, pos_to, sigma)
    vals, vecs = np.linalg.eigh(dT)
    idx = np.argmax(np.abs(vals))
    return vecs[:, idx]


# ---------------------------------------------------------------------------
# State transition dynamics
# ---------------------------------------------------------------------------

def strain_energy(delta_theta: float, beta: float = BETA_SI) -> float:
    """Elastic strain energy for angular transition.

    E_strain = (beta / 3) * (delta_theta)^2

    Parameters
    ----------
    delta_theta : angular displacement in radians.
    beta : elastic constant (eV/rad^2).
    """
    return (beta / 3.0) * delta_theta ** 2


def transition_barrier(delta_theta: float, beta: float = BETA_SI) -> float:
    """Energy barrier at the saddle point for angular transition.

    dE_barrier = (beta / 12) * (delta_theta)^2
    """
    return (beta / 12.0) * delta_theta ** 2


def effective_barrier(
    delta_theta: float,
    B: float,
    delta_lambda: float,
    beta: float = BETA_SI,
) -> float:
    """Effective transition barrier under external field B.

    dE_eff = dE_barrier - mu_B * g * B * delta_lambda
    """
    base = transition_barrier(delta_theta, beta)
    suppression = BOHR_MAGNETON * G_ELECTRON * B * delta_lambda
    return base - suppression


def critical_field(
    delta_theta: float,
    delta_lambda: float,
    beta: float = BETA_SI,
) -> float:
    """Critical field for complete barrier suppression (dE_eff = 0).

    B_crit = dE_barrier / (mu_B * g * delta_lambda)
    """
    barrier = transition_barrier(delta_theta, beta)
    return barrier / (BOHR_MAGNETON * G_ELECTRON * abs(delta_lambda))


def transition_rate(
    delta_E_eff: float,
    temperature: float,
    nu0: float = NU_0,
) -> float:
    """Kramers transition rate.

    k = nu_0 * exp(-dE_eff / (k_B * T))

    Parameters
    ----------
    delta_E_eff : effective barrier height (eV).
    temperature : temperature (K).
    nu0 : attempt frequency (Hz).

    Returns
    -------
    Rate in Hz (s^-1).
    """
    if temperature <= 0:
        return 0.0
    return nu0 * np.exp(-delta_E_eff / (K_B * temperature))


def rabi_period(B1: float) -> float:
    """Rabi oscillation period for coherent state flip.

    T_Rabi = pi * hbar / (mu_B * g * B1)

    Parameters
    ----------
    B1 : RF field amplitude (Tesla).

    Returns
    -------
    Period in seconds.
    """
    hbar = 6.582e-16  # eV*s
    return np.pi * hbar / (BOHR_MAGNETON * G_ELECTRON * B1)


def resonant_frequency(delta_E: float) -> float:
    """Resonant transition frequency omega = delta_E / hbar (rad/s)."""
    hbar = 6.582e-16  # eV*s
    return delta_E / hbar
