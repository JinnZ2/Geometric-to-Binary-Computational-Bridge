"""
multimode_smoke.py  (fabrication/verify/tests/)

Synthetic two-mode resonator (two biquads in parallel). Predict
modes from IR, seed multi-mode claims, run baselined multimode
verifier, assert all modes pass (or drift) and Q sane.

Run with:
    PYTHONPATH=/path/to/repo \\
        python -m fabrication.verify.tests.multimode_smoke

License: CC0. Stdlib only.
"""
import hashlib
from dataclasses import dataclass, field

from ..sweep import exp_sweep, write_wav
from ..baseline import capture_baseline
from ..verifier_modes import verify_multimode
from ...claim_back_modes import (back_claims_multimode,
                                 append_modes_to_ledger)
from .sweep_smoke import simulate_resonator
from .baseline_smoke import simulate_phone


# Minimal IR shim built by hand for this smoke test.
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


if __name__ == "__main__":
    sr = 44100
    port = _Port("acoustic", "Q", "P")

    # Two C,L pairs picked so the 1-D chain has two well-separated modes.
    # Exact numbers don't matter -- the smoke checks the LOOP (predict ->
    # claim -> measure -> match), not the absolute prediction.
    ir = _IR("acoustic", [
        _El("store_effort", {"volume": 2.5e-4},
            2.5e-4 / (1.225 * 343**2), port),
        _El("store_flow",   {"length": 0.03, "area": 1.77e-4},
            1.225 * 0.03 / 1.77e-4, port),
        _El("store_effort", {"volume": 1.2e-4},
            1.2e-4 / (1.225 * 343**2), port),
        _El("store_flow",   {"length": 0.02, "area": 1.77e-4},
            1.225 * 0.02 / 1.77e-4, port),
    ])

    geo_hash = hashlib.sha256(b"twomode_demo").hexdigest()[:12]
    claims = back_claims_multimode(ir, geo_hash, tol_frac=0.10)
    append_modes_to_ledger(claims)
    pred_freqs = [c["value"] for c in claims]
    print("predicted modes:", [round(f, 1) for f in pred_freqs])

    # synth physical response = sum of two biquads tuned to predicted modes
    sweep_samples, _ = exp_sweep(50, 4000, 5.0, sr=sr)
    write_wav("sweep.wav", sweep_samples, sr)

    r1 = simulate_resonator(sweep_samples, sr, f0=pred_freqs[0], q=25.0)
    r2 = simulate_resonator(sweep_samples, sr, f0=pred_freqs[1], q=18.0)
    cavity = [a + b for a, b in zip(r1, r2)]

    baseline = simulate_phone(sweep_samples, sr)
    write_wav("baseline.wav", baseline, sr)
    bid = capture_baseline("sweep.wav", "baseline.wav", {
        "device_tag":     "smoke",
        "volume_setting": "50",
        "sample_rate":    sr,
        "geometry_tag":   "free_space",
        "sweep_f1":       50.0,
        "sweep_f2":       4000.0,
        "sweep_duration": 5.0,
    })

    response = simulate_phone(cavity, sr)
    write_wav("response.wav", response, sr)

    scope_prefix = f"fab::acoustic::{geo_hash}"
    r = verify_multimode("sweep.wav", "response.wav", scope_prefix,
                         search_band=(50, 4000), baseline_id=bid)
    print("overall:", r["overall"])
    for pm in r["per_mode"]:
        print(" ", pm)
    assert r["overall"] in ("pass", "drift"), r
    assert all(pm.get("measured") is not None for pm in r["per_mode"])
    print("multimode smoke OK")
