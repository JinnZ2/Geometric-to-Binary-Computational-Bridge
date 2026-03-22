# engine/spacial_grid.py
#
# Adaptive spatial decomposition using an octree. Regions near sources
# are subdivided to higher resolution; distant regions stay coarse.
# This maps naturally to octahedral geometry (8 children per node).

import numpy as np


class SpatialGrid:
    def __init__(self, adaptive_threshold=0.5, max_depth=4):
        self.adaptive_threshold = adaptive_threshold
        self.max_depth = max_depth

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
        # Refine if sources are close relative to cell size
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
