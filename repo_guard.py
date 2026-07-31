#!/usr/bin/env python3
"""
repo_guard.py -- CC0, stdlib only, phone-buildable, no deps.

STAGE 5.5 OF THE SCAFFOLD: THE NULL STAGE.

Across the archive, five failure classes account for every fatal finding.
Three are mechanically checkable BEFORE a file enters the repo:

  1. NULL HARNESS   does the result survive replacing structure with noise?
                    (killed: the 17-lens isomorphism, the vacuum g_eff
                     assertions, topological attention's run())
  2. SYMMETRY VETO  does the material permit the mechanism at all?
                    (would have caught 9 instances across 6 files, free)
  3. REACH CHECK    is the claimed signal above the instrument floor?
                    (would have caught the 11-order Hall gap, the 500x
                     Er/diamagnetism swamp, the RBS 20-200x shortfall)

The other two -- circular targets and unit errors -- need a human. Checklist
for those at the bottom, and ``human_checklist()`` prints it.

TWO CORRECTIONS TO THE TOOL AS FIRST DRAFTED
--------------------------------------------
1. ``null_harness`` could return SURVIVES for a claim that does not hold. If
   the real metric fails its own criterion and the nulls fail too, the worst
   null pass rate is 0 and the old verdict was SURVIVES. A claim that is simply
   false is not a claim that survived a null test. The verdict is now gated on
   ``real_passes`` and returns CLAIM_FAILS in that case.

2. ``reach`` raised a bare ``KeyError`` for an unknown instrument. It now names
   the available floors, because the point of the tool is to be usable without
   reading it.

WHAT THE FLOORS ARE FOR
-----------------------
Every entry is a number this archive had to derive the hard way. The piezo
figure is the one that corrects an earlier pass of my own: the gauge factor is
``pi_l * E``, and ``pi_l = 71.8e-11 Pa^-1`` is the <110> LONGITUDINAL
coefficient, so it pairs with ``E<110> = 169 GPa``, not ``E<100> = 130 GPa``.
That gives GF = 121, not 93, and dR/R = 12% at 0.1% strain rather than 9%.
"""

import math
import random

__all__ = [
    "null_harness", "report", "VETO", "veto", "veto_report",
    "FLOOR", "reach", "reach_report", "CHECKLIST", "human_checklist",
    "demo", "main",
]

# =====================================================================
# 1. NULL HARNESS
# =====================================================================


def null_harness(metric, real, nulls, passes, name="claim", trials=200):
    """Does the criterion still pass when the structure is removed?

    metric  : callable(obj) -> float
    real    : the structured object your claim is about
    nulls   : list of callables() -> object with the STRUCTURE REMOVED but the
              same shape/type (random, shuffled, degenerate)
    passes  : callable(float) -> bool, your stated success criterion

    Verdict:
      CLAIM_FAILS  the real object does not meet its own criterion
      ARTIFACT     >50% of null draws meet it too
      SUSPECT      >10%
      SURVIVES     the criterion discriminates
    """
    if not nulls:
        raise ValueError("need at least one null generator")
    if trials < 1:
        raise ValueError("need at least one trial")
    m_real = metric(real)
    real_passes = bool(passes(m_real))
    rows = []
    for i, gen in enumerate(nulls):
        vals = [metric(gen()) for _ in range(trials)]
        frac = sum(1 for v in vals if passes(v)) / len(vals)
        vals.sort()
        rows.append({"null": getattr(gen, "__name__", "null%d" % i),
                     "median": vals[len(vals) // 2],
                     "frac_passing": frac})
    worst = max(r["frac_passing"] for r in rows)
    if not real_passes:
        verdict = "CLAIM_FAILS"
    elif worst > 0.5:
        verdict = "ARTIFACT"
    elif worst > 0.1:
        verdict = "SUSPECT"
    else:
        verdict = "SURVIVES"
    return {"name": name, "real": m_real, "real_passes": real_passes,
            "nulls": rows, "worst_null_pass_rate": worst, "verdict": verdict}


def report(res):
    print("NULL HARNESS: %s" % res["name"])
    print("  real metric = %.6f   passes = %s" % (res["real"], res["real_passes"]))
    for r in res["nulls"]:
        print("    %-24s median %12.6f   passes %5.1f%% of the time"
              % (r["null"], r["median"], 100 * r["frac_passing"]))
    print("  VERDICT: %s" % res["verdict"])
    if res["verdict"] == "CLAIM_FAILS":
        print("  -> the real object does not meet its own criterion.")
        print("     nothing about the nulls matters until that is fixed.")
    elif res["verdict"] != "SURVIVES":
        print("  -> the criterion is met by inputs with no structure.")
        print("     the claim is about the arithmetic, not the subject.")
    print()


# =====================================================================
# 2. SYMMETRY / MATERIAL VETO
# =====================================================================

VETO = {
    "silicon": {
        "_facts": "diamond cubic Fd-3m; point group Oh (CENTROSYMMETRIC); "
                  "site symmetry Td; chi = -4e-6 (diamagnetic); "
                  "92.2% Si-28 with I=0; bonding electrons paired",
        "piezoelectric": ("ZERO by inversion symmetry",
                          "electrostriction (even order) IS allowed"),
        "inverse piezo": ("ZERO by inversion symmetry",
                          "photothermal + deformation-potential stress"),
        "pockels": ("ZERO -- chi(2) = 0 in Oh", "plasma dispersion; Kerr chi(3)"),
        "chi2": ("ZERO -- chi(2) = 0 in Oh", "Kerr chi(3), n2 ~ 4.5e-18 m^2/W"),
        "second harmonic": ("ZERO -- forbidden in Oh", "third harmonic (odd order)"),
        "magnetostriction": ("negligible -- diamagnetic",
                             "strain via piezoresistance readout"),
        "magneto-optic": ("negligible Verdet const",
                          "no monolithic Si isolator exists"),
        "faraday": ("negligible Verdet const", "polarization-resolved Raman"),
        "exchange": ("no magnetic order", "elastic coupling via stiffness tensor"),
        "esr": ("no unpaired spins in perfect Si",
                "reads DEFECTS/dopants, not lattice"),
        "spin coherence": ("no intrinsic spin", "P donors in enriched 28Si, <4 K"),
        "thermal anisotropy": ("ZERO -- cubic symmetry, k_ij = k*delta_ij",
                               "none; it is isotropic"),
        "conductivity anisotropy": ("ZERO -- cubic symmetry", "none"),
    },
}


def veto(material, text):
    """Grep a claim or abstract for mechanisms the material forbids."""
    tbl = VETO.get(str(material).lower())
    if not tbl:
        return [("?", "no veto table for %r" % material, "")]
    low = str(text).lower()
    return [(k, v[0], v[1]) for k, v in tbl.items()
            if not k.startswith("_") and k in low]


def veto_report(material, text):
    key = str(material).lower()
    print("SYMMETRY VETO: %s" % material)
    if key in VETO:
        print("  %s" % VETO[key]["_facts"])
    hits = veto(material, text)
    if not hits:
        print("  no forbidden mechanism named. (absence of a hit is not a pass.)")
    for k, why, alt in hits:
        print("  [X] %-24s %s" % (k, why))
        if alt:
            print("      allowed instead: %s" % alt)
    print()
    return hits


# =====================================================================
# 3. REACH CHECK -- signal vs instrument floor
# =====================================================================

FLOOR = {   # (value, unit, note)
    "hall sensor": (2e-5, "T", "A1324 class, ~0.2 G noise"),
    "squid moment": (1e-11, "A.m^2", "commercial MPMS"),
    "raman strain": (1e-4, "strain", "520.7 cm^-1 shift, ~0.02 cm^-1"),
    "rbs areal": (1e13, "cm^-2", "heavy-in-light"),
    "piezoresistive": (1e-5, "dR/R", "4-point probe; GF~121 p-Si <110>"),
    "landauer 300K": (2.87e-21, "J", "kT*ln2; floor for ONE bit erase"),
    "kT 300K": (0.02585, "eV", "thermal energy"),
    "debye-waller theta": (1.9, "deg", "Si bond-angle RMS at 300 K"),
}


#: Case-insensitive lookup. Built from FLOOR rather than duplicating it, so a
#: new floor cannot be reachable under one spelling and not the other.
_FLOOR_LC = {k.lower(): k for k in FLOOR}


def reach(signal, instrument):
    key = _FLOOR_LC.get(str(instrument).lower())
    if key is None:
        raise KeyError("unknown instrument %r; known floors: %s"
                       % (instrument, ", ".join(sorted(FLOOR))))
    if signal < 0:
        raise ValueError("signal must be non-negative")
    f, unit, note = FLOOR[key]
    r = signal / f
    return {"signal": signal, "floor": f, "unit": unit, "ratio": r, "note": note,
            "verdict": "DETECTABLE" if r >= 3 else
                       "MARGINAL" if r >= 1 else "BELOW FLOOR"}


def reach_report(signal, instrument, label=""):
    d = reach(signal, instrument)
    print("REACH: %s  vs  %s" % (label or "signal", instrument))
    print("  signal %.3e %s   floor %.3e %s   ratio %.2e   %s"
          % (d["signal"], d["unit"], d["floor"], d["unit"], d["ratio"], d["note"]))
    print("  VERDICT: %s" % d["verdict"])
    if 0 < d["ratio"] < 1:
        print("  -> short by %.1f orders of magnitude." % (-math.log10(d["ratio"])))
    print()
    return d


# =====================================================================
# HUMAN CHECKLIST -- the two classes no code catches
# =====================================================================

CHECKLIST = """
NOT MECHANISABLE. ask these by hand before committing:

  CIRCULAR TARGET
    [ ] is the target/reference computed from the model being tested?
    [ ] can the numerator be MEASURED on the same device as the
        denominator? if not, it is model-vs-measurement.
    [ ] would an independently-known value work instead?
        (an integer invariant, a handbook constant, a null result)

  UNITS AND ORDERS
    [ ] every number carries a unit, including in tables
    [ ] one quantity has ONE value across the whole repo
    [ ] convert once by hand: eV<->J<->aJ, cm^-1<->N/m, cm^-2<->cm^-3
    [ ] compare each energy to kT*ln2 = 0.0179 eV at 300 K
    [ ] compare each retention claim to tau = tau0*exp(Ea/kT)
    [ ] pair each material coefficient with the modulus for the SAME
        direction (pi_l <110> goes with E<110> = 169 GPa, not E<100>)

  ONE MORE, FREE
    [ ] does the assertion in the test suite have any input that
        would make it FAIL? if not, delete it.
"""


def human_checklist():
    print(CHECKLIST)


# =====================================================================
# DEMO -- run the three checks against findings this archive already made
# =====================================================================

def demo(seed=0):
    rng = random.Random(seed)

    print("=" * 70)
    print("1. NULL HARNESS -- against a claim this archive already killed")
    print("=" * 70)

    def correlation_floor(lenses):
        """Minimum pairwise correlation across a set of scalar lenses."""
        n = len(lenses)
        best = 1.0
        for i in range(n):
            for j in range(i + 1, n):
                a, b = lenses[i], lenses[j]
                ma, mb = sum(a) / len(a), sum(b) / len(b)
                sxy = sum((x - ma) * (y - mb) for x, y in zip(a, b))
                sxx = math.sqrt(sum((x - ma) ** 2 for x in a))
                syy = math.sqrt(sum((y - mb) ** 2 for y in b))
                best = min(best, sxy / (sxx * syy) if sxx * syy > 0 else 0.0)
        return best

    trace = [(rng.random(), rng.random()) for _ in range(120)]

    def make(coeffs):
        return [[c[0] * r + c[1] * a for r, a in trace] for c in coeffs]

    named = make([(1.0, 1.0), (1.2, 0.8), (1.5, 0.7), (0.8, 0.6), (1.1, 1.3)])

    def random_lenses():
        return make([(rng.uniform(0.8, 1.6), rng.uniform(0.6, 1.4))
                     for _ in range(5)])
    random_lenses.__name__ = "random coefficients"

    report(null_harness(correlation_floor, named, [random_lenses],
                        lambda v: v > 0.88, name="17-lens isomorphism (shape of)",
                        trials=120))

    print("=" * 70)
    print("2. SYMMETRY VETO -- against an abstract this archive had to audit")
    print("=" * 70)
    veto_report("silicon",
                "We encode state via magnetostriction and read it out with a "
                "Faraday magneto-optic probe, exploiting the thermal "
                "anisotropy of the [111] direction and an inverse piezo "
                "actuator, with ESR confirming spin coherence.")

    print("=" * 70)
    print("3. REACH CHECK -- three gaps this archive derived the hard way")
    print("=" * 70)
    reach_report(7.96e-17, "hall sensor", "5um cell moment at 50 mT, field at 1 mm")
    reach_report(3.98e-19, "squid moment", "same cell, moment directly")
    reach_report(5e11, "rbs areal", "Er at 1e17 cm^-3 over 50 nm")
    reach_report(0.121, "piezoresistive", "dR/R at 0.1% strain, GF=121")

    print("=" * 70)
    print("4. HUMAN CHECKLIST -- the two classes no code catches")
    print("=" * 70)
    human_checklist()


def main():
    demo()


if __name__ == "__main__":
    main()
