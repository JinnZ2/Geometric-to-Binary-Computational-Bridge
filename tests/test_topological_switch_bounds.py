"""Tests for Silicon/topological_switch_bounds.py -- TSW-1..6.

Stdlib only. TSW-1..5 are arithmetic or a material veto and these tests are
what settles them; TSW-6 (the 2-SL gap) is a recorded absence.
"""

import ast
import inspect
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

import topological_switch_bounds as tsw  # noqa: E402


class TestTSW1Thermal(unittest.TestCase):
    def test_kt_300k(self):
        self.assertAlmostEqual(tsw.kt_mev(300.0), 25.852, places=2)

    def test_kt_zero_and_negative(self):
        self.assertEqual(tsw.kt_mev(0.0), 0.0)
        with self.assertRaises(ValueError):
            tsw.kt_mev(-1.0)

    def test_c1_gap_below_kt_at_300k(self):
        # TSW-1: the C=1 gap is smaller than kT at the Bridge's 300 K target
        self.assertLess(tsw.gap_in_kt(tsw.GAP_C1_6SL_MEV, 300.0), 1.0)

    def test_gap_in_kt_infinite_at_zero(self):
        self.assertTrue(math.isinf(tsw.gap_in_kt(10.0, 0.0)))


class TestTSW2Ceiling(unittest.TestCase):
    def test_protected_below(self):
        # 18.9 meV / (10 * k_B) ~ 21.9 K
        self.assertAlmostEqual(tsw.protected_below_k(18.9), 21.93, places=1)

    def test_ceiling_is_the_lower_of_two(self):
        c = tsw.operating_ceiling_k(tsw.GAP_C1_6SL_MEV)
        self.assertEqual(c["ceiling_k"], min(c["t_order_k"], c["t_gap_k"]))
        self.assertLess(c["ceiling_k"], tsw.SI_TARGET_K)

    def test_binding_can_be_either(self):
        # not CONSTANT: a large gap is bound by magnetic order, a small one by the gap
        self.assertEqual(tsw.operating_ceiling_k(500.0)["binding"], "magnetic_order")
        self.assertEqual(tsw.operating_ceiling_k(5.0)["binding"], "gap")

    def test_margin_is_a_parameter_that_moves_the_answer(self):
        self.assertNotEqual(tsw.protected_below_k(18.9, 5.0),
                            tsw.protected_below_k(18.9, 10.0))

    def test_rejects_nonpositive(self):
        with self.assertRaises(ValueError):
            tsw.protected_below_k(0.0)


class TestTSW3Readout(unittest.TestCase):
    def test_activation_monotone_in_gap(self):
        a_small = tsw.intrinsic_activation(18.9, 300.0)
        a_large = tsw.intrinsic_activation(91.6, 300.0)
        self.assertGreater(a_small, a_large)
        self.assertEqual(tsw.intrinsic_activation(18.9, 0.0), 0.0)

    def test_summary_carries_both_gaps(self):
        r = tsw.readout_summary()
        self.assertIn("C1_parallel", r)
        self.assertIn("C0_antiparallel", r)


class TestTSW4Silicon(unittest.TestCase):
    def test_does_not_transfer(self):
        self.assertEqual(tsw.silicon_transfer()["verdict"], "DOES_NOT_TRANSFER")

    def test_points_at_existing_module(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            tsw.silicon_transfer()["see"].split(" ")[0])
        self.assertTrue(os.path.exists(path))


class TestTSW5Doping(unittest.TestCase):
    def test_window_equals_gap(self):
        self.assertEqual(tsw.doping_window(18.9)["fermi_window_mev"], 18.9)
        self.assertEqual(tsw.doping_window(18.9)["grade"], "PROPOSED")


class TestTSW6Provenance(unittest.TestCase):
    def test_grade_is_prediction_at_press_depth(self):
        self.assertEqual(tsw.STUDY["grade"], "CITED_PRESS")
        self.assertIn("not measured", tsw.STUDY["kind"])
        self.assertIn("uncover", tsw.STUDY["rendering_drift"])

    def test_no_2sl_gap_is_invented(self):
        # TSW-6: the carried gaps are 6-SL; the 2-SL gap is NOT_IN_TEXT
        names = [n for n in dir(tsw) if n.startswith("GAP_")]
        self.assertTrue(names)
        self.assertTrue(all("6SL" in n for n in names))

    def test_thz_photon(self):
        self.assertAlmostEqual(tsw.thz_to_mev(1.0), 4.1357, places=3)

    def test_no_random_draws(self):
        tree = ast.parse(inspect.getsource(tsw))
        names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
        self.assertNotIn("random", names)


if __name__ == "__main__":
    unittest.main()
