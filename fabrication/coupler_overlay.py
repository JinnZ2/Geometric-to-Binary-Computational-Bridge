"""
coupler_overlay.py  (fabrication/)

Coupler overlay graph -- separate from per-domain IRs. Holds
gyrators/transformers across substrates. Loads from / writes to
coupler_overlay.json in the CWD; lookup is by coupler name.

License: CC0. Stdlib only.
"""
import json
import time
import hashlib
from pathlib import Path

from .couplers_piezo import (PIEZO_MATERIALS, piezo_capacitance,
                             effective_k_squared, predict_split,
                             expected_agreement_pct)


OVERLAY = Path("coupler_overlay.json")


def make_piezo_coupler(name, material, disc_geometry, cavity_geometry,
                       acoustic_scope, electrical_scope,
                       f_acoustic_pred):
    """
    Returns a coupler entry. Does NOT compute f₀_acoustic itself --
    that comes from the existing acoustic IR / eigenmode prediction;
    we just link the two scopes via the coupler.
    """
    mat = PIEZO_MATERIALS[material]
    k_eff2 = effective_k_squared(material, disc_geometry, cavity_geometry)
    regime, f_s, f_p = predict_split(f_acoustic_pred, k_eff2)
    C0 = piezo_capacitance(disc_geometry["area"],
                           disc_geometry["thickness"],
                           mat["epsilon_r"])
    expected_pct = expected_agreement_pct(k_eff2)
    entry = {
        "name":             name,
        "kind":             "piezo_gyrator",
        "material":         material,
        "k_eff_squared":    k_eff2,
        "regime":           regime,
        "C0_farads":        C0,
        "disc_geometry":    disc_geometry,
        "cavity_geometry":  cavity_geometry,
        "f_series_Hz":      f_s,
        "f_parallel_Hz":    f_p,
        "expected_agreement_pct": expected_pct,
        "acoustic_scope":   acoustic_scope,
        "electrical_scope": electrical_scope,
        "provenance":       "couplers_piezo.py",
        "ts":               time.time(),
    }
    entry["id"] = hashlib.sha256(
        json.dumps(entry, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    return entry


def append_coupler(entry, path: Path = OVERLAY):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing = [e for e in existing if e["name"] != entry["name"]]
    existing.append(entry)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return entry["id"]


def get_coupler(name, path: Path = OVERLAY):
    if not path.exists():
        return None
    for e in json.loads(path.read_text()):
        if e["name"] == name:
            return e
    return None


def list_couplers(path: Path = OVERLAY):
    if not path.exists():
        return []
    return json.loads(path.read_text())
