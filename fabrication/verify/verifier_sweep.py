"""
verifier_sweep.py  (fabrication/verify/)

Swept-sine variant of verify(). Same verdict + ledger semantics;
different measurement path.

Optional `baseline_id` argument: when present, the phone's own
transfer function is divided out before peak-pick (see
correct.correct_with_baseline). Diagnostics surface when no
baseline was used or when baseline coverage thinned after
correction.

License: CC0. Stdlib only (imports siblings).
"""
import time

from .transfer import transfer_function
from .peak import peak_pick_gated, q_factor
from .baseline import load_baseline
from .correct import correct_with_baseline
from .verifier import (
    _load_claims, _find_composite_freq_claim,
    _verdict, _diagnostic, _append_log,
)


def verify_sweep(sweep_wav, response_wav, scope,
                 search_band=(50, 2000), coh_min=0.7,
                 baseline_id=None, temp_c=None, ref_temp_c=15.0):
    """
    sweep_wav    : the exponential sweep you generated and played
    response_wav : phone-mic recording captured at the same time
    scope        : matches CLAIM_TABLE.fab.json composite claim scope
    baseline_id  : optional id from CLAIM_TABLE.fab.baselines.json
                   -- when provided, divide out the phone's response
    temp_c       : ambient temperature during the measurement (°C). When
                   given, the picked frequency is normalised to ref_temp_c
                   before the verdict, because f scales with c and c(T) moves
                   10.6 % between +20 °C and -40 °C -- more than the ±8 %
                   band. The raw pick travels in the record as measured_raw.
    ref_temp_c   : the temperature the claim's prediction was made at
    """
    freqs, mag, phase, coh = transfer_function(sweep_wav, response_wav)

    used_baseline = None
    if baseline_id is not None:
        baseline = load_baseline(baseline_id)
        freqs, mag, coh = correct_with_baseline(freqs, mag, coh, baseline)
        used_baseline = baseline_id

    peak = peak_pick_gated(freqs, mag, coh, *search_band, coh_min=coh_min)
    if peak is None:
        raise RuntimeError(
            f"No coherent peak in {search_band} Hz at γ²≥{coh_min}. "
            f"{'After baseline correction. ' if used_baseline else ''}"
            "Causes: speaker too quiet, mic too far, baseline-band mismatch."
        )
    f0_meas, _ = peak
    q_meas     = q_factor(freqs, mag, f0_meas)

    # --- temperature normalisation ------------------------------------
    f0_meas_raw = f0_meas
    if temp_c is not None:
        from fabrication.temperature import acoustic_f_correct
        f0_meas = acoustic_f_correct(f0_meas, temp_c, ref_temp_c)

    claims = _load_claims()
    claim  = _find_composite_freq_claim(claims, scope)
    if claim is None:
        raise KeyError(f"No composite freq claim for scope={scope}")

    f0_pred = claim["value"]
    tol     = claim.get("tol_frac", 0.08)
    verdict = _verdict(f0_meas, f0_pred, tol)
    notes   = _diagnostic(claim, f0_meas, q_meas)
    if temp_c is not None:
        notes.append("temperature: %.1f Hz @ %.1f °C -> %.1f Hz @ %.1f °C ref"
                     % (f0_meas_raw, temp_c, f0_meas, ref_temp_c))

    if used_baseline is None:
        notes.append("no baseline correction -- phone speaker/mic peaks may "
                     "contaminate result; capture baseline to improve")
    else:
        bins_ok = sum(1 for c in coh if c >= coh_min)
        if bins_ok < 100:
            notes.append(f"only {bins_ok} bins above coherence floor after "
                         f"baseline division -- recapture baseline or "
                         f"raise speaker amplitude")

    measurement = {
        "scope":        scope,
        "claim_id":     claim.get("id"),
        "method":       "swept_sine_baselined" if used_baseline
                        else "swept_sine",
        "baseline_id":  used_baseline,
        "predicted":    f0_pred,
        "measured":     f0_meas,
        "measured_raw": f0_meas_raw,
        "temp_c":       temp_c,
        "ref_temp_c":   ref_temp_c,
        "q_factor":     q_meas,
        "tol_frac":     tol,
        "verdict":      verdict,
        "diagnostic":   notes,
        "sweep_wav":    str(sweep_wav),
        "response_wav": str(response_wav),
        "coh_min":      coh_min,
        "ts":           time.time(),
    }
    _append_log(measurement)
    return measurement
