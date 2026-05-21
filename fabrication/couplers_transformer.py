"""
couplers_transformer.py  (fabrication/)

Transformer prediction layer. Composes two electrical IRs
(primary + secondary inductors) and one magnetic IR (shared
core / shared reluctance path).

Faraday's law gives the EXACT ratios:

  V₂ / V₁  =  N₂ / N₁  =  n              (open-circuit secondary)
  I₁ / I₂  =  N₂ / N₁  =  n              (ampere-turns balance:
                                          N₁·I₁ = N₂·I₂)
  L₁ / L₂  =  (N₁ / N₂)²                  (inductance scales as N²)

Zero free coupling parameters when k=1. In practice k < 1
captures leakage flux; default 0.99 for a well-coupled toroid,
0.85–0.95 for E-I cores with air gaps.

License: CC0. Stdlib only.
"""
import json
import hashlib
import math
import time
from pathlib import Path


OVERLAY = Path("coupler_overlay.json")


def predict_transformer(
    name,
    N1, N2,
    R_magnetic_total,
    R_lead_primary_ohm=0.0,
    R_lead_secondary_ohm=0.0,
    coupling_factor_k=0.99,
    drive_V_primary=None,
    load_R_secondary=None,
    electrical_scope_primary=None,
    electrical_scope_secondary=None,
    magnetic_scope=None,
    expected_agreement_pct=0.97,
):
    L1 = (N1 ** 2) / R_magnetic_total
    L2 = (N2 ** 2) / R_magnetic_total
    M  = coupling_factor_k * math.sqrt(L1 * L2)
    n  = N2 / N1
    L_ratio_pred = L1 / L2

    pred = {
        "name":  name,
        "kind":  "transformer_gyrator",
        "model": "ideal_plus_leakage",
        "N1": N1, "N2": N2,
        "n_ratio": n,
        "L1_H": L1, "L2_H": L2, "M_H": M,
        "L_ratio_predicted": L_ratio_pred,
        "coupling_factor_k":      coupling_factor_k,
        "R_magnetic_total":       R_magnetic_total,
        "R_lead_primary_ohm":     R_lead_primary_ohm,
        "R_lead_secondary_ohm":   R_lead_secondary_ohm,
        "drive_V_primary":        drive_V_primary,
        "load_R_secondary":       load_R_secondary,
        "expected_agreement_pct": expected_agreement_pct,
        "linked_scopes": {
            "electrical_primary":   electrical_scope_primary,
            "electrical_secondary": electrical_scope_secondary,
            "magnetic":             magnetic_scope,
        },
        "provenance": "couplers_transformer.py",
        "ts":         time.time(),
    }
    if drive_V_primary is not None:
        pred["V2_oc_predicted_V"] = (
            drive_V_primary * n * coupling_factor_k)
        if load_R_secondary is not None and load_R_secondary > 0:
            Z_reflected = (n ** 2) * load_R_secondary
            Z_pri = Z_reflected + R_lead_primary_ohm
            I1 = (drive_V_primary / Z_pri) if Z_pri > 0 else float("inf")
            V2_loaded = (drive_V_primary * n * coupling_factor_k
                         * load_R_secondary
                         / (load_R_secondary + R_lead_secondary_ohm))
            I2 = V2_loaded / load_R_secondary
            pred["I1_loaded_predicted_A"] = I1
            pred["V2_loaded_predicted_V"] = V2_loaded
            pred["I2_loaded_predicted_A"] = I2

    pred["id"] = hashlib.sha256(
        json.dumps(pred, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return pred


def append_transformer(entry, path: Path = OVERLAY):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [e for e in existing if e["name"] != entry["name"]]
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return entry["id"]
