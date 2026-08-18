"""ENG-1..6: what the Engine's performance numbers actually measure.

Needs numpy. These are the figures docs/Implementation_Roadmap.md was written
on top of -- every phase target stated as a multiple of them -- while the
roadmap's own Month-1 item, "Add basic benchmarks for EM field problems",
stayed unchecked. Engine/engine_benchmark.py is that benchmark.

Two things this file guards:

  * A finding that quietly stops being true. ENG-5 and ENG-6 assert DEFECTS
    left in place on purpose. Fixing either should fail here, and the response
    is to amend the AUDIT header in Engine/geometric_solver.py and the roadmap
    item that quotes the measurement.

  * The benchmark measuring nothing. A timing harness that reports a number
    whatever it is handed is the shape this whole exercise exists to catch, so
    the baseline is checked for responding to the problem size, and the
    accuracy column is checked for catching a path that skipped the field.

Timing assertions use wide margins -- ENG-1 is a factor of 20 in the wrong
direction, not a percentage -- so a loaded machine does not flip a verdict.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np  # noqa: E402

from Engine import engine_benchmark as BM  # noqa: E402
from Engine.geometric_solver import GeometricEMSolver, PerformanceTracker  # noqa: E402
from Engine.simd_optimizer import SIMDOptimizer  # noqa: E402
from Engine.spatial_grid import SpatialGrid  # noqa: E402

BOUNDS = BM.BOUNDS
ASYM = BM.CASES["dipole (asymmetric)"]
SYM = BM.CASES["quadrupole (2-fold)"]
ONE = [{"position": [1, 0, 0], "strength": 1e-9, "type": "charge"}]


def solve(sources, resolution=32):
    s = GeometricEMSolver()
    s.calculateElectromagneticField(sources, BOUNDS, resolution=resolution)
    return s


class TestENG_1_RatioIsNotASpeedup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = BM.benchmark(resolutions=(32,), repeats=2, verbose=False)

    def test_the_adaptive_path_is_slower_than_the_uniform_baseline(self):
        for r in self.rows:
            self.assertLess(r["measured_speedup"], 1.0, msg=r["case"])

    def test_the_point_ratio_overstates_the_timing_by_more_than_10x(self):
        for r in self.rows:
            self.assertGreater(r["point_ratio"] / r["measured_speedup"], 10,
                               msg=r["case"])

    def test_the_report_does_not_call_a_point_ratio_a_speedup(self):
        rep = solve(ASYM).performanceMetrics.getEfficiencyReport()
        self.assertIn("not timed", rep["averageSpeedup"])
        self.assertIn("engine_benchmark", rep["measuredSpeedup"])

    def test_no_clock_enters_the_recorded_ratio(self):
        """total_time is recorded in the same call and must not affect it."""
        t = PerformanceTracker()
        common = dict(symmetry_time=0.0, grid_time=0.0, field_time=0.0,
                      n_points=1000, n_regions=1000, simd_efficiency=12.5,
                      symmetry_reduction=1.0, symmetries_found=0,
                      resolution=32)
        t.record(total_time=0.001, **common)
        fast = t._last["point_ratio"]
        t.record(total_time=100.0, **common)
        self.assertEqual(fast, t._last["point_ratio"])


class TestENG_2_BaselineTracksResolution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.last = {r: solve(ASYM, r).performanceMetrics._last
                    for r in (16, 32, 64)}

    def test_the_baseline_is_the_requested_resolution_cubed(self):
        for r in (16, 32, 64):
            self.assertEqual(self.last[r]["baseline_points"], r ** 3)

    def test_the_ratio_now_responds_to_resolution(self):
        self.assertEqual(
            len({self.last[r]["point_ratio"] for r in (16, 32, 64)}), 3)

    def test_resolution_still_reaches_no_part_of_the_decomposition(self):
        """The defect the fix does not touch: adaptiveDecomposition never
        receives resolution, and the 'uniform fallback' its docstring names
        does not exist."""
        self.assertEqual(
            len({self.last[r]["n_points"] for r in (16, 32, 64)}), 1)


class TestENG_3_SymmetryFactorNotTaken(unittest.TestCase):
    def test_symmetry_is_detected(self):
        last = solve(SYM).performanceMetrics._last
        self.assertGreater(last["symmetries_found"], 0)
        self.assertGreater(last["symmetry_reduction_available"], 1.0)

    def test_the_factor_does_not_multiply_the_ratio(self):
        last = solve(SYM).performanceMetrics._last
        self.assertAlmostEqual(last["point_ratio"],
                               32 ** 3 / last["n_points"], places=9)

    def test_every_region_is_still_computed(self):
        """The saving is reported, not taken -- so the point count is not
        divided by the reduction factor."""
        last = solve(SYM).performanceMetrics._last
        self.assertEqual(last["n_points"], last["n_regions"])

    def test_the_report_says_available_not_taken(self):
        rep = solve(SYM).performanceMetrics.getEfficiencyReport()
        self.assertIn("not exploited", rep["symmetryReduction"])


class TestENG_4_AverageIsAnAverage(unittest.TestCase):
    def test_it_is_the_mean_over_history_not_the_last_value(self):
        s = GeometricEMSolver()
        s.calculateElectromagneticField(ASYM, BOUNDS, resolution=16)
        s.calculateElectromagneticField(SYM, BOUNDS, resolution=32)
        hist = [h["point_ratio"] for h in s.performanceMetrics.history]
        mean = sum(hist) / len(hist)
        reported = float(
            s.performanceMetrics.getEfficiencyReport()["pointRatio"]
            .rstrip("x"))
        self.assertAlmostEqual(reported, mean, places=1)
        self.assertGreater(abs(hist[-1] - mean), 0.05,
                           msg="fixture must have a last value that differs "
                               "from the mean, or this asserts nothing")

    def test_history_is_accumulated(self):
        s = GeometricEMSolver()
        for _ in range(3):
            s.calculateElectromagneticField(ASYM, BOUNDS)
        self.assertEqual(len(s.performanceMetrics.history), 3)


class TestENG_5_OnePointPerRegion(unittest.TestCase):
    """Recorded, not fixed."""

    @classmethod
    def setUpClass(cls):
        cls.bd = BM.breakdown(repeats=2, verbose=False)

    def test_each_leaf_region_carries_exactly_one_point(self):
        self.assertAlmostEqual(self.bd["points_per_region"], 1.0, places=9)
        grid = SpatialGrid()
        for region in grid.adaptiveDecomposition(BOUNDS, ASYM)[:20]:
            self.assertEqual(len(region["points"]), 1)

    def test_chunking_per_region_costs_more_than_10x_batching(self):
        self.assertGreater(self.bd["chunking_overhead"], 10)

    def test_batching_would_be_a_large_win_on_the_field_evaluation(self):
        self.assertGreater(self.bd["field_speedup_if_batched"], 5)

    def test_but_the_decomposition_would_then_dominate(self):
        """Why ENG-5 is a roadmap item and not a one-line fix here."""
        self.assertLess(self.bd["endtoend_if_batched"], 2.0)
        self.assertGreater(self.bd["decomposition_s"],
                           0.5 * self.bd["field_uniform_s"])

    def test_batching_gives_the_same_field(self):
        """The 26x is not from computing less."""
        grid, simd = SpatialGrid(), SIMDOptimizer()
        regions = grid.adaptiveDecomposition(BOUNDS, ASYM)
        pts = [p for r in regions for p in r["points"]]
        chunked = np.array([simd.calculateFieldChunk(
            {"points": r["points"]}, ASYM)["electricField"][0]
            for r in regions])
        batched = np.array(simd.calculateFieldChunk(
            {"points": pts}, ASYM)["electricField"])
        np.testing.assert_allclose(chunked, batched, rtol=1e-12)


class TestENG_6_ConstantSimdEfficiency(unittest.TestCase):
    """Recorded, not fixed."""

    def test_it_is_the_same_for_every_configuration(self):
        for sources in (ONE, ASYM, SYM):
            self.assertAlmostEqual(
                solve(sources).performanceMetrics._last["simd_efficiency"],
                12.5, places=9)

    def test_it_is_a_function_of_chunk_length_alone(self):
        simd = SIMDOptimizer()
        for n, want in ((1, 12.5), (8, 100.0), (9, 56.25)):
            pts = [[0.5 * i, 0.0, 0.0] for i in range(1, n + 1)]
            got = simd.calculateFieldChunk({"points": pts},
                                           ONE)["simdEfficiency"]
            self.assertAlmostEqual(got, want, places=6)

    def test_the_report_states_the_constancy(self):
        rep = solve(ONE).performanceMetrics.getEfficiencyReport()
        self.assertIn("constant", rep["simdEfficiency"])


class TestBenchmarkMeasuresSomething(unittest.TestCase):
    """A harness that reports a number whatever it is handed is the shape this
    exercise exists to catch."""

    def test_the_uniform_baseline_grows_with_resolution(self):
        rows = BM.benchmark(resolutions=(8, 16), repeats=1,
                            cases={"d": ASYM}, verbose=False)
        by_res = {r["resolution"]: r for r in rows}
        self.assertEqual(by_res[8]["uniform_points"], 8 ** 3)
        self.assertEqual(by_res[16]["uniform_points"], 16 ** 3)
        self.assertGreater(by_res[16]["point_ratio"], by_res[8]["point_ratio"])

    def test_accuracy_catches_a_path_that_skipped_the_field(self):
        """Feed it a wrong field and the error column must move."""
        pts = [[0.1 * i, 0.0, 0.0] for i in range(1, 40)]
        good = [[1.0, 0.0, 0.0]] * len(pts)
        zero = [[0.0, 0.0, 0.0]] * len(pts)
        med_same, _ = BM.accuracy(pts, good, pts, good)
        med_wrong, _ = BM.accuracy(pts, good, pts, zero)
        self.assertLess(med_same, 1e-12)
        self.assertGreater(med_wrong, 0.5)

    def test_both_paths_go_through_the_same_optimizer(self):
        """Otherwise the comparison would be of two different computations.

        Checked by injecting a counting optimizer into both helpers, rather
        than by counting occurrences of a call in the source -- which is a
        magic number that changes whenever the file is edited and asserts
        nothing about behaviour.
        """
        class Counting(SIMDOptimizer):
            def __init__(self):
                super().__init__()
                self.calls = 0

            def calculateFieldChunk(self, chunk, sources):
                self.calls += 1
                return super().calculateFieldChunk(chunk, sources)

        u, a = Counting(), Counting()
        BM.run_uniform(ASYM, BOUNDS, 8, simd=u)
        BM.run_adaptive(ASYM, BOUNDS, simd=a)
        self.assertGreater(u.calls, 0)
        self.assertGreater(a.calls, 0)

    def test_the_two_paths_agree_where_they_share_a_point(self):
        """A speedup that came from computing a different field would show up
        here rather than in the timing."""
        simd = SIMDOptimizer()
        pts, e_u = BM.run_uniform(ASYM, BOUNDS, 8, simd=simd)
        e_again = simd.calculateFieldChunk({"points": pts},
                                           ASYM)["electricField"]
        np.testing.assert_allclose(np.array(e_u), np.array(e_again),
                                   rtol=1e-12)


class TestSuiteIsLoaded(unittest.TestCase):
    """P-STALE-PATH: a class defined after unittest.main() never runs."""

    def test_every_declared_test_is_collected(self):
        src = open(__file__).read()
        declared = src.count("\n    def test_")
        loaded = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__]).countTestCases()
        self.assertEqual(declared, loaded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
