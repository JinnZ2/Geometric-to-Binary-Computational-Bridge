# engine/spacial_grid.py
#
# Adaptive spatial decomposition using an octree. Regions near sources
# are subdivided to higher resolution; distant regions stay coarse.
# This maps naturally to octahedral geometry (8 children per node).

import numpy as np


class SpatialGrid:
    """Adaptive octree.

    Two refinement rules, selected by `error_tol`:

    * `error_tol=None` (the default, and the only rule the Engine has ever run): refine a
      cell while `size / distance_to_nearest_source > adaptive_threshold` and depth <
      max_depth. This rule reads NOTHING about the field and has no accuracy knob: the leaf
      set is fixed by the source layout and max_depth, so the sample error is the same
      whatever resolution or accuracy is asked for (finding F1 of the matched-accuracy
      measurement, README "Performance"; ENG-2/ENG-5).

    * `error_tol=t`: refine a cell while its ESTIMATED LOCAL ERROR exceeds t and depth <
      max_depth. The estimate is the largest relative deviation, over the cell's 8 corners,
      of a field-magnitude proxy from its value at the cell centre, SYMMETRIC in the ratio:
          f(p) = sum_s |strength_s| / |p - pos_s|^2
          err  = max_k ( max(f_k / f_c, f_c / f_k) - 1 )        f_k at corner k, f_c at centre
      That is the factor a nearest-sample answer is wrong by, for a probe anywhere in the
      cell, so driving it below t is what "accuracy t" means for this representation. The
      ratio is taken both ways on purpose: the first version used |f_k - f_c| / f_c, which is
      capped at 1.0 whenever the centre is the closest point to a source, so a cell with a
      source near its centre reported err < 1 and never refined while its neighbours did
      (tests/test_octree_tolerance.py OT-4 caught it). A cell containing a source now has
      err >> 1 and refines to max_depth. With no sources f is 0 everywhere, err is 0, and
      the box stays one cell.
    """

    def __init__(self, adaptive_threshold=0.5, max_depth=4, error_tol=None):
        self.adaptive_threshold = adaptive_threshold
        self.max_depth = max_depth
        self.error_tol = error_tol

    def adaptiveDecomposition(self, bounds, sources):
        """
        Recursively subdivide the domain, refining near sources.

        Args:
            bounds: dict with 'min' and 'max' (3-element lists)
            sources: list of source dicts with 'position' and 'strength'

        Returns:
            list of region dicts, each containing grid points for field eval
        """
        regions = []
        self._subdivide(bounds, sources, depth=0, regions=regions)
        return regions

    def _subdivide(self, bounds, sources, depth, regions):
        """Recursive octree subdivision."""
        bmin = np.array(bounds["min"])
        bmax = np.array(bounds["max"])
        center = (bmin + bmax) / 2
        size = np.linalg.norm(bmax - bmin)

        # Calculate minimum distance from any source to this cell center
        min_dist = float("inf")
        max_strength = 0.0
        for s in sources:
            pos = np.array(s["position"])
            dist = np.linalg.norm(pos - center)
            min_dist = min(min_dist, dist)
            max_strength = max(max_strength, abs(s.get("strength", 1.0)))

        # Field influence metric: should we refine this cell?
        if self.error_tol is not None:
            # tolerance-driven: refine while the estimated local error exceeds the tolerance
            should_refine = self.local_error(bounds, sources) > self.error_tol and depth < self.max_depth
        else:
            # distance-driven: refine if sources are close relative to cell size
            influence = size / (min_dist + 1e-10)
            should_refine = influence > self.adaptive_threshold and depth < self.max_depth

        if should_refine and depth < self.max_depth:
            # Subdivide into 8 octants (octahedral decomposition)
            for i in range(8):
                child_min = np.array([
                    bmin[0] if (i & 1) == 0 else center[0],
                    bmin[1] if (i & 2) == 0 else center[1],
                    bmin[2] if (i & 4) == 0 else center[2],
                ])
                child_max = np.array([
                    center[0] if (i & 1) == 0 else bmax[0],
                    center[1] if (i & 2) == 0 else bmax[1],
                    center[2] if (i & 4) == 0 else bmax[2],
                ])
                child_bounds = {
                    "min": child_min.tolist(),
                    "max": child_max.tolist()
                }
                self._subdivide(child_bounds, sources, depth + 1, regions)
        else:
            # Leaf node: create evaluation region with grid points
            region = self.createRegion(bounds, sources)
            regions.append(region)

    @staticmethod
    def _magnitude_proxy(point, sources):
        """sum_s |strength_s| / |point - pos_s|^2 : the scale of the field at `point`."""
        f = 0.0
        for src in sources:
            d = point - np.asarray(src["position"], dtype=float)
            f += abs(float(src.get("strength", 1.0))) / (float(d @ d) + 1e-20)
        return f

    def local_error(self, bounds, sources):
        """Estimated relative error of answering any probe in the cell with the centre sample:
        the largest relative deviation of the magnitude proxy at the 8 corners from its value
        at the centre. 0.0 with no sources."""
        if not sources:
            return 0.0
        bmin = np.asarray(bounds["min"], dtype=float)
        bmax = np.asarray(bounds["max"], dtype=float)
        centre = (bmin + bmax) / 2
        fc = self._magnitude_proxy(centre, sources)
        if fc <= 0.0:
            return 0.0
        worst = 0.0
        for i in range(8):
            corner = np.array([bmin[0] if (i & 1) == 0 else bmax[0],
                               bmin[1] if (i & 2) == 0 else bmax[1],
                               bmin[2] if (i & 4) == 0 else bmax[2]])
            fk = self._magnitude_proxy(corner, sources)
            ratio = max(fk / fc, fc / fk) if fk > 0.0 else float("inf")
            worst = max(worst, ratio - 1.0)
        return float(worst)

    def createRegion(self, bounds, sources):
        """Create a leaf region with sample points for field evaluation."""
        bmin = np.array(bounds["min"])
        bmax = np.array(bounds["max"])
        center = (bmin + bmax) / 2
        size = np.linalg.norm(bmax - bmin)

        # Single sample point at cell center
        points = [center.tolist()]

        # Estimate field intensity at center for priority sorting
        field_intensity = 0.0
        for s in sources:
            pos = np.array(s["position"])
            dist = np.linalg.norm(pos - center)
            strength = abs(s.get("strength", 1.0))
            field_intensity += strength / (dist * dist + 1e-20)

        return {
            "bounds": bounds,
            "center": center.tolist(),
            "points": points,
            "fieldIntensity": float(field_intensity),
            "size": float(size)
        }

    def generateUniformGrid(self, bounds, resolution):
        """
        Generate a uniform 3D grid of evaluation points.
        Used as fallback when adaptive decomposition isn't needed.

        Args:
            bounds: dict with 'min' and 'max'
            resolution: number of points per axis

        Returns:
            list of [x, y, z] points
        """
        bmin = np.array(bounds["min"])
        bmax = np.array(bounds["max"])

        x = np.linspace(bmin[0], bmax[0], resolution)
        y = np.linspace(bmin[1], bmax[1], resolution)
        z = np.linspace(bmin[2], bmax[2], resolution)

        points = []
        for xi in x:
            for yi in y:
                for zi in z:
                    points.append([float(xi), float(yi), float(zi)])

        return points
