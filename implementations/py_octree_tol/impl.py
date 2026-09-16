#!/usr/bin/env python3
"""py_octree_tol: the Engine's octree with TOLERANCE-DRIVEN refinement (SpatialGrid.error_tol).

Identical to py_octree except that SpatialGrid is built with error_tol=spec["tolerance"] and
max_depth=8, so the leaf set is decided by an estimated local error instead of by distance to
the nearest source. The field evaluation is py_octree's, one numpy call per leaf, so a change
in the matched-accuracy ratio is the refinement rule and nothing else. Needs numpy.
"""
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "harness"))
import contract  # noqa: E402

MAX_DEPTH = 8


def main(argv):
    spec_path, out_path = contract.impl_args(argv)
    spec = contract.read_spec(spec_path)
    tol = spec.get("tolerance")
    if tol is None:
        raise contract.ContractError("py_octree_tol needs spec['tolerance'] (manifest knob=tolerance)")
    import numpy as np
    from Engine.simd_optimizer import SIMDOptimizer
    from Engine.spatial_grid import SpatialGrid

    t0 = time.perf_counter()
    grid, simd = SpatialGrid(error_tol=float(tol), max_depth=MAX_DEPTH), SIMDOptimizer()
    pts, E, B = [], [], []
    for region in grid.adaptiveDecomposition(spec["bounds"], spec["sources"]):
        res = simd.calculateFieldChunk({"points": region["points"]}, spec["sources"])
        pts.extend(res["points"]); E.extend(res["electricField"]); B.extend(res["magneticField"])
    wall = time.perf_counter() - t0

    P = np.asarray(pts, dtype=float)
    Ea, Ba = np.asarray(E, dtype=float), np.asarray(B, dtype=float)
    probes = np.asarray(spec["probes"], dtype=float)
    idx = np.empty(len(probes), dtype=int)
    for k in range(0, len(probes), 64):                      # blocked: (64, n_pts, 3) at a time
        d2 = ((probes[k:k + 64, None, :] - P[None, :, :]) ** 2).sum(-1)
        idx[k:k + 64] = np.argmin(d2, axis=1)
    contract.finish(out_path, wall, len(pts),
                    {"E": Ea[idx].tolist(), "B": Ba[idx].tolist()},
                    notes=f"error_tol={tol}, max_depth={MAX_DEPTH}; probes answered by nearest leaf sample; "
                          "one numpy call per leaf kept on purpose (ENG-5)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
