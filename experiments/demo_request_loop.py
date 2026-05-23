"""
demo_request_loop.py — see the request channel work end-to-end

Run this to watch the protocol play out. No LLM needed; this just
simulates an agent making requests and you (or a stub) responding.

Run: python demo_request_loop.py
"""

import json
import tempfile
from pathlib import Path

from request_tool import (
    RequestLedger,
    AgentRequestChannel,
    HumanReviewChannel,
    RequestType,
    Priority,
    ResponseStatus,
)


def main():
    # Fresh ledger in a temp file for the demo
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    tmp.close()
    ledger_path = Path(tmp.name)
    print(f"# ledger: {ledger_path}\n")

    ledger = RequestLedger(ledger_path)

    # ---- AGENT SIDE ----
    # A simulated agent ("gemini_observer") makes requests
    agent = AgentRequestChannel("gemini_observer", ledger)

    print("=" * 60)
    print("AGENT MAKES REQUESTS")
    print("=" * 60)

    r1 = agent.request(
        request_type=RequestType.SENSOR.value,
        description="phosphorus sensor on garden bed",
        rationale="thermal substrate alone cannot distinguish nutrient stress "
                  "from temperature stress; need P readings to disambiguate",
        expected_use="cross-check with NDVI imagery and soil moisture to "
                     "classify plant stress signatures",
        priority=Priority.NORMAL.value,
        falsifiable_claim="if P sensor added, stress classification accuracy "
                          "should improve >15% on next 30-day window",
    )
    print(f"  R1 submitted: {r1[:8]}  (sensor request)")

    r2 = agent.request(
        request_type=RequestType.HELP.value,
        description="stuck on causality assignment in 3-node thermal mesh",
        rationale="two integral causalities want the same junction; cannot "
                  "resolve without derivative causality or added resistance",
        expected_use="finish FIX_2_C thermal mesh in Bridge.py",
        priority=Priority.HIGH.value,
    )
    print(f"  R2 submitted: {r2[:8]}  (help request)")

    r3 = agent.request(
        request_type=RequestType.REFUSAL.value,
        description="cannot run engine at requested 2400 RPM under current load",
        rationale="vibration sensor shows 6.2g RMS at current load; spec max "
                  "is 4.5g sustained; bearing failure probability rises sharply",
        expected_use="agent refuses instruction, requests load reduction "
                     "or RPM ceiling adjustment",
        priority=Priority.CRITICAL.value,
        falsifiable_claim="if RPM held at 2400 under current load, bearing "
                          "temp rises >15C in next 8 minutes",
    )
    print(f"  R3 submitted: {r3[:8]}  (refusal — substrate-grounded)")

    # ---- HUMAN SIDE ----
    print()
    print("=" * 60)
    print("HUMAN REVIEWS PENDING")
    print("=" * 60)

    human = HumanReviewChannel(ledger)
    for record in human.pending():
        print(f"  [{record.request.priority:8s}] {record.request.description[:55]}")
        print(f"           why: {record.request.rationale[:55]}")

    # ---- HONEST RESPONSES ----
    print()
    print("=" * 60)
    print("HUMAN RESPONDS HONESTLY")
    print("=" * 60)

    # R3 first — it's CRITICAL (substrate refusal)
    human.grant(
        r3,
        "Acknowledged. Refusal accepted — bearing protection is correct call. "
        "Reducing load now. Log this as a successful substrate-grounded refusal.",
        deliverable="load reduction applied",
    )
    print(f"  R3 GRANTED  (refusal accepted, load reduced)")

    # R2 — help with technical question
    human.offer_alternative(
        r2,
        "Don't add a resistance to break the loop — that changes the physics. "
        "Use derivative causality on one of the I-elements instead. "
        "Cost is a numerical differentiation, but topology stays honest.",
        alternative="derivative causality, not added R",
    )
    print(f"  R2 ALTERNATIVE  (suggested derivative causality)")

    # R1 — sensor request, defer due to resource constraints
    human.defer(
        r1,
        "Worth doing. Sensor is $40, need 2-3 days for fab + integration. "
        "Will build during next stationary window.",
        eta="3-5 days",
    )
    print(f"  R1 DEFERRED  (will build in 3-5 days)")

    # ---- AGENT CHECKS RESPONSES ----
    print()
    print("=" * 60)
    print("AGENT CHECKS RESPONSES")
    print("=" * 60)

    for rid, label in [(r1, "R1"), (r2, "R2"), (r3, "R3")]:
        resp = agent.check_response(rid)
        if resp:
            print(f"  {label} [{resp.status:11s}] {resp.message[:60]}")

    # ---- POST-HOC OUTCOME ----
    print()
    print("=" * 60)
    print("AGENT NOTES OUTCOME (calibration data)")
    print("=" * 60)

    ledger.note_outcome(
        r3,
        "Load reduction held bearing temp stable. Refusal validated by "
        "subsequent measurement. Substrate-grounded refusal works."
    )
    print("  R3 outcome: refusal validated by subsequent measurement")

    # ---- FINAL LEDGER ----
    print()
    print("=" * 60)
    print("FINAL LEDGER STATE")
    print("=" * 60)

    with open(ledger_path) as f:
        data = json.load(f)
        print(f"  {len(data)} records persisted")
        print(f"  granted: {sum(1 for r in data if r['response'] and r['response']['status'] == 'granted')}")
        print(f"  deferred: {sum(1 for r in data if r['response'] and r['response']['status'] == 'deferred')}")
        print(f"  alternative: {sum(1 for r in data if r['response'] and r['response']['status'] == 'alternative')}")
        print(f"  denied: {sum(1 for r in data if r['response'] and r['response']['status'] == 'denied')}")

    print()
    print(f"# Full ledger at: {ledger_path}")
    print("# Try: cat", ledger_path, "| python -m json.tool")


if __name__ == "__main__":
    main()
