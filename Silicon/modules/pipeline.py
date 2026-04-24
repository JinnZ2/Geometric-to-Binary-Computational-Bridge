"""
pipeline.py — Unified Closed-Loop System Runner
================================================
Implements the full co-evolution loop described in To-Do-alternate.md §6
(step_full) and the step_system function, unifying all modules into a single
configurable runner.

The closed loop is:
    φ(x) → [coupling] → S → [dynamics] → S → [operators] → y(x) → [feedback] → S
                                                                         ↓
                                                                    [regime] → atlas

Each step:
  1. Geometry field drives silicon state (coupling.update_with_geometry)
  2. Silicon state evolves on manifold (dynamics.evolve_stochastic or deterministic)
  3. Spatial kernel is built from state + field (operators.build_kernel)
  4. Computation output field is evaluated (operators.evaluate_field)
  5. Output feeds back into state (operators.feedback_update)
  6. Geometry field is updated via PDE step (optional)
  7. Regime is classified (regime.classify_regime)

Trajectory recording
--------------------
All state snapshots, output fields, and regime labels are stored in a
PipelineResult object for downstream analysis and visualisation.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import numpy as np

from .state import SiliconState, make_state
from .coupling import update_with_geometry, field_from_state
from .dynamics import evolve_deterministic, evolve_stochastic
from .operators import build_kernel, evaluate_field, feedback_update
from .regime import classify_regime, RegimeAtlas


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    """
    Configuration for the closed-loop pipeline runner.

    Parameters
    ----------
    steps           : int   — number of time steps to run
    dt              : float — time step size
    integrator      : str   — "stochastic" or "deterministic"
    noise_scale     : float — noise amplitude for stochastic integrator
    N_spatial       : int   — number of spatial grid points
    x_range         : tuple — (x_min, x_max) for spatial grid
    pde_coupling    : bool  — evolve geometry field via PDE each step
    pde_D           : float — diffusion coefficient for field PDE
    pde_beta        : float — nonlinear coefficient for field PDE
    pde_lambda      : float — feedback coupling strength (y → ψ)
    feedback_dt     : float — dt scaling for feedback update
    record_every    : int   — record trajectory snapshot every N steps
    seed            : int   — random seed for reproducibility
    """
    steps        : int   = 200
    dt           : float = 0.01
    integrator   : Literal["stochastic", "deterministic"] = "stochastic"
    noise_scale  : float = 0.1
    N_spatial    : int   = 64
    x_range      : tuple = (-5.0, 5.0)
    pde_coupling : bool  = True
    pde_D        : float = 0.2
    pde_beta     : float = 1.0
    pde_lambda   : float = 0.05
    feedback_dt  : float = 0.01
    record_every : int   = 1
    seed         : int   = 42


# ── Result container ──────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """
    Recorded trajectory from a pipeline run.

    Attributes
    ----------
    times      : list[float]          — time values at each recorded step
    states     : list[np.ndarray]     — state vectors shape (9,)
    psi_fields : list[np.ndarray]     — ψ(x) fields shape (N,)
    phi_fields : list[np.ndarray]     — φ(x) fields shape (N,)
    y_fields   : list[np.ndarray]     — y(x) output fields shape (N,)
    regimes    : list[RegimeAtlas]    — regime classification at each step
    config     : PipelineConfig
    x          : np.ndarray           — spatial grid
    """
    times      : list = field(default_factory=list)
    states     : list = field(default_factory=list)
    psi_fields : list = field(default_factory=list)
    phi_fields : list = field(default_factory=list)
    y_fields   : list = field(default_factory=list)
    regimes    : list = field(default_factory=list)
    config     : PipelineConfig = field(default_factory=PipelineConfig)
    x          : np.ndarray = field(default_factory=lambda: np.array([]))

    def state_array(self) -> np.ndarray:
        """Return all recorded state vectors as shape (T, 9) array."""
        return np.array(self.states)

    def y_array(self) -> np.ndarray:
        """Return all output fields as shape (T, N) array."""
        return np.array(self.y_fields)

    def regime_labels(self) -> list[str]:
        """Return dominant regime label at each recorded step."""
        return [r.label for r in self.regimes]

    def lambda_series(self) -> np.ndarray:
        """Return coupling strength Λ over time."""
        return np.array([r.Lambda_ for r in self.regimes])

    def omega2_mean_series(self) -> np.ndarray:
        """Return mean Ω² over time."""
        return np.array([r.sigma for r in self.regimes])


# ── PDE step for geometry field ───────────────────────────────────────────────

def _pde_step(
    psi: np.ndarray,
    x: np.ndarray,
    y: np.ndarray,
    D: float,
    beta: float,
    lam: float,
    dt: float,
) -> np.ndarray:
    """
    Advance the geometry field ψ(x) by one PDE step:
        ∂ψ/∂t = D·∇²ψ - (β/2)·ψ·(1 + ψ²) + λ·y(x)

    Uses central finite differences for the Laplacian.
    """
    dx  = x[1] - x[0]
    lap = np.gradient(np.gradient(psi, dx), dx)
    dpsi = D * lap - (beta / 2.0) * psi * (1.0 + psi ** 2) + lam * y
    return psi + dt * dpsi


# ── Main runner ───────────────────────────────────────────────────────────────

def run_pipeline(
    S0: SiliconState | None = None,
    config: PipelineConfig | None = None,
    initial_psi: np.ndarray | None = None,
) -> PipelineResult:
    """
    Run the full closed-loop co-evolution pipeline.

    Parameters
    ----------
    S0          : SiliconState — initial silicon state (default: make_state())
    config      : PipelineConfig — run configuration (default: PipelineConfig())
    initial_psi : np.ndarray — initial geometry field ψ(x); defaults to
                               a Gaussian pulse

    Returns
    -------
    PipelineResult — full trajectory record
    """
    if config is None:
        config = PipelineConfig()
    if S0 is None:
        S0 = make_state()

    rng = np.random.default_rng(config.seed)

    # ── Spatial grid ──────────────────────────────────────────────────────────
    x = np.linspace(config.x_range[0], config.x_range[1], config.N_spatial)

    # ── Initial fields ────────────────────────────────────────────────────────
    if initial_psi is None:
        psi = np.exp(-x ** 2)   # Gaussian pulse
    else:
        psi = initial_psi.copy()

    phi = field_from_state(S0, x)

    S   = S0.copy()
    result = PipelineResult(config=config, x=x)

    for step in range(config.steps):
        t = step * config.dt

        # 1. Geometry field drives silicon state
        S = update_with_geometry(S, phi, dt=config.dt)

        # 2. Silicon state evolves on manifold
        if config.integrator == "stochastic":
            S = evolve_stochastic(
                S, dt=config.dt,
                noise_scale=config.noise_scale,
                rng=rng,
            )
        else:
            S = evolve_deterministic(S, dt=config.dt)

        # 3. Build spatial kernel and evaluate output field
        W = build_kernel(x, phi, S)
        y = evaluate_field(W, psi)

        # 4. Feedback: computation output updates silicon state
        S = feedback_update(S, y, dt=config.feedback_dt)

        # 5. Evolve geometry field via PDE (optional)
        if config.pde_coupling:
            psi = _pde_step(psi, x, y, config.pde_D, config.pde_beta, config.pde_lambda, config.dt)

        # 6. Regenerate φ from updated S (bidirectional coupling)
        phi = field_from_state(S, x)

        # 7. Classify regime
        atlas = classify_regime(S, psi=psi, field=phi)

        # ── Record ────────────────────────────────────────────────────────────
        if step % config.record_every == 0:
            result.times.append(t)
            result.states.append(S.vec.copy())
            result.psi_fields.append(psi.copy())
            result.phi_fields.append(phi.copy())
            result.y_fields.append(y.copy())
            result.regimes.append(atlas)

    return result
