"""
verifier_cross_speaker.py  (fabrication/verify/)

Three-substrate cross verifier for a dynamic speaker. Runs the
single-substrate verifiers (acoustic, electrical, mechanical) on
their own captures, then audits whether all three converge on the
predicted f_s within the coupler's agreement budget.

Triangulation table -- with three paths, disagreement narrows the
suspect down to one side instead of two:

    A=E≠M -> mechanical model wrong (clamp, modal mass)
    A=M≠E -> electrical model wrong (Le, stray cap, leads)
    E=M≠A -> acoustic model wrong (radiation, room, mic)
    none  -> coupler itself wrong (BL or Sd)

The shunt-WAV branch for the electrical side is not yet implemented
(same status as in the piezo verifier); we accept the impedance CSV
path only.

License: CC0. Stdlib only.
"""
import time

from .verifier import _load_claims, _verdict, _append_log
from .verifier_sweep import verify_sweep
from .verifier_electrical import verify_electrical_csv
from .verifier_mechanical import verify_mechanical
from ..coupler_overlay import get_coupler


def _find_coupler_claim(claims, scope):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == "f0_agreement_pct":
            return c
    return None


def _pair_agreement(f1, f2):
    return 1.0 - 2.0 * abs(f1 - f2) / (f1 + f2)


def _triangulate(verdict_A, verdict_E, verdict_M,
                 ag_AE, ag_AM, ag_EM, expected, tol):
    """Diagnose which pair agrees / which substrate carries the error."""
    notes = []
    band = expected - tol
    pass_AE = ag_AE >= band
    pass_AM = ag_AM >= band
    pass_EM = ag_EM >= band

    if pass_AE and pass_AM and pass_EM:
        notes.append("all three paths agree -- bond-graph abstraction "
                     "verified for this driver at f_s")
        return notes
    if pass_AE and not pass_AM and not pass_EM:
        notes.append("A=E disagree with M -> mechanical model wrong "
                     "(clamp adds mass, effective Mms higher than spec, "
                     "or suspension nonlinearity at the measured amplitude)")
    elif pass_AM and not pass_AE and not pass_EM:
        notes.append("A=M disagree with E -> electrical model wrong "
                     "(Le shift, lead inductance, stray cap on probe, "
                     "or motor BL not as labelled)")
    elif pass_EM and not pass_AE and not pass_AM:
        notes.append("E=M disagree with A -> acoustic measurement wrong "
                     "(room mode, mic position, port loading, baseline "
                     "mismatch -- electrical+mechanical both saw f_s)")
    elif not (pass_AE or pass_AM or pass_EM):
        notes.append("none of the three pairs agree -> coupler itself "
                     "wrong: revisit BL force factor or Sd cone area "
                     "(the gyrator/transformer chain that links them)")
    if "fail" in (verdict_A, verdict_E, verdict_M):
        notes.append(f"individual paths: A={verdict_A}, E={verdict_E}, "
                     f"M={verdict_M} -- a self-failing path means its "
                     "own claim is unmet before cross-check even runs")
    return notes


def verify_cross_speaker(
    coupler_name,
    # acoustic side
    sweep_wav, acoustic_response_wav, acoustic_baseline_id=None,
    acoustic_search_band=(30, 4000),
    # electrical side
    electrical_impedance_csv=None,
    # mechanical side
    mechanical_vibration_csv=None,
):
    coupler = get_coupler(coupler_name)
    if coupler is None:
        raise KeyError(f"No coupler named '{coupler_name}' in overlay.")
    if electrical_impedance_csv is None:
        raise ValueError("electrical_impedance_csv required "
                         "(shunt-WAV path not yet implemented).")
    if mechanical_vibration_csv is None:
        raise ValueError("mechanical_vibration_csv required.")
    claims = _load_claims()
    coupler_scope = f"fab::coupler::speaker::{coupler_name}"
    cclaim = _find_coupler_claim(claims, coupler_scope)
    if cclaim is None:
        raise KeyError(f"No speaker coupler claim at {coupler_scope}")

    # ---- Path A: acoustic ----
    result_A = verify_sweep(
        sweep_wav, acoustic_response_wav,
        scope=coupler["acoustic_scope"],
        search_band=acoustic_search_band,
        baseline_id=acoustic_baseline_id,
    )
    # ---- Path E: electrical ----
    result_E = verify_electrical_csv(
        electrical_impedance_csv,
        scope=coupler["electrical_scope"],
    )
    # ---- Path M: mechanical ----
    result_M = verify_mechanical(
        mechanical_vibration_csv,
        scope=coupler["mechanical_scope"],
    )

    f_A = result_A["measured"]
    f_E = result_E["measured"]
    f_M = result_M["measured"]
    ag_AE = _pair_agreement(f_A, f_E)
    ag_AM = _pair_agreement(f_A, f_M)
    ag_EM = _pair_agreement(f_E, f_M)
    agreement_min = min(ag_AE, ag_AM, ag_EM)

    expected = cclaim["value"]
    tol      = cclaim.get("tol_frac", 0.05)
    verdict_cross = _verdict(agreement_min, expected, tol)

    rank = {"pass": 0, "drift": 1, "fail": 2}
    overall = max([result_A["verdict"], result_E["verdict"],
                   result_M["verdict"], verdict_cross],
                  key=lambda v: rank[v])

    notes = _triangulate(result_A["verdict"], result_E["verdict"],
                         result_M["verdict"],
                         ag_AE, ag_AM, ag_EM, expected, tol)

    result = {
        "scope":              coupler_scope,
        "method":             "cross_substrate_speaker_triple",
        "coupler":            coupler_name,
        "f_acoustic":         f_A,
        "f_electrical":       f_E,
        "f_mechanical":       f_M,
        "agreement_AE":       ag_AE,
        "agreement_AM":       ag_AM,
        "agreement_EM":       ag_EM,
        "agreement_min":      agreement_min,
        "expected_pct":       expected,
        "tol_frac":           tol,
        "verdict_acoustic":   result_A["verdict"],
        "verdict_electrical": result_E["verdict"],
        "verdict_mechanical": result_M["verdict"],
        "verdict_cross":      verdict_cross,
        "overall":            overall,
        "diagnostic":         notes,
        "linked_results": {
            "acoustic":   {k: result_A.get(k)
                           for k in ("measured", "q_factor", "verdict")
                           if k in result_A},
            "electrical": {k: result_E.get(k)
                           for k in ("measured", "q_factor", "verdict")
                           if k in result_E},
            "mechanical": {k: result_M.get(k)
                           for k in ("measured", "q_factor", "verdict")
                           if k in result_M},
        },
        "ts": time.time(),
    }
    _append_log(result)
    return result
