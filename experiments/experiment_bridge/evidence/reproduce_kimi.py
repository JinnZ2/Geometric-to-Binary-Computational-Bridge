#!/usr/bin/env python3
"""Note 2026-11-17: reproduce Kimi toy correction specimen, not a repair.

All original execution occurs in temporary cwd. Fixed-seed numeric records are
compared after removing ONLY runtime_s and claims[].ts, not float rounding.
No numpy, external models, git, or semantic implementation is used.
"""
import argparse
import collections
import copy
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "kimi_as_received"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe(value):
    if isinstance(value, float) and not math.isfinite(value):
        return "NaN" if math.isnan(value) else ("Infinity" if value > 0 else "-Infinity")
    if isinstance(value, dict):
        return {str(k): safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [safe(v) for v in value]
    return value


def stable(record):
    r = copy.deepcopy(record)
    r.pop("runtime_s", None)
    for c in r.get("claims", []):
        c.pop("ts", None)
    return r


def differences(a, b, path="$"):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for key in sorted(set(a) | set(b)) for d in
                (differences(a[key], b[key], path + "." + key) if key in a and key in b
                 else [{"path": path + "." + key, "left": a.get(key), "right": b.get(key)}])]
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [{"path": path, "left_length": len(a), "right_length": len(b)}]
        return [d for i, (x, y) in enumerate(zip(a, b)) for d in differences(x, y, path + f"[{i}]")]
    return [] if a == b else [{"path": path, "left": a, "right": b}]


def outcome(function):
    try:
        return {"ok": True, "result": function()}
    except Exception as exc:
        return {"ok": False, "error_type": type(exc).__name__, "error": str(exc)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=HERE / "kimi_reproduction.json")
    args = parser.parse_args()
    args.output = args.output.resolve()
    files = sorted(p for p in SOURCE.iterdir() if p.is_file())
    before = {str(p): sha(p) for p in files}
    saved = json.loads((SOURCE / "toy_rvq_void_seed0.json").read_text())
    results = {"note": "2026-11-17: Kimi toy is audited as an unchanged specimen, not a real neural codec or semantic bridge.",
               "environment": {"python": sys.version, "platform": sys.platform},
               "original_sha256_before": before, "edge_cases": {}, "main_runs": []}
    original_cwd = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="experiment-bridge-kimi-") as td:
        temp = Path(td)
        for f in files:
            shutil.copy2(f, temp / f.name)
        os.chdir(temp)
        try:
            results["temporary_cwd"] = str(temp)
            module = runpy.run_path(str(temp / "toy_rvq_void.py"))
            # Twice execute the exact CLI main; original output never touches
            # the supplied file because both script and cwd are temporary.
            replays = []
            for attempt in range(2):
                print(f"Replaying Kimi seed 0, attempt {attempt + 1}/2...", flush=True)
                proc = subprocess.run([sys.executable, "toy_rvq_void.py", "0"], cwd=temp,
                                      text=True, capture_output=True, timeout=180)
                run = {"command": [sys.executable, "toy_rvq_void.py", "0"], "cwd": str(temp),
                       "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
                if proc.returncode:
                    results["main_runs"].append(run)
                    raise RuntimeError("Original Kimi CLI failed")
                replay = json.loads((temp / "toy_rvq_void_seed0.json").read_text())
                run["record"] = replay
                results["main_runs"].append(run)
                replays.append(replay)
            results["replay"] = {
                "saved_vs_replay_stable_differences": differences(stable(saved), stable(replays[0])),
                "replay1_vs_replay2_stable_differences": differences(stable(replays[0]), stable(replays[1])),
                "saved_vs_replay_full_differences": differences(saved, replays[0]),
                "stable_saved_sha256": hashlib.sha256(json.dumps(stable(saved), sort_keys=True).encode()).hexdigest(),
                "stable_replay_sha256": hashlib.sha256(json.dumps(stable(replays[0]), sort_keys=True).encode()).hexdigest(),
                "excluded_fields": ["runtime_s", "claims[].ts"],
            }
            timestamps = [c["ts"] for c in saved["claims"]]
            results["saved_provenance"] = {
                "instrument": saved["instrument"], "claims_provenance": sorted(set(c["provenance"] for c in saved["claims"])),
                "all_claim_timestamps_equal": len(set(timestamps)) == 1,
                "timestamp_epoch": timestamps[0],
                "timestamp_utc": datetime.datetime.fromtimestamp(timestamps[0], datetime.timezone.utc).isoformat(),
                "saved_hash_or_digest_keys": [k for k in saved if "hash" in k or "digest" in k],
                "source_hash_is_audit_added_not_supplied": True,
                "saved_codebooks_or_source_arrays": any(k in saved for k in ("books", "codebooks", "train_vectors", "test_vectors")),
                "saved_runtime_s": saved["runtime_s"],
                "replay_runtimes_s": [r["runtime_s"] for r in replays],
                "supplied_semantic_JSON_is_not_loaded_by_script": "lojban" not in (SOURCE / "toy_rvq_void.py").read_text(),
            }
            results["verdict_recalculation"] = [{"scope": c["scope"], "recorded": c["verdict"],
                "recomputed": module["verdict"](c["measured"], c["value"], c["tol_frac"]),
                "relative_difference": abs(c["measured"] - c["value"]) / abs(c["value"]) if c["value"] else None}
                for c in saved["claims"]]
            results["correct_same_split_captured_energy_fractions"] = {
                split: [e / saved[split]["signal_energy"] for e in saved[split]["per_level_captured_energy"]]
                for split in ("train", "held_out")}
            results["narrative_heldout_fractions_use_wrong_train_denominator"] = [
                e / saved["train"]["signal_energy"] for e in saved["held_out"]["per_level_captured_energy"]]
            print("Retraining once for independent census and bookkeeping checks...", flush=True)
            train = module["make_source"](module["N_TRAIN"], module["DIMS"], 0)
            test = module["make_source"](module["N_TEST"], module["DIMS"], 500000)
            books = module["train_rvq"](train, module["LEVELS"], module["CODES"], 0)
            taus = module["set_thresholds"](train, books, module["VOID_RATE_TARGET"])
            silent_snaps = 0
            max_bookkeeping = 0.0
            max_cross_term_defect = 0.0
            paths = collections.Counter()
            residual_energy = 0.0
            for v in test:
                idx, parts = module["encode"](v, books, taus)
                paths[tuple(idx)] += 1
                r = list(v)
                for k, (j, part) in enumerate(zip(idx, parts)):
                    squared_dist = min(sum((a-b)**2 for a,b in zip(r,c)) for c in books[k])
                    if squared_dist > taus[k] and j != module["CODES"]:
                        silent_snaps += 1
                    r = [a-b for a,b in zip(r,part)]
                zh = module["decode"](idx, books)
                residue = [a-b for a,b in zip(v,zh)]
                residual_energy += sum(x*x for x in residue)
                max_bookkeeping = max(max_bookkeeping, max(abs(z-(a+b)) for z,a,b in zip(v,zh,residue)))
                defect = sum(x*x for x in v) - sum(x*x for x in zh) - sum(x*x for x in residue)
                cross = 2 * sum(a*b for a,b in zip(zh,residue))
                max_cross_term_defect = max(max_cross_term_defect, abs(defect-cross))
            calibration_rates, r = [], [list(v) for v in train]
            for k, book in enumerate(books):
                calibration_rates.append(sum(module["nearest"](v, book)[1] > taus[k] for v in r) / len(r))
                r = [module["sub"](v, book[module["nearest"](v, book)[0]]) for v in r]
            results["independent_census"] = {
                "silent_over_threshold_snap_count": silent_snaps,
                "max_z_equals_reconstruction_plus_residual_abs_error": max_bookkeeping,
                "max_energy_defect_minus_two_dot_abs_error": max_cross_term_defect,
                "final_residual_energy_frac": residual_energy / saved["held_out"]["signal_energy"],
                "heldout_distinct_paths": len(paths),
                "heldout_redundant_sample_fraction": 1-len(paths)/len(test),
                "heldout_fraction_of_samples_in_non_singleton_paths": sum(n for n in paths.values() if n > 1)/len(test),
                "heldout_non_singleton_path_multiplicities": sorted(n for n in paths.values() if n > 1),
                "unconditional_calibration_void_rates": calibration_rates,
                "actual_train_encoded_void_rates": saved["train"]["per_level_void_rate"],
            }
            def case(name, function):
                results["edge_cases"][name] = outcome(function)
            def vec(x):
                return [x] + [0] * 7
            book = [vec(1), vec(3)]
            case("over_threshold_rejects_and_preserves_residual_to_next_level", lambda: module["encode"](vec(10), [book, [vec(10)]], [1, 0]))
            case("threshold_equality_accepts", lambda: module["encode"](vec(2), [book], [1]))
            case("NaN_threshold_accepts_arbitrary_distance", lambda: module["encode"](vec(100), [book], [float("nan")]))
            case("NaN_input_snaps_first_code", lambda: module["encode"](vec(float("nan")), [book], [1]))
            case("extra_input_dimension_ignored", lambda: module["encode"](vec(1)+[1000000], [book], [0]))
            case("empty_input_accepts_first_code", lambda: module["encode"]([], [book], [0]))
            case("missing_tau_silently_skips_level", lambda: module["encode"](vec(1), [book], []))
            case("extra_tau_silently_ignored", lambda: module["encode"](vec(1), [book], [0, 0]))
            case("empty_book", lambda: module["encode"](vec(1), [[]], [1]))
            case("decode_negative_index_is_valid_Python_index", lambda: module["decode"]([-1], [book]))
            case("decode_invalid_index", lambda: module["decode"]([17], [book]))
            case("decode_short_book_changes_dimensions", lambda: module["decode"]([0], [[[1]]]))
            def void_collision():
                big_book = [vec(i) for i in range(17)]
                idx, parts = module["encode"](vec(16), [big_book], [0])
                return {"indices": idx, "parts": parts, "decode": module["decode"](idx, [big_book])}
            case("CODES_global_reserved_index_collides_with_17th_real_code", void_collision)
            case("decode_VOID_skips_missing_book", lambda: module["decode"]([16], []))
            case("measure_empty_data", lambda: module["measure"]("empty", [], books, taus))
            case("measure_all_zero_energy", lambda: module["measure"]("zero", [vec(0)], [[vec(0)]]*4, [0]*4))
            case("measure_no_levels", lambda: module["measure"]("none", [vec(1)], [], []))
            case("threshold_target_zero", lambda: module["set_thresholds"]([vec(1),vec(2)], [book], 0))
            case("kmeans_more_codes_than_samples", lambda: module["kmeans"]([vec(1)], 2, 0))
            case("ragged_kmeans", lambda: module["kmeans"]([[0], [0,1]], 1, 0))
            case("nearest_overflow", lambda: module["nearest"]([1e308], [[0]]))
            case("verdict_NaN_measured", lambda: module["verdict"](float("nan"), 1, 0.1))
        finally:
            os.chdir(original_cwd)
    after = {str(p): sha(p) for p in files}
    results["original_sha256_after"] = after
    results["originals_unchanged"] = before == after
    results["temporary_execution_directory_removed"] = not Path(results["temporary_cwd"]).exists()
    checks = {
        "originals_unchanged": results["originals_unchanged"],
        "stable_saved_replay_exact_match": not results["replay"]["saved_vs_replay_stable_differences"],
        "stable_two_replays_exact_match": not results["replay"]["replay1_vs_replay2_stable_differences"],
        "recorded_verdicts_match": all(v["recorded"] == v["recomputed"] for v in results["verdict_recalculation"]),
        "finite_heldout_no_silent_snaps": results["independent_census"]["silent_over_threshold_snap_count"] == 0,
        "independent_final_energy_matches": results["independent_census"]["final_residual_energy_frac"] == saved["held_out"]["final_residual_energy_frac"],
        "independent_path_census_matches": results["independent_census"]["heldout_distinct_paths"] == saved["held_out"]["codepath_distinct"],
    }
    results["checks"] = checks
    results["all_checks_passed"] = all(checks.values())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(safe(results), indent=2, ensure_ascii=False, allow_nan=False)+"\n", encoding="utf-8")
    print("Kimi evidence:", args.output)
    print("All checks passed:", results["all_checks_passed"])
    print("Stable saved-run differences:", len(results["replay"]["saved_vs_replay_stable_differences"]))
    print("Edge cases:", len(results["edge_cases"]))
    return 0 if results["all_checks_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
