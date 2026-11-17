"""Candidate-only software adversarial fixtures, never empirical semantic data.

Run from repository root: python tests/test_experiment_bridge_adversarial_semantics.py
"""

from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.v1 import semantics as legacy  # noqa: E402
from experiments.experiment_bridge.v1_1 import semantics as candidate  # noqa: E402

REFERENCE = ROOT / "experiments/experiment_bridge/raw/lojban_wordslot_reference.json"
MUTATION_SEED = 20261117
MUTATION_COUNT = 128


class TestAdversarialSemantics(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(REFERENCE.read_text())
        self.rows = candidate.normalize_reference(self.data)
        self.trace = {"fixture": "ILLUSTRATIVE", "steps": [
            {"level": 1, "numerical_status": "ACCEPTED", "code_index": 0},
            {"level": 2, "numerical_status": "ACCEPTED", "code_index": 0},
            {"level": 3, "numerical_status": "REJECTED", "code_index": None}]}
        self.assignments = {(1, 0): self.rows[0]["row_id"]}
        self.evidence = self.rows[-1]["row_id"]

    def annotated(self):
        return candidate.annotate_trace(self.trace, self.rows, self.assignments, self.evidence)

    def extension(self, value):
        self.data["place_structures"][0]["audit_extension"] = value
        return self.data

    def assert_rows_invalid(self, rows):
        with self.assertRaises(ValueError):
            candidate.find_rows(rows)
        with self.assertRaises(ValueError):
            candidate.annotate_trace(self.trace, rows)
        self.assertTrue(candidate.validate_annotation(self.annotated(), rows, self.assignments,
                                                      self.evidence))

    def test_original_41_rows_and_ids_unchanged(self):
        before = deepcopy(self.data)
        self.assertEqual(self.rows, legacy.normalize_reference(self.data))
        self.assertEqual(len(self.rows), 41)
        self.assertEqual(Counter(row["role"] for row in self.rows),
                         {"mapping": 25, "recall_check": 5, "evidential": 11})
        self.assertEqual(self.data, before)

    def test_all_annotation_fields_unchanged_except_version(self):
        original = legacy.annotate_trace(self.trace, self.rows, self.assignments, self.evidence)
        original["semantic_provenance"]["version"] = candidate.SEMANTIC_VERSION
        self.assertEqual(self.annotated(), original)

    def test_ids_stable_under_unrelated_source_and_key_reordering(self):
        self.data["place_structures"].reverse()
        self.data["place_structures"] = [dict(reversed(list(row.items())))
                                         for row in self.data["place_structures"]]
        self.assertEqual({row["row_id"] for row in candidate.normalize_reference(self.data)},
                         {row["row_id"] for row in self.rows})

    def test_unknown_fields_preserved_and_identity_sensitive_not_authenticity(self):
        shared = {"note": ["specimen", None]}
        data = self.extension({"left": shared, "right": shared})
        before = deepcopy(data)
        rows = candidate.normalize_reference(data)
        self.assertEqual(rows[0]["source"], data["place_structures"][0])
        self.assertNotEqual(rows[0]["row_id"], self.rows[0]["row_id"])
        rows[0]["source"]["audit_extension"]["left"]["note"].append("changed")
        self.assertEqual(data, before)

    def test_cyclic_source_extension_rejected_without_recursion_error(self):
        cycle = []
        cycle.append(cycle)
        with self.assertRaises(ValueError):
            candidate.normalize_reference(self.extension(cycle))

    def test_deep_source_extension_rejected_without_recursion_error(self):
        value = None
        for _ in range(1200):
            value = [value]
        with self.assertRaises(ValueError):
            candidate.normalize_reference(self.extension(value))

    def test_resource_policy_boundaries(self):
        candidate.normalize_reference(self.extension("x" * candidate.MAX_JSON_STRING_CHARS))
        for value in ("x" * (candidate.MAX_JSON_STRING_CHARS + 1),
                      [None] * (candidate.MAX_JSON_NODES + 1),
                      ["x" * candidate.MAX_JSON_STRING_CHARS] * 17,
                      1 << candidate.MAX_JSON_INTEGER_BITS):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                candidate.normalize_reference(self.extension(value))

    def test_depth_boundary_and_alias_expansion_count(self):
        value = None
        for _ in range(candidate.MAX_JSON_DEPTH):
            value = [value]
        candidate._check_json(value)
        with self.assertRaises(ValueError):
            candidate._check_json([value])
        value = [None] * 1000
        with self.assertRaises(ValueError):
            candidate._check_json([value] * 101)

    def test_strict_json_types_and_finiteness(self):
        for value in (float("nan"), float("inf"), {1: "key"}, ("tuple",), {"set"}, object()):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                candidate.normalize_reference(self.extension(value))

    def test_row_count_policy(self):
        data = {"place_structures": [deepcopy(self.data["place_structures"][0])]
                * (candidate.MAX_REFERENCE_ROWS + 1), "evidentials": []}
        with self.assertRaises(ValueError):
            candidate.normalize_reference(data)

    def test_duplicate_ids_rejected_in_find_and_annotate(self):
        self.assert_rows_invalid(self.rows + [deepcopy(self.rows[0])])

    def test_source_position_collision_rejected(self):
        rows = deepcopy(self.rows)
        rows[1]["source_index"] = 0
        self.assert_rows_invalid(rows)

    def test_bounded_canonical_occurrence_suffix(self):
        for suffix in ("", "0", "01", "+1", "１", "9" * 4000,
                       str(candidate.MAX_ROW_OCCURRENCE + 1), "2"):
            rows = deepcopy(self.rows)
            rows[0]["row_id"] = rows[0]["row_id"].rsplit(":", 1)[0] + ":" + suffix
            with self.subTest(suffix=suffix[:20]):
                self.assert_rows_invalid(rows)

    def test_duplicate_occurrence_order_not_input_list_order(self):
        source = deepcopy(self.data["place_structures"][0])
        self.data["place_structures"][5] = deepcopy(source)
        self.data["place_structures"][6] = deepcopy(source)
        rows = candidate.normalize_reference(self.data)
        candidate.find_rows(rows[::-1])
        rows[5]["row_id"], rows[6]["row_id"] = rows[6]["row_id"], rows[5]["row_id"]
        self.assert_rows_invalid(rows)

    def test_occurrence_gap_cannot_exceed_source_position_gap(self):
        self.data["place_structures"] = [deepcopy(self.data["place_structures"][0])] * 3
        rows = candidate.normalize_reference(self.data)
        rows = rows[1:]
        rows[0]["row_id"] = rows[0]["row_id"].rsplit(":", 1)[0] + ":1"
        self.assert_rows_invalid(rows)

    def test_reordered_subsets_and_nonfirst_occurrence_still_valid(self):
        subset = self.rows[::3][::-1]
        self.assertEqual(candidate.find_rows(subset), subset)
        self.data["place_structures"].append(deepcopy(self.data["place_structures"][0]))
        second = candidate.normalize_reference(self.data)[30]
        self.assertTrue(second["row_id"].endswith(":2"))
        self.assertEqual(candidate.find_rows([second]), [second])

    def test_source_index_structural_constraints_not_authentication(self):
        rows = deepcopy(self.rows[:1])
        rows[0]["source_index"] = 99
        self.assertEqual(candidate.find_rows(rows), rows)
        for index in (True, -1, candidate.MAX_REFERENCE_ROWS):
            invalid = deepcopy(rows)
            invalid[0]["source_index"] = index
            self.assert_rows_invalid(invalid)

    def test_honest_checker_no_mutation(self):
        annotated = self.annotated()
        inputs = deepcopy((annotated, self.rows, self.assignments))
        self.assertEqual(candidate.validate_annotation(annotated, self.rows, self.assignments,
                                                       self.evidence), [])
        self.assertEqual((annotated, self.rows, self.assignments), inputs)

    def test_checker_detects_forgery_with_unchanged_reference_hash(self):
        annotated = self.annotated()
        hash_before = annotated["semantic_provenance"]["reference_sha256"]
        annotated["steps"][0]["semantic_row"] = deepcopy(self.rows[1])
        self.assertEqual(annotated["semantic_provenance"]["reference_sha256"], hash_before)
        self.assertTrue(candidate.validate_annotation(annotated, self.rows, self.assignments,
                                                      self.evidence))

    def test_checker_uses_external_assignments_and_evidence_only(self):
        annotated = self.annotated()
        self.assertTrue(candidate.validate_annotation(annotated, self.rows))
        changed = {(1, 0): self.rows[1]["row_id"]}
        self.assertTrue(candidate.validate_annotation(annotated, self.rows, changed, self.evidence))
        honest_unmapped = candidate.annotate_trace(self.trace, self.rows)
        self.assertEqual(candidate.validate_annotation(honest_unmapped, self.rows), [])

    def test_missing_reserved_fields_and_type_alias_forgeries(self):
        original = self.annotated()
        for field in candidate.SEMANTIC_TOP_FIELDS:
            changed = deepcopy(original)
            del changed[field]
            self.assertTrue(candidate.validate_annotation(changed, self.rows, self.assignments,
                                                          self.evidence))
        for field in candidate.SEMANTIC_STEP_FIELDS:
            changed = deepcopy(original)
            del changed["steps"][0][field]
            self.assertTrue(candidate.validate_annotation(changed, self.rows, self.assignments,
                                                          self.evidence))
        changed = deepcopy(original)
        changed["steps"][0]["semantic_row"]["source_index"] = False
        self.assertTrue(candidate.validate_annotation(changed, self.rows, self.assignments,
                                                      self.evidence))

    def test_checker_malformed_input_returns_errors(self):
        cycle = {}
        cycle["cycle"] = cycle
        for trace in (None, [], {}, {"steps": [None]}, cycle):
            self.assertTrue(candidate.validate_annotation(trace, self.rows))
        annotated = self.annotated()
        for assignments in ([], {(True, 0): self.rows[0]["row_id"]}, {(1, 0): self.evidence}):
            self.assertTrue(candidate.validate_annotation(annotated, self.rows, assignments))

    def test_minimal_trace_numeric_boundary_and_status_distinctions(self):
        trace = deepcopy(self.trace)
        trace["steps"][0].update(distance_squared=100.0, threshold_squared=0.0)
        void = next(row for row in self.rows if row["lexical_status"] == "LEXICAL_VOID")
        assignments = {(1, 0): void["row_id"], (3, 0): self.rows[0]["row_id"]}
        result = candidate.annotate_trace(trace, self.rows, assignments)
        self.assertEqual([step["semantic_status"] for step in result["steps"]],
                         ["LEXICAL_VOID", "UNMAPPED", "NOT_APPLICABLE"])
        self.assertEqual(candidate.validate_annotation(result, self.rows, assignments), [])
        self.assertEqual(candidate.validate_annotation(candidate.annotate_trace({"steps": []}, []), []), [])

    def test_reserved_output_never_overwritten_and_trace_cycle_rejected(self):
        annotated = self.annotated()
        before = deepcopy(annotated)
        with self.assertRaises(ValueError):
            candidate.annotate_trace(annotated, self.rows)
        self.assertEqual(annotated, before)
        trace = deepcopy(self.trace)
        trace["extra"] = trace
        with self.assertRaises(ValueError):
            candidate.annotate_trace(trace, self.rows)

    def test_deterministic_structured_annotation_mutations(self):
        rng = random.Random(MUTATION_SEED)
        original = self.annotated()
        targets = [("step", i, field) for i in range(3) for field in candidate.SEMANTIC_STEP_FIELDS]
        targets += [("top", 0, field) for field in candidate.SEMANTIC_TOP_FIELDS]
        for mutation in range(MUTATION_COUNT):
            changed = deepcopy(original)
            kind, index, field = rng.choice(targets)
            owner = changed["steps"][index] if kind == "step" else changed
            if mutation % 2:
                del owner[field]
            else:
                owner[field] = {"ILLUSTRATIVE_forgery": mutation}
            before = deepcopy(changed)
            with self.subTest(mutation=mutation, field=field):
                self.assertTrue(candidate.validate_annotation(changed, self.rows, self.assignments,
                                                              self.evidence))
                self.assertEqual(changed, before)
        self.assertEqual(candidate.validate_annotation(original, self.rows, self.assignments,
                                                       self.evidence), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
