"""
claim_back_fluidic.py  (fabrication/)

Emit a "fluidic_resistance" claim from a fluidic geometry +
fluid spec. Sibling to claim_back.py and claim_back_modes.py;
writes to the same CLAIM_TABLE.fab.json ledger.

License: CC0. Stdlib only.
"""
import time
import hashlib
import json
from pathlib import Path

from .backends.fluidic import channel_resistance, FluidParams


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claim_fluidic(geometry, fluid: FluidParams, geometric_hash,
                       tol_frac=0.10):
    R = channel_resistance(geometry["length"], geometry["radius"], fluid)
    scope = f"fab::fluidic::{geometric_hash}"
    payload = {
        "scope":       scope,
        "rate_var":    "fluidic_resistance",
        "wrt":         "Q_m3s",
        "kind":        "steady",
        "value":       R,           # ΔP/Q in Pa·s/m³
        "tol_frac":    tol_frac,
        "geometry":    geometry,
        "fluid":       {"rho": fluid.rho, "mu": fluid.mu},
        "measurement": "regress ΔP on Q from CSV; slope = R; "
                       "Reynolds < 2300 required per point",
        "failure":     "Re ≥ 2300 -> laminar model invalid; "
                       "non-zero intercept -> entrance/exit losses unmodeled; "
                       "r² < 0.95 -> leak, bubble, or pulsing flow",
        "provenance":  "fabrication/backends/fluidic.py::channel_resistance",
        "ts":          time.time(),
    }
    payload["id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return payload


def append_fluidic_claim(claim, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [c for c in existing if c["scope"] != claim["scope"]]
    existing.append(claim)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return claim["id"]
