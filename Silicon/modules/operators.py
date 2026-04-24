"""
operators.py — Continuous Operator Algebra
==========================================
Replaces the discrete graph → binary layer with a state-dependent operator
algebra, as described in To-Do-alternate.md §1–10 (continuous computation section).

The core idea: instead of
    S → regime → logic
we define
    y = O(S)
where O is a family of observables generated continuously from the silicon state.

Three levels of operator are implemented:

Level 1: Global matrix operator  W(S) ∈ ℝ^{m×m}
-------------------------------------------------
A weight matrix modulated by silicon state parameters.
Computation: y = tanh(W(S) · x)
No binary threshold required; digital behavior emerges when tanh saturates.

Level 2: Spatial kernel  W(x, x') ∈ ℝ^{N×N}
----------------------------------------------
A field-level operator coupling spatial points via a transport kernel G(x,x')
modulated by the geometry field φ(x) and silicon state S.
Computation: y(x) = tanh(∫ W(x,x') ψ(x') dx')

Level 3: Feedback update  S ← S + f(y)
----------------------------------------
Computation output y feeds back into the silicon state, closing the loop:
    geometry → silicon → computation → silicon
"""

from __future__ import annotations
import numpy as np
from .state import SiliconState, IDX_N, IDX_DBULK, IDX_DIFACE, IDX_L, IDX_K1, IDX_K2, IDX_K3


# ── Level 1: Global matrix operator ──────────────────────────────────────────

def silicon_operator(S: SiliconState, size: int = 8) -> np.ndarray:
    """
    Generate a continuous weight matrix W ∈ ℝ^{size×size} from silicon state.

    The matrix is modulated by:
      - n  : carrier scaling (amplitude)
      - d  : defect damping (exponential suppression)
      - ℓ  : dimensional sensitivity (inverse Lorentzian)
      - κ  : coupling modes (outer-product structure)

    Parameters
    ----------
    S    : SiliconState
    size : int — operator dimension

    Returns
    -------
    W : np.ndarray, shape (size, size)
    """
    n       = S.vec[IDX_N]
    d_bulk  = S.vec[IDX_DBULK]
    d_iface = S.vec[IDX_DIFACE]
    d       = 0.5 * (d_bulk + d_iface)
    l       = S.vec[IDX_L]
    kappa   = S.vec[IDX_K1:IDX_K3 + 1]

    # Base random-structure matrix (seeded by state for reproducibility)
    seed = int(abs(n) % (2**31))
    rng  = np.random.default_rng(seed)
    M    = rng.standard_normal((size, size))

    # Modulate by silicon state
    M *= (n / (1e17 + 1e-9))                    # carrier amplitude scaling
    M *= np.exp(-d)                              # defect damping
    M *= 1.0 / (1.0 + abs(l - 2.0))             # dimensional sensitivity

    # Coupling mode structure (outer product adds correlated off-diagonal terms)
    kappa_padded = np.zeros(size)
    kappa_padded[:min(3, size)] = kappa[:min(3, size)]
    M += np.outer(kappa_padded, kappa_padded)

    return M


def evaluate(S: SiliconState, x: np.ndarray) -> np.ndarray:
    """
    Compute the continuous output y = tanh(W(S) · x).

    Parameters
    ----------
    S : SiliconState
    x : np.ndarray, shape (m,) — input vector

    Returns
    -------
    y : np.ndarray, shape (m,)
    """
    W = silicon_operator(S, size=len(x))
    return np.tanh(W @ x)


# ── Level 2: Spatial kernel operator ─────────────────────────────────────────

def build_kernel(
    x: np.ndarray,
    phi: np.ndarray,
    S: SiliconState,
) -> np.ndarray:
    """
    Build the spatial kernel W(x, x') ∈ ℝ^{N×N}.

    Kernel structure (To-Do-alternate.md §2):
        W(x, x') = G(x, x'; S) · exp(-α |φ(x) - φ(x')|²)

    where G is a transport/Green-like term:
        G(x, x') = exp(-|x - x'|² / (ε + |n|))

    Modulated by:
      - defect damping: exp(-d)
      - coupling channels: 1 + 0.1 · Σκ

    Parameters
    ----------
    x   : np.ndarray, shape (N,) — spatial coordinate array
    phi : np.ndarray, shape (N,) — geometry field φ(x)
    S   : SiliconState

    Returns
    -------
    W : np.ndarray, shape (N, N)
    """
    N       = len(x)
    n       = max(S.vec[IDX_N], 1e10)
    d_bulk  = S.vec[IDX_DBULK]
    d_iface = S.vec[IDX_DIFACE]
    d       = 0.5 * (d_bulk + d_iface)
    kappa   = S.vec[IDX_K1:IDX_K3 + 1]

    damp     = np.exp(-d)
    coupling = 1.0 + 0.1 * float(np.sum(kappa))

    # Vectorised kernel construction
    xi = x[:, None]   # (N, 1)
    xj = x[None, :]   # (1, N)

    # Transport kernel: Green-like Gaussian
    G = np.exp(-(xi - xj) ** 2 / (1e-2 + abs(n) / 1e17))

    # Geometric coherence: suppresses coupling across field discontinuities
    phi_i = phi[:, None]
    phi_j = phi[None, :]
    geom  = np.exp(-0.5 * (phi_i - phi_j) ** 2)

    W = G * geom * damp * coupling
    return W


def evaluate_field(W: np.ndarray, psi: np.ndarray) -> np.ndarray:
    """
    Apply the spatial kernel to a state field ψ(x).

    y(x) = tanh(W · ψ)

    Parameters
    ----------
    W   : np.ndarray, shape (N, N) — spatial kernel
    psi : np.ndarray, shape (N,)   — state field ψ(x)

    Returns
    -------
    y : np.ndarray, shape (N,)
    """
    return np.tanh(W @ psi)


# ── Level 3: Feedback update ──────────────────────────────────────────────────

def feedback_update(
    S: SiliconState,
    y: np.ndarray,
    dt: float = 0.01,
    enforce: bool = True,
) -> SiliconState:
    """
    Feed computation output y back into the silicon state.

    This closes the loop: geometry → silicon → computation → silicon.

    Update rules (To-Do-alternate.md §4):
      n      += activity · dt    — carrier density increases with activity
      d_bulk += var(y) · dt      — defects from output fluctuation
      ℓ      -= activity · dt    — dimensional compression under load
      κ      += y[:3] · dt       — coupling modes adapt to output

    Parameters
    ----------
    S       : SiliconState
    y       : np.ndarray — computation output (vector or field)
    dt      : float
    enforce : bool

    Returns
    -------
    SiliconState — updated state
    """
    activity = float(np.mean(np.abs(y)))
    var_y    = float(np.var(y))

    new_vec = S.vec.copy()

    new_vec[IDX_N]     += 1e15 * activity * dt
    new_vec[IDX_DBULK] += var_y * dt
    new_vec[IDX_L]     -= activity * dt

    # Coupling modes adapt to first 3 output components (or mean if field)
    if len(y) >= 3:
        new_vec[IDX_K1:IDX_K3 + 1] += dt * y[:3]
    else:
        new_vec[IDX_K1:IDX_K3 + 1] += dt * activity

    S_new = SiliconState(vec=new_vec, vel=S.vel.copy())
    if enforce:
        S_new = S_new.enforce_constraints()
    return S_new
