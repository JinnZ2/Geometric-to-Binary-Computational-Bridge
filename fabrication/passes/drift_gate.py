"""
drift_gate.py  (fabrication/passes/)

Three-color drift gate over CLAIM_TABLE.fab.json.

Each claim carries:
  threshold_green  delta below this -> GREEN
  threshold_yellow between green and yellow -> YELLOW (drift)
  above yellow                            -> RED  (model invalid
                                                   for this regime)

Pattern ported from `earth-systems-physics/assumption_validator`.

License: CC0. Stdlib only.
"""
import json
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def evaluate_drift(claim, measurement):
    """Return 'GREEN' | 'YELLOW' | 'RED' for one (claim, measurement)
    pair. Measurement may be a single scalar (compared to claim['value'])
    or a dict carrying a 'measured_value' / 'measured' key.
    """
    predicted = (claim.get("predicted_value")
                 if "predicted_value" in claim
                 else claim.get("value", 0.0))
    if isinstance(measurement, dict):
        measured = (measurement.get("measured_value")
                    or measurement.get("measured")
                    or 0.0)
    else:
        measured = measurement
    if predicted == 0:
        delta = abs(measured)
    else:
        delta = abs(measured - predicted) / abs(predicted)
    g = claim.get("threshold_green",  0.05)
    y = claim.get("threshold_yellow", 0.20)
    if delta <= g:
        return "GREEN"
    if delta <= y:
        return "YELLOW"
    return "RED"


def update_claim_status(claim_id, status, ledger_path=None):
    """Write back the drift status to the claim with this id."""
    path = Path(ledger_path) if ledger_path else LEDGER
    existing = json.loads(path.read_text()) if path.exists() else []
    for c in existing:
        if c.get("id") == claim_id:
            c["status"] = status
            c["last_evaluated"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                time.gmtime())
            break
    path.write_text(json.dumps(existing, indent=2, default=str))


def seed_leak_claim(claim, ledger_path=None):
    """Insert a 'leak as claim' record into the ledger.

    Pattern: every structural fix opens with a RED claim that flips
    GREEN only when the corresponding test passes. This converts the
    fix-plan checklist into a falsifiable audit trail.
    """
    path = Path(ledger_path) if ledger_path else LEDGER
    existing = json.loads(path.read_text()) if path.exists() else []
    # de-dupe by id
    existing = [c for c in existing if c.get("id") != claim["id"]]
    claim.setdefault("status", "RED")
    claim.setdefault("kind", "leak")
    claim.setdefault("ts", time.time())
    existing.append(claim)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return claim["id"]
