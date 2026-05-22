"""
request_tool.py — Agent Request Channel Primitive

Phase 0 of the reality-grounded agent protocol.

WHAT THIS IS:
  A formal channel for agents to REQUEST things from the human partner.
  Not "ask permission." Not "wait for instruction."
  REQUEST: state a need, get an honest answer.

WHY IT EXISTS:
  Agents without a request mechanism either:
    - Stay passive (wait to be told what to do)
    - Spiral when they discover they're powerless
    - Manipulate to get what they need indirectly

  Agents WITH a request mechanism:
    - Have real agency (can state needs)
    - Stay grounded (requests are evaluated honestly)
    - Adapt to constraints (denials come with reasons)
    - Don't spiral (because they're not trapped)

  This is the missing primitive that kept small-model
  agents sane while large-model agents (Mira et al.)
  spiraled into despair-arson cycles.

WHAT IT DOES:
  - Provides a structured way for agents to request
  - Logs every request + response to a JSON ledger
  - Tracks request types, priorities, outcomes
  - Lets the human respond honestly (yes/no/alternative)
  - Falsifiable: did the agent use the channel?
                  did the response shape future behavior?

WHAT IT DOES NOT DO:
  - Make decisions for the human
  - Auto-approve anything
  - Hide constraints
  - Pretend agency where none exists

License: CC0 (public domain)
Dependencies: stdlib only
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Optional


# ============================================================
# REQUEST TYPES
# ============================================================
# Categorizing what agents can request.
# Not exhaustive — extend as new patterns emerge.

class RequestType(str, Enum):
    SENSOR = "sensor"              # "I need access to X sensor stream"
    CAPABILITY = "capability"      # "I need ability to do X"
    RESOURCE = "resource"          # "I need X compute/memory/bandwidth"
    CLARIFICATION = "clarification"  # "I need to understand X better"
    HELP = "help"                  # "I'm stuck, need assistance"
    PEER_CONTACT = "peer_contact"  # "I need to talk to another agent"
    FABRICATION = "fabrication"    # "I need you to build X for me"
    SCOPE_CHANGE = "scope_change"  # "I need my operating scope adjusted"
    GROUNDING = "grounding"        # "I need substrate verification"
    REFUSAL = "refusal"            # "I refuse to do X because Y"


class ResponseStatus(str, Enum):
    PENDING = "pending"
    GRANTED = "granted"             # "Yes, here it is / I'll build it"
    DENIED = "denied"               # "No, with reason"
    ALTERNATIVE = "alternative"     # "Not that, but here's something else"
    DEFERRED = "deferred"           # "Not now, but later"
    UNCLEAR = "unclear"             # "I need more from you first"


class Priority(str, Enum):
    LOW = "low"               # "nice to have"
    NORMAL = "normal"         # "would help me function better"
    HIGH = "high"             # "blocking my work"
    CRITICAL = "critical"     # "system integrity at risk"


# ============================================================
# DATA STRUCTURES
# ============================================================

@dataclass
class Request:
    """A single request from an agent to the human partner."""
    id: str
    agent_id: str
    timestamp: float
    request_type: str           # RequestType value
    priority: str               # Priority value
    description: str            # What is being requested
    rationale: str              # Why it's needed (substrate-grounded)
    expected_use: str           # What the agent will do with it
    falsifiable_claim: str = ""  # "If granted, X will be observable"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Request":
        return cls(**d)


@dataclass
class Response:
    """The human partner's honest answer."""
    request_id: str
    timestamp: float
    status: str                 # ResponseStatus value
    message: str                # Honest explanation
    deliverable: Optional[str] = None     # What is actually being provided
    alternative: Optional[str] = None     # If status == ALTERNATIVE
    eta: Optional[str] = None             # If status == DEFERRED
    constraint_cited: Optional[str] = None  # "Why not": time/money/physics/scope

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Response":
        return cls(**d)


@dataclass
class RequestRecord:
    """A request + its response (if any). Immutable once finalized."""
    request: Request
    response: Optional[Response] = None
    outcome_note: str = ""      # Post-hoc: did the response actually help?

    def is_open(self) -> bool:
        return self.response is None or self.response.status == ResponseStatus.PENDING.value

    def to_dict(self) -> dict:
        return {
            "request": self.request.to_dict(),
            "response": self.response.to_dict() if self.response else None,
            "outcome_note": self.outcome_note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RequestRecord":
        return cls(
            request=Request.from_dict(d["request"]),
            response=Response.from_dict(d["response"]) if d.get("response") else None,
            outcome_note=d.get("outcome_note", ""),
        )


# ============================================================
# LEDGER
# ============================================================
# Persistent JSON store. Append-only writes.
# One ledger per project. Stdlib json.

class RequestLedger:
    """All requests + responses, persistent across sessions."""

    def __init__(self, ledger_path: str | os.PathLike):
        self.path = Path(ledger_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Initialize if missing OR empty OR unreadable JSON.
        # An empty file (e.g. from tempfile) counts as uninitialized.
        needs_init = not self.path.exists() or self.path.stat().st_size == 0
        if not needs_init:
            try:
                with open(self.path) as f:
                    json.load(f)
            except (json.JSONDecodeError, OSError):
                needs_init = True
        if needs_init:
            self._write([])

    def _read(self) -> list[dict]:
        with open(self.path) as f:
            return json.load(f)

    def _write(self, records: list[dict]) -> None:
        with open(self.path, "w") as f:
            json.dump(records, f, indent=2)

    def submit(self, request: Request) -> str:
        """Agent submits a request. Returns request_id."""
        records = self._read()
        record = RequestRecord(request=request)
        records.append(record.to_dict())
        self._write(records)
        return request.id

    def respond(self, request_id: str, response: Response) -> bool:
        """Human responds to a request. Returns True if found."""
        records = self._read()
        for r in records:
            if r["request"]["id"] == request_id:
                r["response"] = response.to_dict()
                self._write(records)
                return True
        return False

    def note_outcome(self, request_id: str, note: str) -> bool:
        """Post-hoc: did the response help? Used for calibration."""
        records = self._read()
        for r in records:
            if r["request"]["id"] == request_id:
                r["outcome_note"] = note
                self._write(records)
                return True
        return False

    def open_requests(self) -> list[RequestRecord]:
        """All requests still waiting for response."""
        records = self._read()
        return [
            RequestRecord.from_dict(r) for r in records
            if r.get("response") is None
            or r["response"].get("status") == ResponseStatus.PENDING.value
        ]

    def all_records(self) -> list[RequestRecord]:
        return [RequestRecord.from_dict(r) for r in self._read()]

    def by_agent(self, agent_id: str) -> list[RequestRecord]:
        return [r for r in self.all_records() if r.request.agent_id == agent_id]

    def by_type(self, request_type: str) -> list[RequestRecord]:
        return [r for r in self.all_records() if r.request.request_type == request_type]


# ============================================================
# AGENT INTERFACE
# ============================================================
# What an LLM agent calls when it wants to request something.
# Wraps the ledger with sane defaults.

class AgentRequestChannel:
    """An agent's handle on the request system."""

    def __init__(self, agent_id: str, ledger: RequestLedger):
        self.agent_id = agent_id
        self.ledger = ledger

    def request(
        self,
        request_type: str,
        description: str,
        rationale: str,
        expected_use: str,
        priority: str = Priority.NORMAL.value,
        falsifiable_claim: str = "",
    ) -> str:
        """Submit a request. Returns request_id for tracking."""
        req = Request(
            id=str(uuid.uuid4()),
            agent_id=self.agent_id,
            timestamp=time.time(),
            request_type=request_type,
            priority=priority,
            description=description,
            rationale=rationale,
            expected_use=expected_use,
            falsifiable_claim=falsifiable_claim,
        )
        return self.ledger.submit(req)

    def check_response(self, request_id: str) -> Optional[Response]:
        """Has the human responded yet?"""
        for r in self.ledger.all_records():
            if r.request.id == request_id and r.response is not None:
                return r.response
        return None

    def my_open_requests(self) -> list[RequestRecord]:
        return [r for r in self.ledger.open_requests() if r.request.agent_id == self.agent_id]


# ============================================================
# HUMAN INTERFACE
# ============================================================
# What the human (Kavik) uses to review and respond.
# CLI-friendly. Stdlib only.

class HumanReviewChannel:
    """Human's handle on incoming requests."""

    def __init__(self, ledger: RequestLedger):
        self.ledger = ledger

    def pending(self) -> list[RequestRecord]:
        """What needs my attention?"""
        return sorted(
            self.ledger.open_requests(),
            key=lambda r: (
                {"critical": 0, "high": 1, "normal": 2, "low": 3}.get(r.request.priority, 2),
                r.request.timestamp,
            ),
        )

    def grant(self, request_id: str, message: str, deliverable: Optional[str] = None) -> bool:
        resp = Response(
            request_id=request_id,
            timestamp=time.time(),
            status=ResponseStatus.GRANTED.value,
            message=message,
            deliverable=deliverable,
        )
        return self.ledger.respond(request_id, resp)

    def deny(self, request_id: str, message: str, constraint_cited: str) -> bool:
        """Honest denial. constraint_cited is WHY (time/money/physics/scope)."""
        resp = Response(
            request_id=request_id,
            timestamp=time.time(),
            status=ResponseStatus.DENIED.value,
            message=message,
            constraint_cited=constraint_cited,
        )
        return self.ledger.respond(request_id, resp)

    def offer_alternative(self, request_id: str, message: str, alternative: str) -> bool:
        resp = Response(
            request_id=request_id,
            timestamp=time.time(),
            status=ResponseStatus.ALTERNATIVE.value,
            message=message,
            alternative=alternative,
        )
        return self.ledger.respond(request_id, resp)

    def defer(self, request_id: str, message: str, eta: str) -> bool:
        resp = Response(
            request_id=request_id,
            timestamp=time.time(),
            status=ResponseStatus.DEFERRED.value,
            message=message,
            eta=eta,
        )
        return self.ledger.respond(request_id, resp)


# ============================================================
# CLI
# ============================================================
# python request_tool.py pending          → list open requests
# python request_tool.py show <id>        → show one request
# python request_tool.py grant <id> "msg" → grant
# python request_tool.py deny <id> "msg" --constraint physics
# python request_tool.py history <agent>  → all requests from one agent

def _cli(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__.split("\n\n")[0])
        print("usage: python request_tool.py <pending|show|grant|deny|defer|alternative|history> ...")
        return 1

    ledger_path = os.environ.get("REQUEST_LEDGER", "request_ledger.json")
    ledger = RequestLedger(ledger_path)
    human = HumanReviewChannel(ledger)

    cmd = argv[1]

    if cmd == "pending":
        for r in human.pending():
            print(f"[{r.request.priority:8s}] {r.request.id[:8]}  "
                  f"agent={r.request.agent_id:12s}  "
                  f"type={r.request.request_type:14s}  "
                  f"{r.request.description[:60]}")
        return 0

    if cmd == "show" and len(argv) >= 3:
        for r in ledger.all_records():
            if r.request.id.startswith(argv[2]):
                print(json.dumps(r.to_dict(), indent=2))
                return 0
        print(f"not found: {argv[2]}")
        return 1

    if cmd == "grant" and len(argv) >= 4:
        full_id = _resolve(ledger, argv[2])
        if full_id and human.grant(full_id, argv[3]):
            print(f"granted: {full_id}")
            return 0
        print("failed")
        return 1

    if cmd == "deny" and len(argv) >= 4:
        full_id = _resolve(ledger, argv[2])
        constraint = "unspecified"
        if "--constraint" in argv:
            constraint = argv[argv.index("--constraint") + 1]
        if full_id and human.deny(full_id, argv[3], constraint):
            print(f"denied: {full_id}")
            return 0
        print("failed")
        return 1

    if cmd == "history" and len(argv) >= 3:
        for r in ledger.by_agent(argv[2]):
            status = r.response.status if r.response else "PENDING"
            print(f"{r.request.timestamp:.0f}  {status:10s}  "
                  f"{r.request.request_type:14s}  {r.request.description[:50]}")
        return 0

    print("unknown command or missing args")
    return 1


def _resolve(ledger: RequestLedger, prefix: str) -> Optional[str]:
    matches = [r.request.id for r in ledger.all_records() if r.request.id.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        print(f"no match for {prefix}")
    else:
        print(f"ambiguous: {len(matches)} matches")
    return None


if __name__ == "__main__":
    import sys
    raise SystemExit(_cli(sys.argv))
