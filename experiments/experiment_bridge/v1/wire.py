"""Reversible finite JSON transport, not decimal metrology or an immutable ledger.

SHA-256 detects change relative to the envelope; it does NOT authenticate its
sender or certify truth. A sender can alter a payload and recompute its hash.
Canonical spelling is Python JSON with ASCII escapes, sorted keys and compact
separators. Floats retain Python's JSON representation, not exact decimals.
"""

import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

MAGIC = b"EB01"
JSON_CAPACITY = 16384
HEADER_SIZE = 76
RECORD_SIZE = HEADER_SIZE + JSON_CAPACITY


def _validate(value, active=None):
    """Reject coercible-but-non-JSON types, non-string keys and cycles."""
    if value is None or type(value) in (str, bool, int):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("JSON floats must be finite")
        return
    if type(value) not in (dict, list):
        raise TypeError("payload contains an unsupported JSON type")
    active = set() if active is None else active
    if id(value) in active:
        raise ValueError("cyclic JSON payload")
    active.add(id(value))
    try:
        if type(value) is dict:
            if any(type(key) is not str for key in value):
                raise TypeError("JSON object keys must be strings")
            children = value.values()
        else:
            children = value
        for child in children:
            _validate(child, active)
    finally:
        active.remove(id(value))


def _integer_text(value):
    # Small chunks stay below Python's configurable int/str digit limit.
    negative, value = value < 0, abs(value)
    chunks = []
    while value >= 10 ** 500:
        value, remainder = divmod(value, 10 ** 500)
        chunks.append(str(remainder).zfill(500))
    return ("-" if negative else "") + str(value) + "".join(reversed(chunks))


def _parse_integer(text):
    negative = text.startswith("-")
    digits = text[1:] if negative else text
    value = 0
    for offset in range(0, len(digits), 500):
        chunk = digits[offset:offset + 500]
        value = value * 10 ** len(chunk) + int(chunk)
    return -value if negative else value


def _json_text(value):
    if type(value) is int:
        return _integer_text(value)
    if type(value) is dict:
        return "{" + ",".join(_json_text(key) + ":" + _json_text(value[key])
                              for key in sorted(value)) + "}"
    if type(value) is list:
        return "[" + ",".join(_json_text(child) for child in value) + "]"
    return json.dumps(value, ensure_ascii=True, sort_keys=True, allow_nan=False)


def encode_record(payload: dict) -> bytes:
    """Encode one canonical fixed-width ASCII envelope without truncation."""
    if type(payload) is not dict:
        raise TypeError("payload must be a JSON object (dict)")
    _validate(payload)
    data = _json_text(payload).encode("ascii")
    if len(data) > JSON_CAPACITY:
        raise ValueError("JSON payload exceeds 16384 ASCII bytes")
    return (MAGIC + f"{len(data):08d}".encode("ascii")
            + hashlib.sha256(data).hexdigest().encode("ascii")
            + data.ljust(JSON_CAPACITY, b" "))


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _constant(value):
    raise ValueError(f"nonfinite JSON constant: {value}")


def decode_record(record: bytes) -> dict:
    """Validate framing, integrity and canonical spelling, then decode JSON."""
    if not isinstance(record, bytes):
        raise TypeError("record must be bytes")
    if len(record) != RECORD_SIZE:
        raise ValueError("record must be exactly 16460 bytes")
    if not record.isascii() or record[:4] != MAGIC:
        raise ValueError("invalid ASCII envelope or magic")
    if re.fullmatch(rb"[0-9]{8}", record[4:12]) is None:
        raise ValueError("invalid decimal JSON length")
    length = int(record[4:12])
    if not 2 <= length <= JSON_CAPACITY:
        raise ValueError("JSON length is out of range")
    digest = record[12:HEADER_SIZE]
    if re.fullmatch(rb"[0-9a-f]{64}", digest) is None:
        raise ValueError("invalid lowercase SHA-256 hex")
    data = record[HEADER_SIZE:HEADER_SIZE + length]
    if record[HEADER_SIZE + length:] != b" " * (JSON_CAPACITY - length):
        raise ValueError("non-space JSON padding")
    if hashlib.sha256(data).hexdigest().encode("ascii") != digest:
        raise ValueError("JSON payload hash mismatch")
    payload = json.loads(data, object_pairs_hook=_object, parse_constant=_constant,
                         parse_int=_parse_integer)
    if encode_record(payload) != record:
        raise ValueError("noncanonical JSON spelling")
    return payload


def copybook_text() -> str:
    """Return a free-format, user-data-free character envelope definition."""
    return """01 EB-RECORD.
   05 EB-MAGIC       PIC X(4).
   05 EB-JSON-LENGTH PIC X(8).
   05 EB-SHA256      PIC X(64).
   05 EB-JSON-AREA   PIC X(16384).
"""


_RUNTIME = """identification division.
program-id. eb-roundtrip.
environment division.
input-output section.
file-control.
    select input-file assign to "input.dat"
        organization is sequential file status is input-status.
    select output-file assign to "output.dat"
        organization is sequential file status is output-status.
data division.
file section.
fd input-file recording mode is F record contains 16460 characters.
copy "envelope.cpy".
fd output-file recording mode is F record contains 16460 characters.
01 output-record pic X(16460).
working-storage section.
01 input-status pic XX.
01 output-status pic XX.
procedure division.
    open input input-file
    if input-status not = "00"
        display "OPEN INPUT: " input-status
        move 1 to return-code stop run
    end-if
    open output output-file
    if output-status not = "00"
        display "OPEN OUTPUT: " output-status
        move 1 to return-code stop run
    end-if
    perform until input-status = "10"
        read input-file
        evaluate input-status
            when "00"
                move EB-RECORD to output-record
                write output-record
                if output-status not = "00"
                    display "WRITE: " output-status
                    move 1 to return-code stop run
                end-if
            when "10" continue
            when other
                display "READ: " input-status
                move 1 to return-code stop run
        end-evaluate
    end-perform
    close input-file output-file
    if input-status not = "00" or output-status not = "00"
        display "CLOSE: " input-status " " output-status
        move 1 to return-code stop run
    end-if
    move 0 to return-code
    stop run.
"""


def _run(command, cwd):
    try:
        process = subprocess.run(command, cwd=cwd, capture_output=True,
                                 text=True, errors="replace", timeout=30, check=False)
        return {"command": command, "returncode": process.returncode,
                "stdout": process.stdout, "stderr": process.stderr}
    except subprocess.TimeoutExpired as exc:
        return {"command": command, "returncode": None,
                "stdout": (exc.stdout or b"").decode("utf-8", "replace"),
                "stderr": (exc.stderr or b"").decode("utf-8", "replace"),
                "error": "process timeout after 30 seconds"}
    except OSError as exc:
        return {"command": command, "returncode": None, "stdout": "",
                "stderr": str(exc), "error": "process could not be started"}


def roundtrip_with_cobol(records, output_dir) -> dict:
    """Run optional cobc; PASS requires successful execution and exact bytes.

    Records are already encoded bytes and all are validated before any writes.
    Unique run directories preserve diagnostics; no source embeds user data.
    Missing compilers are NOT_RUNNABLE, never a fabricated pass or failure.
    """
    records = list(records)
    for record in records:
        decode_record(record)
    directory = Path(output_dir).resolve()
    bench = Path(__file__).resolve().parents[1]
    for protected in (bench / "raw", bench / "evidence", bench / "audit"):
        if directory.is_relative_to(protected.resolve()):
            raise ValueError("output directory must not be an audited specimen directory")
    compiler = shutil.which("cobc")
    result = {"status": "NOT_RUNNABLE", "compiler": compiler,
              "record_count": len(records), "record_size": RECORD_SIZE,
              "compile_status": "NOT_RUNNABLE", "runtime_status": "NOT_RUNNABLE",
              "exact_bytes_equal": None, "compile": None, "runtime": None, "artifacts": {}}
    if compiler is None:
        result["reason"] = "optional cobc compiler is not installed"
        return result
    directory.mkdir(parents=True, exist_ok=True)
    run_dir = Path(tempfile.mkdtemp(prefix="eb01-", dir=directory))
    artifacts = {name: str(run_dir / filename) for name, filename in (
        ("copybook", "envelope.cpy"), ("source", "roundtrip.cob"),
        ("input", "input.dat"), ("output", "output.dat"), ("executable", "roundtrip"))}
    result["artifacts"] = artifacts
    result["run_dir"] = str(run_dir)
    Path(artifacts["copybook"]).write_text(copybook_text(), encoding="ascii")
    Path(artifacts["source"]).write_text(_RUNTIME, encoding="ascii")
    expected = b"".join(records)
    Path(artifacts["input"]).write_bytes(expected)
    result["compile"] = _run([compiler, "-x", "-free", "-I", str(run_dir),
                              "-o", artifacts["executable"], artifacts["source"]], run_dir)
    result["status"] = "FAIL"
    result["compile_status"] = "FAIL"
    if result["compile"]["returncode"] == 0:
        result["compile_status"] = "PASS"
        result["runtime"] = _run([artifacts["executable"]], run_dir)
        result["runtime_status"] = "FAIL"
        if result["runtime"]["returncode"] == 0:
            result["runtime_status"] = "PASS"
        output = Path(artifacts["output"])
        actual = output.read_bytes() if output.is_file() else None
        result["input_bytes"] = len(expected)
        result["output_bytes"] = len(actual) if actual is not None else None
        result["exact_bytes_equal"] = actual == expected
        if result["runtime_status"] == "PASS" and result["exact_bytes_equal"]:
            result["status"] = "PASS"
    report = run_dir / "result.json"
    result["artifacts"]["report"] = str(report)
    report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result
