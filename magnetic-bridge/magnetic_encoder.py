# Magnetic Bridge Encoder
# Polarity → binary, field curvature → binary, resonance → binary flips

from bridge.abstract_encoder import BinaryBridgeEncoder
import numpy as np

class MagneticBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes magnetic field geometry into binary representation.
    - Polarity (N/S) → 0/1
    - Field line curvature (convex/concave) → 0/1
    - Resonance (constructive/destructive) → 0/1
    """

    def __init__(self):
        super().__init__("magnetic")

    def from_geometry(self, geometry_data):
        """
        geometry_data example:
        {
            "field_lines": [{"curvature": 0.4, "direction": "N"}, ...],
            "resonance_map": [0.9, -0.2, ...]
        }
        """
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if not self.input_geometry:
            raise ValueError("Geometry data not loaded.")

        bits = []

        # Polarity → 0/1
        for line in self.input_geometry.get("field_lines", []):
            bit = "1" if line["direction"].upper() == "N" else "0"
            bits.append(bit)

        # Curvature sign → 0 if convex, 1 if concave
        for line in self.input_geometry.get("field_lines", []):
            bit = "1" if line["curvature"] > 0 else "0"
            bits.append(bit)

        # Resonance map → 1 if constructive (>0), 0 if destructive (<0)
        for val in self.input_geometry.get("resonance_map", []):
            bit = "1" if val > 0 else "0"
            bits.append(bit)

        self.binary_output = "".join(bits)
        return self.binary_output

# Example usage (can live in examples/magnetic_demo.py)
if __name__ == "__main__":
    encoder = MagneticBridgeEncoder()
    sample_geom = {
        "field_lines": [
            {"curvature": 0.2, "direction": "N"},
            {"curvature": -0.5, "direction": "S"},
        ],
        "resonance_map": [0.7, -0.3]
    }
    encoder.from_geometry(sample_geom)
    bitstring = encoder.to_binary()
    print("Bitstring:", bitstring)
    print("Report:", encoder.report())
