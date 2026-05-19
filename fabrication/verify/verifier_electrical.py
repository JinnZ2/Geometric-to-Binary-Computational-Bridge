"""
verifier_electrical.py  (fabrication/verify/)

CSV mode: read (freq_Hz, Z_ohm) sweep -- from a VNA, LCR meter, or
homebrew shunt-resistor-plus-scope. Find peak (parallel LC) or
dip (series LC) of |Z| near the predicted resonance, compute Q
from local -3 dB bandwidth, verdict against the LC composite
claim.

Shunt-WAV mode (drive sweep through DUT in series with known
shunt, derive |Z|(f) from V_source / V_shunt) is sketched in
the paste but not implemented here; once the bench rig is real
it'll mirror transfer_function from the acoustic path.

License: CC0. Stdlib only.
"""
import csv as _csv
import time
from pathlib import Path

from .verifier import _load_claims, _verdict, _append_log
from .peak import q_factor, q_factor_dip


def _read_impedance_csv(path):
    """
    Strict columns:
      freq_Hz, Z_ohm   (magnitude)
      optional: phase_deg  (unused here, accepted)
    """
    rows = list(_csv.reader(Path(path).open()))
    headers = rows[0]
    if "freq_Hz" not in headers or "Z_ohm" not in headers:
        raise ValueError("CSV must contain freq_Hz, Z_ohm columns.")
    f_idx, z_idx = headers.index("freq_Hz"), headers.index("Z_ohm")
    freqs, mag = [], []
    for r in rows[1:]:
        if not r or r[0].startswith("#"):
            continue
        try:
            freqs.append(float(r[f_idx]))
            mag.append(float(r[z_idx]))
        except ValueError:
            continue
    if not freqs:
        raise ValueError(f"No usable data rows in {path}.")
    return freqs, mag


def _find_claim(claims, scope, rate_var):
    for c in claims:
        if c.get("scope") == scope and c.get("rate_var") == rate_var:
            return c
    return None


def _peak_or_dip(freqs, mag, expected, tol_frac):
    """
    LC parallel -> peak in |Z|; LC series -> dip in |Z|.
    Decide by looking near `expected`: whichever extremum is
    closer to f_expected wins. Returns (f_meas, kind).
    """
    lo = expected * (1 - 3*tol_frac)
    hi = expected * (1 + 3*tol_frac)
    band = [(f, m) for f, m in zip(freqs, mag) if lo <= f <= hi]
    if len(band) < 5:
        return None, None
    fs, ms = zip(*band)
    i_pk = max(range(len(ms)), key=lambda i: ms[i])
    i_dp = min(range(len(ms)), key=lambda i: ms[i])
    if abs(fs[i_pk] - expected) <= abs(fs[i_dp] - expected):
        return fs[i_pk], "peak"
    return fs[i_dp], "dip"


def verify_electrical_csv(csv_path, scope):
    """`scope` is the LC composite scope, e.g.
    fab::electrical::<h>::LC0
    """
    freqs, mag = _read_impedance_csv(csv_path)
    claims = _load_claims()
    f_claim = _find_claim(claims, scope, "resonance_freq_Hz")
    if f_claim is None:
        raise KeyError(f"No resonance claim for scope={scope}")
    f_pred = f_claim["value"]
    tol    = f_claim.get("tol_frac", 0.05)

    f_meas, mode = _peak_or_dip(freqs, mag, f_pred, tol)
    if f_meas is None:
        raise RuntimeError(
            f"Insufficient points near {f_pred:.1f} Hz in CSV. "
            "Widen sweep range or increase point density.")
    # Q computation depends on which extremum the LC topology
    # produces: series RLC -> dip (use q_factor_dip), parallel RLC
    # -> peak (use q_factor).
    q_meas = (q_factor_dip(list(freqs), list(mag), f_meas)
              if mode == "dip"
              else q_factor(list(freqs), list(mag), f_meas))
    verdict = _verdict(f_meas, f_pred, tol)

    notes = []
    ratio = f_meas / f_pred
    if ratio < 0.90:
        notes.append("f₀ LOW: extra capacitance (probe, breadboard rails) "
                     "OR larger inductance than spec "
                     "(self-cap not subtracted)")
    if ratio > 1.10:
        notes.append("f₀ HIGH: lead inductance series with cap; "
                     "OR cap value lower than marked "
                     "(voltage coefficient)")
    if mode == "dip":
        notes.append("series-resonance dip detected -- topology is "
                     "series RLC; verify the IR matches (parallel LC "
                     "would give a peak instead)")

    measurement = {
        "scope":      scope,
        "claim_id":   f_claim.get("id"),
        "method":     "electrical_impedance_csv",
        "predicted":  f_pred,
        "measured":   f_meas,
        "delta_pct":  100*(f_meas/f_pred - 1),
        "q_factor":   q_meas,
        "extremum":   mode,         # "peak" or "dip"
        "tol_frac":   tol,
        "verdict":    verdict,
        "diagnostic": notes,
        "csv":        str(csv_path),
        "ts":         time.time(),
    }
    _append_log(measurement)
    return measurement
