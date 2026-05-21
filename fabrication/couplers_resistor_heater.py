"""
couplers_resistor_heater.py  (fabrication/)

Pure resistor as electrical→thermal transformer. Coupling ratio
is EXACTLY 1.0 by physics (every joule of electrical work becomes
heat in an ohmic resistor). No coupling-factor fudge, no geometric
efficiency, no end correction.

That makes this coupler the gold standard for the bond-graph
abstraction: any disagreement between the electrical path and
the thermal path is a real measurement leak, not coupler-model
uncertainty.

Predictions composed from the electrical + thermal IRs:
    P_elec    = V² / R_elec
    ΔT_ss     = P_elec · R_th
    τ_th      = R_th · C_th
    T(t)      = T_amb + ΔT_ss · (1 - e^{-t/τ_th})  (step-on)

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path

from .backends.thermal import time_constant


OVERLAY = Path("coupler_overlay.json")


def predict_resistor_heater(
    name,
    R_elec_ohm, V_drive_V,
    R_th_K_per_W, C_th_J_per_K,
    electrical_scope, thermal_scope,
    expected_agreement_pct=0.97,
):
    P_elec     = (V_drive_V ** 2) / R_elec_ohm
    dT_ss_pred = P_elec * R_th_K_per_W
    tau_pred   = time_constant(R_th_K_per_W, C_th_J_per_K)
    entry = {
        "name":             name,
        "kind":             "resistor_heater",
        "model":            "joule_heating",
        "coupling_ratio":   1.0,
        "R_elec_ohm":       R_elec_ohm,
        "V_drive_V":        V_drive_V,
        "P_elec_W":         P_elec,
        "R_th_K_per_W":     R_th_K_per_W,
        "C_th_J_per_K":     C_th_J_per_K,
        "tau_th_s":         tau_pred,
        "delta_T_ss_K":     dT_ss_pred,
        "expected_agreement_pct": expected_agreement_pct,
        "electrical_scope": electrical_scope,
        "thermal_scope":    thermal_scope,
        "provenance":       "couplers_resistor_heater.py",
        "ts":               time.time(),
    }
    entry["id"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return entry


def append_resistor_heater(entry, path: Path = OVERLAY):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [e for e in existing if e["name"] != entry["name"]]
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return entry["id"]
