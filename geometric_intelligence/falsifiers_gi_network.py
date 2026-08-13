#!/usr/bin/env python3
"""
falsifiers_gi_network.py -- runnable report for GI-1..6 and GR-1..6.

    python geometric_intelligence/falsifiers_gi_network.py

Stdlib only. Each line asserts what the audit headers in
`geometric_intelligence/network/integrity.py` and `.../resonance.py` record --
for an open defect, that it is still present exactly as described; for one
that was corrected, that the correction is still there. Exits nonzero when any
of them stops holding.

A PASS is not "this code is correct". Fixing GI-1, GI-2, GI-3, GI-4, GI-5,
GR-1, GR-2, GR-3, GR-5 or GR-6 is expected to fail this report, and the
response is to amend the finding, not to delete the check.
"""
import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))

from geometric_intelligence.network import (  # noqa: E402
    GeometricNetwork, IntegrityMonitor, MultiScaleResonance,
    PHI, PHI_INV_9, INTEGRITY_THRESHOLD)
from geometric_intelligence.network import resonance as R  # noqa: E402

CHECKS = []
FAILURES = []


def check(cid, claim, ok, detail=""):
    CHECKS.append(cid)
    print("  %-7s %-54s %s" % (cid, claim, "holds" if ok else "BROKEN"))
    if detail:
        print("          %s" % detail)
    if not ok:
        FAILURES.append(cid)


def chain(reverse=False, n=3, base=0.600):
    """The field guide's timber frame: three braces in ratio 1 : phi : phi^2."""
    net = GeometricNetwork()
    ids = ["brace_short", "brace_mid", "brace_long"][:n]
    for i, x in enumerate(ids):
        net.add_node(x, base * PHI ** i)
    for i in range(len(ids) - 1):
        net.add_edge(ids[i], ids[i + 1], "scale", PHI)
        if reverse:
            net.add_edge(ids[i + 1], ids[i], "scale", 1.0 / PHI)
    return net, ids


def integrity_findings():
    print("INTEGRITY MONITOR")

    # GI-1 ---------------------------------------------------------------
    good = IntegrityMonitor(chain(True)[0])
    good.add_measurement("brace_short", 0.600)
    short = IntegrityMonitor(chain(True)[0])
    short.add_measurement("brace_short", 0.400)          # cut 200 mm short
    pa = good.predict_from("brace_short", "brace_mid")
    pb = short.predict_from("brace_short", "brace_mid")
    check("GI-1", "predictions ignore the measurements entirely",
          pa == pb,
          "brace_short measured 0.600 and 0.400 both predict brace_mid at "
          "%.6f m -- a 200 mm error propagates nowhere" % pa)

    # GI-2 ---------------------------------------------------------------
    m = IntegrityMonitor(chain(True)[0])
    for k, v in (("brace_short", 0.600), ("brace_mid", 0.600 * PHI),
                 ("brace_long", 0.600 * PHI ** 2)):
        m.add_measurement(k, v)
    rep = m.full_report()
    check("GI-2", "the INTEGRITY_THRESHOLD clause is unsatisfiable",
          INTEGRITY_THRESHOLD * 0.5 > 1.0
          and rep["threshold_clause_reachable"] is False
          and rep["integrity_score"] <= 1.0,
          "integrity is a product of two fractions so <= 1.0; the clause "
          "tests it against %.6f" % (INTEGRITY_THRESHOLD * 0.5))

    # GI-3 ---------------------------------------------------------------
    net = GeometricNetwork()
    for x, v in (("a", 1.0), ("b", PHI), ("d", PHI ** 3)):
        net.add_node(x, v)
    net.add_edge("a", "d", "scale", PHI ** 3)          # one route
    net.add_edge("a", "b", "scale", PHI)
    net.add_edge("b", "d", "scale", 2.0)               # a contradicting route
    m = IntegrityMonitor(net)
    m.add_measurement("a", 1.0)
    m.add_measurement("b", PHI)
    m.add_measurement("d", PHI * 2.0)                  # agrees with route two
    r = {q.node_id: q for q in m.check()}["d"]
    check("GI-3", "a design contradiction resolves in the measurement's favour",
          r.trusted and r.residual < 1e-9,
          "routes give %.4f and %.4f; measured %.4f is reported trusted at "
          "residual %.3f%% with no note that a route was chosen"
          % (PHI ** 3, PHI * 2, PHI * 2, r.residual * 100))

    # GI-4 ---------------------------------------------------------------
    def two_paths(f1, f2):
        g = GeometricNetwork()
        for x, v in (("a", 1.0), ("b", PHI), ("x", 2.0)):
            g.add_node(x, v)
        g.add_edge("a", "b", "scale", PHI)
        g.add_edge("b", "a", "scale", 1.0 / PHI)
        g.add_edge("a", "x", "scale", f1)
        g.add_edge("a", "x", "scale", f2)
        mm = IntegrityMonitor(g)
        mm.add_measurement("a", 1.0)
        mm.add_measurement("b", PHI)
        return mm.reconstruct().get("x")
    fwd, rev = two_paths(2.0, 5.0), two_paths(5.0, 2.0)
    check("GI-4", "reconstruct() has no averaging; insertion order decides",
          fwd == 2.0 and rev == 5.0,
          "edges a->x with factors (2,5) give x=%s; the same two as (5,2) "
          "give x=%s. The docstring promises a confidence-weighted average."
          % (fwd, rev))

    # GI-5 ---------------------------------------------------------------
    m = IntegrityMonitor(chain(True)[0])
    m.add_measurement("brace_short", 0.600)
    m.add_measurement("brace_mid", 0.600 * PHI)
    vals = {q.node_id: q.reconstructed for q in m.check()}
    check("GI-5", "IntegrityReport.reconstructed is never assigned",
          all(v is None for v in vals.values()),
          "declared Optional[float] on the dataclass, None on every report")

    # GI-6 ---------------------------------------------------------------
    one = IntegrityMonitor(chain(True)[0])
    one.add_measurement("brace_short", 0.600)
    two = IntegrityMonitor(chain(True)[0])
    two.add_measurement("brace_short", 0.600)
    two.add_measurement("brace_mid", 0.600 * PHI)
    fwd_only = IntegrityMonitor(chain(False)[0])
    for k, v in (("brace_short", 0.600), ("brace_mid", 0.600 * PHI),
                 ("brace_long", 0.600 * PHI ** 2)):
        fwd_only.add_measurement(k, v)
    check("GI-6", "one measurement reconstructs nothing; two reconstruct all",
          one.reconstruct() == {} and len(two.reconstruct()) == 3
          and fwd_only.full_report()["untrusted_nodes"] == ["brace_short"],
          "and a forward-only chain reports brace_short untrusted on "
          "PERFECT measurements, because nothing can predict it")


def resonance_findings():
    print()
    print("MULTI-SCALE RESONANCE")

    # GR-1 ---------------------------------------------------------------
    ok, bad, dead = R.edges_are_monotonic()
    r = MultiScaleResonance()
    dropped = r.band_edges[-2]
    check("GR-1", "band edges are not monotonic; the top band is dead",
          (not ok) and len(bad) == 1,
          "last interval is [%.0f, %.0f) which no f can satisfy; every "
          "component above %.0f Hz is dropped, with f_max asked as %.0f"
          % (dead[0][0], dead[0][1], dropped, r.f_max))

    # GR-2 ---------------------------------------------------------------
    check("GR-2", "bands_per_octave is stored and never read",
          not R.band_resolution_is_honoured(),
          "bands_per_octave=1 and =64 give byte-identical edge lists")

    # GR-3 ---------------------------------------------------------------
    check("GR-3", "the power-law fit includes the peaks it judges",
          R.fit_includes_peaks(),
          'the comment says "non-peak bands"; the guard is band_count[i] > 0')

    # GR-4 ---------------------------------------------------------------
    gate = 1.0 + PHI_INV_9 * 100
    reported = r.detect_injection([1.0], [1.0], [1.0])["threshold_ratio"]
    check("GR-4", "the injection gate is x2.316, and the comment now says so",
          abs(gate - 2.31556) < 1e-4 and abs(reported - gate) < 1e-4,
          "an earlier comment read '> ~1.315x baseline', low by %.2fx"
          % (gate / 1.31556))

    # GR-5 ---------------------------------------------------------------
    far = R.injection_false_alarm_rate()
    check("GR-5", "detect_injection flags %.1f%% of bins on pure noise"
          % (100 * far), 0.10 < far < 0.25,
          "two independent draws of one Rayleigh process, no injection "
          "present; injection_score reads %.3f" % far)

    # GR-6 ---------------------------------------------------------------
    with_b, without_b = R.injection_return_shapes()
    check("GR-6", "detect_injection returns two different shapes",
          "injections" in with_b and "injections" not in without_b,
          "without a baseline the keys are %s -- result['injections'] raises "
          "KeyError for exactly the callers who captured no baseline"
          % ", ".join(without_b))


def core_findings():
    print()
    print("CORE  (reconstructed -- was not in the drop)")
    net = GeometricNetwork()
    net.add_node("a", 0.600)
    raised = []
    for name in ("audit", "correct"):
        try:
            getattr(net, name)()
        except NotImplementedError as exc:
            raised.append("GI-8" in str(exc))
    check("GI-8", "audit() and correct() refuse rather than guess",
          len(raised) == 2 and all(raised),
          "both were named by the drop's README and neither was supplied; a "
          "plausible integrity_score invented here is a number someone cuts "
          "timber against")

    check("GI-9", "the timber-frame arithmetic reproduces",
          abs(600 * PHI - 970.820393) < 1e-5
          and abs(600 * PHI ** 2 - 1570.820393) < 1e-5,
          "600 x phi = %.1f mm, 600 x phi^2 = %.1f mm"
          % (600 * PHI, 600 * PHI ** 2))

    def c_lin(t):
        return 331.3 + 0.606 * t

    def c_exact(t):
        return 331.3 * math.sqrt(1.0 + t / 273.15)
    ratio = c_lin(-40) / c_lin(20)
    check("GI-7", "the speed-of-sound shift is 10.6 pct, not the 6 pct documented",
          abs((1 - ratio) - 0.1058) < 0.002
          and abs(c_lin(-40) - c_exact(-40)) / c_exact(-40) < 0.005,
          "c(+20)=%.1f, c(-40)=%.1f, ratio %.4f; the linear form is within "
          "0.32%% of exact at -40 C" % (c_lin(20), c_lin(-40), ratio))


def main():
    print("=" * 72)
    print("GEOMETRIC INTELLIGENCE / NETWORK  --  GI-1..6, GR-1..6")
    print("  Each line asserts what the audit headers record. Fixing an open")
    print("  defect is EXPECTED to fail here; amend the finding.")
    print("=" * 72)
    integrity_findings()
    resonance_findings()
    core_findings()
    print()
    if FAILURES:
        print("NO LONGER HOLDS: %s" % ", ".join(FAILURES))
        return 1
    print("all %d recorded findings still hold" % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
