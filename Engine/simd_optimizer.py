# engine/simd_optimizer.py
#
# Vectorized EM field computation using numpy as a SIMD-like batch engine.
# Processes chunks of evaluation points against all sources simultaneously,
# computing Coulomb electric fields and Biot-Savart magnetic fields.

import numpy as np

# Coulomb constant (N m^2 / C^2)
K_E = 8.9875517873681764e9
# Permeability of free space / 4pi (T m / A)
MU_OVER_4PI = 1e-7


class SIMDOptimizer:
    def __init__(self, vector_width=8):
        self.vector_width = vector_width

    def calculateFieldChunk(self, chunk, sources):
        """
        Compute E and B fields at all points in a chunk from all sources.
        Uses numpy broadcasting for vectorized (SIMD-style) computation.

        Args:
            chunk: dict with 'points' (list of [x,y,z])
            sources: list of source dicts

        Returns:
            dict with 'points', 'electricField', 'magneticField', 'simdEfficiency'
        """
        points = np.array(chunk["points"])  # (N, 3)
        n_points = len(points)

        if n_points == 0 or len(sources) == 0:
            return {
                "points": chunk["points"],
                "electricField": [],
                "magneticField": [],
                "simdEfficiency": 0.0
            }

        E_total = np.zeros((n_points, 3))
        B_total = np.zeros((n_points, 3))

        for source in sources:
            src_type = source.get("type", "charge")

            if src_type == "charge":
                E = self._electric_field_charge(points, source)
                E_total += E

            elif src_type == "current":
                E, B = self._fields_current(points, source)
                E_total += E
                B_total += B

        # SIMD efficiency: fraction of vector lanes used effectively
        # With numpy, we process n_points at once; efficiency is how well
        # that maps to vector_width lanes
        utilized = n_points
        total_lanes = ((n_points + self.vector_width - 1) // self.vector_width) * self.vector_width
        simd_eff = (utilized / total_lanes) * 100.0 if total_lanes > 0 else 0.0

        return {
            "points": points.tolist(),
            "electricField": E_total.tolist(),
            "magneticField": B_total.tolist(),
            "simdEfficiency": float(simd_eff)
        }

    def _electric_field_charge(self, points, source):
        """
        Coulomb electric field from a point charge.
        E = k_e * q / r^2 * r_hat

        Args:
            points: (N, 3) array of evaluation points
            source: dict with 'position' and 'strength' (charge in C)

        Returns:
            (N, 3) electric field vectors
        """
        q = source.get("strength", 1e-9)
        src_pos = np.array(source["position"])

        # Displacement vectors from source to each point
        r_vec = points - src_pos  # (N, 3)
        r_mag = np.linalg.norm(r_vec, axis=1, keepdims=True)  # (N, 1)

        # Avoid division by zero at source location
        r_mag = np.maximum(r_mag, 1e-10)

        # E = k_e * q * r_hat / r^2
        E = K_E * q * r_vec / (r_mag ** 3)

        return E

    def _fields_current(self, points, source):
        """
        Fields from a current element using Biot-Savart law.
        Approximates a current segment as a finite wire.

        B = (mu_0 / 4pi) * I * dl x r_hat / r^2

        Args:
            points: (N, 3) array of evaluation points
            source: dict with 'start', 'end', 'strength' (current in A)

        Returns:
            tuple of (E, B) each (N, 3) — E is zero for static currents
        """
        I = source.get("strength", 0.1)
        start = np.array(source.get("start", source["position"]))
        end = np.array(source.get("end", [p + 1 for p in source["position"]]))

        dl = end - start  # current element direction
        midpoint = (start + end) / 2

        r_vec = points - midpoint  # (N, 3)
        r_mag = np.linalg.norm(r_vec, axis=1, keepdims=True)
        r_mag = np.maximum(r_mag, 1e-10)
        r_hat = r_vec / r_mag

        # Biot-Savart: dB = (mu_0/4pi) * I * (dl x r_hat) / r^2
        dl_cross_r = np.cross(dl, r_hat)  # (N, 3)
        B = MU_OVER_4PI * I * dl_cross_r / (r_mag ** 2)

        # Static current produces no electric field
        E = np.zeros_like(points)

        return E, B
