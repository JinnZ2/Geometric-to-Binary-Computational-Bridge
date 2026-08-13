"""
emit_bridge.py -- geometric constraints into fabrication constraints.

Derives fabrication parameters FROM a geometric network rather than building
an IR and a network separately: each node becomes a target value with a
tolerance, and the tolerance is modulated by edge weight and by the closure
error of the cycles the node participates in.

=====================================================================
AUDIT
=====================================================================
Behaviour is UNCHANGED from the file as supplied, and it inherits every
finding of the modules it calls. Before using a tolerance out of this file:

  * the closure error it reads is GI-11 -- computed at the single point x = 1,
    so an affine cycle that is wrong everywhere else contributes zero;
  * the edge weight it reads is GI-12 -- author-declared confidence, which in
    `audit()` only ever adds and here only ever tightens;
  * `temp_c` defaults to 15.0 throughout, which is `acoustic_f_correct`'s
    reference and not `thermal_expand`'s (20.0). See TMP-2.

So a constraint emitted here is a target value the network already contained,
with a tolerance derived from two quantities neither of which is measured. The
target is trustworthy; the tolerance is a proposal.

License: CC0. Stdlib only.
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

from .core import GeometricNetwork, PHI, PHI_INV_9


@dataclass
class FabConstraint:
    """A fabrication constraint derived from geometric relations."""
    node_id: str
    target_value: float
    tolerance_frac: float
    domain: str
    var: str
    material: str = "steel"
    temp_c: float = 15.0


def network_to_fab_constraints(net: GeometricNetwork,
                                  base_domain: str = "mechanical",
                                  base_var: str = "length_m",
                                  material: str = "steel",
                                  temp_c: float = 15.0,
                                  base_tol: float = 0.05) -> List[FabConstraint]:
    """
    Derive fabrication constraints from a geometric network.

    For each node, the target value is the node's value.
    For edges, tolerance is tightened or loosened based on
    edge weight (confidence) and the geometric closure error
    of cycles the edge participates in.

    Returns a list of FabConstraint objects that can be fed
    directly to emitters or to the claim backend.
    """
    constraints = []

    # First, audit to find closure errors per edge
    cycles = net.find_cycles(max_depth=6)
    edge_errors: Dict[Tuple[str, str], float] = {}

    for cycle, err in cycles:
        for edge in cycle:
            key = (edge.source, edge.target)
            edge_errors[key] = max(edge_errors.get(key, 0.0), err)

    # Build constraint per node
    for node_id, node in net.nodes.items():
        # Find all edges entering this node to determine tolerance
        incoming = [e for e in net.edges if e.target == node_id]

        if incoming:
            # Tighten tolerance if edges have high confidence and low error
            avg_weight = sum(e.weight for e in incoming) / len(incoming)
            max_err = max(edge_errors.get((e.source, e.target), 0.0) 
                         for e in incoming)

            # Higher weight = tighter tolerance (more confident)
            # Higher error = looser tolerance (less certain)
            tol = base_tol * (1.0 + max_err * 10) / (1.0 + avg_weight)
            tol = max(tol, PHI_INV_9)  # minimum tolerance
            tol = min(tol, 0.5)        # maximum tolerance
        else:
            tol = base_tol

        constraints.append(FabConstraint(
            node_id=node_id,
            target_value=node.value,
            tolerance_frac=tol,
            domain=base_domain,
            var=base_var,
            material=material,
            temp_c=temp_c
        ))

    return constraints


def constraints_to_ir(constraints: List[FabConstraint],
                      domain: str = "mechanical") -> "_I":
    """
    Convert FabConstraints to a fabrication IR.

    Each constraint becomes an element in the IR. The geometric
    relations between nodes become the topology.
    """
    from fabrication.mini import _I, _E, _P

    elements = []
    for c in constraints:
        if c.domain == "mechanical":
            port = _P("mechanical", "v", "F")
            elements.append(_E("store_flow", {"length": c.target_value},
                              c.target_value, port))
        elif c.domain == "electrical":
            port = _P("electrical", "I", "V")
            if c.var == "R_value":
                elements.append(_E("dissipate", {"R": c.target_value},
                                  c.target_value, port))
            elif c.var == "L_value":
                elements.append(_E("store_flow", {"L": c.target_value},
                                  c.target_value, port))
            elif c.var == "C_value":
                elements.append(_E("store_effort", {"C": c.target_value},
                                  c.target_value, port))
        elif c.domain == "acoustic":
            port = _P("acoustic", "Q", "P")
            elements.append(_E("store_effort", {"volume": c.target_value},
                              c.target_value, port))
        elif c.domain == "thermal":
            port = _P("thermal", "qdot", "dT")
            elements.append(_E("dissipate", {"R_th": c.target_value},
                              c.target_value, port))

    return _I(domain, elements)


def constraints_to_claims(constraints: List[FabConstraint],
                          scope_prefix: str = "geo_fab") -> List[Dict]:
    """
    Convert constraints directly to fabrication claims.

    Bypasses the IR step and writes claims that the verifier
    can check against physical measurements.
    """
    import hashlib
    import time
    import json

    claims = []
    for c in constraints:
        scope = f"fab::{c.domain}::{scope_prefix}::{c.node_id}"
        payload = {
            "scope": scope,
            "rate_var": c.var,
            "kind": "geometric_derived",
            "value": c.target_value,
            "tol_frac": c.tolerance_frac,
            "measurement": f"{c.var} of {c.node_id} at {c.temp_c}°C",
            "failure": (f"{c.node_id} out of geometric tolerance; "
                       f"check thermal expansion ({c.material}) or fabrication error"),
            "provenance": "geometric_intelligence/emit_bridge.py",
            "ts": time.time(),
            "temp_c": c.temp_c,
            "material": c.material,
        }
        payload["id"] = hashlib.sha256(
            json.dumps(payload, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]
        claims.append(payload)

    return claims


def emit_geometric_network(net: GeometricNetwork,
                           scope_prefix: str = "geo_fab",
                           domain: str = "mechanical",
                           material: str = "steel",
                           temp_c: float = 15.0,
                           out_dir: str = ".") -> Dict[str, str]:
    """
    One-shot: network → constraints → claims → emit artifacts.

    Returns dict of emitted artifact paths.
    """
    from fabrication.emit import emit_all
    from geometric_intelligence.bridge import append_geo_claims

    constraints = network_to_fab_constraints(
        net, base_domain=domain, material=material, temp_c=temp_c
    )

    # Write claims
    claims = constraints_to_claims(constraints, scope_prefix)
    append_geo_claims(claims)

    # Build IR and emit
    ir = constraints_to_ir(constraints, domain)
    geo_hash = net.hash()[:8]

    return emit_all(ir, geo_hash, name=scope_prefix, out_dir=out_dir)
