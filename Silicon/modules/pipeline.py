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
                                                                         ↓
                                                               [Ω² log] + [kernel trace]

Each step:
  1. Geometry field drives silicon state (coupling.update_with_geometry)
  2. Silicon state evolves on manifold (dynamics.evolve_stochastic or deterministic)
  3. Spatial kernel is built from state + field (operators.build_kernel)
  4. Computation output field is evaluated (operators.evaluate_field)
  5. Output feeds back into state (operators.feedback_update)
  6. Geometry field is updated via PDE step (optional)
  7. Regime is classified (regime.classify_regime)
  8. Ω² sign is logged with transition flag (regime.log_omega2)
  9. Kernel entanglement curvature is traced (operators.trace_kernel_curvature)
     at sampled steps (every kernel_trace_every steps)

Trajectory recording
--------------------
All state snapshots, output fields, regime labels, Ω² sign logs, and kernel
curvature traces are stored in a PipelineResult object.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal
import numpy as np

from .state import SiliconState, make_state
from .coupling import update_with_geometry, field_from_state
from .dynamics import evolve_deterministic, evolve_stochastic
from .operators import build_kernel, evaluate_field, feedback_update, trace_kernel_curvature
from .regime import classify_regime, RegimeAtlas, log_omega2, Omega2SignLog, _compute_omega2
from .operators import KernelCurvatureTrace


# ── Configuration ─────────────────────────────────────────────────────────────

@dataclass
class PipelineConfig:
    """
    Configuration for the closed-loop pipeline runner.

    Parameters
    ----------
    steps               : int   — number of time steps to run
    dt                  : float — time step size
    integrator          : str   — "stochastic" or "deterministic"
    noise_scale         : float — noise amplitude for stochastic integrator
    N_spatial           : int   — number of spatial grid points
    x_range             : tuple — (x_min, x_max) for spatial grid
    pde_coupling        : bool  — evolve geometry field via PDE each step
    pde_D               : float — diffusion coefficient for field PDE
    pde_beta            : float — nonlinear coefficient for field PDE
    pde_lambda          : float — feedback coupling strength (y → ψ)
    feedback_dt         : float — dt scaling for feedback update
    record_every        : int   — record trajectory snapshot every N steps
    kernel_trace_every  : int   — compute kernel curvature trace every N steps
                                  (0 = disabled; traces are expensive for large N)
    omega2_alpha        : float — coefficient in Ω²(x) = 1 + α·ψ(x)²
    seed                : int   — random seed for reproducibility
    """
    steps              : int   = 200
    dt                 : float = 0.01
    integrator         : Literal["stochastic", "deterministic"] = "stochastic"
    noise_scale        : float = 0.1
    N_spatial          : int   = 64
    x_range            : tuple = (-5.0, 5.0)
    pde_coupling       : bool  = True
    pde_D              : float = 0.2
    pde_beta           : float = 1.0
    pde_lambda         : float = 0.05
    feedback_dt        : float = 0.01
    record_every       : int   = 1
    kernel_trace_every : int   = 10   # trace kernel every 10 recorded steps
    omega2_alpha       : float = 1.0
    seed               : int   = 42


# ── Result container ──────────────────────────────────────────────────────────

@dataclass
class PipelineResult:
    """
    Recorded trajectory from a pipeline run.

    Attributes
    ----------
    times         : list[float]               — time values at each recorded step
    states        : list[np.ndarray]          — state vectors shape (9,)
    psi_fields    : list[np.ndarray]          — ψ(x) fields shape (N,)
    phi_fields    : list[np.ndarray]          — φ(x) fields shape (N,)
    y_fields      : list[np.ndarray]          — y(x) output fields shape (N,)
    regimes       : list[RegimeAtlas]         — regime classification at each step
    omega2_logs   : list[Omega2SignLog]       — Ω² sign log at each recorded step
    kernel_traces : list[KernelCurvatureTrace]— kernel curvature at sampled steps
    config        : PipelineConfig
    x             : np.ndarray               — spatial grid
    """
    times         : list = field(default_factory=list)
    states        : list = field(default_factory=list)
    psi_fields    : list = field(default_factory=list)
    phi_fields    : list = field(default_factory=list)
    y_fields      : list = field(default_factory=list)
    regimes       : list = field(default_factory=list)
    omega2_logs   : list = field(default_factory=list)
    kernel_traces : list = field(default_factory=list)
    config        : PipelineConfig = field(default_factory=PipelineConfig)
    x             : np.ndarray = field(default_factory=lambda: np.array([]))

    # ── Convenience accessors ─────────────────────────────────────────────────

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

    # ── Ω² diagnostic accessors ───────────────────────────────────────────────

    def omega2_log_array(self) -> dict[str, np.ndarray]:
        """
        Return Ω² log fields as a dict of arrays for easy plotting.

        Returns
        -------
        dict with keys:
          'time', 'mean', 'min', 'max', 'fraction_negative',
          'transition' (bool), 'near_boundary' (bool)
        """
        return {
            "time"             : np.array([e.time              for e in self.omega2_logs]),
            "mean"             : np.array([e.omega2_mean       for e in self.omega2_logs]),
            "min"              : np.array([e.omega2_min        for e in self.omega2_logs]),
            "max"              : np.array([e.omega2_max        for e in self.omega2_logs]),
            "fraction_negative": np.array([e.fraction_negative for e in self.omega2_logs]),
            "transition"       : np.array([e.transition        for e in self.omega2_logs]),
            "near_boundary"    : np.array([e.near_boundary     for e in self.omega2_logs]),
        }

    def transition_times(self) -> np.ndarray:
        """Return time values where Ω² sign transitions occurred."""
        return np.array([e.time for e in self.omega2_logs if e.transition])

    # ── Kernel curvature diagnostic accessors ─────────────────────────────────

    def kernel_trace_array(self) -> dict[str, np.ndarray]:
        """
        Return kernel curvature trace fields as a dict of arrays.

        Returns
        -------
        dict with keys:
          'time', 'entanglement_ratio', 'diag_mean', 'offdiag_mean',
          'spectral_gap', 'sign_changes'
        """
        return {
            "time"              : np.array([t.time               for t in self.kernel_traces]),
            "entanglement_ratio": np.array([t.entanglement_ratio for t in self.kernel_traces]),
            "diag_mean"         : np.array([t.diag_mean          for t in self.kernel_traces]),
            "offdiag_mean"      : np.array([t.offdiag_mean       for t in self.kernel_traces]),
            "spectral_gap"      : np.array([t.spectral_gap       for t in self.kernel_traces]),
            "sign_changes"      : np.array([t.sign_changes       for t in self.kernel_traces]),
        }

    def print_transition_summary(self) -> None:
        """Print a human-readable summary of Ω² transitions and kernel state."""
        logs = self.omega2_logs
        traces = self.kernel_traces
        n_transitions = sum(1 for e in logs if e.transition)
        n_near        = sum(1 for e in logs if e.near_boundary)
        print(f"Ω² Transition Summary")
        print(f"  Total recorded steps : {len(logs)}")
        print(f"  Sign transitions     : {n_transitions}")
        print(f"  Near-boundary steps  : {n_near}")
        if n_transitions:
            print(f"  Transition times     : {self.transition_times()}")
        else:
            print(f"  System stayed {'Riemannian (+)' if logs[-1].sign_positive else 'Lorentzian (-)'} throughout")
        if traces:
            ratios = [t.entanglement_ratio for t in traces]
            print(f"\nKernel Entanglement Curvature Summary")
            print(f"  Kernel snapshots     : {len(traces)}")
            print(f"  Ratio range          : [{min(ratios):.4f}, {max(ratios):.4f}]")
            print(f"  Mean ratio           : {np.mean(ratios):.4f}")
            final = traces[-1]
            regime = (
                "entangled" if final.entanglement_ratio > 0.5
                else "weakly-coupled" if final.entanglement_ratio > 0.1
                else "separable"
            )
            print(f"  Final kernel state   : {regime} (ratio={final.entanglement_ratio:.4f})")


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
    Run the full closed-loop co-evolution pipeline with Ω² and kernel diagnostics.

    Parameters
    ----------
    S0          : SiliconState — initial silicon state (default: make_state())
    config      : PipelineConfig — run configuration (default: PipelineConfig())
    initial_psi : np.ndarray — initial geometry field ψ(x); defaults to Gaussian

    Returns
    -------
    PipelineResult — full trajectory including Ω² logs and kernel curvature traces
    """
    if config is None:
        config = PipelineConfig()
    if S0 is None:
        S0 = make_state()

    rng = np.random.default_rng(config.seed)

    x = np.linspace(config.x_range[0], config.x_range[1], config.N_spatial)

    if initial_psi is None:
        psi = np.exp(-x ** 2)
    else:
        psi = initial_psi.copy()

    phi = field_from_state(S0, x)
    S   = S0.copy()

    result = PipelineResult(config=config, x=x)

    # Track previous Ω² sign for transition detection
    prev_sign_positive: bool | None = None
    # Track how many recorded steps since last kernel trace
    recorded_count = 0

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
        atlas = classify_regime(S, psi=psi, field=phi, alpha=config.omega2_alpha)

        # ── Record ────────────────────────────────────────────────────────────
        if step % config.record_every == 0:
            result.times.append(t)
            result.states.append(S.vec.copy())
            result.psi_fields.append(psi.copy())
            result.phi_fields.append(phi.copy())
            result.y_fields.append(y.copy())
            result.regimes.append(atlas)

            # 8. Ω² sign log — every recorded step
            omega2 = _compute_omega2(psi, alpha=config.omega2_alpha)
            o2_log = log_omega2(omega2, time=t, prev_sign_positive=prev_sign_positive)
            result.omega2_logs.append(o2_log)
            prev_sign_positive = o2_log.sign_positive

            # 9. Kernel curvature trace — every kernel_trace_every recorded steps
            if (config.kernel_trace_every > 0
                    and recorded_count % config.kernel_trace_every == 0):
                trace = trace_kernel_curvature(W, time=t)
                result.kernel_traces.append(trace)

            recorded_count += 1

    return result
