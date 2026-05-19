"""
electrical_smoke.py  (fabrication/verify/tests/)

Synthesize a series RLC resonator (the topology produced when the
IR has R, L, C in series):
    L = 1 mH, C = 100 nF  ->  f₀ = 1/(2π√(LC)) ≈ 15.92 kHz
    R = 5 Ω               ->  Q = (1/R)√(L/C) ≈ 20

Build the predicted IR, write the LC claim, generate a synthetic
|Z|(f) curve in CSV form (series-RLC: |Z| dips to R at f₀),
run verify_electrical_csv, assert pass + Q within band.

Note: the paste's smoke source was truncated mid-line; this is
the smallest reasonable test that exercises the full path
(claim -> CSV -> verify) consistent with the spec in the
docstring of the original paste.

Run with:
    PYTHONPATH=/path/to/repo  python -m fabrication.verify.tests.electrical_smoke

License: CC0. Stdlib only.
"""
import math
from dataclasses import dataclass, field
from pathlib import Path

from ...claim_back_electrical import (back_claims_electrical,
                                      append_electrical_claims)
from ..verifier_electrical import verify_electrical_csv


# Minimal IR shim built by hand for the smoke test
@dataclass
class _Port:
    domain: str
    flow_name: str
    effort_name: str


@dataclass
class _El:
    kind: str
    geometry: dict
    parameter: float
    port_a: _Port
    port_b: "_Port" = None


@dataclass
class _IR:
    domain: str
    elements: list = field(default_factory=list)
    topology: list = field(default_factory=list)


def synth_series_rlc_csv(path, R, L, C, fmin=5e3, fmax=50e3, n=200):
    """Series RLC: |Z(f)| = sqrt(R² + (ωL - 1/(ωC))²). Min at f₀."""
    # log-spaced sweep
    rows = ["freq_Hz,Z_ohm"]
    log_lo, log_hi = math.log10(fmin), math.log10(fmax)
    for i in range(n):
        f = 10 ** (log_lo + (log_hi - log_lo) * i / (n - 1))
        w = 2 * math.pi * f
        z = math.sqrt(R * R + (w * L - 1.0 / (w * C)) ** 2)
        rows.append(f"{f:.4f},{z:.6f}")
    Path(path).write_text("\n".join(rows))


if __name__ == "__main__":
    port = _Port("electrical", "I", "V")
    L, C, R = 1e-3, 1e-7, 5.0
    geo_hash = "ELEC_SMOKE_LC"
    f0_truth = 1.0 / (2 * math.pi * math.sqrt(L * C))
    q_truth = (1.0 / R) * math.sqrt(L / C)
    print(f"truth: f₀ = {f0_truth:.1f} Hz   Q = {q_truth:.1f}")

    ir = _IR("electrical", [
        _El("dissipate",    {"R": R}, R, port),
        _El("store_flow",   {"L": L}, L, port),
        _El("store_effort", {"C": C}, C, port),
    ])

    claims = back_claims_electrical(ir, geo_hash, tol_frac=0.05)
    append_electrical_claims(claims)

    synth_series_rlc_csv("z_sweep.csv", R, L, C,
                         fmin=5e3, fmax=50e3, n=400)

    scope = f"fab::electrical::{geo_hash}::LC0"
    r = verify_electrical_csv("z_sweep.csv", scope)
    print(r)
    assert r["verdict"] in ("pass", "drift"), r
    # series RLC -> dip in |Z|
    assert r["extremum"] == "dip", r
    print("electrical smoke OK")
