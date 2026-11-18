"""ILLUSTRATIVE transport fixtures, not numerical or semantic measurements.

Run from repository root: python tests/test_experiment_bridge_wire.py
The optional real-compiler tests are skipped, not passed, when cobc is absent.
Generated run files live outside the repository's audited evidence.
"""

import hashlib
import json
import math
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from experiments.experiment_bridge.v1 import wire

# was a fixed path under another machine's home directory, which a CI runner
# cannot create; the system temp directory serves the same purpose
WORK = Path(tempfile.gettempdir()) / "expansion_work" / "wire"


def envelope(data):
    """Build deliberately invalid but correctly hashed test specimens."""
    return (b"EB01" + f"{len(data):08d}".encode("ascii")
            + hashlib.sha256(data).hexdigest().encode("ascii")
            + data.ljust(wire.JSON_CAPACITY, b" "))


class TestStrictEnvelope(unittest.TestCase):
    def setUp(self):
        self.record = wire.encode_record({"x": 1})

    def test_fixed_ascii_shape(self):
        self.assertEqual(wire.RECORD_SIZE, 16460)
        self.assertEqual(len(self.record), 16460)
        self.assertTrue(self.record.isascii())
        self.assertEqual(self.record[:12], b"EB0100000007")
        self.assertEqual(wire.decode_record(self.record), {"x": 1})

    def test_unicode_apostrophe_null_bool_float_large_int(self):
        payload = {"text": "O'Brien — 雪 😀\u0000\n\r\t", "null": None,
                   "bool": [True, False], "big": 10 ** 300 + 37,
                   "floats": [0.1, 1.0, -0.0, 5e-324, 1.7976931348623157e308],
                   "nested": [{"é": "\\quoted\""}]}
        record = wire.encode_record(payload)
        decoded = wire.decode_record(record)
        self.assertEqual(decoded, payload)
        self.assertEqual(math.copysign(1, decoded["floats"][2]), -1)
        self.assertIn(b"\\u96ea", record)
        self.assertIn(b"O'Brien", record)
        self.assertTrue(record.isascii())
        self.assertEqual(wire.encode_record(decoded), record)

    def test_integer_beyond_default_conversion_limit(self):
        limit = sys.get_int_max_str_digits()
        payload = {"positive": 10 ** 5000 + 37, "negative": -(10 ** 5000 + 91)}
        record = wire.encode_record(payload)
        self.assertEqual(wire.decode_record(record), payload)
        self.assertEqual(sys.get_int_max_str_digits(), limit)
        with self.assertRaises(ValueError):
            wire.encode_record({"x": 10 ** 17000})

    def test_sorted_compact_json(self):
        first = wire.encode_record({"z": 0, "a": {"y": 2, "b": 1}})
        second = wire.encode_record({"a": {"b": 1, "y": 2}, "z": 0})
        self.assertEqual(first, second)
        self.assertTrue(first[76:].startswith(b'{"a":{"b":1,"y":2},"z":0}'))

    def test_exact_capacity_no_truncation(self):
        payload = {"x": "a" * (wire.JSON_CAPACITY - len(b'{"x":""}'))}
        record = wire.encode_record(payload)
        self.assertEqual(int(record[4:12]), wire.JSON_CAPACITY)
        self.assertEqual(wire.decode_record(record), payload)
        with self.assertRaises(ValueError):
            wire.encode_record({"x": payload["x"] + "a"})

    def test_unicode_width_uses_ascii_bytes(self):
        with self.assertRaises(ValueError):
            wire.encode_record({"x": "雪" * 3000})

    def test_nonfinite_recursive_encode(self):
        for number in (float("nan"), float("inf"), -float("inf")):
            with self.subTest(number=number), self.assertRaises(ValueError):
                wire.encode_record({"nested": [{"number": number}]})

    def test_nonstring_keys_recursive(self):
        for key in (1, True, None, ("key",)):
            with self.subTest(key=key), self.assertRaises(TypeError):
                wire.encode_record({"nested": [{key: "value"}]})

    def test_unsupported_objects_and_root_types(self):
        for value in (set(), (1, 2), b"bytes", object(), complex(1, 2)):
            with self.subTest(value=repr(value)), self.assertRaises(TypeError):
                wire.encode_record({"x": value})
        for root in ([], "text", 3, None, True):
            with self.subTest(root=root), self.assertRaises(TypeError):
                wire.encode_record(root)

    def test_cycles_rejected_shared_objects_allowed(self):
        cyclic = []
        cyclic.append(cyclic)
        with self.assertRaises(ValueError):
            wire.encode_record({"x": cyclic})
        shared = {"v": 2}
        self.assertEqual(wire.decode_record(wire.encode_record({"a": shared, "b": shared})),
                         {"a": {"v": 2}, "b": {"v": 2}})

    def test_wrong_record_width_and_type(self):
        for record in (self.record[:-1], self.record + b" ", b"", self.record * 2):
            with self.subTest(length=len(record)), self.assertRaises(ValueError):
                wire.decode_record(record)
        for record in ("text", bytearray(self.record), None):
            with self.subTest(type=type(record)), self.assertRaises(TypeError):
                wire.decode_record(record)

    def test_bad_header_and_nonascii(self):
        for record in (b"EB02" + self.record[4:], b"\xff" + self.record[1:],
                       self.record[:-1] + b"\x80"):
            with self.subTest(header=record[:4]), self.assertRaises(ValueError):
                wire.decode_record(record)

    def test_bad_length_digits_range_and_mismatch(self):
        for field in (b"+0000007", b"0000000x", b" 0000007", b"00000000",
                      b"00000001", b"00016385", b"99999999", b"00000006", b"00000008"):
            with self.subTest(field=field), self.assertRaises(ValueError):
                wire.decode_record(self.record[:4] + field + self.record[12:])

    def test_payload_tamper_rejected(self):
        with self.assertRaises(ValueError):
            wire.decode_record(self.record[:81] + b"2" + self.record[82:])

    def test_bad_hash(self):
        for digest in (b"g" * 64, b"0" * 64, self.record[12:76].upper()):
            with self.subTest(digest=digest), self.assertRaises(ValueError):
                wire.decode_record(self.record[:12] + digest + self.record[76:])

    def test_bad_padding(self):
        for byte in (b"\n", b"\x00", b"\t", b"x"):
            with self.subTest(byte=byte), self.assertRaises(ValueError):
                wire.decode_record(self.record[:-1] + byte)

    def test_duplicate_keys_at_any_depth(self):
        for data in (b'{"x":1,"x":2}', b'{"x":{"a":1,"a":2}}',
                     b'{"x":1,"\\u0078":2}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                wire.decode_record(envelope(data))

    def test_nonfinite_decode_including_overflow(self):
        for data in (b'{"x":NaN}', b'{"x":Infinity}', b'{"x":-Infinity}',
                     b'{"x":[{"n":1e999}]}'):
            with self.subTest(data=data), self.assertRaises(ValueError):
                wire.decode_record(envelope(data))

    def test_noncanonical_spelling_rejected(self):
        for data in (b'{ "x":1}', b'{"z":0,"a":1}', b'{"x":1e0}',
                     b'{"x":-0}', b'{"x":"\\u0061"}', b'{"x":1} '):
            with self.subTest(data=data), self.assertRaises(ValueError):
                wire.decode_record(envelope(data))

    def test_invalid_json_and_nonobject_decode(self):
        for data in (b'{"x":}', b'[]', b'null', b'1234'):
            with self.subTest(data=data), self.assertRaises((ValueError, TypeError)):
                wire.decode_record(envelope(data))

    def test_rehashed_change_is_not_authentication(self):
        changed = envelope(b'{"x":2}')
        self.assertNotEqual(changed, self.record)
        self.assertEqual(wire.decode_record(changed), {"x": 2})

    def test_copybook_is_data_free_character_fields(self):
        source = wire.copybook_text()
        self.assertTrue(source.isascii())
        for width in (4, 8, 64, 16384):
            self.assertIn(f"PIC X({width})", source)
        self.assertNotIn("O'Brien", source)


class TestCobolTransport(unittest.TestCase):
    def setUp(self):
        WORK.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="test-", dir=WORK)
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)
        self.records = [wire.encode_record({"text": "O'Brien 雪 😀\u0000", "float": 0.1}),
                        wire.encode_record({"null": None, "big": 10 ** 200, "bool": True})]

    @unittest.skipUnless(shutil.which("cobc"), "optional cobc compiler NOT_RUNNABLE")
    def test_two_real_records_exact_raw_bytes(self):
        result = wire.roundtrip_with_cobol(self.records, self.output)
        self.assertEqual(result["status"], "PASS", json.dumps(result, indent=2))
        self.assertEqual(result["compile"]["returncode"], 0)
        self.assertEqual(result["runtime"]["returncode"], 0)
        self.assertTrue(result["exact_bytes_equal"])
        expected = b"".join(self.records)
        self.assertEqual(Path(result["artifacts"]["input"]).read_bytes(), expected)
        actual = Path(result["artifacts"]["output"]).read_bytes()
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 2 * wire.RECORD_SIZE)
        for offset, original in enumerate(self.records):
            self.assertEqual(actual[offset * wire.RECORD_SIZE:(offset + 1) * wire.RECORD_SIZE],
                             original)
        source = Path(result["artifacts"]["source"]).read_text()
        self.assertNotIn("O'Brien", source)
        self.assertNotIn("line sequential", source.lower())
        self.assertIn("recording mode is F", source)

    @unittest.skipUnless(shutil.which("cobc"), "optional cobc compiler NOT_RUNNABLE")
    def test_empty_stream_real_roundtrip(self):
        result = wire.roundtrip_with_cobol([], self.output)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(Path(result["artifacts"]["output"]).read_bytes(), b"")

    @unittest.skipUnless(shutil.which("cobc"), "optional cobc compiler NOT_RUNNABLE")
    def test_full_width_real_roundtrip(self):
        payload = {"x": "a" * (wire.JSON_CAPACITY - len(b'{"x":""}'))}
        record = wire.encode_record(payload)
        result = wire.roundtrip_with_cobol([record], self.output)
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(Path(result["artifacts"]["output"]).read_bytes(), record)

    def test_missing_compiler_not_runnable(self):
        with patch.object(wire.shutil, "which", return_value=None):
            result = wire.roundtrip_with_cobol(self.records, self.output)
        self.assertEqual(result["status"], "NOT_RUNNABLE")
        self.assertIsNone(result["exact_bytes_equal"])
        self.assertIsNone(result["compile"])
        self.assertIsNone(result["runtime"])
        self.assertEqual(list(self.output.iterdir()), [])

    def test_compile_failure_not_pass(self):
        diagnostic = {"returncode": 1, "stderr": "ILLUSTRATIVE simulated compiler error"}
        with patch.object(wire.shutil, "which", return_value="/unused/cobc"), \
                patch.object(wire, "_run", return_value=diagnostic):
            result = wire.roundtrip_with_cobol(self.records, self.output)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["compile_status"], "FAIL")
        self.assertEqual(result["compile"], diagnostic)
        self.assertIsNone(result["runtime"])
        self.assertIsNone(result["exact_bytes_equal"])

    def test_runtime_failure_not_pass(self):
        diagnostics = [{"returncode": 0}, {"returncode": 1, "stderr": "simulated runtime error"}]
        with patch.object(wire.shutil, "which", return_value="/unused/cobc"), \
                patch.object(wire, "_run", side_effect=diagnostics):
            result = wire.roundtrip_with_cobol(self.records, self.output)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["compile_status"], "PASS")
        self.assertEqual(result["runtime_status"], "FAIL")
        self.assertFalse(result["exact_bytes_equal"])

    def test_successful_runtime_with_changed_bytes_not_pass(self):
        def simulated_run(command, cwd):
            # Deliberately wrong output; this is not an actual compiler proof.
            (cwd / "output.dat").write_bytes(b"ILLUSTRATIVE changed bytes")
            return {"command": command, "returncode": 0, "stdout": "", "stderr": ""}

        with patch.object(wire.shutil, "which", return_value="/unused/cobc"), \
                patch.object(wire, "_run", side_effect=simulated_run):
            result = wire.roundtrip_with_cobol(self.records, self.output)
        self.assertEqual(result["compile_status"], "PASS")
        self.assertEqual(result["runtime_status"], "PASS")
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(result["exact_bytes_equal"])

    def test_invalid_records_rejected_before_writes(self):
        with self.assertRaises(ValueError):
            wire.roundtrip_with_cobol([self.records[0], b"bad"], self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_audited_output_directories_forbidden(self):
        bench = ROOT / "experiments" / "experiment_bridge"
        for name in ("raw", "evidence", "audit"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                wire.roundtrip_with_cobol(self.records, bench / name / "never-written")


if __name__ == "__main__":
    unittest.main(verbosity=2)
