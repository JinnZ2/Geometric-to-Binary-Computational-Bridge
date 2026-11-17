"""Schema/routing checks, not linguistic or numerical-codebook validation.

Run from repository root: python tests/test_experiment_bridge_semantics.py
"""

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.v1.semantics import (  # noqa: E402
    annotate_trace, find_rows, normalize_reference,
)

REFERENCE = ROOT / "experiments/experiment_bridge/raw/lojban_wordslot_reference.json"


class TestReferenceSemantics(unittest.TestCase):
    def setUp(self):
        self.data = json.loads(REFERENCE.read_text(encoding="utf-8"))
        self.rows = normalize_reference(self.data)

    def row(self, english, role=None):
        found = find_rows(self.rows, english=english, role=role)
        self.assertEqual(len(found), 1)
        return found[0]

    def trace(self):
        return {"fixture": "ILLUSTRATIVE", "target": [1.0], "steps": [
            {"level": 1, "numerical_status": "ACCEPTED", "code_index": 0,
             "contribution": [0.8], "residual_after": [0.2]},
            {"level": 2, "numerical_status": "ACCEPTED", "code_index": 2,
             "contribution": [0.1], "residual_after": [0.1]},
            {"level": 3, "numerical_status": "REJECTED", "code_index": None,
             "nearest_index": 0, "contribution": [0.0], "residual_after": [0.1]},
        ]}

    def test_all_source_rows_retained_verbatim(self):
        self.assertEqual(len(self.rows), 41)
        self.assertEqual(len({r["row_id"] for r in self.rows}), 41)
        for row in self.rows:
            source = self.data[row["source_collection"]][row["source_index"]]
            self.assertEqual(row["source"], source)
            self.assertIsNot(row["source"], source)
            self.assertEqual(row["identifier"], source["gismu"])
        self.assertEqual(sum(r["role"] == "mapping" for r in self.rows), 25)
        self.assertEqual(sum(r["role"] == "recall_check" for r in self.rows), 5)
        self.assertEqual(sum(r["role"] == "evidential" for r in self.rows), 11)

    def test_unknown_source_fields_deep_copied_without_cleaning(self):
        self.data["place_structures"][0]["specimen"] = {"values": ["  unchanged  ", None]}
        before = deepcopy(self.data)
        rows = normalize_reference(self.data)
        self.assertEqual(rows[0]["source"], before["place_structures"][0])
        rows[0]["source"]["specimen"]["values"].append("changed")
        rows[0]["source"]["alternatives"].clear()
        self.assertEqual(self.data, before)

    def test_safe_and_recall_snura_are_distinct(self):
        found = find_rows(self.rows, identifier="snura")
        self.assertEqual(len(found), 2)
        self.assertEqual({r["role"] for r in found}, {"mapping", "recall_check"})
        self.assertNotEqual(found[0]["row_id"], found[1]["row_id"])
        self.assertEqual(self.row("safe")["source"]["mapping_status"], "PROPOSED")
        self.assertEqual(self.row("snura (recall check)")["source"]["mapping_status"], "DIFFERS")

    def test_xagrai_and_zmadu_are_noncollapsing(self):
        self.assertEqual({r["english"] for r in find_rows(self.rows, identifier="xagrai")},
                         {"best", "optimal"})
        self.assertEqual(len(find_rows(self.rows, identifier="zmadu")), 4)
        self.assertEqual(len(find_rows(self.rows, identifier="zmadu", role="mapping")), 3)
        self.assertEqual(find_rows(self.rows, identifier="xagrai", english="more"), [])

    def test_find_returns_independent_rows(self):
        snapshot = deepcopy(self.rows)
        found = find_rows(self.rows)
        found[0]["source"]["alternatives"].clear()
        self.assertEqual(self.rows, snapshot)
        self.assertEqual(find_rows(self.rows, english="not supplied"), [])

    def test_duplicate_content_gets_occurrence_ids_and_source_indexes(self):
        source = deepcopy(self.data["place_structures"][0])
        self.data["place_structures"].append(source)
        rows = normalize_reference(self.data)
        first, second = find_rows(rows, english="better")
        self.assertEqual(first["row_id"], self.rows[0]["row_id"])
        self.assertEqual(first["row_id"].rsplit(":", 1)[0], second["row_id"].rsplit(":", 1)[0])
        self.assertTrue(first["row_id"].endswith(":1"))
        self.assertTrue(second["row_id"].endswith(":2"))
        self.assertEqual([first["source_index"], second["source_index"]], [0, 30])
        self.assertEqual(first["source"], second["source"])
        self.assertIsNot(first["source"], second["source"])

    def test_ids_stable_across_key_order_and_unrelated_reordering(self):
        self.data["place_structures"].reverse()
        self.data["place_structures"] = [dict(reversed(list(r.items())))
                                         for r in self.data["place_structures"]]
        rows = normalize_reference(self.data)
        self.assertEqual({r["row_id"] for r in rows}, {r["row_id"] for r in self.rows})
        self.data["place_structures"][0]["mapping_reason"] += " specimen"
        self.assertNotEqual(normalize_reference(self.data)[0]["row_id"], rows[0]["row_id"])

    def test_status_is_lexical_not_proof_of_proposed_mapping(self):
        for english in ("efficient", "cold", "imminent"):
            self.assertEqual(self.row(english)["lexical_status"], "LEXICAL_VOID")
        self.assertEqual(self.row("safe")["lexical_status"], "PRESENT")
        self.data["place_structures"][0]["mapping_status"] = "VOID"
        self.assertEqual(normalize_reference(self.data)[0]["lexical_status"], "PRESENT")
        self.data["place_structures"][12]["mapping_status"] = "PROPOSED"
        self.assertEqual(normalize_reference(self.data)[12]["lexical_status"], "LEXICAL_VOID")

    def test_explicit_void_missing_and_rejection_remain_separate(self):
        trace, snapshot = self.trace(), deepcopy(self.rows)
        assignments = {(1, 0): self.row("efficient")["row_id"],
                       (3, 0): self.row("safe")["row_id"]}
        original = deepcopy(trace)
        result = annotate_trace(trace, self.rows, assignments)
        self.assertEqual([s["semantic_status"] for s in result["steps"]],
                         ["LEXICAL_VOID", "UNMAPPED", "NOT_APPLICABLE"])
        self.assertIsNone(result["steps"][1]["semantic_row"])
        self.assertIsNone(result["steps"][2]["semantic_row_id"])
        self.assertIsNone(result["steps"][2]["semantic_row"])
        for before, after in zip(trace["steps"], result["steps"]):
            self.assertEqual({k: after[k] for k in before}, before)
        result["steps"][0]["contribution"][0] = 99
        result["steps"][0]["semantic_row"]["source"]["alternatives"].clear()
        self.assertEqual(trace, original)
        self.assertEqual(self.rows, snapshot)

    def test_explicit_present_preserves_source_status_and_wording(self):
        safe = self.row("safe")
        result = annotate_trace(self.trace(), self.rows, {(1, 0): safe["row_id"]})
        step = result["steps"][0]
        self.assertEqual(step["semantic_status"], "PRESENT")
        self.assertEqual(step["semantic_row_id"], safe["row_id"])
        self.assertEqual(step["semantic_row"], safe)
        self.assertEqual(step["semantic_row"]["source"]["structure_status"], "OBSERVED")
        self.assertEqual(step["semantic_row"]["source"]["mapping_status"], "PROPOSED")

    def test_evidential_is_explicit_independent_metadata_with_provenance(self):
        evidence = self.row("I postulate", "evidential")
        result = annotate_trace(self.trace(), self.rows, evidential_row_id=evidence["row_id"])
        self.assertEqual(result["evidential"], evidence)
        self.assertEqual(result["steps"][0]["semantic_status"], "UNMAPPED")
        provenance = result["semantic_provenance"]
        self.assertEqual(provenance["evidential_row_id"], evidence["row_id"])
        self.assertRegex(provenance["reference_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(provenance["assignments"], [])
        self.assertEqual(provenance["version"], "experiment-bridge/v1")
        result["evidential"]["source"]["alternatives"].append("not source")
        self.assertEqual(self.row("I postulate")["source"]["alternatives"], [])
        self.assertIsNone(annotate_trace(self.trace(), self.rows)["evidential"])

    def test_provenance_explicit_assignments_are_sorted_and_digest_sensitive(self):
        safe = self.row("safe")["row_id"]
        assignments = {(2, 2): safe, (1, 0): safe}
        snapshot = deepcopy(assignments)
        result = annotate_trace(self.trace(), self.rows, assignments)
        self.assertEqual(result["semantic_provenance"]["assignments"], [
            {"level": 1, "code_index": 0, "row_id": safe},
            {"level": 2, "code_index": 2, "row_id": safe}])
        self.assertEqual(assignments, snapshot)
        subset = annotate_trace(self.trace(), self.rows[1:], {})
        self.assertNotEqual(subset["semantic_provenance"]["reference_sha256"],
                            result["semantic_provenance"]["reference_sha256"])

    def test_minimal_trace_requires_no_numerical_reimplementation(self):
        trace = {"steps": [{"level": 1, "numerical_status": "ACCEPTED", "code_index": 0}]}
        self.assertEqual(annotate_trace(trace, self.rows)["steps"][0]["semantic_status"], "UNMAPPED")
        self.assertEqual(annotate_trace({"steps": []}, [])["steps"], [])
        self.assertEqual(normalize_reference({"place_structures": [], "evidentials": []}), [])

    def test_core_trace_preserved_with_explicit_void_and_rejected_pointer(self):
        from experiments.experiment_bridge.v1.core import make_level, validate_trace, walk

        levels = [make_level([[1.0]], 0.0), make_level([[2.0]], 0.0)]
        trace = walk([1.0], levels)
        original = deepcopy(trace)
        assignments = {(1, 0): self.row("efficient")["row_id"],
                       (2, 0): self.row("safe")["row_id"]}
        result = annotate_trace(trace, self.rows, assignments)
        self.assertEqual(validate_trace(result, levels), [])
        self.assertEqual(result["steps"][0]["semantic_status"], "LEXICAL_VOID")
        self.assertEqual(result["steps"][1]["semantic_status"], "NOT_APPLICABLE")
        self.assertIsNone(result["steps"][1]["semantic_row_id"])
        self.assertEqual(result["reconstruction"], [1.0])
        for before, after in zip(trace["steps"], result["steps"]):
            self.assertEqual({key: after[key] for key in before}, before)
        self.assertEqual(trace, original)

    def test_bad_assignments_and_wrong_roles_rejected_even_when_unused(self):
        safe = self.row("safe")["row_id"]
        for assignment in ([], "bad", {(True, 0): safe}, {(1, False): safe}, {(0, 0): safe},
                           {(1, -1): safe}, {(1.0, 0): safe}, {"1,0": safe}, {(1,): safe},
                           {(1, 0): "missing"}, {(1, 0): None}, {(1, 0): []},
                           {(99, 0): self.row("snura (recall check)")["row_id"]},
                           {(99, 0): self.row("I observe")["row_id"]}):
            with self.subTest(assignment=assignment), self.assertRaises(ValueError):
                annotate_trace(self.trace(), self.rows, assignment)
        for row_id in (safe, "unknown", [], self.row("snura (recall check)")["row_id"]):
            with self.subTest(evidential=row_id), self.assertRaises(ValueError):
                annotate_trace(self.trace(), self.rows, evidential_row_id=row_id)

    def test_duplicate_normalized_ids_rejected_but_occurrences_assignable(self):
        with self.assertRaises(ValueError):
            annotate_trace(self.trace(), self.rows + [deepcopy(self.rows[0])])
        self.data["place_structures"].append(deepcopy(self.data["place_structures"][0]))
        rows = normalize_reference(self.data)
        duplicate = find_rows(rows, english="better")[1]
        result = annotate_trace(self.trace(), rows, {(1, 0): duplicate["row_id"]})
        self.assertEqual(result["steps"][0]["semantic_row"]["source_index"], 30)

    def test_malformed_reference_collections_and_rows(self):
        for data in (None, [], {}, {"place_structures": []},
                     {"place_structures": {}, "evidentials": []},
                     {"place_structures": [None], "evidentials": []}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                normalize_reference(data)
        for change in ({"english": 5}, {"class": None}, {"source_url": False},
                       {"retrieved": []}, {"mapping_reason": ""}, {"alternatives": "bad"},
                       {"alternatives": [1]}, {"mapping_status": "VERIFIED"},
                       {"structure_status": "PROPOSED"}, {"structure_status": "VOID"},
                       {"gismu": None}, {"gismu": True}, {"place_structure_verbatim": None},
                       {"class": "evidential"}, {"in_user_list": 1}, {"recalled_form": []},
                       {"extra": float("nan")}, {"extra": {1: "non-JSON key"}},
                       {"extra": ("non-JSON tuple",)}, {"extra": {"non-JSON set"}}):
            data = deepcopy(self.data)
            data["place_structures"][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                normalize_reference(data)
        for field in ("gismu", "place_structure_verbatim", "mapping_status"):
            data = deepcopy(self.data)
            del data["place_structures"][0][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                normalize_reference(data)
        data = deepcopy(self.data)
        data["evidentials"][0]["class"] = "fear"
        with self.assertRaises(ValueError):
            normalize_reference(data)

    def test_malformed_normalized_rows_and_filters(self):
        for rows in (None, {}, [None]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                find_rows(rows)
        for change in ({"row_id": "forged"}, {"role": "mapping"}, {"identifier": "fake"},
                       {"lexical_status": "CERTIFIED"}, {"source_index": True}):
            rows = deepcopy(self.rows)
            rows[-1].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                annotate_trace(self.trace(), rows)
        for filters in ({"role": "unknown"}, {"identifier": 3}, {"english": []}):
            with self.subTest(filters=filters), self.assertRaises(ValueError):
                find_rows(self.rows, **filters)

    def test_malformed_trace_and_reserved_annotations_never_overwritten(self):
        for trace in (None, {}, {"steps": {}}, {"steps": [None]},
                      {"steps": [], "evidential": "original"},
                      {"steps": [], "semantic_provenance": "original"}):
            with self.subTest(trace=trace), self.assertRaises(ValueError):
                annotate_trace(trace, self.rows)
        for change in ({"level": True}, {"level": 0}, {"code_index": True},
                       {"code_index": -1}, {"code_index": None}, {"numerical_status": "UNKNOWN"},
                       {"numerical_status": "REJECTED"}, {"semantic_row_id": "original"}):
            trace = self.trace()
            trace["steps"][0].update(change)
            before = deepcopy(trace)
            with self.subTest(change=change), self.assertRaises(ValueError):
                annotate_trace(trace, self.rows)
            self.assertEqual(trace, before)
        trace = self.trace()
        del trace["steps"][2]["code_index"]
        with self.assertRaises(ValueError):
            annotate_trace(trace, self.rows)


if __name__ == "__main__":
    unittest.main(verbosity=2)
