"""
metric.py — Riemannian Metric on the Silicon State Manifold
============================================================
Implements the non-Euclidean metric g_ab(S) described in To-Do-alternate.md §1
(stochastic geodesic section), with the fabrication-grounded extensions from §5.

Metric structure
----------------
The metric encodes physical sensitivity of each coordinate axis:

  g_nn   = w_n / n²          — log-like scaling; doping changes are cheap at
                                high density, expensive at low density
  g_μμ   = w_μ / μ           — mobility: moderate sensitivity
  g_TT   = w_T               — temperature: uniform (Euclidean)
  g_dd   = w_d               — defect axes: Euclidean (piecewise real)
  g_ℓℓ   = w_ℓ               — feature length: Euclidean
  g_κκ   = W_κ (3×3 block)   — coupling modes: dense sub-block allowing
                                inter-mode curvature (entanglement analogy)

Off-diagonal extension (fabrication-grounded, §5.2)
----------------------------------------------------
A single off-diagonal term g_{d_bulk, κ₁} ≠ 0 is introduced to create real
curvature coupling and path dependence matching the entanglement curvature
analogy from the prior simulations.

Christoffel symbols
-------------------
Only the dominant nonzero terms are computed analytically; the rest are
approximated as zero for tractability (per To-Do-alternate.md §2).

  Γⁿ_nn  = -1/n   (from 1/n² metric term)
  Γ^μ_μμ = -1/(2μ) (from 1/μ metric term)

All other symbols are zero under the diagonal + one off-diagonal approximation.
"""

from __future__ import annotations
import numpy as np
from .state import SiliconState, DIM, IDX_N, IDX_MU, IDX_DBULK, IDX_K1

# ── Default metric weights ────────────────────────────────────────────────────
W_N     = 1.0
W_MU    = 1.0
W_T     = 1.0
W_D     = 1.0
W_L     = 1.0
W_KAPPA = np.eye(3)  # 3×3 block; can be made dense for coupling

# Off-diagonal coupling strength (g_{d_bulk, κ₁})
G_DK_COUPLING = 0.15   # non-zero → real curvature coupling


def metric_tensor(S: SiliconState) -> np.ndarray:
    """
    Compute the 9×9 metric tensor g_ab(S).

    Parameters
    ----------
    S : SiliconState

    Returns
    -------
    g : np.ndarray, shape (9, 9)
        Symmetric positive-definite metric matrix.
    """
    n  = max(S.vec[IDX_N],  1e10)
    mu = max(S.vec[IDX_MU], 1.0)

    g = np.zeros((DIM, DIM))

    # Diagonal blocks
    g[0, 0] = W_N  / (n ** 2)          # n
    g[1, 1] = W_MU / mu                # μ
    g[2, 2] = W_T                      # T
    g[3, 3] = W_D                      # d_bulk
    g[4, 4] = W_D                      # d_iface
    g[5, 5] = W_L                      # ℓ

    # κ block (3×3)
    g[6:9, 6:9] = W_KAPPA

    # Off-diagonal coupling: g_{d_bulk, κ₁} and its transpose
    g[IDX_DBULK, IDX_K1] = G_DK_COUPLING
    g[IDX_K1, IDX_DBULK] = G_DK_COUPLING

    return g


def metric_inverse(S: SiliconState) -> np.ndarray:
    """
    Compute the inverse metric g^ab(S) = g_ab⁻¹.

    Uses numpy.linalg.inv; for the mostly-diagonal structure this is fast
    and numerically stable.

    Returns
    -------
    g_inv : np.ndarray, shape (9, 9)
    """
    g = metric_tensor(S)
    return np.linalg.inv(g)


def christoffel_symbols(S: SiliconState) -> dict[tuple[int, int, int], float]:
    """
    Return the nonzero Christoffel symbols Γ^a_bc for the metric g_ab(S).

    Only analytically dominant terms are included:
      Γⁿ_nn  = -1/n
      Γ^μ_μμ = -1/(2μ)

    Returns
    -------
    Gamma : dict mapping (a, b, c) → float
        Sparse representation; missing entries are zero.
    """
    n  = max(S.vec[IDX_N],  1e10)
    mu = max(S.vec[IDX_MU], 1.0)

    Gamma: dict[tuple[int, int, int], float] = {}

    # Γⁿ_nn = -1/n  (from ∂_n g_nn = -2 w_n / n³)
    Gamma[(0, 0, 0)] = -1.0 / n

    # Γ^μ_μμ = -1/(2μ)  (from ∂_μ g_μμ = -w_μ / μ²)
    Gamma[(1, 1, 1)] = -1.0 / (2.0 * mu)

    return Gamma
