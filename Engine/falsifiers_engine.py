#!/usr/bin/env python3
"""
falsifiers_engine.py -- runnable report for ENG-1..6.

    python Engine/falsifiers_engine.py

Needs numpy. Each line asserts the state the AUDIT header in
`Engine/geometric_solver.py` records -- for a defect that was fixed, that the
fix is still there; for one deliberately left in place, that it is still there
exactly as described. Exits nonzero when any of them stops holding.

ENG-5 and ENG-6 assert DEFECTS. Fixing either is expected to fail this report,
and the response is to amend the finding and the roadmap item that quotes it,
not to delete the check.

Timing checks use generous margins. The point of ENG-1 is a factor of 20 or
more in the wrong direction, not a percentage, so a slow or loaded machine
does not change the verdict.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))

from Engine import engine_benchmark as BM                 # noqa: E402
from Engine.geometric_solver import GeometricEMSolver     # noqa: E402
from Engine.spatial_grid import SpatialGrid               # noqa: E402
from Engine.simd_optimizer import SIMDOptimizer           # noqa: E402

FAILURES = []
CHECKS = []


def check(cid, claim, ok, detail=""):
    CHECKS.append(cid)
    print("  %-8s %-56s %s" % (cid, claim, "holds" if ok else "BROKEN"))
    if detail:
        for line in str(detail).splitlines():
            print("           %s" % line)
    if not ok:
        FAILURES.append(cid)


BOUNDS = BM.BOUNDS
ASYM = BM.CASES["dipole (asymmetric)"]
SYM = BM.CASES["quadrupole (2-fold)"]


def solve(sources, resolution=32):
    s = GeometricEMSolver()
    s.calculateElectromagneticField(sources, BOUNDS, resolution=resolution)
    return s


print("\nWHAT THE REPORTED NUMBER IS")

rows = BM.benchmark(resolutions=(32,), repeats=3, verbose=False)
worst = max(r["point_ratio"] / r["measured_speedup"] for r in rows)
check("ENG-1", "the point ratio overstates the timed speedup by >10x",
      worst > 10,
      "; ".join("%s: ratio %.1fx, measured %.2fx"
                % (r["case"], r["point_ratio"], r["measured_speedup"])
                for r in rows))
check("ENG-1", "every timed case is SLOWER than the uniform baseline",
      all(r["measured_speedup"] < 1.0 for r in rows),
      "measured speedups: %s"
      % ", ".join("%.2fx" % r["measured_speedup"] for r in rows))
rep = solve(ASYM).performanceMetrics.getEfficiencyReport()
check("ENG-1", "the report no longer calls a point ratio a speedup",
      "not timed" in rep["averageSpeedup"]
      and "engine_benchmark" in rep["measuredSpeedup"],
      "averageSpeedup = %r" % rep["averageSpeedup"])

print("\nTHE BASELINE, AND THE RESOLUTION THAT REACHED NOTHING")

last = {res: solve(ASYM, res).performanceMetrics._last for res in (16, 32, 64)}
check("ENG-2", "the baseline now tracks the resolution the caller asked for",
      [last[r]["baseline_points"] for r in (16, 32, 64)]
      == [16 ** 3, 32 ** 3, 64 ** 3]
      and len({last[r]["point_ratio"] for r in (16, 32, 64)}) == 3,
      "; ".join("res %d -> baseline %d, ratio %.2f"
                % (r, last[r]["baseline_points"], last[r]["point_ratio"])
                for r in (16, 32, 64)))
check("ENG-2", "resolution still does not change the adaptive point count",
      len({last[r]["n_points"] for r in (16, 32, 64)}) == 1,
      "n_points = %d at every resolution: adaptiveDecomposition never "
      "receives it, and the 'uniform fallback' the docstring names does not "
      "exist" % last[32]["n_points"])

print("\nA FACTOR FOR WORK THAT IS NOT DONE")

a = solve(ASYM).performanceMetrics._last
c = solve(SYM).performanceMetrics._last


def wall(sources, repeats=3):
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        solve(sources)
        ts.append(time.perf_counter() - t0)
    return min(ts)


check("ENG-3", "symmetry is detected but not exploited",
      c["symmetries_found"] > 0 and c["symmetry_reduction_available"] > 1.0
      and wall(SYM) > wall(ASYM),
      "quadrupole: %d symmetries, %.1fx available, and it takes LONGER "
      "(%.3fs vs %.3fs) -- the call site says 'we compute all but report the "
      "potential reduction'"
      % (c["symmetries_found"], c["symmetry_reduction_available"],
         wall(SYM), wall(ASYM)))
check("ENG-3", "the available factor no longer multiplies the reported ratio",
      abs(c["point_ratio"] - (32 ** 3) / c["n_points"]) < 1e-9,
      "point_ratio is baseline/actual with no symmetry factor in it")
check("ENG-3", "the report says it is available rather than taken",
      "not exploited" in solve(SYM).performanceMetrics
      .getEfficiencyReport()["symmetryReduction"])

print("\nAN AVERAGE THAT WAS THE LAST VALUE")

s = GeometricEMSolver()
s.calculateElectromagneticField(ASYM, BOUNDS, resolution=16)
s.calculateElectromagneticField(SYM, BOUNDS, resolution=32)
hist = [h["point_ratio"] for h in s.performanceMetrics.history]
mean = sum(hist) / len(hist)
reported = float(s.performanceMetrics.getEfficiencyReport()
                 ["pointRatio"].rstrip("x"))
check("ENG-4", "the reported average is the mean over history",
      abs(reported - mean) < 0.05 and abs(hist[-1] - mean) > 0.05,
      "history %s -> mean %.2f, last %.2f, reported %.2f"
      % ([round(h, 2) for h in hist], mean, hist[-1], reported))

print("\nONE POINT PER REGION  (defects left in place, on purpose)")

bd = BM.breakdown(repeats=3, verbose=False)
check("ENG-5", "the decomposition emits exactly one point per leaf region",
      abs(bd["points_per_region"] - 1.0) < 1e-9,
      "%d regions for %d points" % (bd["regions"], bd["adaptive_points"]))
check("ENG-5", "chunking per region costs more than 10x batching them",
      bd["chunking_overhead"] > 10,
      "one call per region %.4f s vs one call for all %.4f s -- %.1fx"
      % (bd["field_chunked_s"], bd["field_batched_s"],
         bd["chunking_overhead"]))
check("ENG-5", "batching alone would not make the path faster overall",
      bd["field_speedup_if_batched"] > 5 and bd["endtoend_if_batched"] < 2.0,
      "field eval would gain %.1fx, but end to end lands at %.2fx: the "
      "octree costs %.4f s against the uniform path's %.4f s total"
      % (bd["field_speedup_if_batched"], bd["endtoend_if_batched"],
         bd["decomposition_s"], bd["field_uniform_s"] + bd["uniform_grid_s"]))

one = solve([{"position": [1, 0, 0], "strength": 1e-9, "type": "charge"}])
four = solve(SYM)
check("ENG-6", "simd efficiency is the same constant for every configuration",
      abs(one.performanceMetrics._last["simd_efficiency"] - 12.5) < 1e-9
      and abs(four.performanceMetrics._last["simd_efficiency"] - 12.5) < 1e-9,
      "1 charge and 4 charges both report 12.5%: with one point per region, "
      "1/8 lanes, always")
check("ENG-6", "the constancy is stated in the report",
      "constant" in one.performanceMetrics.getEfficiencyReport()
      ["simdEfficiency"])

print("\n%d checks over %d findings." % (len(CHECKS), len(set(CHECKS))))
if FAILURES:
    print("BROKEN: %s" % ", ".join(sorted(set(FAILURES))))
    print("A finding stopped holding. Amend the AUDIT header and the roadmap "
          "item that quotes it, rather than deleting the check.")
    raise SystemExit(1)
print("All findings hold as recorded.")
