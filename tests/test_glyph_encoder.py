"""GLY-0..7 and NLS-1..4: the glyph encoder and the non-local sensor.

Stdlib only. Two things this file is guarding against, neither of which is a
wrong number:

  * A finding that quietly stops being true. Most of these assert a DEFECT --
    BLOCKAGE unreachable, sub_glyphs carrying no data, recovery at 7/12. If
    someone fixes one, the assertion fails, and the fix is to amend the audit
    header in `bridges/glyph_state_encoder.py` so it stops describing code
    that no longer exists.

  * The measurement being circular. `recovery_from_spec()` scores the rule
    ladder against exemplars derived from the SUPERSEDED half's declared
    phase_space -- a specification written separately from the ladder. If
    those exemplars ever came from the ladder's own thresholds the score would
    be P-SELF-SUPPLIED-FALSIFIER, so there is a test that they do not.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from bridges import glyph_state_encoder as G  # noqa: E402
from bridges import non_local_sensor as N  # noqa: E402
from bridges.glyph_state_encoder import (  # noqa: E402
    Glyph, GlyphState, GlyphStateEncoder, SensorReading)

ROOT = os.path.join(os.path.dirname(__file__), "..")

STUB_SPEC = {
    "sensor": "non_local_pattern_correlation",
    "sensor_group": "field",
    "function": "stub; the real spec lives in Emotions-as-Sensors",
    "resonance_links": [],
    "scale_to_technique": {"cross_system": ["t_cross"],
                           "landscape": ["t_landscape"],
                           "generational": ["t_generational"],
                           "cellular": ["t_cellular"]},
    "exploration_techniques": [{"name": "t_cross"}, {"name": "t_landscape"},
                               {"name": "t_generational"},
                               {"name": "t_cellular"}],
}


def R(**kw):
    return {k: SensorReading(magnitude=v, confidence=1.0)
            for k, v in kw.items()}


class TestFileIsOneModule(unittest.TestCase):
    """GLY-0. The reason any of this exists: the file arrived as two pasted copies
    and did not compile, so nothing in bridges/ that imported it worked."""

    def setUp(self):
        with open(os.path.join(ROOT, "bridges", "glyph_state_encoder.py"),
                  encoding="utf-8") as fh:
            self.src = fh.read()

    def test_it_compiles(self):
        compile(self.src, "glyph_state_encoder.py", "exec")

    def test_exactly_one_future_import(self):
        self.assertEqual(self.src.count("\nfrom __future__ import"), 1)

    def test_each_public_class_is_defined_once(self):
        import ast
        names = [n.name for n in ast.parse(self.src).body
                 if isinstance(n, ast.ClassDef)]
        self.assertEqual(len(names), len(set(names)), msg=names)

    def test_the_superseded_half_is_in_legacy_and_still_compiles(self):
        p = os.path.join(ROOT, "legacy",
                         "glyph_state_encoder_phase_space.py")
        self.assertTrue(os.path.exists(p))
        with open(p, encoding="utf-8") as fh:
            compile(fh.read(), p, "exec")

    def test_legacy_readme_records_the_cause(self):
        with open(os.path.join(ROOT, "legacy", "README.md"),
                  encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("glyph_state_encoder_phase_space.py", txt)
        self.assertIn("GLY-4", txt)


class TestGly1Unreachable(unittest.TestCase):

    def test_blockage_is_reported_unreachable_with_a_reason(self):
        u = G.unreachable_glyphs()
        self.assertIn("BLOCKAGE", u)
        self.assertIn("total_magnitude", u["BLOCKAGE"])

    def test_no_pressure_value_produces_blockage(self):
        for i in range(0, 501):
            g = Glyph.from_sensor_state(R(pressure=i / 100.0))
            self.assertIsNot(g, Glyph.BLOCKAGE)

    def test_no_reading_set_at_all_produces_blockage(self):
        import random
        rng = random.Random(7)
        keys = ["joy", "love", "curiosity", "fear", "anger", "grief",
                "vigilance", "pressure", "discordance", "fatigue", "longing",
                "flow"]
        for _ in range(5000):
            r = {k: SensorReading(magnitude=round(rng.random(), 2),
                                  confidence=round(rng.random(), 2))
                 for k in rng.sample(keys, rng.randint(1, len(keys)))}
            self.assertIsNot(Glyph.from_sensor_state(r), Glyph.BLOCKAGE)

    def test_only_the_provable_case_is_listed(self):
        """A glyph that merely never turned up in sampling must not appear
        here -- 'not seen in N draws' is a statement about the draws."""
        self.assertEqual(sorted(G.unreachable_glyphs()), ["BLOCKAGE"])


class TestGly2RuleOrder(unittest.TestCase):

    def test_recovery_is_seven_of_twelve(self):
        rec = G.recovery_from_spec()
        self.assertEqual(rec["of"], 12)
        self.assertEqual(rec["recovered"], 7)

    def test_heat_flux_is_shadowed_by_re_normalize(self):
        rec = G.recovery_from_spec()
        self.assertEqual(rec["rows"]["HEAT_FLUX"]["got"], "RE_NORMALIZE")

    def test_the_shadowing_is_precedence_not_logic(self):
        """The HEAT_FLUX exemplar satisfies RE_NORMALIZE's own rule, so the
        ladder is right to match it -- it is the ORDER that decides, and the
        order is nowhere declared."""
        ex = G._spec_exemplar(G.PHASE_SPACE_SPEC["HEAT_FLUX"])
        self.assertGreater(ex["discordance"], 0.4)
        self.assertGreater(ex["fatigue"], 0.3)
        self.assertGreater(ex["pressure"], 0.3)

    def test_the_empty_reading_set_is_void(self):
        self.assertIs(Glyph.from_sensor_state({}), Glyph.VOID)

    def test_a_dead_channel_does_not_read_as_the_healthy_state(self):
        """The one classification error worth designing against, and the
        superseded half made it."""
        self.assertIsNot(Glyph.from_sensor_state({}), Glyph.FELT_COHERENT)


class TestGly2NotCircular(unittest.TestCase):
    """The exemplars must come from a specification the classifier did not
    author, or the score measures nothing."""

    def test_the_spec_matches_the_superseded_half_verbatim(self):
        p = os.path.join(ROOT, "legacy",
                         "glyph_state_encoder_phase_space.py")
        with open(p, encoding="utf-8") as fh:
            src = fh.read()
        for name, conds in G.PHASE_SPACE_SPEC.items():
            self.assertIn(name, src)
            for c in conds:
                self.assertIn('"%s"' % c, src,
                              msg="%s: %s not in the superseded half" %
                                  (name, c))

    def test_the_spec_covers_every_glyph(self):
        self.assertEqual(sorted(G.PHASE_SPACE_SPEC),
                         sorted(g.name for g in Glyph))

    def test_exemplars_are_built_from_the_spec_not_the_ladder(self):
        ex = G._spec_exemplar(["joy", "low_fear", "high_anger",
                               "balanced_active"])
        self.assertEqual(ex, {"joy": 0.70, "fear": 0.05, "anger": 0.85})

    def test_the_two_null_tokens_give_the_empty_set(self):
        self.assertEqual(G._spec_exemplar(["inactive", "zero_intensity"]), {})


class TestGly3SubGlyphs(unittest.TestCase):

    def test_sub_glyphs_do_not_depend_on_the_reading(self):
        self.assertTrue(G.sub_glyphs_are_data_independent())

    def test_the_fixture_lands_on_one_primary_or_says_so(self):
        enc = GlyphStateEncoder()
        a = enc.encode(R(joy=0.9, love=0.9, curiosity=0.9))
        b = enc.encode(R(joy=0.35, love=0.25, grief=0.15))
        self.assertEqual(a.primary_glyph, b.primary_glyph)

    def test_a_constant_travels_into_the_wire_format(self):
        """sub_glyphs is packed into to_binary() and fed to entropy(), so the
        constant is not inert -- it inflates both."""
        enc = GlyphStateEncoder()
        st = enc.encode(R(joy=0.9, love=0.9, curiosity=0.9))
        self.assertTrue(st.sub_glyphs)
        self.assertGreater(len(st.to_binary()),
                           len(GlyphState(st.primary_glyph, st.intensity,
                                          st.confidence, st.vector, [],
                                          st.uncertainty,
                                          st.timestamp).to_binary()))


class TestGly4PhaseSpaceVariant(unittest.TestCase):

    def setUp(self):
        p = os.path.join(ROOT, "legacy",
                         "glyph_state_encoder_phase_space.py")
        mod = type(sys)("legacy_phase_space_t")
        sys.modules["legacy_phase_space_t"] = mod
        with open(p, encoding="utf-8") as fh:
            src = fh.read().split('if __name__ == "__main__":')[0]
        exec(compile(src, p, "exec"), mod.__dict__)
        self.L = mod

    def test_the_empty_reading_set_returns_felt_coherent(self):
        self.assertEqual(self.L.Glyph.from_phase_space({}).name,
                         "FELT_COHERENT")

    def test_only_five_of_twelve_glyphs_are_reachable(self):
        import random
        rng = random.Random(0)
        keys = ["joy", "love", "curiosity", "fear", "anger", "grief",
                "vigilance", "pressure", "discordance", "fatigue", "longing",
                "flow"]
        seen = set()
        for _ in range(20000):
            r = {s: round(rng.random(), 2)
                 for s in rng.sample(keys, rng.randint(1, len(keys)))}
            seen.add(self.L.Glyph.from_phase_space(r).name)
        self.assertEqual(len(seen), 5)
        self.assertNotIn("VOID", seen)

    def test_the_cause_is_the_condition_guard(self):
        """Every predicate branch sits behind `if condition in readings`, and
        the predicates are never reading keys. Supplying one AS a key reaches
        the branch, which is the proof that the guard is what blocks it."""
        blocked = self.L.Glyph.from_phase_space({"vigilance": 0.9})
        reached = self.L.Glyph.from_phase_space({"vigilance": 0.9,
                                                 "high_boundary": 1.0,
                                                 "low_engagement": 1.0})
        self.assertNotEqual(blocked.name, "CONTAINMENT")
        self.assertEqual(reached.name, "CONTAINMENT")

    def test_nothing_in_the_tree_imports_it(self):
        """legacy/ is provenance. It is importable -- `legacy` resolves as a
        namespace package, so there is no import error to rely on -- which
        makes 'nothing imports it' a thing to check rather than assume. The
        falsifier reaches it by exec on the path, deliberately, so that a
        real import statement anywhere is a finding."""
        hits = []
        for base, dirs, files in os.walk(ROOT):
            dirs[:] = [d for d in dirs
                       if d not in (".git", "__pycache__", "node_modules")]
            for f in files:
                if not f.endswith(".py"):
                    continue
                p = os.path.join(base, f)
                rel = os.path.relpath(p, ROOT)
                if (rel.startswith("legacy" + os.sep) or
                        os.path.realpath(p) == os.path.realpath(__file__)):
                    continue          # this file carries the patterns it hunts
                with open(p, encoding="utf-8", errors="replace") as fh:
                    src = fh.read()
                if ("import legacy" in src or
                        "from legacy" in src):
                    hits.append(os.path.relpath(p, ROOT))
        self.assertEqual(hits, [])


class TestGly5Codec(unittest.TestCase):

    def _state(self, **kw):
        base = dict(primary_glyph=Glyph.RESONANCE, intensity=0.5,
                    confidence=0.5, uncertainty=0.5, vector=[0.1, 0.2],
                    sub_glyphs=[], timestamp=0.0)
        base.update(kw)
        return GlyphState(**base)

    def test_the_glyph_itself_round_trips_exactly(self):
        for g in Glyph:
            st = self._state(primary_glyph=g)
            self.assertIs(GlyphState.from_binary(st.to_binary()).primary_glyph,
                          g)

    def test_the_scalar_fields_do_not(self):
        err = G.codec_round_trip_error(self._state(intensity=0.5))
        self.assertGreater(err["intensity"], 0.0)
        self.assertLess(err["intensity"], 1 / 255.0)

    def test_uncertainty_above_one_overflows(self):
        with self.assertRaises(Exception):
            self._state(uncertainty=1.4).to_binary()

    def test_that_overflow_is_reachable_from_a_legal_reading(self):
        """SensorReading.magnitude is documented on [0, inf) and uncertainty
        is (max - min) / 2, so magnitudes of 3.0 and 0.0 get there."""
        enc = GlyphStateEncoder()
        st = enc.encode(R(anger=3.0, joy=0.1))
        self.assertGreater(st.uncertainty, 1.0)
        with self.assertRaises(Exception):
            st.to_binary()

    def test_the_audit_header_says_the_codec_is_lossy(self):
        flat = " ".join(G.__doc__.split())
        self.assertIn("GLY-5", flat)
        self.assertIn("lossy", flat)


class TestGly6And7(unittest.TestCase):

    def test_the_demo_separates_its_own_inputs(self):
        enc = GlyphStateEncoder()
        seen = {enc.encode(r).primary_glyph.name for r in G._demo_readings()}
        self.assertGreaterEqual(len(seen), 3)

    def test_the_demo_returns_nonzero_when_it_does_not(self):
        """The failure the old demo could not express: it printed
        'operational' after classifying six VOIDs."""
        real = G._demo_readings
        G._demo_readings = lambda: [R(joy=0.6, love=0.5, curiosity=0.4),
                                    R(joy=0.7, love=0.6, curiosity=0.5)]
        try:
            import io
            buf, old = io.StringIO(), sys.stdout
            sys.stdout = buf
            try:
                code = G.main()
            finally:
                sys.stdout = old
            self.assertEqual(code, 1)
            self.assertIn("not separating", buf.getvalue())
        finally:
            G._demo_readings = real

    def test_the_demo_passes_on_the_real_inputs(self):
        import io
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            code = G.main()
        finally:
            sys.stdout = old
        self.assertEqual(code, 0)

    def test_encode_works_on_a_plain_import(self):
        """GLY-7. time was imported only inside __main__, so every importer
        got NameError on the first encode while the demo passed."""
        self.assertTrue(hasattr(G, "time"))
        GlyphStateEncoder().encode(R(joy=0.6, love=0.5, curiosity=0.4))


class TestNls1SpecPath(unittest.TestCase):

    def test_construction_without_the_sibling_repo_names_the_mount(self):
        with self.assertRaises(N.SpecUnavailable) as ctx:
            N.NonLocalCorrelationSensor()
        self.assertIn("fieldlink-sync.sh", str(ctx.exception))

    def test_the_spec_is_not_reproduced_in_this_repo(self):
        """Guessing its contents would put a fabricated standard where the
        real one goes."""
        with open(os.path.join(ROOT, "bridges", "non_local_sensor.py"),
                  encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("exploration_techniques\":", src)
        self.assertIn("not reproduced here", src)

    def test_an_explicit_spec_makes_it_constructible(self):
        s = N.NonLocalCorrelationSensor(spec=STUB_SPEC)
        self.assertEqual(s.sensor_id, "non_local_pattern_correlation")


class TestNls2Tautology(unittest.TestCase):

    def setUp(self):
        self.s = N.NonLocalCorrelationSensor(spec=STUB_SPEC)

    def test_no_strength_produces_a_scale_technique_mismatch(self):
        t = N.pairing_is_tautological(self.s, n=201)
        self.assertEqual(t["mismatches"], 0)
        self.assertTrue(t["tautological"])

    def test_the_degeneracy_is_reported_with_every_reading(self):
        self.s.update(correlation_strength=0.6)
        self.assertTrue(self.s.get_metadata()["scale_is_inferred"])
        self.assertTrue(self.s.summary()["scale_is_inferred"])

    def test_supplying_the_scale_clears_the_flag(self):
        self.s.update(correlation_strength=0.6, scale="cross_system")
        self.assertFalse(self.s.get_metadata()["scale_is_inferred"])

    def test_the_flag_is_per_update_not_sticky(self):
        self.s.update(correlation_strength=0.6, scale="landscape")
        self.s.update(correlation_strength=0.6)
        self.assertTrue(self.s.get_metadata()["scale_is_inferred"])


class TestNls3Ordering(unittest.TestCase):

    def setUp(self):
        self.s = N.NonLocalCorrelationSensor(spec=STUB_SPEC)

    def test_a_strong_cross_system_correlation_is_relabelled(self):
        self.s.update(correlation_strength=0.95)
        self.assertEqual(self.s.get_metadata()["scale"], "cellular")

    def test_supplying_it_records_it(self):
        self.s.update(correlation_strength=0.95, scale="cross_system")
        md = self.s.get_metadata()
        self.assertEqual(md["scale"], "cross_system")
        self.assertEqual(md["technique"], "t_cross")

    def test_every_scale_is_excluded_from_three_of_four_bands(self):
        pairs = N.unrepresentable_pairs()
        self.assertEqual(len(pairs), 12)
        for p in pairs:
            self.assertNotEqual(p["true_scale"], p["recorded_as"])

    def test_the_bands_partition_the_unit_interval(self):
        bands = [b for b, _ in N._SCALE_BANDS]
        self.assertEqual(bands, sorted(bands))
        self.assertEqual(bands[-1], float("inf"))

    def test_infer_scale_matches_the_declared_bands(self):
        for strength, expected in ((0.0, "cross_system"), (0.19, "cross_system"),
                                   (0.2, "landscape"), (0.49, "landscape"),
                                   (0.5, "generational"), (0.79, "generational"),
                                   (0.8, "cellular"), (1.0, "cellular")):
            self.assertEqual(self.s._infer_scale(strength), expected,
                             msg=strength)


class TestNls4SilentMiss(unittest.TestCase):

    def test_a_spec_missing_an_inferred_scale_is_refused(self):
        bad = dict(STUB_SPEC)
        bad["scale_to_technique"] = {"planetary": ["t"]}
        with self.assertRaises(ValueError) as ctx:
            N.NonLocalCorrelationSensor(spec=bad)
        self.assertIn("NLS-4", str(ctx.exception))

    def test_all_four_inferred_names_are_checked(self):
        for drop in N._INFERRED_SCALES:
            bad = dict(STUB_SPEC)
            bad["scale_to_technique"] = {k: v for k, v
                                         in STUB_SPEC["scale_to_technique"].items()
                                         if k != drop}
            with self.assertRaises(ValueError, msg=drop):
                N.NonLocalCorrelationSensor(spec=bad)

    def test_the_inferred_names_are_exactly_what_infer_scale_emits(self):
        emitted = {name for _, name in N._SCALE_BANDS}
        self.assertEqual(emitted, set(N._INFERRED_SCALES))


class TestTheFalsifierReportRuns(unittest.TestCase):

    def test_it_exits_zero(self):
        import io
        from bridges import falsifiers_glyph_sensor as F
        F.FAILURES[:] = []
        F.CHECKS[:] = []
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            code = F.main()
        finally:
            sys.stdout = old
        self.assertEqual(code, 0, msg=buf.getvalue())
        self.assertGreaterEqual(len(F.CHECKS), 12)

    def test_it_states_that_a_pass_is_not_correctness(self):
        from bridges import falsifiers_glyph_sensor as F
        flat = " ".join(F.__doc__.split())
        self.assertIn('a PASS is not "this code is correct"', flat)


if __name__ == "__main__":
    unittest.main()
