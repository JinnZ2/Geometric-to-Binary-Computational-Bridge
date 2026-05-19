"""
verifier_modes.py  (fabrication/verify/)

Multi-mode verifier. Drop-in successor to verify_sweep for any
geometry whose ledger contains multiple `::modeN` composite claims.

Returns a richer result than verify_sweep:
  per_mode             : list of {predicted, measured, q_factor, verdict}
  unmatched_measured   : extra peaks the IR didn't predict
  diagnostic           : missing-mode / unmatched-peak notes
  overall              : worst-of {pass, drift, fail}

License: CC0. Stdlib only.
"""
import time

from .transfer import transfer_function
from .baseline import load_baseline
from .correct import correct_with_baseline
from .peak_multi import detect_peaks
from .assign import assign
from .verifier import _load_claims, _verdict, _append_log


def _find_mode_claims(claims, scope_prefix):
    """All composite freq claims under scope_prefix::modeN."""
    out = []
    prefix = scope_prefix + "::mode"
    for c in claims:
        if c.get("rate_var") == "resonance_freq_Hz" and \
           c.get("scope", "").startswith(prefix):
            out.append(c)
    out.sort(key=lambda c: c["mode_index"])
    return out


def _overall(verdicts):
    """Worst-of: fail > drift > pass."""
    rank = {"pass": 0, "drift": 1, "fail": 2}
    return max(verdicts, key=lambda v: rank[v]) if verdicts else "fail"


def verify_multimode(sweep_wav, response_wav, scope_prefix,
                     search_band=(50, 4000), coh_min=0.7,
                     baseline_id=None, prominence_frac=0.05,
                     max_peaks=8):
    freqs, mag, phase, coh = transfer_function(sweep_wav, response_wav)
    if baseline_id is not None:
        baseline = load_baseline(baseline_id)
        freqs, mag, coh = correct_with_baseline(freqs, mag, coh, baseline)

    measured = detect_peaks(freqs, mag, coh,
                            search_band=search_band, coh_min=coh_min,
                            prominence_frac=prominence_frac,
                            max_peaks=max_peaks)
    if not measured:
        raise RuntimeError(
            f"No coherent peaks in {search_band} Hz. "
            "Check baseline, speaker level, and search band.")

    claims = _load_claims()
    mode_claims = _find_mode_claims(claims, scope_prefix)
    if not mode_claims:
        raise KeyError(
            f"No mode claims under {scope_prefix}. Run "
            "back_claims_multimode + append_modes_to_ledger first.")

    predicted = [{"f": c["value"], "mode_index": c["mode_index"],
                  "tol": c.get("tol_frac", 0.08), "claim": c}
                 for c in mode_claims]

    matches, unmatched_p, unmatched_m = assign(predicted, measured)

    per_mode = []
    verdicts = []
    notes_global = []
    for pi, mi, d in matches:
        p = predicted[pi]
        m = measured[mi]
        v = _verdict(m["f"], p["f"], p["tol"])
        per_mode.append({
            "mode_index": p["mode_index"],
            "predicted":  p["f"],
            "measured":   m["f"],
            "delta_pct":  100*(m["f"]/p["f"] - 1),
            "q_factor":   m["q"],
            "coh":        m["coh"],
            "verdict":    v,
        })
        verdicts.append(v)

    for pi in unmatched_p:
        p = predicted[pi]
        per_mode.append({
            "mode_index": p["mode_index"],
            "predicted":  p["f"],
            "measured":   None,
            "verdict":    "fail",
            "reason":     "predicted mode not found in spectrum",
        })
        verdicts.append("fail")
        notes_global.append(
            f"missing mode {p['mode_index']} @ {p['f']:.1f} Hz "
            "-- coupling neck blocked, excitation weak, or Q too high")

    extras = []
    for mi in unmatched_m:
        m = measured[mi]
        extras.append({
            "f":    m["f"], "q": m["q"], "coh": m["coh"],
            "note": "unmatched peak (not predicted by IR)",
        })
        notes_global.append(
            f"unmatched measured peak at {m['f']:.1f} Hz -- "
            "possible room mode, phone enclosure resonance, "
            "or missing physics in IR (e.g. higher-order pipe mode)")

    overall = _overall(verdicts)
    result = {
        "scope_prefix":       scope_prefix,
        "method":             "swept_sine_multimode"
                              + ("_baselined" if baseline_id else ""),
        "baseline_id":        baseline_id,
        "per_mode":           sorted(per_mode, key=lambda x: x["mode_index"]),
        "unmatched_measured": extras,
        "overall":            overall,
        "diagnostic":         notes_global,
        "sweep_wav":          str(sweep_wav),
        "response_wav":       str(response_wav),
        "ts":                 time.time(),
    }
    _append_log(result)
    return result
