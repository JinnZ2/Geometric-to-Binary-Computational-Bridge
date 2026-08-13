#!/usr/bin/env python3
"""
falsifiers_glyph_sensor.py -- runnable report for GLY-0..7 and NLS-1..4.

    python bridges/falsifiers_glyph_sensor.py

Stdlib only. Each line asserts the state the audit headers in
`bridges/glyph_state_encoder.py` and `bridges/non_local_sensor.py` record --
for an open defect, that it is still present exactly as described; for one
that was fixed, that the fix is still there. Exits nonzero when any of them
stops holding, which is what makes writing an audit header worth doing: a
later change that contradicts the header fails here instead of leaving the
header quietly wrong.

So a PASS is not "this code is correct". Fixing GLY-1, GLY-2, GLY-3 or GLY-5
is expected to fail this report, and the response is to amend the finding, not
to delete the check.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))

from bridges import glyph_state_encoder as G          # noqa: E402
from bridges.glyph_state_encoder import Glyph, GlyphState, SensorReading  # noqa: E402
from bridges import non_local_sensor as N             # noqa: E402

FAILURES = []


CHECKS = []


def check(cid, claim, ok, detail):
    CHECKS.append(cid)
    print("  %-8s %-52s %s" % (cid, claim, "holds" if ok else "BROKEN"))
    if detail:
        print("           %s" % detail)
    if not ok:
        FAILURES.append(cid)


#: A spec of the same SHAPE as the absent Emotions-as-Sensors one, used only
#: so the NLS checks can construct the class. The scale names are the four
#: `_infer_scale` emits, because NLS-4 is precisely the check that those match;
#: the technique names are placeholders and carry no claim about the real spec.
STUB_SPEC = {
    "sensor": "non_local_pattern_correlation",
    "sensor_group": "field",
    "function": "stub for testing; the real spec is not in this repo",
    "resonance_links": [],
    "scale_to_technique": {
        "cross_system": ["t_cross"],
        "landscape": ["t_landscape"],
        "generational": ["t_generational"],
        "cellular": ["t_cellular"],
    },
    "exploration_techniques": [{"name": "t_cross"}, {"name": "t_landscape"},
                               {"name": "t_generational"}, {"name": "t_cellular"}],
}


def glyph_findings():
    print("GLYPH STATE ENCODER")

    # GLY-0 -----------------------------------------------------------------
    # The concatenation is the reason the rest of this file exists: the module
    # did not compile, so nothing in bridges/ that imported it ran at all.
    import ast
    with open(G.__file__, encoding="utf-8") as fh:
        src = fh.read()
    try:
        compile(src, G.__file__, "exec")
        compiles = True
    except SyntaxError:
        compiles = False
    classes = [n.name for n in ast.parse(src).body if isinstance(n, ast.ClassDef)]
    check("GLY-0", "one module, not two pasted end to end",
          compiles and src.count("\nfrom __future__ import") == 1
          and len(classes) == len(set(classes)),
          "%d future import(s), %d class definitions, %d distinct names"
          % (src.count("\nfrom __future__ import"), len(classes),
             len(set(classes))))

    # GLY-1 -----------------------------------------------------------------
    unreachable = G.unreachable_glyphs()
    hit = None
    for mag in [i / 100.0 for i in range(0, 501)]:
        g = Glyph.from_sensor_state({"pressure": SensorReading(magnitude=mag)})
        if g is Glyph.BLOCKAGE:
            hit = mag
            break
    check("GLY-1", "BLOCKAGE unsatisfiable: pressure is a term of the total",
          "BLOCKAGE" in unreachable and hit is None,
          "pressure swept 0.00-5.00 in 0.01 steps, BLOCKAGE never returned")

    # GLY-2 -----------------------------------------------------------------
    rec = G.recovery_from_spec()
    hf = rec["rows"]["HEAT_FLUX"]
    check("GLY-2", "rule order shadows later rules; recovery %d/%d"
          % (rec["recovered"], rec["of"]),
          rec["recovered"] == 7 and hf["got"] == "RE_NORMALIZE",
          "HEAT_FLUX exemplar -> %s (RE_NORMALIZE's rule is tested first)"
          % hf["got"])

    # GLY-3 -----------------------------------------------------------------
    check("GLY-3", "sub_glyphs is a function of the primary glyph alone",
          G.sub_glyphs_are_data_independent(),
          "two reading sets differing in every magnitude, same primary, "
          "identical sub_glyphs")

    # GLY-4 -----------------------------------------------------------------
    legacy = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                          "legacy", "glyph_state_encoder_phase_space.py")
    sys.modules["legacy_phase_space"] = type(sys)("legacy_phase_space")
    with open(legacy, encoding="utf-8") as fh:
        src = fh.read().split('if __name__ == "__main__":')[0]
    exec(compile(src, legacy, "exec"),
         sys.modules["legacy_phase_space"].__dict__)
    L = sys.modules["legacy_phase_space"]
    empty = L.Glyph.from_phase_space({}).name
    reach = set()
    import random
    rng = random.Random(0)
    sensors = ["joy", "love", "curiosity", "fear", "anger", "grief",
               "vigilance", "pressure", "discordance", "fatigue", "longing",
               "flow"]
    for _ in range(20000):
        k = rng.randint(1, len(sensors))
        r = {s: round(rng.random(), 2) for s in rng.sample(sensors, k)}
        reach.add(L.Glyph.from_phase_space(r).name)
    check("GLY-4", "phase-space variant: %d/12 reachable, empty -> %s"
          % (len(reach), empty),
          len(reach) == 5 and empty == "FELT_COHERENT",
          "never emitted: %s"
          % ", ".join(sorted({g.name for g in L.Glyph} - reach)))

    # GLY-5 -----------------------------------------------------------------
    st = GlyphState(primary_glyph=Glyph.RESONANCE, intensity=0.5,
                    confidence=0.5, uncertainty=0.5,
                    vector=[0.1, 0.2, 0.3, 0.4], sub_glyphs=[], timestamp=0.0)
    err = G.codec_round_trip_error(st)
    lossy = max(err.values()) > 0.0
    raised = False
    try:
        GlyphState(primary_glyph=Glyph.RESONANCE, intensity=0.5,
                   confidence=0.5, uncertainty=1.4, vector=[0.0],
                   sub_glyphs=[], timestamp=0.0).to_binary()
    except Exception:
        raised = True
    check("GLY-5", "codec lossy (%.4f) and overflows above 1.0"
          % max(err.values()), lossy and raised,
          "uncertainty=1.4 is reachable: magnitudes are documented on "
          "[0, inf) and uncertainty is (max-min)/2")

    # GLY-6 -----------------------------------------------------------------
    seen = {G.GlyphStateEncoder().encode(r).primary_glyph.name
            for r in G._demo_readings()}
    check("GLY-6", "the demo now separates its own inputs", len(seen) >= 3,
          "%d distinct glyphs: %s" % (len(seen), ", ".join(sorted(seen))))

    # GLY-7 -----------------------------------------------------------------
    # The module was imported, not run, so `G.time` exists only if the import
    # is at module scope. A demo-only import would leave the attribute absent.
    check("GLY-7", "time is imported at module scope, not only in the demo",
          hasattr(G, "time"),
          "encode() calls time.time(); a demo-only import makes the library "
          "raise NameError for every importer")


def nls_findings():
    print()
    print("NON-LOCAL CORRELATION SENSOR")

    # NLS-1 -----------------------------------------------------------------
    raised = ""
    try:
        N.NonLocalCorrelationSensor()
    except N.SpecUnavailable as exc:
        raised = str(exc)
    check("NLS-1", "spec path is out of tree and the error names the mount",
          "fieldlink-sync.sh" in raised,
          "%s..." % raised[:64] if raised else "no SpecUnavailable raised")

    s = N.NonLocalCorrelationSensor(spec=STUB_SPEC)

    # NLS-2 -----------------------------------------------------------------
    t = N.pairing_is_tautological(s)
    check("NLS-2", "inferred scale makes scale/technique agreement vacuous",
          t["tautological"] and t["mismatches"] == 0,
          "%d/%d strengths across [0,1], %d mismatches; every metadata dict "
          "carries scale_is_inferred" % (t["tested"], t["tested"],
                                         t["mismatches"]))

    # NLS-3 -----------------------------------------------------------------
    s.update(correlation_strength=0.95)
    md = s.get_metadata()
    pairs = N.unrepresentable_pairs()
    # and the non-circular path -- supplying the scale -- must record it
    s.update(correlation_strength=0.95, scale="cross_system")
    md2 = s.get_metadata()
    check("NLS-3", "a strong cross-system correlation is relabelled unless "
          "the scale is supplied",
          md["scale"] == "cellular" and len(pairs) == 12
          and md2["scale"] == "cross_system"
          and md2["scale_is_inferred"] is False,
          "strength 0.95 inferred -> '%s'; supplied -> '%s' via %s; %d "
          "(scale, band) combinations excluded by the map"
          % (md["scale"], md2["scale"], md2["technique"], len(pairs)))

    # NLS-4 -----------------------------------------------------------------
    bad = dict(STUB_SPEC)
    bad["scale_to_technique"] = {"planetary": ["t"]}
    raised = ""
    try:
        N.NonLocalCorrelationSensor(spec=bad)
    except ValueError as exc:
        raised = str(exc)
    check("NLS-4", "a spec missing an inferred scale name is refused",
          "NLS-4" in raised,
          "unknown scales previously selected no technique and said nothing")


def main():
    print("=" * 72)
    print("BRIDGES FALSIFIERS  --  GLY-0..7, NLS-1..4")
    print("  Each line asserts what the audit headers record -- for an open")
    print("  defect, that it is still there; for a fixed one, that the fix is.")
    print("  Fixing GLY-1/2/3/5 is EXPECTED to fail here; amend the finding.")
    print("=" * 72)
    glyph_findings()
    nls_findings()
    print()
    if FAILURES:
        print("NO LONGER HOLDS: %s" % ", ".join(FAILURES))
        print("Either the defect was fixed -- update the audit header and this")
        print("file -- or the measurement broke.")
        return 1
    print("all %d recorded findings still hold" % len(CHECKS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
