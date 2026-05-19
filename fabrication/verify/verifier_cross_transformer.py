"""
verifier_cross_transformer.py  (fabrication/verify/)

Multi-path cross-verifier for a transformer coupler. Each
measurement CSV is OPTIONAL; the verifier runs whatever is
provided and triangulates from the pattern of pass/fail.

  voltage_csv     V1_volt, V2_volt
                  Open-circuit secondary; measured V₂/V₁ vs n.

  current_csv     I1_amp, I2_amp
                  Short-circuit secondary; measured I₁/I₂ vs n
                  (ampere-turns balance).

  inductance_csv  freq_Hz, Z1_ohm, phase1_deg, Z2_ohm, phase2_deg
                  Paired LCR sweep; measured L₁/L₂ vs (N₁/N₂)².

  loaded_csv      V1_volt, I1_amp, V2_volt, I2_amp
                  Loaded mode; back-derive coupling k and check
                  efficiency.

License: CC0. Stdlib only.
"""
import csv as _csv
import math
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from ..coupler_overlay import get_coupler


def _read_columns(path, required, optional=()):
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    for k in required:
        if k not in headers:
            raise ValueError(f"CSV must contain {k}; got {headers}")
    cols = {k: headers.index(k)
            for k in list(required) + list(optional) if k in headers}
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


def _median(xs):
    s = sorted(xs)
    return s[len(s) // 2] if s else 0.0


def _agreement_pct(measured, predicted):
    if measured == 0 and predicted == 0:
        return 1.0
    if abs(measured) + abs(predicted) == 0:
        return 0.0
    return (1.0 - 2.0 * abs(measured - predicted)
            / (abs(measured) + abs(predicted)))


def _extract_L(freqs, mags, phases_deg):
    Ls = []
    for f, z, p in zip(freqs, mags, phases_deg):
        if f <= 0:
            continue
        X = z * math.sin(math.radians(p))
        if X <= 0:
            continue
        Ls.append(X / (2 * math.pi * f))
    if not Ls:
        raise RuntimeError("No inductive points in CSV.")
    Ls.sort()
    return Ls[len(Ls) // 2]


def _find(claims, scope, var):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == var:
            return c
    return None


def verify_cross_transformer(
    coupler_name,
    voltage_csv=None,
    current_csv=None,
    inductance_csv=None,
    loaded_csv=None,
):
    coupler = get_coupler(coupler_name)
    if coupler is None:
        raise KeyError(f"No coupler named '{coupler_name}' in overlay.")
    if coupler["kind"] != "transformer_gyrator":
        raise ValueError(f"Coupler '{coupler_name}' is not a "
                         "transformer.")

    claims = _load_claims()
    base = f"fab::coupler::transformer::{coupler_name}"
    sub_results, sub_verdicts, notes = {}, {}, []
    n_pred = coupler["n_ratio"]
    exp_default = coupler["expected_agreement_pct"]

    # ---- (1) open-circuit voltage ratio ----
    if voltage_csv is not None:
        d = _read_columns(voltage_csv, ("V1_volt", "V2_volt"))
        V1 = _median(d["V1_volt"])
        V2 = _median(d["V2_volt"])
        v_ratio_meas = (V2 / V1) if V1 != 0 else float("inf")
        agree = _agreement_pct(v_ratio_meas, n_pred)
        claim = _find(claims, f"{base}::n_oc",
                      "turns_ratio_agreement_pct")
        tol = claim.get("tol_frac", 0.03) if claim else 0.03
        exp = claim.get("value", exp_default) if claim else exp_default
        v_n_oc = _verdict(agree, exp, tol)
        sub_results["n_oc"] = {
            "V1_med": V1, "V2_med": V2,
            "V2_over_V1_measured": v_ratio_meas,
            "n_predicted": n_pred,
            "agreement_pct": agree,
        }
        sub_verdicts["n_oc"] = v_n_oc
        if v_n_oc != "pass":
            if v_ratio_meas < n_pred * 0.97:
                notes.append("V₂/V₁ low -> coupling k below assumed, OR "
                             "miscounted secondary turns (low by integer "
                             "count), OR core saturation at drive level")
            else:
                notes.append("V₂/V₁ high -> capacitive coupling at this f "
                             "(lower drive frequency), OR miscounted "
                             "primary turns (low by integer)")

    # ---- (2) short-circuit current ratio (I₁/I₂ = n) ----
    if current_csv is not None:
        d = _read_columns(current_csv, ("I1_amp", "I2_amp"))
        I1 = _median(d["I1_amp"])
        I2 = _median(d["I2_amp"])
        i_ratio_meas = (I1 / I2) if I2 != 0 else float("inf")
        agree = _agreement_pct(i_ratio_meas, n_pred)
        claim = _find(claims, f"{base}::n_sc",
                      "current_ratio_agreement_pct")
        tol = claim.get("tol_frac", 0.05) if claim else 0.05
        exp = claim.get("value", exp_default) if claim else exp_default
        v_n_sc = _verdict(agree, exp, tol)
        sub_results["n_sc"] = {
            "I1_med": I1, "I2_med": I2,
            "I1_over_I2_measured": i_ratio_meas,
            "n_predicted": n_pred,
            "agreement_pct": agree,
        }
        sub_verdicts["n_sc"] = v_n_sc
        if v_n_sc != "pass":
            notes.append("I₁/I₂ off -> leakage inductance limits SC "
                         "current (use lower f), OR lead resistance "
                         "dominates (move sense to a known shunt)")

    # ---- (3) paired LCR -> L₁/L₂ vs (N₁/N₂)² ----
    if inductance_csv is not None:
        d = _read_columns(
            inductance_csv,
            ("freq_Hz", "Z1_ohm", "phase1_deg",
             "Z2_ohm", "phase2_deg"),
        )
        L1_meas = _extract_L(d["freq_Hz"], d["Z1_ohm"], d["phase1_deg"])
        L2_meas = _extract_L(d["freq_Hz"], d["Z2_ohm"], d["phase2_deg"])
        ratio_meas = L1_meas / L2_meas if L2_meas > 0 else float("inf")
        ratio_pred = coupler["L_ratio_predicted"]
        agree = _agreement_pct(ratio_meas, ratio_pred)
        claim = _find(claims, f"{base}::L_ratio",
                      "inductance_ratio_agreement_pct")
        tol = claim.get("tol_frac", 0.05) if claim else 0.05
        exp = claim.get("value", exp_default) if claim else exp_default
        v_L = _verdict(agree, exp, tol)
        sub_results["L_ratio"] = {
            "L1_measured_H": L1_meas, "L2_measured_H": L2_meas,
            "L_ratio_measured": ratio_meas,
            "L_ratio_predicted": ratio_pred,
            "agreement_pct": agree,
        }
        sub_verdicts["L_ratio"] = v_L
        if v_L != "pass":
            L1_pred = coupler["L1_H"]
            L2_pred = coupler["L2_H"]
            d1 = abs(L1_meas / L1_pred - 1.0)
            d2 = abs(L2_meas / L2_pred - 1.0)
            if d1 > 0.10 and d2 < 0.05:
                notes.append("L₁ off but L₂ ok -> primary winding "
                             "count or dispersion problem")
            elif d2 > 0.10 and d1 < 0.05:
                notes.append("L₂ off but L₁ ok -> secondary winding "
                             "count or dispersion problem")
            else:
                notes.append("both L₁ and L₂ off -> core ℛ wrong "
                             "(μ_r at drive level, gap mismeasured, "
                             "or fringing flux)")

    # ---- (4) loaded mode: back-derive coupling k + efficiency ----
    if loaded_csv is not None:
        d = _read_columns(
            loaded_csv,
            ("V1_volt", "I1_amp", "V2_volt", "I2_amp"),
        )
        V1 = _median(d["V1_volt"])
        I1 = _median(d["I1_amp"])
        V2 = _median(d["V2_volt"])
        I2 = _median(d["I2_amp"])
        # V₂ ≈ V₁·n·k·(R_load/(R_load + R_sec_lead)); ignoring
        # the lead-loss term, k_back ≈ (V₂/V₁) / n.
        if V1 > 0 and n_pred > 0:
            k_back = (V2 / V1) / n_pred
        else:
            k_back = 0.0
        k_assumed = coupler["coupling_factor_k"]
        P1 = V1 * I1
        P2 = V2 * I2
        eff = (P2 / P1) if P1 > 0 else 0.0
        v_loaded = _verdict(k_back, k_assumed, 0.05)
        sub_results["loaded"] = {
            "V1_med": V1, "I1_med": I1,
            "V2_med": V2, "I2_med": I2,
            "P_primary_W":   P1,
            "P_secondary_W": P2,
            "efficiency":    eff,
            "k_back_derived": k_back,
            "k_assumed":      k_assumed,
        }
        sub_verdicts["loaded_k"] = v_loaded
        if v_loaded != "pass":
            if k_back < k_assumed * 0.90:
                notes.append("derived k < assumed -> leakage flux higher "
                             "than the coupler's default; recompute "
                             "leakage_factor for this geometry")
            elif k_back > 1.0:
                notes.append("derived k > 1 -> measurement error (scope "
                             "probe attenuation, calibration, OR "
                             "secondary V measured open-circuit instead "
                             "of loaded)")

    # ---- overall verdict + result assembly ----
    if not sub_verdicts:
        raise RuntimeError(
            "No measurement CSVs provided; supply at least one of "
            "voltage_csv, current_csv, inductance_csv, loaded_csv.")
    rank = {"pass": 0, "drift": 1, "fail": 2}
    overall = max(sub_verdicts.values(), key=lambda v: rank[v])
    if all(v == "pass" for v in sub_verdicts.values()):
        notes.append("all provided checks pass -- transformer model "
                     "verified at this drive level and frequency")

    result = {
        "scope":                  base,
        "method":                 "cross_substrate_transformer",
        "coupler":                coupler_name,
        "n_predicted":            n_pred,
        "L_ratio_predicted":      coupler["L_ratio_predicted"],
        "expected_agreement_pct": exp_default,
        "sub_results":            sub_results,
        "sub_verdicts":           sub_verdicts,
        "overall":                overall,
        "diagnostic":             notes,
        "ts":                     time.time(),
    }
    _append_log(result)
    return result
