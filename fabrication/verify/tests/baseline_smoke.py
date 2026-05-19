"""
baseline_smoke.py  (fabrication/verify/tests/)

Synthetic check: simulate a phone with its own coloration, capture
baseline, then run a resonator measurement through it. Verdict
must change from spurious-near-pass (no baseline) to clean pass
(with baseline) when phone coloration would otherwise pull the
peak.

Run with:
    PYTHONPATH=/path/to/repo  python -m fabrication.verify.tests.baseline_smoke

License: CC0. Stdlib only.
"""
import hashlib
import json
import math
import time
from pathlib import Path

from ..sweep import exp_sweep, write_wav
from ..baseline import capture_baseline
from ..verifier_sweep import verify_sweep
from .sweep_smoke import simulate_resonator   # reuse biquad


def simulate_phone(samples, sr):
    """Phone coloration: mild peak ~600 Hz, roll-off below 80 Hz."""
    # peak at 600 Hz
    y = simulate_resonator(samples, sr, f0=600.0, q=2.5)
    # HPF (1-pole) at 80 Hz to mimic mic roll-off
    rc  = 1.0 / (2 * math.pi * 80.0)
    dt  = 1.0 / sr
    a   = rc / (rc + dt)
    out = [0.0] * len(y)
    prev_x = prev_y = 0.0
    for i, x in enumerate(y):
        out[i] = a * (prev_y + x - prev_x)
        prev_x, prev_y = x, out[i]
    return out


def seed_claim(scope, f0):
    L = Path("CLAIM_TABLE.fab.json")
    claims = json.loads(L.read_text()) if L.exists() else []
    claims.append({
        "scope":    scope,
        "rate_var": "resonance_freq_Hz",
        "kind":     "composite",
        "value":    f0,
        "tol_frac": 0.08,
        "id":       hashlib.sha256(scope.encode()).hexdigest()[:16],
        "ts":       time.time(),
    })
    L.write_text(json.dumps(claims, indent=2))


if __name__ == "__main__":
    f0_truth = 171.3
    scope = "fab::acoustic::BASELINE_SMOKE"
    seed_claim(scope, f0_truth)

    sweep_samples, sr = exp_sweep(50, 2000, 4.0)
    write_wav("sweep.wav", sweep_samples, sr)

    # baseline = phone alone (just phone coloration)
    baseline_samples = simulate_phone(sweep_samples, sr)
    write_wav("baseline.wav", baseline_samples, sr)
    bid = capture_baseline("sweep.wav", "baseline.wav", meta={
        "device_tag":     "smoke_phone",
        "volume_setting": "50",
        "sample_rate":    sr,
        "geometry_tag":   "free_space",
        "sweep_f1":       50.0,
        "sweep_f2":       2000.0,
        "sweep_duration": 4.0,
    })

    # response = phone coloration ∘ resonator
    cavity_samples   = simulate_resonator(sweep_samples, sr,
                                          f0=f0_truth, q=20.0)
    response_samples = simulate_phone(cavity_samples, sr)
    write_wav("response.wav", response_samples, sr)

    r_nb = verify_sweep("sweep.wav", "response.wav", scope)
    r_b  = verify_sweep("sweep.wav", "response.wav", scope,
                        baseline_id=bid)
    print("no baseline :", round(r_nb["measured"], 1), "Hz  Q≈",
          round(r_nb["q_factor"], 1), "  ", r_nb["verdict"])
    print("baselined   :", round(r_b ["measured"], 1), "Hz  Q≈",
          round(r_b ["q_factor"], 1), "  ", r_b ["verdict"])

    # Baselined Q should be closer to the truth Q (≈20) than the
    # uncorrected version, because phone's wide 600 Hz hump is gone.
    assert r_b["verdict"] == "pass"
    assert abs(r_b["q_factor"] - 20.0) < abs(r_nb["q_factor"] - 20.0)
    print("baseline smoke OK")
