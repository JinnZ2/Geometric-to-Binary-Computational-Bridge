"""ILLUSTRATIVE v1 integration gates; no real neural/semantic claims."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.experiment_bridge.v1.core import make_level, validate_trace, walk
from experiments.experiment_bridge.v1.demo import BENCH, main, run
from experiments.experiment_bridge.v1.semantics import annotate_trace, find_rows, normalize_reference
from experiments.experiment_bridge.v1.wire import decode_record, encode_record, RECORD_SIZE


class TestExperimentBridgeV1Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix="bridge-v1-integration-tests-")
        cls.summary = run(Path(cls.tmp.name) / "run")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_four_states_do_not_collapse(self):
        actual = [(c["step"]["numerical_status"], c["step"]["semantic_status"])
                  for c in self.summary["states"]]
        self.assertEqual(actual, [("ACCEPTED", "PRESENT"), ("REJECTED", "NOT_APPLICABLE"),
                                  ("ACCEPTED", "UNMAPPED"), ("ACCEPTED", "LEXICAL_VOID")])
        lexical = self.summary["states"][-1]["step"]
        self.assertEqual(lexical["contribution"], [1.0])
        mapped = self.summary["states"][0]["step"]["semantic_row"]
        self.assertEqual(mapped["source"]["mapping_status"], "PROPOSED")

    def test_actual_cobol_result_or_explicit_unavailability(self):
        result = self.summary["cobol"]
        if shutil.which("cobc"):
            self.assertEqual(result["status"], "PASS")
            self.assertTrue(result["exact_bytes_equal"])
            self.assertEqual(result["input_bytes"], 4 * RECORD_SIZE)
            self.assertEqual(Path(result["artifacts"]["input"]).read_bytes(),
                             Path(result["artifacts"]["output"]).read_bytes())
        else:
            self.assertEqual(result["status"], "NOT_RUNNABLE")
            self.assertIsNone(result["exact_bytes_equal"])

    def test_roundtrip_preserves_statuses_and_reference_wording(self):
        raw = json.loads((BENCH / "raw" / "lojban_wordslot_reference.json").read_text())
        rows = normalize_reference(raw)
        better = find_rows(rows, english="better", role="mapping")[0]
        trace = walk([0.15, 0.22, 0.28], [make_level([[0.1, 0.2, 0.3]], 0.09)])
        untouched = copy.deepcopy(trace)
        annotated = annotate_trace(trace, rows, {(1, 0): better["row_id"]})
        result = decode_record(encode_record(annotated))
        self.assertEqual(result, annotated)
        self.assertEqual(trace, untouched)
        self.assertEqual(result["steps"][0]["semantic_row"]["source"], better["source"])

    def test_negative_controls_fire(self):
        self.assertTrue(self.summary["broken_routing_detected"])
        self.assertTrue(self.summary["wire_tamper_detected"])
        intended = [make_level([[1], [3]], 9)]
        fabricated = walk([1], [make_level([[3]], 9)])
        fabricated["steps"][0]["codebook_sha256"] = intended[0].codebook_sha256
        self.assertEqual(validate_trace(fabricated), [])
        self.assertTrue(validate_trace(fabricated, intended))

    def test_existing_output_is_not_overwritten(self):
        with self.assertRaises(ValueError):
            run(Path(self.tmp.name) / "run")
        self.assertTrue((Path(self.tmp.name) / "run" / "summary.json").is_file())

    def test_received_and_prior_audit_directories_are_protected(self):
        for name in ("raw", "evidence", "audit"):
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    run(BENCH / name / "must-not-be-created")
                self.assertFalse((BENCH / name / "must-not-be-created").exists())

    def test_cli_compiler_failure_is_nonzero(self):
        fake = {"scope": "ILLUSTRATIVE failure fixture", "case_count": 0,
                "broken_routing_detected": True, "wire_tamper_detected": True,
                "cobol": {"status": "FAIL"}}
        with patch("experiments.experiment_bridge.v1.demo.run", return_value=fake), \
                patch.object(sys, "argv", ["demo", "--output-dir", "/tmp/fake"]):
            with self.assertRaises(SystemExit) as exc:
                main()
            self.assertEqual(exc.exception.code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
