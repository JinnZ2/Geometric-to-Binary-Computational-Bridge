"""
coupling.py — Geometry Field ↔ Silicon State Coupling
======================================================
Implements the bidirectional coupling between the external geometry field φ(x)
and the silicon state S, as described in To-Do-alternate.md §4 and §5.

Two coupling modes are provided:

1. geometry_force(field) → np.ndarray, shape (9,)
   ------------------------------------------------
   Computes a force vector in state space derived from field statistics:
     mean_f  → drives carrier density n and thermal coupling κ₃
     var_f   → drives defect densities and optical coupling κ₂
     grad_f  → drives feature length ℓ and electrical coupling κ₁

   This is the "external injection" model from To-Do-alternate.md §4.
   It is fast and interpretable but one-directional (φ → S only).

2. update_with_geometry(S, field, dt) → SiliconState
   ---------------------------------------------------
   Applies geometry_force as an additive update to the state vector,
   scaled by dt.  Constraints are enforced after application.

3. field_from_state(S, x) → np.ndarray
   -------------------------------------
   Generates a scalar geometry field proxy from the silicon state,
   enabling the S → φ feedback direction (bidirectionality).
   This closes the loop: geometry → silicon → computation → geometry.

Notes on bidirectionality (To-Do-alternate.md §2.D)
----------------------------------------------------
The document flags that the original system is not fully bidirectional:
geometry influences silicon but silicon does not reshape geometry except
indirectly.  field_from_state() addresses this by allowing S to modulate
the field, which can then be fed back into the next geometry evolution step.
"""

from __future__ import annotations
import numpy as np
from .state import SiliconState, DIM, IDX_N, IDX_MU, IDX_T, IDX_DBULK, IDX_DIFACE, IDX_L, IDX_K1, IDX_K2, IDX_K3


def geometry_force(field: np.ndarray) -> np.ndarray:
    """
    Compute the force vector exerted on the silicon state by the geometry field.

    Parameters
    ----------
    field : np.ndarray, shape (N,)
        Discretised geometry field φ(x) over N spatial points.

    Returns
    -------
    force : np.ndarray, shape (9,)
        Force contribution to each state coordinate.
    """
    mean_f = float(field.mean())
    var_f  = float(field.var())
    grad_f = float(np.mean(np.abs(np.gradient(field))))

    force = np.zeros(DIM)

    # Carrier density: driven by mean field (doping analogy)
    force[IDX_N]     = 1e15 * mean_f

    # Mobility: reduced by field variance (scattering analogy)
    force[IDX_MU]    = -50.0 * var_f

    # Temperature: driven by mean field squared (Joule heating analogy)
    force[IDX_T]     = 10.0 * mean_f ** 2

    # Bulk defects: driven by field variance (disorder analogy)
    force[IDX_DBULK]  = 0.01 * var_f

    # Interface defects: driven by gradient magnitude (surface roughness analogy)
    force[IDX_DIFACE] = 0.005 * grad_f

    # Feature length: compressed by field curvature
    force[IDX_L]     = -0.01 * grad_f

    # Coupling modes
    force[IDX_K1]    = 0.01 * grad_f   # electrical: driven by field gradient
    force[IDX_K2]    = 0.01 * var_f    # optical: driven by variance
    force[IDX_K3]    = 0.01 * mean_f ** 2  # thermal: driven by mean²

    return force


def update_with_geometry(
    S: SiliconState,
    field: np.ndarray,
    dt: float = 0.01,
    enforce: bool = True,
) -> SiliconState:
    """
    Apply geometry field force to the silicon state for one time step.

    Parameters
    ----------
    S       : SiliconState
    field   : np.ndarray — geometry field φ(x)
    dt      : float      — time step scaling for the force
    enforce : bool       — apply hard constraint reflection after update

    Returns
    -------
    SiliconState — updated state
    """
    force   = geometry_force(field)
    new_vec = S.vec + dt * force
    S_new   = SiliconState(vec=new_vec, vel=S.vel.copy())
    if enforce:
        S_new = S_new.enforce_constraints()
    return S_new


def field_from_state(S: SiliconState, x: np.ndarray) -> np.ndarray:
    """
    Generate a geometry field proxy from the silicon state.

    This implements the S → φ feedback direction, enabling true bidirectionality.
    The field is constructed as a superposition of Gaussian modes modulated by
    the silicon state parameters.

    Parameters
    ----------
    S : SiliconState
    x : np.ndarray, shape (N,) — spatial coordinate array

    Returns
    -------
    phi : np.ndarray, shape (N,) — generated geometry field
    """
    n_norm  = S.n  / 1e17          # normalised carrier density
    d_total = S.d                  # combined defect scalar
    l       = S.l                  # feature length (nm)
    kappa   = S.kappa              # coupling modes

    # Carrier density: broad Gaussian envelope
    phi = n_norm * np.exp(-x ** 2 / (2.0 * max(l, 0.5) ** 2))

    # Defect contribution: random-phase modulation (disorder)
    phi += d_total * np.sin(2.0 * np.pi * x / max(l, 0.5))

    # Coupling mode contributions: interference-like oscillations
    for i, k in enumerate(kappa):
        freq = (i + 1) * 2.0 * np.pi / max(l, 0.5)
        phi += 0.1 * k * np.cos(freq * x)

    return phi
