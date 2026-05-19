"""
loop_smoke.py  (fabrication/verify/tests/)

Smoke test WITHOUT real fab -- generates a synthetic damped
sinusoid at known f₀ and Q, writes it to WAV, runs verify,
asserts verdict == "pass". Confirms FFT + peak + claim path
end-to-end before you ever cut anything.

Run from any CWD with the repo on PYTHONPATH:
    PYTHONPATH=/path/to/repo  python -m fabrication.verify.tests.loop_smoke

The CLAIM_TABLE.fab.json + smoke.wav land in CWD; pick a tmp dir.

License: CC0. Stdlib only.
"""
import hashlib
import json
import math
import struct
import time
import wave
from pathlib import Path

from ..verifier import verify


def synth_wav(path, f0=171.3, q=20.0, sr=44100, duration=2.0):
    n = int(sr * duration)
    tau = q / (math.pi * f0)        # decay time from Q
    data = [
        math.sin(2*math.pi*f0*i/sr) * math.exp(-(i/sr)/tau)
        for i in range(n)
    ]
    pcm = b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767))
                   for s in data)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm)


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
    scope = "fab::acoustic::SMOKE_TEST"
    seed_claim(scope, f0=171.3)
    synth_wav("smoke.wav", f0=171.3, q=20.0)
    r = verify("smoke.wav", scope)
    assert r["verdict"] == "pass", r
    print("smoke OK:", r["measured"], "Hz  Q≈", round(r["q_factor"], 1))
