"""
sweep_smoke.py  (fabrication/verify/tests/)

Synthetic end-to-end: generate sweep, simulate a damped
second-order resonator's effect on it, write both wavs,
run verify_sweep, assert pass. No hardware required.

Run from any CWD with the repo on PYTHONPATH:
    PYTHONPATH=/path/to/repo  python -m fabrication.verify.tests.sweep_smoke

License: CC0. Stdlib only.
"""
import hashlib
import json
import math
import time
from pathlib import Path

from ..sweep import exp_sweep, write_wav
from ..verifier_sweep import verify_sweep


def simulate_resonator(samples, sr, f0, q):
    """
    Discrete biquad resonator (2nd-order bandpass-ish).
    Models the cavity's effect on the sweep -- peak at f0 with
    bandwidth f0/Q. Uses the RBJ bandpass with constant 0 dB peak gain.
    """
    w0    = 2 * math.pi * f0 / sr
    alpha = math.sin(w0) / (2 * q)
    cosw  = math.cos(w0)
    b0, b1, b2 =  alpha, 0.0, -alpha
    a0, a1, a2 =  1 + alpha, -2 * cosw, 1 - alpha
    b0, b1, b2 = b0/a0, b1/a0, b2/a0
    a1, a2     = a1/a0, a2/a0
    y = [0.0] * len(samples)
    x1 = x2 = y1 = y2 = 0.0
    for i, x in enumerate(samples):
        y[i] = b0*x + b1*x1 + b2*x2 - a1*y1 - a2*y2
        x2, x1 = x1, x
        y2, y1 = y1, y[i]
    return y


def seed_claim(scope, f0):
    L = Path("CLAIM_TABLE.fab.json")
    claims = json.loads(L.read_text()) if L.exists() else []
    claims.append({
        "scope":     scope,
        "rate_var":  "resonance_freq_Hz",
        "kind":      "composite",
        "value":     f0,
        "tol_frac":  0.08,
        "id":        hashlib.sha256(scope.encode()).hexdigest()[:16],
        "ts":        time.time(),
    })
    L.write_text(json.dumps(claims, indent=2))


if __name__ == "__main__":
    f0_truth, q_truth = 171.3, 20.0
    scope = "fab::acoustic::SWEEP_SMOKE"
    seed_claim(scope, f0_truth)

    sweep_samples, sr = exp_sweep(f1=50, f2=2000, duration=4.0)
    write_wav("sweep.wav", sweep_samples, sr)

    response = simulate_resonator(sweep_samples, sr, f0_truth, q_truth)
    write_wav("response.wav", response, sr)

    r = verify_sweep("sweep.wav", "response.wav", scope)
    assert r["verdict"] == "pass", r
    print("sweep smoke OK:", round(r["measured"], 1),
          "Hz  Q≈", round(r["q_factor"], 1))
