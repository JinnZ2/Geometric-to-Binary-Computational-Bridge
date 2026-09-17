#!/usr/bin/env python3
"""py_octree_mag: the FIRST tolerance knob, kept for comparison at the same tolerances.

SpatialGrid(error_tol=spec['tolerance'], criterion='magnitude', max_depth=8): split while the
largest symmetric corner/centre ratio of a sum|q|/r^2 magnitude proxy, minus 1, exceeds the
tolerance. The proxy diverges at a point source, so refinement there is unbounded by construction
and only the depth cap stops it; that is why py_octree_tol replaced it. Same evaluation path.
Needs numpy.
"""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "harness"))
import contract  # noqa: E402

MAX_DEPTH = 8


def nearest(P, probes):
    """Index of the nearest sample for each probe; one probe at a time so a 2M-leaf P stays
    one 48 MB temporary rather than a (probes x leaves x 3) block."""
    import numpy as np
    return [int(np.argmin(((P - p) ** 2).sum(1))) for p in probes]


def main(argv):
    spec_path, out_path = contract.impl_args(argv)
    spec = contract.read_spec(spec_path)
    tol = spec.get("tolerance")
    import numpy as np
    from Engine.simd_optimizer import SIMDOptimizer
    from Engine.spatial_grid import SpatialGrid

    t0 = time.perf_counter()
    grid, simd = SpatialGrid(error_tol=float(tol), max_depth=MAX_DEPTH, criterion="magnitude"), SIMDOptimizer()
    pts, E, B = [], [], []
    for region in grid.adaptiveDecomposition(spec["bounds"], spec["sources"]):
        res = simd.calculateFieldChunk({"points": region["points"]}, spec["sources"])
        pts.extend(res["points"]); E.extend(res["electricField"]); B.extend(res["magneticField"])
    wall = time.perf_counter() - t0

    P = np.asarray(pts, dtype=float)
    Ea, Ba = np.asarray(E, dtype=float), np.asarray(B, dtype=float)
    idx = nearest(P, np.asarray(spec["probes"], dtype=float))
    idx_w = nearest(P, np.asarray(spec["probes_weighted"], dtype=float))
    contract.finish(out_path, wall, len(pts),
                    {"E": Ea[idx].tolist(), "B": Ba[idx].tolist(),
                     "E_w": Ea[idx_w].tolist(), "B_w": Ba[idx_w].tolist()},
                    notes=f"error_tol={tol}, criterion=magnitude, max_depth={MAX_DEPTH}; probes answered by nearest leaf sample; one numpy call per leaf kept on purpose (ENG-5)",
                    extra={"depth_capped": int(getattr(grid, "depth_capped", 0))})
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
