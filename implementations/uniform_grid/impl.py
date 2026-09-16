#!/usr/bin/env python3
"""uniform_grid: the Engine's uniform-grid path, as a PEER implementation of the harness contract.

Not a reference point: accuracy is judged for it exactly as for every other impl, against
contract.reference_field() at the spec's probes. Thin adapter over Engine/spatial_grid.py and
Engine/simd_optimizer.py, unchanged. Needs numpy (declared in MANIFEST.json).
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

    r = int(spec["resolution"])
    t0 = time.perf_counter()
    points = SpatialGrid().generateUniformGrid(spec["bounds"], r)
    res = SIMDOptimizer().calculateFieldChunk({"points": points}, spec["sources"])
    wall = time.perf_counter() - t0

    # answer the probes: nearest grid point by index arithmetic (the grid is regular)
    lo = np.asarray(spec["bounds"]["min"], dtype=float)
    hi = np.asarray(spec["bounds"]["max"], dtype=float)
    probes = np.asarray(spec["probes"], dtype=float)
    ijk = np.rint((probes - lo) / (hi - lo) * (r - 1)).astype(int).clip(0, r - 1)
    P = np.asarray(res["points"], dtype=float)
    # generateUniformGrid orders points as the meshgrid it builds; recover the flat index
    # from the point coordinates rather than assuming the order
    axis = [np.linspace(lo[k], hi[k], r) for k in range(3)]
    key = {tuple(np.round(p, 9)): i for i, p in enumerate(P)}
    flat = [key[tuple(np.round([axis[0][i], axis[1][j], axis[2][k]], 9))] for i, j, k in ijk]
    Ea, Ba = np.asarray(res["electricField"], dtype=float), np.asarray(res["magneticField"], dtype=float)
    contract.finish(out_path, wall, len(points),
                    {"E": Ea[flat].tolist(), "B": Ba[flat].tolist()},
                    notes="probes answered by nearest grid point")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
