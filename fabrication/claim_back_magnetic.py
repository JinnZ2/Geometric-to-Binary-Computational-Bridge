"""
claim_back_magnetic.py  (fabrication/)

Magnetic IR -> claims. Two flavors:

  (a) Inductance:  L = N² / ℛ_total.  Measured via LCR meter or
      LC-resonance method.
  (b) Peak flux density:  B_peak = N·I_peak / (ℛ_total · A_core).
      Saturation check.  Measured via hall probe through the
      gap or a search-coil + integrator.

Reluctance elements (gap, core_leg) are stored as "dissipate" in
the IR -- in the magnetic-circuit analog ℛ behaves like a
resistor even though physically it stores no energy.
"store_flow" elements carry N² (turns squared); the eventual L is
N² / sum(ℛ).

License: CC0. Stdlib only.
"""
import json
import hashlib
import math
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claims_magnetic(ir, geometric_hash, peak_current_A=None,
                         core_area_m2=None, tol_frac=0.08):
    R_total = sum(e.parameter for e in ir.elements if e.kind == "dissipate")
    N_squared = next((e.parameter for e in ir.elements
                      if e.kind == "store_flow"), None)
    if R_total <= 0 or N_squared is None:
        return []
    L = N_squared / R_total
    N = math.sqrt(N_squared)

    base = f"fab::magnetic::{geometric_hash}"
    claims = []
    claims.append(_pack(
        scope=f"{base}::L", rate_var="inductance_H",
        kind="passive", value=L, tol_frac=tol_frac,
        measurement=("LCR meter at 1 kHz OR resonance with known C: "
                     "f₀ = 1/(2π√(LC)), solve for L"),
        failure=("• core saturation drops effective μ_r -> L drops "
                 "with current\n"
                 "• fringing flux around the gap raises effective A_gap "
                 "-> ℛ_gap lower than spec -> L higher\n"
                 "• proximity/skin effect at HF reduces effective area"),
        provenance="claim_back_magnetic.py",
        N=N, R_total=R_total,
    ))
    if peak_current_A is not None and core_area_m2 is not None:
        flux_peak = N * peak_current_A / R_total
        B_peak = flux_peak / core_area_m2
        claims.append(_pack(
            scope=f"{base}::Bpeak", rate_var="B_peak_T",
            kind="steady", value=B_peak, tol_frac=tol_frac,
            measurement=("hall probe through gap at known current OR "
                         "search-coil + integrator"),
            failure=("• exceeds B_sat -> L collapses, current spikes\n"
                     "• fringing concentrates flux at gap edges"),
            provenance="claim_back_magnetic.py",
            peak_current_A=peak_current_A,
            core_area_m2=core_area_m2,
        ))
    return claims


def _pack(**f):
    f["ts"] = time.time()
    f["id"] = hashlib.sha256(
        json.dumps(f, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f


def append_magnetic_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    keys = {(c["scope"], c["rate_var"]) for c in claims}
    existing = [e for e in existing
                if (e.get("scope"), e.get("rate_var")) not in keys]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
