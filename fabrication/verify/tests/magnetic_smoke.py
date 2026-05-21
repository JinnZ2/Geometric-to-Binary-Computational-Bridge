"""
magnetic_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the magnetic verifier.

  Ferrite 3C90 toroid: A = 50 mm², ℓ = 50 mm, N = 100 turns.
  Predicted ℛ_core = ℓ/(μ₀·μ_r·A); L = N²/ℛ_core.

Generates:
  - a fake LCR-meter CSV (predominantly inductive, phase ≈ 89°)
  - a fake hall-probe B-vs-I CSV (linear, well below saturation)
asserts both verify pass/drift.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.magnetic_smoke

License: CC0. Stdlib only.
"""
import json
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_magnetic import (back_claims_magnetic,
                                    append_magnetic_claims)
from ..verifier_magnetic import (verify_magnetic_lcr,
                                 verify_magnetic_BvI)
from ...backends.magnetic import (core_reluctance, MAGNETIC_CORE)


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
    random.seed(3)
    mat = MAGNETIC_CORE["ferrite_3C90"]
    A_core = 50e-6
    le = 50e-3
    N = 100
    R_core = core_reluctance(le, A_core, mat["mu_r"])
    L_true = N ** 2 / R_core
    print(f"L predicted = {L_true*1e3:.3f} mH")

    port = _P("magnetic", "PhiB", "MMF")
    ir = _I("magnetic", [
        _E("dissipate", {"length": le, "area": A_core,
                         "mu_r": mat["mu_r"]}, R_core, port),
        _E("store_flow", {"turns": N}, N ** 2, port),
    ])
    h = "MAG_SMOKE"
    I_peak = 0.5
    claims = back_claims_magnetic(ir, h,
                                  peak_current_A=I_peak,
                                  core_area_m2=A_core,
                                  tol_frac=0.08)
    append_magnetic_claims(claims)

    # synthesize LCR sweep CSV (phase ≈ 89° -- pure inductor + tiny noise)
    freqs = [100, 200, 500, 1000, 2000, 5000, 10000]
    rows = ["freq_Hz,Z_ohm,phase_deg"]
    for f in freqs:
        Z = 2 * math.pi * f * L_true * (1 + random.gauss(0, 0.02))
        phase = 88.5 + random.gauss(0, 0.5)
        rows.append(f"{f},{Z:.4f},{phase:.2f}")
    Path("lcr.csv").write_text("\n".join(rows))

    r1 = verify_magnetic_lcr("lcr.csv", f"fab::magnetic::{h}")
    print("LCR verify:", json.dumps(r1, indent=2, default=str))
    assert r1["verdict"] in ("pass", "drift"), r1

    # synthesize B-vs-I CSV (linear, ≤ I_peak so we stay below B_sat)
    B_per_I = N / (R_core * A_core)
    rows = ["current_A,B_T"]
    for i in range(11):
        I = i * I_peak / 10
        B = B_per_I * I * (1 + random.gauss(0, 0.02))
        rows.append(f"{I:.4f},{B:.6f}")
    Path("BvI.csv").write_text("\n".join(rows))

    r2 = verify_magnetic_BvI("BvI.csv", f"fab::magnetic::{h}")
    print("B-I verify:", json.dumps(r2, indent=2, default=str))
    assert r2["verdict"] in ("pass", "drift"), r2
    print("magnetic smoke OK")
