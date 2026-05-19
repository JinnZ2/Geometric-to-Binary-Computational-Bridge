"""
claim_back_modes.py  (fabrication/)

Per-mode claim emission. Sibling to claim_back.py; writes the SAME
CLAIM_TABLE.fab.json but with one composite claim per predicted
eigenmode. Each claim's scope is suffixed `::modeN` so the
multimode verifier can look them up individually.

License: CC0. Stdlib only.
"""
import time
import hashlib
import json
from pathlib import Path

from .eigenmodes import predict_eigenmodes


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claims_multimode(ir, geometric_hash, tol_frac=0.08):
    modes = predict_eigenmodes(ir)
    claims = []
    for m in modes:
        scope = f"fab::{ir.domain}::{geometric_hash}::mode{m['mode_index']}"
        payload = {
            "scope":       scope,
            "rate_var":    "resonance_freq_Hz",
            "kind":        "composite",
            "mode_index":  m["mode_index"],
            "value":       m["f"],
            "tol_frac":    tol_frac,
            "measurement": "swept-sine; baselined transfer function; "
                           "multi-peak detection; assignment to this mode",
            "failure":     "if measured mode count < predicted: "
                           "(a) weak excitation in that band, "
                           "(b) coupling neck blocked, "
                           "(c) Q so high that bin resolution misses it",
            "provenance":  "fabrication/eigenmodes.py::predict_eigenmodes",
            "ts":          time.time(),
        }
        payload["id"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        claims.append(payload)
    return claims


def append_modes_to_ledger(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    # drop prior claims with same scope so re-runs supersede
    new_scopes = {c["scope"] for c in claims}
    existing = [e for e in existing if e["scope"] not in new_scopes]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)


# -------------------------------------------------------------
# v2: claims aware of distributed modes (pipe / box / cylinder).
# Each claim carries the mode_kind so diagnostic engines can
# route failure-mode text correctly. Uses predict_eigenmodes_full
# instead of the lumped-only predict_eigenmodes.
# -------------------------------------------------------------

def _failure_text(kind):
    return {
        "lumped":   "ka > 0.3 -> distributed modes likely; "
                    "promote geometry_hints to {pipe|box|cylinder}",
        "pipe":     "end-correction unaccounted (add 0.6·r per open end); "
                    "axial taper changes effective length",
        "box":      "rigid-wall assumption broken if walls thin / soft -> "
                    "modes shift low; corner radii couple (l,m,n) triplets",
        "cylinder": "Bessel zeros assume ideal rigid wall; thermal-viscous "
                    "boundary layer raises Q dependence at high m, k",
    }.get(kind, "see provenance file")


def back_claims_multimode_v2(ir, geometric_hash, geometry_hints=None,
                             tol_frac=0.08):
    """
    Like back_claims_multimode, but uses predict_eigenmodes_full so
    distributed-element modes (pipe / box / cylinder) are predicted
    when geometry_hints indicates ka > 0.3. Each claim carries:
      mode_kind  : "lumped" | "pipe" | "box" | "cylinder"
      extra      : the rest of the mode dict (axial_n, radial, etc.)
    """
    from .eigenmodes import predict_eigenmodes_full
    modes = predict_eigenmodes_full(ir, geometry_hints=geometry_hints)
    claims = []
    for m in modes:
        scope = f"fab::{ir.domain}::{geometric_hash}::mode{m['mode_index']}"
        payload = {
            "scope":       scope,
            "rate_var":    "resonance_freq_Hz",
            "kind":        "composite",
            "mode_kind":   m.get("kind", "lumped"),
            "mode_index":  m["mode_index"],
            "value":       m["f"],
            "tol_frac":    tol_frac,
            "extra":       {k: v for k, v in m.items()
                            if k not in ("f", "mode_index", "kind")},
            "measurement": "swept-sine; baselined transfer; multi-peak; "
                           "assignment to this mode",
            "failure":     _failure_text(m.get("kind", "lumped")),
            "provenance":  "fabrication/eigenmodes.py::predict_eigenmodes_full",
            "ts":          time.time(),
        }
        payload["id"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        claims.append(payload)
    return claims
