"""
verifier_thermal.py  (fabrication/verify/)

Two measurement paths, both CSV-driven:

  (a) heating: time_s, T_<unit>     -- step heat input ON
      fit τ from first-order rise + steady-state ΔT

  (b) cooling: time_s, T_<unit>     -- step heat input OFF
      fit τ from exponential decay toward ambient
      (uses the same fit_first_order machinery: a decay
      y(t) = A·(1 - e^{-t/τ}) + b fits identically with A < 0)

Temperature unit handling (strict suffix, converted to K):
    T_K, T_degC, T_degF

License: CC0. Stdlib only.
"""
import csv as _csv
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .transient_fit import fit_first_order


def _to_K(v, unit):
    if unit == "K":
        return v
    if unit == "degC":
        return v + 273.15
    if unit == "degF":
        return (v - 32.0) * 5.0 / 9.0 + 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def _read_thermal_csv(path):
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    if "time_s" not in headers:
        raise ValueError("CSV must contain time_s column.")
    T_col = next((h for h in headers if h.startswith("T_")), None)
    if T_col is None:
        raise ValueError("CSV must contain a T_<unit> column "
                         "(T_K, T_degC, T_degF).")
    unit = T_col.split("_", 1)[1]
    t_idx, T_idx = headers.index("time_s"), headers.index(T_col)
    t, T = [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            t.append(float(r[t_idx]))
            T.append(_to_K(float(r[T_idx]), unit))
        except ValueError:
            continue
    if len(t) < 10:
        raise ValueError(f"Too few samples in {path}: {len(t)}")
    return t, T, unit


def verify_thermal(csv_path, scope_prefix, mode="heating"):
    """
    mode = "heating" -> y(t) = T₀ + ΔT·(1 - e^{-t/τ})
    mode = "cooling" -> y(t) = T_amb + (T₀ - T_amb)·e^{-t/τ}
                       (fit_first_order accepts this with A < 0)
    """
    if mode not in ("heating", "cooling"):
        raise ValueError("mode must be 'heating' or 'cooling'.")
    t, T, unit = _read_thermal_csv(csv_path)

    fit = fit_first_order(t, T)
    tau_meas = abs(fit["tau"])

    claims = _load_claims()
    tau_claim = next((c for c in claims
                      if c.get("scope") == f"{scope_prefix}::dyn"
                      and c.get("rate_var") == "tau_thermal_s"), None)
    if tau_claim is None:
        raise KeyError(f"No τ_thermal claim at {scope_prefix}::dyn")
    tau_pred = tau_claim["value"]
    tol      = tau_claim.get("tol_frac", 0.15)
    v_tau    = _verdict(tau_meas, tau_pred, tol)

    notes = []
    ratio = tau_meas / tau_pred
    if ratio < 0.85:
        notes.append("τ LOW: extra heat-loss path (radiation, "
                     "air convection, cable conduction) OR less "
                     "thermal mass than modeled")
    if ratio > 1.15:
        notes.append("τ HIGH: thermal interface resistance (paste, "
                     "air gap) OR ambient drifting during test")
    if fit["r2"] < 0.95:
        notes.append(f"poor fit r²={fit['r2']:.3f} -- multiple time "
                     "constants (lumped model missing a node)")

    # steady-state ΔT verdict (heating mode only)
    ss_claim = next((c for c in claims
                     if c.get("scope") == f"{scope_prefix}::steady"
                     and c.get("rate_var") == "delta_T_steady_K"), None)
    v_ss = None
    dT_meas = None
    if ss_claim and mode == "heating":
        dT_meas = T[-1] - T[0]
        v_ss = _verdict(dT_meas, ss_claim["value"],
                        ss_claim.get("tol_frac", 0.15))
        if v_ss != "pass":
            notes.append(f"steady ΔT {dT_meas:.2f} K vs predicted "
                         f"{ss_claim['value']:.2f} K -- heat-loss "
                         "path or power-delivery mismatch")

    rank = {"pass": 0, "drift": 1, "fail": 2}
    parts = [v_tau] + ([v_ss] if v_ss else [])
    overall = max(parts, key=lambda v: rank[v])

    result = {
        "scope_prefix":   scope_prefix,
        "method":         f"thermal_{mode}_csv",
        "predicted_tau":  tau_pred,
        "measured_tau":   tau_meas,
        "r2":             fit["r2"],
        "verdict_tau":    v_tau,
        "predicted_dT":   ss_claim["value"] if ss_claim else None,
        "measured_dT":    dT_meas,
        "verdict_steady": v_ss,
        "verdict":        overall,
        "overall":        overall,
        "measured":       tau_meas,
        "diagnostic":     notes,
        "csv":            str(csv_path),
        "unit":           unit,
        "ts":             time.time(),
    }
    _append_log(result)
    return result
