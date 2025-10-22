# Sound Bridge Encoder
# Phase, pitch, amplitude, and harmonic resonance -> binary

from bridge.abstract_encoder import BinaryBridgeEncoder
import numpy as np

class SoundBridgeEncoder(BinaryBridgeEncoder):
    """
    Encodes sound/vibrational data into binary representation.
    - Phase: in-phase (Δφ < π/2) = 1, out-of-phase = 0
    - Pitch: high (f >= threshold) = 1, low = 0
    - Amplitude: strong (A >= threshold) = 1, soft = 0
    - Resonance: consonant = 1, dissonant = 0
    """

    def __init__(self, pitch_threshold=440, amp_threshold=0.5):
        """
        pitch_threshold: frequency in Hz (default A4=440)
        amp_threshold: normalized amplitude (0–1)
        """
        super().__init__("sound")
        self.pitch_threshold = pitch_threshold
        self.amp_threshold = amp_threshold

    def from_geometry(self, geometry_data):
        """
        geometry_data example:
        {
            "phase_radians": [0.1, 3.4, 1.2, ...],
            "frequency_hz": [220, 880, 440, ...],
            "amplitude": [0.3, 0.7, 0.6, ...],
            "resonance_index": [0.9, 0.2, 0.75, ...]  # 0–1 scale
        }
        """
        self.input_geometry = geometry_data
        return self

    def to_binary(self):
        if not self.input_geometry:
            raise ValueError("Geometry data not loaded.")

        bits = []

        # Phase: in-phase vs out-of-phase
        for phi in self.input_geometry.get("phase_radians", []):
            bits.append("1" if abs(phi) < np.pi / 2 else "0")

        # Pitch: above or below threshold
        for f in self.input_geometry.get("frequency_hz", []):
            bits.append("1" if f >= self.pitch_threshold else "0")

        # Amplitude: strong vs soft
        for A in self.input_geometry.get("amplitude", []):
            bits.append("1" if A >= self.amp_threshold else "0")

        # Resonance: consonant vs dissonant
        for R in self.input_geometry.get("resonance_index", []):
            bits.append("1" if R >= 0.5 else "0")

        self.binary_output = "".join(bits)
        return self.binary_output

# Example usage (examples/sound_demo.py)
if __name__ == "__main__":
    encoder = SoundBridgeEncoder()
    sample_geom = {
        "phase_radians": [0.1, 3.2, 1.0, 2.9],
        "frequency_hz": [220, 880, 440, 660],
        "amplitude": [0.4, 0.8, 0.3, 0.9],
        "resonance_index": [0.9, 0.2, 0.75, 0.1]
    }
    encoder.from_geometry(sample_geom)
    bitstring = encoder.to_binary()
    print("Bitstring:", bitstring)
    print("Report:", encoder.report())
