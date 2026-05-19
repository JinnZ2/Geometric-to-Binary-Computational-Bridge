"""
verifier_cross_solenoid.py  (fabrication/verify/)

Three measurement modes, each optional. Each yields BL:

  motor_csv:     I_amp, F_N      (blocked-coil F vs I)
  generator_csv: v_mps, V_volt   (open-circuit V vs v)
  impedance_csv: freq_Hz, Z_ohm  (swept AC, moving element installed)

At least one mode must be provided; two or more triangulate.
With all three, the pairwise BL agreements localize disagreement
to a specific physical sub-model.

License: CC0. Stdlib only.
"""
import csv as _csv
import math
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .regression import ols
from ..coupler_overlay import get_coupler


def _read_columns(path, required):
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    for k in required:
        if k not in headers:
            raise ValueError(f"CSV must contain {k}; got {headers}")
    cols = {k: headers.index(k) for k in required}
    out = {k: [] for k in cols}
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            for k, i in cols.items():
                out[k].append(float(r[i]))
        except ValueError:
            continue
    return out


def _agreement_pct(a, b):
    if a == 0 and b == 0:
        return 1.0
    if abs(a) + abs(b) == 0:
        return 0.0
    return 1.0 - 2.0 * abs(a - b) / (abs(a) + abs(b))


def _find(claims, scope, var):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == var:
            return c
    return None


def verify_cross_solenoid(
    coupler_name,
    motor_csv=None,
    generator_csv=None,
    impedance_csv=None,
    search_band=(0.5, 1000.0),
):
    coupler = get_coupler(coupler_name)
    if coupler is None:
        raise KeyError(f"No coupler named '{coupler_name}' in overlay.")
    if coupler["kind"] != "solenoid_gyrator":
        raise ValueError(f"Coupler '{coupler_name}' is not a solenoid.")

    claims = _load_claims()
    base = f"fab::coupler::solenoid::{coupler_name}"
    sub_results, sub_verdicts, notes = {}, {}, []
    BL_pred = coupler["BL_T_m"]
    BL_measurements = {}
    exp_default = coupler["expected_agreement_pct"]

    # ----- (1) MOTOR MODE: F vs I -----
    if motor_csv is not None:
        d = _read_columns(motor_csv, ("I_amp", "F_N"))
        fit = ols(d["I_amp"], d["F_N"])
        BL_motor = fit["slope"]
        agree = _agreement_pct(BL_motor, BL_pred)
        claim = _find(claims, f"{base}::BL_motor",
                      "BL_motor_agreement_pct")
        tol = claim.get("tol_frac", 0.08) if claim else 0.08
        exp = claim.get("value", exp_default) if claim else exp_default
        v_motor = _verdict(agree, exp, tol)
        sub_results["motor"] = {
            "BL_motor_measured": BL_motor,
            "BL_predicted":      BL_pred,
            "r2":                fit["r2"],
            "ci95":              fit["ci95"],
            "n_points":          fit["n"],
            "agreement_pct":     agree,
        }
        sub_verdicts["motor"] = v_motor
        BL_measurements["motor"] = BL_motor
        if v_motor != "pass":
            if BL_motor < BL_pred * 0.92:
                notes.append("BL_motor LOW -> coil partially out of "
                             "uniform field OR B lower than predicted")
            elif BL_motor > BL_pred * 1.08:
                notes.append("BL_motor HIGH -> wire length in field "
                             "longer than counted (extra turns OR "
                             "layer geometry mismatched)")
        if fit["r2"] < 0.97:
            notes.append(f"motor-mode r²={fit['r2']:.3f} below 0.97 "
                         "-> nonlinear F vs I; core saturation OR "
                         "sensor nonlinear")

    # ----- (2) GENERATOR MODE: V_open vs v -----
    if generator_csv is not None:
        d = _read_columns(generator_csv, ("v_mps", "V_volt"))
        fit = ols(d["v_mps"], d["V_volt"])
        BL_gen = fit["slope"]
        agree = _agreement_pct(BL_gen, BL_pred)
        claim = _find(claims, f"{base}::BL_generator",
                      "BL_generator_agreement_pct")
        tol = claim.get("tol_frac", 0.08) if claim else 0.08
        exp = claim.get("value", exp_default) if claim else exp_default
        v_gen = _verdict(agree, exp, tol)
        sub_results["generator"] = {
            "BL_generator_measured": BL_gen,
            "BL_predicted":          BL_pred,
            "r2":                    fit["r2"],
            "ci95":                  fit["ci95"],
            "n_points":              fit["n"],
            "agreement_pct":         agree,
        }
        sub_verdicts["generator"] = v_gen
        BL_measurements["generator"] = BL_gen
        if v_gen != "pass" and fit["r2"] < 0.97:
            notes.append(f"generator-mode r²={fit['r2']:.3f} -> V "
                         "rises nonlinearly with v; self-capacitance "
                         "OR coil moving out of field at amplitude")

    # ----- (3) IMPEDANCE-AT-RESONANCE -----
    if impedance_csv is not None and coupler.get("Z_peak_predicted_ohm"):
        d = _read_columns(impedance_csv, ("freq_Hz", "Z_ohm"))
        fL, fH = search_band
        band = [(f, z) for f, z in zip(d["freq_Hz"], d["Z_ohm"])
                if fL <= f <= fH]
        if not band:
            raise RuntimeError(f"No impedance rows in band {search_band}.")
        f_peak, Z_peak = max(band, key=lambda kv: kv[1])
        Re = coupler["Re_coil_ohm"]
        Rms = coupler.get("Rms_Nsm")
        if Rms is None or Rms <= 0:
            raise RuntimeError("Coupler has no Rms; cannot derive BL "
                               "from Z.")
        if Z_peak <= Re:
            raise RuntimeError(
                f"Z_peak={Z_peak:.3f} not greater than Re={Re:.3f}; "
                "verify shunt-resistor sizing and DUT placement.")
        BL_imp = math.sqrt((Z_peak - Re) * Rms)
        agree_BL = _agreement_pct(BL_imp, BL_pred)
        f0_pred = coupler.get("f0_mech_Hz")
        agree_f0 = _agreement_pct(f_peak, f0_pred) if f0_pred else None
        claim = _find(claims, f"{base}::BL_impedance",
                      "BL_impedance_agreement_pct")
        tol = claim.get("tol_frac", 0.10) if claim else 0.10
        exp = claim.get("value", exp_default) if claim else exp_default
        v_imp = _verdict(agree_BL, exp, tol)
        sub_results["impedance"] = {
            "Z_peak_measured":    Z_peak,
            "Z_peak_predicted":   coupler["Z_peak_predicted_ohm"],
            "f_peak_measured_Hz": f_peak,
            "f0_mech_predicted":  f0_pred,
            "BL_back_derived":    BL_imp,
            "BL_predicted":       BL_pred,
            "agreement_BL_pct":   agree_BL,
            "agreement_f0_pct":   agree_f0,
        }
        sub_verdicts["impedance"] = v_imp
        BL_measurements["impedance"] = BL_imp
        if v_imp != "pass":
            if (f0_pred and agree_f0 is not None
                    and abs(f_peak / f0_pred - 1) > 0.05):
                notes.append(f"f_peak={f_peak:.2f} Hz vs predicted "
                             f"{f0_pred:.2f} Hz -> m or k off "
                             "(mechanical IR)")
            else:
                notes.append("Z_peak off but f₀ ok -> BL OR Rms "
                             "wrong; if BL_motor and BL_generator "
                             "agree, this implicates Rms")

    if not sub_results:
        raise RuntimeError("Provide at least one of motor_csv / "
                           "generator_csv / impedance_csv.")

    # ---- triangulation across measured BLs ----
    if len(BL_measurements) >= 2:
        pairs = []
        keys = list(BL_measurements.keys())
        for i in range(len(keys)):
            for j in range(i + 1, len(keys)):
                a = BL_measurements[keys[i]]
                b = BL_measurements[keys[j]]
                pairs.append((f"{keys[i]}~{keys[j]}",
                              _agreement_pct(a, b)))
        worst_pair, worst_agree = min(pairs, key=lambda kv: kv[1])
        sub_results["pairwise_BL"] = dict(pairs)
        if worst_agree < 0.95:
            if worst_pair == "motor~generator":
                notes.append("BL_motor vs BL_generator differ -> "
                             "magnetic hysteresis OR coil partially "
                             "outside uniform-field region (different "
                             "effective field in static vs dynamic)")
            elif "impedance" in worst_pair:
                other = (worst_pair.replace("~impedance", "")
                                   .replace("impedance~", ""))
                notes.append(f"impedance-derived BL disagrees with "
                             f"{other} -> mechanical-side model has "
                             "wrong Rms or m·k product")
        elif (worst_agree >= 0.97
                and all(v == "pass" for v in sub_verdicts.values())):
            notes.append("multi-mode agreement: BL verified across "
                         "motor, generator, and resonance paths -- "
                         "bond-graph magnetic-mechanical edge proven "
                         "for this solenoid")

    rank = {"pass": 0, "drift": 1, "fail": 2}
    overall = max(sub_verdicts.values(), key=lambda v: rank[v])

    result = {
        "scope":             base,
        "method":            "cross_substrate_solenoid",
        "coupler":           coupler_name,
        "BL_predicted_T_m":  BL_pred,
        "BL_measurements":   BL_measurements,
        "sub_results":       sub_results,
        "sub_verdicts":      sub_verdicts,
        "overall":           overall,
        "diagnostic":        notes,
        "ts":                time.time(),
    }
    _append_log(result)
    return result
