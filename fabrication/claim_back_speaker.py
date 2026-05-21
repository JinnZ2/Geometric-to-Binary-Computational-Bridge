"""
claim_back_speaker.py  (fabrication/)

Emit a three-substrate cross-claim:
  "Acoustic, electrical, and mechanical f₀ measurements of the SAME
   driver, through the speaker BL/Sd gyrator chain, must each agree
   pairwise within X%."
X comes from coupler['expected_agreement_pct'].

With two paths only, every disagreement is ambiguous -- could be
either side. Three paths triangulate: whichever two agree tells us
which substrate's model is at fault.

License: CC0. Stdlib only.
"""
import json
import time
import hashlib
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_speaker(coupler):
    scope = f"fab::coupler::speaker::{coupler['name']}"
    payload = {
        "scope":         scope,
        "rate_var":      "f0_agreement_pct",
        "kind":          "cross_substrate_triple",
        "value":         coupler["expected_agreement_pct"],
        "tol_frac":      0.05,
        "coupling_quality": coupler["coupling_quality"],
        "f_s_Hz":        coupler["f_s_Hz"],
        "Q_total":       coupler["Q_total"],
        "linked_scopes": {
            "acoustic":   coupler["acoustic_scope"],
            "electrical": coupler["electrical_scope"],
            "mechanical": coupler["mechanical_scope"],
        },
        "measurement": ("run verify_sweep (acoustic), "
                        "verify_electrical_csv (electrical), and "
                        "verify_mechanical (mechanical) on the SAME "
                        "driver; pairwise agreement = "
                        "1 - 2|f_i - f_j|/(f_i + f_j); all three "
                        "pairs must clear the budget"),
        "failure":     ("- A=E≠M -> mechanical clamp wrong / "
                        "effective Mms off (added mass from clamp)\n"
                        "- A=M≠E -> Le or stray cap shifting Z peak\n"
                        "- E=M≠A -> radiation/cabinet/mic baseline "
                        "issue (room mode, port loading)\n"
                        "- none agree -> BL or Sd model wrong "
                        "(coupling matrix itself)"),
        "provenance":  "claim_back_speaker.py",
        "ts":          time.time(),
    }
    payload["id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return payload


def append_speaker_claim(claim, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [c for c in existing if c["scope"] != claim["scope"]]
    existing.append(claim)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return claim["id"]
