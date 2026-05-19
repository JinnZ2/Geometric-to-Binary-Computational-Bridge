"""
couplers_friction.py  (fabrication/)

Mechanical-to-thermal coupler. Coupling ratio is EXACTLY 1.0 by
the first law: every joule of mechanical work against a viscous
damper becomes heat in that damper.

Why this is interesting to actually measure:
  Most lab dampers exhibit small ΔT (mK to a few K) and slow
  τ_th (minutes). Easier to assume conservation than measure it.
  Once you DO measure it, any deviation is a real physical
  signal -- acoustic radiation, mount conduction, elastic
  storage, parasitic loss paths.

Two measurement modes both supported by the verifier:

  STEADY-STATE forced vibration:
    ⟨P_mech⟩ = ½ · c · v̂²   (sinusoid, at resonance)
    dT_ss    = ⟨P_mech⟩ · R_th

  FREE DECAY:
    E_initial = ½ · k · x̂₀²
    All mech energy eventually becomes heat in the damper,
    then leaks to ambient with τ_th = R_th · C_th.

License: CC0. Stdlib only.
"""
import json
import hashlib
import math
import time
from pathlib import Path


OVERLAY = Path("coupler_overlay.json")


def predict_friction_coupler(
    name,
    damping_coefficient_c_Nsm,
    mass_m_kg,
    spring_k_N_per_m,
    drive_frequency_Hz=None,
    drive_amplitude_m=None,
    initial_amplitude_m=None,
    R_th_K_per_W=None,
    C_th_J_per_K=None,
    mechanical_scope=None,
    thermal_scope=None,
    expected_agreement_pct=0.95,
):
    c, m, k = damping_coefficient_c_Nsm, mass_m_kg, spring_k_N_per_m
    f0_mech = (1.0 / (2 * math.pi)) * math.sqrt(k / m)
    zeta    = c / (2.0 * math.sqrt(m * k))
    tau_th  = (R_th_K_per_W * C_th_J_per_K
               if (R_th_K_per_W and C_th_J_per_K) else None)

    pred = {
        "name":           name,
        "kind":           "friction_to_heat",
        "model":          "energy_conservation",
        "coupling_ratio": 1.0,
        "damping_c_Nsm":  c,
        "mass_m_kg":      m,
        "spring_k":       k,
        "f0_mech_Hz":     f0_mech,
        "zeta":           zeta,
        "R_th_K_per_W":   R_th_K_per_W,
        "C_th_J_per_K":   C_th_J_per_K,
        "tau_th_s":       tau_th,
        "mechanical_scope": mechanical_scope,
        "thermal_scope":    thermal_scope,
        "expected_agreement_pct": expected_agreement_pct,
        "provenance": "couplers_friction.py",
        "ts":         time.time(),
    }

    # steady-state predictions
    if drive_frequency_Hz is not None and drive_amplitude_m is not None:
        w = 2 * math.pi * drive_frequency_Hz
        v_hat = w * drive_amplitude_m
        Z_mag = math.sqrt(c * c + (w * m - k / w) ** 2)
        phase = math.atan2(w * m - k / w, c)
        P_mech_avg = 0.5 * c * (v_hat ** 2)
        pred["drive_frequency_Hz"]       = drive_frequency_Hz
        pred["drive_amplitude_m"]        = drive_amplitude_m
        pred["v_hat_mps"]                = v_hat
        pred["mechanical_impedance_Nsm"] = Z_mag
        pred["mechanical_phase_rad"]     = phase
        pred["P_mech_avg_W"]             = P_mech_avg
        if R_th_K_per_W is not None:
            pred["delta_T_ss_K"] = P_mech_avg * R_th_K_per_W

    # free-decay predictions
    if initial_amplitude_m is not None:
        E_initial = 0.5 * k * (initial_amplitude_m ** 2)
        pred["initial_amplitude_m"] = initial_amplitude_m
        pred["E_initial_J"]         = E_initial
        if C_th_J_per_K is not None:
            # Asymptotic peak ΔT during a quick-dump decay (β·τ >> 1):
            #   ΔT_peak ≈ P₀ / (C_th·β),  β = 2ζωₙ,  P₀ = ½·c·(x̂₀·ωd)²
            wn = math.sqrt(k / m)
            wd = wn * math.sqrt(max(1e-12, 1 - zeta ** 2))
            beta = 2 * zeta * wn
            P0 = 0.5 * c * ((initial_amplitude_m * wd) ** 2)
            if beta > 0:
                pred["delta_T_peak_K_predicted"] = P0 / (C_th_J_per_K * beta)
            else:
                pred["delta_T_peak_K_predicted"] = (
                    E_initial / C_th_J_per_K)

    pred["id"] = hashlib.sha256(
        json.dumps(pred, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return pred


def append_friction_coupler(entry, path: Path = OVERLAY):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [e for e in existing if e["name"] != entry["name"]]
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return entry["id"]
