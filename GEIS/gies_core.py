"""GIES core: sign-sensitive state tensors, site parity, and a true codec.

Stdlib only. Supersedes the tensor construction in ``state_tensor.py`` and the
operator encoding in ``geometric_encoder.py``. Both of those are left in place
for provenance and still pass their suites; see ``GIES_AUDIT.md`` for why they
should not be used for new work.

THE BUG THIS EXISTS TO FIX
--------------------------
``state_tensor.py`` builds ``T = outer(v, v)`` from one position vector, and
``outer(v, v) == outer(-v, -v)`` identically. The position table is antipodal
in pairs (state 7-i is exactly -state i), so:

* eigenvalues are {0, 0, 0.1875} for all eight states
* trace is 0.1875 for all eight, determinant 0 for all eight
* ``project(n)`` returns (n.v)^2 == (n.-v)^2 for every direction n
* eigenvectors differ only up to sign, which is not observable

Every scalar method in the class returns the same number for all eight states,
and states i and 7-i are indistinguishable by any operation it offers. Since
``NOT(i) = 7-i``, the gate set's only unary operation is invisible to the
representation.

``GIES.md`` §7.2 already specifies the right thing --
``T = SUM_i w_i * t_i (x) t_i`` over the bond directions with electron-density
weights -- and §8.3 implements a degenerate special case of it. The spec is
correct; only the code was wrong.

WHAT THE FIX BUYS, IN CLOSED FORM
---------------------------------
The four sp3 bonds are a spherical 2-design, so ``SUM_i t_i (x) t_i = (4/3) I``.
With ``w_i = 1 + kappa * (t_i . u)`` and ``u = +-t_k``, the sum telescopes:

    u = +t_k :  T = (1 - kappa/3)(4/3) I + (4 kappa/3) t_k (x) t_k
    u = -t_k :  T = (1 + kappa/3)(4/3) I - (4 kappa/3) t_k (x) t_k

giving eigenvalues

    lattice      { 4/3 + 8k/9,  4/3 - 4k/9,  4/3 - 4k/9 }   k=0.5 -> 1.778, 1.111, 1.111
    interstitial { 4/3 - 8k/9,  4/3 + 4k/9,  4/3 + 4k/9 }   k=0.5 -> 0.889, 1.556, 1.556

Distinct, so the collapse is gone. The doubly-degenerate pair is not a defect:
it is the C3v axial symmetry of a <111> direction, correctly reproduced.

WHICH INVARIANT CARRIES THE BIT -- not the trace
------------------------------------------------
The anisotropic part is traceless, so ``trace = 4`` for all eight states and
the trace separates nothing. The separating invariant is **J3, the determinant
of the deviator**, which flips sign with parity: +0.02195 on the lattice
sublattice and -0.02195 on the interstitial, at kappa = 0.5. J2 is identical
for both. That is the same "J3 mode" invariant already listed in
``Silicon/silicon_error_correction.json``, so the check bit is readable by the
strain channel that repository settled on.

Information split, and it is the right one:

    J3 sign         -> 1 bit : site type, == index parity   <- the check bit
    unique axis     -> 2 bits: which of the four bond directions
                       3 bits total, with the error-detecting bit free

INDEX PARITY IS SITE TYPE, AND THAT IS PHYSICAL
-----------------------------------------------
Walk 2.352 A from a lattice atom along each of the eight <111> directions.
The four even-parity positions land on atoms; the four odd-parity positions are
empty, and their coordination shell (4 neighbours at 2.352 A, 6 at 2.716 A) is
identical to the tetrahedral interstitial at (1/2,1/2,1/2). Verified in
``tests/test_gies_core.py`` against the diamond-cubic basis.

This refines rather than contradicts the note in ``CLAUDE.md`` that the eight
<111> directions are "4 sublattice-A bonds + 4 sublattice-B bonds". Both hold:
as *directions* the eight are the two sublattices' bond sets, but from a
*fixed* atom only the four even-parity ones terminate on an atom.

Two consequences, both hard:

1. The eight states are 4 atoms + 4 holes, not eight interchangeable
   configurations of one object. Moving an atom to an interstitial is a Frenkel
   pair: ~4.5-5 eV, and it leaves a vacancy behind.
2. ``NOT(i) = 7-i`` flips all three bits, so it flips parity. Every NOT is a
   Frenkel pair. The cheapest operation in the gate set is the most expensive
   physical event in the crystal.

The honest state space is therefore 4 states plus a site-type flag, not 8
interchangeable states, because crossing the flag costs a Frenkel pair.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

__all__ = [
    "R3", "BONDS", "CORNERS", "FRENKEL_EV", "SI_BOND_A",
    "parity", "site_type", "frenkel", "corner_index",
    "Cell", "closed_form_eigenvalues", "decode_tensor",
    "hamming_weight_pairs", "main",
]

R3 = math.sqrt(3.0)

#: The four sp3 bond directions (Td), normalised. These are the LATTICE-SITE
#: directions: from an atom, each terminates on a nearest neighbour.
BONDS: List[Tuple[float, float, float]] = [
    tuple(c / R3 for c in b) for b in
    ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))
]

#: The eight cube corners, NOT octahedron vertices. An octahedron has 6
#: vertices at (+-a,0,0) and permutations; a cube has 8 corners at
#: (+-a,+-a,+-a). The index bits select sign flips on (z, x, y) in that order,
#: matching the position table in GIES.md, so the number of set bits equals the
#: number of negative coordinates.
CORNERS: Dict[int, Tuple[int, int, int]] = {
    0: (1, 1, 1), 1: (1, -1, 1), 2: (-1, 1, 1), 3: (-1, -1, 1),
    4: (1, 1, -1), 5: (1, -1, -1), 6: (-1, 1, -1), 7: (-1, -1, -1),
}

FRENKEL_EV = 4.75          # Si Frenkel pair formation, ~4.5-5 eV
SI_BOND_A = 2.3517         # sqrt(3)/4 * 5.431


def parity(index: int) -> int:
    """Parity of the 3-bit index == parity of the number of negative coords."""
    if not 0 <= index <= 7:
        raise ValueError("index must be 0-7")
    return bin(index).count("1") & 1


def site_type(index: int) -> str:
    """``lattice`` for even parity, ``interstitial`` for odd. See module docs."""
    return "interstitial" if parity(index) else "lattice"


def frenkel(i: int, j: int) -> bool:
    """Does the i -> j transition cross sublattices?

    True means the transition is a Frenkel pair: ~4.75 eV, and it leaves a
    vacancy behind. ``NOT(i) = 7-i`` flips three bits, so NOT always crosses.
    """
    return parity(i) != parity(j)


def corner_index(vec: Sequence[float], tol: float = 1e-9) -> int:
    """Inverse of ``CORNERS``: which index has this sign pattern."""
    signs = tuple(1 if c > tol else (-1 if c < -tol else 0) for c in vec)
    if 0 in signs:
        raise ValueError("direction is not a cube corner: has a zero component")
    for idx, corner in CORNERS.items():
        if signs == corner:
            return idx
    raise ValueError(f"no corner matches {signs}")


def hamming_weight_pairs() -> List[Tuple[int, int]]:
    """The four inversion pairs (i, 7-i) that ``outer(v,v)`` cannot separate."""
    return [(i, 7 - i) for i in range(4)]


class Cell:
    """One GIES cell. Direction is sign-sensitive, unlike ``outer(v, v)``.

    ``kappa`` is the electron-density anisotropy weight from GIES.md §7.2.
    At kappa = 0 the tensor is isotropic and all eight states collapse again --
    that is the correct behaviour, not a bug, and it is what makes kappa the
    knob that controls state distinguishability.
    """

    __slots__ = ("index", "kappa", "u")

    def __init__(self, index: int, kappa: float = 0.5):
        if not 0 <= index <= 7:
            raise ValueError("index must be 0-7")
        if not isinstance(index, int):
            raise ValueError("index must be an integer")
        self.index = index
        self.kappa = float(kappa)
        self.u = tuple(c / R3 for c in CORNERS[index])

    # -- GIES.md §7.2 as written -------------------------------------------
    def tensor(self) -> List[List[float]]:
        """``T = SUM_i w_i * t_i (x) t_i``, ``w_i = 1 + kappa * (t_i . u)``.

        The dot product flips sign under ``u -> -u``, so ``T(i) != T(7-i)``.
        That is the whole fix; §8.3's single outer product cannot do it.
        """
        T = [[0.0] * 3 for _ in range(3)]
        for t in BONDS:
            w = 1.0 + self.kappa * sum(a * b for a, b in zip(t, self.u))
            for a in range(3):
                for b in range(3):
                    T[a][b] += w * t[a] * t[b]
        return T

    def trace(self) -> float:
        """Always 4.0: the anisotropic part is traceless. Carries no bit."""
        T = self.tensor()
        return T[0][0] + T[1][1] + T[2][2]

    def deviator(self) -> List[List[float]]:
        T = self.tensor()
        m = self.trace() / 3.0
        return [[T[i][j] - (m if i == j else 0.0) for j in range(3)]
                for i in range(3)]

    def j2(self) -> float:
        """Second deviatoric invariant. Identical for both sublattices."""
        d = self.deviator()
        return 0.5 * sum(d[i][j] * d[i][j] for i in range(3) for j in range(3))

    def j3(self) -> float:
        """Third deviatoric invariant. THIS is what carries the site-type bit.

        Sign is negative on the interstitial sublattice and positive on the
        lattice sublattice, so ``j3() < 0`` is exactly ``parity(index) == 1``.
        """
        d = self.deviator()
        return (d[0][0] * (d[1][1] * d[2][2] - d[1][2] * d[2][1])
                - d[0][1] * (d[1][0] * d[2][2] - d[1][2] * d[2][0])
                + d[0][2] * (d[1][0] * d[2][1] - d[1][1] * d[2][0]))

    def determinant(self) -> float:
        T = self.tensor()
        return (T[0][0] * (T[1][1] * T[2][2] - T[1][2] * T[2][1])
                - T[0][1] * (T[1][0] * T[2][2] - T[1][2] * T[2][0])
                + T[0][2] * (T[1][0] * T[2][1] - T[1][1] * T[2][0]))

    def project(self, direction: Sequence[float]) -> float:
        """``d . T . d`` for a unit-normalised d."""
        n = math.sqrt(sum(c * c for c in direction))
        if n <= 0.0:
            raise ValueError("direction must be nonzero")
        d = [c / n for c in direction]
        T = self.tensor()
        return sum(d[a] * T[a][b] * d[b] for a in range(3) for b in range(3))

    def bond_projections(self) -> List[float]:
        """``t_j . T . t_j`` for the four bond directions -- the readout."""
        return [self.project(t) for t in BONDS]

    def eigenvalues(self) -> List[float]:
        """Descending. Analytic: T = alpha*I + beta*t_k (x) t_k."""
        alpha, beta, _ = self._decomposition()
        return sorted([alpha + beta, alpha, alpha], reverse=True)

    def unique_axis(self) -> Tuple[float, float, float]:
        """The non-degenerate eigenvector: +-t_k, sign not observable."""
        return BONDS[self._decomposition()[2]]

    def _decomposition(self) -> Tuple[float, float, int]:
        """Recover (alpha, beta, k) from the construction."""
        k = self.index if parity(self.index) == 0 else 7 - self.index
        # the even-parity member of the pair names the bond direction
        bond_of = {0: 0, 3: 3, 5: 1, 6: 2}
        kk = bond_of[k]
        if parity(self.index) == 0:
            alpha = (1.0 - self.kappa / 3.0) * (4.0 / 3.0)
            beta = 4.0 * self.kappa / 3.0
        else:
            alpha = (1.0 + self.kappa / 3.0) * (4.0 / 3.0)
            beta = -4.0 * self.kappa / 3.0
        return alpha, beta, kk

    def site(self) -> str:
        return site_type(self.index)

    def parity(self) -> int:
        return parity(self.index)

    def to_bits(self) -> str:
        return format(self.index, "03b")

    def __eq__(self, other) -> bool:
        return (isinstance(other, Cell) and other.index == self.index
                and other.kappa == self.kappa)

    def __hash__(self) -> int:
        return hash((self.index, self.kappa))

    def __repr__(self) -> str:
        return (f"Cell({self.index}, kappa={self.kappa}) "
                f"[{self.to_bits()}, {self.site()}]")


def closed_form_eigenvalues(is_lattice: bool,
                            kappa: float = 0.5) -> List[float]:
    """The closed form, for checking the construction without running it."""
    base = 4.0 / 3.0
    if is_lattice:
        return sorted([base + 8 * kappa / 9, base - 4 * kappa / 9,
                       base - 4 * kappa / 9], reverse=True)
    return sorted([base - 8 * kappa / 9, base + 4 * kappa / 9,
                   base + 4 * kappa / 9], reverse=True)


def decode_tensor(T: Sequence[Sequence[float]],
                  tol: float = 1e-9) -> Optional[int]:
    """Recover the 3-bit index from a tensor. Returns None if T is isotropic.

    Four projections onto the bond directions suffice here, which does NOT
    contradict TTM-2 in ``Silicon/tensor_readout.py``. TTM-2 says the four sp3
    projections are rank-deficient on a *general* symmetric tensor and blind to
    the E doublet. These tensors are not general: they live in the two-parameter
    family ``alpha*I + beta*t_k (x) t_k``, and inside that family the four
    projections are complete. Reading an arbitrary strain tensor still needs the
    six <110> directions.
    """
    projections = []
    for t in BONDS:
        projections.append(sum(t[a] * T[a][b] * t[b]
                               for a in range(3) for b in range(3)))
    spread = max(projections) - min(projections)
    if spread <= tol:
        return None                       # isotropic: kappa == 0
    # the unique axis is the outlier; whether it is high or low gives parity
    hi = max(range(4), key=lambda i: projections[i])
    lo = min(range(4), key=lambda i: projections[i])
    others_hi = [projections[i] for i in range(4) if i != hi]
    is_lattice = max(others_hi) - min(others_hi) <= tol * 10 + 1e-12
    k = hi if is_lattice else lo
    bond_to_even = {0: 0, 3: 3, 1: 5, 2: 6}
    even_index = bond_to_even[k]
    return even_index if is_lattice else 7 - even_index


def main() -> None:
    print("GIES CORE\n" + "=" * 70)
    print("\nThe collapse in state_tensor.py, in two lines:")

    def outer(v):
        return [[x * y for y in v] for x in v]

    print(f"  outer([.25,.25,.25]) == outer([-.25,-.25,-.25]) -> "
          f"{outer([.25, .25, .25]) == outer([-.25, -.25, -.25])}")
    print(f"  outer([.25,-.25,.25]) == outer([-.25,.25,-.25]) -> "
          f"{outer([.25, -.25, .25]) == outer([-.25, .25, -.25])}")

    print("\nThe fix, per state (kappa = 0.5):")
    print(f"  {'idx':>3} {'bits':>5} {'par':>4} {'site':>13} "
          f"{'eigenvalues':>28} {'Tr':>6} {'J2':>8} {'J3':>9} {'decode':>7}")
    for i in range(8):
        c = Cell(i)
        ev = " ".join(f"{e:.4f}" for e in c.eigenvalues())
        print(f"  {i:>3} {c.to_bits():>5} {c.parity():>4} {c.site():>13} "
              f"{ev:>28} {c.trace():>6.3f} {c.j2():>8.5f} {c.j3():>+9.5f} "
              f"{decode_tensor(c.tensor()):>7}")

    print("\n  trace is identical for all 8 -- carries no bit")
    print("  J2 is identical for both sublattices -- carries no bit")
    print("  J3 flips sign with parity -- THIS is the check bit")

    print("\nInversion pairs, which outer(v,v) could not separate:")
    for i, j in hamming_weight_pairs():
        a, b = Cell(i), Cell(j)
        print(f"  {i} vs {j}: tensors differ = {a.tensor() != b.tensor()}, "
              f"J3 {a.j3():+.5f} vs {b.j3():+.5f}, "
              f"NOT is Frenkel = {frenkel(i, j)}")

    print(f"\nEvery NOT crosses sublattices, at ~{FRENKEL_EV} eV each:")
    print(f"  all 8: {all(frenkel(i, 7 - i) for i in range(8))}")

    print("\nkappa = 0 collapses again, correctly -- it is the anisotropy knob:")
    print(f"  decode_tensor at kappa=0: {decode_tensor(Cell(0, kappa=0.0).tensor())}")
    print(f"  eigenvalues at kappa=0:   "
          f"{[round(e, 6) for e in Cell(0, kappa=0.0).eigenvalues()]}")


if __name__ == "__main__":
    main()
