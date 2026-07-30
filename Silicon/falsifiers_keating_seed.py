#!/usr/bin/env python3
"""Runnable falsifiers: KEA-1, KEA-3, KEA-7, SEED-1, SEED-5.

    python Silicon/falsifiers_keating_seed.py

Stdlib only, no arguments, exits non-zero if any falsifier fails. Thin driver
over ``keating_cluster.py`` and ``seed_influence.py`` so there is one source of
truth for the arithmetic; the assertions live here.
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from keating_cluster import (  # noqa: E402
    ALPHA_EV_A2, BETA_EV_A2, BOND_DIRS, CUBE_CORNERS,
    energy_is_even, ev_a2_to_n_per_m, find_minima, keating_energy,
    nearest_separations, phi_spacing,
)
from seed_influence import (  # noqa: E402
    axis_directions, cube_corner_directions, influence_matrix, is_identity,
    max_offdiagonal, precision_gap_orders, proportions_invariant,
    quantisation_step, row_sums, row_sums_equal,
)

FAILED = []


def check(claim, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {claim}")
    if detail:
        print(f"         {detail}")
    if not ok:
        FAILED.append(claim)


def main():
    print("=" * 72)
    print("KEATING PARAMETERS  (credit where due -- these are right)")
    print("=" * 72)
    print(f"  alpha = {ALPHA_EV_A2} eV/A^2 = {ev_a2_to_n_per_m(ALPHA_EV_A2):.1f} N/m"
          f"   (standard 48.50)")
    print(f"  beta  = {BETA_EV_A2} eV/A^2 = {ev_a2_to_n_per_m(BETA_EV_A2):.1f} N/m"
          f"   (standard 13.81)")

    print("\n" + "=" * 72)
    print("KEA-1  does the clamped 5-atom cluster have 8 minima?")
    print("=" * 72)
    print(f"  E at the ideal centre: {keating_energy((0, 0, 0)):.3e} eV\n")
    print(f"  {'|d| (A)':>9} {'toward +t1 (vertex)':>21} {'toward -t1 (face)':>19}")
    u = BOND_DIRS[0]
    for d in (0.0, 0.05, 0.10, 0.20, 0.50, 0.80):
        ep = keating_energy(tuple(d * c for c in u))
        em = keating_energy(tuple(-d * c for c in u))
        print(f"  {d:>9.2f} {ep:>21.5f} {em:>19.5f}")
    mins = find_minima(starts=200)
    print(f"\n  200 random starts, |d| up to 1.2 A: {len(mins)} distinct minima")
    for p, e in mins:
        print(f"    pos=({p[0]:+.5f},{p[1]:+.5f},{p[2]:+.5f})  "
              f"|d|={math.dist(p, (0, 0, 0)):.5f}  E={e:.3e} eV")
    check("KEA-1: exactly one minimum, at the ideal centre", len(mins) == 1,
          "Keating is a sum of squares -> E >= 0 with a unique zero. "
          "VFF.md claims 8 valleys.")

    print("\n" + "=" * 72)
    print("KEA-7  can the model tell a vertex direction from a face direction?")
    print("=" * 72)
    ev = energy_is_even(samples=2000)
    print(f"  Sum_k v_k = 0 to {ev['resultant_norm']:.1e}")
    print(f"  v_k.v_l + d0^2/3 = 0 to {ev['worst_bend_offset']:.1e}")
    print("  both cross terms vanish -> E(p) = E(-p)")
    print(f"  {ev['samples']} random p: worst relative difference "
          f"{ev['worst_relative']:.1e}")
    e_at = {round(keating_energy(tuple(0.25 * c for c in v)), 10)
            for v in CUBE_CORNERS}
    print(f"  all 8 cube-corner directions at |d|=0.25: "
          f"{len(e_at)} distinct energy value(s)")
    check("KEA-7: energy is exactly even, so vertex and face are degenerate",
          ev["is_even"] and len(e_at) == 1,
          "exact inversion symmetry -- the same collapse as GIES-1's "
          "outer(v,v), reached from a different direction")

    print("\n" + "=" * 72)
    print("KEA-3  is phi * a_Si a realisable Si-Si separation?")
    print("=" * 72)
    t = phi_spacing()
    print(f"  phi * a_Si = {t:.4f} A")
    near = nearest_separations()
    for d, frac in near:
        print(f"    {d:>8.3f} A   off by {d - t:+.3f} A  ({frac * 100:+.1f}%)")
    check("KEA-3: no lattice separation lands on phi*a",
          all(abs(f) > 1e-3 for _, f in near),
          "dopants occupy lattice sites; the target falls between them")

    print("\n" + "=" * 72
          + "\nSEED-1  what is W_ij = max(0, u_i . u_j) on the axis directions?")
    print("=" * 72)
    ident = True
    for dim, label in ((3, "3D, 6 directions"), (8, "8D, 16 directions")):
        w = influence_matrix(axis_directions(dim))
        ident &= is_identity(w)
        print(f"  {label:<20} n={len(w):2d}   max off-diagonal = "
              f"{max_offdiagonal(w):.1f}   W == I ? "
              f"{'YES' if is_identity(w) else 'no'}")
    print("\n  3D W matrix:")
    for row in influence_matrix(axis_directions(3)):
        print("    " + " ".join(f"{v:.0f}" for v in row))
    print("\n  u_i.u_i = +1 -> 1 ;  u_i.u_(-i) = -1 -> max(0,-1) = 0 ;  orth -> 0")
    r = proportions_invariant(axis_directions(3))
    print(f"  proportions across shells: worst drift "
          f"{r['worst_proportion_drift']:.1e}")
    check("SEED-1: W is the identity, so the channels are independent scalars",
          ident, "structure preservation is then automatic, for ANY sigma")

    print("\n" + "=" * 72)
    print("SEED-5  does the recommended cube-corner fix restore falsifiability?")
    print("=" * 72)
    corners = cube_corner_directions()
    w = influence_matrix(corners)
    entries = sorted({round(v, 6) for row in w for v in row})
    print(f"  cube-corner W entries: {entries}   <- non-trivial, as recommended")
    print(f"  every row sums to {sorted(set(round(s, 9) for s in row_sums(w)))}")
    rc = proportions_invariant(corners)
    print(f"  proportions across shells: worst drift "
          f"{rc['worst_proportion_drift']:.1e}, invariant = {rc['invariant']}")
    profiles = [(lambda r, k=k: math.exp(-r * r * (1.0 + 0.35 * k)))
                for k in range(len(corners))]
    rp = proportions_invariant(corners, per_channel=profiles)
    print(f"  with direction-dependent f_i(r): worst drift "
          f"{rp['worst_proportion_drift']:.3f}, invariant = {rp['invariant']}")
    check("SEED-5: the fix makes W non-trivial but keeps proportions invariant",
          (not is_identity(w)) and row_sums_equal(w) and rc["invariant"]
          and not rp["invariant"],
          "vertex-transitivity forces equal row sums; what breaks the "
          "tautology is a direction-dependent radial profile")

    print("\n" + "=" * 72)
    print("SEED-3  seed quantisation against the claimed fidelity")
    print("=" * 72)
    print(f"  5 x 8-bit values: step = {quantisation_step(8):.4e}  (1/256)")
    print("  claimed structure fidelity: 1.0e-16")
    print(f"  ratio = {quantisation_step(8) / 1e-16:.1e}  "
          f"({precision_gap_orders():.1f} orders apart)")
    check("SEED-3: the claimed fidelity is 13 orders below the seed resolution",
          precision_gap_orders() > 13.0,
          "the forward map's numerical precision is being reported as the "
          "compression fidelity")

    print("\n" + "=" * 72)
    if FAILED:
        print(f"{len(FAILED)} FALSIFIER(S) FAILED:")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("all falsifiers behaved as registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
