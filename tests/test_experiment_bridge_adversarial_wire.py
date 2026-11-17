"""Note 2026-11-17: v1.1 wire/output regression gates; legacy v1 is immutable.

Run: python tests/test_experiment_bridge_adversarial_wire.py
Path attacks use temporary mock specimens. Optional cobc tests skip if unavailable.
The inherited transport tests exercise the unmodified v1 expectations against
candidate APIs without changing v1 files or their test imports.
"""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.experiment_bridge.v1_1 import demo, wire
from experiments.experiment_bridge.adversarial.wire_probe import envelope, fake_bench, probe

spec = importlib.util.spec_from_file_location("_candidate_wire_compat", ROOT / "tests/test_experiment_bridge_wire.py")
legacy_tests = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy_tests)
legacy_tests.wire = wire
legacy_tests.WORK = Path(tempfile.gettempdir()) / "candidate-wire-compat"


class TestCandidateEnvelopeCompatibility(legacy_tests.TestStrictEnvelope):
    pass


class TestCandidateCobolCompatibility(legacy_tests.TestCobolTransport):
    pass


def nested(depth):
    value = 0
    for _ in range(depth - 1):
        value = [value]
    return {"x": value}


class TestBoundedCandidateJSON(unittest.TestCase):
    def test_explicit_constants(self):
        self.assertEqual((wire.JSON_CAPACITY, wire.HEADER_SIZE, wire.RECORD_SIZE), (16384, 76, 16460))
        self.assertEqual((wire.MAX_JSON_DEPTH, wire.MAX_JSON_NODES, wire.MAX_RECORDS), (64, 16384, 64))
        self.assertEqual(wire.PROCESS_TIMEOUT_SECONDS, 30)

    def test_depth_boundary_encode_decode(self):
        payload = nested(wire.MAX_JSON_DEPTH)
        self.assertEqual(wire.decode_record(wire.encode_record(payload)), payload)
        with self.assertRaisesRegex(ValueError, "nesting depth exceeds 64"):
            wire.encode_record(nested(wire.MAX_JSON_DEPTH + 1))
        data = b'{"x":' + b'[' * 64 + b'0' + b']' * 64 + b'}'
        self.assertLess(len(data), wire.JSON_CAPACITY)
        with patch.object(wire.json, "loads", side_effect=AssertionError("must preflight depth")):
            with self.assertRaisesRegex(ValueError, "nesting depth exceeds 64"):
                wire.decode_record(envelope(data, wire))

    def test_quoted_brackets_and_escaped_quotes_not_depth(self):
        payload = {"x": ('[{}]\\\"' * 1000)}
        self.assertEqual(wire.decode_record(wire.encode_record(payload)), payload)

    def test_deep_under_capacity_v1_is_preserved_candidate_rejects(self):
        old, new = probe("v1", "deep_decode"), probe("v1_1", "deep_decode")
        self.assertEqual(old["exception"], "RecursionError")
        self.assertEqual(new["exception"], "ValueError")
        self.assertEqual(new["json_bytes"], 2407)

    def test_oversize_preflight_avoids_serialization(self):
        shared = 0
        for _ in range(12):
            shared = {"a": shared, "b": shared}
        values = ([None] * 16385, "a" * 50000, "雪" * 3000, 10 ** 17000,
                  shared, nested(1200))
        with patch.object(wire, "_json_text", side_effect=AssertionError("serialized oversized input")):
            for value in values:
                with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                    wire.encode_record({"x": value})

    def test_huge_integer_rejected_before_chunk_conversion(self):
        with patch.object(wire, "_integer_text", side_effect=AssertionError("converted huge integer")):
            for number in (10 ** 17000, -(10 ** 17000)):
                with self.assertRaisesRegex(ValueError, "integer exceeds"):
                    wire.encode_record({"x": number})

    def test_largest_record_legal_integer_and_conversion_limit(self):
        before = sys.get_int_max_str_digits()
        payload = {"x": 10 ** 16377}
        record = wire.encode_record(payload)
        self.assertEqual(int(record[4:12]), wire.JSON_CAPACITY)
        self.assertEqual(wire.decode_record(record), payload)
        self.assertEqual(sys.get_int_max_str_digits(), before)
        with self.assertRaises(ValueError):
            wire.encode_record({"x": -(10 ** 16377)})

    def test_node_budget_counts_shared_values_and_keys(self):
        with patch.object(wire, "MAX_JSON_NODES", 5):
            self.assertEqual(wire.decode_record(wire.encode_record({"x": [0, 1]})), {"x": [0, 1]})
            with self.assertRaisesRegex(ValueError, "node count"):
                wire.encode_record({"x": [0, 1, 2]})

    def test_all_ascii_and_unicode_escape_sizes(self):
        text = "".join(chr(i) for i in range(128)) + "é雪😀\ud800"
        payload = {"x": text}
        self.assertEqual(wire.decode_record(wire.encode_record(payload)), payload)
        for char, width in (("a", 1), ("\x7f", 6), ("\x00", 6), ("\n", 2), ("雪", 6), ("😀", 12)):
            count = (wire.JSON_CAPACITY - 8) // width
            with self.subTest(char=repr(char)):
                wire.encode_record({"x": char * count})
                with self.assertRaises(ValueError):
                    wire.encode_record({"x": char * (count + 1)})

    def test_recursion_errors_normalized(self):
        with patch.object(wire, "_validate", side_effect=RecursionError("mock")):
            with self.assertRaisesRegex(ValueError, "maximum depth 64"):
                wire.encode_record({"x": 1})
        record = wire.encode_record({"x": 1})
        with patch.object(wire.json, "loads", side_effect=RecursionError("mock")):
            with self.assertRaisesRegex(ValueError, "maximum depth 64"):
                wire.decode_record(record)

    def test_stream_limit_consumes_at_most_one_extra_item(self):
        record = wire.encode_record({"x": 1})
        consumed = 0
        def records():
            nonlocal consumed
            while True:
                consumed += 1
                yield record
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "record count exceeds 64"):
                wire.roundtrip_with_cobol(records(), Path(temp) / "not-created")
            self.assertEqual(consumed, wire.MAX_RECORDS + 1)
            self.assertFalse((Path(temp) / "not-created").exists())
            with patch.object(wire.shutil, "which", return_value=None):
                result = wire.roundtrip_with_cobol((record for _ in range(64)), Path(temp) / "not-created")
            self.assertEqual(result["record_count"], 64)
            self.assertEqual(result["status"], "NOT_RUNNABLE")

    def test_timeout_bytes_and_text_normalization(self):
        for stdout, stderr in ((b"partial", b"error"), ("partial", "error"), (None, None)):
            with patch.object(wire.subprocess, "run", side_effect=subprocess.TimeoutExpired(["mock"], 30, stdout, stderr)) as call:
                result = wire._run(["mock"], ROOT)
            self.assertIsNone(result["returncode"])
            self.assertIsInstance(result["stdout"], str)
            self.assertEqual(call.call_args.kwargs["timeout"], 30)


class TestCandidateOutputPolicy(unittest.TestCase):
    def test_every_held_path_and_alias_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            bench = fake_bench(temp)
            with patch.object(wire, "__file__", str(bench / "v1_1/wire.py")), patch.object(demo, "BENCH", bench):
                for name in wire.PROTECTED_OUTPUT_PATHS:
                    output = bench / name / "never-created"
                    with self.subTest(name=name):
                        for operation in (lambda: wire.roundtrip_with_cobol([], output), lambda: demo.run(output)):
                            with self.assertRaises(ValueError):
                                operation()
                        self.assertFalse(output.exists())
                    alias = temp / (name.replace("/", "-") + "-alias")
                    held = bench / name
                    held.mkdir(parents=True, exist_ok=True)
                    alias.symlink_to(held, target_is_directory=True)
                    with self.assertRaises(ValueError):
                        wire.roundtrip_with_cobol([], alias / "never-created")

    def test_lexical_held_path_even_when_symlink_resolves_outside(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            bench = temp / "bench"
            bench.mkdir()
            outside = temp / "outside"
            outside.mkdir()
            (bench / "audit").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                wire.checked_output_dir(bench / "audit/new", bench)

    def test_allowed_symlink_parent_resolves_and_existing_empty_supported(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            allowed = temp / "allowed"
            allowed.mkdir()
            (temp / "alias").symlink_to(allowed, target_is_directory=True)
            with patch.object(wire.shutil, "which", return_value=None):
                summary = demo.run(temp / "alias")
            self.assertEqual(summary["version"], "experiment-bridge/v1.1")
            self.assertEqual(summary["case_count"], 4)
            self.assertEqual(summary["cobol"]["status"], "NOT_RUNNABLE")
            self.assertTrue((allowed / "summary.json").is_file())
            with self.assertRaises(ValueError):
                demo.run(allowed)

    def test_injected_leaf_symlink_is_not_overwritten(self):
        result = probe("v1_1", "demo_file_symlink_race")
        self.assertEqual(result["exception"], "FileExistsError")
        self.assertTrue(result["victim_unchanged"])
        self.assertFalse(result["summary_exists"])

    def test_recheck_catches_injected_directory_swap_but_is_not_os_isolation(self):
        result = probe("v1_1", "demo_directory_swap")
        self.assertEqual(result["exception"], "ValueError")
        self.assertFalse(result["mock_held_fixture_written"])
        self.assertFalse(result["summary_exists"])

    def test_partial_demo_failure_has_no_success_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "output"
            original = demo.annotate_trace
            calls = 0
            def fail_second(*args, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("mock partial failure")
                return original(*args, **kwargs)
            with patch.object(demo, "annotate_trace", side_effect=fail_second):
                with self.assertRaises(OSError):
                    demo.run(output)
            self.assertTrue((output / "accepted_proposed_mapping.json").is_file())
            self.assertFalse((output / "summary.json").exists())

    def test_report_failure_and_artifact_failure_cannot_report_pass(self):
        result = probe("v1_1", "report_failure")
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["report_error"], "mock report write denied")
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(wire.shutil, "which", return_value="/mock/cobc"), \
                    patch.object(Path, "open", side_effect=OSError("mock artifact denied")), \
                    patch.object(wire, "write_text_exclusive", side_effect=OSError("mock report denied")):
                result = wire.roundtrip_with_cobol([], Path(temp) / "output")
            self.assertEqual(result["status"], "FAIL")
            self.assertEqual(result["compile_status"], "NOT_RUNNABLE")
            self.assertIn("prepare artifacts", result["error"])
            self.assertNotIn("report", result["artifacts"])

    def test_atomic_writer_failure_leaves_no_final_report(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "summary.json"
            with patch.object(wire.os, "link", side_effect=OSError("mock publication denied")):
                with self.assertRaises(OSError):
                    wire.write_text_exclusive(target, '{"status":"PASS"}\n')
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(temp).iterdir()), [])
            original = wire.tempfile.NamedTemporaryFile
            def fail_write(*args, **kwargs):
                handle = original(*args, **kwargs)
                def broken(text):
                    handle.file.write(text[:5])
                    raise OSError("mock partial write")
                handle.write = broken
                return handle
            with patch.object(wire.tempfile, "NamedTemporaryFile", side_effect=fail_write):
                with self.assertRaises(OSError):
                    wire.write_text_exclusive(target, '{"status":"PASS"}\n')
            self.assertFalse(target.exists())
            self.assertEqual(list(Path(temp).iterdir()), [])

    def test_transport_pass_with_report_failure_is_overall_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            def simulated_run(command, cwd):
                (cwd / "output.dat").write_bytes((cwd / "input.dat").read_bytes())
                return {"returncode": 0}
            with patch.object(wire.shutil, "which", return_value="/mock/cobc"), \
                    patch.object(wire, "_run", side_effect=simulated_run), \
                    patch.object(wire, "write_text_exclusive", side_effect=OSError("mock report denied")):
                result = wire.roundtrip_with_cobol([wire.encode_record({"x": 1})], Path(temp) / "output")
            self.assertTrue(result["exact_bytes_equal"])
            self.assertEqual((result["compile_status"], result["runtime_status"]), ("PASS", "PASS"))
            self.assertEqual(result["status"], "FAIL")
            self.assertNotIn("report", result["artifacts"])
            self.assertFalse((Path(result["run_dir"]) / "result.json").exists())

    def test_demo_compiler_failure_summary_is_explicit_and_cli_nonzero(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(demo, "roundtrip_with_cobol", return_value={"status": "FAIL"}):
                summary = demo.run(Path(temp) / "output")
            self.assertEqual(summary["cobol"]["status"], "FAIL")
            saved = json.loads((Path(temp) / "output/summary.json").read_text())
            self.assertEqual(saved["cobol"]["status"], "FAIL")
            with patch.object(demo, "run", return_value=summary), patch.object(sys, "argv", ["demo", "--output-dir", temp]):
                with self.assertRaises(SystemExit) as exc:
                    demo.main()
            self.assertEqual(exc.exception.code, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
