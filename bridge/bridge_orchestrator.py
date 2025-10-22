# Bridge Orchestrator
# Dynamically runs any domain encoder and merges their outputs
# into a unified cross-domain convergence vector.

import importlib
import hashlib
from pathlib import Path
from bridge.abstract_encoder import BinaryBridgeEncoder

class BridgeOrchestrator:
    """
    Central manager for all domain bridge encoders.
    Handles:
      - dynamic loading of encoders
      - unified bitstream aggregation
      - metadata + checksum tracking
    """

    def __init__(self):
        self.registry = {}
        self.results = {}
        self.master_bitstring = ""

    def register_encoder(self, name: str, module_path: str, class_name: str):
        """Register an encoder dynamically by its import path."""
        self.registry[name] = {"module": module_path, "class": class_name}

    def load_encoder(self, name: str) -> BinaryBridgeEncoder:
        """Dynamically import encoder class and instantiate it."""
        if name not in self.registry:
            raise ValueError(f"Encoder '{name}' not registered.")
        entry = self.registry[name]
        module = importlib.import_module(entry["module"])
        encoder_class = getattr(module, entry["class"])
        return encoder_class()

    def run_encoder(self, name: str, geometry_data: dict):
        """Instantiate, run, and store output for one domain."""
        encoder = self.load_encoder(name)
        encoder.from_geometry(geometry_data)
        bitstring = encoder.to_binary()
        self.results[name] = {
            "bits": bitstring,
            "checksum": encoder.checksum(bitstring),
            "length": len(bitstring),
        }
        return bitstring

    def aggregate(self):
        """Merge all domain bitstrings into a single convergence vector."""
        merged = "".join([r["bits"] for r in self.results.values()])
        self.master_bitstring = merged
        return merged

    def global_checksum(self):
        """Return overall checksum of the merged vector."""
        return hashlib.sha256(self.master_bitstring.encode("utf-8")).hexdigest()

    def report(self):
        """Full orchestration report."""
        return {
            "domains": list(self.results.keys()),
            "individual": self.results,
            "total_bits": len(self.master_bitstring),
            "global_checksum": self.global_checksum() if self.master_bitstring else None
        }


# Example orchestrator use (examples/orchestrator_demo.py)
if __name__ == "__main__":
    orchestrator = BridgeOrchestrator()

    # Register all domains
    orchestrator.register_encoder("magnetic", "magnetic_bridge.magnetic_encoder", "MagneticBridgeEncoder")
    orchestrator.register_encoder("light", "light_bridge.light_encoder", "LightBridgeEncoder")
    orchestrator.register_encoder("sound", "sound_bridge.sound_encoder", "SoundBridgeEncoder")
    orchestrator.register_encoder("gravity", "gravity_bridge.gravity_encoder", "GravityBridgeEncoder")
    orchestrator.register_encoder("electric", "electric_bridge.electric_encoder", "ElectricBridgeEncoder")

    # Minimal demo data for each domain
    demo_inputs = {
        "magnetic": {"field_lines":[{"curvature":0.5,"direction":"N"}], "resonance_map":[0.8]},
        "light": {"polarization":["H"],"spectrum_nm":[600],"interference_intensity":[0.9],"photon_spin":["R"]},
        "sound": {"phase_radians":[0.1],"frequency_hz":[440],"amplitude":[0.8],"resonance_index":[0.9]},
        "gravity": {"vectors":[[0,-9.8]],"curvature":[1.0],"orbital_stability":[0.8],"potential_energy":[-1e7]},
        "electric": {"charge":[1],"current_A":[0.02],"voltage_V":[1.2],"conductivity_S":[1e-3]},
    }

    # Run all encoders
    for name, data in demo_inputs.items():
        orchestrator.run_encoder(name, data)

    # Aggregate to unified vector
    convergence_vector = orchestrator.aggregate()
    print("Unified bitstring:", convergence_vector)
    print("Report:", orchestrator.report())
