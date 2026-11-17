"""Context-bound consumer check of four ILLUSTRATIVE candidate demo records.

Input is the candidate demo's actual COBOL output.dat, not a fabricated compiler
result. External references/assignments below are hand-selected test context,
not inferred from the incoming provenance. This does not certify semantics.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from experiments.experiment_bridge.v1_1.core import make_level, walk
from experiments.experiment_bridge.v1_1.semantics import annotate_trace, find_rows, normalize_reference
from experiments.experiment_bridge.v1_1.verify import checked_decode
from experiments.experiment_bridge.v1_1.wire import decode_record, encode_record, RECORD_SIZE

BENCH = Path(__file__).resolve().parents[1]


def probe(input_file):
    data = Path(input_file).read_bytes()
    if len(data) != 4 * RECORD_SIZE:
        raise ValueError("This finite probe expects exactly four demo records")
    reference = BENCH / "raw" / "lojban_wordslot_reference.json"
    raw_bytes = reference.read_bytes()
    rows = normalize_reference(json.loads(raw_bytes))
    better = find_rows(rows, english="better", role="mapping")[0]
    gap = find_rows(rows, english="efficient", role="mapping")[0]
    ev = find_rows(rows, identifier="ja'o", role="evidential")[0]["row_id"]
    levels = [make_level([[0.1, 0.2, 0.3], [0.9, 0.8, 0.7]], 0.09)]
    contexts = [
        ("accepted_proposed_mapping", levels, {(1, 0): better["row_id"]}),
        ("numerical_rejection", levels, {(1, 0): better["row_id"]}),
        ("accepted_without_mapping", levels, {}),
        ("accepted_with_declared_lexical_gap", [make_level([[1]], 0)],
         {(1, 0): gap["row_id"]}),
    ]
    honest, first = [], None
    for position, (name, books, assignments) in enumerate(contexts):
        record = data[position * RECORD_SIZE:(position + 1) * RECORD_SIZE]
        payload = checked_decode(record, books, rows, assignments, ev)
        if payload.get("fixture") != name:
            raise AssertionError("Record order/fixture label differs from expected demo")
        step = payload["trace"]["steps"][0]
        honest.append({"fixture": name, "numerical_status": step["numerical_status"],
                       "semantic_status": step["semantic_status"], "context_consistent": True})
        if first is None:
            first = payload

    forged = copy.deepcopy(first)
    forged["trace"]["steps"][0]["semantic_row"]["source"]["mapping_reason"] = "Verified by fiat"
    forged_record = encode_record(forged)  # attacker recomputes the envelope hash
    wire_accepts = decode_record(forged_record) == forged
    try:
        checked_decode(forged_record, levels, rows, contexts[0][2], ev)
    except ValueError as exc:
        forgery_error = str(exc)
    else:
        raise AssertionError("Semantic forgery passed external-context checks")

    intended = [make_level([[1], [3]], 9)]
    false_trace = walk([1], [make_level([[3]], 9)])
    false_trace["steps"][0]["codebook_sha256"] = intended[0].codebook_sha256
    assigned = {(1, 0): better["row_id"]}
    false_trace = annotate_trace(false_trace, rows, assigned)
    wrong_record = encode_record({"trace": false_trace})
    try:
        checked_decode(wrong_record, intended, rows, assigned)
    except ValueError as exc:
        numerical_error = str(exc)
    else:
        raise AssertionError("Wrong-code trace passed externally supplied codebook")

    label = copy.deepcopy(first)
    label["scope"] = "An attacker supplied this unrelated outer label"
    label_result = checked_decode(encode_record(label), levels, rows, contexts[0][2], ev)
    replaced_target = {"trace": annotate_trace(walk([0.1, 0.2, 0.3], levels), rows,
                                               contexts[0][2], ev)}
    target_result = checked_decode(encode_record(replaced_target), levels, rows, contexts[0][2], ev)
    if reference.read_bytes() != raw_bytes:
        raise AssertionError("Reference bytes changed during probe")
    return {
        "scope": "ILLUSTRATIVE software consumer probe, not authentication or semantics",
        "input_sha256": hashlib.sha256(data).hexdigest(), "input_bytes": len(data),
        "reference_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "honest_records": honest,
        "rehashed_semantic_forgery": {"wire_accepts": wire_accepts,
                                       "context_rejects": True, "error": forgery_error},
        "self_consistent_wrong_code": {"wire_accepts": decode_record(wrong_record)["trace"] == false_trace,
                                       "context_rejects": True, "error": numerical_error},
        "outer_label_trust_limit": {"accepted": label_result["scope"] == label["scope"],
                                     "meaning": "Trace consistency does not certify arbitrary outer labels"},
        "replaced_target_trust_limit": {
            "accepted": target_result["trace"]["target"] == [0.1, 0.2, 0.3],
            "meaning": "External codebooks and reference do not authenticate the original input measurement"},
        "reference_unchanged": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-file", required=True, type=Path)
    parser.add_argument("--output", type=Path, help="new JSON output file; existing files are not overwritten")
    args = parser.parse_args()
    result = probe(args.input_file)
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(text)
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
