"""
claim_back_resistor_heater.py  (fabrication/)

Cross-substrate claim for a resistor-heater coupler. One claim,
multiple agreements rolled into it:

  • ΔT_ss agreement: measured ΔT_ss / predicted ΔT_ss
  • τ agreement:     measured τ_th  / predicted τ_th
  • P agreement:     V·I              vs V²/R
  • R_th internal consistency:
      ΔT_ss_measured / P_measured  vs  R_th_geometric

Because the coupling ratio is exactly 1.0 by physics, ANY of
these disagreements is a real leak. The verifier's job is just
to localize which one.

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_resistor_heater(coupler):
    scope = f"fab::coupler::heater::{coupler['name']}"
    payload = {
        "scope":     scope,
        "rate_var":  "joule_heating_agreement_pct",
        "kind":      "cross_substrate",
        "value":     coupler["expected_agreement_pct"],
        "tol_frac":  0.05,
        "coupling_ratio": 1.0,
        "predicted_delta_T_ss_K": coupler["delta_T_ss_K"],
        "predicted_tau_th_s":     coupler["tau_th_s"],
        "predicted_P_elec_W":     coupler["P_elec_W"],
        "linked_scopes": {
            "electrical": coupler["electrical_scope"],
            "thermal":    coupler["thermal_scope"],
        },
        "measurement": ("measure V, I at the heater steady state -> "
                        "P_meas; measure ΔT_ss and τ_th from the thermal "
                        "CSV; cross-check P_meas·R_th vs ΔT_ss_meas; "
                        "and R_th_back_derived = ΔT_ss / P_meas vs "
                        "R_th_geom"),
        "failure": (
            "• P_meas ≠ V²/R -> wiring loss, lead resistance, OR R "
            "drifted with T\n"
            "• ΔT_ss agrees but τ off -> C_th wrong (mass, c_p, "
            "mounting hardware)\n"
            "• τ agrees but ΔT_ss off -> R_th wrong (extra convection "
            "path, radiation underweighted)\n"
            "• both off in same direction -> ambient drifted during "
            "test OR power supply not actually regulated\n"
            "• both off, R_th_back == R_th_pred -> thermal model "
            "self-consistent; leak is in the ELECTRICAL path"),
        "provenance": "claim_back_resistor_heater.py",
        "ts":         time.time(),
    }
    payload["id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return payload


def append_heater_claim(claim, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [c for c in existing if c["scope"] != claim["scope"]]
    existing.append(claim)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return claim["id"]
