"""
verifier_cross_heater.py  (fabrication/verify/)

Two-path cross verifier for a resistor heater.

  Path E (electrical):
    - V, I CSV (multimeter logger)
    - take medians across steady-state samples
    - P_meas = V·I,  R_meas = V/I

  Path T (thermal):
    - run verify_thermal on the heating CSV
    - get τ_meas and ΔT_ss_meas

  Cross-check:
    - back-derive R_th from path-T measurements
      R_th_back = ΔT_ss / P_meas
    - compare to R_th from geometric thermal IR
    - the joint behavior of (ΔT_ss, τ, R_th_back) localizes the leak

The coupling ratio is exactly 1.0 by physics, so this verifier
has the strongest diagnostic power of any in the framework: every
mismatch maps to a concrete failure mode rather than to "coupler
model uncertainty".

License: CC0. Stdlib only.
"""
import csv as _csv
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .verifier_thermal import verify_thermal
from ..coupler_overlay import get_coupler


def _read_VI_csv(path):
    """Strict columns: V_volt, I_amp (plus optional time_s)."""
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    if "V_volt" not in headers or "I_amp" not in headers:
        raise ValueError("CSV must contain V_volt, I_amp columns.")
    iV, iI = headers.index("V_volt"), headers.index("I_amp")
    V, I = [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            V.append(float(r[iV]))
            I.append(float(r[iI]))
        except ValueError:
            continue
    if not V:
        raise RuntimeError(f"No usable V,I rows in {path}.")
    return V, I


def _find(claims, scope, var):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == var:
            return c
    return None


def _agreement_pct(a, b):
    if a == 0 and b == 0:
        return 1.0
    if a + b == 0:
        return 0.0
    return 1.0 - 2.0 * abs(a - b) / abs(a + b)


def _to_K(v, unit):
    if unit == "K":
        return v
    if unit == "degC":
        return v + 273.15
    if unit == "degF":
        return (v - 32.0) * 5.0 / 9.0 + 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def _extract_dT_ss(csv_path, mode):
    """Quick ΔT_ss extraction without re-fitting.
    For mode='heating', returns T_final - T_initial (positive).
    For mode='cooling', returns T_initial - T_final (positive)."""
    rows = list(_csv.reader(Path(csv_path).open()))
    headers = rows[0]
    if "time_s" not in headers:
        raise ValueError("thermal CSV must have time_s column.")
    T_col = next((h for h in headers if h.startswith("T_")), None)
    if T_col is None:
        raise ValueError("thermal CSV must have a T_<unit> column.")
    unit = T_col.split("_", 1)[1]
    i_T = headers.index(T_col)
    T_series = []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            T_series.append(_to_K(float(r[i_T]), unit))
        except ValueError:
            continue
    if not T_series:
        raise RuntimeError("No T data in CSV.")
    T0 = T_series[0]
    tail = T_series[-min(5, len(T_series)):]
    T_ss = sum(tail) / len(tail)
    return abs(T_ss - T0)


def verify_cross_heater(
    coupler_name,
    VI_csv,
    thermal_csv,
    thermal_mode="heating",
):
    coupler = get_coupler(coupler_name)
    if coupler is None:
        raise KeyError(f"No coupler named '{coupler_name}' in overlay.")
    if coupler["kind"] != "resistor_heater":
        raise ValueError(f"Coupler '{coupler_name}' is not a "
                         "resistor_heater.")

    claims = _load_claims()
    coupler_scope = f"fab::coupler::heater::{coupler_name}"
    cclaim = _find(claims, coupler_scope, "joule_heating_agreement_pct")
    if cclaim is None:
        raise KeyError(f"No heater coupler claim at {coupler_scope}")

    # ---- Path E: electrical ----
    V_list, I_list = _read_VI_csv(VI_csv)
    V_sorted, I_sorted = sorted(V_list), sorted(I_list)
    V_med = V_sorted[len(V_sorted) // 2]
    I_med = I_sorted[len(I_sorted) // 2]
    P_meas = V_med * I_med
    R_meas = V_med / I_med if I_med != 0 else float("inf")
    P_pred = coupler["P_elec_W"]
    R_pred = coupler["R_elec_ohm"]
    v_P = _verdict(P_meas, P_pred, 0.05)
    v_R = _verdict(R_meas, R_pred, 0.05)

    # ---- Path T: thermal ----
    thermal_result = verify_thermal(
        thermal_csv,
        scope_prefix=coupler["thermal_scope"],
        mode=thermal_mode,
    )
    tau_meas = thermal_result["measured_tau"]
    dT_meas  = _extract_dT_ss(thermal_csv, mode=thermal_mode)

    dT_pred  = coupler["delta_T_ss_K"]
    tau_pred = coupler["tau_th_s"]
    agree_dT  = _agreement_pct(dT_meas,  dT_pred)
    agree_tau = _agreement_pct(tau_meas, tau_pred)

    expected = cclaim["value"]
    tol      = cclaim.get("tol_frac", 0.05)
    v_dT  = _verdict(agree_dT,  expected, tol)
    v_tau = _verdict(agree_tau, expected, tol)

    # ---- back-derived R_th from path-T over path-E ----
    R_th_back = dT_meas / P_meas if P_meas > 0 else float("inf")
    R_th_pred = coupler["R_th_K_per_W"]
    v_Rth = _verdict(R_th_back, R_th_pred, 0.10)

    # ---- localized diagnostics ----
    notes = []
    if v_P == "fail":
        notes.append(f"P_meas={P_meas:.3f} W vs predicted {P_pred:.3f} W "
                     "-- supply not delivering rated voltage, lead "
                     "loss, OR resistor drifted (TCR)")
    if v_R == "fail":
        notes.append(f"R_meas={R_meas:.3f} Ω vs predicted {R_pred:.3f} Ω "
                     "-- measured at operating temperature; thermal "
                     "coefficient of resistance may explain")
    if v_dT == "pass" and v_tau == "fail":
        notes.append("ΔT_ss agrees but τ off -> C_th wrong "
                     "(thermal mass mis-specified, mounting added mass)")
    if v_tau == "pass" and v_dT == "fail":
        notes.append("τ agrees but ΔT_ss off -> R_th wrong "
                     "(extra convection path OR radiation underweighted)")
    if v_dT == "fail" and v_tau == "fail":
        notes.append("both ΔT_ss and τ off -> check ambient drift OR "
                     "supply regulation; if R_th_back matches "
                     "R_th_predicted, the leak is in the ELECTRICAL "
                     "side (P measurement)")
    if v_Rth == "pass" and (v_dT == "fail" or v_tau == "fail"):
        notes.append("back-derived R_th matches geometric prediction "
                     "-> thermal model is self-consistent; the leak "
                     "is in the ELECTRICAL side (P measurement)")
    if (v_P == "pass" and v_R == "pass" and v_dT == "pass"
            and v_tau == "pass" and v_Rth == "pass"):
        notes.append("all five sub-checks pass -- Joule-heating "
                     "coupler verified end to end; no leak detected")

    rank = {"pass": 0, "drift": 1, "fail": 2}
    sub_verdicts = {
        "P_elec":               v_P,
        "R_elec":               v_R,
        "delta_T_ss":           v_dT,
        "tau_th":               v_tau,
        "R_th_back_derived":    v_Rth,
        "thermal_overall":      thermal_result["overall"],
    }
    overall = max(sub_verdicts.values(), key=lambda v: rank[v])

    result = {
        "scope":                       coupler_scope,
        "method":                      "cross_substrate_resistor_heater",
        "coupler":                     coupler_name,
        "P_measured_W":                P_meas,
        "P_predicted_W":               P_pred,
        "R_measured_ohm":              R_meas,
        "R_predicted_ohm":             R_pred,
        "delta_T_ss_measured_K":       dT_meas,
        "delta_T_ss_predicted_K":      dT_pred,
        "tau_th_measured_s":           tau_meas,
        "tau_th_predicted_s":          tau_pred,
        "R_th_back_derived_K_per_W":   R_th_back,
        "R_th_predicted_K_per_W":      R_th_pred,
        "agreement_delta_T_pct":       agree_dT,
        "agreement_tau_pct":           agree_tau,
        "expected_pct":                expected,
        "tol_frac":                    tol,
        "sub_verdicts":                sub_verdicts,
        "overall":                     overall,
        "diagnostic":                  notes,
        "ts":                          time.time(),
    }
    _append_log(result)
    return result
