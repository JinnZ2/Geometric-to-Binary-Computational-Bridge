"""
claim_back_mechanical.py  (fabrication/)

Emit claims for a mechanical IR:
  - per-element passive value (m / c / b) with tolerance band
  - composite: free-vibration resonance freq for each (mass, compliance)
    pair
  - composite: damping ratio ζ from (b, m, c) when present

Same ledger and verdict semantics as the other claim_back_* modules:
nothing here is mechanical-specific from the audit's point of view.

License: CC0. Stdlib only.
"""
import math
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claims_mechanical(ir, geometric_hash, tol_frac=0.06):
    claims = []
    base_scope = f"fab::mechanical::{geometric_hash}"

    # ---- passive element claims ----
    for i, el in enumerate(ir.elements):
        scope = f"{base_scope}::el{i}"
        var_name = {"store_flow":   "m",
                    "store_effort": "c",
                    "dissipate":    "b"}[el.kind]
        payload = {
            "scope":       scope,
            "rate_var":    f"{var_name}_value",
            "kind":        "passive",
            "value":       el.parameter,
            "tol_frac":    tol_frac,
            "geometry":    el.geometry,
            "measurement": _measurement_for(var_name),
            "failure":     _failure_for(var_name),
            "provenance":  "backends/mechanical.py",
        }
        payload["id"] = _h(payload)
        claims.append(payload)

    # ---- composite: free-vibration resonance(s) ----
    Ms = [e.parameter for e in ir.elements if e.kind == "store_flow"]
    Cs = [e.parameter for e in ir.elements if e.kind == "store_effort"]
    Bs = [e.parameter for e in ir.elements if e.kind == "dissipate"]
    for k, (m, c) in enumerate(zip(Ms, Cs)):
        f0 = 1.0 / (2 * math.pi * math.sqrt(m * c))
        scope = f"{base_scope}::mode{k}"
        payload = {
            "scope":       scope,
            "rate_var":    "resonance_freq_Hz",
            "kind":        "composite",
            "value":       f0,
            "tol_frac":    tol_frac * 2,
            "measurement": "free-vibration: impulse the structure, log "
                           "displacement/accel vs time, fit damped sinusoid",
            "failure":     "mass distributed (not lumped) -> multiple modes; "
                           "spring nonlinear -> drift with amplitude; "
                           "boundary clamp imperfect -> effective k lower",
            "provenance":  "claim_back_mechanical.py",
            "M_index": k, "C_index": k,
        }
        payload["id"] = _h(payload)
        claims.append(payload)

        if k < len(Bs):
            b = Bs[k]
            k_stiff = 1.0 / c
            zeta = b / (2.0 * math.sqrt(m * k_stiff))
            scope_z = f"{base_scope}::zeta{k}"
            payload = {
                "scope":       scope_z,
                "rate_var":    "damping_ratio",
                "kind":        "composite",
                "value":       zeta,
                "tol_frac":    0.20,
                "measurement": "log-decrement of free-vibration envelope; "
                               "ζ = δ/√(4π² + δ²) where δ=ln(A_n/A_{n+1})",
                "failure":     "air drag, joint friction, internal damping "
                               "of the material -- any missing loss path "
                               "biases ζ low in the prediction",
                "provenance":  "claim_back_mechanical.py",
            }
            payload["id"] = _h(payload)
            claims.append(payload)
    return claims


def append_mechanical_claims(claims, path: Path = LEDGER):
    existing = json.loads(path.read_text()) if path.exists() else []
    new_scopes = {c["scope"] for c in claims}
    existing = [e for e in existing if e["scope"] not in new_scopes]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)


def _h(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _measurement_for(var):
    return {
        "m": "weigh the moving element on a balance OR ρ·V from geometry",
        "c": "static load test: hang known F, measure displacement x; "
             "c = x/F (k = F/x = 1/c)",
        "b": "free-vibration log-decrement OR forced-response phase lag "
             "at resonance",
    }[var]


def _failure_for(var):
    return {
        "m": "distributed mass approximated as lumped -- effective "
             "modal mass differs by mode-shape integral",
        "c": "nonlinear stiffening at large deflection; clamp boundary "
             "compliance not subtracted; temperature shifts E",
        "b": "amplitude-dependent (Coulomb friction at joints); "
             "frequency-dependent (eddy currents, viscoelasticity)",
    }[var]
