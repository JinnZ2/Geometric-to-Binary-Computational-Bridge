"""
helmholtz_loop.py  (fabrication/tests/)

FALSIFIABLE END-TO-END DEMO.

Spec a Helmholtz resonator geometrically, lower it, emit fab
artifacts, and write claims. Then a human (you, at a fuel stop)
can 3D-print or bottle-mock it and measure resonance with any
phone mic. If measured f ∈ tol band -> bridge verified for this
substrate. If not -> claim_back.failure tells us where to look.

License: CC0. Stdlib only.
"""
import os
import sys

# Put fabrication/ on sys.path so we can import siblings directly.
sys.path.insert(0,
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hashlib
import json
from dataclasses import dataclass
from math import pi

from lowering import lower
from backends.acoustic import helmholtz_freq, with_tolerance
from emit.stl import emit_helmholtz_stl
from emit.spice_acoustic import emit_spice
from claim_back import back_claim, append_ledger


# --- spec the geometry (mm, then SI) -----------------------------
spec = {
    "cavity_volume_mL": 250.0,     # ~ soda-bottle scale
    "neck_length_mm":   30.0,
    "neck_radius_mm":   7.5,
}
V       = spec["cavity_volume_mL"] * 1e-6           # m^3
L_neck  = spec["neck_length_mm"]   * 1e-3
r_neck  = spec["neck_radius_mm"]   * 1e-3
A_neck  = pi * r_neck**2

# --- predicted resonance from first principles ------------------
f0      = helmholtz_freq(A_neck, L_neck, V)
f0_band = with_tolerance(f0, frac=0.08)             # 8% fab tol

# --- build geometric graph (placeholder dataclass for demo) -----
@dataclass
class Node:
    primitive: str
    geometry: dict


@dataclass
class Graph:
    nodes: list
    edges: list


graph = Graph(
    nodes=[
        Node("cavity", {"volume": V}),
        Node("neck",   {"length": L_neck, "area": A_neck}),
    ],
    edges=[(0, 1)],
)

ir = lower(graph, domain="acoustic")

# --- emit artifacts ---------------------------------------------
stl   = emit_helmholtz_stl(
    cavity_r=(V * 3 / (4 * pi))**(1/3),   # sphere-equiv (or set cylinder)
    cavity_h=0.10,
    neck_r=r_neck,
    neck_h=L_neck,
)
spice = emit_spice(ir, source_amp=1.0)

# --- claims (substrate-scoped ledger) ---------------------------
geo_hash = hashlib.sha256(
    json.dumps(spec, sort_keys=True).encode()
).hexdigest()[:12]
claims   = back_claim(ir, artifact_path="resonator.stl",
                     geometric_hash=geo_hash)

# add the COMPOSITE claim (the one a human can actually measure)
claims.append({
    "scope":       f"fab::acoustic::{geo_hash}",
    "rate_var":    "resonance_freq_Hz",
    "kind":        "composite",
    "value":       f0,
    "bounds":      f0_band[1],
    "geometry":    spec,
    "measurement": "tap cavity once; FFT of mic recording; peak = f0",
    "failure":     "if measured f outside band: (a) check end-correction, "
                   "(b) leak at neck-cavity joint, (c) air-temp drift",
    "provenance":  "backends/acoustic.py::helmholtz_freq",
})

n = append_ledger(claims)
print(f"f0 predicted = {f0:.1f} Hz  band = {f0_band[1]}  "
      f"ledger entries total = {n}")
print(f"\nSTL ({len(stl)} bytes), first 200 chars:")
print(stl[:200] + "...")
print(f"\nSPICE netlist ({len(spice)} bytes):")
print(spice)
