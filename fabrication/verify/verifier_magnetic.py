"""
verifier_magnetic.py  (fabrication/verify/)

Two measurement paths:

  (a) LCR-meter CSV: freq_Hz, Z_ohm, phase_deg
        L = Z·sin(φ) / (2π·f)   -- median across measurement band

  (b) Hall-probe CSV: current_A, B_T
        slope of B vs I = N/(ℛ·A);  B_meas_at_I_peak vs claim

The LC-resonance method (pair inductor with a known C, run swept
sine) reduces to the EXISTING verify_electrical_csv path -- no
new code needed, just link the magnetic claim to the electrical
LC scope. That coupler wedge is out of scope for this commit.

License: CC0. Stdlib only.
"""
import csv as _csv
import math
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .regression import ols


# ----- LCR-meter CSV path ----------------------------------------

def _read_lcr_csv(path):
    """Strict columns: freq_Hz, Z_ohm, phase_deg."""
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    for k in ("freq_Hz", "Z_ohm", "phase_deg"):
        if k not in headers:
            raise ValueError(f"CSV must contain {k} column.")
    i_f, i_z, i_p = (headers.index(k)
                     for k in ("freq_Hz", "Z_ohm", "phase_deg"))
    f, z, p = [], [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            f.append(float(r[i_f]))
            z.append(float(r[i_z]))
            p.append(float(r[i_p]))
        except ValueError:
            continue
    if not f:
        raise ValueError(f"No usable rows in {path}.")
    return f, z, p


def _extract_L(freqs, mags, phases_deg):
    """L = Z·sin(φ) / (2π·f). Median across all inductive bins."""
    Ls = []
    for fi, zi, pi in zip(freqs, mags, phases_deg):
        if fi <= 0:
            continue
        X = zi * math.sin(math.radians(pi))
        if X <= 0:
            continue
        Ls.append(X / (2 * math.pi * fi))
    if not Ls:
        raise RuntimeError("No inductive points in CSV (all phases ≤ 0).")
    Ls.sort()
    return Ls[len(Ls) // 2]


def verify_magnetic_lcr(csv_path, scope_prefix):
    freqs, mags, phases = _read_lcr_csv(csv_path)
    L_meas = _extract_L(freqs, mags, phases)
    claims = _load_claims()
    L_claim = next((c for c in claims
                    if c.get("scope") == f"{scope_prefix}::L"
                    and c.get("rate_var") == "inductance_H"), None)
    if L_claim is None:
        raise KeyError(f"No L claim at {scope_prefix}::L")
    L_pred = L_claim["value"]
    tol    = L_claim.get("tol_frac", 0.08)
    verdict = _verdict(L_meas, L_pred, tol)

    notes = []
    ratio = L_meas / L_pred
    if ratio < 0.85:
        notes.append("L LOW: core not seated (extra air gap), "
                     "saturation at measurement current, OR μ_r "
                     "overestimated")
    if ratio > 1.15:
        notes.append("L HIGH: turns higher than spec, OR effective "
                     "core area larger than geometric (fringing)")
    f_mid = freqs[len(freqs) // 2]
    if not (1e2 <= f_mid <= 1e4):
        notes.append("measurement band outside 100 Hz - 10 kHz -- "
                     "at HF, self-capacitance shifts apparent L "
                     "upward; at LF, ohmic part dominates")

    result = {
        "scope_prefix": scope_prefix,
        "method":       "magnetic_lcr_csv",
        "predicted_L":  L_pred,
        "measured_L":   L_meas,
        "tol_frac":     tol,
        "verdict":      verdict,
        "diagnostic":   notes,
        "csv":          str(csv_path),
        "ts":           time.time(),
    }
    _append_log(result)
    return result


# ----- Hall-probe (B vs I) CSV path ------------------------------

def _read_BvI_csv(path):
    """Strict columns: current_A, B_T."""
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    for k in ("current_A", "B_T"):
        if k not in headers:
            raise ValueError(f"CSV must contain {k} column.")
    i_i, i_b = (headers.index(k) for k in ("current_A", "B_T"))
    I, B = [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            I.append(float(r[i_i]))
            B.append(float(r[i_b]))
        except ValueError:
            continue
    return I, B


def verify_magnetic_BvI(csv_path, scope_prefix):
    I, B = _read_BvI_csv(csv_path)
    fit = ols(I, B)
    slope = fit["slope"]              # T per A

    claims = _load_claims()
    B_claim = next((c for c in claims
                    if c.get("scope") == f"{scope_prefix}::Bpeak"
                    and c.get("rate_var") == "B_peak_T"), None)
    if B_claim is None:
        raise KeyError(f"No B_peak claim at {scope_prefix}::Bpeak")
    B_pred = B_claim["value"]
    # Compare predicted peak B against measured slope × the
    # current that was used as 'peak' in the claim. If the claim
    # stored peak_current_A use that; otherwise use max(I) from CSV.
    I_ref = B_claim.get("peak_current_A", max(I))
    B_meas_at_peak = slope * I_ref
    tol = B_claim.get("tol_frac", 0.08)
    verdict = _verdict(B_meas_at_peak, B_pred, tol)

    notes = []
    if fit["r2"] < 0.97:
        notes.append(f"B-I nonlinearity (r²={fit['r2']:.3f}) -- "
                     "core approaching saturation OR hysteresis "
                     "dominant in the swept range")
    ratio = B_meas_at_peak / B_pred
    if ratio < 0.85:
        notes.append("B LOW: bigger gap than spec (fringing or "
                     "mounting) OR fewer turns than counted")
    if ratio > 1.15:
        notes.append("B HIGH: gap smaller than spec OR μ_r higher "
                     "(different core grade than labelled)")

    result = {
        "scope_prefix":         scope_prefix,
        "method":               "magnetic_BvI_csv",
        "predicted_B":          B_pred,
        "measured_B_at_peak_I": B_meas_at_peak,
        "slope_T_per_A":        slope,
        "I_ref":                I_ref,
        "r2":                   fit["r2"],
        "tol_frac":             tol,
        "verdict":              verdict,
        "diagnostic":           notes,
        "csv":                  str(csv_path),
        "ts":                   time.time(),
    }
    _append_log(result)
    return result
