"""Seed-expansion influence matrix: SEED-1..5. Stdlib only.

Settles the arithmetic in ``seed_physics.md`` and ``lattice/seed_expansion.py``
/ ``lattice/expansion_8d.py``.

SEED-1 -- THE INFLUENCE MATRIX IS THE IDENTITY
----------------------------------------------
``W_ij = max(0, u_i . u_j)`` evaluated on the axis directions ``+-e_k``:

    u_i . u_i      = +1  ->  1
    u_i . u_(-i)   = -1  ->  max(0, -1) = 0
    u_i . u_j orth =  0  ->  0

So W is exactly the identity, in 3D (6 directions) and in 8D (16 directions)
alike. Nothing follows from the geometry, because no direction influences any
other and the 6 or 16 channels are independent scalars.

SEED-2 -- SO "STRUCTURE PRESERVATION" IS A TAUTOLOGY
----------------------------------------------------
With ``W = I`` every channel is multiplied by the same radial envelope
``f(r)``, so ``S_i / sum(S)`` is invariant by construction, for **any** sigma.
Three consequences:

* "Structure preservation: exact, 1e-16" is IEEE-754 round-off on the map
  ``x -> c*x``. It is a property of binary floating point, not of the expansion.
* The proportional-sigma insight -- real as a design idea -- cannot bite here.
  It would only matter if channels had *different* radial profiles. They do not.
* "Verified under dynamic physics ``W' = W + alpha*T``" was measured on the
  Euclidean identity, because ``get_phi_torsion_tensor()`` is a stub whose body
  is ``pass``, so it returns ``None``.

SEED-5 -- AND THE PROPOSED FIX IS NECESSARY BUT NOT SUFFICIENT
--------------------------------------------------------------
Not in the audit. The recommended repair is to use the eight cube-corner
directions ``(+-1,+-1,+-1)/sqrt(3)``, where ``max(0, u_i.u_j)`` becomes a real
matrix with entries {1, 1/3, 0}. That much is right and worth doing -- the
channels genuinely couple.

But it does not restore falsifiability on its own. **Every row of the
cube-corner matrix sums to exactly 2.0**, so under a single shared radial
envelope

    S_i = sum_j W_ij f(r) = (row sum) * f(r) = 2 f(r)   for every i

and the proportions are *still* invariant. This holds for any
vertex-transitive direction set, because transitivity forces equal row sums.
The tautology survives the fix.

What actually breaks it is a **direction-dependent radial profile**
``f_i(r)`` -- or a direction set that is not vertex-transitive, so the row sums
differ. ``row_sums_equal()`` and ``proportions_invariant()`` test exactly this,
and a "we fixed W and still get 1e-16" result should be read as the tautology
persisting rather than as validation.

SEED-3 -- THE PRECISION CLAIM CONTRADICTS THE ENCODING
------------------------------------------------------
Five 8-bit values give a quantisation step of 1/256 = 3.9e-3, against a claimed
fidelity of 1e-16: **13.6 orders apart**. The forward map's numerical precision
is being reported as the compression fidelity. The actual seed resolution is
1/256.

SEED-4 -- OPTIMISER RECOVERY IS NOT A BIJECTIVITY PROOF
-------------------------------------------------------
Recovering the original by L-BFGS-B or differential evolution on sampled seeds
shows that an optimiser found the answer for the seeds tested. Injectivity needs
a proof or an adversarial search; Dirichlet sampling plus pairwise collision
detection is neither. And under ``W = I`` the map is trivially injective on
proportions, which is not a finding either.

WHAT SURVIVES, AND IT IS WORTH KEEPING
--------------------------------------
The proportional-sigma insight is a real design idea once the channels differ.
"Pause anywhere, resume without loss" is a legitimate goal. And the scoping is
unusually honest for this set: "not a general-purpose compression algorithm --
it encodes structure", and "not optimized, production-ready, or battle-tested".
"""

from __future__ import annotations

import itertools
import math
from typing import Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "axis_directions", "cube_corner_directions", "influence_matrix",
    "is_identity", "row_sums", "row_sums_equal", "max_offdiagonal",
    "channel_response", "proportions", "proportions_invariant",
    "quantisation_step", "precision_gap_orders", "main",
]


# ---------------------------------------------------------------------------
# Direction sets
# ---------------------------------------------------------------------------

def axis_directions(dim: int = 3) -> List[Tuple[float, ...]]:
    """The ``2*dim`` signed axis directions ``+-e_k``. What the code uses."""
    if dim < 1:
        raise ValueError("dimension must be at least 1")
    out = []
    for k in range(dim):
        for sign in (1.0, -1.0):
            v = [0.0] * dim
            v[k] = sign
            out.append(tuple(v))
    return out


def cube_corner_directions() -> List[Tuple[float, float, float]]:
    """The eight ``(+-1,+-1,+-1)/sqrt(3)`` directions. The proposed fix."""
    r3 = math.sqrt(3.0)
    return [tuple(c / r3 for c in p) for p in itertools.product((1, -1), repeat=3)]


# ---------------------------------------------------------------------------
# SEED-1: the matrix
# ---------------------------------------------------------------------------

def influence_matrix(dirs: Sequence[Sequence[float]]) -> List[List[float]]:
    """``W_ij = max(0, u_i . u_j)``."""
    if not dirs:
        raise ValueError("need at least one direction")
    return [[max(0.0, sum(a * b for a, b in zip(u, v))) for v in dirs]
            for u in dirs]


def is_identity(w: Sequence[Sequence[float]], tol: float = 1e-12) -> bool:
    n = len(w)
    return all(abs(w[i][j] - (1.0 if i == j else 0.0)) <= tol
               for i in range(n) for j in range(n))


def max_offdiagonal(w: Sequence[Sequence[float]]) -> float:
    n = len(w)
    off = [abs(w[i][j]) for i in range(n) for j in range(n) if i != j]
    return max(off) if off else 0.0


def row_sums(w: Sequence[Sequence[float]]) -> List[float]:
    return [sum(row) for row in w]


def row_sums_equal(w: Sequence[Sequence[float]], tol: float = 1e-12) -> bool:
    """SEED-5: equal row sums are what keep the tautology alive.

    Any vertex-transitive direction set has them, so making W non-trivial is not
    enough to make structure preservation losable.
    """
    s = row_sums(w)
    return max(s) - min(s) <= tol


# ---------------------------------------------------------------------------
# SEED-2 / SEED-5: is structure preservation a result or a tautology?
# ---------------------------------------------------------------------------

def channel_response(w: Sequence[Sequence[float]], radius: float,
                     envelope: Optional[Callable[[float], float]] = None,
                     per_channel: Optional[Sequence[Callable[[float], float]]] = None
                     ) -> List[float]:
    """``S_i = sum_j W_ij f_j(r)``.

    ``envelope`` is the shared radial profile the code actually uses.
    ``per_channel`` supplies a different profile per direction, which is the
    thing that would make proportions losable.
    """
    n = len(w)
    if per_channel is not None:
        if len(per_channel) != n:
            raise ValueError("need one profile per direction")
        f = [per_channel[j](radius) for j in range(n)]
    else:
        g = envelope if envelope is not None else (lambda r: math.exp(-r * r))
        val = g(radius)
        f = [val] * n
    return [sum(w[i][j] * f[j] for j in range(n)) for i in range(n)]


def proportions(values: Sequence[float]) -> List[float]:
    total = sum(values)
    if total == 0.0:
        raise ValueError("cannot take proportions of an all-zero response")
    return [v / total for v in values]


def proportions_invariant(dirs: Sequence[Sequence[float]],
                          radii: Sequence[float] = (0.5, 1.0, 2.0, 4.0),
                          envelope: Optional[Callable[[float], float]] = None,
                          per_channel: Optional[Sequence[Callable]] = None,
                          tol: float = 1e-12) -> Dict[str, object]:
    """Do channel proportions change across shells?

    Under a shared envelope and equal row sums they cannot, which is why
    "structure preserved to 1e-16" is not a result. Supply ``per_channel``
    profiles and the answer becomes informative.
    """
    if len(radii) < 2:
        raise ValueError("need at least two radii to compare")
    w = influence_matrix(dirs)
    props = [proportions(channel_response(w, r, envelope, per_channel))
             for r in radii]
    worst = max(abs(props[k][i] - props[0][i])
                for k in range(1, len(props)) for i in range(len(props[0])))
    return {
        "n_directions": len(dirs),
        "identity": is_identity(w),
        "max_offdiagonal": max_offdiagonal(w),
        "row_sums": row_sums(w),
        "row_sums_equal": row_sums_equal(w),
        "worst_proportion_drift": worst,
        "invariant": worst <= tol,
        "tautological": row_sums_equal(w) and per_channel is None,
    }


# ---------------------------------------------------------------------------
# SEED-3
# ---------------------------------------------------------------------------

def quantisation_step(bits: int = 8) -> float:
    """``1 / 2**bits``. 3.9e-3 at 8 bits."""
    if bits < 1:
        raise ValueError("need at least one bit")
    return 1.0 / (1 << bits)


def precision_gap_orders(bits: int = 8, claimed_fidelity: float = 1e-16) -> float:
    """Orders of magnitude between the seed resolution and a claimed fidelity."""
    if claimed_fidelity <= 0.0:
        raise ValueError("fidelity must be positive")
    return math.log10(quantisation_step(bits) / claimed_fidelity)


# ---------------------------------------------------------------------------

def main() -> None:
    print("SEED-EXPANSION INFLUENCE MATRIX\n" + "=" * 68)

    print("\nSEED-1  W_ij = max(0, u_i . u_j) on the axis directions")
    for dim, label in ((3, "3D, 6 directions"), (8, "8D, 16 directions")):
        dirs = axis_directions(dim)
        w = influence_matrix(dirs)
        print(f"  {label:<20} n={len(dirs):2d}  "
              f"max off-diagonal = {max_offdiagonal(w):.1f}  "
              f"W == I ? {'YES' if is_identity(w) else 'no'}")
    print("\n  3D matrix:")
    for row in influence_matrix(axis_directions(3)):
        print("    " + " ".join(f"{v:.0f}" for v in row))
    print("\n  u_i.u_i = +1 -> 1 ; u_i.u_(-i) = -1 -> max(0,-1) = 0 ; orth -> 0")
    print("  => no direction influences any other; the channels are")
    print("     independent scalars.")

    print("\nSEED-2  so structure preservation is automatic")
    r = proportions_invariant(axis_directions(3))
    print(f"  proportions across shells: worst drift "
          f"{r['worst_proportion_drift']:.1e}, invariant = {r['invariant']}")
    print(f"  tautological = {r['tautological']}")
    print("  '1e-16' is IEEE-754 round-off on x -> c*x, not a property of the")
    print("  expansion. And the sigma insight cannot bite while channels share")
    print("  one radial envelope.")

    print("\nSEED-5  the proposed fix helps, but not enough")
    corners = cube_corner_directions()
    w = influence_matrix(corners)
    entries = sorted({round(v, 6) for row in w for v in row})
    print(f"  cube-corner W entries: {entries}   <- non-trivial, as recommended")
    print(f"  but every row sums to {sorted(set(round(s, 9) for s in row_sums(w)))}")
    rc = proportions_invariant(corners)
    print(f"  proportions across shells: worst drift "
          f"{rc['worst_proportion_drift']:.1e}, invariant = {rc['invariant']}")
    print("  vertex-transitivity forces equal row sums, so S_i = (row sum)*f(r)")
    print("  and proportions survive unchanged. The tautology survives the fix.")

    print("\n  what actually breaks it: direction-dependent radial profiles")
    profiles = [(lambda r, k=k: math.exp(-r * r * (1.0 + 0.35 * k)))
                for k in range(len(corners))]
    rp = proportions_invariant(corners, per_channel=profiles)
    print(f"  with per-channel f_i(r): worst drift "
          f"{rp['worst_proportion_drift']:.3f}, invariant = {rp['invariant']}")
    print("  now preservation is something you can lose -- which is what would")
    print("  make preserving it a result.")

    print("\nSEED-3  quantisation against the claimed fidelity")
    print(f"  5 x 8-bit values: step = {quantisation_step(8):.4e}")
    print(f"  claimed fidelity 1e-16 -> {precision_gap_orders():.1f} orders apart")
    print("  the forward map's numerical precision is being reported as the")
    print("  compression fidelity; the real seed resolution is 1/256.")

    print("\nSEED-4  recovery by optimiser is not a proof of injectivity")
    print("  and under W = I the map is trivially injective on proportions,")
    print("  which is not a finding either.")


if __name__ == "__main__":
    main()
