"""
fluidic_transient_smoke.py  (fabrication/verify/tests/)

Two synthetic step responses through the verifier:

  first-order  RC:   τ_true = R·C  = 0.45 s
  second-order RLC:  underdamped step response with computed
                     ωn = 1/√(LC) and ζ = R/2 · √(C/L)

Both must verify pass (or drift).

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.fluidic_transient_smoke

License: CC0. Stdlib only.
"""
import math
import random
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_fluidic_transient import (back_claims_fluidic_transient,
                                             append_dyn_claims)
from ..verifier_fluidic_transient import verify_fluidic_transient


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


def write_csv(path, t, y, value_label="dP_Pa"):
    Path(path).write_text(
        f"time_s,{value_label},Q_m3s\n" +
        "\n".join(f"{ti:.4f},{yi:.4f},0.0" for ti, yi in zip(t, y))
    )


if __name__ == "__main__":
    port = _P("fluidic", "mdot", "P")
    random.seed(1)

    # --- first-order ---
    R, C = 4.5e9, 1e-10
    tau_true = R * C
    print(f"truth: tau = {tau_true:.3f} s")
    ir = _I("fluidic", [
        _E("dissipate",    {}, R, port),
        _E("store_effort", {}, C, port),
    ])
    hash1 = "FLUID_TRANS_RC"
    claims = back_claims_fluidic_transient(ir, hash1, tol_frac=0.15)
    append_dyn_claims(claims)

    t = [0.01*i for i in range(200)]   # 0..2 s
    A = 1000.0
    y = [A*(1 - math.exp(-ti/tau_true)) * (1 + random.gauss(0, 0.02))
         for ti in t]
    write_csv("step_rc.csv", t, y)

    r = verify_fluidic_transient("step_rc.csv",
                                 f"fab::fluidic::{hash1}::dyn")
    print("first-order:", r)
    assert r["verdict"] in ("pass", "drift"), r
    print("first-order smoke OK")

    # --- second-order ---
    R2, L2, Cc = 1e8, 1e8, 1e-9
    ir2 = _I("fluidic", [
        _E("dissipate",    {}, R2, port),
        _E("store_flow",   {}, L2, port),
        _E("store_effort", {}, Cc, port),
    ])
    hash2 = "FLUID_TRANS_RLC"
    claims2 = back_claims_fluidic_transient(ir2, hash2, tol_frac=0.15)
    append_dyn_claims(claims2)

    wn = 1.0 / math.sqrt(L2*Cc)
    zeta = (R2/2.0) * math.sqrt(Cc/L2)
    print(f"truth: wn={wn:.3f} rad/s   zeta={zeta:.3f}")
    # 1 / wn ~ 0.316 s, period ~ 2 s for these params -- a 2 s
    # window only contains ~1 oscillation, not enough for the
    # Gauss-Newton fit to converge with 2% noise. Use a 10 s
    # window (~5 oscillations) so the fit is well-constrained.
    t2 = [0.01*i for i in range(1000)]   # 0..10 s
    wd = wn * math.sqrt(1 - zeta**2)
    A2 = 1000.0
    y2 = []
    for ti in t2:
        env = math.exp(-zeta*wn*ti)
        osc = (math.cos(wd*ti) +
               (zeta/math.sqrt(1-zeta**2)) * math.sin(wd*ti))
        y2.append(A2*(1 - env*osc) * (1 + random.gauss(0, 0.02)))
    write_csv("step_rlc.csv", t2, y2)

    r2 = verify_fluidic_transient("step_rlc.csv",
                                  f"fab::fluidic::{hash2}::dyn")
    print("second-order:", r2)
    assert r2["verdict"] in ("pass", "drift"), r2
    print("second-order smoke OK")
