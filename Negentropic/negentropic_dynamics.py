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
  - Langevin:      dphi/dt = -grad V(phi) + F_C + eta   (+ spurious drift,
                   see spurious_drift(); D depends on state here)
  - Fokker-Planck: dP/dt   = -div(F*P) + laplacian(D*P)  [Ito]

The Fokker-Planck term is laplacian(D*P), not D*laplacian(P). Those are the
same only for constant D, and this framework sets D = k*J^2 with J a
function of state. The framework text (01-framework.md) previously wrote the
constant-D form, which is why the "D -> 0 collapse" result did not actually
follow from the equation as written; it does follow from the form here.

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
        diffusion_gradient: Optional[callable] = None,
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
        diffusion_gradient : callable, optional
            Function phi -> dD/dphi (np.ndarray of shape (n_dims,)). Supply
            this whenever D depends on state -- which it does under the
            framework's D = k*J^2 -- and the integrator adds the Ito
            spurious drift (1/2) dD/dphi. Leaving it None integrates as if D
            were locally constant, which has no correct stationary
            distribution when it is not. See spurious_drift().
        """
        self.grad_v = potential_gradient
        self.n_dims = n_dims
        self.dt = dt
        self.eta_scale = eta_scale
        self.grad_d = diffusion_gradient
        self.rng = np.random.default_rng(seed)

    def step(self, state: LangevinState) -> LangevinState:
        """Advance one Euler-Maruyama step.

        dphi = (-grad V + (1/2) dD/dphi + F_C + eta) * dt
        """
        grad = self.grad_v(state.phi)
        f_c = stochastic_force(
            state.j_val, self.n_dims, state.d_coeff, self.dt, self.rng
        )
        eta = self.eta_scale * math.sqrt(self.dt) * self.rng.standard_normal(self.n_dims)
        drift_correction = (
            0.5 * np.asarray(self.grad_d(state.phi), dtype=float)
            if self.grad_d is not None
            else 0.0
        )

        new_phi = state.phi + (-grad + drift_correction + f_c + eta) * self.dt

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

def spurious_drift(d_values: np.ndarray, dx: float) -> np.ndarray:
    """Ito drift correction for a state-dependent diffusion coefficient.

    A Stratonovich SDE ``dphi = A dt + sqrt(2 D(phi)) o dW`` is the same
    process as the Ito SDE ``dphi = (A + (1/2) dD/dphi) dt + sqrt(2 D(phi)) dW``.
    The extra ``(1/2) dD/dphi`` is the spurious (or noise-induced) drift.
    Omitting it is not a small error: the simulated process then has no
    correct stationary distribution, so anything read off the steady state
    -- including the ``D -> 0`` collapse result -- does not follow.

    This matters here because the framework sets ``D = k J^2`` with ``J`` a
    function of state, so ``D`` is state-dependent by construction.
    """
    return 0.5 * np.gradient(np.asarray(d_values, dtype=float), dx)


class FokkerPlanck1D:
    """Discretised 1-D Fokker-Planck equation on a grid.

    Ito convention (the default), for a possibly state-dependent D::

        dP/dt = -d/dx (F P) + d^2/dx^2 (D P)

    Stratonovich convention::

        dP/dt = -d/dx (F P) + d/dx ( sqrt(D) d/dx ( sqrt(D) P ) )

    The two agree only when D is constant, in which case both reduce to
    ``D d^2P/dx^2``. Writing the constant-D form and then passing a
    state-dependent D -- which is what the framework's ``D ~ J^2`` does --
    silently solves a different equation from the one intended.

    Uses finite differences with reflecting boundary conditions.
    """

    def __init__(
        self,
        x_min: float = -5.0,
        x_max: float = 5.0,
        n_grid: int = 256,
        dt: float = 0.001,
        convention: str = "ito",
    ):
        if convention not in ("ito", "stratonovich"):
            raise ValueError("convention must be 'ito' or 'stratonovich'")
        self.n_grid = n_grid
        self.x = np.linspace(x_min, x_max, n_grid)
        self.dx = self.x[1] - self.x[0]
        self.dt = dt
        self.convention = convention
        # Initialise uniform probability
        self.p = np.ones(n_grid) / (n_grid * self.dx)

    def step(self, force: np.ndarray, d_coeff) -> None:
        """Advance P by one time step.

        Parameters
        ----------
        force : np.ndarray
            Drift force F(x) evaluated at grid points, shape (n_grid,).
        d_coeff : float or np.ndarray
            Diffusion coefficient D. A scalar is broadcast; an array of
            shape (n_grid,) is treated as state-dependent and integrated
            under ``self.convention``.
        """
        p = self.p
        dx = self.dx
        dt = self.dt

        d_arr = np.asarray(d_coeff, dtype=float)
        if d_arr.ndim == 0:
            d_arr = np.full_like(p, float(d_arr))
        elif d_arr.shape != p.shape:
            raise ValueError(f"d_coeff must be scalar or shape {p.shape}")
        if np.any(d_arr < 0):
            raise ValueError("diffusion coefficient must be non-negative")

        # Conservative flux form. The probability current on the interior
        # cell faces (half-grid points) is
        #     J = F p - d(D p)/dx                 [Ito]
        #     J = F p - sqrt(D) d(sqrt(D) p)/dx   [Stratonovich]
        # and dp/dt = -dJ/dx. Zero current at both ends is the reflecting
        # boundary condition, imposed exactly rather than by copying edge
        # values afterwards.
        #
        # The previous version differenced the drift and diffusion terms
        # separately on the interior, zeroed them at the edges, copied edge
        # values, and renormalised. That scheme does not conserve
        # probability: for a uniform p the drift term contributes a spatially
        # constant d(xp)/dx = p that renormalisation then divides straight
        # back out, making the uniform distribution a spurious fixed point.
        # The D -> 0 collapse result could not be demonstrated with it.
        face_force = 0.5 * (force[:-1] + force[1:])
        face_p = 0.5 * (p[:-1] + p[1:])

        if self.convention == "ito":
            g = d_arr * p
            grad_term = (g[1:] - g[:-1]) / dx
        else:
            root = np.sqrt(d_arr)
            face_root = 0.5 * (root[:-1] + root[1:])
            grad_term = face_root * (root[1:] * p[1:] - root[:-1] * p[:-1]) / dx

        current = face_force * face_p - grad_term

        divergence = np.zeros_like(p)
        divergence[1:-1] = -(current[1:] - current[:-1]) / dx
        # Zero-flux walls: the outermost cells exchange only inward.
        divergence[0] = -current[0] / dx
        divergence[-1] = current[-1] / dx

        self.p = p + divergence * dt
        np.maximum(self.p, 0.0, out=self.p)

        # Total probability is conserved by construction; this corrects
        # floating-point drift and the clip above, and should be a no-op of
        # order 1e-15 per step. A large correction here means dt violates
        # the stability condition dt < dx^2 / (2 max(D)).
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

    DIMENSIONALLY INVALID. D is a variance (pattern^2) and L is a power
    (pattern^2 / time^2); subtracting them is not an operation. M is an
    ordinal index comparable only against other M values computed under
    identical normalisation, and any absolute threshold on it -- "M >= 10",
    "M = 3711.50" -- is meaningless. Kept because the historical figures
    were produced with it.

    For a criterion with units that survive the subtraction, use NEG-8 in
    persistence.py: Phi = -S_exchange_dot - sigma, both in W/K, persist iff
    Phi >= 0. That criterion also has no threshold to tune.

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

    # -- Fokker-Planck: the D -> 0 collapse, actually computed --
    print("\nFokker-Planck, harmonic drift F = -x, stationary state vs D:")
    for d_const in (0.5, 0.1, 0.01):
        fp = FokkerPlanck1D(n_grid=128, dt=0.0005)
        fp.evolve(force_fn=lambda x: -x, d_coeff_fn=lambda: d_const, n_steps=20000)
        var = float(_trapz(fp.p * fp.x ** 2, fp.x))
        print(f"  D={d_const:<5} variance={var:.4f} (exact {d_const})"
              f"  entropy={fp.entropy():+.4f} nats")
    print("  variance -> D and entropy -> -inf as D -> 0: the distribution "
          "collapses to a point.")

    # -- state-dependent D: the two conventions are different models --
    print("\nSame D(x) profile under each convention:")
    for convention in ("ito", "stratonovich"):
        fp_var = FokkerPlanck1D(n_grid=128, dt=0.0005, convention=convention)
        d_profile = 0.1 + 0.4 * np.exp(-fp_var.x ** 2)
        ent = fp_var.evolve(force_fn=lambda x: -x,
                            d_coeff_fn=lambda: d_profile, n_steps=20000)
        var = float(_trapz(fp_var.p * fp_var.x ** 2, fp_var.x))
        print(f"  {convention:13s} variance={var:.4f}  entropy={ent[-1]:+.4f} nats")
    print("  different stationary states from one D profile -- the convention "
          "is part of the model, not a detail.")

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
