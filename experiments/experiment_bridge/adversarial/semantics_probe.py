"""Deterministic software fixtures, not empirical linguistic evidence.

Run from repository root:
  python experiments/experiment_bridge/adversarial/semantics_probe.py --phase legacy
  python experiments/experiment_bridge/adversarial/semantics_probe.py --phase candidate
The second invocation retains the recorded pre-fix replay and checks its source hash.
"""

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
BASE = ROOT / "experiments/experiment_bridge"
OUTPUT = BASE / "adversarial/semantics_results.json"


def load_module(version):
    path = BASE / version / "semantics.py"
    spec = importlib.util.spec_from_file_location(f"semantics_{version}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, hashlib.sha256(path.read_bytes()).hexdigest()


def fixtures(module):
    data = json.loads((BASE / "raw/lojban_wordslot_reference.json").read_text())
    rows = module.normalize_reference(data)
    minimal = {"steps": [{"level": 1, "numerical_status": "ACCEPTED", "code_index": 0}]}
    assignments = {(1, 0): rows[0]["row_id"]}

    def normalize_extension(extension):
        changed = deepcopy(data)
        changed["place_structures"][0]["audit_extension"] = extension
        return lambda: module.normalize_reference(changed)

    cycle = []
    cycle.append(cycle)
    deep = None
    for _ in range(1200):
        deep = [deep]
    duplicate_id = deepcopy(rows) + [deepcopy(rows[0])]
    position_collision = deepcopy(rows)
    position_collision[1]["source_index"] = position_collision[0]["source_index"]
    impossible_occurrence = deepcopy(rows)
    impossible_occurrence[0]["row_id"] = rows[0]["row_id"].rsplit(":", 1)[0] + ":2"
    long_suffix = deepcopy(rows)
    long_suffix[0]["row_id"] = rows[0]["row_id"].rsplit(":", 1)[0] + ":" + "9" * 4000
    duplicated_data = deepcopy(data)
    duplicated_data["place_structures"].append(deepcopy(data["place_structures"][0]))
    reversed_occurrences = module.normalize_reference(duplicated_data)
    first, last = reversed_occurrences[0], reversed_occurrences[30]
    first["row_id"], last["row_id"] = last["row_id"], first["row_id"]
    lone_position = deepcopy(rows[:1])
    lone_position[0]["source_index"] = 99
    numeric_mismatch = deepcopy(minimal)
    numeric_mismatch["steps"][0].update(distance_squared=10.0, threshold_squared=0.0)
    honest = module.annotate_trace(minimal, rows, assignments)
    forged = deepcopy(honest)
    forged["steps"][0]["semantic_row"] = deepcopy(rows[1])

    def changed_source():
        changed = deepcopy(data)
        changed["place_structures"][0]["audit_extension"] = {"claim": "ILLUSTRATIVE"}
        new_rows = module.normalize_reference(changed)
        assert new_rows[0]["row_id"] != rows[0]["row_id"]
        assert new_rows[0]["source"]["audit_extension"] == {"claim": "ILLUSTRATIVE"}
        return new_rows

    def check_forgery():
        # Legacy has no semantic consumer checker. Its provenance hash is unchanged
        # by replacing the separately transported row; this is a demonstrated gap,
        # not a claim that v1 promised upstream authentication.
        if not hasattr(module, "validate_annotation"):
            assert forged["semantic_provenance"] == honest["semantic_provenance"]
            return {"checker_available": False, "reference_hash_unchanged": True}
        errors = module.validate_annotation(forged, rows, assignments)
        if not errors:
            raise AssertionError("forged transported row was not detected")
        return {"checker_available": True, "errors": errors}

    def check_honest():
        if not hasattr(module, "validate_annotation"):
            return {"checker_available": False}
        errors = module.validate_annotation(honest, rows, assignments)
        if errors:
            raise AssertionError(errors)
        return {"checker_available": True, "errors": errors}

    return [
        ("cyclic_source_extension", "defect", normalize_extension(cycle)),
        ("deep_source_extension", "defect", normalize_extension(deep)),
        ("oversize_source_string", "bounded_policy", normalize_extension("x" * 65537)),
        ("oversize_source_nodes", "bounded_policy", normalize_extension([None] * 100001)),
        ("giant_occurrence_suffix", "defect", lambda: module.find_rows(long_suffix)),
        ("duplicate_row_ids_in_find", "defect", lambda: module.find_rows(duplicate_id)),
        ("colliding_source_positions", "defect", lambda: module.find_rows(position_collision)),
        ("impossible_occurrence_at_position_zero", "defect",
         lambda: module.find_rows(impossible_occurrence)),
        ("reversed_duplicate_occurrence_metadata", "defect",
         lambda: module.find_rows(reversed_occurrences)),
        ("reordered_subset", "compatibility", lambda: module.find_rows(rows[::3][::-1])),
        ("unknown_fields_retained_and_identity_changes", "intentional_trust_limit", changed_source),
        ("uncontradicted_source_index_not_authenticated", "intentional_trust_limit",
         lambda: module.find_rows(lone_position)),
        ("minimal_trace", "compatibility", lambda: module.annotate_trace(minimal, rows)),
        ("numerically_inconsistent_trace", "intentional_boundary",
         lambda: module.annotate_trace(numeric_mismatch, rows)),
        ("forged_transported_row_unchanged_reference_hash", "consumer_validation_gap", check_forgery),
        ("honest_annotation", "compatibility", check_honest),
    ]


def replay(version):
    module, source_hash = load_module(version)
    records = []
    for name, classification, operation in fixtures(module):
        start = time.perf_counter()
        try:
            value = operation()
            result = {"outcome": "accepted"}
            if isinstance(value, dict) and "checker_available" in value:
                result["detail"] = value
        except Exception as exc:
            result = {"outcome": "exception", "exception_type": type(exc).__name__,
                      "message": str(exc)[:400]}
        result.update(case=name, classification=classification,
                      elapsed_seconds=round(time.perf_counter() - start, 6))
        records.append(result)
    return {"module": f"experiments/experiment_bridge/{version}/semantics.py",
            "module_sha256": source_hash, "case_count": len(records), "cases": records}


def structured_mutations():
    module, _ = load_module("v1_1")
    data = json.loads((BASE / "raw/lojban_wordslot_reference.json").read_text())
    rows = module.normalize_reference(data)
    trace = {"fixture": "ILLUSTRATIVE", "steps": [
        {"level": 1, "numerical_status": "ACCEPTED", "code_index": 0},
        {"level": 2, "numerical_status": "ACCEPTED", "code_index": 0},
        {"level": 3, "numerical_status": "REJECTED", "code_index": None}]}
    assignments, evidence = {(1, 0): rows[0]["row_id"]}, rows[-1]["row_id"]
    original = module.annotate_trace(trace, rows, assignments, evidence)
    seed, count, detected, unchanged = 20261117, 128, 0, 0
    rng = random.Random(seed)
    targets = [("step", i, field) for i in range(3) for field in module.SEMANTIC_STEP_FIELDS]
    targets += [("top", 0, field) for field in module.SEMANTIC_TOP_FIELDS]
    coverage = {}
    for mutation in range(count):
        changed = deepcopy(original)
        kind, index, field = rng.choice(targets)
        coverage[field] = coverage.get(field, 0) + 1
        owner = changed["steps"][index] if kind == "step" else changed
        if mutation % 2:
            del owner[field]
        else:
            owner[field] = {"ILLUSTRATIVE_forgery": mutation}
        before = deepcopy(changed)
        detected += bool(module.validate_annotation(changed, rows, assignments, evidence))
        unchanged += changed == before
    return {"seed": seed, "generated": count, "detected": detected,
            "inputs_unmodified": unchanged, "field_coverage": coverage,
            "honest_validation_errors": module.validate_annotation(original, rows, assignments, evidence)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=("legacy", "candidate"), required=True)
    args = parser.parse_args()
    if args.phase == "legacy":
        result = {"fixture_type": "deterministic software mutation; not empirical data",
                  "legacy": replay("v1")}
    else:
        result = json.loads(OUTPUT.read_text())
        _, legacy_hash = load_module("v1")
        if result["legacy"]["module_sha256"] != legacy_hash:
            raise SystemExit("Legacy snapshot source changed; refusing to replace pre-fix findings")
        result["candidate"] = replay("v1_1")
        result["candidate"]["structured_mutations"] = structured_mutations()
    OUTPUT.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(f"Saved {args.phase} replay to {OUTPUT}")


if __name__ == "__main__":
    main()
