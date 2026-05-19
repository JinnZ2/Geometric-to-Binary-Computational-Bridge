"""
claim_back_fluidic_transient.py  (fabrication/)

Predicted transient claims from a fluidic IR. Reads R, L
(inertance), C (compliance) from the IR elements; decides regime
(RC first-order vs RLC second-order) from what's present.

License: CC0. Stdlib only.
"""
import math
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claims_fluidic_transient(ir, geometric_hash, tol_frac=0.15):
    R = next((e.parameter for e in ir.elements if e.kind == "dissipate"),    None)
    L = next((e.parameter for e in ir.elements if e.kind == "store_flow"),   None)
    C = next((e.parameter for e in ir.elements if e.kind == "store_effort"), None)

    base = f"fab::fluidic::{geometric_hash}"
    claims = []

    if R and C and not L:
        tau = R * C
        claims.append(_pack(
            scope=f"{base}::dyn",
            rate_var="tau_RC_s",
            value=tau, tol_frac=tol_frac,
            kind="first_order",
            measurement="step input; fit y = A(1 - e^{-t/τ}) + b",
            failure="extra compliance (soft tubing), parasitic resistance",
            provenance="claim_back_fluidic_transient.py",
            R=R, C=C,
        ))
    elif R and L and C:
        wn = 1.0 / math.sqrt(L * C)
        zeta = (R / 2.0) * math.sqrt(C / L)
        claims.append(_pack(
            scope=f"{base}::dyn",
            rate_var="omega_n_rad_s",
            value=wn, tol_frac=tol_frac,
            kind="second_order",
            measurement="step input; fit underdamped 2nd-order response",
            failure="see omega_n / damping_ratio failure modes",
            provenance="claim_back_fluidic_transient.py",
            R=R, L=L, C=C,
        ))
        claims.append(_pack(
            scope=f"{base}::dyn",
            rate_var="damping_ratio",
            value=zeta, tol_frac=0.20,
            kind="second_order",
            measurement="fit ζ from overshoot ratio",
            failure="laminar/turbulent regime shift; "
                    "minor losses unmodeled",
            provenance="claim_back_fluidic_transient.py",
        ))
    return claims


def _pack(**fields):
    fields["ts"] = time.time()
    fields["id"] = hashlib.sha256(
        json.dumps(fields, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return fields


def append_dyn_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    new_scopes_vars = {(c["scope"], c["rate_var"]) for c in claims}
    existing = [e for e in existing
                if (e.get("scope"), e.get("rate_var"))
                not in new_scopes_vars]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
