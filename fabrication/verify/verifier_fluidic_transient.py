"""
verifier_fluidic_transient.py  (fabrication/verify/)

Step-response verifier for fluidic dynamics.

CSV format reused from csv_io.read_flow_csv (time_s, dP_<unit>,
Q_<unit>). The verifier classifies the response as first-order
(no overshoot) or second-order (overshoot ≥ 5%) and fits the
corresponding model.

License: CC0. Stdlib only.
"""
import time

from .verifier import _load_claims, _verdict, _append_log
from .csv_io import read_flow_csv
from .transient_fit import fit_first_order, fit_second_order


def _classify_regime(t, y):
    """Detect if overshoot present -> second-order; else first-order."""
    if len(y) < 10:
        return "first"
    final = sum(y[-5:]) / 5.0
    initial = y[0]
    span = final - initial
    if abs(span) < 1e-12:
        return "first"
    peak = max(y) if span > 0 else min(y)
    overshoot = (peak - final) / span if span > 0 else (final - peak)/abs(span)
    return "second" if overshoot > 0.05 else "first"


def _find_dyn_claim(claims, scope, rate_var):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == rate_var:
            return c
    return None


def verify_fluidic_transient(csv_path, scope):
    """
    Reads transient CSV. Accepts either dP_<unit> or Q_<unit> as the
    response variable -- whichever has nonzero values.
    """
    data, meta = read_flow_csv(csv_path)
    t = data["time_s"]
    y = data["dP_Pa"] if max(data["dP_Pa"]) > 0 else data["Q_m3s"]

    regime = _classify_regime(t, y)
    claims = _load_claims()

    if regime == "first":
        fit = fit_first_order(t, y)
        tau_meas = fit["tau"]
        claim = _find_dyn_claim(claims, scope, "tau_RC_s")
        if claim is None:
            raise KeyError(f"No tau_RC claim at scope={scope}")
        tau_pred = claim["value"]
        tol = claim.get("tol_frac", 0.15)
        verdict = _verdict(tau_meas, tau_pred, tol)
        notes = _diag_first(fit, tau_meas, tau_pred)
        result = {
            "scope":         scope,
            "method":        "fluidic_transient_first_order",
            "regime":        "first",
            "predicted_tau": tau_pred,
            "measured_tau":  tau_meas,
            "r2":            fit["r2"],
            "verdict":       verdict,
            "tol_frac":      tol,
            "diagnostic":    notes,
            "csv":           str(csv_path),
            "ts":            time.time(),
        }
    else:
        fit = fit_second_order(t, y)
        wn_meas, z_meas = fit["wn"], fit["zeta"]
        c_wn = _find_dyn_claim(claims, scope, "omega_n_rad_s")
        c_z  = _find_dyn_claim(claims, scope, "damping_ratio")
        if c_wn is None or c_z is None:
            raise KeyError(f"Missing ωn or ζ claim at scope={scope}")
        v_wn = _verdict(wn_meas, c_wn["value"], c_wn.get("tol_frac", 0.15))
        v_z  = _verdict(z_meas,  c_z["value"],  c_z.get("tol_frac", 0.20))
        # overall = worse of the two
        rank = {"pass": 0, "drift": 1, "fail": 2}
        verdict = max([v_wn, v_z], key=lambda v: rank[v])
        notes = _diag_second(fit, wn_meas, z_meas,
                             c_wn["value"], c_z["value"])
        result = {
            "scope":          scope,
            "method":         "fluidic_transient_second_order",
            "regime":         "second",
            "predicted_wn":   c_wn["value"],
            "measured_wn":    wn_meas,
            "predicted_zeta": c_z["value"],
            "measured_zeta":  z_meas,
            "r2":             fit["r2"],
            "verdict":        verdict,
            "diagnostic":     notes,
            "csv":            str(csv_path),
            "ts":             time.time(),
        }
    _append_log(result)
    return result


def _diag_first(fit, tau_m, tau_p):
    out = []
    if fit["r2"] < 0.95:
        out.append(f"poor fit r²={fit['r2']:.3f} -- multiple time "
                   "constants present (second tank, parasitic compliance)")
    ratio = tau_m / tau_p
    if ratio < 0.85:
        out.append("τ LOW: less compliance (rigid wall, no air pocket) "
                   "OR less resistance (wider/smoother channel)")
    if ratio > 1.15:
        out.append("τ HIGH: extra compliance (soft tubing, trapped bubble) "
                   "OR partial blockage")
    return out


def _diag_second(fit, wn_m, z_m, wn_p, z_p):
    out = []
    if fit["r2"] < 0.92:
        out.append(f"poor fit r²={fit['r2']:.3f} -- system order > 2, "
                   "nonlinear element, or measurement noise")
    if abs(wn_m/wn_p - 1) > 0.15:
        out.append("ωn off: inertance (ρℓ/A) or compliance miscalibrated "
                   "-- check tube length and stored-gas volume")
    if abs(z_m - z_p) > 0.10:
        out.append("ζ off: resistance model wrong -- laminar/turbulent "
                   "regime change, viscous loss at fittings")
    return out
