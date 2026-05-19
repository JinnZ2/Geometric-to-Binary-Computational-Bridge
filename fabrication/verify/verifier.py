"""
verifier.py  (fabrication/verify/)

CORE -- closes the loop against CLAIM_TABLE.fab.json.

verdict states:
  "pass"   -> measured ∈ predicted band
  "drift"  -> outside band, but within 2× (warning, not failure)
  "fail"   -> outside 2× band; bridge model is wrong for this fab

In all cases the measurement is appended back to the ledger
so the next run can detect trends.

License: CC0. Stdlib only.
"""
import json
import time
from pathlib import Path

from .wav_reader import read_wav
from .fft import magnitude_spectrum
from .peak import peak_pick, q_factor


LEDGER = Path("CLAIM_TABLE.fab.json")
LOG    = Path("CLAIM_TABLE.fab.measurements.json")


def _load_claims():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else []


def _find_composite_freq_claim(claims, scope):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == "resonance_freq_Hz":
            return c
    return None


def _verdict(measured, predicted, tol_frac):
    lo = predicted * (1 - tol_frac)
    hi = predicted * (1 + tol_frac)
    if lo <= measured <= hi:
        return "pass"
    lo2 = predicted * (1 - 2*tol_frac)
    hi2 = predicted * (1 + 2*tol_frac)
    if lo2 <= measured <= hi2:
        return "drift"
    return "fail"


def _diagnostic(claim, measured, q):
    """Map verdict + direction to most-likely failure mode."""
    predicted = claim["value"]
    ratio = measured / predicted
    notes = []
    if ratio < 0.85:
        notes.append("measured LOW: effective neck length larger than modeled "
                     "(end-correction undercounted) OR cavity volume larger "
                     "(wall flex / extra dead space)")
    if ratio > 1.15:
        notes.append("measured HIGH: cavity smaller than modeled "
                     "(material fill / mis-print) OR temp above 15°C "
                     "(c scales as √T)")
    if q is not None and q < 5:
        notes.append("Q very low: leak at neck-cavity joint OR porous wall")
    if q is not None and q > 50:
        notes.append("Q very high: model under-counts losses -- check "
                     "whether mic was in near-field")
    return notes or ["within model assumptions; tighten tol_frac if reproducible"]


def verify(wav_path, scope, search_band=(50, 2000)):
    """
    wav_path: phone recording of a single tap (or sweep) on the resonator
    scope:    matches the 'scope' field of the composite claim
              e.g. f"fab::acoustic::{geo_hash}"
    """
    samples, sr = read_wav(wav_path)
    freqs, mags = magnitude_spectrum(samples, sr)

    peak = peak_pick(freqs, mags, *search_band)
    if peak is None:
        raise RuntimeError(f"No peak in {search_band} Hz; check recording.")
    f0_meas, _ = peak
    q_meas     = q_factor(freqs, mags, f0_meas)

    claims = _load_claims()
    claim  = _find_composite_freq_claim(claims, scope)
    if claim is None:
        raise KeyError(f"No composite freq claim for scope={scope}")

    f0_pred = claim["value"]
    tol     = claim.get("tol_frac", 0.08)
    verdict = _verdict(f0_meas, f0_pred, tol)
    notes   = _diagnostic(claim, f0_meas, q_meas)

    measurement = {
        "scope":       scope,
        "claim_id":    claim.get("id"),
        "predicted":   f0_pred,
        "measured":    f0_meas,
        "q_factor":    q_meas,
        "tol_frac":    tol,
        "verdict":     verdict,
        "diagnostic":  notes,
        "wav":         str(wav_path),
        "sample_rate": sr,
        "ts":          time.time(),
    }
    _append_log(measurement)
    return measurement


def _append_log(entry):
    existing = json.loads(LOG.read_text()) if LOG.exists() else []
    existing.append(entry)
    LOG.write_text(json.dumps(existing, indent=2))
