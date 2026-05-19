"""
coating_detector.py  (fabrication/voice/)

Flags responses that look self-reinforcing -- a signature of the
framework smoothing over missing physics rather than measuring
real-world disagreement.

Signals:
  - too-clean pass rate (N >= threshold, zero fail, zero drift)
  - measurement/claim ratio too high (echo / re-run loop)
  - one verifier dominates results (narrow base)

The output is a warning surface for the optics translator.

License: CC0. Stdlib only.
"""
import json
from pathlib import Path


MEASUREMENTS = Path("CLAIM_TABLE.fab.measurements.json")
LEDGER       = Path("CLAIM_TABLE.fab.json")


def detect(threshold_n=10, threshold_ratio=5.0):
    ms = (json.loads(MEASUREMENTS.read_text())
          if MEASUREMENTS.exists() else [])
    cs = (json.loads(LEDGER.read_text())
          if LEDGER.exists() else [])

    verdicts = {}
    for m in ms:
        v = m.get("verdict") or m.get("overall") or "?"
        verdicts[v] = verdicts.get(v, 0) + 1

    n_pass  = verdicts.get("pass",  0)
    n_drift = verdicts.get("drift", 0)
    n_fail  = verdicts.get("fail",  0)
    n_total = n_pass + n_drift + n_fail
    n_claims = len(cs)

    reasons = []
    if n_total >= threshold_n and n_fail == 0 and n_drift == 0:
        reasons.append(f"all {n_total} measurements PASS, none "
                       "drift or fail -- too clean for real fab")
    if n_claims > 0 and n_total / max(1, n_claims) > threshold_ratio:
        ratio = n_total / n_claims
        reasons.append(f"measurement/claim ratio = {ratio:.2f} -- "
                       "far more verdicts than claims; "
                       "possible echo / re-run loop")
    methods = {}
    for m in ms:
        meth = m.get("method", "?")
        methods[meth] = methods.get(meth, 0) + 1
    if methods:
        top = max(methods.values())
        if top / max(1, n_total) > 0.8 and n_total > 5:
            top_name = max(methods, key=methods.get)
            reasons.append(f"{top}/{n_total} measurements come from "
                           f"one verifier ({top_name}) -- narrow base")

    return {
        "coating_suspected": bool(reasons),
        "reasons": reasons,
        "stats": {
            "n_pass":              n_pass,
            "n_drift":             n_drift,
            "n_fail":              n_fail,
            "n_total_measurements": n_total,
            "n_claims":             n_claims,
            "methods":              methods,
        },
    }
