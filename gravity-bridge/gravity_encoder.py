# Gravity Bridge Encoder
# Direction, curvature, orbital stability, and binding threshold -> binary

from bridge.abstract_encoder import BinaryBridgeEncoder
import numpy as np

class GravityBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes gravitational field states into binary representation.
    - Direction: attraction (inward) = 1, escape (outward) = 0
    - Curvature: concave (positive curvature) = 1, convex = 0
    - Orbit: stable = 1, unstable = 0
    - Binding: bound (E < 0) = 1, unbound (E >= 0) = 0
    """

    def __init__(self):
        super().__init__("gravity")

    def from_geometry(self, geometry_data):
        """
        geometry_data example:
        {
            "vectors": [[0, -9.8], [0, 9.8], ...],  # direction (y<0 => inward)
            "curvature": [1.2, -0.5, ...],         # field curvature
            "orbital_stability": [0.9, 0.2, ...],  # 0–1 scale
            "potential_energy": [-5e7, 1e6, ...]   # J/kg
        }
        """
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if not self.input_geometry:
            raise ValueError("Geometry data not loaded.")

        bits = []

        # Direction: inward (y < 0 or vector points inward)
        for vec in self.input_geometry.get("vectors", []):
            # inward (negative radial or y-component)
            inward = vec[1] < 0 if len(vec) > 1 else vec[0] < 0
            bits.append("1" if inward else "0")

        # Curvature sign: concave (+) vs convex (-)
        for k in self.input_geometry.get("curvature", []):
            bits.append("1" if k > 0 else "0")

        # Orbital stability: stable (>0.5) vs unstable
        for s in self.input_geometry.get("orbital_stability", []):
            bits.append("1" if s >= 0.5 else "0")

        # Binding: potential energy < 0 → bound
        for E in self.input_geometry.get("potential_energy", []):
            bits.append("1" if E < 0 else "0")

        self.binary_output = "".join(bits)
        return self.binary_output

# Example usage (examples/gravity_demo.py)
if __name__ == "__main__":
    encoder = GravityBridgeEncoder()
    sample_geom = {
        "vectors": [[0, -9.8], [0, 9.8], [0, -3.5], [0, 2.0]],
        "curvature": [1.1, -0.6, 0.4, -0.9],
        "orbital_stability": [0.8, 0.3, 0.9, 0.1],
        "potential_energy": [-5e7, 1e6, -1e7, 3e6]
    }
    encoder.from_geometry(sample_geom)
    bitstring = encoder.to_binary()
    print("Bitstring:", bitstring)
    print("Report:", encoder.report())
