"""Reversible finite JSON transport, not decimal metrology or an immutable ledger.

SHA-256 detects change relative to the envelope; it does NOT authenticate its
sender or certify truth. A sender can alter a payload and recompute its hash.
Canonical spelling is Python JSON with ASCII escapes, sorted keys and compact
separators. Floats retain Python's JSON representation, not exact decimals.
"""

import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

VERSION = "experiment-bridge/v1.1"
MAGIC = b"EB01"
JSON_CAPACITY = 16384
HEADER_SIZE = 76
RECORD_SIZE = HEADER_SIZE + JSON_CAPACITY
MAX_JSON_DEPTH = 64  # Container depth; the root object is depth 1.
MAX_JSON_NODES = 16384  # Values and object keys, including repeated shared values.
MAX_JSON_STRING_LENGTH = JSON_CAPACITY  # Code points; ASCII escaped size also checked.
MAX_INTEGER_DIGITS = JSON_CAPACITY
MAX_RECORDS = 64  # At most 1,053,440 encoded input bytes per compiler run.
PROCESS_TIMEOUT_SECONDS = 30
_INTEGER_BOUND = 10 ** MAX_INTEGER_DIGITS
PROTECTED_OUTPUT_PATHS = ("raw", "evidence", "audit", "v1", "v1_1/runs", "adversarial")


def _validate(value, active=None):
    """Bound work and exact canonical byte size before assembling JSON text."""
    active = set() if active is None else active
    nodes, size = 0, 0

    def consume(amount):
        nonlocal size
        size += amount
        if size > JSON_CAPACITY:
            raise ValueError("JSON payload exceeds 16384 ASCII bytes")

    def visit(item, parent_depth):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_JSON_NODES:
            raise ValueError(f"JSON node count exceeds {MAX_JSON_NODES}")
        kind = type(item)
        if kind is str:
            if len(item) > MAX_JSON_STRING_LENGTH:
                raise ValueError(f"JSON string length exceeds {MAX_JSON_STRING_LENGTH}")
            consume(2)
            for char in item:
                code = ord(char)
                consume(2 if char in '\\"\b\f\n\r\t' else
                        6 if code < 32 or 127 <= code <= 65535 else
                        12 if code > 65535 else 1)
        elif kind is int:
            # Compare before abs(), divmod(), or decimal chunk construction.
            if not -_INTEGER_BOUND < item < _INTEGER_BOUND:
                raise ValueError(f"JSON integer exceeds {MAX_INTEGER_DIGITS} digits")
            consume(len(_integer_text(item)))
        elif item is None or kind is bool:
            consume(4 if item is None or item is True else 5)
        elif kind is float:
            if not math.isfinite(item):
                raise ValueError("JSON floats must be finite")
            consume(len(json.dumps(item, allow_nan=False)))
        elif kind in (dict, list):
            depth = parent_depth + 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError(f"JSON nesting depth exceeds {MAX_JSON_DEPTH}")
            if id(item) in active:
                raise ValueError("cyclic JSON payload")
            if len(item) > MAX_JSON_NODES - nodes:
                raise ValueError(f"JSON node count exceeds {MAX_JSON_NODES}")
            consume(2 + max(0, len(item) - 1) + (len(item) if kind is dict else 0))
            active.add(id(item))
            try:
                if kind is dict:
                    for key, child in item.items():
                        if type(key) is not str:
                            raise TypeError("JSON object keys must be strings")
                        visit(key, depth)
                        visit(child, depth)
                else:
                    for child in item:
                        visit(child, depth)
            finally:
                active.remove(id(item))
        else:
            raise TypeError("payload contains an unsupported JSON type")

    visit(value, 0)


def _check_json_depth(data):
    """Bound nesting before Python's recursive parser; ignore quoted brackets."""
    depth, quoted, escaped = 0, False, False
    for byte in data:
        if quoted:
            if escaped:
                escaped = False
            elif byte == 92:
                escaped = True
            elif byte == 34:
                quoted = False
        elif byte == 34:
            quoted = True
        elif byte in (91, 123):
            depth += 1
            if depth > MAX_JSON_DEPTH:
                raise ValueError(f"JSON nesting depth exceeds {MAX_JSON_DEPTH}")
        elif byte in (93, 125):
            depth -= 1


def checked_output_dir(output_dir, bench=None):
    """Reject lexical and resolved held paths. This is NOT a TOCTOU sandbox.

    Callers must trust the local filesystem not to replace directories/symlinks
    during a run. Exclusive new files/directories prevent accidental overwrite,
    but do not isolate an adversarial local process or compiler.
    """
    bench = Path(__file__).resolve().parents[1] if bench is None else Path(bench)
    lexical = Path(os.path.abspath(output_dir))
    directory = lexical.resolve()
    for name in PROTECTED_OUTPUT_PATHS:
        held = Path(os.path.abspath(bench / name))
        if lexical.is_relative_to(held) or directory.is_relative_to(held.resolve()):
            raise ValueError("output directory must not be inside preserved specimen, legacy, or archived evidence paths")
    return directory


def write_text_exclusive(path, text, encoding="utf-8"):
    """Publish a complete, closed text file without replacing an existing leaf.

    Temporary files and same-filesystem exclusive hard links keep final reports
    absent on write/close failure. This is not crash durability or path isolation.
    """
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding=encoding, dir=path.parent,
                                         prefix=f".{path.name}-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.link(temporary, path)  # Fails rather than overwrites a file or symlink.
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass  # A leftover temporary is not a false final success report.


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
    try:
        _validate(payload)
        data = _json_text(payload).encode("ascii")
    except RecursionError as exc:
        raise ValueError(f"JSON recursion limit reached (maximum depth {MAX_JSON_DEPTH})") from exc
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
    _check_json_depth(data)
    try:
        payload = json.loads(data, object_pairs_hook=_object, parse_constant=_constant,
                             parse_int=_parse_integer)
    except RecursionError as exc:
        raise ValueError(f"JSON recursion limit reached (maximum depth {MAX_JSON_DEPTH})") from exc
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
                                 text=True, errors="replace", timeout=PROCESS_TIMEOUT_SECONDS, check=False)
        return {"command": command, "returncode": process.returncode,
                "stdout": process.stdout, "stderr": process.stderr}
    except subprocess.TimeoutExpired as exc:
        def text(value):
            return value.decode("utf-8", "replace") if isinstance(value, bytes) else value or ""
        return {"command": command, "returncode": None,
                "stdout": text(exc.stdout), "stderr": text(exc.stderr),
                "error": f"process timeout after {PROCESS_TIMEOUT_SECONDS} seconds"}
    except OSError as exc:
        return {"command": command, "returncode": None, "stdout": "",
                "stderr": str(exc), "error": "process could not be started"}


def roundtrip_with_cobol(records, output_dir) -> dict:
    """Run optional cobc; PASS requires successful execution and exact bytes.

    Records are already encoded bytes and all are validated before any writes.
    Unique run directories preserve diagnostics; no source embeds user data.
    Missing compilers are NOT_RUNNABLE, never a fabricated pass or failure.
    At most MAX_RECORDS are accepted; one extra item is consumed to detect excess.
    The iterable itself and local filesystem/compiler must be trusted to return.
    """
    directory = checked_output_dir(output_dir)
    bounded = []
    for record in records:
        if len(bounded) >= MAX_RECORDS:
            raise ValueError(f"record count exceeds {MAX_RECORDS}")
        decode_record(record)
        bounded.append(record)
    records = bounded
    compiler = shutil.which("cobc")
    result = {"status": "NOT_RUNNABLE", "compiler": compiler,
              "record_count": len(records), "record_size": RECORD_SIZE,
              "compile_status": "NOT_RUNNABLE", "runtime_status": "NOT_RUNNABLE",
              "exact_bytes_equal": None, "compile": None, "runtime": None, "artifacts": {}}
    if compiler is None:
        result["reason"] = "optional cobc compiler is not installed"
        return result
    expected = b"".join(records)
    result["status"] = "FAIL"
    run_dir = None
    stage = "prepare artifacts"
    try:
        directory.mkdir(parents=True, exist_ok=True)
        directory = checked_output_dir(directory)
        run_dir = Path(tempfile.mkdtemp(prefix="eb01-", dir=directory))
        checked_output_dir(run_dir)
        artifacts = {name: str(run_dir / filename) for name, filename in (
            ("copybook", "envelope.cpy"), ("source", "roundtrip.cob"),
            ("input", "input.dat"), ("output", "output.dat"), ("executable", "roundtrip"))}
        result["artifacts"] = artifacts
        result["run_dir"] = str(run_dir)
        for name, text in (("copybook", copybook_text()), ("source", _RUNTIME)):
            with Path(artifacts[name]).open("x", encoding="ascii") as handle:
                handle.write(text)
        with Path(artifacts["input"]).open("xb") as handle:
            handle.write(expected)
        stage = "compile"
        result["compile_status"] = "FAIL"
        result["compile"] = _run([compiler, "-x", "-free", "-I", str(run_dir),
                                  "-o", artifacts["executable"], artifacts["source"]], run_dir)
        if result["compile"]["returncode"] == 0:
            result["compile_status"] = "PASS"
            stage = "runtime"
            result["runtime_status"] = "FAIL"
            result["runtime"] = _run([artifacts["executable"]], run_dir)
            if result["runtime"]["returncode"] == 0:
                result["runtime_status"] = "PASS"
            stage = "read output"
            output = Path(artifacts["output"])
            actual = None
            if output.is_file():
                with output.open("rb") as handle:
                    actual = handle.read(len(expected) + 1)
            result["input_bytes"] = len(expected)
            result["output_bytes"] = output.stat().st_size if actual is not None else None
            result["exact_bytes_equal"] = actual == expected
            if result["runtime_status"] == "PASS" and result["exact_bytes_equal"]:
                result["status"] = "PASS"
    except OSError as exc:
        result["status"] = "FAIL"
        result["error"] = f"{stage}: {exc}"
    if run_dir is None:
        return result
    report = run_dir / "result.json"
    result["artifacts"]["report"] = str(report)
    try:
        checked_output_dir(run_dir)
        write_text_exclusive(report, json.dumps(result, indent=2) + "\n")
    except OSError as exc:
        result["status"] = "FAIL"
        result["report_error"] = str(exc)
        result["artifacts"].pop("report", None)
    return result
