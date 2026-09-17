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
  OT-6  criterion="error": field_at reproduces contract.reference_field to 1e-9 on both
        probe sets, so the estimator judges what the harness scores; the leaf count is
        monotone in the tolerance; no sources gives one cell
  OT-7  criterion="error" terminates at the depth cap and SAYS SO: depth_capped > 0 at a
        tight tolerance, every capped leaf is at max_depth and carries the flag, and the
        count is 0 at a tolerance the root satisfies. The magnitude criterion's count is the
        record of why it was replaced: its proxy diverges at a source, so it caps too
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
        for crit, est in (("magnitude", SpatialGrid.local_error), ("error", SpatialGrid.local_error_field)):
            root_err = est(SpatialGrid(), BOUNDS, DIPOLE)
            self.assertEqual(len(_leaves(SpatialGrid(error_tol=root_err * 1.01, max_depth=8, criterion=crit))), 1, crit)
            self.assertGreater(len(_leaves(SpatialGrid(error_tol=root_err * 0.99, max_depth=8, criterion=crit))), 1, crit)


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



class TestOT6ErrorCriterion(unittest.TestCase):
    def test_field_at_matches_the_harness_reference(self):
        with open(os.path.join(ROOT, "harness", "workloads.json"), encoding="utf-8") as fh:
            ws = json.load(fh)["workloads"]
        for w in ws:
            spec = contract.make_spec(w, 8)
            for probes in (spec["probes"][:40], spec["probes_weighted"][:40]):
                ref = contract.reference_field(spec, probes)
                for i, p in enumerate(probes):
                    E, B = SpatialGrid.field_at(p, spec["sources"])
                    for k in range(3):
                        self.assertAlmostEqual(E[k], ref["E"][i][k], delta=1e-9 * (1 + abs(ref["E"][i][k])))
                        self.assertAlmostEqual(B[k], ref["B"][i][k], delta=1e-9 * (1 + abs(ref["B"][i][k])))

    def test_leaf_count_monotone_and_empty_is_one_cell(self):
        counts = [len(_leaves(SpatialGrid(error_tol=t, max_depth=6, criterion="error"))) for t in (2.0, 1.0, 0.7, 0.5)]
        for a, b in zip(counts, counts[1:]):
            self.assertLessEqual(a, b, counts)
        self.assertGreater(counts[-1], counts[0])
        self.assertEqual(len(SpatialGrid(error_tol=0.1, max_depth=6, criterion="error").adaptiveDecomposition(BOUNDS, [])), 1)

    def test_unknown_criterion_is_refused(self):
        with self.assertRaises(ValueError):
            SpatialGrid(error_tol=0.5, criterion="vibes")


class TestOT7DepthCapIsReported(unittest.TestCase):
    def test_capped_leaves_are_counted_flagged_and_at_max_depth(self):
        g = SpatialGrid(error_tol=0.5, max_depth=5, criterion="error")
        leaves = g.adaptiveDecomposition(BOUNDS, DIPOLE)
        self.assertGreater(g.depth_capped, 0)
        flagged = [l for l in leaves if l.get("depth_capped")]
        self.assertEqual(len(flagged), g.depth_capped)
        self.assertTrue(all(l["depth"] == 5 for l in flagged))
        # every capped leaf still exceeds the tolerance by the estimator's own measure
        self.assertTrue(all(g.local_error_field(l["bounds"], DIPOLE) > 0.5 for l in flagged))

    def test_no_cap_when_the_root_satisfies_the_tolerance(self):
        g = SpatialGrid(error_tol=50.0, max_depth=5, criterion="error")
        self.assertEqual(len(g.adaptiveDecomposition(BOUNDS, DIPOLE)), 1)
        self.assertEqual(g.depth_capped, 0)

    def test_magnitude_criterion_caps_too_and_is_counted(self):
        g = SpatialGrid(error_tol=0.5, max_depth=5, criterion="magnitude")
        g.adaptiveDecomposition(BOUNDS, DIPOLE)
        self.assertGreater(g.depth_capped, 0)

if __name__ == "__main__":
    unittest.main()
