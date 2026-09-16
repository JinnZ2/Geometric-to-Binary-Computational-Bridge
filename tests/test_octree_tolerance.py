#!/usr/bin/env python3
"""
OT-1..5: tolerance-driven refinement in Engine/spatial_grid.py (needs numpy).

F1 (README, Performance) is that the shipped octree has no accuracy knob: its leaf set is
fixed by the source layout, so its error is the same whatever is asked for. SpatialGrid's
`error_tol` is the knob. These tests pin what the knob does and does not do:

  OT-1  the default rule is knob-free: the leaf count is identical for every resolution
        argument the Engine could be given, because none reaches it (the F1 record)
  OT-2  with error_tol the leaf count is monotone non-decreasing as the tolerance tightens
  OT-3  a tolerance above the root cell's own estimate leaves the box as one cell
  OT-4  a cell containing a source refines to max_depth; no sources gives one cell
  OT-5  the estimator tracks the quantity it claims to: the measured nearest-sample error at
        the harness probes falls as the tolerance tightens, on the dipole workload, against
        contract.reference_field, the same metric the harness scores with
"""
import json
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "harness"))

import numpy as np  # noqa: E402

import contract  # noqa: E402
from Engine.simd_optimizer import SIMDOptimizer  # noqa: E402
from Engine.spatial_grid import SpatialGrid  # noqa: E402

BOUNDS = {"min": [-2.0, -2.0, -2.0], "max": [2.0, 2.0, 2.0]}
DIPOLE = [{"position": [0.3, 0.11, -0.7], "strength": 1e-9, "type": "charge"},
          {"position": [1.3, -0.4, 0.2], "strength": -2e-9, "type": "charge"}]


def _leaves(grid, sources=DIPOLE):
    return grid.adaptiveDecomposition(BOUNDS, sources)


class TestOT1DefaultHasNoKnob(unittest.TestCase):
    def test_leaf_count_ignores_every_resolution_argument(self):
        counts = {len(SpatialGrid().adaptiveDecomposition(BOUNDS, DIPOLE)) for _ in (8, 16, 32, 64, 128)}
        self.assertEqual(len(counts), 1)          # nothing to pass a resolution to
        self.assertIsNone(SpatialGrid().error_tol)


class TestOT2TolMonotone(unittest.TestCase):
    def test_tightening_never_removes_leaves(self):
        tols = (0.9, 0.7, 0.5, 0.4)
        counts = [len(_leaves(SpatialGrid(error_tol=t, max_depth=8))) for t in tols]
        for a, b in zip(counts, counts[1:]):
            self.assertLessEqual(a, b, counts)
        self.assertGreater(counts[-1], counts[0], counts)


class TestOT3Loose(unittest.TestCase):
    def test_tolerance_above_root_estimate_gives_one_cell(self):
        root_err = SpatialGrid().local_error(BOUNDS, DIPOLE)
        self.assertEqual(len(_leaves(SpatialGrid(error_tol=root_err * 1.01, max_depth=8))), 1)
        self.assertGreater(len(_leaves(SpatialGrid(error_tol=root_err * 0.99, max_depth=8))), 1)


class TestOT4SourceCellAndEmpty(unittest.TestCase):
    def test_source_cell_reaches_max_depth(self):
        depth = 5
        leaves = _leaves(SpatialGrid(error_tol=0.9, max_depth=depth))
        smallest = min(l["size"] for l in leaves)
        root = np.linalg.norm(np.subtract(BOUNDS["max"], BOUNDS["min"]))
        self.assertAlmostEqual(smallest, root / 2 ** depth, places=9)
        # and some smallest cell contains a source
        hit = [l for l in leaves if abs(l["size"] - smallest) < 1e-9
               and any(all(l["bounds"]["min"][k] <= s["position"][k] <= l["bounds"]["max"][k] for k in range(3))
                       for s in DIPOLE)]
        self.assertTrue(hit)

    def test_no_sources_is_one_cell_and_zero_error(self):
        self.assertEqual(SpatialGrid().local_error(BOUNDS, []), 0.0)
        self.assertEqual(len(SpatialGrid(error_tol=0.01, max_depth=8).adaptiveDecomposition(BOUNDS, [])), 1)


class TestOT5EstimatorTracksMeasuredError(unittest.TestCase):
    def test_probe_error_falls_with_tolerance(self):
        with open(os.path.join(ROOT, "harness", "workloads.json"), encoding="utf-8") as fh:
            w = [x for x in json.load(fh)["workloads"] if x["name"] == "dipole"][0]
        spec = contract.make_spec(w, 16)
        ref = contract.reference_field(spec)
        probes = np.asarray(spec["probes"])
        errs = []
        for tol in (0.9, 0.6, 0.4):
            simd = SIMDOptimizer()
            pts, E = [], []
            for region in SpatialGrid(error_tol=tol, max_depth=8).adaptiveDecomposition(spec["bounds"], spec["sources"]):
                r = simd.calculateFieldChunk({"points": region["points"]}, spec["sources"])
                pts.extend(r["points"]); E.extend(r["electricField"])
            P, Ea = np.asarray(pts), np.asarray(E)
            idx = [int(np.argmin(((p - P) ** 2).sum(1))) for p in probes]
            errs.append(contract.accuracy(ref, {"E": Ea[idx].tolist(), "B": [[0, 0, 0]] * len(idx)})["E"])
        self.assertGreater(errs[0], errs[1])
        self.assertGreater(errs[1], errs[2])


if __name__ == "__main__":
    unittest.main()
