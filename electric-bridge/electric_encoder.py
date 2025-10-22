# Electric Bridge Encoder
# Charge polarity, current flow, and potential threshold -> binary

from bridge.abstract_encoder import BinaryBridgeEncoder
import numpy as np

class ElectricBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes electrical field and circuit states into binary representation.
    - Charge: positive (+) = 1, negative (-) = 0
    - Flow: current present (I > 0) = 1, no current = 0
    - Potential: above threshold (V >= Vref) = 1, below = 0
    - Conductivity: conducting = 1, insulating = 0
    """

    def __init__(self, Vref=1.0, conduction_threshold=1e-6):
        super().__init__("electric")
        self.Vref = Vref
        self.conduction_threshold = conduction_threshold

    def from_geometry(self, geometry_data):
        """
        geometry_data example:
        {
            "charge": [1, -1, 1, ...],         # sign convention (+/-)
            "current_A": [0.02, 0.0, 0.1, ...],
            "voltage_V": [1.2, 0.4, 3.3, ...],
            "conductivity_S": [5e-3, 0.0, 2e-2, ...]
        }
        """
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if not self.input_geometry:
            raise ValueError("Geometry data not loaded.")

        bits = []

        # Charge polarity
        for q in self.input_geometry.get("charge", []):
            bits.append("1" if q > 0 else "0")

        # Current flow: present vs none
        for I in self.input_geometry.get("current_A", []):
            bits.append("1" if I > 0 else "0")

        # Potential: above or below reference voltage
        for V in self.input_geometry.get("voltage_V", []):
            bits.append("1" if V >= self.Vref else "0")

        # Conductivity: conducting vs insulating
        for sigma in self.input_geometry.get("conductivity_S", []):
            bits.append("1" if sigma >= self.conduction_threshold else "0")

        self.binary_output = "".join(bits)
        return self.binary_output


# Example usage (examples/electric_demo.py)
if __name__ == "__main__":
    encoder = ElectricBridgeEncoder(Vref=1.0)
    sample_geom = {
        "charge": [1, -1, 1, -1],
        "current_A": [0.02, 0.0, 0.1, 0.0],
        "voltage_V": [1.2, 0.8, 3.3, 0.4],
        "conductivity_S": [5e-3, 0.0, 2e-2, 1e-5]
    }
    encoder.from_geometry(sample_geom)
    bitstring = encoder.to_binary()
    print("Bitstring:", bitstring)
    print("Report:", encoder.report())
