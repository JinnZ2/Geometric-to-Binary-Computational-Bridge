"""Tests for mappings/field_system.py"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mappings.field_system import (
    fill_state,
    regen_capacity,
    constraints,
    score,
    compare_scenarios,
    effective_yield,
    thermal_limit_check,
    drift,
    suggest,
    report,
    SCENARIOS,
    DEFAULTS,
)


class TestFillState(unittest.TestCase):
    def test_empty_input_returns_defaults(self):
        result = fill_state({})
        self.assertIsInstance(result, dict)
        for k in DEFAULTS:
            self.assertIn(k, result)
            self.assertAlmostEqual(result[k], float(DEFAULTS[k]))

    def test_partial_input_fills_missing(self):
        result = fill_state({"soil_trend": 0.5})
        self.assertAlmostEqual(result["soil_trend"], 0.5)
        self.assertAlmostEqual(result["water_retention"], float(DEFAULTS["water_retention"]))


class TestRegenCapacity(unittest.TestCase):
    def test_returns_float(self):
        state = fill_state({})
        rc = regen_capacity(state)
        self.assertIsInstance(rc, float)

    def test_positive_for_defaults(self):
        state = fill_state({})
        self.assertGreater(regen_capacity(state), 0)

    def test_zero_disturbance_no_penalty(self):
        state = fill_state({"disturbance": 0.0, "soil_trend": 0.0, "water_retention": 1.0})
        self.assertAlmostEqual(regen_capacity(state), 1.0)


class TestConstraints(unittest.TestCase):
    def test_returns_dict_of_bools(self):
        state = fill_state({})
        c = constraints(state)
        self.assertIsInstance(c, dict)
        for v in c.values():
            self.assertIsInstance(v, (bool, int))

    def test_good_state_all_pass(self):
        state = fill_state({
            "soil_trend": 0.1,
            "water_retention": 0.7,
            "input_energy": 0.5,
            "output_yield": 0.4,
            "disturbance": 0.0,
        })
        c = constraints(state)
        self.assertTrue(c["soil_positive"])
        self.assertTrue(c["water_non_degrading"])


class TestScore(unittest.TestCase):
    def test_returns_float(self):
        state = fill_state({})
        s = score(state)
        self.assertIsInstance(s, float)

    def test_range_0_to_1(self):
        state = fill_state({})
        s = score(state)
        self.assertGreaterEqual(s, 0.0)
        self.assertLessEqual(s, 1.0)


class TestEffectiveYield(unittest.TestCase):
    def test_returns_dict(self):
        state = fill_state({})
        ey = effective_yield(state)
        self.assertIn("adjusted_yield", ey)
        self.assertIn("effective_yield_per_acre", ey)
        self.assertIn("total_nourishment_units", ey)

    def test_nourishment_positive(self):
        state = fill_state({})
        ey = effective_yield(state)
        self.assertGreater(ey["total_nourishment_units"], 0)


class TestThermalLimitCheck(unittest.TestCase):
    def test_returns_dict(self):
        state = fill_state({})
        result = thermal_limit_check(state)
        self.assertIn("prediction_error", result)
        self.assertIn("thermal_load", result)
        self.assertIn("critical_alert", result)

    def test_high_disturbance_triggers_alert(self):
        state = fill_state({"disturbance": 0.9, "input_energy": 2.0})
        result = thermal_limit_check(state)
        self.assertTrue(result["critical_alert"])


class TestCompareScenarios(unittest.TestCase):
    def test_known_scenarios(self):
        results = compare_scenarios("big_ag_bot", "sovereign_steward")
        self.assertIn("big_ag_bot", results)
        self.assertIn("sovereign_steward", results)
        for name, r in results.items():
            self.assertIn("score", r)
            self.assertIn("label", r)

    def test_steward_scores_higher(self):
        results = compare_scenarios("big_ag_bot", "sovereign_steward")
        self.assertGreater(
            results["sovereign_steward"]["score"],
            results["big_ag_bot"]["score"],
        )


class TestReport(unittest.TestCase):
    def test_full_report(self):
        r = report(SCENARIOS["sovereign_steward"]["state"])
        self.assertIn("state", r)
        self.assertIn("constraints", r)
        self.assertIn("drift", r)
        self.assertIn("score", r)
        self.assertIn("yield_analysis", r)
        self.assertIn("thermal_limit", r)


if __name__ == "__main__":
    unittest.main()
