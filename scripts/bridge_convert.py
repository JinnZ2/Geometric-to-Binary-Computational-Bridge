"""
bridge_convert.py
Converts .gshape geometric descriptions into binary arrays + optional plots.
"""

import json, re, struct, sys, math
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

def parse_gshape(path):
    params = {}
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"): 
                continue
            key, val = [x.strip() for x in line.split(":", 1)]
            try:
                val = float(val)
            except ValueError:
                pass
            params[key] = val
    return params

def generate_phi_shells(params):
    base = params.get("base_radius", 1.0)
    phi  = params.get("scale_factor", 1.618034)
    layers = int(params.get("layers", 5))
    radii = [base * (phi ** n) for n in range(layers)]
    return np.array(radii, dtype=np.float32)

def write_binary(radii, outfile):
    with open(outfile, "wb") as f:
        for r in radii:
            f.write(struct.pack("f", r))
    print(f"Saved binary radii to {outfile}")

def visualize_shells(radii):
    fig, ax = plt.subplots(figsize=(5,5))
    for r in radii:
        circle = plt.Circle((0,0), r, fill=False, lw=2, alpha=0.6)
        ax.add_artist(circle)
    ax.set_aspect('equal')
    ax.set_xlim(-radii[-1]*1.1, radii[-1]*1.1)
    ax.set_ylim(-radii[-1]*1.1, radii[-1]*1.1)
    ax.set_title("φ-Shell Geometry")
    plt.show()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bridge_convert.py examples/phi_shells.gshape")
        sys.exit(1)

    path = Path(sys.argv[1])
    params = parse_gshape(path)
    radii = generate_phi_shells(params)
    out = path.with_suffix(".bin")
    write_binary(radii, out)
    visualize_shells(radii)
