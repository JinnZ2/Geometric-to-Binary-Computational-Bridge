"""Tests for mappings/six_sigma_audit.py"""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mappings.six_sigma_audit import (
    defect_rate,
    process_capability,
    handshake,
    stress_test,
    TOLERANCES,
)
from mappings.field_system import SCENARIOS, fill_state


class TestDefectRate(unittest.TestCase):
    def test_returns_dict_with_keys(self):
        state = SCENARIOS["sovereign_steward"]["state"]
        dr = defect_rate(state)
        self.assertIn("details", dr)
        self.assertIn("defects", dr)
        self.assertIn("total", dr)
        self.assertIn("defect_rate", dr)

    def test_per_variable_results(self):
        state = SCENARIOS["sovereign_steward"]["state"]
        dr = defect_rate(state)
        for key in TOLERANCES:
            self.assertIn(key, dr["details"])
            entry = dr["details"][key]
            self.assertIn("pass", entry)
            self.assertIn("value", entry)
            self.assertIsInstance(entry["pass"], bool)

    def test_defect_rate_range(self):
        state = SCENARIOS["big_ag_bot"]["state"]
        dr = defect_rate(state)
        self.assertGreaterEqual(dr["defect_rate"], 0.0)
        self.assertLessEqual(dr["defect_rate"], 1.0)

    def test_good_state_low_defect_rate(self):
        state = SCENARIOS["sovereign_steward"]["state"]
        dr = defect_rate(state)
        self.assertLessEqual(dr["defect_rate"], 0.5)

    def test_bad_state_higher_defect_rate(self):
        state = SCENARIOS["big_ag_bot"]["state"]
        dr = defect_rate(state)
        self.assertGreater(dr["defect_rate"], 0.0)


class TestProcessCapability(unittest.TestCase):
    def test_returns_dict_with_cp(self):
        state = SCENARIOS["sovereign_steward"]["state"]
        cp = process_capability(state)
        self.assertIsInstance(cp, dict)
        for key in TOLERANCES:
            self.assertIn(key, cp)
            self.assertIn("cp", cp[key])
            self.assertIsInstance(cp[key]["cp"], float)

    def test_good_state_positive_cp(self):
        state = SCENARIOS["sovereign_steward"]["state"]
        cp = process_capability(state)
        positive_count = sum(1 for v in cp.values() if v["cp"] >= 0)
        self.assertGreater(positive_count, len(cp) // 2)


class TestHandshake(unittest.TestCase):
    def test_state_only(self):
        result = handshake(state=SCENARIOS["sovereign_steward"]["state"])
        self.assertIn("verdict", result)
        self.assertIn("flags", result)
        self.assertIsNotNone(result["field"])
        self.assertIsNone(result["narrative"])

    def test_text_only(self):
        result = handshake(text="Profits always increase with optimization.")
        self.assertIsNotNone(result["narrative"])
        self.assertIsNone(result["field"])

    def test_combined(self):
        result = handshake(
            text="Profits always increase.",
            state=SCENARIOS["big_ag_bot"]["state"],
        )
        self.assertIsNotNone(result["narrative"])
        self.assertIsNotNone(result["field"])
        self.assertIn("verdict", result)


class TestStressTest(unittest.TestCase):
    def test_pipeline_runs(self):
        claim = "AI will increase productivity 270% by 2030."
        result = stress_test(
            claim_text=claim,
            claimed_state=SCENARIOS["corporate_270"]["state"],
            label="test_claim",
        )
        self.assertIn("label", result)
        self.assertEqual(result["label"], "test_claim")
        self.assertIn("handshake", result)
        self.assertIn("h_total", result)
        self.assertIsInstance(result["h_total"], float)
        self.assertIn("benchmarks", result)
        self.assertIn("ratio_vs_steward", result)

    def test_ratio_is_positive(self):
        claim = "Test claim"
        result = stress_test(
            claim_text=claim,
            claimed_state=SCENARIOS["sovereign_steward"]["state"],
            label="steward_self_check",
        )
        self.assertGreater(result["ratio_vs_steward"], 0)


if __name__ == "__main__":
    unittest.main()
