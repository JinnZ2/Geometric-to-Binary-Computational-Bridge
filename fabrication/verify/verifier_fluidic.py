"""
verifier_fluidic.py  (fabrication/verify/)

Steady-state hydraulic verifier.

  Predicted:   R_pred = ΔP / Q   (Hagen-Poiseuille from geometry)
  Measured:    slope of ΔP vs Q via OLS over CSV points
  Verdict:     pass/drift/fail against tol_frac band

Reynolds gate: each row checked; if Re > 2300 anywhere, that row
is excluded AND a warning is emitted. If all rows turbulent
-> bail with a clear message (laminar model invalid for the rig).

License: CC0. Stdlib only.
"""
import time
import math

from .csv_io import read_flow_csv
from .regression import ols
from .verifier import _load_claims, _verdict, _append_log


def _reynolds_row(rho, mu, Q_m3s, area_m2, diameter_m):
    if Q_m3s <= 0:
        return 0.0
    v = Q_m3s / area_m2
    return rho * v * diameter_m / mu


def _find_resistance_claim(claims, scope):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == "fluidic_resistance":
            return c
    return None


def verify_fluidic(csv_path, scope, fluid_rho, fluid_mu,
                   channel_radius_m):
    """
    csv_path         : CSV with time_s, dP_<unit>, Q_<unit>
    scope            : matches the steady-resistance claim
    fluid_rho, _mu   : density (kg/m³), viscosity (Pa·s)
    channel_radius_m : for Reynolds gating
    """
    data, meta = read_flow_csv(csv_path)
    dP = data["dP_Pa"]
    Q  = data["Q_m3s"]
    area = math.pi * channel_radius_m ** 2
    diam = 2 * channel_radius_m

    # Reynolds gate per row
    keep_dP, keep_Q, dropped = [], [], []
    Re_max = 0.0
    for i in range(len(dP)):
        Re = _reynolds_row(fluid_rho, fluid_mu, Q[i], area, diam)
        Re_max = max(Re_max, Re)
        if Re < 2300:
            keep_dP.append(dP[i])
            keep_Q.append(Q[i])
        else:
            dropped.append((i, Re))
    if len(keep_dP) < 3:
        raise RuntimeError(
            f"Only {len(keep_dP)} laminar points (Re_max={Re_max:.0f}). "
            "Reduce flow rate or use higher-viscosity fluid.")

    fit = ols(keep_Q, keep_dP)             # ΔP = R · Q
    R_meas = fit["slope"]
    R_ci   = fit["ci95"]

    claims = _load_claims()
    claim  = _find_resistance_claim(claims, scope)
    if claim is None:
        raise KeyError(f"No fluidic_resistance claim for scope={scope}")
    R_pred = claim["value"]
    tol    = claim.get("tol_frac", 0.10)
    verdict = _verdict(R_meas, R_pred, tol)

    notes = []
    ratio = R_meas / R_pred
    if ratio < 0.85:
        notes.append("R LOW: channel wider than modeled (over-etch, "
                     "soft wall bulging) OR fluid less viscous "
                     "(temp-corrected μ?)")
    if ratio > 1.15:
        notes.append("R HIGH: partial clog, bubble in line, OR fluid "
                     "more viscous than spec (cold glycerin)")
    if fit["r2"] < 0.95:
        notes.append(f"poor linearity (r²={fit['r2']:.3f}) -- "
                     "non-laminar entrance length, intermittent leak, "
                     "or air entrainment")
    if dropped:
        notes.append(f"dropped {len(dropped)} rows (Re ≥ 2300, "
                     f"max Re seen {Re_max:.0f})")
    if fit["intercept"] > 0.05 * max(dP):
        notes.append(f"non-zero intercept ({fit['intercept']:.1f} Pa) -- "
                     "minor losses (fittings, entrance) not modeled")

    measurement = {
        "scope":        scope,
        "claim_id":     claim.get("id"),
        "method":       "fluidic_steady_csv",
        "predicted_R":  R_pred,
        "measured_R":   R_meas,
        "ci95_R":       list(R_ci),
        "r2":           fit["r2"],
        "intercept":    fit["intercept"],
        "n_points":     fit["n"],
        "n_dropped_Re": len(dropped),
        "Re_max":       Re_max,
        "tol_frac":     tol,
        "verdict":      verdict,
        "diagnostic":   notes,
        "csv":          str(csv_path),
        "fluid":        {"rho": fluid_rho, "mu": fluid_mu},
        "ts":           time.time(),
    }
    _append_log(measurement)
    return measurement
