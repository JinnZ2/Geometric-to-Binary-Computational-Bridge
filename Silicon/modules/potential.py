"""
potential.py — Effective Potential on the Silicon State Manifold
================================================================
Defines V(S) — the fabrication + stability constraint potential — and its
gradient, used by both the deterministic and stochastic geodesic integrators.

Physical interpretation
-----------------------
Each term in V penalises deviation from a physically meaningful target:

  V_n     : carrier density toward N_REF (stable doping regime)
  V_μ     : mobility toward MU_REF (undegraded transport)
  V_T     : temperature toward T_REF (room temperature stability)
  V_dbulk : bulk defect density toward zero (clean crystal)
  V_diface: interface defect density toward zero
  V_ℓ     : feature length toward L_REF (design target)
  V_κ     : coupling modes toward K_REF (target operating point)

The potential is smooth everywhere, but hard constraint reflection is handled
separately in SiliconState.enforce_constraints().

Gradient
--------
Computed via central finite differences for generality; analytic expressions
are available for each term but the numerical approach keeps the module
independent of metric changes.
"""

from __future__ import annotations
import numpy as np
from .state import SiliconState, DIM, N_REF, MU_REF, T_REF, L_REF, K_REF

# ── Potential weights (tune to adjust basin shapes) ───────────────────────────
W_POT_N     = 1.0 / 1e34   # normalised so V_n ~ O(1) near N_REF
W_POT_MU    = 1.0 / (MU_REF ** 2)
W_POT_T     = 1.0 / (T_REF ** 2)
W_POT_D     = 1.0           # defect penalty weight
W_POT_L     = 1.0
W_POT_K     = 1.0

# Gradient step
_EPS = 1e-6


def potential(S: SiliconState) -> float:
    """
    Compute the effective potential V(S).

    Returns
    -------
    float
        Scalar potential value; lower = more physically stable state.
    """
    v = S.vec
    n, mu, T        = v[0], v[1], v[2]
    d_bulk, d_iface = v[3], v[4]
    l               = v[5]
    kappa           = v[6:9]

    V_n      = W_POT_N  * (n   - N_REF)  ** 2
    V_mu     = W_POT_MU * (mu  - MU_REF) ** 2
    V_T      = W_POT_T  * (T   - T_REF)  ** 2
    V_dbulk  = W_POT_D  * d_bulk  ** 2
    V_diface = W_POT_D  * d_iface ** 2
    V_l      = W_POT_L  * (l - L_REF)   ** 2
    V_kappa  = W_POT_K  * float(np.sum((kappa - K_REF) ** 2))

    return float(V_n + V_mu + V_T + V_dbulk + V_diface + V_l + V_kappa)


def grad_potential(S: SiliconState) -> np.ndarray:
    """
    Compute the gradient ∂V/∂S^a via central finite differences.

    Returns
    -------
    grad : np.ndarray, shape (9,)
    """
    grad = np.zeros(DIM)
    for i in range(DIM):
        dvec_p = S.vec.copy(); dvec_p[i] += _EPS
        dvec_m = S.vec.copy(); dvec_m[i] -= _EPS
        Sp = SiliconState(vec=dvec_p, vel=S.vel)
        Sm = SiliconState(vec=dvec_m, vel=S.vel)
        grad[i] = (potential(Sp) - potential(Sm)) / (2.0 * _EPS)
    return grad
