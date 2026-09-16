#!/usr/bin/env python3
"""py_octree: the Engine's adaptive octree path, as an implementation of the harness contract.

Thin adapter. The algorithm is Engine/spatial_grid.py + Engine/simd_optimizer.py, unchanged;
this file only reads the spec, times the compute, answers the probes by nearest leaf sample,
and calls contract.finish(). Needs numpy (declared in MANIFEST.json).
"""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "harness"))
import contract  # noqa: E402


def main(argv):
    spec_path, out_path = contract.impl_args(argv)
    spec = contract.read_spec(spec_path)
    import numpy as np
    from Engine.simd_optimizer import SIMDOptimizer
    from Engine.spatial_grid import SpatialGrid

    t0 = time.perf_counter()
    grid, simd = SpatialGrid(), SIMDOptimizer()
    pts, E, B = [], [], []
    for region in grid.adaptiveDecomposition(spec["bounds"], spec["sources"]):
        res = simd.calculateFieldChunk({"points": region["points"]}, spec["sources"])
        pts.extend(res["points"]); E.extend(res["electricField"]); B.extend(res["magneticField"])
    wall = time.perf_counter() - t0

    # answer the probes: nearest leaf sample point (the octree's representation of the field)
    P = np.asarray(pts, dtype=float)
    Ea, Ba = np.asarray(E, dtype=float), np.asarray(B, dtype=float)
    probes = np.asarray(spec["probes"], dtype=float)
    d2 = ((probes[:, None, :] - P[None, :, :]) ** 2).sum(-1)
    idx = np.argmin(d2, axis=1)
    contract.finish(out_path, wall, len(pts),
                    {"E": Ea[idx].tolist(), "B": Ba[idx].tolist()},
                    notes="probes answered by nearest leaf sample; the octree emits one point per leaf (ENG-5)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
