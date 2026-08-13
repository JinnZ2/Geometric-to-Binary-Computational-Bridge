#!/usr/bin/env python3
"""
falsifiers_gi_network.py -- runnable report for GI-1..16, GR-1..6, GB-1..5, TMP-1..5, TRD-0..7, TMP-1..5, TRD-0..7.

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
    print("CORE")

    # the good news first ---------------------------------------------------
    import random
    rng = random.Random(0)

    def nautilus(weight=1.0, jitter=False, wjitter=False):
        n = GeometricNetwork()
        for i in range(6):
            n.add_node("c%d" % i, PHI ** i)
        for i in range(5):
            n.add_edge("c%d" % i, "c%d" % (i + 1), "scale", PHI, weight=weight)
            n.add_edge("c%d" % (i + 1), "c%d" % i, "scale", 1 / PHI,
                       weight=weight)
        if jitter:
            for e in n.edges:
                e.factor = rng.uniform(0.2, 5.0)
        if wjitter:
            for e in n.edges:
                e.weight = rng.uniform(0.0, 1.0)
        return n

    real = nautilus().audit()["integrity_score"]
    noise = [nautilus(jitter=True).audit()["integrity_score"]
             for _ in range(200)]
    check("GI-8", "audit() survives the null harness",
          real > 1.9 and sum(noise) / len(noise) < 0.1,
          "phi network %.4f; edge factors randomised, geometry destroyed, "
          "mean %.4f over 200 draws -- the score is responding to the "
          "geometry" % (real, sum(noise) / len(noise)))

    # GI-11 -----------------------------------------------------------------
    n = GeometricNetwork()
    n.add_node("a", 1.0)
    n.add_node("b", 1.0)
    n.add_edge("a", "b", "compose", factor=2.0, offset=-1.0)
    n.add_edge("b", "a", "scale", factor=1.0)
    cyc = n.find_cycles()
    a_t, b_t = n._compose_transforms(cyc[0][0])
    au = n.audit()
    check("GI-11", "cycle closure is probed only at x = 1",
          cyc[0][1] < 1e-12 and au["consistent_cycles"] == 1
          and abs(a_t * 10 + b_t - 10) > 1.0,
          "the map x -> %.0fx %+.0f fixes x=1, so closure error is %.6f and "
          "the cycle counts CONSISTENT -- but it returns %.0f for an input "
          "of 10" % (a_t, b_t, cyc[0][1], a_t * 10 + b_t))

    # GI-12 -----------------------------------------------------------------
    w0 = nautilus(weight=0.0).audit()["integrity_score"]
    w1 = nautilus(weight=1.0).audit()["integrity_score"]
    spread = [nautilus(wjitter=True).audit()["integrity_score"]
              for _ in range(200)]
    check("GI-12", "integrity_score is part geometry, part declaration",
          w0 == 1.0 and w1 == 2.0 and max(spread) - min(spread) > 0.4
          and w1 < INTEGRITY_THRESHOLD,
          "every edge declared weight 0.0 still scores %.4f; weight 1.0 "
          "scores %.4f; randomising weights alone spans %.4f-%.4f, and the "
          "ceiling %.1f never reaches the threshold %.4f"
          % (w0, w1, min(spread), max(spread), w1, INTEGRITY_THRESHOLD))

    # GI-13 -----------------------------------------------------------------
    def corrupted():
        n = nautilus()
        for e in n.edges:
            if e.source == "c2" and e.target == "c3":
                e.factor = 2.0
        return n
    n = corrupted()
    before = n.audit()["integrity_score"]
    n.correct(max_iter=5)
    after5 = n.audit()["integrity_score"]
    n2 = corrupted()
    n2.correct(max_iter=500)
    au2 = n2.audit()
    fwd = [e for e in n2.edges if e.source == "c2" and e.target == "c3"][0]
    rev = [e for e in n2.edges if e.source == "c3" and e.target == "c2"][0]
    check("GI-13", "correct() balances the error instead of removing it",
          before == after5 and au2["consistent_cycles"] == au2["n_cycles"]
          and abs(fwd.factor - PHI) / PHI > 0.10,
          "max_iter=5 leaves integrity %.6f -> %.6f; run to convergence the "
          "injected edge lands at %.6f (%+.1f%% from phi) and its partner at "
          "%.6f (%+.1f%%), and audit reports %d/%d consistent"
          % (before, after5, fwd.factor, 100 * (fwd.factor / PHI - 1),
             rev.factor, 100 * (rev.factor * PHI - 1),
             au2["consistent_cycles"], au2["n_cycles"]))

    # GI-14 -----------------------------------------------------------------
    n = GeometricNetwork()
    for x in ("a", "b", "c"):
        n.add_node(x, 1.0)
    n.add_edge("a", "b", "scale", PHI)
    n.add_edge("b", "a", "scale", 1 / PHI)
    n.add_edge("c", "b", "scale", 0.0)
    m = IntegrityMonitor(n)
    m.add_measurement("a", 1.0)
    m.add_measurement("b", PHI)
    rec = m.reconstruct()
    check("GI-14", "_inverse_apply returns inf where the caller guards on "
          "ZeroDivisionError",
          rec.get("c") == float("inf"),
          "reconstruct() guards with except (ZeroDivisionError, "
          "OverflowError); core returns float('inf'), so inf enters the "
          "reconstruction as a value: c = %s" % rec.get("c"))

    # GI-15 -----------------------------------------------------------------
    p = GeometricNetwork()
    p.add_node("A", 1.0)
    p.add_node("B", 2.0)
    q = GeometricNetwork()
    q.add_node("B", 2.0)
    q.add_node("A", 1.0)
    check("GI-15", "hash() is a hash of insertion order too",
          p.hash() == p.hash() and p.hash() != q.hash(),
          "same two nodes, same values, added in the other order -> %s vs %s; "
          "the docstring says 'topology and relations'" % (p.hash(), q.hash()))

    # GI-16 -----------------------------------------------------------------
    # both bounds, from the two directions that could break them: a network
    # with no consistent cycle (lower) and one with an absurd weight (upper)
    broke = GeometricNetwork()
    broke.add_node("a", 1.0)
    broke.add_node("b", 1.0)
    broke.add_edge("a", "b", "scale", 99.0)
    broke.add_edge("b", "a", "scale", 99.0)
    lo = broke.audit()["integrity_score"]
    hi = nautilus(weight=1e9).audit()["integrity_score"]
    sc = hi
    fx = GeometricNetwork()
    fx.add_node("A", 1.0)
    fx.add_node("B", 2.0)
    fx.add_edge("A", "B", "scale", 2.5)
    fx.add_edge("B", "A", "scale", 0.4)
    check("GI-16", "three of the drop's 20 tests cannot fail",
          lo == 0.0 and abs(hi - INTEGRITY_THRESHOLD) < 1e-5
          and fx.audit()["inconsistent_cycles"] == 0
          and abs(2.5 * 0.4 - 1.0) < 1e-12,
          "test_audit_passes' bounds hold by construction -- a network with "
          "no consistent cycle scores %.4f and weight 1e9 is clamped to "
          "%.4f; test_hash_stable hashes one object twice; test_correct's "
          "fixture is 2.5 x 0.4 = 1.0 exactly, already consistent, so "
          "correct() is never run on an inconsistent network" % (lo, hi))


def bridge_findings():
    print()
    print("FABRICATION BRIDGE")
    import tempfile
    from pathlib import Path
    from geometric_intelligence.network import bridge as B

    # GB-2 ------------------------------------------------------------------
    chain = GeometricNetwork()
    for x, v in (("L1", 0.100), ("L2", 0.162), ("L3", 0.262)):
        chain.add_node(x, v)
    chain.add_edge("L1", "L2", "scale", PHI)
    chain.add_edge("L2", "L3", "scale", PHI)
    claims = B.network_to_claims(chain, scope_prefix="acyclic")
    ic = [c for c in claims if "integrity" in c["scope"]][0]
    check("GB-2", "an acyclic design records an integrity claim of zero",
          ic["value"] == 0.0 and chain.audit()["n_cycles"] == 0,
          "three parts in a correct phi chain, no reverse edges -> "
          "integrity_score %.6f +/- %.0f%% with 0/0 cycles consistent"
          % (ic["value"], 100 * ic["tol_frac"]))

    # GB-1 ------------------------------------------------------------------
    d = tempfile.mkdtemp()
    led = Path(d) / "led.json"
    rot = GeometricNetwork()
    rot.add_node("a", 0.0)
    rot.add_node("b", 0.0)
    rot.add_edge("a", "b", "rotate", factor=0.0)
    B.append_geo_claims(B.network_to_claims(rot, scope_prefix="rot"), led)
    raised = ""
    try:
        B.verify_edge_measurement("rot", 0, 0.1, led)
    except ZeroDivisionError as exc:
        raised = str(exc)
    check("GB-1", "verify_edge_measurement divides by the predicted value",
          bool(raised),
          "a rotate edge at angle 0 is legal and its claim value is 0.0; "
          "delta_pct = 100*(measured/pred - 1) raises %s" % (raised or "-"))

    # GB-3 ------------------------------------------------------------------
    check("GB-3", "the integrity claim's failure text is a different test",
          "below" in ic["failure"] and ic["tol_frac"] == 0.10,
          "the record encodes a +/-%.0f%% band around the value; the text "
          "reads 'below threshold %.4f'"
          % (100 * ic["tol_frac"], INTEGRITY_THRESHOLD))

    # GB-4 ------------------------------------------------------------------
    tols = {c["scope"].rsplit("::", 1)[1].rstrip("0123456789"): c["tol_frac"]
            for c in claims}
    B.append_geo_claims(B.network_to_claims(chain, scope_prefix="tol"), led)
    band = B.verify_edge_measurement("tol", 0, PHI * 1.09, led)
    # GB-5 ------------------------------------------------------------------
    from pathlib import Path as _P
    import inspect as _i
    src = _i.getsource(B.append_geo_claims)
    check("GB-5", "relative ledger path, unlocked read-modify-write",
          not _P(B.LEDGER).is_absolute()
          and "read_text" in src and "flock" not in src and "lock" not in src,
          "LEDGER = %r resolves against the working directory, so running "
          "from the repo root and from fabrication/ writes two ledgers; the "
          "append is read-modify-write with no lock, as at the 23 sites in "
          "fabrication/" % str(B.LEDGER))

    check("GB-4", "three unsourced tolerances, and drift is (1+t)^2 not 2t",
          set(tols.values()) >= {0.05, 0.10} and band["verdict"] == "drift",
          "edge 0.05, cycle %.4f, integrity 0.10; drift band is "
          "[p(1-t)^2, p(1+t)^2] = [%.4f, %.4f] of p, not [1-2t, 1+2t]"
          % (PHI_INV_9, 0.95 ** 2, 1.05 ** 2))

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


def temperature_findings():
    print()
    print("TEMPERATURE COMPENSATION  (fabrication/temperature.py)")
    from fabrication import temperature as T
    import inspect

    # TMP-5 (the positive one) -----------------------------------------------
    worst = max(abs(T.c_air(t) / (331.3 * math.sqrt(1 + t / 273.15)) - 1)
                for t in range(-50, 51))
    check("TMP-5", "c_air is within 0.6 pct of exact over its range",
          worst < 0.006,
          "max error %.2f%% over -50..+50 C against 331.3*sqrt(1+T/273.15); "
          "the claim of validity is true and now carries the number"
          % (100 * worst))

    # TMP-1 ------------------------------------------------------------------
    dT = 40.0
    code = math.sqrt(T.k_correct(1.0, 15.0 + dT, 15.0)) - 1.0
    physics = 0.5 * (-2.4e-4 * dT)          # dE/E for steel, f ~ sqrt(E)
    check("TMP-1", "the mechanical correction is ~20x small and inverted",
          code * physics < 0 and abs(physics / code) > 10,
          "at dT=+40 C this module gives df/f = %+.4f%%, the modulus term "
          "gives %+.3f%% -- %.0fx larger, opposite sign. k_correct's own "
          "docstring says 'dominant effect is length'."
          % (100 * code, 100 * physics, abs(physics / code)))

    # TMP-2 ------------------------------------------------------------------
    refs = {}
    for f in (T.thermal_expand, T.r_correct, T.c_correct, T.l_correct,
              T.k_correct, T.helmholtz_f_correct, T.acoustic_f_correct,
              T.normalize_measurement):
        p = inspect.signature(f).parameters.get("ref_temp_c")
        if p is not None:
            refs.setdefault(p.default, []).append(f.__name__)
    bias = 0.00393 * 5.0
    check("TMP-2", "two reference temperatures in one module, and a crossing",
          set(refs) == {20.0, 15.0},
          "%s default to 20.0 C, %s to 15.0 C; normalize_measurement passes "
          "its 15.0 into r_correct, whose TCR is the copper value at 20 C -- "
          "a %.1f%% bias on every electrical normalisation"
          % (len(refs[20.0]), len(refs[15.0]), 100 * bias))

    # TMP-3 ------------------------------------------------------------------
    a = T.acoustic_f_correct(1000.0, -40.0)
    h = T.helmholtz_f_correct(1000.0, -40.0)
    check("TMP-3", "two corrections for one physics, docstrings swapped",
          abs(a - h) > 1.0 and "linear approximation" in
          T.helmholtz_f_correct.__doc__,
          "1000 Hz at -40 C -> %.2f (linear c ratio) vs %.2f (exact sqrt), "
          "%.2f%% apart; the exact one is the one whose docstring says "
          "'simplified linear approximation'" % (a, h, 100 * abs(a - h) / h))

    # TMP-4 ------------------------------------------------------------------
    err100 = T.mu_water(100.0) / 2.82e-4 - 1.0
    check("TMP-4", "mu_water has no stated range and freezes below 0 C",
          abs(err100) > 0.4 and T.mu_water(-40.0) == T.mu_water(-1.0),
          "%.0f%% low at 100 C against tabulated 2.82e-4 Pa*s, and every "
          "T < 0 returns the same 1.79e-3 -- the 0 C value, for water that "
          "is ice" % (100 * err100))


def trend_findings():
    print()
    print("TREND DETECTION  (geometric_intelligence/network/trend.py)")
    from geometric_intelligence.network import trend as TR
    from pathlib import Path
    fix = Path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "tests", "fixtures",
                            "measurements_drift_fixture.json"))

    # the headline ------------------------------------------------------------
    res = TR.detect_all_trends(fix)
    drifting = [r for r in res.values() if r.verdict_trend == "failed"]
    noisy = [r for r in res.values() if r.verdict_trend == "noisy"]
    check("TRD-0", "the only failure prediction belongs to the stable channel",
          all(r.predicted_fail_days is None for r in drifting)
          and any(r.predicted_fail_days for r in noisy),
          "%d failing scopes report fail_in=None; the one with a number is "
          "%s at %.1f days from an R2 of %.3f"
          % (len(drifting), noisy[0].scope.split("::")[-1],
             noisy[0].predicted_fail_days, noisy[0].r_squared))

    # TRD-1 -------------------------------------------------------------------
    down = [{"ts": i * 86400, "measured": 10.0 - 0.5 * i,
             "predicted": 10.0, "tol_frac": 0.05} for i in range(20)]
    tr = TR.analyze_scope_trend("down", down)
    check("TRD-1", "the fail band is one-sided",
          tr.verdict_trend != "failed" and tr.current_value < 10.0 * 0.9,
          "a value fallen to %.2f against a claim of 10.0 +/- 5%% is reported "
          "'%s'; fail_threshold = predicted*(1 + 2*tol) = %.2f is an upper "
          "edge only" % (tr.current_value, tr.verdict_trend, 10.0 * 1.1))

    # TRD-2 -------------------------------------------------------------------
    above = [{"ts": i * 86400, "measured": 30.0 - 1.0 * i,
              "predicted": 10.0, "tol_frac": 0.05} for i in range(10)]
    tr = TR.analyze_scope_trend("above", above)
    check("TRD-2", "the negative-slope branch counts days to STOP failing",
          tr.verdict_trend == "failed" and tr.predicted_fail_days is not None,
          "a value falling from 30.0, failing throughout, reports "
          "predicted_fail_days = %.1f -- the time to re-enter the band"
          % tr.predicted_fail_days)

    # TRD-3 -------------------------------------------------------------------
    pair = [{"ts": 0, "measured": 10.0, "predicted": 10.0, "tol_frac": 0.05},
            {"ts": 86400, "measured": 10.0001, "predicted": 10.0,
             "tol_frac": 0.05}]
    tr = TR.analyze_scope_trend("pair", pair)
    check("TRD-3", "two points always give R2 = 1.0 and a trend verdict",
          tr.r_squared == 1.0 and tr.verdict_trend in ("drifting",
                                                       "accelerating"),
          "readings 0.0001 apart classify as '%s' at R2 %.3f; the residual "
          "sum of squares is zero for any two points"
          % (tr.verdict_trend, tr.r_squared))

    # TRD-4 -------------------------------------------------------------------
    import inspect as _insp
    _src = _insp.getsource(TR.analyze_scope_trend)
    check("TRD-4", "the stable threshold has units",
          "abs(slope) < 1e-6" in _src and "/ pred" not in _src
          and "relative" not in _src,
          "abs(slope) < 1e-6 is compared against ohms/day, hertz/day and "
          "kelvin/day alike: 1e-5/day is %.3f%% per year of a 10-ohm claim "
          "and %.0f%% per year of a 0.001-unit one"
          % (100 * 1e-5 * 365 / 10.0, 100 * 1e-5 * 365 / 0.001))

    # TRD-5 / TRD-6 -----------------------------------------------------------
    tm = TR.cross_domain_correlation(fix, "thermal", "mechanical")
    default = TR.cross_domain_correlation(fix)
    import json as _json
    raw = _json.loads(fix.read_text())
    for m in raw:
        if m["scope"].startswith("fab::thermal"):
            m["ts"] += 0.001
    jit = Path("/tmp/_trd_jitter.json")
    jit.write_text(_json.dumps(raw))
    check("TRD-5", "any two monotone drifts correlate at |r| ~ 1",
          bool(tm) and abs(tm[0]["correlation"]) > 0.999,
          "thermal x mechanical -- two straight ramps with no stated physical "
          "link -- give r = %.4f over %d points, against a gate of 0.6 with "
          "no null" % (tm[0]["correlation"], tm[0]["n_common"]))
    check("TRD-6", "and the defaults never compare that pair",
          not default and not TR.cross_domain_correlation(jit, "thermal",
                                                          "mechanical"),
          "defaults are electrical x thermal, which returns nothing; and "
          "shifting one channel's timestamps by 1 ms drops the overlap to "
          "zero, because it is an exact float set intersection")

    # TRD-7 -------------------------------------------------------------------
    check("TRD-7", "LEDGER is a relative path",
          not Path(TR.LEDGER).is_absolute(),
          "LEDGER = %r, like the 24 sites in bridge.py and fabrication/"
          % str(TR.LEDGER))

def main():
    print("=" * 72)
    print("GEOMETRIC INTELLIGENCE / NETWORK  --  GI-1..16, GR-1..6, GB-1..5, TMP-1..5, TRD-0..7")
    print("  Each line asserts what the audit headers record. Fixing an open")
    print("  defect is EXPECTED to fail here; amend the finding.")
    print("=" * 72)
    integrity_findings()
    resonance_findings()
    core_findings()
    bridge_findings()
    temperature_findings()
    trend_findings()
    print()
    if FAILURES:
        print("NO LONGER HOLDS: %s" % ", ".join(FAILURES))
        return 1
    print("all %d recorded findings still hold" % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
