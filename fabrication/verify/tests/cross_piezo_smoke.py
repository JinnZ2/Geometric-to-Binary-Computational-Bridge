"""
cross_piezo_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the cross-substrate piezo verifier.

Strategy:
  1. Define a cavity with a true f₀ = 412 Hz.
  2. Build acoustic IR + claim.
  3. Build electrical IR for the piezo-driven side; the piezo
     reads as a parallel RLC at the SAME f₀ (k_eff² shifts left
     for the smoke -- we run weak-coupling regime, agreement
     ≥ 99% expected).
  4. Build a piezo coupler entry linking the two scopes.
  5. Synthesize: acoustic sweep + response, electrical impedance.csv.
  6. Run verify_cross_piezo.
  7. Assert: both paths pass AND agreement meets the predicted band.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.cross_piezo_smoke

License: CC0. Stdlib only.
"""
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

from ..sweep import exp_sweep, write_wav
from ..baseline import capture_baseline
from .baseline_smoke import simulate_phone
from .sweep_smoke import simulate_resonator
from ...claim_back_modes import (back_claims_multimode,
                                 append_modes_to_ledger)
from ...claim_back_electrical import (back_claims_electrical,
                                      append_electrical_claims)
from ...coupler_overlay import make_piezo_coupler, append_coupler
from ...claim_back_coupler import (back_claim_piezo_coupler,
                                   append_coupler_claim)
from ..verifier_cross_piezo import verify_cross_piezo


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
    sr = 44100
    f0_truth = 412.0
    geo_hash_a = "CROSS_PIEZO_A"

    # --- acoustic IR (one Helmholtz) and claim ---
    port_a = _P("acoustic", "Q", "P")
    C_ac = 1.0 / ((2*math.pi*f0_truth)**2 * 1.0e-3)
    L_ac = 1.0e-3
    ir_a = _I("acoustic", [
        _E("store_effort", {}, C_ac, port_a),
        _E("store_flow",   {}, L_ac, port_a),
    ])
    claims_a = back_claims_multimode(ir_a, geo_hash_a, tol_frac=0.08)
    # patch claim to exactly f0_truth so the smoke isolates the
    # cross-check rather than fitting accuracy
    for c in claims_a:
        c["value"] = f0_truth
    append_modes_to_ledger(claims_a)
    acoustic_scope = f"fab::acoustic::{geo_hash_a}::mode0"

    # --- electrical IR (piezo presents an LC near f₀_acoustic) ---
    geo_hash_e = "CROSS_PIEZO_E"
    port_e = _P("electrical", "I", "V")
    L_e = 10e-3
    C_e = 1.0 / ((2*math.pi*f0_truth)**2 * L_e)
    R_e = 8.0
    ir_e = _I("electrical", [
        _E("dissipate",    {"R": R_e}, R_e, port_e),
        _E("store_flow",   {"L": L_e}, L_e, port_e),
        _E("store_effort", {"C": C_e}, C_e, port_e),
    ])
    claims_e = back_claims_electrical(ir_e, geo_hash_e, tol_frac=0.05)
    append_electrical_claims(claims_e)
    electrical_scope = f"fab::electrical::{geo_hash_e}::LC0"

    # --- coupler entry ---
    coupler = make_piezo_coupler(
        name="smoke_disc",
        material="PZT-5A",
        disc_geometry={"area": 5e-4, "thickness": 0.5e-3},
        cavity_geometry={"wall_area": 5e-3, "compliance_factor": 1.0},
        acoustic_scope=acoustic_scope,
        electrical_scope=electrical_scope,
        f_acoustic_pred=f0_truth,
    )
    append_coupler(coupler)
    coupler_claim = back_claim_piezo_coupler(coupler)
    append_coupler_claim(coupler_claim)

    print(f"k_eff² = {coupler['k_eff_squared']:.4f}   "
          f"regime = {coupler['regime']}")

    # --- synthesize acoustic side ---
    sweep_samples, _ = exp_sweep(50, 2000, 4.0, sr=sr)
    write_wav("sweep.wav", sweep_samples, sr)
    baseline = simulate_phone(sweep_samples, sr)
    write_wav("baseline.wav", baseline, sr)
    bid = capture_baseline("sweep.wav", "baseline.wav", {
        "device_tag":     "smoke",
        "volume_setting": "50",
        "sample_rate":    sr,
        "geometry_tag":   "free_space",
        "sweep_f1":       50.0,
        "sweep_f2":       2000.0,
        "sweep_duration": 4.0,
    })
    cavity = simulate_resonator(sweep_samples, sr, f0=f0_truth, q=22.0)
    response = simulate_phone(cavity, sr)
    write_wav("acoustic_response.wav", response, sr)

    # --- synthesize electrical impedance.csv (parallel RLC) ---
    freqs, mag = [], []
    for k in range(400):
        f = 50 * 10**(k/200)        # 50 Hz -> 5 kHz log-spaced
        w = 2*math.pi*f
        Y = complex(1.0/R_e, w*C_e - 1.0/(w*L_e))
        z = 1.0/abs(Y)
        freqs.append(f)
        mag.append(z)
    Path("impedance.csv").write_text(
        "freq_Hz,Z_ohm\n" +
        "\n".join(f"{f:.3f},{z:.6e}" for f, z in zip(freqs, mag))
    )

    # --- run cross verifier ---
    r = verify_cross_piezo(
        coupler_name="smoke_disc",
        sweep_wav="sweep.wav",
        acoustic_response_wav="acoustic_response.wav",
        acoustic_baseline_id=bid,
        electrical_impedance_csv="impedance.csv",
    )
    print(json.dumps(r, indent=2, default=str))

    assert r["overall"] in ("pass", "drift")
    assert r["agreement_pct"] >= r["expected_pct"] - r["tol_frac"]
    print("cross_piezo smoke OK")
