"""
couplers_solenoid.py  (fabrication/)

Solenoid / voice-coil cross-substrate coupler.

The gyrator ratio is the motor constant BL = B·L_wire,
  with units T·m = N/A = V·s/m.

  Motor equation:     F     = BL · I
  Generator equation: V_emf = BL · v

The same number BL falls out of both. Plus a third independent
mode (impedance peak at mechanical resonance) back-derives BL
through Z_peak = Re + BL²/Rms. Three independent paths -> the
first soft-ratio coupler whose single soft parameter is
directly falsifiable.

License: CC0. Stdlib only.
"""
import json
import hashlib
import math
import time
from pathlib import Path


OVERLAY = Path("coupler_overlay.json")


def predict_solenoid_coupler(
    name,
    Re_coil_ohm,
    Le_coil_H=None,
    B_field_T=None,
    L_wire_m=None,
    mass_m_kg=None,
    spring_k_N_per_m=None,
    damping_c_Nsm=None,
    electrical_scope=None,
    magnetic_scope=None,
    mechanical_scope=None,
    expected_agreement_pct=0.95,
):
    if B_field_T is None or L_wire_m is None:
        raise ValueError("B_field_T and L_wire_m are required.")
    BL = B_field_T * L_wire_m
    pred = {
        "name":  name,
        "kind":  "solenoid_gyrator",
        "model": "BL_motor_constant",
        "BL_T_m":          BL,
        "Re_coil_ohm":     Re_coil_ohm,
        "Le_coil_H":       Le_coil_H,
        "B_field_T":       B_field_T,
        "L_wire_m":        L_wire_m,
        "mass_m_kg":       mass_m_kg,
        "spring_k":        spring_k_N_per_m,
        "damping_c":       damping_c_Nsm,
        "linked_scopes": {
            "electrical": electrical_scope,
            "magnetic":   magnetic_scope,
            "mechanical": mechanical_scope,
        },
        "expected_agreement_pct": expected_agreement_pct,
        "provenance": "couplers_solenoid.py",
        "ts":         time.time(),
    }
    if mass_m_kg and spring_k_N_per_m:
        f0_mech = (1.0 / (2 * math.pi)) * math.sqrt(
            spring_k_N_per_m / mass_m_kg)
        pred["f0_mech_Hz"] = f0_mech
    if mass_m_kg and spring_k_N_per_m and damping_c_Nsm:
        Rms = damping_c_Nsm
        Z_peak = Re_coil_ohm + (BL ** 2) / Rms
        pred["Z_peak_predicted_ohm"] = Z_peak
        pred["Rms_Nsm"]              = Rms

    pred["id"] = hashlib.sha256(
        json.dumps(pred, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return pred


def append_solenoid_coupler(entry, path: Path = OVERLAY):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [e for e in existing if e["name"] != entry["name"]]
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return entry["id"]
