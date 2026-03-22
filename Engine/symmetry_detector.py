# engine/symmetry_detector.py
#
# Detects exploitable symmetries in source configurations to reduce
# redundant field calculations. Supported symmetry types:
#   - Reflective (mirror across a plane)
#   - Rotational (n-fold around an axis)
#   - Translational (periodic repetition)

import numpy as np


class SymmetryDetector:
    def __init__(self, position_tol=1e-4, magnitude_tol=1e-4):
        self.position_tol = position_tol
        self.magnitude_tol = magnitude_tol

    def findSymmetries(self, sources, bounds):
        """
        Detect symmetries in a list of sources.

        Args:
            sources: list of dicts with 'position', 'strength', 'type'
            bounds: dict with 'min' and 'max' keys (3-element lists)

        Returns:
            list of symmetry dicts, each with:
                'type': 'reflective' | 'rotational'
                'axis' or 'plane': symmetry element description
                'reduction_factor': how much computation can be saved
        """
        if len(sources) < 2:
            return []

        symmetries = []
        positions = np.array([s["position"] for s in sources])
        strengths = np.array([s.get("strength", 1.0) for s in sources])
        types = [s.get("type", "charge") for s in sources]

        centroid = np.mean(positions, axis=0)

        # Check reflective symmetries across each axis through the centroid
        for axis_idx, axis_name in enumerate(["x", "y", "z"]):
            if self._check_reflection(positions, strengths, types, centroid, axis_idx):
                symmetries.append({
                    "type": "reflective",
                    "plane": axis_name,
                    "center": centroid.tolist(),
                    "reduction_factor": 2.0
                })

        # Check rotational symmetries (2-fold, 3-fold, 4-fold) around each axis
        for axis_idx, axis_name in enumerate(["x", "y", "z"]):
            axis_vec = np.zeros(3)
            axis_vec[axis_idx] = 1.0
            for n_fold in [2, 3, 4, 6]:
                if self._check_rotation(positions, strengths, types, centroid, axis_vec, n_fold):
                    symmetries.append({
                        "type": "rotational",
                        "axis": axis_name,
                        "center": centroid.tolist(),
                        "n_fold": n_fold,
                        "reduction_factor": float(n_fold)
                    })
                    break  # highest fold found for this axis is sufficient

        return symmetries

    def _check_reflection(self, positions, strengths, types, center, axis_idx):
        """Check if sources are symmetric under reflection across a plane."""
        reflected = positions.copy()
        reflected[:, axis_idx] = 2 * center[axis_idx] - reflected[:, axis_idx]

        return self._configurations_match(positions, strengths, types,
                                          reflected, strengths, types)

    def _check_rotation(self, positions, strengths, types, center, axis, n_fold):
        """Check if sources are symmetric under n-fold rotation around axis."""
        angle = 2 * np.pi / n_fold
        rotated = self._rotate_points(positions - center, axis, angle) + center

        return self._configurations_match(positions, strengths, types,
                                          rotated, strengths, types)

    def _rotate_points(self, points, axis, angle):
        """Rotate points around an axis by angle (Rodrigues' formula)."""
        axis = axis / np.linalg.norm(axis)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)

        # Rotation matrix via Rodrigues
        K = np.array([
            [0, -axis[2], axis[1]],
            [axis[2], 0, -axis[0]],
            [-axis[1], axis[0], 0]
        ])
        R = np.eye(3) + sin_a * K + (1 - cos_a) * (K @ K)

        return (R @ points.T).T

    def _configurations_match(self, pos_a, str_a, types_a, pos_b, str_b, types_b):
        """Check if two source configurations are equivalent (permutation match)."""
        n = len(pos_a)
        if n != len(pos_b):
            return False

        matched = [False] * n
        for i in range(n):
            found = False
            for j in range(n):
                if matched[j]:
                    continue
                dist = np.linalg.norm(pos_a[i] - pos_b[j])
                if (dist < self.position_tol and
                        abs(str_a[i] - str_b[j]) < self.magnitude_tol and
                        types_a[i] == types_b[j]):
                    matched[j] = True
                    found = True
                    break
            if not found:
                return False
        return True

    def get_reduction_factor(self, symmetries):
        """Calculate total computation reduction from detected symmetries."""
        if not symmetries:
            return 1.0
        # Use the best single symmetry (they don't always compose)
        return max(s["reduction_factor"] for s in symmetries)
