"""
claim_back_solenoid.py  (fabrication/)

Three independent claims, all measuring the SAME BL through
three different physical paths:

  1. ::BL_motor       BL_motor_agreement_pct
                      Blocked-coil F-vs-I: BL = slope of F vs I.

  2. ::BL_generator   BL_generator_agreement_pct
                      Open-circuit V_emf vs v: BL = slope of V vs v.

  3. ::BL_impedance   BL_impedance_agreement_pct
                      Swept-AC impedance with moving element installed:
                      Z_peak at f₀_mech satisfies
                      BL² = (Z_peak - Re) · Rms.

Joint pass/fail pattern triangulates which physical sub-model
is at fault.

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_solenoid(coupler):
    base = f"fab::coupler::solenoid::{coupler['name']}"
    claims = []

    claims.append(_pack(
        scope=f"{base}::BL_motor",
        rate_var="BL_motor_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.08,
        BL_predicted=coupler["BL_T_m"],
        measurement=(
            "BLOCKED-COIL: restrain the moving element; pass known DC "
            "current; measure force with load cell; BL_motor = F / I"),
        failure=(
            "• BL_motor < BL_predicted -> coil partially out of uniform "
            "field (or B lower than magnetic IR predicts)\n"
            "• BL_motor > BL_predicted -> wire length in field longer "
            "than counted (turn count or layer geometry mismatched)\n"
            "• nonlinear F vs I -> core saturation OR force sensor "
            "nonlinear"),
        provenance="claim_back_solenoid.py",
        linked_scopes=coupler["linked_scopes"],
    ))

    claims.append(_pack(
        scope=f"{base}::BL_generator",
        rate_var="BL_generator_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.08,
        BL_predicted=coupler["BL_T_m"],
        measurement=(
            "BACK-EMF: coil leads OPEN-CIRCUIT (no current); drive moving "
            "element mechanically at known velocity v; measure V_open "
            "across coil; BL_generator = V_open / v"),
        failure=(
            "• disagreement with BL_motor -> magnetic hysteresis OR coil "
            "moving out of uniform-field region at high amplitude\n"
            "• V_open lower than predicted -> coil leakage flux escaping "
            "the magnetic circuit\n"
            "• V_open rises with f -> self-capacitance, not pure BL"),
        provenance="claim_back_solenoid.py",
        linked_scopes=coupler["linked_scopes"],
    ))

    if coupler.get("Z_peak_predicted_ohm") is not None:
        claims.append(_pack(
            scope=f"{base}::BL_impedance",
            rate_var="BL_impedance_agreement_pct",
            kind="cross_substrate",
            value=coupler["expected_agreement_pct"],
            tol_frac=0.10,
            Z_peak_predicted=coupler["Z_peak_predicted_ohm"],
            BL_predicted=coupler["BL_T_m"],
            f0_mech_predicted_Hz=coupler.get("f0_mech_Hz"),
            measurement=(
                "IMPEDANCE-AT-RESONANCE: install moving element with "
                "spring; drive coil with swept AC; measure |Z(f)| via "
                "shunt; peak at mechanical f₀; back-derive "
                "BL² = (Z_peak - Re)·Rms"),
            failure=(
                "• Z_peak right but f₀ wrong -> m or k off "
                "(mechanical model)\n"
                "• f₀ right but Z_peak wrong -> BL wrong OR Rms wrong\n"
                "• both off -> coupling between field and coil weak; "
                "OR Re drifted under drive (TCR)"),
            provenance="claim_back_solenoid.py",
            linked_scopes=coupler["linked_scopes"],
        ))

    return claims


def _pack(**f):
    f["ts"] = time.time()
    f["id"] = hashlib.sha256(
        json.dumps(f, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f


def append_solenoid_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    keys = {(c["scope"], c["rate_var"]) for c in claims}
    existing = [e for e in existing
                if (e.get("scope"), e.get("rate_var")) not in keys]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
