"""
cross_heater_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the resistor-heater cross verifier.

  47 Ω power resistor at 12 V drive (P = 144/47 ≈ 3.06 W).
  Mounted on a small aluminum heatsink (40 × 40 × 20 mm) through
  a 0.5 mm thermal-paste interface, natural convection to ambient.

  Predicted: R_th ≈ 16.7 K/W, C_th ≈ 77.5 J/K,
             τ_th ≈ 1295 s, ΔT_ss ≈ 51 K.

Synthesizes VI.csv (20 steady samples, 0.5% jitter) and
thermal.csv (5τ of step heating with 0.8% noise), runs
verify_cross_heater, asserts overall ∈ {pass, drift} and that
the back-derived R_th matches geometric prediction within 15%.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.cross_heater_smoke

License: CC0. Stdlib only.
"""
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_electrical import (back_claims_electrical,
                                      append_electrical_claims)
from ...claim_back_thermal import (back_claims_thermal,
                                   append_thermal_claims)
from ...couplers_resistor_heater import (predict_resistor_heater,
                                         append_resistor_heater)
from ...claim_back_resistor_heater import (back_claim_resistor_heater,
                                           append_heater_claim)
from ..verifier_cross_heater import verify_cross_heater
from ...backends.thermal import (conduction_resistance,
                                 storage_capacity,
                                 MATERIAL_THERMAL)


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
    random.seed(4)

    # --- electrical IR: a single resistor ---
    R_e = 47.0
    V_drive = 12.0
    port_e = _P("electrical", "I", "V")
    ir_e = _I("electrical", [
        _E("dissipate", {"R": R_e}, R_e, port_e),
    ])
    h_e = "HEATER_ELEC"
    claims_e = back_claims_electrical(ir_e, h_e, tol_frac=0.05)
    append_electrical_claims(claims_e)
    elec_scope = f"fab::electrical::{h_e}::el0"

    # --- thermal IR: heater on aluminum sink ---
    al = MATERIAL_THERMAL["aluminum"]
    V_sink = 0.040 * 0.040 * 0.020
    C_th = storage_capacity(V_sink, al["rho"], al["cp"])
    R_paste = conduction_resistance(length_m=0.0005, area_m2=0.0009,
                                    k_thermal=0.5)
    A_surf = 2 * (0.040*0.040 + 0.040*0.020 + 0.040*0.020)
    R_conv = 1.0 / (10.0 * A_surf)
    R_th = R_paste + R_conv

    port_t = _P("thermal", "qdot", "dT")
    ir_t = _I("thermal", [
        _E("dissipate",    {}, R_paste, port_t),
        _E("dissipate",    {}, R_conv,  port_t),
        _E("store_effort", {}, C_th,    port_t),
    ])
    h_t = "HEATER_THERM"
    P_elec_W = V_drive ** 2 / R_e
    claims_t = back_claims_thermal(ir_t, h_t,
                                   heat_source_W=P_elec_W,
                                   tol_frac=0.10)
    append_thermal_claims(claims_t)
    therm_scope = f"fab::thermal::{h_t}"

    # --- coupler entry + cross claim ---
    coupler = predict_resistor_heater(
        name="smoke_heater",
        R_elec_ohm=R_e, V_drive_V=V_drive,
        R_th_K_per_W=R_th, C_th_J_per_K=C_th,
        electrical_scope=elec_scope,
        thermal_scope=therm_scope,
    )
    append_resistor_heater(coupler)
    append_heater_claim(back_claim_resistor_heater(coupler))
    print(f"predicted P={coupler['P_elec_W']:.2f} W   "
          f"ΔT_ss={coupler['delta_T_ss_K']:.2f} K   "
          f"τ={coupler['tau_th_s']:.1f} s")

    # --- synthesize VI.csv ---
    rows = ["V_volt,I_amp"]
    for _ in range(20):
        V = V_drive * (1 + random.gauss(0, 0.005))
        I = V / R_e * (1 + random.gauss(0, 0.005))
        rows.append(f"{V:.5f},{I:.5f}")
    Path("VI.csv").write_text("\n".join(rows))

    # --- synthesize thermal.csv (first-order heating) ---
    tau_true = coupler["tau_th_s"]
    dT_ss    = coupler["delta_T_ss_K"]
    T_amb_K  = 293.15
    n = int(5 * tau_true) + 1
    t = [float(i) for i in range(n)]
    T_k = [T_amb_K + dT_ss * (1 - math.exp(-ti / tau_true))
           * (1 + random.gauss(0, 0.008)) for ti in t]
    Path("thermal.csv").write_text(
        "time_s,T_K\n"
        + "\n".join(f"{ti:.2f},{Tk:.3f}" for ti, Tk in zip(t, T_k))
    )

    r = verify_cross_heater(
        coupler_name="smoke_heater",
        VI_csv="VI.csv",
        thermal_csv="thermal.csv",
        thermal_mode="heating",
    )
    print(json.dumps(r, indent=2, default=str))

    assert r["overall"] in ("pass", "drift"), r
    ratio = r["R_th_back_derived_K_per_W"] / r["R_th_predicted_K_per_W"]
    assert abs(ratio - 1.0) < 0.15, (ratio, r)
    print("cross_heater smoke OK")
