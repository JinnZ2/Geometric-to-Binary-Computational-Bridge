"""ILLUSTRATIVE numerical fixtures, not empirical or semantic validation.

Run from repository root: python tests/test_experiment_bridge_core.py
"""

from copy import deepcopy
from dataclasses import FrozenInstanceError
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.v1.core import (  # noqa: E402
    Level, calibrate_thresholds, make_level, validate_trace, walk,
)


class TestLevel(unittest.TestCase):
    def test_defensive_immutable_direct_construction(self):
        source = [[1, 2], [3, 4]]
        level = Level(source, 2, "illustrative")
        source[0][0] = 99
        source.append([5, 6])
        self.assertEqual(level.codebook, ((1.0, 2.0), (3.0, 4.0)))
        with self.assertRaises(FrozenInstanceError):
            level.threshold_squared = 3
        with self.assertRaises(TypeError):
            level.codebook[0][0] = 3

    def test_direct_construction_rejects_invalid(self):
        for book, threshold, label in (([], 0, ""), ([[1], [1, 2]], 0, ""),
                                       ([[True]], 0, ""), ([[1]], -1, ""),
                                       ([[1]], float("inf"), ""), ([[1]], 0, None)):
            with self.subTest(book=book, threshold=threshold):
                with self.assertRaises(ValueError):
                    Level(book, threshold, label)

    def test_canonical_hash_is_order_sensitive(self):
        level = make_level([[1], [2]], 0)
        expected = hashlib.sha256(b"[[1.0],[2.0]]").hexdigest()
        self.assertEqual(level.codebook_sha256, expected)
        self.assertEqual(level.codebook_sha256, make_level([[1.0], [2.0]], 9).codebook_sha256)
        self.assertNotEqual(level.codebook_sha256, make_level([[2], [1]], 0).codebook_sha256)

    def test_empty_ragged_unordered_and_nonreal_books(self):
        for book in (None, [], [[]], [[1], []], [[1], [1, 2]], "1", {1}, {"a": [1]},
                     [["1"]], [[True]], [[None]], [[1 + 0j]], [[float("nan")]],
                     [[float("inf")]], [[-float("inf")]], [[10 ** 400]]):
            with self.subTest(book=book):
                with self.assertRaises(ValueError):
                    make_level(book, 0)

    def test_invalid_thresholds(self):
        for threshold in (-1, True, False, "0", None, float("nan"), float("inf"),
                          -float("inf"), 10 ** 400):
            with self.subTest(threshold=threshold):
                with self.assertRaises(ValueError):
                    make_level([[1]], threshold)

    def test_ordered_one_shot_inputs_and_real_fraction(self):
        book = (iter(row) for row in [[Fraction(1, 2)], [2]])
        level = make_level(book, Fraction(1, 4))
        self.assertEqual(level.codebook, ((0.5,), (2.0,)))
        self.assertEqual(level.threshold_squared, 0.25)
        self.assertEqual(walk(iter([0.5]), iter([level]))["residual"], [0.0])


class TestWalk(unittest.TestCase):
    def test_accepted_trace_fields_and_signed_reduction(self):
        levels = [make_level([[1, 0], [0, 1]], 0.25), make_level([[0.25, 0]], 0)]
        trace = walk([1.25, 0], levels)
        self.assertEqual(trace["version"], "experiment-bridge/v1")
        self.assertEqual(trace["dimension"], 2)
        self.assertEqual(trace["reconstruction"], [1.25, 0.0])
        self.assertEqual(trace["residual"], [0.0, 0.0])
        self.assertEqual([step["level"] for step in trace["steps"]], [1, 2])
        step = trace["steps"][0]
        self.assertEqual(step["distance_squared"], 0.0625)
        self.assertEqual(step["error_squared_before"], 1.5625)
        self.assertEqual(step["error_squared_after"], 0.0625)
        self.assertEqual(step["error_reduction"], 1.5)
        self.assertEqual(step["numerical_status"], "ACCEPTED")
        self.assertEqual(step["code_index"], 0)
        self.assertEqual(validate_trace(trace), [])
        self.assertEqual(validate_trace(trace, levels), [])
        json.dumps(trace, allow_nan=False)

    def test_rejection_null_zero_unchanged_and_next_stage(self):
        levels = [make_level([[2, 0]], 0.25), make_level([[0.25, 0]], 0)]
        trace = walk([0.25, 0], levels)
        step = trace["steps"][0]
        self.assertEqual(step["numerical_status"], "REJECTED")
        self.assertEqual(step["nearest_index"], 0)
        self.assertIsNone(step["code_index"])
        self.assertEqual(step["contribution"], [0, 0])
        self.assertEqual(step["residual_before"], step["residual_after"])
        self.assertEqual(step["reconstruction_before"], step["reconstruction_after"])
        self.assertEqual(step["error_reduction"], 0)
        self.assertEqual(trace["steps"][1]["residual_before"], [0.25, 0])
        self.assertEqual(trace["residual"], [0, 0])
        self.assertEqual(validate_trace(trace, levels), [])

    def test_exact_ties_use_first_code(self):
        trace = walk([0], [make_level([[-1], [1]], 1)])
        self.assertEqual(trace["steps"][0]["nearest_index"], 0)
        self.assertEqual(trace["reconstruction"], [-1])

    def test_zero_vector_is_a_normal_code_not_rejection(self):
        trace = walk([0], [make_level([[0], [2]], 0)])
        self.assertEqual(trace["steps"][0]["numerical_status"], "ACCEPTED")
        self.assertEqual(trace["steps"][0]["code_index"], 0)

    def test_accepted_squared_error_can_increase(self):
        levels = [make_level([[3]], 4)]
        trace = walk([1], levels)
        step = trace["steps"][0]
        self.assertEqual(step["numerical_status"], "ACCEPTED")
        self.assertEqual((step["error_squared_before"], step["error_squared_after"]), (1, 4))
        self.assertEqual(step["error_reduction"], -3)
        self.assertEqual(validate_trace(trace, levels), [])

    def test_target_and_level_validation(self):
        for target, levels in (([], [make_level([[0]], 0)]), ([1], []), ([1], [None]),
                               ([1], [make_level([[1, 2]], 0)]), ([True], [make_level([[0]], 0)]),
                               ([float("nan")], [make_level([[0]], 0)]),
                               ([float("inf")], [make_level([[0]], 0)]),
                               (["1"], [make_level([[0]], 0)]), (None, [make_level([[0]], 0)])):
            with self.subTest(target=target):
                with self.assertRaises(ValueError):
                    walk(target, levels)

    def test_rechecks_levels_even_if_frozen_safeguard_bypassed(self):
        level = make_level([[0]], 0)
        object.__setattr__(level, "threshold_squared", True)
        with self.assertRaises(ValueError):
            walk([0], [level])

    def test_finite_arithmetic_overflow_rejected(self):
        fixtures = (([1e308], [[0]], 0), ([1e154, 1e154], [[0, 0]], 0),
                    ([0], [[1e308]], 0), ([0], [[0], [1e308]], 0))
        for target, book, threshold in fixtures:
            with self.subTest(target=target, book=book):
                with self.assertRaises(ValueError):
                    walk(target, [make_level(book, threshold)])

    def test_binary64_roundoff_and_input_isolation(self):
        target = [0.3]
        levels = [make_level([[0.1]], 1), make_level([[0.2]], 1)]
        trace = walk(target, levels)
        self.assertEqual(validate_trace(trace, levels), [])
        target[0] = 99
        trace["steps"][0]["contribution"][0] = 88
        self.assertEqual(levels[0].codebook, ((0.1,),))
        self.assertEqual(trace["target"], [0.3])


class TestTraceAudit(unittest.TestCase):
    def setUp(self):
        self.levels = [make_level([[1, 0]], 1), make_level([[0.25, 0]], 0)]
        self.trace = walk([1.25, 0], self.levels)

    def test_over_threshold_accepted_transition_detected(self):
        trace = walk([1], [make_level([[3]], 4)])
        trace["steps"][0]["threshold_squared"] = 3
        self.assertTrue(validate_trace(trace))
        self.assertTrue(validate_trace(trace, [make_level([[3]], 3)]))

    def test_stale_residual_and_dimension_mismatch(self):
        for key, value in (("residual_before", [1.25, 0]), ("residual_after", [9, 0]),
                           ("contribution", [0.25]), ("reconstruction_before", [9, 0])):
            trace = deepcopy(self.trace)
            trace["steps"][1][key] = value
            self.assertTrue(validate_trace(trace), key)
            self.assertTrue(validate_trace(trace, self.levels), key)

    def test_recorded_errors_and_additive_identity_recomputed(self):
        for key, value in (("error_squared_before", 99), ("error_squared_after", 99),
                           ("error_reduction", 99), ("reconstruction_after", [99, 0]),
                           ("distance_squared", 0.5), ("code_index", None),
                           ("nearest_index", True), ("numerical_status", "UNMAPPED")):
            trace = deepcopy(self.trace)
            trace["steps"][0][key] = value
            self.assertTrue(validate_trace(trace), key)

    def test_rejected_nonzero_or_indexed_transition_detected(self):
        trace = walk([0], [make_level([[2]], 0)])
        for key, value in (("contribution", [2]), ("code_index", 0)):
            altered = deepcopy(trace)
            altered["steps"][0][key] = value
            self.assertTrue(validate_trace(altered))

    def test_missing_and_wrong_actual_hash(self):
        trace = deepcopy(self.trace)
        del trace["steps"][0]["codebook_sha256"]
        self.assertTrue(validate_trace(trace))
        trace = deepcopy(self.trace)
        trace["steps"][0]["codebook_sha256"] = "0" * 64
        self.assertEqual(validate_trace(trace), [])  # Presence alone cannot establish identity.
        self.assertTrue(validate_trace(trace, self.levels))

    def test_actual_tie_routing_threshold_and_count(self):
        levels = [make_level([[-1], [1]], 1)]
        trace = walk([0], levels)
        for key, value in (("nearest_index", 1), ("threshold_squared", 2)):
            altered = deepcopy(trace)
            altered["steps"][0][key] = value
            if key == "nearest_index":
                altered["steps"][0]["code_index"] = 1
            self.assertEqual(validate_trace(altered), [])
            self.assertTrue(validate_trace(altered, levels))
        self.assertTrue(validate_trace(self.trace, self.levels[:1]))
        self.assertTrue(validate_trace(self.trace, self.levels + [make_level([[0, 0]], 0)]))

    def test_self_consistent_wrong_code_does_not_pass_actual_audit(self):
        intended = [make_level([[1], [3]], 9)]
        fabricated = walk([1], [make_level([[3]], 9)])
        fabricated["steps"][0]["codebook_sha256"] = intended[0].codebook_sha256
        self.assertEqual(validate_trace(fabricated), [])
        self.assertTrue(validate_trace(fabricated, intended))

    def test_malformed_trace_returns_diagnostics_without_mutating(self):
        for trace in (None, [], {}, {"target": [0]}, {**self.trace, "steps": []},
                      {**self.trace, "steps": [None]}, {**self.trace, "dimension": True},
                      {**self.trace, "version": "wrong"}, {**self.trace, "target": [float("nan")]},
                      {**self.trace, "residual": [0]}, {**self.trace, "reconstruction": [9, 0]}):
            self.assertTrue(validate_trace(trace))
        original = deepcopy(self.trace)
        self.assertEqual(validate_trace(self.trace, iter(self.levels)), [])
        self.assertEqual(self.trace, original)
        self.assertTrue(validate_trace(self.trace, []))

    def test_every_required_step_field_checked(self):
        for key in self.trace["steps"][0]:
            trace = deepcopy(self.trace)
            del trace["steps"][0][key]
            self.assertTrue(validate_trace(trace), key)

    def test_nonfinite_boolean_and_bad_shapes_in_trace(self):
        for key, value in (("threshold_squared", float("inf")), ("distance_squared", True),
                           ("error_squared_before", float("nan")), ("level", False),
                           ("codebook_sha256", []), ("code_index", True),
                           ("contribution", [True, 0]), ("residual_before", [[1], 0])):
            trace = deepcopy(self.trace)
            trace["steps"][0][key] = value
            self.assertTrue(validate_trace(trace), key)


class TestCalibration(unittest.TestCase):
    def test_ordered_squared_quantile_and_zero_rejection(self):
        samples, books = [[0], [1], [2], [3]], [[[0]]]
        self.assertEqual(calibrate_thresholds(samples, books, 0.25), (4.0,))
        self.assertEqual(calibrate_thresholds(samples, books, 0), (9.0,))
        self.assertEqual(calibrate_thresholds(samples, books, 0.99), (0.0,))

    def test_discrete_sample_limit_and_ties(self):
        self.assertEqual(calibrate_thresholds([[0], [1]], [[[0]]], 0.1), (1.0,))
        self.assertEqual(calibrate_thresholds([[0], [1], [1], [1]], [[[0]]], 0.5), (1.0,))
        self.assertEqual(calibrate_thresholds([[2]], [[[0]]], 0.999), (4.0,))

    def test_gated_earlier_rejection_preserves_trajectory(self):
        samples, books = [[0], [2], [10]], [[[2]], [[4]]]
        self.assertEqual(calibrate_thresholds(samples, books, 0.34), (4.0, 36.0))
        self.assertEqual(calibrate_thresholds(samples, books, 0.34, gated=False), (4.0, 16.0))
        thresholds = calibrate_thresholds(samples, books, 0.34)
        trace = walk([10], [make_level(book, threshold) for book, threshold in zip(books, thresholds)])
        self.assertEqual(trace["steps"][0]["residual_after"], [10])
        self.assertEqual(trace["steps"][1]["distance_squared"], 36)

    def test_one_shot_inputs_copied_once(self):
        samples = (iter(row) for row in [[0], [1]])
        books = ((iter(row) for row in [[0]]),)
        self.assertEqual(calibrate_thresholds(samples, iter(books), 0), (1.0,))

    def test_invalid_fraction_and_gated_flag(self):
        for fraction in (-0.1, 1, 2, True, float("nan"), float("inf"), "0"):
            with self.subTest(fraction=fraction):
                with self.assertRaises(ValueError):
                    calibrate_thresholds([[0]], [[[0]]], fraction)
        for flag in (0, 1, None, "yes"):
            with self.assertRaises(ValueError):
                calibrate_thresholds([[0]], [[[0]]], 0, gated=flag)

    def test_empty_dimension_nonfinite_and_overflow_rejected(self):
        for samples, books in (([], [[[0]]]), ([[0]], []), ([[0]], [[]]),
                               ([[0], [0, 1]], [[[0]]]), ([[0]], [[[0, 1]]]),
                               ([[True]], [[[0]]]), ([[float("inf")]], [[[0]]]),
                               ([[0]], [[[float("nan")]]]), ([[1e308]], [[[0]]]),
                               ([[0]], [[[1e308]]])):
            with self.subTest(samples=samples, books=books):
                with self.assertRaises(ValueError):
                    calibrate_thresholds(samples, books, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
