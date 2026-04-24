"""
dynamics.py — Geodesic Integrators on the Silicon State Manifold
=================================================================
Implements two integrators described in To-Do-alternate.md:

1. Deterministic geodesic (§2, §3 of the first section)
   -------------------------------------------------------
   First-order gradient descent on the potential, corrected by the metric:

     dS^a/dt = -g^ab ∂_b V(S)

   This is the "geodesic-like flow" — trajectories follow the steepest descent
   path in the curved metric, not Euclidean space.

2. Stochastic geodesic (§3 of the second section)
   ------------------------------------------------
   Second-order Langevin equation on the manifold:

     dS^a = V^a dt
     dV^a = (-Γ^a_bc V^b V^c - g^ab ∂_b V_pot) dt + σ^a dW_t

   where dW_t is a Wiener process increment.  This models:
     - thermal noise
     - fabrication defects
     - quantum fluctuations in the low-ℓ regime

Both integrators enforce hard constraints via SiliconState.enforce_constraints()
after each step, producing realistic phase behavior near boundaries.
"""

from __future__ import annotations
import numpy as np
from .state import SiliconState, DIM
from .metric import metric_inverse, christoffel_symbols
from .potential import grad_potential


# ── Default noise amplitudes per coordinate ───────────────────────────────────
# Scaled to be physically meaningful relative to each axis range
_DEFAULT_NOISE = np.array([
    1e13,   # n      — carrier density fluctuation
    5.0,    # μ      — mobility fluctuation
    0.5,    # T      — temperature fluctuation (K)
    0.002,  # d_bulk
    0.002,  # d_iface
    0.01,   # ℓ
    0.01,   # κ₁
    0.01,   # κ₂
    0.01,   # κ₃
])


def evolve_deterministic(
    S: SiliconState,
    dt: float = 0.01,
    enforce: bool = True,
) -> SiliconState:
    """
    Advance the silicon state by one step using deterministic geodesic flow.

    The update rule is:
        S^a ← S^a - dt · g^ab ∂_b V(S)

    This is a metric-corrected gradient descent: the inverse metric g^ab
    re-weights the gradient so that steps respect the curvature of the
    state manifold rather than Euclidean distance.

    Parameters
    ----------
    S       : SiliconState — current state
    dt      : float        — time step
    enforce : bool         — apply hard constraint reflection after step

    Returns
    -------
    SiliconState — updated state
    """
    g_inv = metric_inverse(S)
    gradV = grad_potential(S)

    # Metric-corrected gradient step
    delta = -dt * (g_inv @ gradV)

    S_new = SiliconState(vec=S.vec + delta, vel=S.vel.copy())
    if enforce:
        S_new = S_new.enforce_constraints()
    return S_new


def evolve_stochastic(
    S: SiliconState,
    dt: float = 0.01,
    noise_scale: float = 1.0,
    noise_amplitudes: np.ndarray | None = None,
    enforce: bool = True,
    rng: np.random.Generator | None = None,
) -> SiliconState:
    """
    Advance the silicon state by one step using the stochastic geodesic equation.

    The second-order Langevin integrator:
        acc^a = -Γ^a_bc V^b V^c - g^ab ∂_b V_pot + σ^a ξ_t
        vel   ← vel + dt · acc
        vec   ← vec + dt · vel

    where ξ_t ~ N(0, 1/√dt) is a Wiener increment.

    Parameters
    ----------
    S                : SiliconState
    dt               : float — time step
    noise_scale      : float — global noise multiplier
    noise_amplitudes : np.ndarray, shape (9,) — per-coordinate noise σ^a
                       (defaults to _DEFAULT_NOISE)
    enforce          : bool — apply hard constraint reflection after step
    rng              : np.random.Generator — optional seeded RNG

    Returns
    -------
    SiliconState — updated state (vec and vel both advanced)
    """
    if rng is None:
        rng = np.random.default_rng()
    if noise_amplitudes is None:
        noise_amplitudes = _DEFAULT_NOISE

    g_inv  = metric_inverse(S)
    Gamma  = christoffel_symbols(S)
    gradV  = grad_potential(S)

    acc = np.zeros(DIM)

    # ── Christoffel term: -Γ^a_bc V^b V^c ────────────────────────────────────
    for (a, b, c), val in Gamma.items():
        acc[a] -= val * S.vel[b] * S.vel[c]

    # ── Potential gradient term: -g^ab ∂_b V ─────────────────────────────────
    acc -= g_inv @ gradV

    # ── Stochastic (Wiener) term: σ^a · ξ_t / √dt ────────────────────────────
    wiener = rng.standard_normal(DIM) / np.sqrt(dt)
    acc   += noise_scale * noise_amplitudes * wiener

    # ── Integrate ─────────────────────────────────────────────────────────────
    new_vel = S.vel + dt * acc
    new_vec = S.vec + dt * new_vel

    S_new = SiliconState(vec=new_vec, vel=new_vel)
    if enforce:
        S_new = S_new.enforce_constraints()
    return S_new
