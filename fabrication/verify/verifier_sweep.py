"""
verifier_sweep.py  (fabrication/verify/)

Swept-sine variant of verify(). Same verdict + ledger semantics;
different measurement path.

Why this is its own file (not additive to verifier.py): the
swept-sine path has its own diagnostics (coherence-bin count,
phone-case resonance smell) that don't apply to tap tests, and
keeping them separate lets the CLI cleanly subcommand "tap" vs
"sweep" without one path's helpers leaking into the other.

License: CC0. Stdlib only (imports siblings).
"""
import time

from .transfer import transfer_function
from .peak import peak_pick_gated, q_factor
from .verifier import (
    _load_claims, _find_composite_freq_claim,
    _verdict, _diagnostic, _append_log,
)


def verify_sweep(sweep_wav, response_wav, scope,
                 search_band=(50, 2000), coh_min=0.7):
    """
    sweep_wav    : the exponential sweep you generated and played
    response_wav : phone-mic recording captured at the same time
    scope        : matches CLAIM_TABLE.fab.json composite claim scope
    """
    freqs, mag, phase, coh = transfer_function(sweep_wav, response_wav)

    peak = peak_pick_gated(freqs, mag, coh, *search_band, coh_min=coh_min)
    if peak is None:
        raise RuntimeError(
            f"No coherent peak in {search_band} Hz at γ²≥{coh_min}. "
            "Speaker level too low, mic too far, or band excludes f₀."
        )
    f0_meas, _ = peak
    q_meas     = q_factor(freqs, mag, f0_meas)

    claims = _load_claims()
    claim  = _find_composite_freq_claim(claims, scope)
    if claim is None:
        raise KeyError(f"No composite freq claim for scope={scope}")

    f0_pred = claim["value"]
    tol     = claim.get("tol_frac", 0.08)
    verdict = _verdict(f0_meas, f0_pred, tol)
    notes   = _diagnostic(claim, f0_meas, q_meas)

    # sweep-specific diagnostics -- additive to tap diagnostics
    if q_meas > 100:
        notes.append("Q very high under sweep: likely resonance with "
                     "phone case, room mode, or speaker enclosure -- "
                     "move setup to free space and re-run")
    bins_trusted = sum(1 for c in coh if c >= coh_min)
    if bins_trusted < 100:
        notes.append(f"only {bins_trusted} frequency bins above coherence "
                     f"threshold -- increase sweep duration or speaker amp")

    measurement = {
        "scope":        scope,
        "claim_id":     claim.get("id"),
        "method":       "swept_sine",
        "predicted":    f0_pred,
        "measured":     f0_meas,
        "q_factor":     q_meas,
        "tol_frac":     tol,
        "verdict":      verdict,
        "diagnostic":   notes,
        "sweep_wav":    str(sweep_wav),
        "response_wav": str(response_wav),
        "coh_min":      coh_min,
        "bins_trusted": bins_trusted,
        "ts":           time.time(),
    }
    _append_log(measurement)
    return measurement
