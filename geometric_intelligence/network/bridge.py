"""
bridge.py -- geometric networks into the fabrication claim ledger.

Each edge becomes a claim about a ratio between two physical measurements;
each cycle becomes a claim about closure; the network gets one integrity
claim. `verify_edge_measurement` scores a measured ratio against a stored
claim as pass / drift / fail.

=====================================================================
AUDIT
=====================================================================
Behaviour is UNCHANGED from the file as supplied.

GB-1  `verify_edge_measurement` divides by the predicted value.
      `delta_pct = 100 * (measured / pred - 1)` raises ZeroDivisionError
      whenever `pred == 0`, and zero is reachable two ways that both occur in
      the shipped demo's own domain: a `rotate` edge declares an angle, and
      an angle of 0 is legal; and an acyclic network's integrity claim has
      value exactly 0.0 (GB-2). Measured: a rotate edge at angle 0 written to
      a ledger and then verified raises immediately.

GB-2  An acyclic design records an integrity claim of zero.
      `network_to_claims` calls `net.audit()`, which returns
      `integrity_score = 0.0` when there are no cycles -- there is nothing to
      be consistent about. `examples/demo.py` does exactly this: three parts
      in a chain L1 -> L2 -> L3, no reverse edges, and the ledger gets
      `integrity_score = 0.000000 +/- 10.0%` with "0/0 cycles consistent".
      A correct design scores worst, and the claim it writes is the one
      GB-1 crashes on. The fix is the same one the field guide already needs:
      build networks with edges in both directions.

GB-3  The integrity claim's failure text describes a different test from the
      one the claim encodes. The record carries `value = integrity_score` and
      `tol_frac = 0.10`, i.e. a two-sided band around the score, while
      `failure` reads "integrity score X below threshold 3.618". A verifier
      implements the band; the text tells a reader to expect a threshold. And
      3.618 is unreachable by that score anyway -- see GI-12.

GB-4  Three tolerances, no source, and a drift band that is not 2x.
      Edge claims default to `tol_frac = 0.05`, cycle claims to `phi^-9`
      (0.0132), the integrity claim to 0.10. None is derived or measured.
      Separately the drift band in `verify_edge_measurement` is
      `[pred*(1-tol)^2, pred*(1+tol)^2]`, not the doubled tolerance it reads
      as: at tol = 0.05 that is [0.9025, 1.1025] against a pass band of
      [0.95, 1.05], which is close, but at tol = 0.5 it is [0.25, 2.25]
      rather than [0, 2].

GB-5  `LEDGER = Path("CLAIM_TABLE.fab.json")` is relative and
      `append_geo_claims` does an unlocked read-modify-write. Both match the
      23 sites in `fabrication/` and inherit the same two problems: the
      ledger written depends on the working directory, and two processes
      appending at once interleave. Not changed here, because changing it in
      one of 24 places would make the split worse rather than better. Open
      problem GI-10.

License: CC0. Stdlib only.
"""
from __future__ import annotations

import json
import time
import hashlib
from pathlib import Path
from typing import Dict, List, Optional

from .core import GeometricNetwork, PHI_INV_9, INTEGRITY_THRESHOLD

LEDGER = Path("CLAIM_TABLE.fab.json")


def network_to_claims(net: GeometricNetwork, scope_prefix: str = "geo",
                      tol_frac: float = 0.05) -> List[Dict]:
    """
    Convert a geometric network into fabrication claims.

    Each edge becomes a claim about the geometric ratio between
    two physical measurements. Each cycle becomes a composite
    claim about self-consistency.
    """
    claims = []
    base = f"fab::geometric::{scope_prefix}"

    # Edge claims: each edge predicts a ratio
    for i, edge in enumerate(net.edges):
        scope = f"{base}::edge{i}"
        if edge.rel_type == "scale":
            rate_var = "scale_factor"
            value = edge.factor
            measurement = f"ratio of {edge.target} measurement to {edge.source} measurement"
            failure = (f"fabrication error: {edge.target} not in scale "
                      f"relation to {edge.source}; check dimensional tolerance")
        elif edge.rel_type == "rotate":
            rate_var = "phase_offset_rad"
            value = edge.factor
            measurement = f"phase difference between {edge.target} and {edge.source}"
            failure = "misalignment or torsional drift in assembly"
        else:
            rate_var = "compose_coeff"
            value = edge.factor
            measurement = f"composite relation {edge.source} -> {edge.target}"
            failure = "coupled degree of freedom not isolated in fixture"

        payload = {
            "scope": scope,
            "rate_var": rate_var,
            "kind": "geometric_edge",
            "value": value,
            "tol_frac": tol_frac,
            "measurement": measurement,
            "failure": failure,
            "provenance": "geometric_intelligence/bridge.py",
            "ts": time.time(),
            "edge": {"source": edge.source, "target": edge.target,
                     "rel_type": edge.rel_type}
        }
        payload["id"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        claims.append(payload)

    # Cycle claims: self-consistency
    cycles = net.find_cycles(max_depth=6)
    for j, (cycle, err) in enumerate(cycles):
        scope = f"{base}::cycle{j}"
        cycle_str = " -> ".join(e.source for e in cycle) + " -> " + cycle[-1].target
        payload = {
            "scope": scope,
            "rate_var": "closure_error",
            "kind": "geometric_composite",
            "value": err,
            "tol_frac": PHI_INV_9,
            "measurement": f"traverse cycle {cycle_str} and compare start/end",
            "failure": (f"geometric inconsistency in cycle; "
                       f"closure error {err:.6f} exceeds φ⁻⁹ ({PHI_INV_9:.6f}); "
                       f"check for thermal expansion, wear, or assembly error"),
            "provenance": "geometric_intelligence/bridge.py",
            "ts": time.time(),
            "cycle": cycle_str
        }
        payload["id"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        claims.append(payload)

    # Integrity claim: overall network health
    audit = net.audit()
    scope = f"{base}::integrity"
    payload = {
        "scope": scope,
        "rate_var": "integrity_score",
        "kind": "geometric_composite",
        "value": audit["integrity_score"],
        "tol_frac": 0.10,
        "measurement": "network-wide geometric consistency check",
        "failure": (f"integrity score {audit['integrity_score']:.4f} below "
                   f"threshold {INTEGRITY_THRESHOLD:.4f}; "
                   f"network has {audit['inconsistent_cycles']} inconsistent cycles"),
        "provenance": "geometric_intelligence/bridge.py",
        "ts": time.time(),
        "audit": audit
    }
    payload["id"] = hashlib.sha256(
        json.dumps(payload, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]
    claims.append(payload)

    return claims


def append_geo_claims(claims: List[Dict], path: Path = LEDGER):
    """Append geometric claims to fabrication ledger."""
    existing = json.loads(path.read_text()) if path.exists() else []
    new_scopes = {c["scope"] for c in claims}
    existing = [e for e in existing if e.get("scope") not in new_scopes]
    existing.extend(claims)
    path.write_text(json.dumps(existing, indent=2, default=str))
    return len(existing)


def verify_edge_measurement(scope_prefix: str, edge_index: int,
                            measured_ratio: float,
                            path: Path = LEDGER) -> Dict:
    """
    Verify a single edge claim against a physical measurement.

    Example: you built two parts that should have a 1.618 length
    ratio. You measure them and pass the ratio here.
    """
    claims = json.loads(path.read_text()) if path.exists() else []
    scope = f"fab::geometric::{scope_prefix}::edge{edge_index}"

    claim = None
    for c in claims:
        if c.get("scope") == scope:
            claim = c
            break

    if claim is None:
        return {"verdict": "unknown", "reason": f"no claim for {scope}"}

    pred = claim["value"]
    tol = claim.get("tol_frac", 0.05)
    lo = pred * (1 - tol)
    hi = pred * (1 + tol)

    if lo <= measured_ratio <= hi:
        verdict = "pass"
    elif lo * (1 - tol) <= measured_ratio <= hi * (1 + tol):
        verdict = "drift"
    else:
        verdict = "fail"

    return {
        "scope": scope,
        "predicted": pred,
        "measured": measured_ratio,
        "delta_pct": round(100 * (measured_ratio / pred - 1), 4),
        "tol_frac": tol,
        "verdict": verdict,
        "ts": time.time()
    }
