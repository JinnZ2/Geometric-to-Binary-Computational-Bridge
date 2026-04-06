"""
geometric_bridge.py
===================
Standard library for any AI to read sensors and control actuators
using the Geometric Binary Bridge protocol.

Usage:
    from geometric_bridge import SensorDecoder, ActuatorController
    
    decoder = SensorDecoder()
    data = decoder.decode(binary_stream)
    print(f"Temperature: {data.temperature_c}°C")
    print(f"Confidence: {data.confidence}")
    
    actuator = ActuatorController()
    actuator.set_thermal(50.0)
"""

import struct
import math
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# ----------------------------------------------------------------------
# Protocol constants
# ----------------------------------------------------------------------
MAGIC_NUMBER = 0xGB  # 0x47 0x42 in bytes? We'll use 0x47 for 'G', 0x42 for 'B'
PROTOCOL_VERSION = 1

class Modality(IntEnum):
    HARDWARE = 0
    ELECTRIC = 1
    MAGNETIC = 2
    GRAVITATIONAL = 3
    SPECTRUM = 4
    POLYHEDRAL = 5
    GEIS = 6

class BridgeTarget(IntEnum):
    THERMAL = 0
    ELECTRIC = 1
    MAGNETIC = 2
    LIGHT = 3
    SOUND = 4
    WAVE = 5
    PRESSURE = 6
    CHEMICAL = 7

class DrillDepth(IntEnum):
    PASS = 0
    MONITOR = 1
    ALERT = 3   # Gray-coded: 11 binary
    QUARANTINE = 2  # Gray-coded: 10 binary

# ----------------------------------------------------------------------
# Band tables (from your encoders)
# ----------------------------------------------------------------------
HEALTH_BANDS = [0.0, 0.125, 0.25, 0.375, 0.5, 0.625, 0.75, 0.875]
VOLTAGE_BANDS = [0.0, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 50.0]
CURRENT_BANDS = [0.0, 1e-6, 1e-4, 1e-3, 0.01, 0.1, 1.0, 10.0]
TEMP_BANDS = [-55.0, 25.0, 40.0, 60.0, 85.0, 100.0, 125.0, 175.0]
NOISE_BANDS = [0.0, 0.01, 0.05, 0.1, 0.2, 0.4, 0.7, 1.0]
DRIFT_BANDS = [0.0, 1.0, 10.0, 50.0]
LIFETIME_BANDS = [0.0, 1.0, 10.0, 100.0, 500.0, 1000.0, 5000.0, 1e9]

# Failure modes (Gray-coded order)
FAILURE_MODES = ["none", "drift", "degradation", "partial_degradation", "open_circuit", "short_circuit"]

# ----------------------------------------------------------------------
# Utility functions
# ----------------------------------------------------------------------
def gray_to_binary(gray_bits: str) -> int:
    """Convert Gray code bits to binary integer."""
    g = int(gray_bits, 2)
    mask = g >> 1
    while mask:
        g ^= mask
        mask >>= 1
    return g

def gray_to_value(gray_bits: str, bands: List[float]) -> float:
    """Convert Gray-coded band to representative value."""
    idx = gray_to_binary(gray_bits)
    if idx >= len(bands):
        return 0.0
    return bands[idx]

# ----------------------------------------------------------------------
# Hardware decoder
# ----------------------------------------------------------------------
@dataclass
class HardwareData:
    failure_mode: str
    health_score: float
    is_critical: bool
    confidence_hi: bool
    has_synergy: bool
    voltage_v: float
    current_a: float
    temperature_c: float
    noise_level: float
    repurpose_class: str
    effectiveness: float
    bridge_target: BridgeTarget
    drift_pct: float
    salvageable: bool
    fallback_ready: bool
    lifetime_hours: float
    drill_depth: DrillDepth
    is_semiconductor: bool
    confidence: float  # computed from noise_level

def decode_hardware(bits: str) -> HardwareData:
    """Decode 39-bit hardware payload."""
    if len(bits) < 39:
        raise ValueError(f"Hardware payload too short: {len(bits)} bits")
    
    pos = 0
    # Section A (9 bits)
    failure_gray = bits[pos:pos+3]; pos += 3
    health_gray = bits[pos:pos+3]; pos += 3
    is_critical = bits[pos] == '1'; pos += 1
    confidence_hi = bits[pos] == '1'; pos += 1
    has_synergy = bits[pos] == '1'; pos += 1
    
    # Section B (12 bits)
    voltage_gray = bits[pos:pos+3]; pos += 3
    current_gray = bits[pos:pos+3]; pos += 3
    temp_gray = bits[pos:pos+3]; pos += 3
    noise_gray = bits[pos:pos+3]; pos += 3
    
    # Section C (12 bits)
    repurpose_gray = bits[pos:pos+3]; pos += 3
    effect_gray = bits[pos:pos+2]; pos += 2
    bridge_gray = bits[pos:pos+3]; pos += 3
    drift_gray = bits[pos:pos+2]; pos += 2
    salvageable = bits[pos] == '1'; pos += 1
    fallback_ready = bits[pos] == '1'; pos += 1
    
    # Section D (6 bits)
    lifetime_gray = bits[pos:pos+3]; pos += 3
    drill_gray = bits[pos:pos+2]; pos += 2
    is_semiconductor = bits[pos] == '1' if pos < len(bits) else False
    
    # Convert to values
    failure_mode = FAILURE_MODES[gray_to_binary(failure_gray)]
    health_score = gray_to_value(health_gray, HEALTH_BANDS)
    voltage = gray_to_value(voltage_gray, VOLTAGE_BANDS)
    current = gray_to_value(current_gray, CURRENT_BANDS)
    temperature = gray_to_value(temp_gray, TEMP_BANDS)
    noise = gray_to_value(noise_gray, NOISE_BANDS)
    effectiveness = gray_to_value(effect_gray, [0.0, 2.5, 5.0, 7.5])
    bridge_target = BridgeTarget(gray_to_binary(bridge_gray))
    drift = gray_to_value(drift_gray, DRIFT_BANDS)
    lifetime = gray_to_value(lifetime_gray, LIFETIME_BANDS)
    drill = DrillDepth(gray_to_binary(drill_gray))
    
    # Compute confidence from noise (FELTSensor)
    confidence = 1.0 / (1.0 + noise) if noise > 0 else 1.0
    
    return HardwareData(
        failure_mode=failure_mode,
        health_score=health_score,
        is_critical=is_critical,
        confidence_hi=confidence_hi,
        has_synergy=has_synergy,
        voltage_v=voltage,
        current_a=current,
        temperature_c=temperature,
        noise_level=noise,
        repurpose_class="unknown",  # Would need reverse map
        effectiveness=effectiveness,
        bridge_target=bridge_target,
        drift_pct=drift,
        salvageable=salvageable,
        fallback_ready=fallback_ready,
        lifetime_hours=lifetime,
        drill_depth=drill,
        is_semiconductor=is_semiconductor,
        confidence=confidence,
    )

# ----------------------------------------------------------------------
# Main decoder
# ----------------------------------------------------------------------
class SensorDecoder:
    """Decode Geometric Binary Bridge protocol streams."""
    
    def decode(self, binary_stream: bytes) -> Dict[str, Any]:
        """
        Decode a binary stream into sensor data.
        
        Args:
            binary_stream: Raw bytes from sensor or network
            
        Returns:
            Dictionary with keys: modality, data, confidence, drill_depth, etc.
        """
        # Parse header (simplified - would need actual bit unpacking)
        # For now, assume we have a binary string
        if isinstance(binary_stream, bytes):
            # Convert to binary string
            bits = ''.join(f'{b:08b}' for b in binary_stream)
        else:
            bits = binary_stream
        
        # Check magic number (first 8 bits should be 0x47 0x42 pattern)
        # Simplified: just check length
        
        # Extract modality from header (bits 12-15)
        if len(bits) < 16:
            raise ValueError("Stream too short for header")
        
        modality_byte = int(bits[12:16], 2)
        modality = Modality(modality_byte)
        
        # Decode based on modality
        if modality == Modality.HARDWARE:
            # Skip header (first 32 bits) for now
            payload = bits[32:]
            data = decode_hardware(payload)
            return {
                "modality": "hardware",
                "data": data,
                "confidence": data.confidence,
                "drill_depth": data.drill_depth.name,
                "temperature_c": data.temperature_c,
                "health_score": data.health_score,
            }
        else:
            return {
                "modality": modality.name,
                "data": None,
                "message": f"Decoder for {modality.name} not yet implemented",
            }

# ----------------------------------------------------------------------
# Actuator controller
# ----------------------------------------------------------------------
class ActuatorController:
    """Control physical actuators through the bridge."""
    
    def __init__(self):
        self.targets = {}
    
    def set_thermal(self, temperature_c: float, confidence: float = 1.0):
        """Set thermal bridge target temperature."""
        # Gray-code the value
        # Send binary through the bridge
        self.targets["thermal"] = {"value": temperature_c, "confidence": confidence}
        # In real implementation, this would output binary
        print(f"Actuator: thermal set to {temperature_c}°C (confidence {confidence})")
    
    def set_electric(self, voltage_v: float, current_a: float):
        """Set electric bridge output."""
        self.targets["electric"] = {"voltage": voltage_v, "current": current_a}
        print(f"Actuator: electric set to {voltage_v}V, {current_a}A")
    
    # Additional actuators for magnetic, light, sound, wave, pressure, chemical
