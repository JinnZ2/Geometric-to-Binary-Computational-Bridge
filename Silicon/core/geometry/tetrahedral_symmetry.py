# STATUS: validated — tested by tests/test_silicon_modules.py
"""
Tetrahedral symmetry analysis module.

Implements tensor decomposition (isotropic / deviatoric), Lode angle
computation (J2, J3, theta_L), symmetry-adapted tensor components
under T_d point group, and directional readout via sp3 basis vectors.

Reference: Silicon/Tetrahedral.md
"""

from typing import Tuple
import numpy as np
from numpy.typing import NDArray

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SP3 basis vectors (tetrahedral directions, normalised)
T1: NDArray[np.float64] = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
T2: NDArray[np.float64] = np.array([1.0, -1.0, -1.0]) / np.sqrt(3.0)
T3: NDArray[np.float64] = np.array([-1.0, 1.0, -1.0]) / np.sqrt(3.0)
T4: NDArray[np.float64] = np.array([-1.0, -1.0, 1.0]) / np.sqrt(3.0)

SP3_BASIS: NDArray[np.float64] = np.array([T1, T2, T3, T4])


# ---------------------------------------------------------------------------
# Tensor decomposition
# ---------------------------------------------------------------------------

def isotropic_part(T: NDArray[np.float64]) -> NDArray[np.float64]:
    """Isotropic component: T_iso = (1/3) Tr(T) I.

    Parameters
    ----------
    T : (3, 3) tensor.

    Returns
    -------
    (3, 3) isotropic tensor.
    """
    return (np.trace(T) / 3.0) * np.eye(3)


def deviatoric_part(T: NDArray[np.float64]) -> NDArray[np.float64]:
    """Deviatoric component: T_dev = T - T_iso.

    Parameters
    ----------
    T : (3, 3) tensor.

    Returns
    -------
    (3, 3) traceless deviatoric tensor.
    """
    return T - isotropic_part(T)


# ---------------------------------------------------------------------------
# Deviatoric invariants
# ---------------------------------------------------------------------------

def J2(T_dev: NDArray[np.float64]) -> float:
    """Second deviatoric invariant (magnitude of anisotropy).

    J2 = (1/2) * T_dev : T_dev = (1/2) * sum_ij T_dev_ij^2

    Parameters
    ----------
    T_dev : (3, 3) deviatoric (traceless) tensor.

    Returns
    -------
    J2 scalar (non-negative).
    """
    return float(0.5 * np.sum(T_dev * T_dev))


def J3(T_dev: NDArray[np.float64]) -> float:
    """Third deviatoric invariant (shape descriptor: prolate vs oblate).

    J3 = det(T_dev)

    Parameters
    ----------
    T_dev : (3, 3) deviatoric tensor.

    Returns
    -------
    J3 scalar.
    """
    return float(np.linalg.det(T_dev))


def lode_angle(T_dev: NDArray[np.float64]) -> float:
    """Lode angle theta_L -- a non-degenerate geometric fingerprint.

    theta_L = (1/3) * arccos( (3*sqrt(3)/2) * J3 / J2^(3/2) )

    Parameters
    ----------
    T_dev : (3, 3) deviatoric tensor.

    Returns
    -------
    Lode angle in radians (0 to pi/3).
    """
    j2 = J2(T_dev)
    j3 = J3(T_dev)
    if j2 < 1e-15:
        return 0.0  # isotropic, angle undefined -> 0
    arg = (3.0 * np.sqrt(3.0) / 2.0) * j3 / (j2 ** 1.5)
    # Clamp to [-1, 1] for numerical safety
    arg = float(np.clip(arg, -1.0, 1.0))
    return float(np.arccos(arg) / 3.0)


def deviatoric_invariants(
    T: NDArray[np.float64],
) -> Tuple[float, float, float]:
    """Convenience: compute J2, J3, theta_L from a full tensor.

    Parameters
    ----------
    T : (3, 3) tensor (not necessarily deviatoric).

    Returns
    -------
    (J2, J3, theta_L) tuple.
    """
    Td = deviatoric_part(T)
    return J2(Td), J3(Td), lode_angle(Td)


# ---------------------------------------------------------------------------
# Symmetry-adapted tensor components (T_d point group)
# ---------------------------------------------------------------------------

def quadrupole_E_components(T: NDArray[np.float64]) -> Tuple[float, float]:
    """E-representation (doublet) components under T_d symmetry.

    The E irreducible representation of the l=2 quadrupole
    in T_d comprises two independent components:

        Q_E1 = T_xx - T_yy
        Q_E2 = (2*T_zz - T_xx - T_yy) / sqrt(3)

    Parameters
    ----------
    T : (3, 3) tensor.

    Returns
    -------
    (Q_E1, Q_E2) tuple.
    """
    Q_E1 = float(T[0, 0] - T[1, 1])
    Q_E2 = float((2.0 * T[2, 2] - T[0, 0] - T[1, 1]) / np.sqrt(3.0))
    return Q_E1, Q_E2


def quadrupole_T2_components(
    T: NDArray[np.float64],
) -> Tuple[float, float, float]:
    """T2-representation (triplet) components under T_d symmetry.

    The T2 irreducible representation of the l=2 quadrupole
    in T_d corresponds to the three off-diagonal elements:

        Q_T2_xy = T_xy
        Q_T2_xz = T_xz
        Q_T2_yz = T_yz

    Parameters
    ----------
    T : (3, 3) tensor.

    Returns
    -------
    (Q_T2_xy, Q_T2_xz, Q_T2_yz) tuple.
    """
    return float(T[0, 1]), float(T[0, 2]), float(T[1, 2])


def symmetry_fingerprint(
    T: NDArray[np.float64],
) -> Tuple[float, float, float, float, float]:
    """Full symmetry-adapted fingerprint (E + T2 components).

    Returns
    -------
    (Q_E1, Q_E2, Q_T2_xy, Q_T2_xz, Q_T2_yz)
    """
    e1, e2 = quadrupole_E_components(T)
    t2_xy, t2_xz, t2_yz = quadrupole_T2_components(T)
    return e1, e2, t2_xy, t2_xz, t2_yz


def E_weight(T: NDArray[np.float64]) -> float:
    """Norm of the E-representation component."""
    e1, e2 = quadrupole_E_components(T)
    return float(np.sqrt(e1 ** 2 + e2 ** 2))


def T2_weight(T: NDArray[np.float64]) -> float:
    """Norm of the T2-representation component."""
    xy, xz, yz = quadrupole_T2_components(T)
    return float(np.sqrt(xy ** 2 + xz ** 2 + yz ** 2))


# ---------------------------------------------------------------------------
# Directional readout via sp3 basis vectors
# ---------------------------------------------------------------------------

def directional_projections(
    T: NDArray[np.float64],
    basis: NDArray[np.float64] | None = None,
) -> NDArray[np.float64]:
    """Project tensor T onto each sp3 basis direction.

    s_i = t_i^T T t_i  for i = 1..4

    Parameters
    ----------
    T : (3, 3) tensor.
    basis : (4, 3) array of sp3 vectors (default: SP3_BASIS).

    Returns
    -------
    (4,) array of directional projections [s1, s2, s3, s4].
    """
    if basis is None:
        basis = SP3_BASIS
    return np.array([float(v @ T @ v) for v in basis])


def fingerprint_from_projections(
    T: NDArray[np.float64],
) -> NDArray[np.float64]:
    """Non-degenerate fingerprint that uniquely distinguishes sites
    even when eigenvalue traces are identical.

    Returns
    -------
    (4,) projection fingerprint.
    """
    return directional_projections(T)


# ---------------------------------------------------------------------------
# Full analysis pipeline
# ---------------------------------------------------------------------------

def full_tensor_analysis(
    T: NDArray[np.float64],
) -> dict:
    """Run the complete degeneracy-breaking analysis on tensor T.

    Returns a dictionary with all computed descriptors:
    - trace, eigenvalues, eigenvectors
    - J2, J3, lode_angle
    - E / T2 symmetry weights
    - directional projections
    """
    vals, vecs = np.linalg.eigh(T)
    idx = np.argsort(vals)[::-1]
    vals = vals[idx]
    vecs = vecs[:, idx]

    j2, j3, theta_l = deviatoric_invariants(T)
    e_w = E_weight(T)
    t2_w = T2_weight(T)
    proj = directional_projections(T)

    return {
        "trace": float(np.trace(T)),
        "eigenvalues": vals,
        "eigenvectors": vecs,
        "J2": j2,
        "J3": j3,
        "lode_angle": theta_l,
        "E_weight": e_w,
        "T2_weight": t2_w,
        "directional_projections": proj,
    }
