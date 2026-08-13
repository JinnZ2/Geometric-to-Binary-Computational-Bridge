"""GI-1..16, GR-1..6, GB-1..5: geometric_intelligence/network.

Stdlib only. Most assertions here pin a DEFECT in place. If someone fixes one,
the test fails, and the fix is to amend the audit header in the module so it
stops describing code that no longer exists.

Two things this file also guards that are not findings:

  * The subpackage must stay a subpackage. `geometric_intelligence/__init__.py`
    is empty on purpose and four other suites depend on that; the drop assumed
    it could put `from .core import ...` there.
  * The drop's own 20-test suite is vendored under network/tests/ and is run
    from here. It is evidence, not coverage: three of its tests cannot fail,
    and TestGi16TheDropsOwnTests asserts exactly that.
"""

import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from geometric_intelligence.network import (  # noqa: E402
    GeometricNetwork, GeoEdge, IntegrityMonitor, MultiScaleResonance,
    PHI, PHI_INV, PHI_INV_9, INTEGRITY_THRESHOLD)
from geometric_intelligence.network import resonance as R  # noqa: E402
from geometric_intelligence.network import core as C  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def chain(reverse=True):
    net = GeometricNetwork()
    ids = ["brace_short", "brace_mid", "brace_long"]
    for i, x in enumerate(ids):
        net.add_node(x, 0.600 * PHI ** i)
    for i in range(len(ids) - 1):
        net.add_edge(ids[i], ids[i + 1], "scale", PHI)
        if reverse:
            net.add_edge(ids[i + 1], ids[i], "scale", 1.0 / PHI)
    return net


class TestConstants(unittest.TestCase):

    def test_phi_and_its_powers(self):
        self.assertAlmostEqual(PHI, 1.6180339887, places=9)
        self.assertAlmostEqual(PHI_INV, PHI - 1.0, places=12)
        self.assertAlmostEqual(PHI_INV_9, 0.0131556175, places=9)
        self.assertAlmostEqual(INTEGRITY_THRESHOLD, PHI + 2.0, places=12)

    def test_the_timber_frame_numbers_in_the_field_guide(self):
        self.assertAlmostEqual(600 * PHI, 970.8203932, places=6)
        self.assertAlmostEqual(600 * PHI ** 2, 1570.8203932, places=6)


class TestSubpackageBoundary(unittest.TestCase):
    """The drop assumed it owned geometric_intelligence/__init__.py."""

    def test_the_parent_init_is_still_empty(self):
        p = os.path.join(ROOT, "geometric_intelligence", "__init__.py")
        with open(p, encoding="utf-8") as fh:
            self.assertEqual(fh.read().strip(), "")

    def test_the_sibling_modules_still_import_without_this_package(self):
        import importlib
        for name in ("multi_helix_swarm", "resonance_sensors"):
            importlib.import_module("geometric_intelligence." + name)

    def test_the_docs_use_the_subpackage_import_path(self):
        for doc in ("README.md", "FIELD_GUIDE.md"):
            p = os.path.join(ROOT, "geometric_intelligence", "network", doc)
            with open(p, encoding="utf-8") as fh:
                txt = fh.read()
            self.assertNotIn("from geometric_intelligence import Geometric",
                             txt, msg=doc)


def nautilus(weight=1.0, n_ch=6):
    net = GeometricNetwork()
    for i in range(n_ch):
        net.add_node("c%d" % i, PHI ** i)
    for i in range(n_ch - 1):
        net.add_edge("c%d" % i, "c%d" % (i + 1), "scale", PHI, weight=weight)
        net.add_edge("c%d" % (i + 1), "c%d" % i, "scale", PHI_INV,
                     weight=weight)
    return net


def corrupted():
    net = nautilus()
    for e in net.edges:
        if e.source == "c2" and e.target == "c3":
            e.factor = 2.0
    return net


class TestCoreEdgeSemantics(unittest.TestCase):

    def test_the_three_relation_types(self):
        net = GeometricNetwork()
        for rel, factor, offset, expect in (("scale", 2.0, 0.0, 10.0),
                                            ("rotate", 3.0, 0.0, 8.0),
                                            ("compose", 2.0, 3.0, 13.0)):
            e = GeoEdge("A", "B", rel, factor, offset)
            self.assertAlmostEqual(net._apply(e, 5.0), expect, msg=rel)

    def test_each_relation_inverts(self):
        net = GeometricNetwork()
        for rel, factor, offset in (("scale", 2.0, 0.0), ("rotate", 3.0, 0.0),
                                    ("compose", 2.0, 3.0)):
            e = GeoEdge("A", "B", rel, factor, offset)
            self.assertAlmostEqual(net._inverse_apply(e, net._apply(e, 5.0)),
                                   5.0, msg=rel)

    def test_add_edge_creates_missing_nodes(self):
        net = GeometricNetwork()
        net.add_edge("a", "b", "scale", 2.0)
        self.assertEqual(sorted(net.nodes), ["a", "b"])

    def test_compose_transforms_chains_affine_maps(self):
        net = GeometricNetwork()
        a, b = net._compose_transforms([GeoEdge("A", "B", "scale", 2.0),
                                        GeoEdge("B", "C", "scale", 3.0)])
        self.assertEqual((a, b), (6.0, 0.0))
        a, b = net._compose_transforms([GeoEdge("A", "B", "compose", 2.0, 1.0),
                                        GeoEdge("B", "C", "compose", 3.0, 1.0)])
        self.assertEqual((a, b), (6.0, 4.0))


class TestGi8NullHarness(unittest.TestCase):
    """The one positive result in the core audit."""

    def test_the_score_collapses_when_the_geometry_is_destroyed(self):
        import random
        rng = random.Random(0)
        real = nautilus().audit()["integrity_score"]
        vals = []
        for _ in range(120):
            net = nautilus()
            for e in net.edges:
                e.factor = rng.uniform(0.2, 5.0)
            vals.append(net.audit()["integrity_score"])
        self.assertGreater(real, 1.9)
        self.assertLess(sum(vals) / len(vals), 0.1)

    def test_the_audit_header_reports_it_before_the_negatives(self):
        flat = " ".join(C.__doc__.split())
        self.assertIn("PASSES the null harness", flat)


class TestGi11FixedProbe(unittest.TestCase):

    def _affine_cycle(self, factor, offset):
        net = GeometricNetwork()
        net.add_node("a", 1.0)
        net.add_node("b", 1.0)
        net.add_edge("a", "b", "compose", factor=factor, offset=offset)
        net.add_edge("b", "a", "scale", factor=1.0)
        return net

    def test_a_non_identity_map_that_fixes_one_is_called_consistent(self):
        net = self._affine_cycle(2.0, -1.0)
        au = net.audit()
        self.assertEqual(au["consistent_cycles"], 1)
        self.assertEqual(au["inconsistent_cycles"], 0)

    def test_the_same_cycle_is_wrong_everywhere_else(self):
        net = self._affine_cycle(2.0, -1.0)
        a, b = net._compose_transforms(net.find_cycles()[0][0])
        for x in (0.0, 2.0, 10.0):
            self.assertGreater(abs(a * x + b - x), 0.9, msg=x)

    def test_every_a_plus_b_equals_one_map_passes(self):
        for factor in (0.5, 2.0, 5.0, -3.0):
            net = self._affine_cycle(factor, 1.0 - factor)
            self.assertEqual(net.audit()["inconsistent_cycles"], 0,
                             msg=factor)

    def test_pure_scale_cycles_are_unaffected(self):
        """Which is why nothing in the drop's demos or tests sees it."""
        net = self._affine_cycle(2.0, 0.0)
        self.assertEqual(net.audit()["inconsistent_cycles"], 1)

    def test_two_probe_points_would_catch_it(self):
        net = self._affine_cycle(2.0, -1.0)
        a, b = net._compose_transforms(net.find_cycles()[0][0])
        self.assertLess(abs(a * 1.0 + b - 1.0), 1e-12)
        self.assertGreater(abs(a - 1.0) + abs(b), 1.0)


class TestGi12IntegrityScore(unittest.TestCase):

    def test_zero_confidence_costs_nothing(self):
        self.assertEqual(nautilus(weight=0.0).audit()["integrity_score"], 1.0)

    def test_full_confidence_doubles_it(self):
        self.assertEqual(nautilus(weight=1.0).audit()["integrity_score"], 2.0)

    def test_weights_alone_move_the_score(self):
        import random
        rng = random.Random(1)
        vals = []
        for _ in range(120):
            net = nautilus()
            for e in net.edges:
                e.weight = rng.uniform(0.0, 1.0)
            vals.append(net.audit()["integrity_score"])
        self.assertGreater(max(vals) - min(vals), 0.4)

    def test_the_threshold_is_out_of_range_for_a_confidence_in_zero_one(self):
        self.assertLess(nautilus(weight=1.0).audit()["integrity_score"],
                        INTEGRITY_THRESHOLD)
        self.assertAlmostEqual(nautilus(weight=1e9).audit()["integrity_score"],
                               INTEGRITY_THRESHOLD, places=5)

    def test_two_modules_emit_one_name_with_two_ranges(self):
        net = nautilus()
        m = IntegrityMonitor(net)
        for i in range(6):
            m.add_measurement("c%d" % i, PHI ** i)
        self.assertEqual(net.audit()["integrity_score"], 2.0)
        self.assertLessEqual(m.full_report()["integrity_score"], 1.0)


class TestGi13Correct(unittest.TestCase):

    def test_five_iterations_move_nothing_measurable(self):
        net = corrupted()
        before = net.audit()["integrity_score"]
        net.correct(max_iter=5)
        self.assertEqual(before, net.audit()["integrity_score"])

    def test_convergence_reaches_consistency(self):
        net = corrupted()
        net.correct(max_iter=500)
        au = net.audit()
        self.assertEqual(au["inconsistent_cycles"], 0)

    def test_but_not_by_restoring_the_wrong_edge(self):
        net = corrupted()
        net.correct(max_iter=500)
        fwd = [e for e in net.edges
               if e.source == "c2" and e.target == "c3"][0]
        self.assertGreater(abs(fwd.factor - PHI) / PHI, 0.10)

    def test_the_error_is_split_with_the_inverse_partner(self):
        net = corrupted()
        net.correct(max_iter=500)
        fwd = [e for e in net.edges
               if e.source == "c2" and e.target == "c3"][0]
        rev = [e for e in net.edges
               if e.source == "c3" and e.target == "c2"][0]
        self.assertGreater(fwd.factor, PHI)
        self.assertLess(rev.factor, PHI_INV)
        self.assertLess(abs(fwd.factor * rev.factor - 1.0), 0.02)

    def test_only_the_edges_of_the_bad_cycle_move(self):
        net = corrupted()
        net.correct(max_iter=500)
        moved = [e for e in net.edges
                 if abs(e.factor - (PHI if int(e.target[1:]) >
                                    int(e.source[1:]) else PHI_INV)) > 1e-9]
        self.assertEqual(sorted((e.source, e.target) for e in moved),
                         [("c2", "c3"), ("c3", "c2")])

    def test_modified_counts_adjustments_not_edges(self):
        net = corrupted()
        self.assertGreaterEqual(net.correct(max_iter=5), len(net.edges))


class TestGi14InfiniteReconstruction(unittest.TestCase):

    def test_a_zero_factor_edge_yields_inf_not_an_exception(self):
        net = GeometricNetwork()
        for x in ("a", "b", "c"):
            net.add_node(x, 1.0)
        net.add_edge("a", "b", "scale", PHI)
        net.add_edge("b", "a", "scale", PHI_INV)
        net.add_edge("c", "b", "scale", 0.0)
        m = IntegrityMonitor(net)
        m.add_measurement("a", 1.0)
        m.add_measurement("b", PHI)
        self.assertEqual(m.reconstruct().get("c"), float("inf"))

    def test_core_returns_inf_rather_than_raising(self):
        net = GeometricNetwork()
        e = GeoEdge("a", "b", "scale", 0.0)
        self.assertEqual(net._inverse_apply(e, 1.0), float("inf"))

    def test_the_caller_guards_on_the_exception_that_never_comes(self):
        import inspect
        src = inspect.getsource(IntegrityMonitor.reconstruct)
        self.assertIn("ZeroDivisionError", src)


class TestGi15Hash(unittest.TestCase):

    def test_it_is_stable_for_one_object(self):
        net = GeometricNetwork()
        net.add_node("A", 1.0)
        self.assertEqual(net.hash(), net.hash())

    def test_it_is_stable_across_identical_builds(self):
        a, b = GeometricNetwork(), GeometricNetwork()
        for net in (a, b):
            net.add_node("A", 1.0)
            net.add_node("B", 2.0)
        self.assertEqual(a.hash(), b.hash())

    def test_it_changes_with_insertion_order(self):
        a, b = GeometricNetwork(), GeometricNetwork()
        a.add_node("A", 1.0)
        a.add_node("B", 2.0)
        b.add_node("B", 2.0)
        b.add_node("A", 1.0)
        self.assertNotEqual(a.hash(), b.hash())

    def test_the_docstring_claims_topology_and_relations(self):
        self.assertIn("topology and relations",
                      GeometricNetwork.hash.__doc__)


class TestGi16TheDropsOwnTests(unittest.TestCase):
    """The suite the package README cites as its validation. All 20 pass."""

    def test_the_suite_still_passes(self):
        import unittest as U
        loader = U.TestLoader()
        suite = loader.loadTestsFromName(
            "geometric_intelligence.network.tests.test_geometric_intelligence")
        with open(os.devnull, "w") as sink:
            result = U.TextTestRunner(verbosity=0, stream=sink).run(suite)
        self.assertTrue(result.wasSuccessful())
        self.assertEqual(result.testsRun, 20)

    def test_audit_passes_bounds_hold_by_construction(self):
        broke = GeometricNetwork()
        broke.add_node("a", 1.0)
        broke.add_node("b", 1.0)
        broke.add_edge("a", "b", "scale", 99.0)
        broke.add_edge("b", "a", "scale", 99.0)
        self.assertEqual(broke.audit()["integrity_score"], 0.0)
        self.assertAlmostEqual(nautilus(weight=1e9).audit()["integrity_score"],
                               INTEGRITY_THRESHOLD, places=5)

    def test_the_correct_fixture_is_already_consistent(self):
        net = GeometricNetwork()
        net.add_node("A", 1.0)
        net.add_node("B", 2.0)
        net.add_edge("A", "B", "scale", 2.5)
        net.add_edge("B", "A", "scale", 0.4)
        self.assertEqual(net.audit()["inconsistent_cycles"], 0)
        self.assertAlmostEqual(2.5 * 0.4, 1.0, places=12)

    def test_the_guarded_cycle_assertion_does_run(self):
        """Checked rather than assumed: a guarded assertion that never runs
        is the same defect as one that cannot fail."""
        net = GeometricNetwork()
        net.add_node("A", 1.0)
        net.add_node("B", PHI)
        net.add_node("C", PHI ** 2)
        net.add_edge("A", "B", "scale", PHI)
        net.add_edge("B", "C", "scale", PHI)
        net.add_edge("C", "A", "scale", PHI_INV ** 2)
        self.assertTrue(any(len(c) == 3
                            for c, _ in net.find_cycles(max_depth=5)))


class TestBridgeClaims(unittest.TestCase):

    def setUp(self):
        import tempfile
        from geometric_intelligence.network import bridge
        self.B = bridge
        self.led = os.path.join(tempfile.mkdtemp(), "led.json")

    def _chain(self):
        net = GeometricNetwork()
        for x, v in (("L1", 0.100), ("L2", 0.162), ("L3", 0.262)):
            net.add_node(x, v)
        net.add_edge("L1", "L2", "scale", PHI)
        net.add_edge("L2", "L3", "scale", PHI)
        return net

    def test_gb2_an_acyclic_design_scores_zero(self):
        claims = self.B.network_to_claims(self._chain(), scope_prefix="a")
        ic = [c for c in claims if "integrity" in c["scope"]][0]
        self.assertEqual(ic["value"], 0.0)
        self.assertEqual(self._chain().audit()["n_cycles"], 0)

    def test_gb2_reverse_edges_fix_it(self):
        net = self._chain()
        net.add_edge("L2", "L1", "scale", PHI_INV)
        net.add_edge("L3", "L2", "scale", PHI_INV)
        claims = self.B.network_to_claims(net, scope_prefix="b")
        ic = [c for c in claims if "integrity" in c["scope"]][0]
        self.assertGreater(ic["value"], 1.0)

    def test_gb1_verify_divides_by_the_prediction(self):
        from pathlib import Path
        net = GeometricNetwork()
        net.add_node("a", 0.0)
        net.add_node("b", 0.0)
        net.add_edge("a", "b", "rotate", factor=0.0)
        self.B.append_geo_claims(
            self.B.network_to_claims(net, scope_prefix="rot"),
            Path(self.led))
        with self.assertRaises(ZeroDivisionError):
            self.B.verify_edge_measurement("rot", 0, 0.1, Path(self.led))

    def test_gb1_the_acyclic_integrity_claim_is_the_same_zero(self):
        from pathlib import Path
        self.B.append_geo_claims(
            self.B.network_to_claims(self._chain(), scope_prefix="c"),
            Path(self.led))
        with open(self.led, encoding="utf-8") as fh:
            claims = json.load(fh)
        ic = [c for c in claims if c["scope"].endswith("::integrity")][0]
        self.assertEqual(ic["value"], 0.0)

    def test_gb3_the_failure_text_describes_a_threshold_not_a_band(self):
        claims = self.B.network_to_claims(self._chain(), scope_prefix="d")
        ic = [c for c in claims if "integrity" in c["scope"]][0]
        self.assertEqual(ic["tol_frac"], 0.10)
        self.assertIn("below", ic["failure"])
        self.assertIn("threshold", ic["failure"])

    def test_gb4_three_unsourced_tolerances(self):
        net = self._chain()
        net.add_edge("L2", "L1", "scale", PHI_INV)
        claims = self.B.network_to_claims(net, scope_prefix="e")
        tols = {c["tol_frac"] for c in claims}
        self.assertEqual(tols, {0.05, PHI_INV_9, 0.10})

    def test_gb4_the_drift_band_is_the_square_not_the_double(self):
        from pathlib import Path
        self.B.append_geo_claims(
            self.B.network_to_claims(self._chain(), scope_prefix="f"),
            Path(self.led))
        p = Path(self.led)
        # (1+t)^2 = 1.1025; 1+2t = 1.10. A ratio between them is drift under
        # the square band and would be fail under a doubled one.
        r = self.B.verify_edge_measurement("f", 0, PHI * 1.101, p)
        self.assertEqual(r["verdict"], "drift")
        r = self.B.verify_edge_measurement("f", 0, PHI * 1.11, p)
        self.assertEqual(r["verdict"], "fail")

    def test_gb5_the_ledger_path_is_relative(self):
        from pathlib import Path
        self.assertFalse(Path(self.B.LEDGER).is_absolute())

    def test_the_edge_claims_carry_a_failure_mode(self):
        claims = self.B.network_to_claims(self._chain(), scope_prefix="g")
        for c in claims:
            self.assertTrue(c["failure"])
            self.assertTrue(c["measurement"])
            self.assertEqual(len(c["id"]), 16)


class TestGi1MeasurementsDoNotPropagate(unittest.TestCase):

    def test_the_source_measurement_changes_no_prediction(self):
        a = IntegrityMonitor(chain())
        a.add_measurement("brace_short", 0.600)
        b = IntegrityMonitor(chain())
        b.add_measurement("brace_short", 0.400)
        self.assertEqual(a.predict_from("brace_short", "brace_mid"),
                         b.predict_from("brace_short", "brace_mid"))

    def test_the_prediction_is_the_design_value(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.400)
        self.assertAlmostEqual(m.predict_from("brace_short", "brace_mid"),
                               0.600 * PHI, places=9)

    def test_the_report_says_so_rather_than_letting_it_be_assumed(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.600)
        m.add_measurement("brace_mid", 0.600 * PHI)
        self.assertIs(m.full_report()["predictions_use_measurements"], False)

    def test_the_audit_header_records_it_as_the_load_bearing_one(self):
        from geometric_intelligence.network import integrity as I
        flat = " ".join(I.__doc__.split())
        self.assertIn("GI-1", flat)
        self.assertIn("load-bearing", flat)


class TestGi2ThresholdUnreachable(unittest.TestCase):

    def test_the_clause_cannot_be_satisfied(self):
        self.assertGreater(INTEGRITY_THRESHOLD * 0.5, 1.0)

    def test_integrity_is_bounded_by_one_by_construction(self):
        for meas in ({"brace_short": 0.600},
                     {"brace_short": 0.600, "brace_mid": 0.600 * PHI},
                     {"brace_short": 0.600, "brace_mid": 0.600 * PHI,
                      "brace_long": 0.600 * PHI ** 2}):
            m = IntegrityMonitor(chain())
            for k, v in meas.items():
                m.add_measurement(k, v)
            self.assertLessEqual(m.full_report()["integrity_score"], 1.0)

    def test_the_report_flags_the_clause_as_unreachable(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.600)
        m.add_measurement("brace_mid", 0.600 * PHI)
        self.assertIs(m.full_report()["threshold_clause_reachable"], False)

    def test_passes_is_decided_by_the_first_clause_alone(self):
        m = IntegrityMonitor(chain())
        for k, v in (("brace_short", 0.600), ("brace_mid", 0.600 * PHI),
                     ("brace_long", 0.600 * PHI ** 2)):
            m.add_measurement(k, v)
        r = m.full_report()
        first = (r["n_trusted"] == r["n_measured"] and r["coverage"] >= 0.5)
        self.assertEqual(r["passes"], first)


class TestGi3ContradictionResolvedByMeasurement(unittest.TestCase):

    def _two_routes(self, measured):
        net = GeometricNetwork()
        for x, v in (("a", 1.0), ("b", PHI), ("d", PHI ** 3)):
            net.add_node(x, v)
        net.add_edge("a", "d", "scale", PHI ** 3)
        net.add_edge("a", "b", "scale", PHI)
        net.add_edge("b", "d", "scale", 2.0)
        m = IntegrityMonitor(net)
        m.add_measurement("a", 1.0)
        m.add_measurement("b", PHI)
        m.add_measurement("d", measured)
        return {q.node_id: q for q in m.check()}["d"]

    def test_the_route_that_agrees_is_the_one_reported(self):
        for value in (PHI ** 3, PHI * 2.0):
            r = self._two_routes(value)
            self.assertTrue(r.trusted, msg=value)
            self.assertAlmostEqual(r.predicted, value, places=9)

    def test_nothing_in_the_report_says_a_route_was_chosen(self):
        r = self._two_routes(PHI * 2.0)
        self.assertEqual(
            [f for f in ("source", "route", "path", "ambiguous")
             if hasattr(r, f)], [])

    def test_on_a_consistent_design_every_source_gives_one_value(self):
        net = chain()
        m = IntegrityMonitor(net)
        preds = {s: m.predict_from(s, "brace_long")
                 for s in ("brace_short", "brace_mid")}
        self.assertEqual(len(set(round(v, 12) for v in preds.values())), 1)


class TestGi4ReconstructHasNoAveraging(unittest.TestCase):

    def _two_paths(self, f1, f2):
        g = GeometricNetwork()
        for x, v in (("a", 1.0), ("b", PHI), ("x", 2.0)):
            g.add_node(x, v)
        g.add_edge("a", "b", "scale", PHI)
        g.add_edge("b", "a", "scale", 1.0 / PHI)
        g.add_edge("a", "x", "scale", f1)
        g.add_edge("a", "x", "scale", f2)
        m = IntegrityMonitor(g)
        m.add_measurement("a", 1.0)
        m.add_measurement("b", PHI)
        return m.reconstruct().get("x")

    def test_insertion_order_decides_the_value(self):
        self.assertEqual(self._two_paths(2.0, 5.0), 2.0)
        self.assertEqual(self._two_paths(5.0, 2.0), 5.0)

    def test_it_is_not_the_average(self):
        self.assertNotEqual(self._two_paths(2.0, 5.0), 3.5)

    def test_the_docstring_still_promises_the_average(self):
        flat = " ".join(IntegrityMonitor.reconstruct.__doc__.split())
        self.assertIn("average", flat)
        self.assertIn("weighted by path confidence", flat)

    def test_no_weighting_appears_in_the_body(self):
        import inspect
        body = inspect.getsource(IntegrityMonitor.reconstruct).split('"""')[2]
        for token in ("average", "weight", "confidence"):
            self.assertNotIn(token, body)


class TestGi5DeadField(unittest.TestCase):

    def test_reconstructed_is_none_on_every_report(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.600)
        m.add_measurement("brace_mid", 0.600 * PHI)
        for r in m.check():
            self.assertIsNone(r.reconstructed)

    def test_full_report_gets_the_value_from_elsewhere(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.600)
        m.add_measurement("brace_mid", 0.600 * PHI)
        rows = m.full_report()["node_reports"]
        self.assertTrue(all(r["reconstructed"] is not None for r in rows))


class TestGi6ReconstructionNeedsTwo(unittest.TestCase):

    def test_one_measurement_reconstructs_nothing(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.600)
        self.assertEqual(m.reconstruct(), {})

    def test_two_measurements_reconstruct_the_third(self):
        m = IntegrityMonitor(chain())
        m.add_measurement("brace_short", 0.600)
        m.add_measurement("brace_mid", 0.600 * PHI)
        recon = m.reconstruct()
        self.assertEqual(len(recon), 3)
        self.assertAlmostEqual(recon["brace_long"], 0.600 * PHI ** 2, places=6)

    def test_an_isolated_node_is_untrusted_whatever_it_measures(self):
        net = GeometricNetwork()
        net.add_node("lonely", 1.0)
        m = IntegrityMonitor(net)
        m.add_measurement("lonely", 1.0)
        self.assertFalse(m.check()[0].trusted)

    def test_a_forward_only_chain_flags_its_first_node_on_perfect_data(self):
        """The field guide's own timber example, before it was corrected."""
        m = IntegrityMonitor(chain(reverse=False))
        for k, v in (("brace_short", 0.600), ("brace_mid", 0.600 * PHI),
                     ("brace_long", 0.600 * PHI ** 2)):
            m.add_measurement(k, v)
        self.assertEqual(m.full_report()["untrusted_nodes"], ["brace_short"])

    def test_adding_the_reverse_edges_clears_it(self):
        m = IntegrityMonitor(chain(reverse=True))
        for k, v in (("brace_short", 0.600), ("brace_mid", 0.600 * PHI),
                     ("brace_long", 0.600 * PHI ** 2)):
            m.add_measurement(k, v)
        r = m.full_report()
        self.assertEqual(r["untrusted_nodes"], [])
        self.assertTrue(r["passes"])

    def test_the_corrected_field_guide_adds_them(self):
        p = os.path.join(ROOT, "geometric_intelligence", "network",
                         "FIELD_GUIDE.md")
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn('"brace_mid",   "brace_short", "scale", factor=1/PHI',
                      txt)


class TestGr1BandEdges(unittest.TestCase):

    def test_the_edges_are_not_monotonic(self):
        ok, bad, dead = R.edges_are_monotonic()
        self.assertFalse(ok)
        self.assertEqual(len(bad), 1)

    def test_the_last_band_is_empty_by_construction(self):
        r = MultiScaleResonance()
        lo, hi = r.band_edges[-2], r.band_edges[-1]
        self.assertGreater(lo, hi)
        for f in (hi, lo, lo * 2, 1e6):
            self.assertFalse(lo <= f < hi)

    def test_the_penultimate_edge_overshoots_f_max(self):
        r = MultiScaleResonance(f_min=1.0, f_max=10000.0)
        self.assertGreater(r.band_edges[-2], r.f_max)

    def test_energy_above_the_overshoot_is_dropped(self):
        r = MultiScaleResonance()
        top = r.band_edges[-2]
        out = r.analyze([top * 1.5, top * 2.0], [10.0, 10.0])
        self.assertEqual(out["peaks"], [])
        self.assertEqual(out["anomalies"], [])


class TestGr2UnusedParameter(unittest.TestCase):

    def test_bands_per_octave_changes_nothing(self):
        self.assertFalse(R.band_resolution_is_honoured())

    def test_every_value_gives_the_same_edges(self):
        base = MultiScaleResonance().band_edges
        for n in (1, 2, 5, 12, 64):
            self.assertEqual(MultiScaleResonance(bands_per_octave=n).band_edges,
                             base, msg=n)

    def test_the_ratio_between_edges_is_always_phi(self):
        e = MultiScaleResonance(bands_per_octave=64).band_edges
        for i in range(len(e) - 3):
            self.assertAlmostEqual(e[i + 1] / e[i], PHI, places=9)


class TestGr3FitIncludesPeaks(unittest.TestCase):

    def test_the_guard_admits_every_populated_band(self):
        self.assertTrue(R.fit_includes_peaks())

    def test_the_comment_and_the_code_disagree(self):
        import inspect
        src = inspect.getsource(MultiScaleResonance.analyze)
        self.assertIn("non-peak bands", src)
        self.assertIn("if band_count[i] > 0:", src.split('"""')[2])

    def test_a_spike_raises_the_baseline_it_is_judged_against(self):
        r = MultiScaleResonance()
        freqs = [1.0 * PHI ** (i / 8.0) for i in range(200)]
        clean = [f ** -0.5 for f in freqs]
        spiked = list(clean)
        mid = len(freqs) // 2
        for k in range(mid - 2, mid + 3):
            spiked[k] *= 30.0
        self.assertNotAlmostEqual(r.analyze(freqs, clean)["fitted_slope"],
                                  r.analyze(freqs, spiked)["fitted_slope"],
                                  places=3)


class TestGr4Threshold(unittest.TestCase):

    def test_the_gate_is_two_point_three(self):
        self.assertAlmostEqual(1.0 + PHI_INV_9 * 100, 2.3155617, places=6)

    def test_the_reported_threshold_matches_the_code(self):
        r = MultiScaleResonance()
        out = r.detect_injection([1.0], [1.0], [1.0])
        self.assertAlmostEqual(out["threshold_ratio"], 1.0 + PHI_INV_9 * 100,
                               places=4)

    def test_a_ratio_between_the_old_and_new_comment_does_not_fire(self):
        r = MultiScaleResonance()
        out = r.detect_injection([1.0], [1.8], [1.0])
        self.assertEqual(out["n_injections"], 0)

    def test_a_ratio_above_the_gate_does(self):
        r = MultiScaleResonance()
        out = r.detect_injection([1.0], [3.0], [1.0])
        self.assertEqual(out["n_injections"], 1)

    def test_the_corrected_comment_is_in_the_source(self):
        import inspect
        src = inspect.getsource(MultiScaleResonance.detect_injection)
        self.assertIn("the gate is ratio > 2.3156", src)
        # the old text survives only inside the correction that names it
        self.assertIn("An earlier", src.split("~1.315x baseline")[0][-90:])


class TestGr5NoNull(unittest.TestCase):

    def test_pure_noise_trips_a_sixth_of_the_bins(self):
        far = R.injection_false_alarm_rate(n_bins=2048, trials=20, seed=3)
        self.assertGreater(far, 0.10)
        self.assertLess(far, 0.25)

    def test_the_rate_does_not_fall_with_more_bins(self):
        """No multiplicity correction, so it is a constant, not a rate."""
        a = R.injection_false_alarm_rate(n_bins=512, trials=12, seed=5)
        b = R.injection_false_alarm_rate(n_bins=8192, trials=6, seed=5)
        self.assertLess(abs(a - b), 0.04)

    def test_the_analytic_value_for_an_exponential_ratio(self):
        """For iid Exp(1) numerator and denominator, P(A/B > t) = 1/(1+t)."""
        t = 1.0 + PHI_INV_9 * 100
        self.assertAlmostEqual(1.0 / (1.0 + t), 0.3016, places=3)

    def test_there_is_no_minimum_sample_gate(self):
        r = MultiScaleResonance()
        out = r.detect_injection([1.0], [10.0], [1.0])
        self.assertEqual(out["injection_score"], 1.0)


class TestGr6TwoShapes(unittest.TestCase):

    def test_the_key_sets_differ(self):
        with_b, without_b = R.injection_return_shapes()
        self.assertNotEqual(with_b, without_b)

    def test_the_no_baseline_path_has_no_injections_key(self):
        r = MultiScaleResonance()
        out = r.detect_injection([1.0], [1.0], None)
        with self.assertRaises(KeyError):
            out["injections"]

    def test_the_fallback_itself_is_documented_and_intended(self):
        import inspect
        src = inspect.getsource(MultiScaleResonance.detect_injection)
        self.assertIn("No baseline: use power-law expectation", src)
        flat = " ".join(MultiScaleResonance.detect_injection.__doc__.split())
        self.assertIn("not in the baseline", flat)


class TestSpeedOfSound(unittest.TestCase):
    """GI-7. The field guide's headline correction."""

    @staticmethod
    def c_lin(t):
        return 331.3 + 0.606 * t

    @staticmethod
    def c_exact(t):
        return 331.3 * math.sqrt(1.0 + t / 273.15)

    def test_the_linear_form_is_good_to_half_a_percent_over_the_stated_range(self):
        for t in range(-50, 51, 5):
            err = abs(self.c_lin(t) - self.c_exact(t)) / self.c_exact(t)
            self.assertLess(err, 0.006, msg=t)

    def test_the_shift_from_plus_twenty_to_minus_forty(self):
        ratio = self.c_lin(-40) / self.c_lin(20)
        self.assertAlmostEqual(1.0 - ratio, 0.1058, places=3)

    def test_it_is_not_the_six_percent_the_drop_documented(self):
        self.assertGreater(1.0 - self.c_lin(-40) / self.c_lin(20), 0.09)

    def test_the_hardcoded_343_is_the_fifteen_degree_value(self):
        self.assertAlmostEqual(self.c_lin(15), 340.4, places=1)
        self.assertLess(abs(343.0 - self.c_lin(15)) / 343.0, 0.01)

    def test_the_corrected_guide_carries_the_right_number(self):
        p = os.path.join(ROOT, "geometric_intelligence", "network",
                         "FIELD_GUIDE.md")
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("10.6 %", txt)
        self.assertIn("331.3 + 0.606", txt)


class TestContractionTable(unittest.TestCase):
    """The drop's table gave percentages with no reference temperature, and
    back-solving them found three different references across five rows."""

    def test_the_metals_imply_a_plus_fifteen_reference(self):
        for alpha, claimed in ((12e-6, 0.066), (23e-6, 0.127), (10e-6, 0.055)):
            dT = (claimed / 100.0) / alpha
            self.assertAlmostEqual(-40 + dT, 15.0, delta=0.5)

    def test_the_wood_rows_did_not(self):
        for alpha, claimed in ((4e-6, 0.020), (42.5e-6, 0.170)):
            dT = (claimed / 100.0) / alpha
            self.assertNotAlmostEqual(-40 + dT, 15.0, delta=1.0)

    def test_the_corrected_table_states_its_reference_and_gives_ranges(self):
        p = os.path.join(ROOT, "geometric_intelligence", "network",
                         "FIELD_GUIDE.md")
        with open(p, encoding="utf-8") as fh:
            txt = fh.read()
        self.assertIn("Δ from +15 °C to −40 °C", txt)
        self.assertIn("−0.14 % to −0.33 %", txt)
        self.assertIn("moisture", txt)


class TestFalsifierReportRuns(unittest.TestCase):

    def test_it_exits_zero(self):
        import io
        from geometric_intelligence import falsifiers_gi_network as F
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
        from geometric_intelligence import falsifiers_gi_network as F
        flat = " ".join(F.__doc__.split())
        self.assertIn('A PASS is not "this code is correct"', flat)


if __name__ == "__main__":
    unittest.main()
