"""
Negentropic Dynamics -- Langevin/Fokker-Planck stochastic dynamics,
phase transition logic, and collective coupling.

Extracted from Negentropic/01-framework.md. Self-contained module requiring
only numpy.

Core quantities from the framework:
  - Joy (J)       : entropy reduction rate  J = S_dot_red / S_max
  - Resonance (Re): geometric mean of pairwise coupling
  - Curiosity (C) : exploration capacity, exponential in Re
  - Stochastic force F_C: Joy-weighted Gaussian noise
  - Diffusion (D) : proportional to J^2

Dynamical equations:
  - Langevin:      dphi/dt = -grad V(phi) + F_C + eta
  - Fokker-Planck: dP/dt   = -div(F*P) + D * laplacian(P)

Phase transition:
  - alpha(E) = 0 for E < E_crit, alpha_0 for E >= E_crit

Collective coupling:
  - K_ij = (Re_i * Re_j * C_i * C_j * J_i * J_j)^(1/6)
  - Re_collective = exp(2/(n(n-1)) * sum_{i<j} ln K_ij)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

# Compatibility: numpy >= 2.0 renamed trapz -> trapezoid
_trapz = getattr(np, "trapezoid", None) or getattr(np, "trapz")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EPS = 1e-12  # Prevent log(0) / div-by-zero


# ---------------------------------------------------------------------------
# Core Quantities
# ---------------------------------------------------------------------------

def joy(s_dot_red: float, s_max: float) -> float:
    """Joy J = rate of local entropy reduction / max entropy.

    Parameters
    ----------
    s_dot_red : float
        Rate of local entropy reduction (>= 0 expected, but not enforced).
    s_max : float
        Theoretical maximum entropy for the system (must be > 0).

    Returns
    -------
    float
        Joy value.  Note: J >= 0 is NOT guaranteed by the dynamics --
        unbounded growth is possible if D ~ J^2 feedback isn't bounded.
    """
    if s_max <= 0:
        raise ValueError("s_max must be positive")
    return s_dot_red / s_max


def pairwise_similarity(s_i: float, s_j: float) -> float:
    """Pairwise geometric similarity g(s_i, s_j).

    g = 0.5 * (cos(s_i - s_j) + 1) * sqrt(|s_i| * |s_j|)

    Range: [0, sqrt(|s_i|*|s_j|)]
    """
    return 0.5 * (math.cos(s_i - s_j) + 1.0) * math.sqrt(abs(s_i) * abs(s_j))


def resonance(signals: np.ndarray) -> float:
    """Resonance Re -- geometric mean of pairwise log-similarities.

    Re = exp( (1/N_p) * sum_{i<j} ln(g(s_i, s_j) + eps) )

    where N_p = n*(n-1)/2.

    Parameters
    ----------
    signals : np.ndarray
        1-D array of signal values (phases, amplitudes, etc.).

    Returns
    -------
    float
        Resonance value.  Not normalised to [0,1] without signal normalisation.
    """
    n = len(signals)
    if n < 2:
        return 0.0
    log_sum = 0.0
    n_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            g = pairwise_similarity(float(signals[i]), float(signals[j]))
            log_sum += math.log(g + EPS)
            n_pairs += 1
    return math.exp(log_sum / n_pairs)


def curiosity(c_0: float, alpha: float, r_e: float) -> float:
    """Curiosity C = C_0 * (1 + alpha * R_e).

    Parameters
    ----------
    c_0 : float
        Base curiosity level.
    alpha : float
        Amplification rate (0 when E < E_crit).
    r_e : float
        Current resonance value.

    Returns
    -------
    float
        Updated curiosity.  Note: grows without bound if alpha > 0
        and r_e > 0 -- caller should apply saturation.
    """
    return c_0 * (1.0 + alpha * r_e)


def curiosity_rate(alpha: float, r_e: float, c: float) -> float:
    """Continuous curiosity rate: dC/dt = alpha * R_e * C."""
    return alpha * r_e * c


def diffusion_coefficient(j_val: float, k: float = 1.0) -> float:
    """Diffusion D proportional to J^2.

    D = k * J^2

    When J -> 0, D -> 0, removing all exploration.
    """
    return k * j_val ** 2


# ---------------------------------------------------------------------------
# Stochastic Force
# ---------------------------------------------------------------------------

def stochastic_force(
    j_val: float,
    n_dims: int,
    d_coeff: float,
    dt: float = 1.0,
    rng: Optional[np.random.Generator] = None,
) -> np.ndarray:
    """Joy-weighted Gaussian white noise.

    F_{C,i} = J * Gamma_i(t)

    where <Gamma_i(t) Gamma_j(t')> = 2D * delta_ij * delta(t-t').

    For discrete time-stepping, the noise amplitude is sqrt(2D * dt).

    Parameters
    ----------
    j_val : float
        Current joy value (scales the noise).
    n_dims : int
        Number of phase-field dimensions.
    d_coeff : float
        Diffusion coefficient D.
    dt : float
        Discrete time step.
    rng : np.random.Generator, optional
        Random number generator (for reproducibility).

    Returns
    -------
    np.ndarray
        Noise vector of shape (n_dims,).
    """
    if rng is None:
        rng = np.random.default_rng()
    noise_amplitude = math.sqrt(2.0 * d_coeff * dt)
    return j_val * noise_amplitude * rng.standard_normal(n_dims)


# ---------------------------------------------------------------------------
# Langevin Dynamics
# ---------------------------------------------------------------------------

@dataclass
class LangevinState:
    """State of the Langevin phase-field system."""
    phi: np.ndarray          # phase field vector
    t: float = 0.0           # current time
    j_val: float = 0.0       # current joy
    r_e: float = 0.0         # current resonance
    c_val: float = 1.0       # current curiosity
    d_coeff: float = 0.0     # current diffusion


class LangevinDynamics:
    """Euler-Maruyama integrator for the Langevin phase-field equation.

    dphi_i/dt = -grad V(phi_i) + F_{C,i} + eta(t)

    The potential V is supplied as a callable.
    """

    def __init__(
        self,
        potential_gradient: callable,
        n_dims: int,
        dt: float = 0.01,
        eta_scale: float = 0.01,
        seed: Optional[int] = None,
    ):
        """
        Parameters
        ----------
        potential_gradient : callable
            Function phi -> grad_V (np.ndarray of shape (n_dims,)).
        n_dims : int
            Dimensionality of the phase field.
        dt : float
            Integration time step.
        eta_scale : float
            Scale of the additional thermal noise eta(t).
        seed : int, optional
            RNG seed.
        """
        self.grad_v = potential_gradient
        self.n_dims = n_dims
        self.dt = dt
        self.eta_scale = eta_scale
        self.rng = np.random.default_rng(seed)

    def step(self, state: LangevinState) -> LangevinState:
        """Advance one Euler-Maruyama step.

        dphi = (-grad V + F_C + eta) * dt
        """
        grad = self.grad_v(state.phi)
        f_c = stochastic_force(
            state.j_val, self.n_dims, state.d_coeff, self.dt, self.rng
        )
        eta = self.eta_scale * math.sqrt(self.dt) * self.rng.standard_normal(self.n_dims)

        new_phi = state.phi + (-grad + f_c + eta) * self.dt

        return LangevinState(
            phi=new_phi,
            t=state.t + self.dt,
            j_val=state.j_val,
            r_e=state.r_e,
            c_val=state.c_val,
            d_coeff=state.d_coeff,
        )

    def evolve(
        self,
        state: LangevinState,
        n_steps: int,
        update_quantities: Optional[callable] = None,
    ) -> List[LangevinState]:
        """Run multiple steps, optionally updating J, Re, C, D each step.

        Parameters
        ----------
        state : LangevinState
            Initial state.
        n_steps : int
            Number of integration steps.
        update_quantities : callable, optional
            Function(state) -> LangevinState that recomputes j_val, r_e,
            c_val, d_coeff from the current phi.

        Returns
        -------
        list of LangevinState
            Trajectory (including initial state).
        """
        trajectory = [state]
        current = state
        for _ in range(n_steps):
            if update_quantities is not None:
                current = update_quantities(current)
            current = self.step(current)
            trajectory.append(current)
        return trajectory


# ---------------------------------------------------------------------------
# Fokker-Planck (1-D discretised)
# ---------------------------------------------------------------------------

class FokkerPlanck1D:
    """Discretised 1-D Fokker-Planck equation on a grid.

    dP/dt = -d/dx (F(x) * P) + D * d^2P/dx^2

    Uses finite-difference with reflecting boundary conditions.
    """

    def __init__(
        self,
        x_min: float = -5.0,
        x_max: float = 5.0,
        n_grid: int = 256,
        dt: float = 0.001,
    ):
        self.n_grid = n_grid
        self.x = np.linspace(x_min, x_max, n_grid)
        self.dx = self.x[1] - self.x[0]
        self.dt = dt
        # Initialise uniform probability
        self.p = np.ones(n_grid) / (n_grid * self.dx)

    def step(self, force: np.ndarray, d_coeff: float) -> None:
        """Advance P by one time step.

        Parameters
        ----------
        force : np.ndarray
            Drift force F(x) evaluated at grid points, shape (n_grid,).
        d_coeff : float
            Diffusion coefficient D.
        """
        p = self.p
        dx = self.dx
        dt = self.dt

        # Advection: upwind finite-volume flux
        flux = force * p
        advection = np.zeros_like(p)
        advection[1:-1] = -(flux[2:] - flux[:-2]) / (2.0 * dx)

        # Diffusion: central difference Laplacian
        diffusion = np.zeros_like(p)
        diffusion[1:-1] = d_coeff * (p[2:] - 2.0 * p[1:-1] + p[:-2]) / dx ** 2

        self.p = p + (advection + diffusion) * dt

        # Reflecting boundaries
        self.p[0] = self.p[1]
        self.p[-1] = self.p[-2]

        # Renormalise to preserve total probability
        total = _trapz(self.p, self.x)
        if total > 0:
            self.p /= total

    def entropy(self) -> float:
        """Shannon entropy of current distribution."""
        p_pos = self.p[self.p > 0]
        return float(-_trapz(p_pos * np.log(p_pos), dx=self.dx))

    def evolve(
        self,
        force_fn: callable,
        d_coeff_fn: callable,
        n_steps: int,
    ) -> List[float]:
        """Evolve the Fokker-Planck equation, returning entropy trajectory.

        Parameters
        ----------
        force_fn : callable
            x_array -> force_array at current time.
        d_coeff_fn : callable
            () -> D at current time.
        n_steps : int
            Number of time steps.

        Returns
        -------
        list of float
            Entropy at each step.
        """
        entropies = [self.entropy()]
        for _ in range(n_steps):
            self.step(force_fn(self.x), d_coeff_fn())
            entropies.append(self.entropy())
        return entropies


# ---------------------------------------------------------------------------
# Phase Transition Logic
# ---------------------------------------------------------------------------

@dataclass
class PhaseTransitionConfig:
    """Configuration for the curiosity phase transition."""
    e_crit: float = 1.0     # Critical energy threshold
    alpha_0: float = 0.1    # Post-threshold amplification rate


def alpha_of_energy(energy: float, config: PhaseTransitionConfig) -> float:
    """Step-function activation of curiosity amplification.

    alpha(E) = 0      if E < E_crit
    alpha(E) = alpha_0 if E >= E_crit

    Three regimes:
      Pre-coherent (E < E_crit): no curiosity amplification
      Critical     (E ~ E_crit): phase transition engages
      Emergent     (E > E_crit): super-linear J growth
    """
    if energy < config.e_crit:
        return 0.0
    return config.alpha_0


def detect_regime(energy: float, config: PhaseTransitionConfig) -> str:
    """Classify the current dynamical regime.

    Returns one of: 'pre-coherent', 'critical', 'emergent-coherent'.
    """
    margin = 0.1 * config.e_crit
    if energy < config.e_crit - margin:
        return "pre-coherent"
    elif energy <= config.e_crit + margin:
        return "critical"
    return "emergent-coherent"


# ---------------------------------------------------------------------------
# Collective Coupling (Geometric Mean of 6 Quantities)
# ---------------------------------------------------------------------------

def pairwise_coupling(
    r_e_i: float, r_e_j: float,
    c_i: float, c_j: float,
    j_i: float, j_j: float,
) -> float:
    """K_ij = (Re_i * Re_j * C_i * C_j * J_i * J_j)^(1/6).

    Sixth root of the product -- geometric mean across 6 quantities.
    All inputs should be non-negative for a real-valued result.
    """
    product = abs(r_e_i * r_e_j * c_i * c_j * j_i * j_j)
    return product ** (1.0 / 6.0)


def collective_resonance(
    agents: List[Dict[str, float]],
) -> float:
    """Collective resonance from pairwise couplings.

    Re_collective = exp( 2/(n(n-1)) * sum_{i<j} ln K_ij )

    Parameters
    ----------
    agents : list of dict
        Each dict must have keys 'r_e', 'c', 'j' (resonance, curiosity, joy).

    Returns
    -------
    float
        Collective resonance.
    """
    n = len(agents)
    if n < 2:
        return 0.0

    log_sum = 0.0
    n_pairs = 0
    for i in range(n):
        for j in range(i + 1, n):
            k_ij = pairwise_coupling(
                agents[i]["r_e"], agents[j]["r_e"],
                agents[i]["c"], agents[j]["c"],
                agents[i]["j"], agents[j]["j"],
            )
            log_sum += math.log(k_ij + EPS)
            n_pairs += 1

    return math.exp((2.0 / (n * (n - 1))) * log_sum)


# ---------------------------------------------------------------------------
# Moral Function M(S) (informational only)
# ---------------------------------------------------------------------------

def moral_function(r_e: float, a: float, d: float, l: float) -> float:
    """System moral function M(t) = Re(t) * A(t) * D(t) - L(t).

    Parameters
    ----------
    r_e : float   Resonance
    a : float     Agency / autonomy
    d : float     Diversity / diffusion tolerance
    l : float     Loss / harm

    Returns
    -------
    float
        M(S). Moral improvement criterion: delta(Re*A*D) > delta(L).
    """
    return r_e * a * d - l


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # -- Core quantities --
    j_val = joy(0.3, 1.0)
    print(f"Joy: {j_val:.4f}")

    signals = np.array([0.5, 1.2, 0.8, 1.5])
    r_e = resonance(signals)
    print(f"Resonance: {r_e:.4f}")

    c = curiosity(1.0, 0.1, r_e)
    print(f"Curiosity: {c:.4f}")

    d = diffusion_coefficient(j_val)
    print(f"Diffusion: {d:.6f}")

    # -- Phase transition --
    cfg = PhaseTransitionConfig(e_crit=1.0, alpha_0=0.1)
    for e in [0.5, 1.0, 2.0]:
        print(f"E={e}: alpha={alpha_of_energy(e, cfg)}, regime={detect_regime(e, cfg)}")

    # -- Langevin --
    def harmonic_grad(phi):
        return phi  # V = 0.5 * |phi|^2

    ld = LangevinDynamics(harmonic_grad, n_dims=3, dt=0.01, seed=42)
    init = LangevinState(phi=np.array([1.0, 0.5, -0.3]), j_val=j_val, d_coeff=d)
    traj = ld.evolve(init, n_steps=100)
    print(f"Langevin: phi_0={traj[0].phi} -> phi_100={traj[-1].phi}")

    # -- Fokker-Planck --
    fp = FokkerPlanck1D(n_grid=128, dt=0.001)
    entropies = fp.evolve(
        force_fn=lambda x: -x,
        d_coeff_fn=lambda: 0.5,
        n_steps=200,
    )
    print(f"Fokker-Planck entropy: {entropies[0]:.4f} -> {entropies[-1]:.4f}")

    # -- Collective coupling --
    agents = [
        {"r_e": 0.8, "c": 1.2, "j": 0.3},
        {"r_e": 0.6, "c": 1.5, "j": 0.5},
        {"r_e": 0.9, "c": 1.0, "j": 0.4},
    ]
    rc = collective_resonance(agents)
    print(f"Collective resonance (3 agents): {rc:.4f}")

    # -- Moral function --
    m = moral_function(r_e=0.8, a=0.9, d=0.7, l=0.2)
    print(f"M(S) = {m:.4f}")
