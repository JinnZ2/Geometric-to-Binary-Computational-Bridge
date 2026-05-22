"""Patch verification — runs all three patch tests in sequence."""
import json
import os
import sys
import tempfile

sys.path.insert(0, ".")
from request_tool import (
    RequestLedger, AgentRequestChannel, HumanReviewChannel,
    Request, RequestType, Priority, _cli,
)


def test_normalization():
    """Patch 2: LLM-style sloppy strings should be normalized."""
    ledger_path = tempfile.mktemp(suffix=".json")
    ledger = RequestLedger(ledger_path)
    agent = AgentRequestChannel("test", ledger)

    # Simulated LLM output with mixed case + whitespace
    rid = agent.request(
        request_type="  Sensor  ",   # sloppy
        description="x",
        rationale="y",
        expected_use="z",
        priority="HIGH\n",           # sloppy
    )

    record = ledger.all_records()[0]
    assert record.request.request_type == "sensor", f"got {record.request.request_type!r}"
    assert record.request.priority == "high", f"got {record.request.priority!r}"
    print("  PASS: normalization handles 'Sensor' and 'HIGH\\n'")

    # Unknown priority falls back to normal
    rid2 = agent.request(
        request_type="sensor",
        description="x", rationale="y", expected_use="z",
        priority="ULTRA_MEGA_URGENT",  # not in enum
    )
    r2 = ledger.all_records()[1]
    assert r2.request.priority == "normal", f"unknown priority not defaulted: {r2.request.priority!r}"
    print("  PASS: unknown priority defaults to 'normal'")

    os.unlink(ledger_path)


def test_cli_deny_arg_safety():
    """Patch 3: --constraint flag at any position should not shadow message."""
    ledger_path = tempfile.mktemp(suffix=".json")
    os.environ["REQUEST_LEDGER"] = ledger_path

    ledger = RequestLedger(ledger_path)
    agent = AgentRequestChannel("test", ledger)
    rid = agent.request(
        request_type="sensor", description="x", rationale="y", expected_use="z",
    )

    # Case A: --constraint at the end (normal)
    rc = _cli(["request_tool.py", "deny", rid[:8], "no budget right now", "--constraint", "money"])
    assert rc == 0
    record = ledger.all_records()[0]
    assert record.response.constraint_cited == "money"
    assert record.response.message == "no budget right now"
    print("  PASS: --constraint at end")

    # Case B: --constraint placed before message (must not steal message slot)
    ledger_path2 = tempfile.mktemp(suffix=".json")
    os.environ["REQUEST_LEDGER"] = ledger_path2
    ledger2 = RequestLedger(ledger_path2)
    agent2 = AgentRequestChannel("test", ledger2)
    rid2 = agent2.request(
        request_type="sensor", description="x", rationale="y", expected_use="z",
    )
    rc = _cli(["request_tool.py", "deny", rid2[:8], "--constraint", "physics", "out of spec"])
    assert rc == 0
    record2 = ledger2.all_records()[0]
    assert record2.response.constraint_cited == "physics", f"got {record2.response.constraint_cited!r}"
    assert record2.response.message == "out of spec", f"got {record2.response.message!r}"
    print("  PASS: --constraint before message")

    os.unlink(ledger_path)
    os.unlink(ledger_path2)


def test_atomic_write_no_corruption_on_kill():
    """Patch 1: simulate writes happening; verify ledger is always valid JSON."""
    # Direct test: write 100 records, then verify file is parseable JSON
    # (Hard to simulate kill mid-write in a unit test; we verify the
    #  atomic-replace path produces a valid file and that the temp file
    #  is gone after.)
    ledger_path = tempfile.mktemp(suffix=".json")
    ledger = RequestLedger(ledger_path)
    agent = AgentRequestChannel("test", ledger)

    for i in range(100):
        agent.request(
            request_type="sensor",
            description=f"req {i}",
            rationale="testing atomic writes",
            expected_use="stress test",
        )

    # File must be valid JSON
    with open(ledger_path) as f:
        data = json.load(f)
    assert len(data) == 100, f"got {len(data)} records"

    # No leftover .tmp files in the directory
    leftovers = [f for f in os.listdir(os.path.dirname(ledger_path) or ".") if f.endswith(".tmp")]
    assert not leftovers, f"leftover temp files: {leftovers}"
    print("  PASS: 100 atomic writes, valid JSON, no leftover .tmp")

    os.unlink(ledger_path)


if __name__ == "__main__":
    print("Patch 1 — atomic write:")
    test_atomic_write_no_corruption_on_kill()
    print()
    print("Patch 2 — LLM string normalization:")
    test_normalization()
    print()
    print("Patch 3 — CLI deny arg safety:")
    test_cli_deny_arg_safety()
    print()
    print("All patches verified.")
