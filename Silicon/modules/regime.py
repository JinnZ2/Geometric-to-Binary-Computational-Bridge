"""
regime.py — Regime Atlas and Phase Classifier
==============================================
Implements the REGIME ATLAS described in To-Do-alternate.md (compressed alternate
section), mapping the silicon state and field to one of five dynamical regimes.

The 4-axis manifold S = (Λ, d, σ, χ) is derived from the silicon state:

  Λ (coupling strength)  : derived from κ norms and field statistics
  d (effective dimension): derived from feature length ℓ
  σ (signature)          : derived from Ω²(x) = 1 + α·ψ(x)²
  χ (topology)           : derived from field winding / compactness proxy

The sole hard phase boundary is Ω² = 0.

Five regimes
------------
  A. Linear / Quantum-like  — Λ ≪ 1, Ω² > 0, d < 4
  B. Solitonic              — Λ ~ O(1), bounded Ω² > 0
  C. Chaotic / Turbulent    — Λ ≫ 1, strong W coupling
  D. Topological            — χ < 0 or non-compact embedding
  E. Signature Transition   — Ω² ≈ 0  (only non-reversible boundary)

The classifier returns both a discrete label and continuous regime weights,
replacing hard if/else switching with a probability distribution over regimes
(per To-Do-alternate.md §5.3 extension).

Attractor taxonomy
------------------
  QM attractor      : low Λ, stable Ω² > 0
  Soliton attractor : intermediate Λ, localised stability
  Lorentzian basin  : high coupling + Ω² < 0 instability
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np
from .state import SiliconState

# ── Regime labels ─────────────────────────────────────────────────────────────
REGIME_LINEAR      = "A_linear_quantum"
REGIME_SOLITONIC   = "B_solitonic"
REGIME_CHAOTIC     = "C_chaotic_turbulent"
REGIME_TOPOLOGICAL = "D_topological"
REGIME_TRANSITION  = "E_signature_transition"

ALL_REGIMES = [
    REGIME_LINEAR,
    REGIME_SOLITONIC,
    REGIME_CHAOTIC,
    REGIME_TOPOLOGICAL,
    REGIME_TRANSITION,
]

# ── Omega² threshold for signature transition ─────────────────────────────────
OMEGA2_TRANSITION_TOL = 0.05   # |Ω²| < this → transition regime


@dataclass
class RegimeAtlas:
    """
    Container for the derived 4-axis manifold coordinates and regime outputs.

    Attributes
    ----------
    Lambda_   : float — coupling strength Λ
    d_eff     : float — effective dimension d
    sigma     : float — signature proxy (mean Ω²)
    chi       : float — topology proxy (field compactness)
    omega2    : np.ndarray — Ω²(x) field
    label     : str   — dominant regime label
    weights   : dict[str, float] — continuous regime weights (sum to 1)
    attractor : str   — nearest attractor basin
    """
    Lambda_  : float
    d_eff    : float
    sigma    : float
    chi      : float
    omega2   : np.ndarray
    label    : str
    weights  : dict[str, float]
    attractor: str

    def __repr__(self) -> str:
        w_str = ", ".join(f"{k.split('_')[0]}={v:.3f}" for k, v in self.weights.items())
        return (
            f"RegimeAtlas(Λ={self.Lambda_:.3f}, d={self.d_eff:.2f}, "
            f"σ={self.sigma:.3f}, χ={self.chi:.3f})\n"
            f"  label={self.label}  attractor={self.attractor}\n"
            f"  weights=[{w_str}]"
        )


def _compute_lambda(S: SiliconState, field: np.ndarray | None = None) -> float:
    """
    Coupling strength Λ: norm of κ vector, optionally boosted by field variance.
    """
    kappa = S.kappa
    lam   = float(np.linalg.norm(kappa))
    if field is not None:
        lam += float(field.var())
    return lam


def _compute_d_eff(S: SiliconState) -> float:
    """
    Effective dimension d: maps feature length ℓ to a dimensionality proxy.
    ℓ ≤ 1 nm → d ~ 1 (quantum wire), ℓ ~ 3 nm → d ~ 3, ℓ ≥ 10 nm → d ~ 4+
    """
    l = S.l
    return float(np.clip(np.log2(max(l, 0.5) + 1.0), 0.5, 6.0))


def _compute_omega2(psi: np.ndarray, alpha: float = 1.0) -> np.ndarray:
    """
    Gate function Ω²(x) = 1 + α·ψ(x)².
    Ω² > 0 → Riemannian / stable
    Ω² = 0 → degenerate boundary
    Ω² < 0 → Lorentzian / instability (requires α < 0 or modified ψ)
    """
    return 1.0 + alpha * psi ** 2


def _compute_chi(field: np.ndarray) -> float:
    """
    Topology proxy χ: negative if field has strong winding / non-compact structure.
    Approximated as negative of the normalised field range.
    """
    if field is None or len(field) == 0:
        return 0.0
    span = float(field.max() - field.min())
    mean = float(np.abs(field.mean())) + 1e-9
    return -span / mean   # negative → non-compact / open topology


def _regime_weights(
    Lambda_: float,
    d_eff: float,
    sigma: float,
    chi: float,
    omega2_mean: float,
) -> dict[str, float]:
    """
    Compute continuous regime weights as soft scores over the 5 regimes.
    Weights are normalised to sum to 1.
    """
    scores: dict[str, float] = {}

    # A: Linear / Quantum-like
    scores[REGIME_LINEAR] = (
        np.exp(-Lambda_)
        * float(omega2_mean > 0)
        * np.exp(-max(d_eff - 4.0, 0.0))
    )

    # B: Solitonic
    scores[REGIME_SOLITONIC] = (
        np.exp(-(Lambda_ - 1.0) ** 2)
        * float(omega2_mean > 0)
    )

    # C: Chaotic / Turbulent
    scores[REGIME_CHAOTIC] = (
        (1.0 - np.exp(-Lambda_ + 1.0)) * float(Lambda_ > 1.0)
    )

    # D: Topological
    scores[REGIME_TOPOLOGICAL] = (
        np.exp(chi)  # chi < 0 → large weight
    )

    # E: Signature Transition
    scores[REGIME_TRANSITION] = (
        np.exp(-abs(omega2_mean) / OMEGA2_TRANSITION_TOL)
    )

    # Normalise
    total = sum(scores.values()) + 1e-12
    return {k: v / total for k, v in scores.items()}


def _attractor(Lambda_: float, omega2_mean: float) -> str:
    if omega2_mean < 0:
        return "Lorentzian_basin"
    elif Lambda_ < 0.5:
        return "QM_attractor"
    elif Lambda_ < 2.0:
        return "Soliton_attractor"
    else:
        return "Lorentzian_basin"


def classify_regime(
    S: SiliconState,
    psi: np.ndarray | None = None,
    field: np.ndarray | None = None,
    alpha: float = 1.0,
) -> RegimeAtlas:
    """
    Classify the current silicon state into the regime atlas.

    Parameters
    ----------
    S     : SiliconState
    psi   : np.ndarray, shape (N,) — state field ψ(x); defaults to zeros
    field : np.ndarray, shape (N,) — geometry field φ(x); used for Λ and χ
    alpha : float — coefficient in Ω²(x) = 1 + α·ψ²

    Returns
    -------
    RegimeAtlas
    """
    if psi is None:
        psi = np.zeros(32)
    if field is None:
        field = np.zeros_like(psi)

    Lambda_     = _compute_lambda(S, field)
    d_eff       = _compute_d_eff(S)
    omega2      = _compute_omega2(psi, alpha)
    omega2_mean = float(omega2.mean())
    sigma       = omega2_mean
    chi         = _compute_chi(field)

    weights = _regime_weights(Lambda_, d_eff, sigma, chi, omega2_mean)
    label   = max(weights, key=weights.__getitem__)
    att     = _attractor(Lambda_, omega2_mean)

    return RegimeAtlas(
        Lambda_  = Lambda_,
        d_eff    = d_eff,
        sigma    = sigma,
        chi      = chi,
        omega2   = omega2,
        label    = label,
        weights  = weights,
        attractor= att,
    )
