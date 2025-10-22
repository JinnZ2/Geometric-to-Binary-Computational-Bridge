# Light Bridge Encoder
# Polarization, spectral band, interference, and photon spin -> binary

from bridge.abstract_encoder import BinaryBridgeEncoder
import numpy as np

class LightBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes optical geometry into binary representation.
    - Polarization: horizontal (H)=0, vertical (V)=1
    - Spectrum: short (λ < 550nm)=0, long (λ >= 550nm)=1
    - Interference: bright fringe=1, dark fringe=0
    - Photon spin: right circular=1, left circular=0
    """

    def __init__(self):
        super().__init__("light")

    def from_geometry(self, geometry_data):
        """
        geometry_data example:
        {
            "polarization": ["H", "V", "H", ...],
            "spectrum_nm": [450, 610, 520, ...],
            "interference_intensity": [0.92, 0.03, 0.51, ...],
            "photon_spin": ["L", "R", "R", ...]
        }
        """
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if not self.input_geometry:
            raise ValueError("Geometry data not loaded.")

        bits = []

        # Polarization mapping
        for p in self.input_geometry.get("polarization", []):
            bits.append("1" if p.upper() == "V" else "0")

        # Spectrum mapping (short vs long wavelength)
        for lam in self.input_geometry.get("spectrum_nm", []):
            bits.append("1" if lam >= 550 else "0")

        # Interference pattern (bright vs dark)
        for I in self.input_geometry.get("interference_intensity", []):
            bits.append("1" if I >= 0.5 else "0")

        # Photon spin (right vs left)
        for s in self.input_geometry.get("photon_spin", []):
            bits.append("1" if s.upper().startswith("R") else "0")

        self.binary_output = "".join(bits)
        return self.binary_output

# Example usage (examples/light_demo.py)
if __name__ == "__main__":
    encoder = LightBridgeEncoder()
    sample_geom = {
        "polarization": ["H", "V", "V", "H"],
        "spectrum_nm": [420, 580, 610, 495],
        "interference_intensity": [0.9, 0.1, 0.6, 0.3],
        "photon_spin": ["L", "R", "R", "L"]
    }
    encoder.from_geometry(sample_geom)
    bitstring = encoder.to_binary()
    print("Bitstring:", bitstring)
    print("Report:", encoder.report())
