"""
Complete readout of a symmetric rank-2 tensor by directional projection.

TTM-2 / TTM-3. Companion to ``silicon_error_correction.json`` v2.0 and
``optical_interface.md``: those established that the state is an
ORIENTATION carried by eigenvectors, and that polarization-resolved Raman
can read it. This module answers the question that leaves open -- **which
directions do you have to sample?**

THE DEFECT (TTM-2)
------------------
A natural-looking choice is the four sp3 bond directions. It does not work,
and the failure is structural rather than numerical.

For a direction ``r``, the projection is ``s = r^T T r``. With the four sp3
directions ``(1,1,1) (1,-1,-1) (-1,1,-1) (-1,-1,1) / sqrt3``, every one has
``rx^2 = ry^2 = rz^2 = 1/3``, so the three diagonal components of ``T``
enter every projection with the *same* weight. For a traceless ``T`` they
cancel exactly::

    s1 = (2/3)( Txy + Txz + Tyz)
    s2 = (2/3)(-Txy - Txz + Tyz)
    s3 = (2/3)(-Txy + Txz - Tyz)
    s4 = (2/3)( Txy - Txz - Tyz)

Only off-diagonals survive, and ``s1 + s2 + s3 + s4 = 0``, so on traceless
tensors the four numbers carry **rank 3**, not 4.

Stated exactly, because the two ranks are both true in their own domain and
it matters which one is being quoted:

===============================  ====  ====================================
domain                           rank  what is seen
===============================  ====  ====================================
full symmetric space (6-dim)        4  trace + T2. Blind to E (2-dim)
traceless subspace (5-dim)          3  T2 only. Blind to E (2-dim)
===============================  ====  ====================================

The four projections are linearly independent as functionals on the full
space -- they can read the trace -- but they become dependent the moment
the trace is fixed, which is the regime a deviatoric state variable lives
in. Either way the conclusion is the same and it is the one that matters:
**E is invisible**, so two dimensions of the state space have no readout.

In Td symmetry an ell=2 tensor decomposes as ``E + T2``. The sp3 projections
span exactly ``T2`` (the three off-diagonal / shear components). The ``E``
doublet -- ``(Txx - Tyy)`` and ``(2Tzz - Txx - Tyy)`` -- is **invisible**::

    T = diag(1, -1, 0)   ->   s = (0, 0, 0, 0)
    T = 0                ->   s = (0, 0, 0, 0)

Two physically distinct states, one fingerprint. Any claim that the sp3
readout "resolves positions 0, 2, 3" is false: it resolves T2-type states
and collapses every E-type state onto zero.

THE FIX (TTM-3)
---------------
A symmetric 3x3 has six independent components, so you need six independent
projections. The six ``<110>`` directions work::

    (1,1,0) (1,-1,0) (1,0,1) (1,0,-1) (0,1,1) (0,1,-1)  / sqrt2

These span ``E + T2 + trace`` -- complete, invertible, and each one is a
physically realisable measurement axis. :func:`recover_tensor` inverts the
design matrix and returns the tensor exactly.

This is the same lesson as ``Negentropic/triangnet.py`` and the invariant
blindness in ``silicon_check.py``, in a third setting: a projection is a
scalarisation, and the question is always which part of the geometry it
throws away. Four numbers cannot carry six components no matter how
natural the four directions look.

Stdlib only.
"""

from __future__ import annotations

import math
from typing import List, Sequence, Tuple

__all__ = [
    "SP3_DIRECTIONS", "HKL110_DIRECTIONS",
    "normalize", "project", "projections", "design_matrix",
    "matrix_rank", "traceless_rank", "recover_tensor",
    "components_to_tensor", "tensor_to_components",
]

Matrix = Sequence[Sequence[float]]
Vector = Sequence[float]

#: The four sp3 bond directions of one sublattice. Rank 3 as a readout basis.
SP3_DIRECTIONS: List[Tuple[float, float, float]] = [
    (1.0, 1.0, 1.0), (1.0, -1.0, -1.0), (-1.0, 1.0, -1.0), (-1.0, -1.0, 1.0),
]

#: The six <110> directions. Rank 6 -- a complete readout basis.
HKL110_DIRECTIONS: List[Tuple[float, float, float]] = [
    (1.0, 1.0, 0.0), (1.0, -1.0, 0.0),
    (1.0, 0.0, 1.0), (1.0, 0.0, -1.0),
    (0.0, 1.0, 1.0), (0.0, 1.0, -1.0),
]


def normalize(v: Vector) -> Tuple[float, float, float]:
    """Unit vector. Raises on the zero vector."""
    n = math.sqrt(sum(x * x for x in v))
    if n == 0.0:
        raise ValueError("cannot normalize the zero vector")
    return tuple(x / n for x in v)


def project(T: Matrix, direction: Vector) -> float:
    """``s = r^T T r`` for a unit-normalised ``r``."""
    r = normalize(direction)
    return sum(T[i][j] * r[i] * r[j] for i in range(3) for j in range(3))


def projections(T: Matrix, directions: Sequence[Vector] = None) -> List[float]:
    """Projections of ``T`` onto each direction. Defaults to the sp3 set.

    The default is the *broken* basis on purpose: this function is what the
    TTM readout proposed, and calling it with no argument reproduces the
    defect. Pass ``HKL110_DIRECTIONS`` for a complete measurement.
    """
    dirs = SP3_DIRECTIONS if directions is None else directions
    return [project(T, d) for d in dirs]


def tensor_to_components(T: Matrix) -> List[float]:
    """``(Txx, Tyy, Tzz, Txy, Txz, Tyz)`` -- the six independent components."""
    return [T[0][0], T[1][1], T[2][2], T[0][1], T[0][2], T[1][2]]


def components_to_tensor(c: Sequence[float]) -> List[List[float]]:
    """Inverse of :func:`tensor_to_components`."""
    if len(c) != 6:
        raise ValueError("expected 6 components")
    return [[c[0], c[3], c[4]], [c[3], c[1], c[5]], [c[4], c[5], c[2]]]


def design_matrix(directions: Sequence[Vector]) -> List[List[float]]:
    """Rows mapping tensor components to projections.

    ``s = r^T T r`` expands to
    ``Txx rx^2 + Tyy ry^2 + Tzz rz^2 + 2 Txy rx ry + 2 Txz rx rz + 2 Tyz ry rz``,
    so each row is ``[rx^2, ry^2, rz^2, 2 rx ry, 2 rx rz, 2 ry rz]``.

    Inspecting this matrix is the whole diagnosis: for the sp3 set the first
    three columns are identical in every row, which is why the diagonal is
    unrecoverable.
    """
    rows = []
    for d in directions:
        x, y, z = normalize(d)
        rows.append([x * x, y * y, z * z, 2 * x * y, 2 * x * z, 2 * y * z])
    return rows


def matrix_rank(rows: Matrix, tol: float = 1e-10) -> int:
    """Numerical rank by Gaussian elimination with partial pivoting."""
    a = [list(map(float, r)) for r in rows]
    if not a:
        return 0
    n_rows, n_cols = len(a), len(a[0])
    rank = 0
    for col in range(n_cols):
        pivot = None
        best = tol
        for r in range(rank, n_rows):
            if abs(a[r][col]) > best:
                best, pivot = abs(a[r][col]), r
        if pivot is None:
            continue
        a[rank], a[pivot] = a[pivot], a[rank]
        pv = a[rank][col]
        for r in range(n_rows):
            if r != rank and abs(a[r][col]) > 0.0:
                f = a[r][col] / pv
                for c in range(col, n_cols):
                    a[r][c] -= f * a[rank][c]
        rank += 1
        if rank == n_rows:
            break
    return rank


def traceless_rank(directions: Sequence[Vector], tol: float = 1e-10) -> int:
    """Rank of the readout restricted to TRACELESS symmetric tensors.

    The deviatoric part is where a strain state variable lives, so this is
    usually the number that matters. The sp3 set gives 4 here on the full
    space and 3 on the traceless subspace; both say E is unreadable.

    Implemented by substituting ``Tzz = -(Txx + Tyy)`` and re-ranking the
    resulting 5-column system.
    """
    rows = []
    for row in design_matrix(directions):
        xx, yy, zz, xy, xz, yz = row
        rows.append([xx - zz, yy - zz, xy, xz, yz])
    return matrix_rank(rows, tol)


def recover_tensor(measurements: Sequence[float],
                   directions: Sequence[Vector] = None) -> List[List[float]]:
    """Solve for the symmetric tensor that produced these projections.

    Defaults to the six ``<110>`` directions, which give a square invertible
    system. Raises if the supplied directions are rank-deficient -- that is
    the TTM-2 failure, and it is better to refuse than to return one of the
    infinitely many tensors consistent with an incomplete measurement.
    """
    dirs = HKL110_DIRECTIONS if directions is None else directions
    if len(measurements) != len(dirs):
        raise ValueError("need one measurement per direction")

    A = design_matrix(dirs)
    if matrix_rank(A) < 6:
        raise ValueError(
            f"rank-deficient readout basis: rank {matrix_rank(A)} < 6. "
            "These directions cannot determine a symmetric rank-2 tensor. "
            "The four sp3 directions have rank 3 and are blind to the E "
            "doublet -- use HKL110_DIRECTIONS."
        )
    if len(dirs) != 6:
        raise ValueError("exactly 6 directions required for a square solve")

    # Gaussian elimination with partial pivoting on the augmented system.
    aug = [row[:] + [float(measurements[i])] for i, row in enumerate(A)]
    for col in range(6):
        pivot = max(range(col, 6), key=lambda r: abs(aug[r][col]))
        if abs(aug[pivot][col]) < 1e-12:
            raise ValueError("singular readout basis")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        pv = aug[col][col]
        for c in range(col, 7):
            aug[col][c] /= pv
        for r in range(6):
            if r != col and aug[r][col] != 0.0:
                f = aug[r][col]
                for c in range(col, 7):
                    aug[r][c] -= f * aug[col][c]
    return components_to_tensor([aug[i][6] for i in range(6)])


if __name__ == "__main__":
    print("TTM-2: the sp3 readout is rank-3 and blind to the E doublet\n")

    A_sp3 = design_matrix(SP3_DIRECTIONS)
    print(f"  sp3 rank, full space      : {matrix_rank(A_sp3)} of 6"
          f"   (trace + T2)")
    print(f"  sp3 rank, traceless       : {traceless_rank(SP3_DIRECTIONS)} of 5"
          f"   (T2 only -- E is unreadable either way)")
    print("  first three columns (Txx, Tyy, Tzz weights), one row per direction:")
    for row in A_sp3:
        print(f"    {row[0]:+.4f} {row[1]:+.4f} {row[2]:+.4f}"
              f"   | off-diag {row[3]:+.4f} {row[4]:+.4f} {row[5]:+.4f}")
    print("  identical in every row -> the diagonal cannot be recovered.\n")

    e_state = [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 0.0]]
    zero = [[0.0] * 3 for _ in range(3)]
    print(f"  T = diag(1,-1,0)  -> s = {[round(v, 12) for v in projections(e_state)]}")
    print(f"  T = 0             -> s = {[round(v, 12) for v in projections(zero)]}")
    print("  Two distinct states, one fingerprint. This is the counterexample.\n")

    s = projections(e_state)
    print(f"  sum of the four projections: {sum(s):.1e}  -> rank 3, not 4\n")

    print("TTM-3: six <110> projections determine the tensor completely\n")
    A_110 = design_matrix(HKL110_DIRECTIONS)
    print(f"  <110> rank, full space    : {matrix_rank(A_110)} of 6")
    print(f"  <110> rank, traceless     : {traceless_rank(HKL110_DIRECTIONS)} of 5")

    for label, T in (
        ("E-type  diag(1,-1,0)", e_state),
        ("T2-type pure shear   ", [[0.0, 0.5, 0.0], [0.5, 0.0, 0.0], [0.0, 0.0, 0.0]]),
        ("general              ", [[0.3, -0.2, 0.15], [-0.2, -0.1, 0.05],
                                   [0.15, 0.05, -0.2]]),
    ):
        rec = recover_tensor(projections(T, HKL110_DIRECTIONS))
        err = max(abs(rec[i][j] - T[i][j]) for i in range(3) for j in range(3))
        print(f"  {label} recovered, max error {err:.2e}")

    print("\n  The E-type state that the sp3 basis could not see is recovered")
    print("  exactly. Six components need six projections.\n")

    try:
        recover_tensor(projections(e_state), SP3_DIRECTIONS)
    except ValueError as exc:
        print(f"  recover_tensor(sp3) refuses: {str(exc)[:60]}...")
