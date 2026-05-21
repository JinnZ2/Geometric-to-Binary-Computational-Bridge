"""
cross_transformer_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the transformer cross verifier.

Small audio-isolation transformer:
  N₁ = 600, N₂ = 60        (10:1 step-down, n = 0.1)
  Ferrite 3C90 toroid: A = 80 mm², path = 70 mm, μ_r = 2300
  Drive V₁ = 1.0 V AC, coupling k = 0.98

Predicted:
  L₁ ≈ N₁²/ℛ_core ≈ 1.19 H,  L₂ ≈ 11.9 mH
  L₁/L₂ = 100
  V₂_oc = V₁·n·k ≈ 0.098 V
  I₁/I₂ = n = 0.1                (ampere-turns balance)

Synthesizes three CSVs (voltage, current, inductance), runs the
cross verifier, asserts overall ∈ {pass, drift}.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.cross_transformer_smoke

License: CC0. Stdlib only.
"""
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...backends.magnetic import (core_reluctance, MAGNETIC_CORE)
from ...claim_back_magnetic import (back_claims_magnetic,
                                    append_magnetic_claims)
from ...claim_back_electrical import (back_claims_electrical,
                                      append_electrical_claims)
from ...couplers_transformer import (predict_transformer,
                                     append_transformer)
from ...claim_back_transformer import (back_claim_transformer,
                                       append_transformer_claims)
from ..verifier_cross_transformer import verify_cross_transformer


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
    random.seed(5)

    # --- magnetic IR for shared core ---
    mat = MAGNETIC_CORE["ferrite_3C90"]
    A_core = 80e-6
    le = 70e-3
    R_core = core_reluctance(le, A_core, mat["mu_r"])
    N1, N2 = 600, 60
    L1_true = N1 ** 2 / R_core
    L2_true = N2 ** 2 / R_core
    print(f"L1 = {L1_true*1e3:.2f} mH   L2 = {L2_true*1e3:.4f} mH   "
          f"L1/L2 = {L1_true/L2_true:.2f}")

    port_m = _P("magnetic", "PhiB", "MMF")

    # primary winding magnetic IR
    ir_m1 = _I("magnetic", [
        _E("dissipate", {"length": le, "area": A_core,
                         "mu_r": mat["mu_r"]}, R_core, port_m),
        _E("store_flow", {"turns": N1}, N1 ** 2, port_m),
    ])
    h_m1 = "TX_MAG_P"
    append_magnetic_claims(
        back_claims_magnetic(ir_m1, h_m1, tol_frac=0.08))

    # secondary winding magnetic IR (same core, different N)
    ir_m2 = _I("magnetic", [
        _E("dissipate", {"length": le, "area": A_core,
                         "mu_r": mat["mu_r"]}, R_core, port_m),
        _E("store_flow", {"turns": N2}, N2 ** 2, port_m),
    ])
    h_m2 = "TX_MAG_S"
    append_magnetic_claims(
        back_claims_magnetic(ir_m2, h_m2, tol_frac=0.08))

    # --- electrical IRs for primary + secondary as pure inductors ---
    port_e = _P("electrical", "I", "V")
    ir_e1 = _I("electrical", [
        _E("store_flow", {"L": L1_true}, L1_true, port_e),
    ])
    h_e1 = "TX_ELEC_P"
    append_electrical_claims(
        back_claims_electrical(ir_e1, h_e1, tol_frac=0.05))
    primary_scope = f"fab::electrical::{h_e1}::el0"

    ir_e2 = _I("electrical", [
        _E("store_flow", {"L": L2_true}, L2_true, port_e),
    ])
    h_e2 = "TX_ELEC_S"
    append_electrical_claims(
        back_claims_electrical(ir_e2, h_e2, tol_frac=0.05))
    secondary_scope = f"fab::electrical::{h_e2}::el0"

    # --- transformer coupler ---
    coupler = predict_transformer(
        name="smoke_tx",
        N1=N1, N2=N2, R_magnetic_total=R_core,
        R_lead_primary_ohm=2.0, R_lead_secondary_ohm=0.5,
        coupling_factor_k=0.98,
        drive_V_primary=1.0,
        load_R_secondary=None,
        electrical_scope_primary=primary_scope,
        electrical_scope_secondary=secondary_scope,
        magnetic_scope=f"fab::magnetic::{h_m1}",
    )
    append_transformer(coupler)
    append_transformer_claims(back_claim_transformer(coupler))
    print(f"predicted n = {coupler['n_ratio']:.4f}   "
          f"V2_oc = {coupler['V2_oc_predicted_V']:.4f} V")

    # --- (1) voltage CSV: open-circuit ratio (V₂/V₁ = n·k) ---
    rows = ["V1_volt,V2_volt"]
    for _ in range(20):
        V1 = 1.000 * (1 + random.gauss(0, 0.005))
        V2 = (V1 * coupler["n_ratio"] * coupler["coupling_factor_k"]
              * (1 + random.gauss(0, 0.005)))
        rows.append(f"{V1:.6f},{V2:.6f}")
    Path("voltage.csv").write_text("\n".join(rows))

    # --- (2) current CSV: short-circuit ratio (I₁/I₂ = n) ---
    # Ampere-turns balance: N₁·I₁ = N₂·I₂, so on a step-down (n<1)
    # the secondary carries the LARGER current.
    rows = ["I1_amp,I2_amp"]
    n = coupler["n_ratio"]
    for _ in range(20):
        I2 = 0.50 * (1 + random.gauss(0, 0.005))
        I1 = I2 * n * (1 + random.gauss(0, 0.005))
        rows.append(f"{I1:.6f},{I2:.6f}")
    Path("current.csv").write_text("\n".join(rows))

    # --- (3) paired LCR sweep ---
    rows = ["freq_Hz,Z1_ohm,phase1_deg,Z2_ohm,phase2_deg"]
    for f in [100, 200, 500, 1000, 2000]:
        w = 2 * math.pi * f
        Z1 = w * L1_true * (1 + random.gauss(0, 0.02))
        Z2 = w * L2_true * (1 + random.gauss(0, 0.02))
        ph = 88.0 + random.gauss(0, 0.5)
        rows.append(f"{f},{Z1:.4f},{ph:.2f},{Z2:.6f},{ph:.2f}")
    Path("inductance.csv").write_text("\n".join(rows))

    r = verify_cross_transformer(
        coupler_name="smoke_tx",
        voltage_csv="voltage.csv",
        current_csv="current.csv",
        inductance_csv="inductance.csv",
    )
    print(json.dumps(r, indent=2, default=str))

    assert r["overall"] in ("pass", "drift"), r
    assert r["sub_verdicts"]["n_oc"]    in ("pass", "drift"), r
    assert r["sub_verdicts"]["n_sc"]    in ("pass", "drift"), r
    assert r["sub_verdicts"]["L_ratio"] in ("pass", "drift"), r
    print("cross_transformer smoke OK")
