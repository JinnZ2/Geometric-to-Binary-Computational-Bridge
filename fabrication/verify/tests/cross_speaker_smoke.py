"""
cross_speaker_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end of the three-substrate speaker verifier.

Strategy:
  1. Define Thiele-Small for a small full-range driver:
       Re=6.4Ω  Le=0.5mH   BL=4.2 T·m
       Mms=4.5g  Cms=6.5e-4 m/N   Rms=1.2 N·s/m   Sd=30 cm²
     -> predicted f_s = 1/(2π·√(Mms·Cms)) ≈ 93 Hz
  2. Build acoustic IR (one LC pair) -- claim patched to true f_s.
  3. Build electrical IR (RLC, parallel) -- claim patched to true f_s.
  4. Build mechanical IR (mass + compliance + damper) -- claim
     patched to true f_s and open-circuit ζ_ms.
  5. Make speaker coupler entry + cross-substrate claim.
  6. Synthesize:
       - acoustic sweep + biquad response at f_s
       - electrical impedance.csv -- motional peak at f_s
       - mechanical vibration.csv -- damped sinusoid at f_s
  7. Run verify_cross_speaker.
  8. Assert overall ∈ {pass, drift} and pairwise agreement >= budget.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.cross_speaker_smoke

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
from ...claim_back_mechanical import (back_claims_mechanical,
                                      append_mechanical_claims)
from ...coupler_overlay import make_speaker_coupler, append_coupler
from ...claim_back_speaker import (back_claim_speaker,
                                   append_speaker_claim)
from ...couplers_speaker import (speaker_fs_Hz, speaker_Q_mech,
                                 speaker_Q_total)
from ..verifier_cross_speaker import verify_cross_speaker


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


def _write_vib_csv(path, t, y, col="y_mm"):
    """y is in meters; write as mm to exercise the unit-aware reader."""
    lines = [f"time_s,{col}"]
    scale = 1e3 if col == "y_mm" else 1.0
    for ti, yi in zip(t, y):
        lines.append(f"{ti:.6f},{yi*scale:.6e}")
    Path(path).write_text("\n".join(lines))


if __name__ == "__main__":
    sr = 44100

    # ---- driver Thiele-Small ----
    Re, Le, BL  = 6.4, 0.5e-3, 4.2
    Mms, Cms    = 4.5e-3, 6.5e-4
    Rms         = 1.2
    Sd          = 30e-4
    f0_truth = speaker_fs_Hz(Mms, Cms)           # ≈ 93 Hz
    Q_ms     = speaker_Q_mech(Mms, Cms, Rms)
    Q_total  = speaker_Q_total(Mms, Cms, Rms, Re, BL)
    print(f"f_s = {f0_truth:.2f} Hz   Q_ms = {Q_ms:.2f}   "
          f"Q_total = {Q_total:.2f}")

    # ---- acoustic IR (one LC pair at f_s) ----
    geo_hash_a = "CROSS_SPK_A"
    port_a = _P("acoustic", "Q", "P")
    C_ac = 1.0 / ((2*math.pi*f0_truth)**2 * 1.0e-3)
    L_ac = 1.0e-3
    ir_a = _I("acoustic", [
        _E("store_effort", {}, C_ac, port_a),
        _E("store_flow",   {}, L_ac, port_a),
    ])
    claims_a = back_claims_multimode(ir_a, geo_hash_a, tol_frac=0.08)
    for c in claims_a:
        c["value"] = f0_truth
    append_modes_to_ledger(claims_a)
    acoustic_scope = f"fab::acoustic::{geo_hash_a}::mode0"

    # ---- electrical IR (parallel RLC peak at f_s) ----
    geo_hash_e = "CROSS_SPK_E"
    port_e = _P("electrical", "I", "V")
    L_e = 10e-3
    C_e = 1.0 / ((2*math.pi*f0_truth)**2 * L_e)
    R_e_lc = 8.0
    ir_e = _I("electrical", [
        _E("dissipate",    {"R": R_e_lc}, R_e_lc, port_e),
        _E("store_flow",   {"L": L_e},    L_e,    port_e),
        _E("store_effort", {"C": C_e},    C_e,    port_e),
    ])
    claims_e = back_claims_electrical(ir_e, geo_hash_e, tol_frac=0.05)
    append_electrical_claims(claims_e)
    electrical_scope = f"fab::electrical::{geo_hash_e}::LC0"

    # ---- mechanical IR (Mms, Cms, Rms) ----
    geo_hash_m = "CROSS_SPK_M"
    port_m = _P("mechanical", "v", "F")
    ir_m = _I("mechanical", [
        _E("store_flow",   {"m": Mms}, Mms, port_m),
        _E("store_effort", {"c": Cms}, Cms, port_m),
        _E("dissipate",    {"b": Rms}, Rms, port_m),
    ])
    claims_m = back_claims_mechanical(ir_m, geo_hash_m, tol_frac=0.06)
    append_mechanical_claims(claims_m)
    mechanical_scope = f"fab::mechanical::{geo_hash_m}::mode0"

    # ---- speaker coupler entry + cross-claim ----
    coupler = make_speaker_coupler(
        name="smoke_driver",
        Re=Re, Le=Le, BL=BL, Mms=Mms, Cms=Cms, Rms=Rms, Sd=Sd,
        acoustic_scope=acoustic_scope,
        electrical_scope=electrical_scope,
        mechanical_scope=mechanical_scope,
    )
    append_coupler(coupler)
    cclaim = back_claim_speaker(coupler)
    append_speaker_claim(cclaim)
    print(f"coupling_quality = {coupler['coupling_quality']:.3f}   "
          f"expected agreement = {100*coupler['expected_agreement_pct']:.1f}%")

    # ---- synthesize acoustic side ----
    sweep_samples, _ = exp_sweep(40, 2000, 4.0, sr=sr)
    write_wav("sweep.wav", sweep_samples, sr)
    baseline = simulate_phone(sweep_samples, sr)
    write_wav("baseline.wav", baseline, sr)
    bid = capture_baseline("sweep.wav", "baseline.wav", {
        "device_tag":     "smoke",
        "volume_setting": "50",
        "sample_rate":    sr,
        "geometry_tag":   "free_space",
        "sweep_f1":       40.0,
        "sweep_f2":       2000.0,
        "sweep_duration": 4.0,
    })
    cavity = simulate_resonator(sweep_samples, sr, f0=f0_truth, q=Q_total*1.5)
    response = simulate_phone(cavity, sr)
    write_wav("acoustic_response.wav", response, sr)

    # ---- synthesize electrical impedance.csv (parallel RLC peak) ----
    freqs, mag = [], []
    # log-spaced 20 Hz -> 2 kHz, 600 points
    for k in range(600):
        f = 20.0 * 10 ** (k / 300.0)
        if f > 2000.0:
            break
        w = 2 * math.pi * f
        # parallel RLC admittance
        Y = complex(1.0 / R_e_lc, w * C_e - 1.0 / (w * L_e))
        z = 1.0 / abs(Y)
        freqs.append(f)
        mag.append(z)
    Path("impedance.csv").write_text(
        "freq_Hz,Z_ohm\n" +
        "\n".join(f"{f:.3f},{z:.6e}" for f, z in zip(freqs, mag))
    )

    # ---- synthesize mechanical vibration.csv (damped sinusoid) ----
    # open-circuit mechanical ζ
    k_stiff = 1.0 / Cms
    zeta_truth = Rms / (2.0 * math.sqrt(Mms * k_stiff))
    wn_truth   = 2 * math.pi * f0_truth
    wd_truth   = wn_truth * math.sqrt(1 - zeta_truth**2)
    n = 4000
    dur = 0.5                  # 0.5 s of ring-down
    A_disp = 1.5e-3            # 1.5 mm initial displacement (typical impulse)
    t_arr = [i * dur / (n - 1) for i in range(n)]
    y_arr = [A_disp * math.exp(-zeta_truth*wn_truth*ti)
             * math.cos(wd_truth*ti) for ti in t_arr]
    _write_vib_csv("vibration.csv", t_arr, y_arr, col="y_mm")
    print(f"truth ζ_ms = {zeta_truth:.3f}   ωd = {wd_truth:.2f}   "
          f"f_d = {wd_truth/(2*math.pi):.2f} Hz")

    # ---- run cross verifier ----
    r = verify_cross_speaker(
        coupler_name="smoke_driver",
        sweep_wav="sweep.wav",
        acoustic_response_wav="acoustic_response.wav",
        acoustic_baseline_id=bid,
        acoustic_search_band=(40.0, 400.0),
        electrical_impedance_csv="impedance.csv",
        mechanical_vibration_csv="vibration.csv",
    )
    print(json.dumps(r, indent=2, default=str))

    assert r["overall"] in ("pass", "drift"), r
    assert r["agreement_min"] >= r["expected_pct"] - r["tol_frac"], r
    print("cross_speaker smoke OK")
