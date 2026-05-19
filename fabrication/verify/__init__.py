"""
fabrication/verify/

Phone-mic FFT verifier. Closes the falsification loop.

  .wav (phone recording)  ──►  FFT  ──►  peak-pick (f₀, Q)
                                              │
                                              ▼
                            CLAIM_TABLE.fab.json lookup by scope
                                              │
                                              ▼
                            VERDICT: pass | drift | fail
                                              │
                                              ▼
                            measurement appended to
                            CLAIM_TABLE.fab.measurements.json

Stdlib-only. No numpy/scipy. Pure-Python Cooley-Tukey FFT.
Reads 16-bit PCM WAV. Runs on a phone via Termux/Pyto.

Usage:
    python -m fabrication.verify <wav> <scope> [f_lo f_hi]
"""
