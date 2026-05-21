"""
claim_back_thermal.py  (fabrication/)

Thermal IR -> claims. Two flavors:

  (a) Dynamic: τ = R_total · C_total -- first-order time constant
      for a step heat input. Falsifiable by step-heating a known
      resistive heater and logging temperature vs time.

  (b) Steady: ΔT_ss = q̇ · R_total -- equilibrium temperature
      rise when heat_source_W is known. Falsifiable by powering
      the heater for ≥5τ and measuring final ΔT.

Same ledger and verdict semantics as the rest of the fabrication
audit: nothing thermal-specific from the auditor's point of view.

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claims_thermal(ir, geometric_hash,
                        heat_source_W=None, tol_frac=0.15):
    R_total = sum(e.parameter for e in ir.elements if e.kind == "dissipate")
    C_total = sum(e.parameter for e in ir.elements if e.kind == "store_effort")
    base = f"fab::thermal::{geometric_hash}"
    claims = []
    if R_total > 0 and C_total > 0:
        tau = R_total * C_total
        claims.append(_pack(
            scope=f"{base}::dyn", rate_var="tau_thermal_s",
            kind="first_order", value=tau, tol_frac=tol_frac,
            measurement=("step heat input (resistor turned on); log "
                         "temperature vs t; fit first-order rise"),
            failure=("• unaccounted radiation path at high ΔT\n"
                     "• thermal interface resistance (paste, air gap)\n"
                     "• convection coefficient varies with orientation"),
            provenance="claim_back_thermal.py",
            R_th=R_total, C_th=C_total,
        ))
    if heat_source_W is not None and R_total > 0:
        delta_T_ss = heat_source_W * R_total
        claims.append(_pack(
            scope=f"{base}::steady", rate_var="delta_T_steady_K",
            kind="steady", value=delta_T_ss, tol_frac=tol_frac,
            measurement=("apply known power for ≥5τ; record ΔT_ss; "
                         "compare to q̇·R prediction"),
            failure=("• actual power lower (resistor tolerance, V drop)\n"
                     "• parallel loss path (cable conduction, radiation)\n"
                     "• ambient drift during long-duration test"),
            provenance="claim_back_thermal.py",
            heat_source_W=heat_source_W,
        ))
    return claims


def _pack(**f):
    f["ts"] = time.time()
    f["id"] = hashlib.sha256(
        json.dumps(f, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f


def append_thermal_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    keys = {(c["scope"], c["rate_var"]) for c in claims}
    existing = [e for e in existing
                if (e.get("scope"), e.get("rate_var")) not in keys]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
