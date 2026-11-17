"""Note 2026-11-17: reproducible bounded v1/v1.1 adversarial wire probes.

Run from repository root:
python experiments/experiment_bridge/adversarial/wire_probe.py
Every child has a five-second deadline. Path attacks use disposable mock benches,
never actual specimens. This is not an exhaustion or arbitrary-process sandbox.
"""
import argparse
from contextlib import ExitStack
import hashlib
import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
VERSIONS = ("v1", "v1_1")
CASES = (
    "deep_decode", "deep_encode", "wide_encode", "huge_string", "unicode_size",
    "huge_integer", "shared_expansion", "cycle", "legal_integer", "exact_capacity",
    "noncanonical", "rehashed_change", "stream_count", "held_legacy_runs",
    "held_candidate_runs", "held_adversarial", "symlink_held_parent",
    "demo_held_legacy_runs", "demo_file_symlink_race", "demo_directory_swap",
    "demo_partial_failure", "compiler_timeout", "compile_failure", "report_failure",
    "real_cobol",
)


def envelope(data, wire):
    return (wire.MAGIC + f"{len(data):08d}".encode("ascii")
            + hashlib.sha256(data).hexdigest().encode("ascii")
            + data.ljust(wire.JSON_CAPACITY, b" "))


def fake_bench(path):
    bench = Path(path) / "bench"
    for name in ("raw", "evidence", "audit", "v1", "v1_1", "adversarial"):
        (bench / name).mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "experiments/experiment_bridge/raw/lojban_wordslot_reference.json",
                    bench / "raw/lojban_wordslot_reference.json")
    return bench


def probe(version, case):
    wire = importlib.import_module(f"experiments.experiment_bridge.{version}.wire")
    demo = importlib.import_module(f"experiments.experiment_bridge.{version}.demo")
    detail = {}
    try:
        with tempfile.TemporaryDirectory(prefix="bridge-wire-probe-") as temp:
            temp = Path(temp)
            if case == "deep_decode":
                data = b'{"x":' + b'[' * 1200 + b'0' + b']' * 1200 + b'}'
                detail["json_bytes"] = len(data)
                wire.decode_record(envelope(data, wire))
            elif case in ("deep_encode", "wide_encode", "huge_string", "unicode_size",
                          "huge_integer", "shared_expansion", "cycle"):
                if case == "deep_encode":
                    value = 0
                    for _ in range(1200):
                        value = [value]
                elif case == "wide_encode":
                    value = [None] * 16385
                elif case == "huge_string":
                    value = "a" * 50000
                elif case == "unicode_size":
                    value = "雪" * 3000
                elif case == "huge_integer":
                    value = 10 ** 17000
                elif case == "shared_expansion":
                    value = 0
                    for _ in range(12):
                        value = {"a": value, "b": value}
                else:
                    value = []
                    value.append(value)
                calls = []
                original = wire._json_text
                def tracked(item):
                    calls.append(1)
                    return original(item)
                try:
                    with patch.object(wire, "_json_text", side_effect=tracked):
                        wire.encode_record({"x": value})
                finally:
                    detail["serialization_calls"] = len(calls)
            elif case == "legal_integer":
                payload = {"x": 10 ** 16376}
                record = wire.encode_record(payload)
                detail["equal"] = wire.decode_record(record) == payload
                detail["json_bytes"] = int(record[4:12])
            elif case == "exact_capacity":
                payload = {"x": "a" * (wire.JSON_CAPACITY - 8)}
                record = wire.encode_record(payload)
                detail["equal"] = wire.decode_record(record) == payload
                detail["json_bytes"] = int(record[4:12])
            elif case == "noncanonical":
                samples = (b'{ "x":1}', b'{"z":0,"a":1}', b'{"x":1e0}',
                           b'{"x":-0}', b'{"x":"\\u0061"}', b'{"x":1} ',
                           b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}')
                rejected = 0
                for data in samples:
                    try:
                        wire.decode_record(envelope(data, wire))
                    except ValueError:
                        rejected += 1
                detail.update(rejected=rejected, total=len(samples))
            elif case == "rehashed_change":
                detail["accepted_change"] = wire.decode_record(envelope(b'{"x":2}', wire)) == {"x": 2}
            elif case == "stream_count":
                record = wire.encode_record({"x": 1})
                count = 0
                def stream():
                    nonlocal count
                    for _ in range(66):
                        count += 1
                        yield record
                    raise RuntimeError("probe stopped unbounded collection after 66 records")
                try:
                    with patch.object(wire.shutil, "which", return_value=None):
                        wire.roundtrip_with_cobol(stream(), temp / "output")
                finally:
                    detail["items_consumed"] = count
            elif case.startswith("held_") or case == "symlink_held_parent":
                bench = fake_bench(temp)
                destinations = {"held_legacy_runs": "v1/runs/new-run",
                                "held_candidate_runs": "v1_1/runs/new-run",
                                "held_adversarial": "adversarial/new-evidence"}
                if case == "symlink_held_parent":
                    (temp / "alias").symlink_to(bench / "raw", target_is_directory=True)
                    output = temp / "alias/new-run"
                else:
                    output = bench / destinations[case]
                with patch.object(wire, "__file__", str(bench / version / "wire.py")), \
                        patch.object(wire.shutil, "which", return_value=None):
                    detail["status"] = wire.roundtrip_with_cobol([], output)["status"]
            elif case.startswith("demo_"):
                bench = fake_bench(temp)
                output = temp / "output"
                output.mkdir()
                original = demo.normalize_reference
                victim = temp / "victim.txt"
                victim.write_text("untouched\n")
                first = "accepted_proposed_mapping.json"
                def intervene(raw):
                    if case == "demo_file_symlink_race":
                        (output / first).symlink_to(victim)
                    elif case == "demo_directory_swap":
                        output.rmdir()
                        output.symlink_to(bench / "raw", target_is_directory=True)
                    return original(raw)
                if case == "demo_held_legacy_runs":
                    output = bench / "v1/runs/new-run"
                try:
                    with patch.object(demo, "BENCH", bench), \
                            patch.object(demo, "normalize_reference", side_effect=intervene), \
                            patch.object(demo, "roundtrip_with_cobol", return_value={"status": "NOT_RUNNABLE"}):
                        if case == "demo_partial_failure":
                            original_annotate = demo.annotate_trace
                            calls = 0
                            def fail_second(*args, **kwargs):
                                nonlocal calls
                                calls += 1
                                if calls == 2:
                                    raise OSError("mock partial failure")
                                return original_annotate(*args, **kwargs)
                            with patch.object(demo, "annotate_trace", side_effect=fail_second):
                                demo.run(output)
                        else:
                            detail["case_count"] = demo.run(output)["case_count"]
                finally:
                    detail["victim_unchanged"] = victim.read_text() == "untouched\n"
                    detail["summary_exists"] = (output / "summary.json").exists()
                    detail["first_fixture_exists"] = (output / first).exists()
                    detail["mock_held_fixture_written"] = (bench / "raw" / first).exists()
            elif case == "compiler_timeout":
                exc = subprocess.TimeoutExpired(["mock"], 30, output=b"partial", stderr=b"diagnostic")
                with patch.object(wire.subprocess, "run", side_effect=exc) as call:
                    detail.update(wire._run(["mock"], temp))
                    detail["timeout_seconds"] = call.call_args.kwargs["timeout"]
            elif case in ("compile_failure", "report_failure"):
                diagnostic = {"returncode": 1, "stdout": "", "stderr": "mock compile failure"}
                original_open = Path.open
                def broken_report(path, *args, **kwargs):
                    if path.name == "result.json":
                        raise OSError("mock report write denied")
                    return original_open(path, *args, **kwargs)
                with patch.object(wire.shutil, "which", return_value="/mock/cobc"), \
                        patch.object(wire, "_run", return_value=diagnostic):
                    if case == "report_failure":
                        with ExitStack() as stack:
                            stack.enter_context(patch.object(Path, "open", broken_report))
                            if hasattr(wire, "write_text_exclusive"):
                                stack.enter_context(patch.object(wire, "write_text_exclusive",
                                                                side_effect=OSError("mock report write denied")))
                            result = wire.roundtrip_with_cobol([wire.encode_record({"x": 1})], temp / "output")
                    else:
                        result = wire.roundtrip_with_cobol([wire.encode_record({"x": 1})], temp / "output")
                detail.update(status=result["status"], compile_status=result["compile_status"],
                              report_error=result.get("report_error"))
            elif case == "real_cobol":
                result = wire.roundtrip_with_cobol([wire.encode_record({"x": "雪 O'Brien", "n": 0.1})], temp / "output")
                detail.update(status=result["status"], exact_bytes_equal=result["exact_bytes_equal"],
                              compile_status=result["compile_status"], runtime_status=result["runtime_status"])
            return {"outcome": "returned", **detail}
    except Exception as exc:
        return {"outcome": "raised", "exception": type(exc).__name__,
                "message": str(exc)[:300], **detail}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", choices=VERSIONS)
    parser.add_argument("--case", choices=CASES)
    parser.add_argument("--output", type=Path, default=Path(__file__).with_name("wire_results.json"))
    args = parser.parse_args()
    if args.case:
        if not args.version:
            parser.error("--case requires --version")
        print(json.dumps(probe(args.version, args.case), sort_keys=True))
        return
    results = {"note_date": "2026-11-17", "baseline": "19c9a80", "probe_timeout_seconds": 5,
               "scope": "bounded software probes; all write adversaries use temporary mock benches",
               "cases": {}}
    for case in CASES:
        results["cases"][case] = {}
        for version in VERSIONS:
            command = [sys.executable, str(Path(__file__).resolve()), "--version", version, "--case", case]
            try:
                child = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                                       timeout=5, check=False)
                result = json.loads(child.stdout) if child.returncode == 0 else {
                    "outcome": "child_error", "returncode": child.returncode,
                    "stderr": child.stderr[-1000:]}
            except subprocess.TimeoutExpired:
                result = {"outcome": "bounded_timeout", "timeout_seconds": 5}
            results["cases"][case][version] = result
        print(case, json.dumps(results["cases"][case], sort_keys=True), flush=True)
    from experiments.experiment_bridge.v1_1 import wire
    results["candidate_limits"] = {name: getattr(wire, name) for name in (
        "JSON_CAPACITY", "HEADER_SIZE", "RECORD_SIZE", "MAX_JSON_DEPTH", "MAX_JSON_NODES",
        "MAX_JSON_STRING_LENGTH", "MAX_INTEGER_DIGITS", "MAX_RECORDS", "PROCESS_TIMEOUT_SECONDS",
        "PROTECTED_OUTPUT_PATHS")}
    observations = [item for versions in results["cases"].values() for item in versions.values()]
    results["counts"] = {"cases": len(CASES), "versions": len(VERSIONS),
                         "executions": len(observations),
                         "bounded_timeouts": sum(item["outcome"] == "bounded_timeout" for item in observations),
                         "child_errors": sum(item["outcome"] == "child_error" for item in observations)}
    args.output.write_text(json.dumps(results, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
