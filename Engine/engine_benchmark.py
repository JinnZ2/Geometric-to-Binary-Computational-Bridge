#!/usr/bin/env python3
"""
engine_benchmark.py -- the measured speedup, against a baseline that is run.

    python Engine/engine_benchmark.py
    python Engine/engine_benchmark.py --resolutions 16,24,32 --repeats 5

Needs numpy. Closes the oldest unchecked item on `docs/Implementation_Roadmap.md`
("Add basic benchmarks for EM field problems", Month 1), which stayed unchecked
while every downstream phase target was written in multiples of a number
nothing had timed.

WHAT THIS MEASURES, AND WHAT `PerformanceTracker` MEASURED
----------------------------------------------------------
`PerformanceTracker.geometric_speedup` is `(32**3 / n_points) * symmetry_
reduction` -- a ratio of point counts, times a factor for work the solver does
not skip. No clock enters it, though `total_time` is recorded in the same call.

This file times both paths on the same sources and the same bounds:
`generateUniformGrid(bounds, resolution)` -- which existed and was never called
by the solver -- against `adaptiveDecomposition(bounds, sources)`, each through
the same `SIMDOptimizer`. The ratio of wall times is the speedup. The ratio of
point counts is reported beside it, because the gap between them is the whole
finding (ENG-1).

Field values are compared at the adaptive points nearest the uniform ones, so a
"speedup" that came from computing less of the field would show up as error
rather than as speed.
"""
import argparse
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 2)[0])

from Engine.simd_optimizer import SIMDOptimizer          # noqa: E402
from Engine.spatial_grid import SpatialGrid              # noqa: E402
from Engine.symmetry_detector import SymmetryDetector    # noqa: E402

BOUNDS = {"min": [-2.0, -2.0, -2.0], "max": [2.0, 2.0, 2.0]}

#: The Engine's source schema is {"position", "strength", "type"} -- see
#: SIMDOptimizer.calculateFieldChunk, which dispatches on "type" and reads
#: "strength". A dict carrying "charge"/"current" keys silently falls back to
#: the defaults (1e-9 for a charge, 0.1 A for a current) and computes a field
#: nobody asked for. The first version of this file did exactly that.
CASES = {
    "dipole (asymmetric)": [
        {"position": [0.3, 0.11, -0.7], "strength": 1e-9, "type": "charge"},
        {"position": [1.3, -0.4, 0.2], "strength": -2e-9, "type": "charge"},
    ],
    "quadrupole (2-fold)": [
        {"position": [1.0, 0.0, 0.0], "strength": 1e-9, "type": "charge"},
        {"position": [-1.0, 0.0, 0.0], "strength": 1e-9, "type": "charge"},
        {"position": [0.0, 1.0, 0.0], "strength": 1e-9, "type": "charge"},
        {"position": [0.0, -1.0, 0.0], "strength": 1e-9, "type": "charge"},
    ],
    "wire + charge": [
        {"position": [0.0, 0.0, 0.0], "strength": 1.0, "type": "current",
         "direction": [0, 0, 1]},
        {"position": [0.8, 0.2, 0.0], "strength": 5e-10, "type": "charge"},
    ],
}


def _time(fn, repeats):
    """Best of N. Best, not mean: the minimum is the least contaminated by
    scheduler noise, and a speedup quoted from a mean flatters whichever path
    happened to be interrupted less."""
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return min(ts), statistics.median(ts)


def run_uniform(sources, bounds, resolution, simd=None):
    grid = SpatialGrid()
    simd = simd or SIMDOptimizer()
    points = grid.generateUniformGrid(bounds, resolution)
    res = simd.calculateFieldChunk({"points": points}, sources)
    return res["points"], res["electricField"]


def run_adaptive(sources, bounds, simd=None):
    grid = SpatialGrid()
    simd = simd or SIMDOptimizer()
    pts, ef = [], []
    for region in grid.adaptiveDecomposition(bounds, sources):
        res = simd.calculateFieldChunk({"points": region["points"]}, sources)
        pts.extend(res["points"])
        ef.extend(res["electricField"])
    return pts, ef


def accuracy(uniform_pts, uniform_E, adaptive_pts, adaptive_E):
    """Relative field error at each uniform point, using its nearest adaptive
    neighbour. A path that is fast because it skipped the field lands here."""
    up = np.asarray(uniform_pts, dtype=float)
    ap = np.asarray(adaptive_pts, dtype=float)
    ue = np.linalg.norm(np.asarray(uniform_E, dtype=float), axis=1)
    ae = np.linalg.norm(np.asarray(adaptive_E, dtype=float), axis=1)
    if not len(ap) or not len(up):
        return float("nan"), float("nan")
    idx = np.argmin(((up[:, None, :] - ap[None, :, :]) ** 2).sum(-1), axis=1)
    ref, got = ue, ae[idx]
    scale = np.maximum(np.abs(ref), 1e-30)
    rel = np.abs(got - ref) / scale
    return float(np.median(rel)), float(np.percentile(rel, 90))


def benchmark(resolutions=(16, 24, 32), repeats=3, cases=None, verbose=True):
    cases = cases or CASES
    rows = []
    for name, sources in cases.items():
        det = SymmetryDetector()
        syms = det.findSymmetries(sources, BOUNDS)
        reduction = det.get_reduction_factor(syms)
        a_best, _ = _time(lambda: run_adaptive(sources, BOUNDS), repeats)
        a_pts, a_E = run_adaptive(sources, BOUNDS)
        for res in resolutions:
            u_best, _ = _time(
                lambda: run_uniform(sources, BOUNDS, res), repeats)
            u_pts, u_E = run_uniform(sources, BOUNDS, res)
            med, p90 = accuracy(u_pts, u_E, a_pts, a_E)
            rows.append({
                "case": name, "resolution": res,
                "uniform_points": len(u_pts), "adaptive_points": len(a_pts),
                "point_ratio": len(u_pts) / max(len(a_pts), 1),
                "uniform_s": u_best, "adaptive_s": a_best,
                "measured_speedup": u_best / a_best if a_best else float("nan"),
                "symmetry_reduction_available": reduction,
                "median_rel_err": med, "p90_rel_err": p90,
            })
    if verbose:
        _report(rows)
    return rows


def _report(rows):
    print("MEASURED SPEEDUP -- uniform grid vs adaptive octree, same sources")
    print("  best-of-N wall clock, both paths through the same SIMDOptimizer")
    print()
    print("  %-22s %5s %8s %8s %9s %9s  %9s" %
          ("case", "res", "unif pts", "adap pts", "pt ratio",
           "MEASURED", "med err"))
    for r in rows:
        print("  %-22s %5d %8d %8d %8.1fx %8.2fx  %8.1e" %
              (r["case"], r["resolution"], r["uniform_points"],
               r["adaptive_points"], r["point_ratio"],
               r["measured_speedup"], r["median_rel_err"]))
    print()
    sp = [r["measured_speedup"] for r in rows]
    pr = [r["point_ratio"] for r in rows]
    print("  measured speedup   min %.2fx  median %.2fx  max %.2fx"
          % (min(sp), statistics.median(sp), max(sp)))
    print("  point-count ratio  min %.1fx  median %.1fx  max %.1fx"
          % (min(pr), statistics.median(pr), max(pr)))
    print("  the gap between those two lines is ENG-1: the point-count ratio")
    print("  was reported as a speedup, and no clock entered it.")


def breakdown(sources=None, bounds=None, resolution=32, repeats=5,
              verbose=True):
    """Where the adaptive path's time actually goes (ENG-5).

    The slowdown in ENG-1 is not the geometry. It is that `createRegion`
    emits one sample point per leaf, so the solver makes one numpy call per
    point. This splits the cost so the roadmap item is a measurement rather
    than a multiplier.
    """
    sources = sources or CASES["dipole (asymmetric)"]
    bounds = bounds or BOUNDS
    grid, simd = SpatialGrid(), SIMDOptimizer()
    regions = grid.adaptiveDecomposition(bounds, sources)
    apts = [p for r in regions for p in r["points"]]
    upts = grid.generateUniformGrid(bounds, resolution)

    t_decomp, _ = _time(
        lambda: SpatialGrid().adaptiveDecomposition(bounds, sources), repeats)
    t_ugrid, _ = _time(
        lambda: SpatialGrid().generateUniformGrid(bounds, resolution), repeats)
    t_chunked, _ = _time(
        lambda: [simd.calculateFieldChunk({"points": r["points"]}, sources)
                 for r in regions], repeats)
    t_batched, _ = _time(
        lambda: simd.calculateFieldChunk({"points": apts}, sources), repeats)
    t_uniform, _ = _time(
        lambda: simd.calculateFieldChunk({"points": upts}, sources), repeats)

    out = {
        "regions": len(regions), "adaptive_points": len(apts),
        "uniform_points": len(upts),
        "points_per_region": len(apts) / max(len(regions), 1),
        "decomposition_s": t_decomp, "uniform_grid_s": t_ugrid,
        "field_chunked_s": t_chunked, "field_batched_s": t_batched,
        "field_uniform_s": t_uniform,
        "chunking_overhead": t_chunked / t_batched if t_batched else float("nan"),
        "field_speedup_if_batched": t_uniform / t_batched if t_batched else float("nan"),
        "endtoend_if_batched": ((t_uniform + t_ugrid) / (t_batched + t_decomp)
                                if (t_batched + t_decomp) else float("nan")),
    }
    if verbose:
        print()
        print("WHERE THE TIME GOES  (ENG-5)")
        print("  regions %d for %d points -- %.2f points per region"
              % (out["regions"], out["adaptive_points"],
                 out["points_per_region"]))
        print("  octree decomposition          %.4f s" % t_decomp)
        print("  uniform grid construction     %.4f s" % t_ugrid)
        print("  field, one call per region    %.4f s   <- as the solver does it"
              % t_chunked)
        print("  field, all points one call    %.4f s   <- same points" % t_batched)
        print("  field, uniform grid one call  %.4f s   (%d pts)"
              % (t_uniform, len(upts)))
        print()
        print("  chunking overhead                    %.1fx"
              % out["chunking_overhead"])
        print("  field-eval speedup if batched        %.1fx"
              % out["field_speedup_if_batched"])
        print("  END-TO-END if batched                %.2fx"
              % out["endtoend_if_batched"])
        print("  -- batching alone lands at break-even: the decomposition")
        print("     costs more than the uniform path's entire computation.")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--resolutions", default="16,24,32")
    ap.add_argument("--repeats", type=int, default=3)
    args = ap.parse_args(argv)
    benchmark(tuple(int(x) for x in args.resolutions.split(",")),
              args.repeats)
    breakdown(repeats=args.repeats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
