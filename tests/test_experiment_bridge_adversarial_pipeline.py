"""ILLUSTRATIVE context-bound adversarial tests, not authentication proofs."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.experiment_bridge.v1_1.core import make_level, walk
from experiments.experiment_bridge.v1_1.semantics import annotate_trace, find_rows, normalize_reference
from experiments.experiment_bridge.v1_1.verify import checked_decode
from experiments.experiment_bridge.v1_1.wire import decode_record, encode_record


class TestContextBoundAdversarialPipeline(unittest.TestCase):
    def setUp(self):
        self.reference = Path(__file__).resolve().parents[1] / (
            "experiments/experiment_bridge/raw/lojban_wordslot_reference.json")
        self.raw_bytes = self.reference.read_bytes()
        self.rows = normalize_reference(json.loads(self.raw_bytes))
        better = find_rows(self.rows, english="better", role="mapping")[0]
        self.assignments = {(1, 0): better["row_id"]}
        self.levels = [make_level([[1], [3]], 9)]
        self.trace = annotate_trace(walk([1], self.levels), self.rows, self.assignments)
        self.payload = {"scope": "ILLUSTRATIVE adversarial fixture", "trace": self.trace}

    def tearDown(self):
        self.assertEqual(self.reference.read_bytes(), self.raw_bytes)

    def test_original_record_matches_external_context(self):
        result = checked_decode(encode_record(self.payload), self.levels, self.rows, self.assignments)
        self.assertEqual(result, self.payload)

    def test_rehashed_semantic_forgery_passes_wire_but_not_context(self):
        altered = copy.deepcopy(self.payload)
        altered["trace"]["steps"][0]["semantic_row"]["source"]["mapping_reason"] = "Verified by fiat"
        encoded = encode_record(altered)
        self.assertEqual(decode_record(encoded), altered)
        with self.assertRaisesRegex(ValueError, "Annotation validation"):
            checked_decode(encoded, self.levels, self.rows, self.assignments)

    def test_self_consistent_wrong_codebook_is_not_trusted(self):
        false_trace = walk([1], [make_level([[3]], 9)])
        false_trace["steps"][0]["codebook_sha256"] = self.levels[0].codebook_sha256
        annotated = annotate_trace(false_trace, self.rows, self.assignments)
        encoded = encode_record({"trace": annotated})
        self.assertEqual(decode_record(encoded)["trace"], annotated)
        with self.assertRaisesRegex(ValueError, "Numerical validation"):
            checked_decode(encoded, self.levels, self.rows, self.assignments)

    def test_accepted_annotation_does_not_override_external_assignment_policy(self):
        with self.assertRaisesRegex(ValueError, "Annotation validation"):
            checked_decode(encode_record(self.payload), self.levels, self.rows, {})

    def test_rehashed_evidential_is_not_automatically_trusted(self):
        altered = copy.deepcopy(self.payload)
        altered["trace"]["evidential"] = find_rows(self.rows, identifier="za'a", role="evidential")[0]
        with self.assertRaisesRegex(ValueError, "Annotation validation"):
            checked_decode(encode_record(altered), self.levels, self.rows, self.assignments)

    def test_missing_external_context_is_rejected(self):
        record = encode_record(self.payload)
        for levels, rows in ((None, self.rows), (self.levels, None)):
            with self.assertRaisesRegex(ValueError, "External"):
                checked_decode(record, levels, rows, self.assignments)

    def test_untrusted_outer_labels_are_not_authentication(self):
        altered = copy.deepcopy(self.payload)
        altered["scope"] = "An attacker changed this label and recomputed the hash"
        result = checked_decode(encode_record(altered), self.levels, self.rows, self.assignments)
        self.assertEqual(result["scope"], altered["scope"])
        # The helper validates trace/context consistency, not arbitrary outer
        # labels, sender identity, or the external policy's semantic truth.

    def test_consistent_different_target_is_not_measurement_authentication(self):
        altered = {"trace": annotate_trace(walk([2], self.levels), self.rows, self.assignments)}
        result = checked_decode(encode_record(altered), self.levels, self.rows, self.assignments)
        self.assertEqual(result["trace"]["target"], [2.0])
        # External codebooks/reference do not pin the original target or prove
        # a sensor/encoder produced this input. That needs another trust input.

    def test_valid_bytes_do_not_imply_trace_schema(self):
        with self.assertRaisesRegex(ValueError, "trace object"):
            checked_decode(encode_record({"just": "bytes"}), self.levels, self.rows, self.assignments)


if __name__ == "__main__":
    unittest.main(verbosity=2)
