"""
thermal_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the thermal verifier.

  50 × 50 × 20 mm aluminum block heated by a 5 W resistor through
  a 1 mm thermal-paste interface (k = 0.5 W/m·K). Surface loses
  heat by natural convection (h = 10 W/m²·K).

  Predicted τ ≈ R_total · C_total ≈ 16 K/W · 121 J/K ≈ 1960 s.
  Predicted ΔT_ss = 5 W · 16 K/W ≈ 80 K.

Synthesizes 5τ of step-heating data with 1% gaussian noise, runs
verify_thermal, asserts overall ∈ {pass, drift}.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.thermal_smoke

License: CC0. Stdlib only.
"""
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_thermal import (back_claims_thermal,
                                   append_thermal_claims)
from ..verifier_thermal import verify_thermal
from ...backends.thermal import (conduction_resistance, storage_capacity,
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
    random.seed(2)
    al = MATERIAL_THERMAL["aluminum"]

    # block: 50 × 50 × 20 mm aluminum
    V_block = 0.050 * 0.050 * 0.020
    C_th = storage_capacity(V_block, al["rho"], al["cp"])
    # 1 mm "paste" interface, k = 0.5 W/m·K, A = 25 cm²
    R_paste = conduction_resistance(length_m=0.001, area_m2=0.0025,
                                    k_thermal=0.5)
    # natural convection from the block's outer surface
    # (subtract the paste contact patch since heat leaves there
    # via conduction, not convection)
    A_total = 2 * (0.050*0.050 + 0.050*0.020 + 0.050*0.020)
    A_surf  = A_total - 0.0025
    R_conv  = 1.0 / (10.0 * A_surf)
    R_total = R_paste + R_conv
    tau_true = R_total * C_th
    dT_ss_true = 5.0 * R_total
    print(f"τ predicted = {tau_true:.1f} s   "
          f"ΔT_ss predicted = {dT_ss_true:.2f} K")

    port = _P("thermal", "qdot", "dT")
    ir = _I("thermal", [
        _E("dissipate",    {}, R_paste, port),
        _E("dissipate",    {}, R_conv,  port),
        _E("store_effort", {}, C_th,    port),
    ])
    h = "THERM_SMOKE"
    claims = back_claims_thermal(ir, h, heat_source_W=5.0, tol_frac=0.15)
    append_thermal_claims(claims)

    # synthesize step-heating data over 5τ, ~1 sample/sec, mild noise
    n = int(5 * tau_true) + 1
    t = [float(i) for i in range(n)]
    T0 = 293.15
    T = [T0 + dT_ss_true * (1 - math.exp(-ti / tau_true))
         * (1 + random.gauss(0, 0.01)) for ti in t]
    Path("heating.csv").write_text(
        "time_s,T_K\n"
        + "\n".join(f"{ti:.2f},{Ti:.3f}" for ti, Ti in zip(t, T))
    )

    r = verify_thermal("heating.csv", f"fab::thermal::{h}",
                       mode="heating")
    print(json.dumps(r, indent=2, default=str))
    assert r["overall"] in ("pass", "drift"), r
    print("thermal smoke OK")
