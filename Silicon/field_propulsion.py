# STATUS: infrastructure — field propulsion shape computation
"""
Field Propulsion Shape -- computational module.

Implements the coupled-oscillator, helix-geometry, and efficiency
equations from Silicon/FIELD_PROPULSION_SHAPE.md.

All functions are pure numpy; no external state.
"""

import numpy as np
from typing import Tuple, Optional


# ---------------------------------------------------------------------------
# 1. Coupled oscillator fields (Section 1.1)
# ---------------------------------------------------------------------------

def node_field(t: np.ndarray, amplitude: float, omega: float,
               phi: float) -> np.ndarray:
    """Single-node sinusoidal field  F_i(t) = A_i sin(omega_i t + phi_i)."""
    return amplitude * np.sin(omega * t + phi)


def net_field(t: np.ndarray, amplitudes: np.ndarray, omegas: np.ndarray,
              phases: np.ndarray, k_c: float) -> np.ndarray:
    """
    Coupled network field (Eq. from Section 1.1).

    F_net(t) = sum_i A_i sin(w_i t + phi_i)
             + k_c sum_i A_i A_{i+1} sin(phi_{i+1} - phi_i)

    Parameters
    ----------
    t : (T,) array of time samples
    amplitudes, omegas, phases : (N,) per-node parameters
    k_c : coupling constant

    Returns
    -------
    (T,) net field evaluated at each time point.
    """
    N = len(amplitudes)
    # Direct sum: each node's free oscillation
    # Shape: (N, T)
    individual = amplitudes[:, None] * np.sin(
        omegas[:, None] * t[None, :] + phases[:, None]
    )
    direct = individual.sum(axis=0)

    # Coupling sum over neighboring pairs
    coupling = 0.0
    for i in range(N - 1):
        coupling += amplitudes[i] * amplitudes[i + 1] * np.sin(
            phases[i + 1] - phases[i]
        )
    coupling *= k_c

    return direct + coupling


# ---------------------------------------------------------------------------
# 2. Logarithmic harmonic frequency series (Section 1.3)
# ---------------------------------------------------------------------------

def log_harmonic_frequencies(omega_0: float, alpha: float,
                             N: int) -> np.ndarray:
    """
    omega_i = omega_0 * [1 + alpha * ln(i+1)]   for i = 0 .. N-1.

    Minimises destructive overlap (harmonic-nozzle spacing).
    """
    i = np.arange(N)
    return omega_0 * (1.0 + alpha * np.log(i + 1))


# ---------------------------------------------------------------------------
# 3. Phase optimisation (Section 1.1 / 3)
# ---------------------------------------------------------------------------

def constant_phase_offsets(N: int, delta_phi: float) -> np.ndarray:
    """Return phase array [0, dphi, 2*dphi, ...] for a traveling wave."""
    return np.arange(N) * delta_phi


def optimal_phase_sweep(amplitudes: np.ndarray, omegas: np.ndarray,
                        k_c: float, t: np.ndarray,
                        n_steps: int = 360) -> Tuple[float, np.ndarray]:
    """
    Sweep delta_phi in [0, 2pi) and return the offset that maximises the
    peak magnitude of F_net.  (Section 3: expected peak near 3pi/2.)

    Returns
    -------
    best_dphi : float
    forward_proxy : (n_steps,) peak |F_net| at each tested offset
    """
    N = len(amplitudes)
    dphi_values = np.linspace(0, 2 * np.pi, n_steps, endpoint=False)
    peaks = np.empty(n_steps)
    for idx, dp in enumerate(dphi_values):
        phases = constant_phase_offsets(N, dp)
        f = net_field(t, amplitudes, omegas, phases, k_c)
        peaks[idx] = np.max(np.abs(f))
    best = int(np.argmax(peaks))
    return dphi_values[best], peaks


# ---------------------------------------------------------------------------
# 4. Helix geometry (Section 2.1)
# ---------------------------------------------------------------------------

def helix_positions(N: int, R: float, pitch: float,
                    theta_0: float) -> np.ndarray:
    """
    Parametric helix node positions.

        x_i = R cos(i theta_0)
        y_i = R sin(i theta_0)
        z_i = pitch * i / N

    Returns (N, 3) array.
    """
    i = np.arange(N)
    x = R * np.cos(i * theta_0)
    y = R * np.sin(i * theta_0)
    z = pitch * i / N
    return np.column_stack([x, y, z])


# ---------------------------------------------------------------------------
# 5. Poynting-like directional momentum (Section 1.2)
# ---------------------------------------------------------------------------

def poynting_vector(E: np.ndarray, H: np.ndarray,
                    c: float = 3e8) -> np.ndarray:
    """
    Local Poynting-like momentum density  p = (1/c^2) E x H.

    E, H : (..., 3) field vectors (same leading shape).
    Returns array of same shape.
    """
    return np.cross(E, H) / (c ** 2)


def forward_momentum(E: np.ndarray, H: np.ndarray,
                     n_hat: np.ndarray,
                     c: float = 3e8) -> float:
    """
    Net forward component  P_forward ~ integral (E x H) . n_hat  dV.

    E, H : (M, 3) field samples over volume elements of equal weight.
    n_hat : (3,) unit thrust-axis direction.
    """
    S = poynting_vector(E, H, c)          # (M, 3)
    return float(np.sum(S @ n_hat))


# ---------------------------------------------------------------------------
# 6. Energy density (Section 5)
# ---------------------------------------------------------------------------

def energy_density(E_mag: np.ndarray, H_mag: np.ndarray,
                   epsilon: float = 8.854e-12,
                   mu: float = 1.2566e-6) -> np.ndarray:
    """
    U = 0.5 * (epsilon * E^2  +  mu * H^2).

    E_mag, H_mag : scalar field magnitudes (any shape, must match).
    """
    return 0.5 * (epsilon * E_mag ** 2 + mu * H_mag ** 2)


# ---------------------------------------------------------------------------
# 7. Coherence metric (Appendix A.1)
# ---------------------------------------------------------------------------

def coherence(phases: np.ndarray) -> complex:
    """
    I_coherence = (1/N) sum_i exp(j (phi_i - phi_bar)).

    |I_coherence| in [0, 1]:  1 = perfect traveling wave, 0 = chaotic.
    """
    phi_bar = np.mean(phases)
    return np.mean(np.exp(1j * (phases - phi_bar)))


def coherence_magnitude(phases: np.ndarray) -> float:
    """Scalar coherence measure in [0, 1]."""
    return float(np.abs(coherence(phases)))


# ---------------------------------------------------------------------------
# 8. Coupling matrix & propagation modes (Section 4)
# ---------------------------------------------------------------------------

def coupling_matrix(phases: np.ndarray, k_c: float) -> np.ndarray:
    """
    Build the N x N complex coupling matrix A where

        A_ij = k_c * exp(j (phi_j - phi_i))   if |i-j| == 1
               0                                otherwise

    Eigenvalues define propagation modes; principal eigenvector gives
    the direction of energy transfer.
    """
    N = len(phases)
    A = np.zeros((N, N), dtype=complex)
    for i in range(N):
        for j in range(N):
            if abs(i - j) == 1:
                A[i, j] = k_c * np.exp(1j * (phases[j] - phases[i]))
    return A


def propagation_modes(phases: np.ndarray,
                      k_c: float) -> Tuple[np.ndarray, np.ndarray]:
    """
    Return (eigenvalues, eigenvectors) of the coupling matrix.
    Sorted by descending magnitude of eigenvalue.
    """
    A = coupling_matrix(phases, k_c)
    vals, vecs = np.linalg.eig(A)
    order = np.argsort(-np.abs(vals))
    return vals[order], vecs[:, order]


# ---------------------------------------------------------------------------
# 9. Efficiency ratio eta (Appendix B)
# ---------------------------------------------------------------------------

def phase_entropy(amplitudes: np.ndarray) -> float:
    """
    Shannon-like entropy of the energy distribution across emitters.

        p_i = |E_i|^2 / sum |E_j|^2
        I_entropy = -sum p_i ln(p_i)

    Returns 0 when a single emitter dominates (perfect order).
    """
    power = amplitudes ** 2
    total = power.sum()
    if total == 0:
        return 0.0
    p = power / total
    # Guard against log(0)
    p = p[p > 0]
    return float(-np.sum(p * np.log(p)))


def directed_energy(E_mag: np.ndarray, H_mag: np.ndarray,
                    cos_theta: np.ndarray,
                    epsilon: float = 8.854e-12,
                    mu: float = 1.2566e-6) -> float:
    """
    E_directed = integral 0.5*(eps E^2 + mu H^2) cos(theta) dV.

    cos_theta : cosine of angle between local Poynting vector and thrust
                axis, same shape as E_mag / H_mag.
    """
    U = energy_density(E_mag, H_mag, epsilon, mu)
    return float(np.sum(U * cos_theta))


def efficiency_ratio(E_mag: np.ndarray, H_mag: np.ndarray,
                     cos_theta: np.ndarray,
                     amplitudes: np.ndarray,
                     epsilon: float = 8.854e-12,
                     mu: float = 1.2566e-6) -> float:
    """
    Field-Information Efficiency Ratio (Appendix B):

        eta = E_directed / I_entropy

    eta -> inf conceptually means perfect order from zero entropy;
    in practice we clamp the denominator to avoid division by zero.
    """
    E_dir = directed_energy(E_mag, H_mag, cos_theta, epsilon, mu)
    I_ent = phase_entropy(amplitudes)
    if I_ent < 1e-30:
        return float('inf') if E_dir > 0 else 0.0
    return E_dir / I_ent


# ---------------------------------------------------------------------------
# 10. Compression-as-acceleration proxy (Appendix A.3)
# ---------------------------------------------------------------------------

def field_acceleration(phases: np.ndarray, z_positions: np.ndarray,
                       dt: float) -> float:
    """
    a_field ~ d/dz (d phi / dt).

    Approximated via finite-difference: spatial gradient of the phase rate.
    phases : (N,) instantaneous phases at node positions z_positions.
    dt : time step used to estimate d(phi)/dt (caller supplies delta).
    """
    dphi_dt = np.gradient(phases) / dt      # rough phase-rate proxy
    d2phi_dz = np.gradient(dphi_dt, z_positions)
    return float(np.mean(d2phi_dz))
