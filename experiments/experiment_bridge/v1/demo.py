"""ILLUSTRATIVE integration demo, not real NCM or semantic calibration.

Run from repository root:
python -m experiments.experiment_bridge.v1.demo --output-dir /tmp/bridge-v1-demo

Fresh run directories avoid overwriting received or prior audit evidence.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from .core import make_level, validate_trace, walk
from .semantics import annotate_trace, find_rows, normalize_reference
from .wire import decode_record, encode_record, roundtrip_with_cobol

BENCH = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output_dir):
    output_dir = Path(output_dir).resolve()
    for forbidden in (BENCH / "raw", BENCH / "evidence", BENCH / "audit"):
        if output_dir == forbidden or forbidden in output_dir.parents:
            raise ValueError("Run output must not overwrite received or audit specimens")
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("Choose a new or empty output directory")
    output_dir.mkdir(parents=True, exist_ok=True)

    reference_path = BENCH / "raw" / "lojban_wordslot_reference.json"
    raw = json.loads(reference_path.read_text())
    before_raw = copy.deepcopy(raw)
    rows = normalize_reference(raw)
    better = find_rows(rows, english="better", role="mapping")[0]
    gap = find_rows(rows, english="efficient", role="mapping")[0]
    evidential = find_rows(rows, identifier="ja'o", role="evidential")[0]
    levels = [make_level([[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]], 0.09,
                         label="ILLUSTRATIVE hand-specified vectors")]
    gap_levels = [make_level([[1.0]], 0.0, label="ILLUSTRATIVE lexical-gap fixture")]
    fixtures = [
        ("accepted_proposed_mapping", [0.15, 0.22, 0.28], levels,
         {(1, 0): better["row_id"]}),
        ("numerical_rejection", [8.0, 8.0, 8.0], levels,
         {(1, 0): better["row_id"]}),
        ("accepted_without_mapping", [0.1, 0.2, 0.3], levels, {}),
        ("accepted_with_declared_lexical_gap", [1.0], gap_levels,
         {(1, 0): gap["row_id"]}),
    ]
    records = []
    cases = []
    for name, target, books, assignments in fixtures:
        trace = walk(target, books)
        errors = validate_trace(trace, books)
        if errors:
            raise AssertionError(errors)
        untouched = copy.deepcopy(trace)
        annotated = annotate_trace(trace, rows, assignments,
                                   evidential_row_id=evidential["row_id"])
        if trace != untouched or raw != before_raw:
            raise AssertionError("Annotation mutated numerical or source state")
        payload = {"fixture": name, "scope": "ILLUSTRATIVE, not calibrated semantics",
                   "trace": annotated}
        record = encode_record(payload)
        if decode_record(record) != payload:
            raise AssertionError("Python wire round trip changed payload")
        records.append(record)
        cases.append(payload)
        (output_dir / (name + ".json")).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")

    broken = copy.deepcopy(walk([8.0, 8.0, 8.0], levels))
    broken["steps"][0]["numerical_status"] = "ACCEPTED"
    broken["steps"][0]["code_index"] = broken["steps"][0]["nearest_index"]
    broken_errors = validate_trace(broken, levels)
    if not broken_errors:
        raise AssertionError("Independent trace validator accepted broken routing")
    corrupt = bytearray(records[0])
    corrupt[76] ^= 1
    try:
        decode_record(bytes(corrupt))
    except ValueError:
        tamper_detected = True
    else:
        raise AssertionError("Wire validator accepted altered payload")

    cobol = roundtrip_with_cobol(records, output_dir / "cobol")
    summary = {
        "version": "experiment-bridge/v1", "scope": "ILLUSTRATIVE integration fixtures",
        "semantic_validation": "NOT_PERFORMED", "neural_model": "NOT_RUN",
        "physical_interpretation": "NOT_ESTABLISHED",
        "reference_sha256": digest(reference_path),
        "source_sha256": {p.name: digest(p) for p in sorted(Path(__file__).parent.glob("*.py"))},
        "reference_rows": len(rows), "case_count": len(cases),
        "states": [{"fixture": c["fixture"], "step": c["trace"]["steps"][0]} for c in cases],
        "raw_reference_unchanged": raw == before_raw,
        "broken_routing_detected": bool(broken_errors), "broken_routing_errors": broken_errors,
        "wire_tamper_detected": tamper_detected,
        "python_roundtrip_exact": True, "record_lengths": [len(r) for r in records],
        "cobol": cobol,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="new or empty run directory; raw/evidence paths forbidden")
    args = parser.parse_args()
    summary = run(args.output_dir)
    print(json.dumps({"scope": summary["scope"], "case_count": summary["case_count"],
                      "broken_routing_detected": summary["broken_routing_detected"],
                      "wire_tamper_detected": summary["wire_tamper_detected"],
                      "cobol": summary["cobol"]}, indent=2))
    print("summary ->", args.output_dir / "summary.json")
    if summary["cobol"]["status"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
