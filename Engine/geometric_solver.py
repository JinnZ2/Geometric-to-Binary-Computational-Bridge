# engine/geometric_solver.py
#
# Main solver orchestrating spatial decomposition, symmetry detection,
# and vectorized field computation. Produces the field data consumed
# by the frontend visualization.
#
# =====================================================================
# AUDIT -- ENG-1..6
# =====================================================================
# The performance numbers this module reported were the load-bearing figures
# in docs/Implementation_Roadmap.md, where every phase target was written as a
# multiple of them ("10x-100x", "100x-1000x", "1000x+"). The roadmap's one
# unchecked Month-1 item was "Add basic benchmarks for EM field problems", and
# it stayed unchecked. So the multiples had no measurement under them.
#
# Engine/engine_benchmark.py is that benchmark. Every number below is measured
# and reproduced by Engine/falsifiers_engine.py.
#
#   ENG-1  `geometric_speedup` was (32**3 / n_points) * symmetry_reduction --
#          a ratio of point counts, times a factor for work that is not
#          skipped. No clock entered it, though `total_time` is recorded in
#          the same call. Timed against a uniform baseline on the same
#          sources, the adaptive path runs at 0.02x-0.48x, i.e. between 2x and
#          50x SLOWER, while the metric reported 15x-33x faster.
#          Renamed to `point_ratio`; the report says "fewer points (not
#          timed)" and names the benchmark.
#
#   ENG-2  `naive_points` was hardcoded to 32**3 while `resolution` was a
#          documented parameter ("grid resolution per axis for uniform
#          fallback") that reached nothing -- there is no uniform fallback
#          path, `adaptiveDecomposition` always runs. Measured: resolution
#          16, 32 and 64 gave identical n_points and an identical reported
#          speedup. Fixed: the baseline is the resolution the caller asked
#          for. Fourth instance of the unread-parameter shape, after GR-2's
#          `bands_per_octave`, GLY-3's `sub_glyphs` and ASF-13's
#          `exploration_rate`.
#
#   ENG-3  The ratio was multiplied by `symmetry_reduction`, which the call
#          site's own comment describes as not taken: "we compute all but
#          report the potential reduction". Measured, a symmetric
#          configuration reported 1.50x MORE speedup while taking 1.89x more
#          wall clock -- the metric moved opposite to the truth. The factor
#          is kept under the name `symmetry_reduction_available`.
#
#   ENG-4  `averageSpeedup` reported the last run, not an average, while
#          `history` accumulated every run and was read by nothing. Two runs
#          at 15.24 and 22.88 reported 22.9x against a true mean of 19.06.
#
#   ENG-5  RECORDED, NOT FIXED. `SpatialGrid.createRegion` returns exactly one
#          sample point per leaf region, so the solver calls
#          `calculateFieldChunk` once per point -- 2150 numpy calls on
#          1-element arrays. Measured: the same points in one call take
#          0.0022 s against 0.0616 s chunked, a 28x overhead, and that is the
#          whole of the slowdown in ENG-1. Batching them is a real 25x on the
#          field evaluation. It is not done here because the octree
#          decomposition itself costs 0.0634 s against the uniform path's
#          0.0657 s total, so batching alone lands at break-even (1.00x) and
#          the decomposition has to come down too. Both numbers are in
#          docs/Implementation_Roadmap.md as the near-term item, with the
#          measurement rather than a multiplier.
#
#   ENG-6  RECORDED, NOT FIXED. `simdEfficiency` is
#          n_points / (ceil(n_points/8) * 8), a function of the array length
#          alone. With one point per region every chunk has length 1, so it
#          reports 12.5% for every configuration ever run -- measured
#          identical for 1 charge and for 4. It becomes informative only once
#          ENG-5 is addressed, which is why it is reported with the constancy
#          stated rather than silently.

import time
import numpy as np

from Engine.symmetry_detector import SymmetryDetector
from Engine.spatial_grid import SpatialGrid
from Engine.simd_optimizer import SIMDOptimizer


class GeometricEMSolver:
    def __init__(self):
        self.sources = []
        self.fieldData = None
        self.performanceMetrics = PerformanceTracker()
        self.symmetryDetector = SymmetryDetector()
        self.spatialGrid = SpatialGrid()
        self.simdOptimizer = SIMDOptimizer()

    def calculateElectromagneticField(self, sources, bounds, resolution=32):
        """
        Compute electromagnetic fields across a 3D domain.

        Pipeline:
            1. Detect symmetries in source configuration
            2. Adaptively decompose space (octree near sources, coarse far away)
            3. Compute E and B fields at all grid points (vectorized)
            4. Aggregate results and track performance

        Args:
            sources: list of source dicts
            bounds: dict with 'min' and 'max' (3-element lists)
            resolution: grid resolution per axis for uniform fallback

        Returns:
            dict with 'electricField', 'magneticField', 'points', 'symmetries'
        """
        self.sources = sources
        t_start = time.perf_counter()

        if not sources:
            self.fieldData = {
                "electricField": [],
                "magneticField": [],
                "points": [],
                "symmetries": []
            }
            return self.fieldData

        # 1. Symmetry detection
        t_sym = time.perf_counter()
        symmetries = self.symmetryDetector.findSymmetries(sources, bounds)
        reduction = self.symmetryDetector.get_reduction_factor(symmetries)
        t_sym = time.perf_counter() - t_sym

        # 2. Spatial decomposition
        t_grid = time.perf_counter()
        regions = self.spatialGrid.adaptiveDecomposition(bounds, sources)
        t_grid = time.perf_counter() - t_grid

        # If symmetry detected, we only need to compute a fraction of regions
        # then mirror/rotate results. For now, we compute all but report
        # the potential reduction.
        effective_regions = len(regions)

        # 3. Vectorized field computation across all regions
        t_field = time.perf_counter()
        all_points = []
        all_E = []
        all_B = []
        total_simd_eff = 0.0

        for region in regions:
            chunk = {"points": region["points"]}
            result = self.simdOptimizer.calculateFieldChunk(chunk, sources)
            all_points.extend(result["points"])
            all_E.extend(result["electricField"])
            all_B.extend(result["magneticField"])
            total_simd_eff += result["simdEfficiency"]

        avg_simd_eff = total_simd_eff / len(regions) if regions else 0.0
        t_field = time.perf_counter() - t_field

        t_total = time.perf_counter() - t_start

        # 4. Update performance metrics
        self.performanceMetrics.record(
            total_time=t_total,
            symmetry_time=t_sym,
            grid_time=t_grid,
            field_time=t_field,
            n_points=len(all_points),
            n_regions=effective_regions,
            simd_efficiency=avg_simd_eff,
            symmetry_reduction=reduction,
            resolution=resolution,
            symmetries_found=len(symmetries)
        )

        self.fieldData = {
            "electricField": all_E,
            "magneticField": all_B,
            "points": all_points,
            "symmetries": symmetries,
            "numRegions": effective_regions
        }
        return self.fieldData


class PerformanceTracker:
    def __init__(self):
        self.totalSolutions = 0
        self.totalTime = 0.0
        self.history = []
        self._last = {}

    def record(self, total_time, symmetry_time, grid_time, field_time,
               n_points, n_regions, simd_efficiency, symmetry_reduction,
               symmetries_found, resolution=32):
        """Record metrics from a solver run.

        ENG-1/2/3. What this computes is a POINT-COUNT RATIO: how many points
        a uniform grid at `resolution` would have carried, over how many the
        adaptive decomposition actually evaluated. It is not a speedup and no
        clock enters it -- `total_time` sits in this same call and is not used
        for it. For a speedup, run `Engine/engine_benchmark.py`, which times
        both paths; measured, the adaptive path is currently SLOWER (ENG-5).

        Two corrections to what this used to compute:

          * `naive_points` was hardcoded to 32**3 while `resolution` was a
            documented parameter that reached nothing. The baseline is now the
            resolution the caller actually asked for.
          * the ratio was multiplied by `symmetry_reduction`, a saving the
            solver explicitly does not take -- see the comment at the call
            site, "we compute all but report the potential reduction". A
            symmetric configuration therefore reported 1.50x more "speedup"
            while taking 1.89x more wall clock. The factor is still recorded,
            under a name that says it is available rather than taken.
        """
        self.totalSolutions += 1
        self.totalTime += total_time

        baseline_points = max(int(resolution), 1) ** 3
        actual_points = max(n_points, 1)
        point_ratio = baseline_points / actual_points

        self._last = {
            "total_time": total_time,
            "symmetry_time": symmetry_time,
            "grid_time": grid_time,
            "field_time": field_time,
            "n_points": n_points,
            "n_regions": n_regions,
            "resolution": resolution,
            "baseline_points": baseline_points,
            "simd_efficiency": simd_efficiency,
            "symmetry_reduction_available": symmetry_reduction,
            "symmetries_found": symmetries_found,
            "point_ratio": point_ratio,
        }
        self.history.append(self._last.copy())

    def getEfficiencyReport(self):
        """Return metrics dict matching the format the frontend expects.

        ENG-4. `averageSpeedup` reported `self._last` -- the most recent run --
        while `history` accumulated every run and was read by nothing. Two runs
        at 15.24 and 22.88 reported 22.9x against a true mean of 19.06. It is
        now the mean over history, and it is labelled as a point ratio rather
        than a speedup, because that is what it is (ENG-1).

        ENG-6. `simdEfficiency` is `n_points / ceil(n_points/8)*8`, a function
        of the array length alone. The decomposition emits one point per leaf
        region (ENG-5), so every chunk has length 1 and this is 1/8 = 12.5%
        for every configuration ever run. Reported with that stated rather
        than as a measurement.
        """
        if not self._last:
            return {
                "averageSpeedup": "N/A",
                "simdEfficiency": "N/A",
                "symmetryReduction": "N/A",
                "solutionsComputed": self.totalSolutions,
                "totalComputeTime": "0.00s",
                "measuredSpeedup": "not measured",
                "pointRatio": "N/A",
            }

        last = self._last
        ratios = [h["point_ratio"] for h in self.history] or [0.0]
        mean_ratio = sum(ratios) / len(ratios)
        constant_simd = len({round(h["simd_efficiency"], 6)
                             for h in self.history}) == 1

        return {
            # Kept for the frontend panel, restated so it cannot be read as a
            # timing. Engine/engine_benchmark.py is the timing.
            "averageSpeedup": f"{mean_ratio:.1f}x fewer points (not timed)",
            "pointRatio": f"{mean_ratio:.1f}x",
            "measuredSpeedup": "not measured -- run Engine/engine_benchmark.py",
            "simdEfficiency": (f"{last['simd_efficiency']:.1f}%"
                               + (" (constant: one point per region, ENG-6)"
                                  if constant_simd else "")),
            "symmetryReduction": (
                f"{last['symmetry_reduction_available']:.0f}x available, "
                "not exploited (ENG-3)"
                if last["symmetries_found"] > 0 else "none detected"),
            "solutionsComputed": self.totalSolutions,
            "totalComputeTime": f"{self.totalTime:.3f}s",
        }
