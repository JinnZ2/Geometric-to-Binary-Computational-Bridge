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
# Bit layout per field line  : polarity(1) + curv_sign(1) + curv_mag_gray(3) + B_mag_gray(3) = 8
# Bit layout per current elem: I_mag_gray(3) + B_biot_gray(3) + flow_sign(1)               = 7
# Bit layout per resonance   : constructive(1) + res_mag_gray(3)                            = 4
# Summary (when field_lines present): flux_sign(1) + flux_mag_gray(3) + pressure_gray(3)   = 7

print("\n=== MagneticBridgeEncoder ===")

import importlib.util as _ilu
_mag_spec = _ilu.spec_from_file_location(
    "magnetic_encoder",
    os.path.join(ROOT, "magnetic-bridge", "magnetic_encoder.py")
)
_mag_mod = _ilu.module_from_spec(_mag_spec)
_mag_spec.loader.exec_module(_mag_mod)
MagneticBridgeEncoder      = _mag_mod.MagneticBridgeEncoder
biot_savart_magnitude      = _mag_mod.biot_savart_magnitude
magnetic_flux              = _mag_mod.magnetic_flux
magnetic_pressure          = _mag_mod.magnetic_pressure
larmor_frequency           = _mag_mod.larmor_frequency
_gray_bits                 = _mag_mod._gray_bits
_B_BANDS                   = _mag_mod._B_BANDS
_KAPPA_BANDS               = _mag_mod._KAPPA_BANDS
_PRESSURE_BANDS            = _mag_mod._PRESSURE_BANDS
_FLUX_BANDS                = _mag_mod._FLUX_BANDS
_RES_BANDS                 = _mag_mod._RES_BANDS
MU_0                       = _mag_mod.MU_0

enc = MagneticBridgeEncoder()
check(enc.modality == "magnetic", "Modality is 'magnetic'")

# ── Test 1: field lines without explicit magnitude ─────────────────
# 3 lines × 8 bits + 3 resonance × 4 bits + 7 summary = 43 bits
data = {
    "field_lines": [
        {"curvature": 0.2, "direction": "N"},   # magnitude defaults to 0.0
        {"curvature": -0.5, "direction": "S"},
        {"curvature": 0.8, "direction": "N"},
    ],
    "resonance_map": [0.7, -0.3, 0.1]
}
enc.from_geometry(data)
bits = enc.to_binary()
check(len(bits) == 43, f"Expected 43 bits (3×8 + 3×4 + 7), got {len(bits)}")
check(all(b in '01' for b in bits), "Output is valid binary string")

# Section 1 — polarity bits (index 0, 8, 16 of each 8-bit line)
check(bits[0]  == '1', "Line 0 polarity N = 1")
check(bits[8]  == '0', "Line 1 polarity S = 0")
check(bits[16] == '1', "Line 2 polarity N = 1")

# Section 1 — curvature sign bits (index 1, 9, 17)
check(bits[1]  == '1', "Line 0 curv_sign: 0.2 > 0 = 1")
check(bits[9]  == '0', "Line 1 curv_sign: -0.5 < 0 = 0")
check(bits[17] == '1', "Line 2 curv_sign: 0.8 > 0 = 1")

# Section 1 — curvature magnitude Gray bands (bits 2-4, 10-12, 18-20)
# 0.2 m⁻¹ → κ band 2 → Gray(2)=3="011"
check(bits[2:5]   == '011', "Line 0 curv_mag Gray(2)='011' for κ=0.2")
# 0.5 m⁻¹ → κ band 3 → Gray(3)=2="010"
check(bits[10:13] == '010', "Line 1 curv_mag Gray(3)='010' for κ=0.5")
# 0.8 m⁻¹ → κ band 3 → Gray(3)=2="010"
check(bits[18:21] == '010', "Line 2 curv_mag Gray(3)='010' for κ=0.8")

# Section 1 — B magnitude Gray bands (bits 5-7, 13-15, 21-23)
# magnitude=0.0 (default) → B band 0 → Gray(0)=0="000"
check(bits[5:8]   == '000', "Line 0 B_mag Gray(0)='000' for B=0.0T")
check(bits[13:16] == '000', "Line 1 B_mag Gray(0)='000' for B=0.0T")
check(bits[21:24] == '000', "Line 2 B_mag Gray(0)='000' for B=0.0T")

# Section 3 — resonance (starts at bit 24, 4 bits each)
check(bits[24] == '1', "Resonance 0.7 constructive = 1")
check(bits[25:28] == '111', "Resonance |0.7| → band 5 → Gray(5)='111'")
check(bits[28] == '0', "Resonance -0.3 destructive = 0")
check(bits[29:32] == '011', "Resonance |0.3| → band 2 → Gray(2)='011'")
check(bits[32] == '1', "Resonance 0.1 constructive = 1")
check(bits[33:36] == '000', "Resonance |0.1| → band 0 → Gray(0)='000'")

# Section 4 — summary (starts at bit 36; B_mean=0 → flux=0, pressure=0)
check(bits[36]    == '1',   "Summary flux_sign: Φ=0.0 ≥ 0 = 1")
check(bits[37:40] == '000', "Summary flux_mag Gray(0)='000' for Φ=0")
check(bits[40:43] == '000', "Summary pressure Gray(0)='000' for P=0")

# ── Test 2: with explicit magnitude + current element (Biot-Savart) ─
# 1 line × 8 + 1 element × 7 + 1 resonance × 4 + 7 summary = 26 bits
physics_data = {
    "field_lines": [
        {"direction": "N", "curvature": 1.5, "magnitude": 0.001},  # B = 1 mT
    ],
    "current_elements": [
        # 1 A wire along +z at x=1m → Biot-Savart gives B=1e-7 T at origin
        {"current": 1.0, "dl": [0.0, 0.0, 1.0], "position": [1.0, 0.0, 0.0]},
    ],
    "resonance_map": [0.6],
}
enc_p = MagneticBridgeEncoder()
enc_p.from_geometry(physics_data)
bits_p = enc_p.to_binary()
check(len(bits_p) == 26, f"Physics test: expected 26 bits, got {len(bits_p)}")

# Field line bits (0-7)
check(bits_p[0]   == '1',   "Physics: polarity N = 1")
check(bits_p[1]   == '1',   "Physics: curv_sign 1.5 > 0 = 1")
check(bits_p[2:5] == '110', "Physics: κ=1.5 → band 4 → Gray(4)='110'")
check(bits_p[5:8] == '010', "Physics: B=0.001T → band 3 → Gray(3)='010'")

# Current element bits (8-14): I=1A → band 5 → Gray(5)=7="111"
#   Biot-Savart: B = (μ₀/4π)·I/r² = 1e-7·1/1 = 1e-7 T → band 1 → Gray(1)="001"
#   dl_z=1.0 > 0 → flow_sign=1
check(bits_p[8:11]  == '111', "Physics: I=1A → I band 5 → Gray(5)='111'")
check(bits_p[11:14] == '001', "Physics: Biot-Savart 1e-7T → B band 1 → Gray(1)='001'")
check(bits_p[14]    == '1',   "Physics: dl_z=1.0 > 0 → flow_sign=1")

# Resonance bits (15-18): 0.6 constructive, |0.6| → band 4 → Gray(4)=6="110"
check(bits_p[15]    == '1',   "Physics: resonance 0.6 constructive = 1")
check(bits_p[16:19] == '110', "Physics: |0.6| → band 4 → Gray(4)='110'")

# Summary bits (19-25): B_mean=0.001T
#   flux = 0.001·1.0·cos(0) = 0.001 Wb → band 4 → Gray(4)="110"
#   pressure = (0.001)²/(2μ₀) ≈ 0.398 Pa → band 3 → Gray(3)="010"
check(bits_p[19]    == '1',   "Physics summary: flux ≥ 0 = 1")
check(bits_p[20:23] == '110', "Physics summary: Φ=0.001Wb → band 4 → Gray(4)='110'")
check(bits_p[23:26] == '010', "Physics summary: P≈0.398Pa → band 3 → Gray(3)='010'")

# ── Physics equation unit tests ──────────────────────────────────────
import math as _math

# Biot-Savart: wire along z at x=1m, current=1A
#   r_vec = (-1,0,0), r² = 1, dl=(0,0,1), dl·r = 0, sin(α) = 1
#   B = (μ₀/4π)·I/r² = 1e-7 T
B_bs = biot_savart_magnitude(1.0, [0.0, 0.0, 1.0], [1.0, 0.0, 0.0])
check(abs(B_bs - 1e-7) < 1e-15, f"Biot-Savart: 1A at 1m = 1e-7 T (got {B_bs:.3e})")

# Biot-Savart: wire parallel to r → sin(α)=0 → B=0
B_parallel = biot_savart_magnitude(10.0, [1.0, 0.0, 0.0], [2.0, 0.0, 0.0])
check(abs(B_parallel) < 1e-20, "Biot-Savart: parallel dl and r → B = 0")

# Biot-Savart: zero current → B = 0
check(biot_savart_magnitude(0.0, [0,0,1], [1,0,0]) == 0.0, "Biot-Savart: I=0 → B=0")

# Biot-Savart: element at origin → B = 0
check(biot_savart_magnitude(5.0, [0,0,1], [0,0,0]) == 0.0, "Biot-Savart: r=0 → B=0")

# Magnetic flux: Φ = B·A·cos(θ)
check(abs(magnetic_flux(0.5, 2.0, 0.0)   - 1.0)        < 1e-10, "Flux: 0.5T, 2m², 0rad = 1.0 Wb")
check(abs(magnetic_flux(1.0, 1.0, _math.pi/2)) < 1e-10, "Flux: B⊥normal (π/2) = 0 Wb")
check(abs(magnetic_flux(2.0, 3.0, _math.pi/3) - 3.0)    < 1e-10, "Flux: 2T, 3m², π/3 = 3.0 Wb")

# Magnetic pressure: P = B²/(2μ₀)
P_1T = magnetic_pressure(1.0)
expected_P = 1.0 / (2.0 * MU_0)
check(abs(P_1T - expected_P) / expected_P < 1e-10, f"Pressure: B=1T → B²/2μ₀ = {expected_P:.2f} Pa")
check(magnetic_pressure(0.0) == 0.0, "Pressure: B=0 → 0 Pa")

# Larmor frequency: ω_L = eB/(2mₑ)
import math as _m
E = 1.602176634e-19
Me = 9.1093837015e-31
wL_expected = E * 0.5 / (2 * Me)
check(abs(larmor_frequency(0.5) - wL_expected) / wL_expected < 1e-10,
      f"Larmor: B=0.5T → ω_L = {wL_expected:.4e} rad/s")
check(larmor_frequency(0.0) == 0.0, "Larmor: B=0 → ω_L=0")

# ── Gray code property: adjacent bands differ by exactly 1 bit ───────
def _hamming(a, b):
    return sum(x != y for x, y in zip(a, b))

all_gray_ok = True
for bands, label in [(_B_BANDS, "B_BANDS"), (_KAPPA_BANDS, "KAPPA_BANDS"),
                     (_PRESSURE_BANDS, "PRESSURE_BANDS")]:
    for i in range(len(bands) - 1):
        v_lo = (bands[i] + bands[i+1]) / 2 if i < len(bands)-1 else bands[i]
        v_hi = (bands[i+1] + (bands[i+2] if i+2 < len(bands) else bands[i+1]*10)) / 2
        b_lo = _gray_bits(v_lo, bands)
        b_hi = _gray_bits(v_hi, bands)
        if b_lo != b_hi and _hamming(b_lo, b_hi) != 1:
            all_gray_ok = False
check(all_gray_ok, "Gray code: adjacent bands all differ by exactly 1 bit")

# ── Report and edge cases ─────────────────────────────────────────────
report = enc.report()
check(report["modality"] == "magnetic", "Report modality")
check(report["bits"] == 43, "Report bit count = 43")
check(len(report["checksum"]) == 64, "Report has SHA256 checksum")

# Empty data → no sections → empty string
enc_empty = MagneticBridgeEncoder()
enc_empty.from_geometry({"field_lines": [], "resonance_map": []})
check(enc_empty.to_binary() == "", "Empty data produces empty output")

# No geometry raises ValueError
enc_none = MagneticBridgeEncoder()
try:
    enc_none.to_binary()
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
