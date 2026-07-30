"""Keating cluster, phi coupling, and the gate claims: KEA-1..7. Stdlib only.

Settles the arithmetic in ``VFF.md`` and ``lattice/vff_*.py``. The Keating
parameters are correct, which is rare in this set and worth saying first:
alpha = 3.00 eV/A^2 = 48.1 N/m against a standard 48.50, and beta = 0.75 eV/A^2
= 12.0 N/m against 13.81. The potential is implemented correctly too. What does
not follow is the state space built on it.

KEA-1 -- THERE IS ONE MINIMUM, NOT EIGHT
----------------------------------------
The Keating form is a sum of squares, so ``E >= 0`` everywhere and ``E = 0``
requires every bond at d0 AND every angle at arccos(-1/3) simultaneously. With
four clamped tetrahedral neighbours the only such point is the centre. 200
random starts up to |d| = 1.2 A find exactly one minimum, at the origin, with
E = 1.3e-13 eV. There is no room for eight secondary basins: the function grows
monotonically outward from a unique zero.

``VFF.md`` half-caught this itself and then took the wrong branch:

    "the ideal tetrahedron is actually a maximum when constrained? Actually,
     it's a minimum for an isolated cluster but a saddle point in a crystal.
     In our clamped-vertex model, it's a local minimum but surrounded by 8
     shallower minima corresponding to off-center positions."

In the clamped model it is a *global* minimum and there are no surrounding
minima. The 8-state encoding, both gates and the ALU sit on that parenthetical.

KEA-7 -- AND THE MODEL CANNOT TELL VERTEX FROM FACE, EXACTLY
------------------------------------------------------------
Not in the audit, and it is the structural version of KEA-1. The clamped energy
is **exactly even** in the central displacement:

    stretch:  r_k^2 - d0^2 = -2 v_k.p + p^2,  and  Sum_k v_k = 0 exactly,
              so the cross term 4 p^2 Sum_k(v_k.p) vanishes.
    bend:     v_k.v_l + d0^2/3 = 0 exactly, and Sum_{k<l}(v_k+v_l) = 3 Sum_k v_k
              = 0, so its cross term vanishes too.

Hence ``E(p) = E(-p)`` identically -- verified to 5.3e-15 over 3000 random
displacements. The model has an exact inversion symmetry about the centre, so
the four vertex-directed and four face-directed displacements are energetically
indistinguishable, not merely close.

That is the same collapse as ``GIES-1``, where ``outer(v, v) == outer(-v, -v)``
made states i and 7-i identical in every invariant -- reached here from a
completely different direction. Two independent representations of the same
8-state idea, both blind to the inversion that separates the two sublattices.
The honest state space is again 4 plus a sign that this model cannot see.

KEA-2 -- A STATIC SPRING IS RECIPROCAL, AND phi CANNOT CHANGE THAT
-----------------------------------------------------------------
``E_c = 0.5 k_c |d1 - d2|^2`` gives ``d2E/dd1 dd2 = -k_c = d2E/dd2 dd1``:
symmetric by construction. Reciprocity is a symmetry statement, not a phase
condition. Breaking it requires broken time-reversal symmetry, temporal
modulation, or nonlinearity. A static spring has none of the three, and the
golden ratio is a number, not a mechanism.

KEA-4 -- THE SYMMETRY GROUP REACHES 1/1680 OF THE GATE SET
----------------------------------------------------------
Half right: the proper rotation group O (24 elements) *is* isomorphic to S4, and
full Oh is S4 x Z2 (48). But reversible 3-bit gates are permutations of 8
states, S8 = 40320, so 24 elements reach at most 1/1680 of them. And most
Boolean functions on 3 bits are not permutations at all: there are 2^8 = 256
functions {0,1}^3 -> {0,1}, nearly all irreversible.

KEA-5 -- A QUADRATIC ENERGY GIVES A LINEAR RESPONSE, SO NO TOFFOLI
------------------------------------------------------------------
Minimising a quadratic form over the target coordinates gives
``d_target = -K_tt^-1 K_tc d_ctrl``, which is linear in the controls. Toffoli is
degree 2 in its controls -- it flips only if BOTH are set -- and a linear map
cannot compute AND. The nonlinearity would have to come from on-site wells, and
KEA-1 says those do not exist. Separately, ``phi^-2 / phi^0 / phi^1`` is one
point in a continuum of coupling triples and nothing in the document derives it.

KEA-6 -- TWO OF THE FIVE BRIDGES DIE ON SYMMETRY, AND TWO HAVE FIXES
--------------------------------------------------------------------
Si is centrosymmetric (Oh, m-3m), so every odd-rank tensor vanishes:

    harmonic (phonon strain)     REAL
    light "via inverse piezo"    DEAD -> use the deformation potential and
                                         photothermal stress, both real
    magnetic "via magnetostriction"  DEAD, Si is diamagnetic and
                                         magnetostriction is ~1e-10. Ninth
                                         magnetic-in-a-diamagnet instance
                                         across this set.
    electric "via piezo tensor"  DEAD -> ELECTROSTRICTION is even-order and IS
                                         allowed in a centrosymmetric crystal.
                                         The bridge survives under that name.
    gravitational                ~1e-10 self-weight strain on 1 mm of Si
                                         against a 1e-2 requirement: 8 orders.
                                         And a uniform level shift is
                                         unobservable in any case.

ONE THING THIS DOCUMENT GETS RIGHT THAT SIX OTHERS DID NOT
----------------------------------------------------------
An octahedron has 8 FACES and 6 vertices, and "8 octahedral faces" is correct
terminology. Every other file in the set said "8 vertices". Relative to a
tetrahedral cage the eight (+-1,+-1,+-1) directions split 4+4 under Td -- four
toward vertices, four toward face centres -- which is exactly the parity
structure GIES-2 confirmed against the lattice. They are not symmetry-equivalent
states, and KEA-7 is why this model cannot see the difference.
"""

from __future__ import annotations

import itertools
import math
import random
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "D0", "ALPHA_EV_A2", "BETA_EV_A2", "EV_A2_TO_N_PER_M", "PHI", "A_SI",
    "BOND_DIRS", "CUBE_CORNERS", "BRIDGES",
    "ev_a2_to_n_per_m", "clamped_neighbours", "keating_energy",
    "energy_is_even", "minimise", "find_minima",
    "phi_spacing", "lattice_separations", "nearest_separations",
    "coupling_hessian_is_symmetric", "gate_set_coverage",
    "linear_response", "toffoli_is_degree_two",
    "self_weight_strain", "bridge_verdicts", "main",
]

D0 = 2.35                       # Si-Si bond length, A (VFF.md's value)
ALPHA_EV_A2 = 3.0               # bond stretching, eV/A^2
BETA_EV_A2 = 0.75               # bond bending, eV/A^2
EV_A2_TO_N_PER_M = 1.602176634e-19 / 1e-20
PHI = (1.0 + math.sqrt(5.0)) / 2.0
A_SI = 5.431

_R3 = math.sqrt(3.0)
BOND_DIRS: List[Tuple[float, float, float]] = [
    tuple(c / _R3 for c in t) for t in
    ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))
]
CUBE_CORNERS: List[Tuple[float, float, float]] = [
    tuple(c / _R3 for c in p) for p in itertools.product((1, -1), repeat=3)
]

#: The five proposed bridges, with the symmetry verdict and the replacement.
BRIDGES: Dict[str, Dict[str, object]] = {
    "harmonic": {"mechanism": "phonon strain", "allowed": True,
                 "reason": "no symmetry obstruction", "replacement": None},
    "light": {"mechanism": "inverse piezoelectric", "allowed": False,
              "reason": "Si is centrosymmetric; no piezoelectric tensor",
              "replacement": "deformation potential + photothermal stress"},
    "magnetic": {"mechanism": "magnetostriction", "allowed": False,
                 "reason": "Si is diamagnetic; magnetostriction ~1e-10",
                 "replacement": "strain, written piezo/optomechanically"},
    "electric": {"mechanism": "piezoelectric tensor", "allowed": False,
                 "reason": "same odd-rank symmetry veto",
                 "replacement": "electrostriction (even-order, allowed in Oh)"},
    "gravitational": {"mechanism": "self-weight strain", "allowed": False,
                      "reason": "~1e-10 against a 1e-2 requirement, and a "
                                "uniform level shift is unobservable",
                      "replacement": None},
}


def ev_a2_to_n_per_m(value: float) -> float:
    """Convert eV/A^2 to N/m. 3.0 eV/A^2 = 48.1 N/m."""
    return value * EV_A2_TO_N_PER_M


# ---------------------------------------------------------------------------
# KEA-1 / KEA-7: the clamped cluster
# ---------------------------------------------------------------------------

def clamped_neighbours(d0: float = D0) -> List[Tuple[float, float, float]]:
    """The four tetrahedral neighbours, clamped at the ideal bond length."""
    if d0 <= 0.0:
        raise ValueError("bond length must be positive")
    return [tuple(d0 * c for c in u) for u in BOND_DIRS]


def keating_energy(p: Sequence[float], d0: float = D0,
                   alpha: float = ALPHA_EV_A2,
                   beta: float = BETA_EV_A2) -> float:
    """Keating energy of the central atom at ``p``, eV, neighbours clamped.

    ``E = (3/16)(alpha/d0^2) Sum_k (r_k^2 - d0^2)^2
         + (3/8)(beta/d0^2) Sum_{k<l} (r_k.r_l + d0^2/3)^2``

    Both terms are squares, so E >= 0 with equality only when every bond is at
    d0 and every angle at arccos(-1/3) at once.
    """
    if len(p) != 3:
        raise ValueError("position must be 3-dimensional")
    if alpha < 0.0 or beta < 0.0:
        raise ValueError("force constants must be non-negative")
    v = clamped_neighbours(d0)
    r = [tuple(v[k][i] - p[i] for i in range(3)) for k in range(4)]
    stretch = sum((sum(c * c for c in rk) - d0 * d0) ** 2 for rk in r)
    bend = sum((sum(r[k][i] * r[l][i] for i in range(3)) + d0 * d0 / 3.0) ** 2
               for k, l in itertools.combinations(range(4), 2))
    return ((3.0 / 16.0) * (alpha / d0 ** 2) * stretch
            + (3.0 / 8.0) * (beta / d0 ** 2) * bend)


def energy_is_even(samples: int = 2000, reach: float = 1.0,
                   seed: int = 0, **kw) -> Dict[str, float]:
    """KEA-7: is ``E(p) == E(-p)`` identically?

    It is, and provably: ``Sum_k v_k = 0`` and ``v_k.v_l = -d0^2/3`` exactly, so
    both cross-terms vanish. That makes the model blind to the inversion which
    separates vertex-directed from face-directed displacement -- the same
    degeneracy as GIES-1, from a different direction.
    """
    rng = random.Random(seed)
    worst = 0.0
    scale = 0.0
    for _ in range(samples):
        p = tuple(rng.uniform(-reach, reach) for _ in range(3))
        a = keating_energy(p, **kw)
        b = keating_energy(tuple(-c for c in p), **kw)
        worst = max(worst, abs(a - b))
        scale = max(scale, abs(a))
    v = clamped_neighbours(kw.get("d0", D0))
    resultant = [sum(vk[k] for vk in v) for k in range(3)]
    d0 = kw.get("d0", D0)
    dots = [sum(a * b for a, b in zip(v[k], v[l]))
            for k, l in itertools.combinations(range(4), 2)]
    return {
        "samples": samples,
        "worst_abs_difference": worst,
        "worst_relative": worst / scale if scale > 0 else 0.0,
        "resultant_norm": math.sqrt(sum(x * x for x in resultant)),
        "worst_bend_offset": max(abs(d + d0 * d0 / 3.0) for d in dots),
        "is_even": worst / (scale if scale > 0 else 1.0) < 1e-12,
    }


def minimise(p0: Sequence[float], tol: float = 1e-13,
             step0: float = 0.05, **kw) -> Tuple[Tuple[float, ...], float]:
    """Coordinate descent with step halving. Deterministic, stdlib."""
    p = list(p0)
    step = step0
    e = keating_energy(p, **kw)
    while step > 1e-10:
        moved = False
        for i in range(3):
            for sign in (1, -1):
                q = list(p)
                q[i] += sign * step
                eq = keating_energy(q, **kw)
                if eq < e - tol:
                    p, e = q, eq
                    moved = True
        if not moved:
            step *= 0.5
    return tuple(p), e


def find_minima(starts: int = 200, reach: float = 1.2, seed: int = 1,
                merge_tol: float = 1e-3, **kw) -> List[Tuple[Tuple, float]]:
    """Distinct local minima found from random starts, sorted by energy."""
    if starts <= 0:
        raise ValueError("need at least one start")
    rng = random.Random(seed)
    out: List[Tuple[Tuple, float]] = []
    for _ in range(starts):
        p, e = minimise(tuple(rng.uniform(-reach, reach) for _ in range(3)), **kw)
        if not any(math.dist(p, q) < merge_tol for q, _ in out):
            out.append((p, e))
    return sorted(out, key=lambda t: t[1])


# ---------------------------------------------------------------------------
# KEA-3: phi spacing
# ---------------------------------------------------------------------------

def phi_spacing(a: float = A_SI) -> float:
    """``phi * a_Si`` = 8.7875 A."""
    if a <= 0.0:
        raise ValueError("lattice constant must be positive")
    return PHI * a


def lattice_separations(a: float = A_SI, cells: int = 3,
                        lo: float = 0.1, hi: float = 12.0) -> List[float]:
    """Realisable Si-Si separations in diamond cubic, angstroms, sorted."""
    fcc = [(0.0, 0.0, 0.0), (0.5, 0.5, 0.0), (0.5, 0.0, 0.5), (0.0, 0.5, 0.5)]
    seps = set()
    for n in itertools.product(range(-cells, cells + 1), repeat=3):
        for off in ((0.0, 0.0, 0.0), (0.25, 0.25, 0.25)):
            for f in fcc:
                w = [n[k] + off[k] + f[k] for k in range(3)]
                d = a * math.sqrt(sum(c * c for c in w))
                if lo < d < hi:
                    seps.add(round(d, 3))
    return sorted(seps)


def nearest_separations(target: Optional[float] = None, count: int = 4,
                        a: float = A_SI) -> List[Tuple[float, float]]:
    """(separation, fractional detuning) for the nearest realisable sites."""
    if target is None:
        target = phi_spacing(a)
    if target <= 0.0:
        raise ValueError("target must be positive")
    seps = lattice_separations(a)
    near = sorted(seps, key=lambda d: abs(d - target))[:count]
    return [(d, (d - target) / target) for d in near]


# ---------------------------------------------------------------------------
# KEA-2, KEA-4, KEA-5
# ---------------------------------------------------------------------------

def coupling_hessian_is_symmetric(k_c: float = 1.0) -> Dict[str, object]:
    """KEA-2: the cross-derivative of a static spring, both orders."""
    if k_c <= 0.0:
        raise ValueError("spring constant must be positive")
    return {"d2E_d1d2": -k_c, "d2E_d2d1": -k_c, "symmetric": True,
            "note": "reciprocity is a symmetry statement; breaking it needs "
                    "broken time-reversal, temporal modulation, or "
                    "nonlinearity. phi is none of these."}


def gate_set_coverage(bits: int = 3, group_order: int = 24) -> Dict[str, object]:
    """KEA-4: how much of the reversible gate set a symmetry group reaches."""
    if bits < 1 or group_order < 1:
        raise ValueError("need bits >= 1 and group order >= 1")
    states = 1 << bits
    reversible = math.factorial(states)
    return {
        "bits": bits, "states": states,
        "group_order": group_order,
        "reversible_gates": reversible,
        "coverage": group_order / reversible,
        "one_in": reversible // group_order,
        "boolean_functions": 2 ** states,
        "generates_all": group_order >= reversible,
    }


def linear_response(k_tt: float, k_tc: Sequence[float],
                    controls: Sequence[float]) -> float:
    """KEA-5: minimising a quadratic form gives ``-K_tt^-1 K_tc d_ctrl``.

    Linear in the controls, so no product term and no AND.
    """
    if k_tt <= 0.0:
        raise ValueError("K_tt must be positive for a minimum to exist")
    if len(k_tc) != len(controls):
        raise ValueError("coupling and control vectors must match")
    return -sum(k * c for k, c in zip(k_tc, controls)) / k_tt


def toffoli_is_degree_two() -> Dict[str, object]:
    """KEA-5: Toffoli's target flip is the AND of its controls -- degree 2."""
    table = {(a, b): a & b for a in (0, 1) for b in (0, 1)}
    # a linear map f(a,b) = p*a + q*b + r cannot reproduce AND
    linear_fits = []
    for p in (-1.0, 0.0, 1.0):
        for q in (-1.0, 0.0, 1.0):
            for r in (-1.0, 0.0, 1.0):
                if all(abs(p * a + q * b + r - table[(a, b)]) < 1e-12
                       for a, b in table):
                    linear_fits.append((p, q, r))
    return {"truth_table": table, "degree": 2,
            "linear_fits_found": linear_fits,
            "linear_suffices": bool(linear_fits)}


# ---------------------------------------------------------------------------
# KEA-6
# ---------------------------------------------------------------------------

def self_weight_strain(length_m: float = 1e-3, density: float = 2329.0,
                       youngs_pa: float = 130e9, g: float = 9.80665) -> float:
    """``rho g L / E`` -- gravitational strain in a self-supporting bar."""
    if length_m <= 0.0 or youngs_pa <= 0.0:
        raise ValueError("need length > 0 and modulus > 0")
    return density * g * length_m / youngs_pa


def bridge_verdicts(required_strain: float = 1e-2) -> List[Dict[str, object]]:
    """The five bridges with their symmetry verdicts and replacements."""
    out = []
    for name, b in BRIDGES.items():
        row = dict(b)
        row["bridge"] = name
        if name == "gravitational":
            s = self_weight_strain()
            row["achievable_strain"] = s
            row["orders_short"] = math.log10(required_strain / s)
        out.append(row)
    return out


# ---------------------------------------------------------------------------

def main() -> None:
    print("KEATING CLUSTER AND phi COUPLING\n" + "=" * 70)

    print("\nParameters -- correct, and worth saying so")
    for name, v, std in (("alpha", ALPHA_EV_A2, 48.50), ("beta", BETA_EV_A2, 13.81)):
        print(f"  {name:>5} = {v} eV/A^2 = {ev_a2_to_n_per_m(v):5.1f} N/m"
              f"   (standard {std})")

    print("\nKEA-1  how many minima does the clamped cluster have?")
    mins = find_minima(starts=200)
    print(f"  E at the ideal centre = {keating_energy((0, 0, 0)):.3e} eV")
    print(f"  distinct minima from 200 random starts, |d| <= 1.2 A: {len(mins)}")
    for p, e in mins:
        print(f"    |d| = {math.dist(p, (0, 0, 0)):.6f} A   E = {e:.3e} eV")
    print("  VFF.md claims 8 valleys toward the octahedral faces.")
    print("  Keating is a sum of squares: E >= 0 with a unique zero at the")
    print("  ideal centre, growing outward. No secondary basins exist.")

    print("\nKEA-7  and the model cannot tell vertex from face, exactly")
    ev = energy_is_even(samples=2000)
    print(f"  Sum_k v_k = 0 to {ev['resultant_norm']:.1e}")
    print(f"  v_k.v_l + d0^2/3 = 0 to {ev['worst_bend_offset']:.1e}")
    print("  so both cross terms vanish -> E(p) = E(-p)")
    print(f"  over {ev['samples']} random p: worst relative difference "
          f"{ev['worst_relative']:.1e}, is_even = {ev['is_even']}")
    print("  exact inversion symmetry: the 4 vertex and 4 face directions are")
    print("  energetically indistinguishable. Same collapse as GIES-1's")
    print("  outer(v,v), reached from a completely different direction.")

    print("\nKEA-3  phi*a_Si against realisable lattice separations")
    t = phi_spacing()
    print(f"  phi * a_Si = {t:.4f} A")
    for d, frac in nearest_separations():
        print(f"    {d:7.3f} A  ({frac*100:+.1f}%)")
    print("  dopants occupy lattice sites, so the target falls between them.")

    print("\nKEA-2  reciprocity")
    c = coupling_hessian_is_symmetric()
    print(f"  d2E/dd1dd2 = {c['d2E_d1d2']}, d2E/dd2dd1 = {c['d2E_d2d1']}, "
          f"symmetric = {c['symmetric']}")

    print("\nKEA-4  gate-set coverage")
    g = gate_set_coverage()
    print(f"  O = S4 has {g['group_order']} elements; reversible 3-bit gates "
          f"= S8 = {g['reversible_gates']}")
    print(f"  coverage = 1 in {g['one_in']}; generates_all = {g['generates_all']}")
    print(f"  and there are {g['boolean_functions']} Boolean functions on 3 "
          "bits, nearly all irreversible")

    print("\nKEA-5  a quadratic energy cannot do AND")
    t2 = toffoli_is_degree_two()
    print(f"  Toffoli target flip is degree {t2['degree']} in the controls")
    print(f"  linear fits to the AND table: {t2['linear_fits_found']} "
          f"-> suffices = {t2['linear_suffices']}")
    print(f"  example response, K_tt=2, K_tc=(1,1), controls=(1,1): "
          f"{linear_response(2.0, (1.0, 1.0), (1.0, 1.0)):+.3f} "
          "-- additive, not conditional")

    print("\nKEA-6  the five bridges")
    for row in bridge_verdicts():
        tag = "REAL" if row["allowed"] else "DEAD"
        print(f"  {row['bridge']:>14} ({row['mechanism']}): {tag}")
        print(f"                 {row['reason']}")
        if row["replacement"]:
            print(f"                 -> {row['replacement']}")
        if "orders_short" in row:
            print(f"                 achievable {row['achievable_strain']:.2e}, "
                  f"{row['orders_short']:.1f} orders short")

    print("\nTerminology, correct here and nowhere else in the set:")
    print("  an octahedron has 8 FACES and 6 vertices. '8 octahedral faces' is")
    print("  right. Relative to a tetrahedral cage the eight (+-1,+-1,+-1)")
    print("  directions split 4+4 under Td -- the GIES-2 parity structure.")


if __name__ == "__main__":
    main()
