"""
claim_back_coupler.py  (fabrication/)

Emit a cross-substrate claim:
  "Acoustic and electrical f₀ measurements of the SAME cavity,
   through a piezo coupler, must agree within X%."
X comes from the coupler's expected_agreement_pct.

License: CC0. Stdlib only.
"""
import json
import time
import hashlib
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_piezo_coupler(coupler):
    scope = f"fab::coupler::piezo::{coupler['name']}"
    payload = {
        "scope":         scope,
        "rate_var":      "f0_agreement_pct",
        "kind":          "cross_substrate",
        "value":         coupler["expected_agreement_pct"],
        "tol_frac":      0.05,
        "regime":        coupler["regime"],
        "k_eff_squared": coupler["k_eff_squared"],
        "linked_scopes": {
            "acoustic":   coupler["acoustic_scope"],
            "electrical": coupler["electrical_scope"],
        },
        "measurement": ("run verify_sweep (acoustic side) and "
                        "verify_electrical_csv (electrical side) on the "
                        "SAME physical cavity; agreement = "
                        "1 - 2|f_A - f_E|/(f_A + f_E); for strong "
                        "coupling, expect TWO peaks per side "
                        "(series + parallel)"),
        "failure":     ("- disagreement > tol -> coupler model wrong "
                        "(η, k_eff², or split prediction)\n"
                        "- one path passes, other fails -> that path "
                        "has a leak\n"
                        "- both paths drift in same direction -> "
                        "cavity geometry is off from spec"),
        "provenance":  "claim_back_coupler.py",
        "ts":          time.time(),
    }
    payload["id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return payload


def append_coupler_claim(claim, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [c for c in existing if c["scope"] != claim["scope"]]
    existing.append(claim)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return claim["id"]
