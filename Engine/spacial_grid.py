# engine/spatial_grid.py

class SpatialGrid:
    def __init__(self):
        self.adaptiveThreshold = 0.1
        self.maxDepth = 6

    def adaptiveDecomposition(self, bounds, sources):
        # Minimal working stub
        return [self.createRegion(bounds, sources)]

    def createRegion(self, bounds, sources):
        return {
            "bounds": bounds,
            "sources": sources,
            "center": [
                (bounds["min"][0] + bounds["max"][0]) / 2,
                (bounds["min"][1] + bounds["max"][1]) / 2,
                (bounds["min"][2] + bounds["max"][2]) / 2
            ],
            "points": [s["position"] for s in sources],
            "fieldIntensity": 1.0
        }
