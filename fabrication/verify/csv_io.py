"""
csv_io.py  (fabrication/verify/)

Minimal CSV reader (no pandas). Strict on columns: requires
time_s, dP_<unit>, Q_<unit> with explicit unit suffix in the
header so a fuel-stop scribbled spreadsheet can't silently mix
units.

Allowed headers:
  time_s             (seconds, always)
  dP_Pa | dP_kPa | dP_bar | dP_psi | dP_mmH2O
  Q_m3s | Q_Lmin | Q_mLmin | Q_mLs

Anything else -> fail loud.

License: CC0. Stdlib only.
"""
import csv as _csv
from pathlib import Path


PRESSURE_TO_PA = {
    "Pa":    1.0,
    "kPa":   1e3,
    "bar":   1e5,
    "psi":   6894.757,
    "mmH2O": 9.80665,
}

FLOW_TO_M3S = {
    "m3s":   1.0,
    "Lmin":  1.0e-3 / 60.0,
    "mLmin": 1.0e-6 / 60.0,
    "mLs":   1.0e-6,
}


def _split_unit(header, allowed):
    # header like "dP_Pa" -> ("dP", "Pa")
    if "_" not in header:
        return None
    base, unit = header.split("_", 1)
    if unit not in allowed:
        raise ValueError(f"Unknown unit '{unit}' in column '{header}'. "
                         f"Allowed: {sorted(allowed)}")
    return base, unit


def read_flow_csv(path):
    """
    Returns (data, meta):
      data = {"time_s": [...], "dP_Pa": [...], "Q_m3s": [...]}
              all converted to SI
      meta = {"dP_unit": ..., "Q_unit": ..., "rows": N}
    Raises on missing columns or bad units.
    """
    path = Path(path)
    with path.open() as f:
        reader = _csv.reader(f)
        headers = next(reader)
        rows    = [r for r in reader if r and not r[0].startswith("#")]

    if "time_s" not in headers:
        raise ValueError("CSV must contain 'time_s' column.")
    dp_col = next((h for h in headers if h.startswith("dP_")), None)
    q_col  = next((h for h in headers if h.startswith("Q_")),  None)
    if not dp_col or not q_col:
        raise ValueError("CSV must contain a dP_<unit> and a Q_<unit> column.")

    _, dp_unit = _split_unit(dp_col, PRESSURE_TO_PA)
    _, q_unit  = _split_unit(q_col,  FLOW_TO_M3S)
    dp_scale = PRESSURE_TO_PA[dp_unit]
    q_scale  = FLOW_TO_M3S[q_unit]

    t_idx, d_idx, q_idx = (headers.index(x) for x in ("time_s", dp_col, q_col))
    out = {"time_s": [], "dP_Pa": [], "Q_m3s": []}
    for row in rows:
        try:
            out["time_s"].append(float(row[t_idx]))
            out["dP_Pa"].append(float(row[d_idx]) * dp_scale)
            out["Q_m3s"].append(float(row[q_idx]) * q_scale)
        except ValueError:
            continue   # skip malformed rows; never silently mangle units
    if not out["time_s"]:
        raise ValueError(f"No usable data rows in {path}.")
    return out, {"dP_unit": dp_unit, "Q_unit": q_unit,
                 "rows": len(out["time_s"])}
