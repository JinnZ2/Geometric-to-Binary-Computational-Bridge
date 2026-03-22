"""
Tests for all bridge encoders (OOP domain bridges).
"""

import sys
import os
import importlib
import importlib.util

# Add project root to path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

passed = 0
failed = 0


def check(condition, label):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS: {label}")
    else:
        failed += 1
        print(f"  FAIL: {label}")


def load_encoder(dir_name, module_name, class_name):
    """Import encoder class from a hyphenated directory."""
    spec = importlib.util.spec_from_file_location(
        module_name,
        os.path.join(ROOT, dir_name, f"{module_name}.py")
    )
    mod = importlib.util.module_from_spec(spec)
    # Ensure bridge.abstract_encoder is importable
    spec.loader.exec_module(mod)
    return getattr(mod, class_name)


# ─── Magnetic Bridge ────────────────────────────────────────────────

print("\n=== MagneticBridgeEncoder ===")
MagneticBridgeEncoder = load_encoder("magnetic-bridge", "magnetic_encoder", "MagneticBridgeEncoder")

enc = MagneticBridgeEncoder()
check(enc.modality == "magnetic", "Modality is 'magnetic'")

# Encode sample data
data = {
    "field_lines": [
        {"curvature": 0.2, "direction": "N"},
        {"curvature": -0.5, "direction": "S"},
        {"curvature": 0.8, "direction": "N"},
    ],
    "resonance_map": [0.7, -0.3, 0.1]
}
enc.from_geometry(data)
bits = enc.to_binary()
check(len(bits) == 9, f"Expected 9 bits (3+3+3), got {len(bits)}")
check(all(b in '01' for b in bits), "Output is valid binary string")

# Polarity: N=1, S=0, N=1
check(bits[0] == '1', "First field line N = 1")
check(bits[1] == '0', "Second field line S = 0")
check(bits[2] == '1', "Third field line N = 1")

# Curvature: 0.2>0=1, -0.5<0=0, 0.8>0=1
check(bits[3] == '1', "Curvature 0.2 > 0 = 1")
check(bits[4] == '0', "Curvature -0.5 < 0 = 0")
check(bits[5] == '1', "Curvature 0.8 > 0 = 1")

# Resonance: 0.7>0=1, -0.3<0=0, 0.1>0=1
check(bits[6] == '1', "Resonance 0.7 = 1")
check(bits[7] == '0', "Resonance -0.3 = 0")
check(bits[8] == '1', "Resonance 0.1 = 1")

# Report
report = enc.report()
check(report["modality"] == "magnetic", "Report modality")
check(report["bits"] == 9, "Report bit count")
check(len(report["checksum"]) == 64, "Report has SHA256 checksum")

# Empty data
enc2 = MagneticBridgeEncoder()
enc2.from_geometry({"field_lines": [], "resonance_map": []})
check(enc2.to_binary() == "", "Empty data produces empty output")

# No geometry raises
enc3 = MagneticBridgeEncoder()
try:
    enc3.to_binary()
    check(False, "to_binary without geometry raises")
except ValueError:
    check(True, "to_binary without geometry raises")


# ─── Light Bridge ───────────────────────────────────────────────────

print("\n=== LightBridgeEncoder ===")
LightBridgeEncoder = load_encoder("light-bridge", "light_encoder", "LightBridgeEncoder")

enc = LightBridgeEncoder()
check(enc.modality == "light", "Modality is 'light'")

data = {
    "polarization": ["H", "V", "V"],
    "spectrum_nm": [420, 580, 610],
    "interference_intensity": [0.9, 0.1, 0.6],
    "photon_spin": ["L", "R", "R"]
}
enc.from_geometry(data)
bits = enc.to_binary()
check(len(bits) == 12, f"Expected 12 bits (3*4), got {len(bits)}")

# Polarization: H=0, V=1, V=1
check(bits[0] == '0', "H polarization = 0")
check(bits[1] == '1', "V polarization = 1")
check(bits[2] == '1', "V polarization = 1")

# Spectrum: 420<550=0, 580>=550=1, 610>=550=1
check(bits[3] == '0', "420nm < 550 = 0")
check(bits[4] == '1', "580nm >= 550 = 1")
check(bits[5] == '1', "610nm >= 550 = 1")


# ─── Sound Bridge ──────────────────────────────────────────────────

print("\n=== SoundBridgeEncoder ===")
import numpy as np  # noqa: E402
SoundBridgeEncoder = load_encoder("sound-bridge", "sound_encoder", "SoundBridgeEncoder")

enc = SoundBridgeEncoder(pitch_threshold=440, amp_threshold=0.5)
check(enc.modality == "sound", "Modality is 'sound'")

data = {
    "phase_radians": [0.1, 3.2],        # in-phase, out-of-phase
    "frequency_hz": [220, 880],          # below, above threshold
    "amplitude": [0.3, 0.8],            # below, above threshold
    "resonance_index": [0.9, 0.2]       # consonant, dissonant
}
enc.from_geometry(data)
bits = enc.to_binary()
check(len(bits) == 8, f"Expected 8 bits (2*4), got {len(bits)}")

# Phase: 0.1 < pi/2 = 1, 3.2 > pi/2 = 0
check(bits[0] == '1', "Phase 0.1 in-phase = 1")
check(bits[1] == '0', "Phase 3.2 out-of-phase = 0")

# Pitch: 220<440=0, 880>=440=1
check(bits[2] == '0', "220Hz < 440 = 0")
check(bits[3] == '1', "880Hz >= 440 = 1")


# ─── Gravity Bridge ────────────────────────────────────────────────

print("\n=== GravityBridgeEncoder ===")
GravityBridgeEncoder = load_encoder("gravity-bridge", "gravity_encoder", "GravityBridgeEncoder")

enc = GravityBridgeEncoder()
check(enc.modality == "gravity", "Modality is 'gravity'")

data = {
    "vectors": [[0, -9.8], [0, 9.8]],
    "curvature": [1.1, -0.6],
    "orbital_stability": [0.8, 0.3],
    "potential_energy": [-5e7, 1e6]
}
enc.from_geometry(data)
bits = enc.to_binary()
check(len(bits) == 8, f"Expected 8 bits (2*4), got {len(bits)}")

# Direction: y<0 = inward=1, y>0 = outward=0
check(bits[0] == '1', "y=-9.8 inward = 1")
check(bits[1] == '0', "y=9.8 outward = 0")

# Curvature: 1.1>0=1, -0.6<0=0
check(bits[2] == '1', "Curvature 1.1 = 1")
check(bits[3] == '0', "Curvature -0.6 = 0")

# Stability: 0.8>=0.5=1, 0.3<0.5=0
check(bits[4] == '1', "Stability 0.8 = 1")
check(bits[5] == '0', "Stability 0.3 = 0")

# Binding: -5e7<0=1, 1e6>0=0
check(bits[6] == '1', "E=-5e7 bound = 1")
check(bits[7] == '0', "E=1e6 unbound = 0")


# ─── Electric Bridge ───────────────────────────────────────────────

print("\n=== ElectricBridgeEncoder ===")
ElectricBridgeEncoder = load_encoder("electric-bridge", "electric_encoder", "ElectricBridgeEncoder")

enc = ElectricBridgeEncoder(Vref=1.0, conduction_threshold=1e-6)
check(enc.modality == "electric", "Modality is 'electric'")

data = {
    "charge": [1, -1],
    "current_A": [0.02, 0.0],
    "voltage_V": [1.2, 0.4],
    "conductivity_S": [5e-3, 0.0]
}
enc.from_geometry(data)
bits = enc.to_binary()
check(len(bits) == 8, f"Expected 8 bits (2*4), got {len(bits)}")

# Charge: +1=1, -1=0
check(bits[0] == '1', "Charge +1 = 1")
check(bits[1] == '0', "Charge -1 = 0")

# Current: 0.02>0=1, 0.0=0
check(bits[2] == '1', "Current 0.02 = 1")
check(bits[3] == '0', "Current 0.0 = 0")

# Voltage: 1.2>=1.0=1, 0.4<1.0=0
check(bits[4] == '1', "Voltage 1.2 >= Vref = 1")
check(bits[5] == '0', "Voltage 0.4 < Vref = 0")


# ─── Bridge Orchestrator ───────────────────────────────────────────

print("\n=== BridgeOrchestrator ===")
from bridge.bridge_orchestrator import BridgeOrchestrator  # noqa: E402
# Register using the hyphenated directory import paths the orchestrator uses
# The orchestrator uses importlib.import_module internally

orch = BridgeOrchestrator()

orch.register_encoder("magnetic", "magnetic-bridge.magnetic_encoder", "MagneticBridgeEncoder")
orch.register_encoder("light", "light-bridge.light_encoder", "LightBridgeEncoder")

mag_data = {"field_lines": [{"curvature": 0.5, "direction": "N"}], "resonance_map": [0.8]}
light_data = {"polarization": ["V"], "spectrum_nm": [600], "interference_intensity": [0.9], "photon_spin": ["R"]}

bits_m = orch.run_encoder("magnetic", mag_data)
check(len(bits_m) > 0, "Magnetic encoder produced bits")
check("magnetic" in orch.results, "Magnetic result stored")

bits_l = orch.run_encoder("light", light_data)
check(len(bits_l) > 0, "Light encoder produced bits")

merged = orch.aggregate()
check(merged == bits_m + bits_l, "Aggregated = magnetic + light")
check(len(orch.global_checksum()) == 64, "Global checksum is SHA256")

report = orch.report()
check(len(report["domains"]) == 2, "Report has 2 domains")
check(report["total_bits"] == len(merged), "Report total_bits correct")

# Unknown encoder
try:
    orch.run_encoder("nonexistent", {})
    check(False, "Unknown encoder raises")
except ValueError:
    check(True, "Unknown encoder raises")


# ─── Summary ────────────────────────────────────────────────────────

print(f"\n{'='*50}")
total = passed + failed
print(f"Results: {passed}/{total} passed, {failed} failed")
if failed == 0:
    print("ALL TESTS PASSED!")
else:
    print(f"WARNING: {failed} test(s) failed")
    exit(1)
