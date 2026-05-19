"""
claim_back_electrical.py  (fabrication/)

Emit claims for an electrical IR:
  - per-element passive value (R / L / C) with tolerance band
  - composite: LC resonance freq for each LC pair
  - composite: Q from R, L, C if R present

All claims share the same CLAIM_TABLE.fab.json ledger and the
same _verdict() semantics, so a bridge-wide audit can read
electrical results alongside acoustic and fluidic without any
substrate-specific code.

License: CC0. Stdlib only.
"""
import math
import json
import hashlib
import time
from pathlib import Path


LEDGER = Path("CLAIM_TABLE.fab.json")


def back_claims_electrical(ir, geometric_hash, tol_frac=0.05):
    claims = []
    base_scope = f"fab::electrical::{geometric_hash}"

    # ---- passive element claims ----
    for i, el in enumerate(ir.elements):
        scope = f"{base_scope}::el{i}"
        var_name = {"store_flow":   "L",
                    "store_effort": "C",
                    "dissipate":    "R"}[el.kind]
        payload = {
            "scope":       scope,
            "rate_var":    f"{var_name}_value",
            "kind":        "passive",
            "value":       el.parameter,
            "tol_frac":    tol_frac,
            "geometry":    el.geometry,
            "measurement": _measurement_for(var_name),
            "failure":     _failure_for(var_name),
            "provenance":  "backends/electrical.py",
        }
        payload["id"] = _h(payload)
        claims.append(payload)

    # ---- composite: LC resonance(s) ----
    Ls = [e.parameter for e in ir.elements if e.kind == "store_flow"]
    Cs = [e.parameter for e in ir.elements if e.kind == "store_effort"]
    Rs = [e.parameter for e in ir.elements if e.kind == "dissipate"]
    for k, (L, C) in enumerate(zip(Ls, Cs)):
        f0 = 1.0 / (2*math.pi*math.sqrt(L*C))
        scope = f"{base_scope}::LC{k}"
        payload = {
            "scope":       scope,
            "rate_var":    "resonance_freq_Hz",
            "kind":        "composite",
            "value":       f0,
            "tol_frac":    tol_frac * 2,    # compounded tolerance
            "measurement": "AC sweep V(out)/I(in); peak in |Z| at f₀",
            "failure":     "stray capacitance / lead inductance shifts f₀; "
                           "self-resonance of inductor caps the usable band",
            "provenance":  "claim_back_electrical.py",
            "L_index": k, "C_index": k,
        }
        payload["id"] = _h(payload)
        claims.append(payload)

        if k < len(Rs):
            R = Rs[k]
            Q = (1.0/R)*math.sqrt(L/C) if R > 0 else float("inf")
            scope_q = f"{base_scope}::Q{k}"
            payload = {
                "scope":       scope_q,
                "rate_var":    "Q_factor",
                "kind":        "composite",
                "value":       Q,
                "tol_frac":    0.20,
                "measurement": "half-power bandwidth of |Z| peak",
                "failure":     "ESR of cap, DCR of inductor, "
                               "skin effect at HF",
                "provenance":  "claim_back_electrical.py",
            }
            payload["id"] = _h(payload)
            claims.append(payload)
    return claims


def append_electrical_claims(claims, path: Path = LEDGER):
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
        "R": "DC ohmmeter OR slope of V vs I at low current",
        "L": "AC bridge OR LCR meter at 1 kHz; impedance |Z|=ωL",
        "C": "AC bridge OR LCR meter at 1 kHz; |Z|=1/(ωC)",
    }[var]


def _failure_for(var):
    return {
        "R": "self-heating drift, contact resistance, lead inductance at HF",
        "L": "core saturation, proximity/skin loss, self-capacitance -> SRF",
        "C": "dielectric absorption, ESR, voltage coefficient",
    }[var]
