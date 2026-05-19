"""
fluidic_smoke.py  (fabrication/verify/tests/)

Synthesize a Hagen-Poiseuille channel, write the predicted claim,
generate a "measured" CSV with mild noise + a couple turbulent
points to confirm Reynolds gating works, verify.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.fluidic_smoke

License: CC0. Stdlib only.
"""
import random
from pathlib import Path

from ...claim_back_fluidic import back_claim_fluidic, append_fluidic_claim
from ...backends.fluidic   import FluidParams, channel_resistance
from ..verifier_fluidic    import verify_fluidic


if __name__ == "__main__":
    geometry = {"length": 0.30, "radius": 0.0015}   # 30 cm × 1.5 mm
    fluid    = FluidParams(rho=1000.0, mu=1.0e-3)    # water @ 20 °C
    geo_hash = "FLUIDIC_SMOKE"
    R_true = channel_resistance(geometry["length"],
                                geometry["radius"], fluid)
    print(f"R predicted = {R_true:.3e} Pa·s/m³")

    claim = back_claim_fluidic(geometry, fluid, geo_hash, tol_frac=0.10)
    append_fluidic_claim(claim)

    # synthesize CSV -- 10 laminar points + 2 turbulent
    random.seed(1)
    Q_points_laminar = [1e-7 * (i+1) for i in range(10)]    # 0.1 -> 1.0 µL/s
    Q_points_turb    = [2e-5, 4e-5]                          # forces high Re
    rows = [("time_s", "dP_Pa", "Q_mLs")]
    t = 0.0
    for Q in Q_points_laminar + Q_points_turb:
        dP = R_true * Q * (1 + random.gauss(0, 0.02))   # 2% noise
        rows.append((round(t, 2),
                     round(dP, 3),
                     round(Q / 1e-6, 6)))               # back to mL/s
        t += 5.0

    Path("flow.csv").write_text(
        "\n".join(",".join(str(x) for x in r) for r in rows)
    )

    scope = f"fab::fluidic::{geo_hash}"
    r = verify_fluidic("flow.csv", scope,
                       fluid_rho=fluid.rho, fluid_mu=fluid.mu,
                       channel_radius_m=geometry["radius"])
    print(r)
    assert r["verdict"] in ("pass", "drift"), r
    assert r["n_dropped_Re"] >= 1, "Reynolds gate must drop turb points"
    print("fluidic smoke OK")
