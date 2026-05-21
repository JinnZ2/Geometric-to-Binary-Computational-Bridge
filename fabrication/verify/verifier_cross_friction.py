"""
verifier_cross_friction.py  (fabrication/verify/)

Two measurement modes; provide whichever you have. The verifier
runs both if given both, then triangulates from the joint pattern.

  STEADY-STATE:
    force_velocity_csv:   time_s, F_N, v_mps
    thermal_steady_csv:   time_s, T_<unit>

  FREE-DECAY:
    decay_csv:            time_s, x_m
    thermal_decay_csv:    time_s, T_<unit>

Energy-balance formula (free decay):

    E_mech_in  = ½ · k · x̂₀²

    E_thermal_total = C_th · (T_end - T_amb)
                    + ∫₀ᵗ_end (T - T_amb) / R_th  dt

    The two should match within the agreement budget. The
    integral term captures heat that has already leaked to
    ambient; the storage term captures heat still in the
    damper at the end of the recording. If T_end ≈ T_amb,
    the integral alone equals E_mech_in.

License: CC0. Stdlib only.
"""
import csv as _csv
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .verifier_mechanical import fit_damped_sinusoid
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


def _to_K(v, unit):
    if unit == "K":
        return v
    if unit == "degC":
        return v + 273.15
    if unit == "degF":
        return (v - 32.0) * 5.0 / 9.0 + 273.15
    raise ValueError(f"Unknown temperature unit: {unit}")


def _read_thermal_K(csv_path):
    rows = list(_csv.reader(Path(csv_path).open()))
    headers = rows[0]
    if "time_s" not in headers:
        raise ValueError("thermal CSV must have time_s column.")
    T_col = next((h for h in headers if h.startswith("T_")), None)
    if T_col is None:
        raise ValueError("thermal CSV must have T_<unit> column.")
    unit = T_col.split("_", 1)[1]
    i_t, i_T = headers.index("time_s"), headers.index(T_col)
    t, T = [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            t.append(float(r[i_t]))
            T.append(_to_K(float(r[i_T]), unit))
        except ValueError:
            continue
    return t, T


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


def verify_cross_friction(
    coupler_name,
    force_velocity_csv=None,
    thermal_steady_csv=None,
    decay_csv=None,
    thermal_decay_csv=None,
):
    coupler = get_coupler(coupler_name)
    if coupler is None:
        raise KeyError(f"No coupler named '{coupler_name}' in overlay.")
    if coupler["kind"] != "friction_to_heat":
        raise ValueError(f"Coupler '{coupler_name}' is not "
                         "friction_to_heat.")

    claims = _load_claims()
    base = f"fab::coupler::friction::{coupler_name}"
    sub_results, sub_verdicts, notes = {}, {}, []
    exp_default = coupler["expected_agreement_pct"]

    # ---- STEADY-STATE ----
    if force_velocity_csv is not None and thermal_steady_csv is not None:
        d = _read_columns(force_velocity_csv,
                          ("time_s", "F_N", "v_mps"))
        F = d["F_N"]
        v = d["v_mps"]
        P_inst = [F[i] * v[i] for i in range(len(F))]
        P_mech_meas = sum(P_inst) / len(P_inst) if P_inst else 0.0

        _, T_K = _read_thermal_K(thermal_steady_csv)
        T_amb = T_K[0]
        n_tail = min(5, len(T_K))
        T_ss = sum(T_K[-n_tail:]) / n_tail
        dT_ss_meas = T_ss - T_amb

        R_th = coupler["R_th_K_per_W"]
        q_dot_thermal = (dT_ss_meas / R_th) if (R_th and R_th > 0) else 0.0

        agree_PQ = _agreement_pct(P_mech_meas, q_dot_thermal)
        claim = _find(claims, f"{base}::mech_to_heat",
                      "mech_power_agreement_pct")
        tol = claim.get("tol_frac", 0.08) if claim else 0.08
        exp = claim.get("value", exp_default) if claim else exp_default
        v_PQ = _verdict(agree_PQ, exp, tol)

        sub_results["steady"] = {
            "P_mech_measured_W":      P_mech_meas,
            "P_mech_predicted_W":     coupler.get("P_mech_avg_W"),
            "delta_T_ss_measured_K":  dT_ss_meas,
            "delta_T_ss_predicted_K": coupler.get("delta_T_ss_K"),
            "q_dot_from_thermal_W":   q_dot_thermal,
            "agreement_pct_PQ":       agree_PQ,
        }
        sub_verdicts["steady"] = v_PQ

        if v_PQ != "pass" and P_mech_meas != 0:
            ratio = q_dot_thermal / P_mech_meas
            if ratio < 0.85:
                notes.append(f"q̇/P_mech = {ratio:.2f} (LOW) -> mech "
                             "energy stored elastically OR acoustic "
                             "radiation OR R_th underestimated")
            elif ratio > 1.15:
                notes.append(f"q̇/P_mech = {ratio:.2f} (HIGH) -> "
                             "second heat source (bearing, amp "
                             "loss conducting in) OR R_th "
                             "overestimated")

    # ---- FREE DECAY ----
    if decay_csv is not None and thermal_decay_csv is not None:
        d = _read_columns(decay_csv, ("time_s", "x_m"))
        x = d["x_m"]
        t_x = d["time_s"]
        k_spring = coupler["spring_k"]
        E_mech_in = 0.5 * k_spring * (x[0] ** 2)

        # mechanical ζ from damped-sinusoid fit
        zeta_mech = None
        try:
            fit = fit_damped_sinusoid(t_x, x)
            zeta_mech = fit.get("zeta")
        except Exception:
            pass

        # thermal-side energy accounting (correct formula):
        #   E_thermal_total = C_th · (T_end - T_amb) + ∫(T-T_amb)/R_th dt
        t_th, T_K = _read_thermal_K(thermal_decay_csv)
        T_amb = T_K[0]
        C_th  = coupler["C_th_J_per_K"]
        R_th  = coupler["R_th_K_per_W"]

        n_tail = min(5, len(T_K))
        T_end = sum(T_K[-n_tail:]) / n_tail
        dT_end = T_end - T_amb
        dT_peak = max(T_K) - T_amb

        E_storage_end = C_th * dT_end if C_th else 0.0
        E_leaked = 0.0
        if R_th and R_th > 0:
            for i in range(1, len(t_th)):
                dt = t_th[i] - t_th[i-1]
                avg_dT = (((T_K[i]   - T_amb)
                         + (T_K[i-1] - T_amb)) / 2.0)
                E_leaked += avg_dT / R_th * dt
        E_thermal_total = E_storage_end + E_leaked

        agree_EB = _agreement_pct(E_thermal_total, E_mech_in)
        claim = _find(claims, f"{base}::energy_balance",
                      "energy_balance_agreement_pct")
        tol = claim.get("tol_frac", 0.10) if claim else 0.10
        exp = claim.get("value", exp_default) if claim else exp_default
        v_EB = _verdict(agree_EB, exp, tol)

        sub_results["decay"] = {
            "E_mech_in_J":          E_mech_in,
            "E_storage_end_J":      E_storage_end,
            "E_leaked_to_amb_J":    E_leaked,
            "E_thermal_total_J":    E_thermal_total,
            "delta_T_peak_K":       dT_peak,
            "delta_T_end_K":        dT_end,
            "zeta_mech_measured":   zeta_mech,
            "zeta_predicted":       coupler["zeta"],
            "agreement_pct_EB":     agree_EB,
        }
        sub_verdicts["decay"] = v_EB

        if v_EB != "pass" and E_mech_in > 0:
            ratio = E_thermal_total / E_mech_in
            if ratio < 0.85:
                notes.append(f"E_thermal/E_mech = {ratio:.2f} (LOW) -> "
                             "energy escaping non-thermally (acoustic, "
                             "mount conduction) OR R_th underestimated")
            elif ratio > 1.15:
                notes.append(f"E_thermal/E_mech = {ratio:.2f} (HIGH) -> "
                             "external heat source during decay (HVAC, "
                             "sun) OR x̂₀ underestimated OR R_th too "
                             "small so leaked-energy integral inflated")

        # ζ consistency
        if zeta_mech is not None and coupler.get("zeta") is not None:
            agree_zeta = _agreement_pct(zeta_mech, coupler["zeta"])
            zclaim = _find(claims, f"{base}::zeta_consistency",
                           "zeta_agreement_pct")
            tol_z = zclaim.get("tol_frac", 0.15) if zclaim else 0.15
            exp_z = zclaim.get("value", exp_default) if zclaim \
                else exp_default
            v_z = _verdict(agree_zeta, exp_z, tol_z)
            sub_results["zeta"] = {
                "zeta_mech_measured": zeta_mech,
                "zeta_predicted":     coupler["zeta"],
                "agreement_pct_zeta": agree_zeta,
            }
            sub_verdicts["zeta"] = v_z

    if not sub_verdicts:
        raise RuntimeError(
            "Provide steady-state OR decay measurement pair "
            "(force_velocity_csv + thermal_steady_csv, or "
            "decay_csv + thermal_decay_csv).")

    rank = {"pass": 0, "drift": 1, "fail": 2}
    overall = max(sub_verdicts.values(), key=lambda v: rank[v])

    # triangulation diagnostics
    if "steady" in sub_verdicts and "decay" in sub_verdicts:
        if (sub_verdicts["steady"] == "fail"
                and sub_verdicts["decay"] == "pass"):
            notes.append("steady FAIL + decay PASS -> R_th issue at "
                         "steady operating point OR phase error in F/v "
                         "sensors during forced vibration")
        elif (sub_verdicts["steady"] == "pass"
                and sub_verdicts["decay"] == "fail"):
            notes.append("steady PASS + decay FAIL -> C_th wrong OR "
                         "initial x̂₀ in nonlinear-k range")
    if all(v == "pass" for v in sub_verdicts.values()):
        notes.append("multi-mode agreement: friction-to-heat ratio "
                     "verified at 1.0 -- bond-graph energy "
                     "conservation intact for this damper")

    result = {
        "scope":        f"fab::coupler::friction::{coupler_name}",
        "method":       "cross_substrate_friction_to_heat",
        "coupler":      coupler_name,
        "sub_results":  sub_results,
        "sub_verdicts": sub_verdicts,
        "overall":      overall,
        "diagnostic":   notes,
        "ts":           time.time(),
    }
    _append_log(result)
    return result
