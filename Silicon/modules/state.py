"""
state.py — Silicon State Vector
================================
Defines the silicon state manifold coordinate S = (n, μ, T, d_bulk, d_iface, ℓ, κ₁, κ₂, κ₃).

Fabrication-grounded expansion (per To-Do-alternate.md §5):
  - n  : carrier density          [cm⁻³]   — doping axis
  - μ  : carrier mobility         [cm²/Vs] — transport axis (split from n)
  - T  : lattice temperature      [K]       — thermal axis (split from n)
  - d_bulk  : bulk defect density [0–1]     — volume trap density
  - d_iface : interface defect    [0–1]     — surface/interface trap density
  - ℓ  : effective feature length [nm]      — confinement / lithography axis
  - κ₁ : electrical coupling mode [a.u.]
  - κ₂ : optical coupling mode    [a.u.]
  - κ₃ : thermal coupling mode    [a.u.]

The state vector is stored as a flat numpy array of length 9 for compatibility
with the metric and dynamics modules.  Named accessors are provided for clarity.

Index map
---------
  0: n      1: μ      2: T
  3: d_bulk 4: d_iface
  5: ℓ
  6: κ₁     7: κ₂     8: κ₃
"""

from __future__ import annotations
import numpy as np
from dataclasses import dataclass, field

# ── Physical reference values (fabrication defaults) ─────────────────────────
N_REF   = 1e17   # cm⁻³  — moderate n-type doping
MU_REF  = 1400.0 # cm²/Vs — intrinsic electron mobility in Si
T_REF   = 300.0  # K      — room temperature
L_REF   = 3.0    # nm     — representative feature length
K_REF   = np.array([1.0, 0.5, 0.3])  # coupling mode targets

DIM = 9  # total state-vector dimension

# ── Index constants ───────────────────────────────────────────────────────────
IDX_N      = 0
IDX_MU     = 1
IDX_T      = 2
IDX_DBULK  = 3
IDX_DIFACE = 4
IDX_L      = 5
IDX_K1     = 6
IDX_K2     = 7
IDX_K3     = 8


@dataclass
class SiliconState:
    """
    Full silicon state on the 9D manifold.

    Parameters
    ----------
    vec : np.ndarray, shape (9,)
        State coordinate vector [n, μ, T, d_bulk, d_iface, ℓ, κ₁, κ₂, κ₃].
    vel : np.ndarray, shape (9,)
        Velocity in state space (used by second-order stochastic integrator).
    """

    vec: np.ndarray = field(default_factory=lambda: _default_vec())
    vel: np.ndarray = field(default_factory=lambda: np.zeros(DIM))

    # ── Named property accessors ──────────────────────────────────────────────
    @property
    def n(self) -> float:
        return float(self.vec[IDX_N])

    @property
    def mu(self) -> float:
        return float(self.vec[IDX_MU])

    @property
    def T(self) -> float:
        return float(self.vec[IDX_T])

    @property
    def d_bulk(self) -> float:
        return float(self.vec[IDX_DBULK])

    @property
    def d_iface(self) -> float:
        return float(self.vec[IDX_DIFACE])

    @property
    def d(self) -> float:
        """Combined defect scalar (mean of bulk and interface)."""
        return 0.5 * (self.d_bulk + self.d_iface)

    @property
    def l(self) -> float:
        return float(self.vec[IDX_L])

    @property
    def kappa(self) -> np.ndarray:
        return self.vec[IDX_K1:IDX_K3 + 1].copy()

    # ── Constraint enforcement ────────────────────────────────────────────────
    def enforce_constraints(self) -> "SiliconState":
        """
        Reflect state back to physical domain at hard constraint surfaces.

        Constraints (from To-Do-alternate.md §5.4):
          n > 0, μ > 0, T > 0
          d_bulk ∈ [0, 1], d_iface ∈ [0, 1]
          ℓ ∈ [0.5, 100] nm  (lithography bounds)
          κᵢ ∈ [0, 10]
        """
        v = self.vec.copy()
        # Carrier density / mobility / temperature: must be positive
        v[IDX_N]     = max(v[IDX_N],     1e10)
        v[IDX_MU]    = max(v[IDX_MU],    1.0)
        v[IDX_T]     = max(v[IDX_T],     1.0)
        # Defect densities: [0, 1]
        v[IDX_DBULK]  = float(np.clip(v[IDX_DBULK],  0.0, 1.0))
        v[IDX_DIFACE] = float(np.clip(v[IDX_DIFACE], 0.0, 1.0))
        # Feature length: lithography bounds
        v[IDX_L]     = float(np.clip(v[IDX_L], 0.5, 100.0))
        # Coupling modes: non-negative, bounded
        v[IDX_K1:IDX_K3 + 1] = np.clip(v[IDX_K1:IDX_K3 + 1], 0.0, 10.0)
        return SiliconState(vec=v, vel=self.vel.copy())

    def copy(self) -> "SiliconState":
        return SiliconState(vec=self.vec.copy(), vel=self.vel.copy())

    def __repr__(self) -> str:
        return (
            f"SiliconState("
            f"n={self.n:.3e}, μ={self.mu:.1f}, T={self.T:.1f}K, "
            f"d_bulk={self.d_bulk:.3f}, d_iface={self.d_iface:.3f}, "
            f"ℓ={self.l:.2f}nm, κ={self.kappa})"
        )


def _default_vec() -> np.ndarray:
    return np.array([
        N_REF,    # n
        MU_REF,   # μ
        T_REF,    # T
        0.05,     # d_bulk
        0.05,     # d_iface
        L_REF,    # ℓ
        K_REF[0], # κ₁
        K_REF[1], # κ₂
        K_REF[2], # κ₃
    ], dtype=float)


def make_state(
    n: float = N_REF,
    mu: float = MU_REF,
    T: float = T_REF,
    d_bulk: float = 0.05,
    d_iface: float = 0.05,
    l: float = L_REF,
    k1: float = 1.0,
    k2: float = 0.5,
    k3: float = 0.3,
) -> SiliconState:
    """
    Convenience constructor for SiliconState with named parameters.

    Returns
    -------
    SiliconState
        Initialised state with zero velocity.
    """
    vec = np.array([n, mu, T, d_bulk, d_iface, l, k1, k2, k3], dtype=float)
    return SiliconState(vec=vec, vel=np.zeros(DIM))
