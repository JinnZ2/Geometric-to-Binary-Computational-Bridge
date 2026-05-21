"""
cross_friction_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the friction-to-heat cross verifier.

  m = 0.30 kg, k = 1200 N/m → f₀ ≈ 10.07 Hz
  c = 0.6 N·s/m              → ζ ≈ 0.0158
  damper thermal block: C_th = 4.5 J/K, R_th = 20 K/W
  τ_th = 90 s

  Steady drive at f₀, x̂ = 5 mm:
    v̂ = 0.316 m/s
    ⟨P_mech⟩ = ½·c·v̂² ≈ 30 mW
    ΔT_ss ≈ 0.6 K

  Free decay from x̂₀ = 30 mm:
    E_init = ½·k·x̂₀² = 0.54 J
    β = 2·ζ·ωₙ = 2 /s    (β·τ_th = 180, fast dump)
    ΔT_peak ≈ P₀/(C_th·β) ≈ 0.12 K
    ∫(T-T_amb)/R_th dt over full decay = P₀/β = E_init

Synthesizes both CSV pairs (additive noise scaled to ΔT, not
multiplicative on absolute T — important because the signal is
~0.6 K and ambient is ~293 K), runs verify_cross_friction,
asserts overall ∈ {pass, drift}.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.cross_friction_smoke

License: CC0. Stdlib only.
"""
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_mechanical import (back_claims_mechanical,
                                      append_mechanical_claims)
from ...claim_back_thermal import (back_claims_thermal,
                                   append_thermal_claims)
from ...couplers_friction import (predict_friction_coupler,
                                  append_friction_coupler)
from ...claim_back_friction import (back_claim_friction,
                                    append_friction_claims)
from ..verifier_cross_friction import verify_cross_friction


@dataclass
class _P:
    domain: str
    flow_name: str
    effort_name: str


@dataclass
class _E:
    kind: str
    geometry: dict
    parameter: float
    port_a: _P
    port_b: "_P" = None


@dataclass
class _I:
    domain: str
    elements: list = field(default_factory=list)
    topology: list = field(default_factory=list)


if __name__ == "__main__":
    random.seed(6)

    # ---- mechanical IR ----
    m, k, c = 0.30, 1200.0, 0.6
    port_m = _P("mechanical", "v", "F")
    ir_m = _I("mechanical", [
        _E("store_flow",   {"m": m},        m,       port_m),
        _E("store_effort", {"k": k},        1.0 / k, port_m),
        _E("dissipate",    {"c": c},        c,       port_m),
    ])
    h_m = "FRIC_MECH"
    append_mechanical_claims(
        back_claims_mechanical(ir_m, h_m, tol_frac=0.10))
    mech_scope = f"fab::mechanical::{h_m}"

    # ---- thermal IR ----
    C_th_val = 4.5
    R_th_val = 20.0
    port_t = _P("thermal", "qdot", "dT")
    ir_t = _I("thermal", [
        _E("dissipate",    {}, R_th_val, port_t),
        _E("store_effort", {}, C_th_val, port_t),
    ])
    h_t = "FRIC_THERM"
    append_thermal_claims(
        back_claims_thermal(ir_t, h_t, heat_source_W=None, tol_frac=0.10))
    therm_scope = f"fab::thermal::{h_t}"

    # ---- driver parameters ----
    f0 = (1 / (2 * math.pi)) * math.sqrt(k / m)
    wn = math.sqrt(k / m)
    zeta = c / (2 * math.sqrt(m * k))
    wd = wn * math.sqrt(1 - zeta ** 2)
    x_hat = 0.005
    w = 2 * math.pi * f0
    v_hat = w * x_hat
    P_mech_avg = 0.5 * c * v_hat ** 2
    dT_ss = P_mech_avg * R_th_val
    print(f"f0={f0:.3f} Hz   v̂={v_hat:.4f} m/s   "
          f"⟨P⟩={P_mech_avg:.4f} W   ΔT_ss={dT_ss:.3f} K")

    coupler = predict_friction_coupler(
        name="smoke_friction",
        damping_coefficient_c_Nsm=c,
        mass_m_kg=m, spring_k_N_per_m=k,
        drive_frequency_Hz=f0,
        drive_amplitude_m=x_hat,
        initial_amplitude_m=0.030,
        R_th_K_per_W=R_th_val,
        C_th_J_per_K=C_th_val,
        mechanical_scope=mech_scope,
        thermal_scope=therm_scope,
        expected_agreement_pct=0.95,
    )
    append_friction_coupler(coupler)
    append_friction_claims(back_claim_friction(coupler))

    # ---- (1) steady-state F,v CSV  (resonance: F and v in phase) ----
    F_hat = c * v_hat                       # |Z| at resonance = c
    sr = 1000
    duration = 2.0
    rows = ["time_s,F_N,v_mps"]
    for i in range(int(duration * sr)):
        t = i / sr
        F = F_hat * math.cos(w * t) + random.gauss(0, 0.01 * F_hat)
        v = v_hat * math.cos(w * t) + random.gauss(0, 0.01 * v_hat)
        rows.append(f"{t:.4f},{F:.6f},{v:.6f}")
    Path("Fv.csv").write_text("\n".join(rows))

    # ---- (2) steady-state thermal CSV  (additive ΔT-scaled noise) ----
    tau_th = R_th_val * C_th_val
    T0 = 293.15
    sr_steady = 1
    rows = ["time_s,T_K"]
    for i in range(int(5 * tau_th) + 1):
        t = float(i)
        dT = dT_ss * (1 - math.exp(-t / tau_th))
        T = T0 + dT + random.gauss(0, 0.01 * dT_ss)
        rows.append(f"{t:.2f},{T:.5f}")
    Path("therm_steady.csv").write_text("\n".join(rows))

    # ---- (3) free-decay x(t)  (lightly damped ringdown) ----
    # Truncate to ~6 s: by then the envelope is at 30·exp(-6) ≈ 74 µm,
    # which is 25× the 3 µm sensor noise. Recording the noise-
    # dominated tail breaks the zero-crossing period estimator.
    x0 = 0.030
    sr_d = 500
    duration_d = 6.0
    rows = ["time_s,x_m"]
    for i in range(int(duration_d * sr_d)):
        t = i / sr_d
        x = (x0 * math.exp(-zeta * wn * t) * math.cos(wd * t)
             + random.gauss(0, 3e-6))
        rows.append(f"{t:.4f},{x:.7f}")
    Path("decay.csv").write_text("\n".join(rows))

    # ---- (4) thermal decay CSV  (numerically integrate the ODE) ----
    # C_th · dT/dt = ⟨P_mech⟩(t) - (T-T_amb) / R_th
    # ⟨P_mech⟩(t) = ½ · c · v_envelope(t)²
    #             = ½ · c · (x₀·ωd·exp(-ζ·ωₙ·t))² (lightly damped)
    P0 = 0.5 * c * (x0 * wd) ** 2
    beta = 2 * zeta * wn
    dt_sim = 0.05
    duration_th = 5 * tau_th
    n_steps = int(duration_th / dt_sim) + 1
    sample_every = int(1.0 / dt_sim)       # record at 1 Hz
    T_curr = T0
    rows = ["time_s,T_K"]
    rows.append(f"0.00,{T_curr:.5f}")
    for step in range(1, n_steps + 1):
        t_sim = step * dt_sim
        P_mech_t = P0 * math.exp(-beta * t_sim)
        dT_curr = T_curr - T0
        dT_dt = (P_mech_t - dT_curr / R_th_val) / C_th_val
        T_curr += dT_dt * dt_sim
        if step % sample_every == 0:
            T_noisy = T_curr + random.gauss(0, 0.005 * 0.12)
            rows.append(f"{t_sim:.2f},{T_noisy:.5f}")
    Path("therm_decay.csv").write_text("\n".join(rows))

    print(f"E_init = {0.5*k*x0**2:.4f} J   "
          f"ΔT_peak(predicted) = {coupler['delta_T_peak_K_predicted']:.4f} K")

    # ---- run cross verifier ----
    r = verify_cross_friction(
        coupler_name="smoke_friction",
        force_velocity_csv="Fv.csv",
        thermal_steady_csv="therm_steady.csv",
        decay_csv="decay.csv",
        thermal_decay_csv="therm_decay.csv",
    )
    print(json.dumps(r, indent=2, default=str))
    assert r["overall"] in ("pass", "drift"), r
    print("cross_friction smoke OK")
