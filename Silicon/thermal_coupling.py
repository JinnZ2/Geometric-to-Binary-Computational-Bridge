"""
Thermal-Information Coupling in Octahedral Silicon -- computational module.

Implements phonon dispersion, tensor-phonon interaction, anisotropic
thermal conductivity, heat flux from state transitions, and deformation
potential coupling from Silicon/Thermal-information.md.

All functions are pure numpy; no external state.
"""

import numpy as np
from typing import Tuple, Optional


# ---------------------------------------------------------------------------
# Physical constants for silicon
# ---------------------------------------------------------------------------

HBAR = 1.0546e-34        # reduced Planck constant  [J s]
K_B = 1.3806e-23         # Boltzmann constant       [J / K]
V_SOUND_SI = 8400.0      # longitudinal sound speed in Si  [m/s]

# Tetrahedral / octahedral directions (normalised [111] family)
OCTA_AXES = np.array([
    [1, 1, 1], [1, 1, -1], [1, -1, 1], [1, -1, -1],
    [-1, 1, 1], [-1, 1, -1], [-1, -1, 1], [-1, -1, -1],
], dtype=float) / np.sqrt(3)


# ---------------------------------------------------------------------------
# 1. Phonon dispersion relation (acoustic branch)
# ---------------------------------------------------------------------------

def phonon_dispersion(q: np.ndarray,
                      v_s: float = V_SOUND_SI) -> np.ndarray:
    """
    Acoustic phonon dispersion (linear regime):

        omega_q = v_s * |q|

    Parameters
    ----------
    q : (...,) or (..., 3) wavevectors.  If last axis is 3 the magnitude
        is computed automatically; otherwise q is treated as |q| directly.
    v_s : sound velocity [m/s].

    Returns
    -------
    omega : same leading shape, angular frequencies [rad/s].
    """
    q = np.asarray(q, dtype=float)
    if q.ndim >= 1 and q.shape[-1] == 3:
        q_mag = np.linalg.norm(q, axis=-1)
    else:
        q_mag = np.abs(q)
    return v_s * q_mag


def group_velocity(q: np.ndarray,
                   v_s: float = V_SOUND_SI) -> np.ndarray:
    """
    Group velocity  v_g = nabla_q omega_q.

    For the linear acoustic branch this is simply v_s * q_hat.

    Parameters
    ----------
    q : (..., 3) wavevectors.

    Returns
    -------
    v_g : (..., 3) group velocity vectors.
    """
    q = np.asarray(q, dtype=float)
    q_mag = np.linalg.norm(q, axis=-1, keepdims=True)
    q_mag = np.where(q_mag == 0, 1.0, q_mag)   # avoid /0
    q_hat = q / q_mag
    return v_s * q_hat


def bose_einstein(omega: np.ndarray, T: float) -> np.ndarray:
    """
    Bose-Einstein occupation number  <n_q> = 1 / (exp(hbar omega / k_B T) - 1).

    Parameters
    ----------
    omega : angular frequencies [rad/s].
    T : temperature [K] (must be > 0).
    """
    if T <= 0:
        raise ValueError("Temperature must be positive.")
    x = HBAR * np.asarray(omega, dtype=float) / (K_B * T)
    # Clip to avoid overflow in exp
    x = np.clip(x, 0, 500)
    return 1.0 / (np.exp(x) - 1.0 + 1e-30)


# ---------------------------------------------------------------------------
# 2. Tensor-phonon interaction Hamiltonian
# ---------------------------------------------------------------------------

def strain_tensor_from_phonon(q: np.ndarray,
                              polarisation: np.ndarray,
                              amplitude: float) -> np.ndarray:
    """
    Construct the symmetric strain tensor epsilon_q for a single phonon
    mode with wavevector q and polarisation vector e:

        epsilon_{ij} = 0.5 * amplitude * (q_i e_j + q_j e_i)

    Parameters
    ----------
    q : (3,) wavevector.
    polarisation : (3,) unit polarisation vector.
    amplitude : scalar displacement amplitude.

    Returns
    -------
    epsilon : (3, 3) symmetric strain tensor.
    """
    q = np.asarray(q, dtype=float)
    e = np.asarray(polarisation, dtype=float)
    return 0.5 * amplitude * (np.outer(q, e) + np.outer(e, q))


def tensor_phonon_coupling_energy(T_electron: np.ndarray,
                                  epsilon_q: np.ndarray,
                                  g_q: float) -> float:
    """
    Single-mode coupling energy:

        H_tp = g_q * Tr(T . epsilon_q) * <b†_q + b_q>

    Here we return just the matrix element  g_q * Tr(T . epsilon_q).
    The caller multiplies by the phonon displacement expectation value
    (sqrt(2 <n_q> + 1) for a thermal state).

    Parameters
    ----------
    T_electron : (3, 3) electron tensor at a lattice site.
    epsilon_q : (3, 3) strain tensor for phonon mode q.
    g_q : coupling strength [eV or J -- user's unit system].

    Returns
    -------
    Scalar coupling matrix element.
    """
    return float(g_q * np.trace(T_electron @ epsilon_q))


def phonon_energy_shift(eigenvalues: np.ndarray,
                        epsilon_q: np.ndarray,
                        g_q: float,
                        n_q: float) -> float:
    """
    Energy shift of an octahedral state due to phonon dressing:

        Delta E_n = g_q * (lambda_principal . diag(epsilon_q)) * <b†+b>

    where <b†+b> ~ sqrt(2 n_q + 1).

    Parameters
    ----------
    eigenvalues : (3,) principal eigenvalues of the electron tensor.
    epsilon_q : (3, 3) strain tensor.
    g_q : coupling constant.
    n_q : mean phonon occupation number.

    Returns
    -------
    Energy shift (same units as g_q).
    """
    eps_diag = np.diag(epsilon_q)
    displacement = np.sqrt(2 * n_q + 1)
    return float(g_q * np.dot(eigenvalues, eps_diag) * displacement)


# ---------------------------------------------------------------------------
# 3. Thermal conductivity tensor (anisotropic)
# ---------------------------------------------------------------------------

def thermal_conductivity_tensor(kappa_perp: float) -> np.ndarray:
    """
    Cubic-symmetric thermal conductivity tensor in [100] frame:

        kappa = diag(kappa_perp, kappa_perp, kappa_perp)

    Parameters
    ----------
    kappa_perp : thermal conductivity along <100> directions [W / (m K)].
                 Bulk Si at 300 K: ~148 W/(m K).

    Returns
    -------
    (3, 3) diagonal tensor.
    """
    return kappa_perp * np.eye(3)


def kappa_along_111(kappa_perp: float) -> float:
    """
    Enhanced thermal conductivity along the [111] direction:

        kappa_[111] = 1.5 * kappa_perp

    due to direct phonon pathways along tetrahedral bonds.
    """
    return 1.5 * kappa_perp


def heat_flux(kappa: np.ndarray, grad_T: np.ndarray) -> np.ndarray:
    """
    Fourier's law with tensor conductivity:

        J_heat = -kappa . nabla T

    Parameters
    ----------
    kappa : (3, 3) thermal conductivity tensor.
    grad_T : (3,) or (M, 3) temperature gradient(s) [K/m].

    Returns
    -------
    J : same shape as grad_T, heat flux [W/m^2].
    """
    grad_T = np.asarray(grad_T, dtype=float)
    return -grad_T @ kappa.T


def heat_flux_tensor_111(kappa_perp: float,
                         grad_T_111: float) -> np.ndarray:
    """
    Convenience: heat flux along [111] given scalar gradient magnitude.

    Returns (3,) vector along the normalised [111] direction.
    """
    k111 = kappa_along_111(kappa_perp)
    direction = np.array([1, 1, 1], dtype=float) / np.sqrt(3)
    return -k111 * grad_T_111 * direction


# ---------------------------------------------------------------------------
# 4. Heat flux from state transitions
# ---------------------------------------------------------------------------

def transition_heat_flux(eigenvalues_initial: np.ndarray,
                         eigenvalues_final: np.ndarray,
                         eigenvector_final_principal: np.ndarray
                         ) -> np.ndarray:
    """
    Directed heat flux from an octahedral state transition n -> m:

        J_heat^(n->m) ~ (lambda_1^m - lambda_1^n) * v_hat_1^m

    Parameters
    ----------
    eigenvalues_initial : (3,) eigenvalues of initial state (sorted descending).
    eigenvalues_final : (3,) eigenvalues of final state (sorted descending).
    eigenvector_final_principal : (3,) principal eigenvector of final state
                                  (corresponding to largest eigenvalue).

    Returns
    -------
    (3,) directed heat-flux vector (arbitrary units proportional to the
    eigenvalue anisotropy change).
    """
    delta_lambda = eigenvalues_final[0] - eigenvalues_initial[0]
    v_hat = np.asarray(eigenvector_final_principal, dtype=float)
    norm = np.linalg.norm(v_hat)
    if norm > 0:
        v_hat = v_hat / norm
    return delta_lambda * v_hat


def transition_thermal_energy(E_write: float,
                              delta_E_nm: float) -> float:
    """
    Thermal energy released during a state transition:

        Q_thermal = E_write - Delta E_nm

    For resonant transitions E_write ~ Delta E_nm, yielding
    Q ~ 0.001 eV (non-adiabatic losses only).

    Parameters
    ----------
    E_write : energy supplied by the write pulse [eV or J].
    delta_E_nm : energy difference between states n and m.

    Returns
    -------
    Q_thermal (same units as inputs).
    """
    return E_write - delta_E_nm


# ---------------------------------------------------------------------------
# 5. Deformation potential coupling
# ---------------------------------------------------------------------------

def deformation_potential_coupling(g_q: float,
                                   T_electron: np.ndarray,
                                   q: np.ndarray,
                                   polarisation: np.ndarray,
                                   amplitude: float,
                                   T: float) -> float:
    """
    Full deformation-potential coupling energy at temperature T,
    combining strain construction, trace coupling, and thermal occupation:

        H_tp = g_q * Tr(T . epsilon_q) * sqrt(2 <n_q> + 1)

    Parameters
    ----------
    g_q : coupling constant.
    T_electron : (3, 3) electron tensor.
    q : (3,) phonon wavevector.
    polarisation : (3,) phonon polarisation unit vector.
    amplitude : displacement amplitude.
    T : temperature [K].

    Returns
    -------
    Coupling energy (same units as g_q).
    """
    eps = strain_tensor_from_phonon(q, polarisation, amplitude)
    omega = phonon_dispersion(q)
    n_q = bose_einstein(omega, T)
    matrix_element = tensor_phonon_coupling_energy(T_electron, eps, g_q)
    displacement = np.sqrt(2 * n_q + 1)
    return float(matrix_element * displacement)


def anisotropy_measure(eigenvalues: np.ndarray) -> float:
    """
    Quantify tensor anisotropy (controls coupling strength to phonons).

    anisotropy = max(eigenvalue) - min(eigenvalue)

    States with larger anisotropy couple more strongly to phonons
    along their principal axis.
    """
    return float(np.max(eigenvalues) - np.min(eigenvalues))


def phonon_mean_free_path(T: float, T_ref: float = 300.0,
                          mfp_ref: float = 300e-9) -> float:
    """
    Approximate phonon mean free path in silicon as a function of
    temperature (Umklapp-limited):

        MFP(T) ~ MFP_ref * (T_ref / T)

    At 300 K the MFP ~ 300 nm.  Below MFP: ballistic (direction
    preserved); above MFP: diffusive (direction lost).

    Parameters
    ----------
    T : temperature [K].
    T_ref : reference temperature [K] (default 300).
    mfp_ref : MFP at T_ref [m] (default 300 nm).

    Returns
    -------
    MFP in metres.
    """
    if T <= 0:
        raise ValueError("Temperature must be positive.")
    return mfp_ref * (T_ref / T)
