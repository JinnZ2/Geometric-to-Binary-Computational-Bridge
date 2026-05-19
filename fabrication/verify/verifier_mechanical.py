"""
verifier_mechanical.py  (fabrication/verify/)

Free-vibration verifier. Reads a CSV of (time_s, y_<unit>) where y is
displacement, velocity, or acceleration (any -- only the frequency
and the envelope decay matter, not the absolute scale). Fits a
damped sinusoid

    y(t) = A·exp(-ζ·ωn·t)·cos(ωd·t + φ) + b
    ωd   = ωn·√(1-ζ²)

and verdicts ωn (-> f₀) and ζ against the mechanical claim pair.

CSV format -- strict header detection. Accepted y-columns:
    y_m, y_mm, y_um   (displacement)
    v_mps, v_mmps     (velocity)
    a_mps2, a_g       (acceleration; g = 9.80665 m/s²)
First match wins; column is normalized to SI internally so the fit's
A has unit-consistent meaning but the audit only uses ωn and ζ which
are scale-free.

License: CC0. Stdlib only.
"""
import csv as _csv
import math
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .transient_fit import _gauss_newton


_Y_UNITS = {
    "y_m":    1.0,
    "y_mm":   1e-3,
    "y_um":   1e-6,
    "v_mps":  1.0,
    "v_mmps": 1e-3,
    "a_mps2": 1.0,
    "a_g":    9.80665,
}


def _read_vibration_csv(path):
    """Return (t, y_SI, y_col_name)."""
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    if "time_s" not in headers:
        raise ValueError("CSV must contain time_s column.")
    t_idx = headers.index("time_s")
    y_col = next((c for c in headers if c in _Y_UNITS), None)
    if y_col is None:
        raise ValueError(
            "CSV must contain one of: " + ", ".join(_Y_UNITS.keys()))
    y_idx = headers.index(y_col)
    scale = _Y_UNITS[y_col]
    t, y = [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            t.append(float(r[t_idx]))
            y.append(float(r[y_idx]) * scale)
        except ValueError:
            continue
    if len(t) < 30:
        raise ValueError(f"Too few samples in {path}: {len(t)}")
    return t, y, y_col


def _initial_guesses(t, y):
    """Coarse pass for (A, wn, zeta, phi, b)."""
    b0 = sum(y[-max(5, len(y)//20):]) / max(5, len(y)//20)
    z = [v - b0 for v in y]
    A0 = max(abs(v) for v in z) or 1.0

    # zero-crossing estimate of ωd
    crossings = []
    for i in range(1, len(z)):
        if z[i-1] == 0 or (z[i-1] * z[i] < 0):
            # linear interp to crossing
            denom = (z[i] - z[i-1]) or 1e-12
            frac = -z[i-1] / denom
            crossings.append(t[i-1] + frac * (t[i] - t[i-1]))
    if len(crossings) >= 3:
        periods = [2.0 * (crossings[k+1] - crossings[k])
                   for k in range(len(crossings)-1)]
        T = sum(periods) / len(periods)
        wd0 = 2 * math.pi / T
    else:
        wd0 = 2 * math.pi * 50.0   # last-ditch fallback

    # log-decrement on successive same-sign peaks
    peaks = []
    for i in range(2, len(z)-2):
        if (z[i] > z[i-1] and z[i] >= z[i+1]
                and z[i] > 0 and z[i] > 0.05*A0):
            peaks.append((t[i], z[i]))
    zeta0 = 0.1
    if len(peaks) >= 2:
        deltas = []
        for k in range(len(peaks)-1):
            if peaks[k+1][1] > 0 and peaks[k][1] > 0:
                deltas.append(math.log(peaks[k][1] / peaks[k+1][1]))
        if deltas:
            delta = sum(deltas) / len(deltas)
            denom = math.sqrt(4 * math.pi**2 + delta**2)
            zeta0 = max(0.005, min(0.95, delta / denom))

    wn0 = wd0 / max(math.sqrt(1 - zeta0**2), 0.1)
    # phase from y(0)
    phi0 = math.atan2(0.0, (y[0] - b0) / (A0 if A0 != 0 else 1.0)) \
        if False else 0.0
    return A0, wn0, zeta0, phi0, b0


def fit_damped_sinusoid(t, y):
    """y(t) = A·exp(-ζ·ωn·t)·cos(ωd·t + φ) + b, ωd = ωn·√(1-ζ²)."""
    A0, wn0, z0, phi0, b0 = _initial_guesses(t, y)

    def resid(p):
        A, wn, zeta, phi, b = p
        wd = wn * math.sqrt(max(1e-12, 1 - zeta**2))
        return [A * math.exp(-zeta*wn*t[i]) * math.cos(wd*t[i] + phi)
                + b - y[i] for i in range(len(t))]

    def clamp(p):
        A, wn, zeta, phi, b = p
        if wn <= 1e-6:
            wn = 1e-6
        if zeta <= 0.001:
            zeta = 0.001
        if zeta >= 0.99:
            zeta = 0.99
        # keep phi bounded so jacobian columns don't wander
        if phi > math.pi:
            phi -= 2 * math.pi
        if phi < -math.pi:
            phi += 2 * math.pi
        return [A, wn, zeta, phi, b]

    params, ssr = _gauss_newton(resid, [A0, wn0, z0, phi0, b0],
                                clamp=clamp, max_iter=80)
    A, wn, zeta, phi, b = params
    ymean = sum(y) / len(y)
    sst = sum((v - ymean)**2 for v in y) or 1.0
    r2 = 1.0 - ssr / sst
    return {"A": A, "wn": wn, "zeta": zeta, "phi": phi, "b": b,
            "r2": r2, "ssr": ssr}


def _find_claim(claims, scope, rate_var):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == rate_var:
            return c
    return None


def verify_mechanical(csv_path, scope):
    """`scope` is the mode composite, e.g.
    fab::mechanical::<h>::mode0  -- f₀ claim
    plus a paired ζ claim at .../zeta<k>.
    """
    t, y, ycol = _read_vibration_csv(csv_path)
    fit = fit_damped_sinusoid(t, y)
    wn_m   = fit["wn"]
    zeta_m = fit["zeta"]
    f_meas = wn_m / (2 * math.pi)

    claims = _load_claims()
    c_f = _find_claim(claims, scope, "resonance_freq_Hz")
    if c_f is None:
        raise KeyError(f"No mechanical freq claim at scope={scope}")
    f_pred = c_f["value"]
    tol_f  = c_f.get("tol_frac", 0.08)
    verdict_f = _verdict(f_meas, f_pred, tol_f)

    # damping verdict if paired claim exists
    zeta_scope = scope.replace("::mode", "::zeta")
    c_z = _find_claim(claims, zeta_scope, "damping_ratio")
    verdict_z = None
    zeta_pred = None
    tol_z = None
    if c_z is not None:
        zeta_pred = c_z["value"]
        tol_z = c_z.get("tol_frac", 0.20)
        verdict_z = _verdict(zeta_m, zeta_pred, tol_z)

    # overall: worse of the two
    rank = {"pass": 0, "drift": 1, "fail": 2}
    overall = verdict_f
    if verdict_z is not None:
        overall = max([verdict_f, verdict_z], key=lambda v: rank[v])

    notes = []
    if fit["r2"] < 0.92:
        notes.append(f"fit r²={fit['r2']:.3f} -- multiple modes excited, "
                     "nonlinear spring, or noise dominates the tail")
    ratio = f_meas / f_pred
    if ratio < 0.90:
        notes.append("f₀ LOW: effective mass higher than modeled "
                     "(clamp adds end-mass), or spring softer "
                     "(boundary compliance)")
    if ratio > 1.10:
        notes.append("f₀ HIGH: stiffer than modeled (work-hardened, "
                     "preload), or mass lower (used wrong density)")
    if zeta_pred is not None and zeta_m > zeta_pred * 1.5:
        notes.append("ζ much higher than predicted -- joint friction, "
                     "air drag, or magnetic damping not modeled")

    measurement = {
        "scope":          scope,
        "claim_id":       c_f.get("id"),
        "method":         "mechanical_free_vibration",
        "y_column":       ycol,
        "predicted_f0":   f_pred,
        "measured_f0":    f_meas,
        "delta_pct":      100 * (f_meas / f_pred - 1),
        "tol_frac":       tol_f,
        "verdict_f":      verdict_f,
        "predicted_zeta": zeta_pred,
        "measured_zeta":  zeta_m,
        "verdict_zeta":   verdict_z,
        "r2":             fit["r2"],
        "verdict":        overall,
        "measured":       f_meas,
        "q_factor":       (1.0 / (2 * zeta_m)) if zeta_m > 1e-6 else None,
        "diagnostic":     notes,
        "csv":            str(csv_path),
        "ts":             time.time(),
    }
    _append_log(measurement)
    return measurement
