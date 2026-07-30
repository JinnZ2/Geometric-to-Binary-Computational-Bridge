#!/usr/bin/env python3
"""Runnable falsifiers: ER-2, NEG-7, GIES-2.

    python Silicon/falsifiers.py

Stdlib only, no arguments, exits non-zero if any falsifier fails. Thin driver
over ``er_bounds.py``, ``Negentropic/lens_collapse_test.py`` and
``GEIS/gies_core.py`` so the arithmetic has one home; the assertions live here.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
for p in (_HERE, _ROOT, os.path.join(_ROOT, "GEIS"),
          os.path.join(_ROOT, "Negentropic")):
    sys.path.insert(0, p)

from er_bounds import (  # noqa: E402
    MASSES_U, coherence_shortfall, force_constant, gap_mode_possible,
    heavy_mass_ceiling, kT_wavenumber, lvm_gate, mass_ratio, orbach_regime,
    wavenumber_from_k,
)
from gies_core import (  # noqa: E402
    CORNERS, frenkel, parity, site_type,
)

FAILED = []


def check(claim, ok, detail=""):
    tag = "PASS" if ok else "FAIL"
    print(f"  [{tag}] {claim}")
    if detail:
        print(f"         {detail}")
    if not ok:
        FAILED.append(claim)


def er2():
    print("=" * 72)
    print("ER-2  LOCAL VIBRATIONAL MODE -- THE GAP-MODE CRITERION")
    print("=" * 72)
    print("  a localized mode lies ABOVE the host phonon maximum only if the")
    print("  impurity is LIGHTER than the host it replaces.\n")
    print("  Si optical phonon maximum: 520.7 cm^-1\n")
    print(f"  {'impurity':>10} {'m/u':>9} {'m/mSi':>7}   verdict")
    for name in ("B", "C", "O", "Si", "P", "Er"):
        r = mass_ratio(name)
        verdict = ("GAP MODE possible" if r < 1.0
                   else "NO GAP MODE -- in-band resonance")
        print(f"  {name:>10} {MASSES_U[name]:>9.2f} {r:>7.2f}   {verdict}")
    ceil = heavy_mass_ceiling("Er")
    print(f"\n  heavy-mass ceiling for Er: 520.7*sqrt(28.09/167.26) "
          f"= {ceil:.0f} cm^-1")
    g = lvm_gate(300.0, 400.0, "Er")
    print("  the document's search window is 300-400 cm^-1 -- ABOVE that.")
    check("ER-2: no Er gap mode exists in the searched window",
          (not gap_mode_possible("Er")) and (not g["window_reachable"]),
          "the $10k flagship gate has no target")
    check("ER-2b: the same criterion kills 'P local mode at ~500 cm^-1'",
          not gap_mode_possible("P"),
          f"P/Si = {mass_ratio('P'):.2f} > 1, and 500 sits in the tail of "
          "the far stronger 520.7 line")

    print("\n  k_well = m_Er * omega^2 consistency, both directions:")
    for wn in (300.0, 350.0, 400.0):
        print(f"    omega = {wn:>5.0f} cm^-1  ->  k = {force_constant(wn):>7.0f} N/m")
    for k in (100.0, 150.0):
        print(f"    k     = {k:>5.0f} N/m    ->  omega = {wavenumber_from_k(k):>5.0f} cm^-1")
    ratio = force_constant(350.0) / 150.0
    print("\n  the document pairs 300-400 cm^-1 with k_well >= 150 N/m.")
    print(f"  350 cm^-1 -> {force_constant(350.0):.0f} N/m; "
          f"150 N/m -> {wavenumber_from_k(150.0):.0f} cm^-1.")
    check("ER-3: the stated (omega, k) pair is inconsistent by ~8x",
          7.5 < ratio < 8.5, f"measured {ratio:.1f}x")

    print("\n  and Orbach at 300 K:")
    print(f"    kT = {kT_wavenumber(300.0):.1f} cm^-1 against a CF gap of 40-60")
    for gap in (40.0, 60.0):
        r = orbach_regime(gap)
        print(f"    gap {gap:.0f}: D/kT = {r['gap_over_kT']:.3f}, "
              f"exp = {r['exp_factor']:.3f}, Bose n_bar = "
              f"{r['bose_occupation']:.2f}  -> {r['regime']}")
    s = coherence_shortfall(166e-3, 1e-9)
    print(f"    claimed T2 166 ms vs a 2*T1 ceiling of "
          f"{s['t2_ceiling_s'] * 1e9:.0f} ns: "
          f"{s['orders_over_ceiling']:.1f} orders")
    check("ER-1: Orbach is saturated at 300 K, not merely open",
          orbach_regime(40.0)["saturated"] and orbach_regime(40.0)["bose_occupation"] > 1.0,
          "Delta << kT, so the rate goes linear in T and the intermediate "
          "doublet is several phonons deep")
    print()


def neg7():
    print("=" * 72)
    print("NEG-7  IS THE 17-LENS ISOMORPHISM A FINDING OR AN ARTIFACT?")
    print("=" * 72)
    from core import DissipativeCore  # noqa: E402
    from lens_collapse_test import compare, matched_verdict  # noqa: E402

    trace = DissipativeCore(n=60, seed=42).legacy_rad_trace(steps=300,
                                                            burn_in=100)
    Rs = [t[0] for t in trace]
    Ds = [t[2] for t in trace]
    print("  core trace, 300 steps after burn-in:")
    print(f"    R range {min(Rs):.4f} .. {max(Rs):.4f}")
    print(f"    D range {min(Ds):.6f} .. {max(Ds):.6f}")
    r = compare(trace, trials=200, seed=7)
    print("\n  named 17 lenses (the repo's own coefficients):")
    print(f"    minimum pairwise r = {r['named_floor']:.4f}")
    print(f"\n  random coefficients, 17 lenses, {int(r['trials'])} trials:")
    print(f"    median floor = {r['random_median']:.4f}")
    print(f"    range        = {r['random_min']:.4f} .. {r['random_max']:.4f}")
    print(f"    named percentile among random = {r['named_percentile']:.3f}")
    print(f"\n  verdict: {matched_verdict(r['named_percentile'])}")
    check("NEG-7: random coefficients reproduce the correlation floor",
          r["named_percentile"] <= 0.9,
          "the named floor sits inside the random distribution, so the 17 "
          "worldview names carry no information")
    print()


def gies2():
    print("=" * 72)
    print("GIES-2  INDEX PARITY vs CRYSTALLOGRAPHIC SITE TYPE")
    print("=" * 72)
    fcc = [(0, 0, 0), (.5, .5, 0), (.5, 0, .5), (0, .5, .5)]
    atoms = {tuple(round((a + .25) % 1, 4) for a in p) for p in fcc}
    atoms |= {tuple(round(a % 1, 4) for a in p) for p in fcc}
    names = {0: "+t1", 1: "-t3", 2: "-t2", 3: "+t4",
             4: "-t4", 5: "+t2", 6: "+t3", 7: "-t1"}
    print("  idx  bin   position               frac (mod 1)        dir  par  site")
    ok = True
    for i in range(8):
        p = tuple(c / 4.0 for c in CORNERS[i])
        fr = tuple(round(c % 1, 4) for c in p)
        actual = "LATTICE" if fr in atoms else "interstitial"
        predicted = "interstitial" if parity(i) else "LATTICE"
        if actual != predicted:
            ok = False
        flag = "" if actual == predicted else "   <-- MISMATCH"
        print(f"   {i}   {format(i, '03b')}  ({p[0]:+.2f},{p[1]:+.2f},{p[2]:+.2f})"
              f"      ({fr[0]:.2f},{fr[1]:.2f},{fr[2]:.2f})   "
              f"{names[i]:>4}  {parity(i)}   {actual}{flag}")
    print("\n  even parity -> along +t_k, occupied sublattice")
    print("  odd  parity -> along -t_k, empty tetrahedral interstitial")
    check("GIES-2: index parity equals site type, 8/8", ok,
          "a free, exact, single-bit error-detecting code already in the "
          "address space -- and it reads atom vs hole")

    print("\n  NOT(i) = 7-i flips all three bits, hence parity, every time:")
    print("    " + ", ".join(f"{i}->{7 - i}" for i in range(8)))
    check("GIES-3: every NOT crosses sublattices, so every NOT is a Frenkel pair",
          all(frenkel(i, 7 - i) for i in range(8)),
          "~4.75 eV each: the cheapest logic operation is the most expensive "
          "physical event in the crystal")
    print(f"\n  site types: "
          f"{[site_type(i) for i in range(8)].count('lattice')} lattice, "
          f"{[site_type(i) for i in range(8)].count('interstitial')} interstitial")
    print()


def main():
    er2()
    neg7()
    gies2()
    print("=" * 72)
    if FAILED:
        print(f"{len(FAILED)} FALSIFIER(S) FAILED:")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("all falsifiers behaved as registered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
