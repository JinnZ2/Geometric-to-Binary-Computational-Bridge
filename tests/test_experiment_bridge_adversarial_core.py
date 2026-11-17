"""ILLUSTRATIVE software fixtures, not empirical/statistical validation.

Run from repository root: python tests/test_experiment_bridge_adversarial_core.py
All nonterminating iterator probes use subprocess hard timeouts. Seeded random
cases are finite dyadic software regressions, not a scientific data sweep.
"""

from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import random
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.v1 import core as old  # noqa: E402
from experiments.experiment_bridge.v1_1 import core as new  # noqa: E402
from experiments.experiment_bridge.adversarial.core_probe import run_worker  # noqa: E402


class TestAdversarialCoreNumerics(unittest.TestCase):
    def test_constants_are_explicit(self):
        self.assertEqual(new.VERSION, "experiment-bridge/v1.1")
        self.assertEqual(old.VERSION, "experiment-bridge/v1")
        self.assertEqual((new.MAX_ITERABLE_ITEMS, new.MAX_DIMENSION, new.MAX_CODES,
                          new.MAX_LEVELS, new.MAX_SAMPLES), (4096, 4096, 4096, 64, 4096))
        self.assertEqual((new.TRACE_REL_TOL, new.TRACE_ABS_TOL), (1e-12, 1e-12))

    def test_zero_threshold_underflow_reproduces_and_is_rejected(self):
        fixtures = (([1e-200], [[0]], 0), ([1, 0], [[1, 1e-200]], 0))
        for target, book, threshold in fixtures:
            with self.subTest(target=target):
                levels = [old.make_level(book, threshold)]
                trace = old.walk(target, levels)
                self.assertEqual(trace["steps"][0]["distance_squared"], 0)
                self.assertEqual(trace["steps"][0]["numerical_status"], "ACCEPTED")
                self.assertEqual(old.validate_trace(trace, levels), [])
                with self.assertRaisesRegex(ValueError, "underflow"):
                    new.walk(target, [new.make_level(book, threshold)])

    def test_partial_component_underflow_is_conservatively_rejected(self):
        self.assertEqual(old.walk([1, 1e-200], [old.make_level([[0, 0]], 1)])
                         ["steps"][0]["distance_squared"], 1)
        with self.assertRaisesRegex(ValueError, "underflow"):
            new.walk([1, 1e-200], [new.make_level([[0, 0]], 1)])

    def test_nonzero_subnormal_square_is_not_rejected_as_underflow(self):
        for core in (old, new):
            trace = core.walk([1e-160], [core.make_level([[0]], 0)])
            self.assertGreater(trace["steps"][0]["distance_squared"], 0)
            self.assertEqual(trace["steps"][0]["numerical_status"], "REJECTED")

    def test_decimal_threshold_roundoff_is_preserved(self):
        for core in (old, new):
            trace = core.walk([0.1], [core.make_level([[0]], 0.01)])
            self.assertGreater(trace["steps"][0]["distance_squared"], 0.01)
            self.assertEqual(trace["steps"][0]["numerical_status"], "REJECTED")

    def test_lossy_integer_target_old_acceptance_new_rejection(self):
        original = 2**53 + 1
        trace = old.walk([original], [old.make_level([[2**53]], 0)])
        self.assertNotEqual(int(trace["target"][0]), original)
        self.assertEqual(trace["steps"][0]["numerical_status"], "ACCEPTED")
        with self.assertRaisesRegex(ValueError, "integer cannot be represented exactly"):
            new.walk([original], [new.make_level([[2**53]], 0)])

    def test_lossy_integers_are_rejected_in_all_numeric_input_roles(self):
        value = 2**1000 + 1
        calls = (lambda: new.make_level([[value]], 0),
                 lambda: new.make_level([[0]], value),
                 lambda: new.calibrate_thresholds([[2**53 + 1]], [[[2**53]]], 0),
                 lambda: new.calibrate_thresholds([[0]], [[[2**53 + 1]]], 0),
                 lambda: new.calibrate_thresholds([[0]], [[[0]]], 2**53 + 1))
        self.assertNotEqual(int(old.make_level([[value]], 0).codebook[0][0]), value)
        for call in calls:
            with self.subTest(call=call):
                with self.assertRaisesRegex(ValueError, "integer cannot be represented exactly"):
                    call()

    def test_exact_large_integers_remain_supported_for_conversion(self):
        for value in (2**53, 2**53 + 2, -(2**53 + 2), 2**1000):
            with self.subTest(value=value):
                self.assertEqual(int(new.make_level([[value]], 0).codebook[0][0]), value)
        self.assertEqual(new.walk([2**53], [new.make_level([[2**53]], 0)])["residual"], [0])
        # Conversion support is not a promise that a subsequent square fits.
        with self.assertRaises(ValueError):
            new.walk([2**1000], [new.make_level([[0]], 0)])

    def test_expected_invalid_inputs_and_overflow_stay_rejected(self):
        for core in (old, new):
            for value in (True, None, "1", 1 + 0j, float("nan"), float("inf"), 10**400):
                with self.subTest(core=core.VERSION, value=value):
                    with self.assertRaises(ValueError):
                        core.make_level([[value]], 0)
            with self.assertRaises(ValueError):
                core.walk([1e308], [core.make_level([[0]], 0)])

    def test_fraction_rounding_and_ordinary_float_roundoff_remain_explicit(self):
        level = new.make_level([[Fraction(1, 10)]], 0)
        self.assertEqual(level.codebook, ((0.1,),))
        self.assertEqual(new.walk([0.1], [level])["residual"], [0])
        levels = [new.make_level([[0.1]], 1), new.make_level([[0.2]], 1)]
        trace = new.walk([0.3], levels)
        self.assertNotEqual(trace["residual"], [0])
        self.assertEqual(new.validate_trace(trace, levels), [])

    def test_cancellation_old_produces_self_invalid_trace_new_fails_closed(self):
        levels = [old.make_level([[1e16]], 1e32), old.make_level([[-1e16]], 1e32)]
        trace = old.walk([1], levels)
        self.assertEqual(trace["reconstruction"], [0])
        self.assertEqual(trace["residual"], [0])
        self.assertIn("step 2: additive identity mismatch", old.validate_trace(trace, levels))
        with self.assertRaisesRegex(ValueError, "additive identity outside"):
            new.walk([1], [new.make_level([[1e16]], 1e32), new.make_level([[-1e16]], 1e32)])

    def test_cancellation_inside_tolerance_is_not_claimed_exact(self):
        levels = [new.make_level([[1e16]], 1e32), new.make_level([[-1e16]], 1e32)]
        trace = new.walk([1e-13], levels)
        self.assertNotEqual(trace["target"][0], trace["reconstruction"][0] + trace["residual"][0])
        self.assertEqual(new.validate_trace(trace, levels), [])

    def test_rejection_ties_and_negative_reduction_keep_original_metric(self):
        for core in (old, new):
            trace = core.walk([0], [core.make_level([[-1], [1]], 1)])
            self.assertEqual(trace["steps"][0]["nearest_index"], 0)
            trace = core.walk([1], [core.make_level([[3]], 4)])
            self.assertEqual(trace["steps"][0]["error_reduction"], -3)
            trace = core.walk([1], [core.make_level([[3]], 3)])
            self.assertEqual(trace["steps"][0]["numerical_status"], "REJECTED")
            self.assertEqual(trace["steps"][0]["contribution"], [0])
            self.assertIsNone(trace["steps"][0]["code_index"])
            self.assertEqual(trace["residual"], [1])

    def test_finite_seeded_dyadic_regressions_match_legacy(self):
        rng = random.Random(20261117)
        for case in range(512):
            dimension = rng.randint(1, 8)
            target = [rng.randint(-32, 32) / 4 for _ in range(dimension)]
            specs = [([[rng.randint(-24, 24) / 4 for _ in range(dimension)]
                       for _ in range(rng.randint(1, 6))], rng.randint(0, 1024) / 4)
                     for _ in range(rng.randint(1, 5))]
            old_levels = [old.make_level(book, threshold) for book, threshold in specs]
            new_levels = [new.make_level(book, threshold) for book, threshold in specs]
            legacy, candidate = old.walk(target, old_levels), new.walk(target, new_levels)
            with self.subTest(software_case=case):
                self.assertEqual(old.validate_trace(legacy, old_levels), [])
                self.assertEqual(new.validate_trace(candidate, new_levels), [])
                candidate["version"] = old.VERSION
                self.assertEqual(candidate, legacy)
            samples = [target, [rng.randint(-32, 32) / 4 for _ in range(dimension)]]
            books = [book for book, _ in specs]
            self.assertEqual(new.calibrate_thresholds(samples, books, 0.5),
                             old.calibrate_thresholds(samples, books, 0.5))


class TestAdversarialCoreBounds(unittest.TestCase):
    def test_dimension_boundary(self):
        trace = new.walk([0] * 4096, [new.make_level([[0] * 4096], 0)])
        self.assertEqual(trace["dimension"], 4096)
        with self.assertRaisesRegex(ValueError, "vector exceeds limit"):
            new.walk([0] * 4097, [new.make_level([[0]], 0)])
        with self.assertRaisesRegex(ValueError, "vector exceeds limit"):
            new.make_level([[0] * 4097], 0)

    def test_code_count_boundary(self):
        self.assertEqual(len(new.make_level([[0]] * 4096, 0).codebook), 4096)
        with self.assertRaisesRegex(ValueError, "codebook exceeds limit"):
            new.make_level([[0]] * 4097, 0)

    def test_level_count_boundary(self):
        level = new.make_level([[0]], 0)
        self.assertEqual(len(new.walk([0], [level] * 64)["steps"]), 64)
        with self.assertRaisesRegex(ValueError, "levels exceeds limit"):
            new.walk([0], [level] * 65)

    def test_calibration_boundaries(self):
        self.assertEqual(new.calibrate_thresholds([[0]] * 4096, [[[0]]], 0), (0,))
        self.assertEqual(len(new.calibrate_thresholds([[0]], [[[0]]] * 64, 0)), 64)
        with self.assertRaisesRegex(ValueError, "samples exceeds limit"):
            new.calibrate_thresholds([[0]] * 4097, [[[0]]], 0)
        with self.assertRaisesRegex(ValueError, "codebooks exceeds limit"):
            new.calibrate_thresholds([[0]], [[[0]]] * 65, 0)

    def test_finite_iterable_consumption_stops_after_limit_plus_one(self):
        consumed = []
        def finite_numbers():
            for i in range(10000):
                consumed.append(i)
                yield 0
        with self.assertRaises(ValueError):
            new.walk(finite_numbers(), [new.make_level([[0]], 0)])
        self.assertEqual(len(consumed), 4097)
        consumed.clear()
        def finite_levels():
            level = new.make_level([[0]], 0)
            for i in range(1000):
                consumed.append(i)
                yield level
        with self.assertRaises(ValueError):
            new.walk([0], finite_levels())
        self.assertEqual(len(consumed), 65)

    def test_nonterminating_probes_only_run_under_hard_subprocess_timeout(self):
        for name in ("infinite_target", "infinite_codes", "infinite_levels", "infinite_generator_steps"):
            with self.subTest(probe=name):
                self.assertEqual(run_worker("legacy", name, 2)["outcome"], "TIMEOUT")
                expected = "DIAGNOSTICS" if name.endswith("steps") else "ValueError"
                self.assertEqual(run_worker("candidate", name, 2)["outcome"], expected)

    def test_one_shot_ordered_inputs_and_defensive_copy(self):
        consumed = []
        def row():
            for value in (1, 2):
                consumed.append(value)
                yield value
        level = new.make_level(iter([row()]), 0)
        self.assertEqual(consumed, [1, 2])
        trace = new.walk(iter([1, 2]), iter([level]))
        self.assertEqual(trace["residual"], [0, 0])
        trace["steps"][0]["contribution"][0] = 99
        self.assertEqual(level.codebook, ((1.0, 2.0),))


class TestAdversarialCoreTrace(unittest.TestCase):
    def setUp(self):
        self.levels = [new.make_level([[0]], 2)]
        self.trace = new.walk([1], self.levels)

    def test_small_final_and_step_mutations_pass_documented_tolerance(self):
        for location in ("final", "step"):
            trace = deepcopy(self.trace)
            if location == "final":
                trace["reconstruction"][0] += 5e-13
            else:
                trace["steps"][0]["reconstruction_after"][0] += 5e-13
            self.assertEqual(new.validate_trace(trace, self.levels), [])
        trace = deepcopy(self.trace)
        trace["reconstruction"][0] += 5e-11
        self.assertIn("final reconstruction mismatch", new.validate_trace(trace, self.levels))

    def test_small_distance_mutation_without_levels_passes_but_actual_check_rejects(self):
        trace = deepcopy(self.trace)
        trace["steps"][0]["distance_squared"] += 5e-13
        self.assertEqual(new.validate_trace(trace), [])
        self.assertIn("step 1: actual nearest/distance mismatch", new.validate_trace(trace, self.levels))

    def test_ordinary_failed_iterators_return_diagnostics(self):
        def failed():
            yield 1
            raise RuntimeError("ILLUSTRATIVE iterator failure")
        for location in ("target", "step", "levels"):
            trace = deepcopy(self.trace)
            levels = self.levels
            if location == "target":
                trace["target"] = failed()
            elif location == "step":
                trace["steps"][0]["contribution"] = failed()
            else:
                levels = failed()
            self.assertTrue(new.validate_trace(trace, levels))

    def test_wrong_steps_type_is_rejected_without_consumption(self):
        consumed = []
        def finite_steps():
            consumed.append(1)
            yield self.trace["steps"][0]
        trace = deepcopy(self.trace)
        trace["steps"] = finite_steps()
        self.assertTrue(new.validate_trace(trace))
        self.assertEqual(consumed, [])

    def test_step_limit_is_a_diagnostic(self):
        trace = new.walk([0], [new.make_level([[0]], 0)])
        trace["steps"] = [deepcopy(trace["steps"][0]) for _ in range(65)]
        for i, step in enumerate(trace["steps"], 1):
            step["level"] = i
        self.assertTrue(any("steps exceeds limit" in error for error in new.validate_trace(trace)))

    def test_missing_all_required_top_and_step_fields_are_diagnostics(self):
        for key in self.trace:
            trace = deepcopy(self.trace)
            del trace[key]
            self.assertTrue(new.validate_trace(trace, self.levels), key)
        for key in self.trace["steps"][0]:
            trace = deepcopy(self.trace)
            del trace["steps"][0][key]
            self.assertTrue(new.validate_trace(trace, self.levels), key)

    def test_malformed_structured_trace_cases_are_diagnostics(self):
        fixtures = [None, [], {}, {**self.trace, "target": [[1]]},
                    {**self.trace, "steps": [None]}, {**self.trace, "steps": []},
                    {**self.trace, "dimension": True}, {**self.trace, "residual": [False]},
                    {**self.trace, "version": []}, {**self.trace, "target": {"x": 1}}]
        for trace in fixtures:
            self.assertTrue(new.validate_trace(trace, self.levels))
        for key, value in (("distance_squared", float("inf")), ("level", {}),
                           ("contribution", [[1]]), ("codebook_sha256", []),
                           ("numerical_status", []), ("nearest_index", True),
                           ("error_squared_after", float("nan"))):
            trace = deepcopy(self.trace)
            trace["steps"][0][key] = value
            self.assertTrue(new.validate_trace(trace, self.levels), key)

    def test_trace_validation_does_not_call_walk_or_mutate_trace(self):
        original = deepcopy(self.trace)
        with patch.object(new, "walk", side_effect=AssertionError("validator replayed producer")):
            self.assertEqual(new.validate_trace(self.trace, iter(self.levels)), [])
        self.assertEqual(self.trace, original)

    def test_legacy_underflow_trace_cannot_be_certified_by_candidate(self):
        trace = old.walk([1, 0], [old.make_level([[1, 1e-200]], 0)])
        trace["version"] = new.VERSION
        self.assertTrue(new.validate_trace(trace, [new.make_level([[1, 1e-200]], 0)]))

    def test_canonical_hash_is_unchanged_except_version_field(self):
        self.assertEqual(old.make_level([[1], [2]], 0).codebook_sha256,
                         new.make_level([[1], [2]], 0).codebook_sha256)
        self.assertEqual(new.make_level([[1], [2]], 0).codebook_sha256,
                         new.make_level([[1.0], [2.0]], 99).codebook_sha256)


if __name__ == "__main__":
    unittest.main(verbosity=2)
