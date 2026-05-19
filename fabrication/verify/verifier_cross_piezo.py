"""
verifier_cross_piezo.py  (fabrication/verify/)

Cross-substrate verifier. Calls the acoustic and electrical
single-substrate verifiers on their own captures, then audits
whether the bond-graph prediction (same f₀ up to coupling shift)
holds.

The paste mentioned an electrical_shunt_wav path; the
corresponding function doesn't exist yet (deferred from the
electrical wedge), so this verifier only supports the
impedance-CSV path. The shunt-WAV branch is left as a TODO.

License: CC0. Stdlib only.
"""
import time

from .verifier import _load_claims, _verdict, _append_log
from .verifier_sweep import verify_sweep
from .verifier_electrical import verify_electrical_csv
from ..coupler_overlay import get_coupler


def _find_coupler_claim(claims, scope):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == "f0_agreement_pct":
            return c
    return None


def _agreement_pct(f_a, f_e):
    return 1.0 - 2.0 * abs(f_a - f_e) / (f_a + f_e)


def verify_cross_piezo(
    coupler_name,
    # acoustic side inputs
    sweep_wav, acoustic_response_wav, acoustic_baseline_id=None,
    acoustic_search_band=(50, 4000),
    # electrical side: impedance CSV (shunt-WAV TBD)
    electrical_impedance_csv=None,
):
    coupler = get_coupler(coupler_name)
    if coupler is None:
        raise KeyError(f"No coupler named '{coupler_name}' in overlay.")
    claims = _load_claims()
    coupler_scope = f"fab::coupler::piezo::{coupler_name}"
    cclaim = _find_coupler_claim(claims, coupler_scope)
    if cclaim is None:
        raise KeyError(f"No coupler claim at {coupler_scope}")

    # ---- Path A: acoustic ----
    result_A = verify_sweep(
        sweep_wav, acoustic_response_wav,
        scope=coupler["acoustic_scope"],
        search_band=acoustic_search_band,
        baseline_id=acoustic_baseline_id,
    )

    # ---- Path B: electrical ----
    if electrical_impedance_csv is None:
        raise ValueError("electrical_impedance_csv required "
                         "(shunt-WAV path not yet implemented).")
    result_B = verify_electrical_csv(
        electrical_impedance_csv,
        scope=coupler["electrical_scope"],
    )

    f_A = result_A["measured"]
    f_E = result_B["measured"]
    agreement = _agreement_pct(f_A, f_E)
    expected  = cclaim["value"]
    tol       = cclaim.get("tol_frac", 0.05)

    # cross verdict: how close to expected agreement
    verdict_cross = _verdict(agreement, expected, tol)
    # consolidated overall: worst of path A, path B, and cross
    rank = {"pass": 0, "drift": 1, "fail": 2}
    overall = max([result_A["verdict"], result_B["verdict"], verdict_cross],
                  key=lambda v: rank[v])

    notes = []
    if result_A["verdict"] == "pass" and result_B["verdict"] == "fail":
        notes.append("acoustic passes, electrical fails -> electrical path "
                     "has a leak (piezo bonding, shunt loading, or stray cap)")
    if result_A["verdict"] == "fail" and result_B["verdict"] == "pass":
        notes.append("electrical passes, acoustic fails -> acoustic path "
                     "has a leak (mic placement, baseline mismatch, "
                     "or room mode)")
    if (result_A["verdict"] in ("pass", "drift")
            and result_B["verdict"] in ("pass", "drift")
            and verdict_cross == "fail"):
        notes.append("both paths self-consistent but disagree -> coupler "
                     "model wrong: revisit k_eff² and η "
                     "(geometric coupling factor)")
    if (abs((f_A - f_E)/((f_A + f_E)/2)) < 0.01
            and verdict_cross == "pass"):
        notes.append("excellent cross-substrate agreement -- bond-graph "
                     "abstraction verified for this cavity at this f₀")

    result = {
        "scope":              coupler_scope,
        "method":             "cross_substrate_piezo",
        "coupler":            coupler_name,
        "f_acoustic":         f_A,
        "f_electrical":       f_E,
        "agreement_pct":      agreement,
        "expected_pct":       expected,
        "tol_frac":           tol,
        "verdict_acoustic":   result_A["verdict"],
        "verdict_electrical": result_B["verdict"],
        "verdict_cross":      verdict_cross,
        "overall":            overall,
        "diagnostic":         notes,
        "linked_results": {
            "acoustic":   {k: result_A.get(k)
                           for k in ("measured", "q_factor", "verdict")
                           if k in result_A},
            "electrical": {k: result_B.get(k)
                           for k in ("measured", "q_factor", "verdict")
                           if k in result_B},
        },
        "ts": time.time(),
    }
    _append_log(result)
    return result
