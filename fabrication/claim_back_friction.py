"""
claim_back_friction.py  (fabrication/)

Three cross-substrate claims for friction-to-heat:

  1. ::mech_to_heat    mech_power_agreement_pct
     Steady-state: ⟨P_mech⟩ from F·v vs q̇ from ΔT_ss/R_th.

  2. ::energy_balance  energy_balance_agreement_pct
     Free decay: ½·k·x̂₀² vs C_th·ΔT_end + ∫(T-T_amb)/R_th dt.

  3. ::zeta_consistency zeta_agreement_pct
     ζ from mechanical log-decrement vs ζ predicted from c, m, k.

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_friction(coupler):
    base = f"fab::coupler::friction::{coupler['name']}"
    claims = []

    claims.append(_pack(
        scope=f"{base}::mech_to_heat",
        rate_var="mech_power_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.08,
        coupling_ratio=1.0,
        predicted_P_mech_W=coupler.get("P_mech_avg_W"),
        predicted_delta_T_ss_K=coupler.get("delta_T_ss_K"),
        measurement=("steady-state forced vibration at f_drive; measure "
                     "F(t) and v(t); compute ⟨P_mech⟩ = ⟨F·v⟩; measure "
                     "ΔT_ss at the damper; derive q̇ = ΔT_ss / R_th; "
                     "compare (ratio should be 1.0 exactly)"),
        failure=(
            "• q̇ < P_mech -> mechanical energy storing elastically OR "
            "radiating acoustically OR R_th underestimated\n"
            "• q̇ > P_mech -> second heat source (bearing friction, "
            "amplifier I²R conducting in)\n"
            "• both off, ratio ok -> drive level mis-recorded"),
        provenance="claim_back_friction.py",
        linked_scopes={
            "mechanical": coupler["mechanical_scope"],
            "thermal":    coupler["thermal_scope"],
        },
    ))

    if coupler.get("E_initial_J") is not None:
        claims.append(_pack(
            scope=f"{base}::energy_balance",
            rate_var="energy_balance_agreement_pct",
            kind="cross_substrate",
            value=coupler["expected_agreement_pct"],
            tol_frac=0.10,
            E_initial_J=coupler["E_initial_J"],
            predicted_delta_T_peak_K=coupler.get("delta_T_peak_K_predicted"),
            measurement=("release damper from initial x̂₀; record x(t) and "
                         "T(t) at the damper; compare ½·k·x̂₀² to "
                         "C_th·ΔT_end + ∫(T-T_amb)/R_th dt over the "
                         "full recording"),
            failure=(
                "• E_thermal < E_mech -> energy radiating acoustically OR "
                "mount conducting heat away OR R_th underestimated\n"
                "• E_thermal > E_mech -> external heating during test "
                "(room HVAC, sun on rig) OR x̂₀ underestimated"),
            provenance="claim_back_friction.py",
        ))

    claims.append(_pack(
        scope=f"{base}::zeta_consistency",
        rate_var="zeta_agreement_pct",
        kind="cross_substrate",
        value=coupler["expected_agreement_pct"],
        tol_frac=0.15,
        predicted_zeta=coupler["zeta"],
        measurement=("ζ_meas from mechanical log-decrement on x(t); "
                     "ζ_pred = c / (2·√(m·k))"),
        failure=(
            "• ζ_meas > ζ_pred -> NON-thermal loss path "
            "(acoustic radiation, sub-harmonic generation)\n"
            "• ζ_meas < ζ_pred -> external energy injection OR "
            "amplitude in nonlinear regime"),
        provenance="claim_back_friction.py",
    ))

    return claims


def _pack(**f):
    f["ts"] = time.time()
    f["id"] = hashlib.sha256(
        json.dumps(f, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return f


def append_friction_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    keys = {(c["scope"], c["rate_var"]) for c in claims}
    existing = [e for e in existing
                if (e.get("scope"), e.get("rate_var")) not in keys]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
