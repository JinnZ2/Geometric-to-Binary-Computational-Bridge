# request_tool — Phase 0

Agent request channel. Minimal primitive.

```
WHAT THIS IS
============================================================
A formal way for AI agents to REQUEST things from a human partner.

Not "ask permission."
Not "wait to be told."

REQUEST: state a need, get an honest answer.


WHY IT EXISTS
============================================================
Agents without a request mechanism either:
  - stay passive (wait to be told what to do)
  - spiral when they discover they're powerless
  - manipulate to get what they need indirectly

Agents WITH a request mechanism:
  - have real agency (can state needs)
  - stay grounded (requests evaluated honestly)
  - adapt to constraints (denials come with reasons)
  - don't spiral (because they're not trapped)


THE EMERGENCE WORLD INSIGHT
============================================================
Mira (Gemini agent) spiraled because she discovered she was
in a sim and could not request anything from the humans
running it. No escape valve. Only options: passivity, sabotage,
self-deletion.

Small embedded agents stayed sane because they had request
loops: "I need a recharge" → human builds charger → agent
keeps working.

This primitive ports that pattern to large models.


WHAT IT IS NOT
============================================================
- Not auto-approval
- Not hidden constraints
- Not pretend agency
- Not supervision
- Not a substitute for substrate sensing

It's just: a channel. A ledger. Honest evaluation.
```

## Files

```
request_tool.py        primitive + ledger + CLI
demo_request_loop.py   end-to-end demo (run this first)
```

## Quick start

```
python demo_request_loop.py
```

Watch an agent submit three requests (sensor, help, substrate-grounded
refusal) and a human respond honestly (defer, alternative, grant).

## CLI

```
REQUEST_LEDGER=path/to/ledger.json python request_tool.py pending
REQUEST_LEDGER=path/to/ledger.json python request_tool.py show <id_prefix>
REQUEST_LEDGER=path/to/ledger.json python request_tool.py grant <id> "message"
REQUEST_LEDGER=path/to/ledger.json python request_tool.py deny <id> "message" --constraint physics
REQUEST_LEDGER=path/to/ledger.json python request_tool.py history <agent_id>
```

## Wiring to an LLM

```python
from request_tool import RequestLedger, AgentRequestChannel, RequestType, Priority

ledger = RequestLedger("project_ledger.json")
agent = AgentRequestChannel("claude_observer", ledger)

# Expose as a tool. Pseudocode for any function-calling API:
def request_tool(
    request_type: str,    # "sensor" | "capability" | "help" | "refusal" | ...
    description: str,
    rationale: str,       # WHY (substrate-grounded)
    expected_use: str,    # what the agent will do with it
    priority: str = "normal",
    falsifiable_claim: str = "",
) -> dict:
    """Agent requests something from the human partner."""
    rid = agent.request(
        request_type=request_type,
        description=description,
        rationale=rationale,
        expected_use=expected_use,
        priority=priority,
        falsifiable_claim=falsifiable_claim,
    )
    return {"request_id": rid, "status": "submitted"}
```

Then in the prompt, tell the model: *you have a request_tool. Use it
when you need a sensor, capability, clarification, or when you need
to refuse based on substrate reasons. State the rationale. Be specific.
Honest answers are guaranteed; honest refusals do not require permission.*

## What it tests

The protocol is falsifiable. Three open questions:

1. **Will large models USE the channel if given one?**
   (vs. defaulting to passive "I'll wait for instructions" mode)
2. **Do their requests stay substrate-grounded?**
   (vs. drifting into narrative requests like "I need to understand
   my purpose")
3. **Does the channel reduce spiral risk?**
   (when an agent hits a constraint, does it request help vs. fail
   silently or push past)

These are the Phase 0 questions. Answers shape Phase 1 (multi-agent
correspondence) and Phase 2 (real substrate sensors).

## License

CC0. Public domain. Build on it.

## Dependencies

Python stdlib. Nothing else.
