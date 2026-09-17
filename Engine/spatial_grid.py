# engine/spacial_grid.py
#
# Adaptive spatial decomposition using an octree. Regions near sources
# are subdivided to higher resolution; distant regions stay coarse.
# This maps naturally to octahedral geometry (8 children per node).

import math

import numpy as np


class SpatialGrid:
    """Adaptive octree.

    Three refinement rules, selected by `error_tol` and `criterion`:

    * `error_tol=None` (the default, and the only rule the Engine ran before 2026-09): refine
      a cell while `size / distance_to_nearest_source > adaptive_threshold` and depth <
      max_depth. This rule reads NOTHING about the field and has no accuracy knob: the leaf
      set is fixed by the source layout and max_depth, so the sample error is the same
      whatever resolution or accuracy is asked for (finding F1, README "Performance").

    * `error_tol=t, criterion="error"` (the default criterion): refine a cell while the
      ESTIMATED LOCAL ERROR exceeds t, where the estimate compares the cell's answer at the
      current level with its answer one level finer:
          coarse = field at the cell centre           (what a nearest-sample answer returns)
          fine_k = field at child centre k, k = 1..8  (what it would return after one split)
          err    = max_k |fine_k - coarse| / |fine_k|       over E, and over B when present
      The field is the real one (Coulomb, current element), not a proxy. The estimate is
      bounded near a source: when |fine_k| >> |coarse| it tends to 1, so a cell holding a
      source refines until max_depth and is then counted in `depth_capped`, reported as a
      first-class quantity rather than an error. With no sources every field is zero, err
      is 0, and the box stays one cell.

    * `error_tol=t, criterion="magnitude"`: the first knob built, kept so the two can be
      compared at the same tolerances. Refine while the largest symmetric ratio of a
      magnitude proxy f(p) = sum_s |strength_s| / |p - pos_s|^2 at the 8 corners to its value
      at the centre, minus 1, exceeds t. f diverges at a point source, so refinement there is
      unbounded by construction and only max_depth stops it (the reason "error" replaced it).
      Its first version used |f_k - f_c| / f_c, capped at 1 when the centre is the closest
      point to a source, so the source cell never refined (tests/test_octree_tolerance.py
      OT-4 caught it).

    After `adaptiveDecomposition`, `depth_capped` holds the number of leaves that still
    exceeded the tolerance at max_depth, and each such region carries `depth_capped: True`.
    """

    CRITERIA = ("error", "magnitude")
    K_E = 8.9875517873681764e9
    MU_OVER_4PI = 1e-7

    def __init__(self, adaptive_threshold=0.5, max_depth=4, error_tol=None, criterion="error"):
        if criterion not in self.CRITERIA:
            raise ValueError("criterion must be one of %r" % (self.CRITERIA,))
        self.adaptive_threshold = adaptive_threshold
        self.max_depth = max_depth
        self.error_tol = error_tol
        self.criterion = criterion
        self.depth_capped = 0

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
        self.depth_capped = 0
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
        capped = False
        if self.error_tol is not None:
            # tolerance-driven: refine while the estimated local error exceeds the tolerance
            err = (self.local_error(bounds, sources) if self.criterion == "magnitude"
                   else self.local_error_field(bounds, sources))
            should_refine = err > self.error_tol and depth < self.max_depth
            capped = err > self.error_tol and depth >= self.max_depth
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
            if capped:
                region["depth_capped"] = True
                self.depth_capped += 1
            region["depth"] = depth
            regions.append(region)

    @staticmethod
    def _magnitude_proxy(point, sources):
        """sum_s |strength_s| / |point - pos_s|^2 : the scale of the field at `point`."""
        f = 0.0
        for src in sources:
            d = point - np.asarray(src["position"], dtype=float)
            f += abs(float(src.get("strength", 1.0))) / (float(d @ d) + 1e-20)
        return f

    @classmethod
    def field_at(cls, point, sources):
        """(E, B) at `point` by direct summation: Coulomb for charges, a current element of
        length dl = end - start (default end = position + (1,1,1)) evaluated at its midpoint
        for currents. The same definitions as harness/contract.reference_field, so the
        estimator judges the quantity the harness scores. Pure Python on purpose: 3-vectors
        as tuples run several times faster than numpy arrays at this size, and the estimator
        is called 9 times per cell visited."""
        px, py, pz = float(point[0]), float(point[1]), float(point[2])
        Ex = Ey = Ez = Bx = By = Bz = 0.0
        for src in sources:
            kind = src.get("type", "charge")
            if kind == "charge":
                sx, sy, sz = src["position"]
                rx, ry, rz = px - sx, py - sy, pz - sz
                m = math.sqrt(rx * rx + ry * ry + rz * rz)
                if m < 1e-10:
                    m = 1e-10
                f = cls.K_E * float(src["strength"]) / (m * m * m)
                Ex += f * rx; Ey += f * ry; Ez += f * rz
            elif kind == "current":
                start = src.get("start", src["position"])
                end = src.get("end", [c + 1 for c in src["position"]])
                dx, dy, dz = end[0] - start[0], end[1] - start[1], end[2] - start[2]
                mx, my, mz = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2, (start[2] + end[2]) / 2
                rx, ry, rz = px - mx, py - my, pz - mz
                m = math.sqrt(rx * rx + ry * ry + rz * rz)
                if m < 1e-10:
                    m = 1e-10
                ux, uy, uz = rx / m, ry / m, rz / m
                f = cls.MU_OVER_4PI * float(src["strength"]) / (m * m)
                Bx += f * (dy * uz - dz * uy); By += f * (dz * ux - dx * uz); Bz += f * (dx * uy - dy * ux)
        return (Ex, Ey, Ez), (Bx, By, Bz)

    @staticmethod
    def _rel_change(fine, coarse):
        nf = math.sqrt(fine[0] ** 2 + fine[1] ** 2 + fine[2] ** 2)
        if nf <= 0.0:
            return 0.0
        d = math.sqrt((fine[0] - coarse[0]) ** 2 + (fine[1] - coarse[1]) ** 2 + (fine[2] - coarse[2]) ** 2)
        return d / nf

    def local_error_field(self, bounds, sources):
        """criterion="error": the largest relative change in the field between the cell's
        centre sample and the sample each of its 8 children would give. 0.0 with no sources."""
        if not sources:
            return 0.0
        bmin, bmax = bounds["min"], bounds["max"]
        cx, cy, cz = (bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2, (bmin[2] + bmax[2]) / 2
        qx, qy, qz = (bmax[0] - bmin[0]) / 4, (bmax[1] - bmin[1]) / 4, (bmax[2] - bmin[2]) / 4
        Ec, Bc = self.field_at((cx, cy, cz), sources)
        worst = 0.0
        for i in range(8):
            child = (cx + (qx if i & 1 else -qx), cy + (qy if i & 2 else -qy), cz + (qz if i & 4 else -qz))
            Ef, Bf = self.field_at(child, sources)
            worst = max(worst, self._rel_change(Ef, Ec), self._rel_change(Bf, Bc))
        return worst

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
