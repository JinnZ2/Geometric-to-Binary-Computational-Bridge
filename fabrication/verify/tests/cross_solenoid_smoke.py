"""
cross_solenoid_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the magnetic↔mechanical (solenoid) cross
verifier.

Small voice-coil actuator:
  B = 0.6 T in air gap,  L_wire = 4.5 m   -> BL = 2.7 T·m
  Re = 5.6 Ω,  Le = 0.4 mH
  moving mass m = 8 g, suspension k = 1200 N/m -> f₀ ≈ 61.5 Hz
  Rms = 1.1 N·s/m
  Z_peak (predicted) = Re + BL²/Rms ≈ 12.23 Ω

Synthesizes:
  - motor.csv:     F = BL·I + small noise
  - generator.csv: V = BL·v + small noise
  - impedance.csv: |Z(f)| with the motional peak from the moving
                   mass-spring-damper system reflected back through BL

Asserts overall ∈ {pass, drift} and at least the motor + generator
paths land in pass/drift.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.cross_solenoid_smoke

License: CC0. Stdlib only.
"""
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_electrical import (back_claims_electrical,
                                      append_electrical_claims)
from ...claim_back_magnetic import (back_claims_magnetic,
                                    append_magnetic_claims)
from ...claim_back_mechanical import (back_claims_mechanical,
                                      append_mechanical_claims)
from ...couplers_solenoid import (predict_solenoid_coupler,
                                  append_solenoid_coupler)
from ...claim_back_solenoid import (back_claim_solenoid,
                                    append_solenoid_claims)
from ..verifier_cross_solenoid import verify_cross_solenoid


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
    random.seed(7)

    # ---- design numbers ----
    B = 0.6
    L_wire = 4.5
    BL = B * L_wire
    Re = 5.6
    Le = 0.4e-3
    m_mov = 8e-3
    k_susp = 1200.0
    Rms = 1.1
    f0_mech = (1 / (2 * math.pi)) * math.sqrt(k_susp / m_mov)
    Z_peak_truth = Re + BL ** 2 / Rms
    print(f"BL = {BL:.3f} T·m   f₀_mech = {f0_mech:.2f} Hz   "
          f"Z_peak = {Z_peak_truth:.2f} Ω")

    # ---- electrical IR (coil winding) ----
    port_e = _P("electrical", "I", "V")
    ir_e = _I("electrical", [
        _E("dissipate", {"R": Re}, Re, port_e),
    ])
    h_e = "SOL_ELEC"
    append_electrical_claims(
        back_claims_electrical(ir_e, h_e, tol_frac=0.05))
    elec_scope = f"fab::electrical::{h_e}::el0"

    # ---- magnetic IR (placeholder; B is already specified for the coupler) ----
    port_m = _P("magnetic", "PhiB", "MMF")
    ir_g = _I("magnetic", [
        _E("dissipate",  {}, 1e6, port_m),
        _E("store_flow", {"turns": 1}, 1.0, port_m),
    ])
    h_g = "SOL_MAG"
    append_magnetic_claims(
        back_claims_magnetic(ir_g, h_g, tol_frac=0.10))
    mag_scope = f"fab::magnetic::{h_g}"

    # ---- mechanical IR (moving mass + suspension + damper) ----
    port_x = _P("mechanical", "v", "F")
    ir_x = _I("mechanical", [
        _E("store_flow",   {"m": m_mov},  m_mov,    port_x),
        _E("store_effort", {"k": k_susp}, 1.0/k_susp, port_x),
        _E("dissipate",    {"c": Rms},    Rms,      port_x),
    ])
    h_x = "SOL_MECH"
    append_mechanical_claims(
        back_claims_mechanical(ir_x, h_x, tol_frac=0.10))
    mech_scope = f"fab::mechanical::{h_x}"

    # ---- solenoid coupler ----
    coupler = predict_solenoid_coupler(
        name="smoke_solenoid",
        Re_coil_ohm=Re, Le_coil_H=Le,
        B_field_T=B, L_wire_m=L_wire,
        mass_m_kg=m_mov, spring_k_N_per_m=k_susp, damping_c_Nsm=Rms,
        electrical_scope=elec_scope,
        magnetic_scope=mag_scope,
        mechanical_scope=mech_scope,
    )
    append_solenoid_coupler(coupler)
    append_solenoid_claims(back_claim_solenoid(coupler))

    # ---- (1) motor.csv:  F = BL · I ----
    rows = ["I_amp,F_N"]
    for i in range(20):
        I = 0.05 * (i + 1)
        F = BL * I * (1 + random.gauss(0, 0.01))
        rows.append(f"{I:.4f},{F:.4f}")
    Path("motor.csv").write_text("\n".join(rows))

    # ---- (2) generator.csv:  V_emf = BL · v ----
    rows = ["v_mps,V_volt"]
    for i in range(20):
        v = 0.01 * (i + 1)
        V = BL * v * (1 + random.gauss(0, 0.01))
        rows.append(f"{v:.4f},{V:.4f}")
    Path("generator.csv").write_text("\n".join(rows))

    # ---- (3) impedance.csv:  Z(f) with mechanical motional peak ----
    # Z_motional = BL² / (Rms + j·(ω·m - k/ω));
    # Z_total    = Re + jω·Le + Z_motional
    rows = ["freq_Hz,Z_ohm"]
    for k_i in range(400):
        f = 1.0 * 10 ** (k_i / 200.0)        # 1 Hz -> 100 Hz log-spaced
        w = 2 * math.pi * f
        denom = complex(Rms, w * m_mov - k_susp / w)
        Z_motional = (BL ** 2) / denom
        Z_total = Re + 1j * w * Le + Z_motional
        z = abs(Z_total) * (1 + random.gauss(0, 0.01))
        rows.append(f"{f:.4f},{z:.5f}")
    Path("impedance.csv").write_text("\n".join(rows))

    # ---- run cross verifier ----
    r = verify_cross_solenoid(
        coupler_name="smoke_solenoid",
        motor_csv="motor.csv",
        generator_csv="generator.csv",
        impedance_csv="impedance.csv",
        search_band=(20.0, 100.0),
    )
    print(json.dumps(r, indent=2, default=str))
    assert r["overall"] in ("pass", "drift"), r
    assert r["sub_verdicts"]["motor"]     in ("pass", "drift"), r
    assert r["sub_verdicts"]["generator"] in ("pass", "drift"), r
    print("cross_solenoid smoke OK")
