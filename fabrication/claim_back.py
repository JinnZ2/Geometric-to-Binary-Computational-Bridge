"""
claim_back.py  (fabrication/)

Writes a sibling ledger: CLAIM_TABLE.fab.json (relative to CWD).
Each claim is dX/dt under a substrate-scoped namespace.
Falsifiable: every claim has bounds + a measurement protocol.

If a fabricated artifact's measured value falls outside the claim's
tolerance band, the BRIDGE has a leak -- not the part. That keeps
the substrate honest.

License: CC0. Stdlib only.
"""
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def _hash(payload: dict) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _measurement_protocol(el):
    """How a human at a bench validates this claim."""
    return {
        "store_flow":   "swept-sine 20–20k; phase −90° at resonance => confirms L-like",
        "store_effort": "swept-sine; phase +90° below resonance => confirms C-like",
        "dissipate":    "DC or steady-flow drop; R = ΔP / Q (or ΔV / I in analog)",
        "transform":    "input/output amplitude ratio at low f",
        "gyrator":      "cross-domain transfer: input effort vs output flow",
    }.get(el.kind, "unspecified")


def _failure_mode(el):
    return {
        "store_flow":   "turbulence onset (Re > 2300) => claim invalid",
        "store_effort": "wall flex / leak => C drifts high",
        "dissipate":    "non-laminar flow OR thermal heating => R drifts",
    }.get(el.kind, "see provenance file")


def back_claim(ir, artifact_path, geometric_hash):
    """
    For each element in IR, emit a packed claim:
      dX/dt = f(geometry, domain)
    where X is the domain's stored quantity.
    These are PREDICTIONS that the fabricated object must satisfy
    when measured. If it doesn't -> bridge has a leak; not the part.
    """
    claims = []
    for el in ir.elements:
        payload = {
            "scope":       f"fab::{ir.domain}::{geometric_hash}",
            "rate_var":    el.port_a.flow_name,
            "wrt":         el.port_a.effort_name,
            "kind":        el.kind,
            "value":       el.parameter,
            "tol_frac":    0.05,
            "geometry":    el.geometry,
            "artifact":    str(artifact_path),
            "measurement": _measurement_protocol(el),
            "failure":     _failure_mode(el),
            "provenance":  "fabrication/lowering.py",
            "ts":          time.time(),
        }
        payload["id"] = _hash(payload)
        claims.append(payload)
    return claims


def append_ledger(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)
