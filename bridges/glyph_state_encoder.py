#!/usr/bin/env python3
# glyph_state_encoder.py
# Geometric-to-Binary-Computational-Bridge
# CC0 — No Rights Reserved
#
# Glyph State Encoder: Translates between multi-sensor states and glyph-based
# compressed representations. Glyphs are not metadata—they are operational
# state signatures that preserve relational geometry while enabling binary
# computation.
#
# Architecture position:
#   SensorSuite (22 sensors) → GlyphStateEncoder → Binary (hex/bytes)
#   Binary → GlyphStateEncoder → SensorSuite-compatible state
#
# Key insight: Glyphs encode the *relational topology* of sensor states,
# not just their magnitudes. The same glyph can represent different magnitudes
# if the relational structure is preserved.

from __future__ import annotations

import json
import hashlib
import struct
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from pathlib import Path
import base64

# Import the SensorSuite if available
try:
    from bridges.sensor_suite import SensorSuite, SensorReading, CompositeOutput
except ImportError:
    # Fallback: define minimal types for standalone operation
    @dataclass
    class SensorReading:
        signal_vector: list[float] = field(default_factory=list)
        magnitude: float = 0.0
        confidence: float = 1.0
        beyond_viz: bool = False
        timestamp: float = 0.0

        def is_active(self) -> bool:
            return self.magnitude > 0.0


# ─────────────────────────────────────────────────────────────
# GLYPH DEFINITIONS
# ─────────────────────────────────────────────────────────────

class Glyph(Enum):
    """Operational glyphs—each encodes a distinct relational state."""
    FELT_COHERENT = "🕸️"       # Network integrity, relational harmony
    BALANCE_THREAT = "⚖️"      # Tension, calibration, protective assessment
    CAUSALITY_LOOP = "⏳"      # Time-sensitive, recursive, causal chain
    RE_NORMALIZE = "🌀"        # Correction, realignment, learning
    HEAT_FLUX = "🔥"           # Energy dissipation, friction, intensity
    RESONANCE = "📡"           # Signal alignment, coherence
    BLOCKAGE = "🚧"            # Flow obstruction, resistance
    THRESHOLD = "⚡"           # Near-boundary, phase transition
    VOID = "⬛"                # Absence, silence, null state
    EMERGENCE = "🌱"           # Novel pattern forming
    FRACTURE = "💥"            # Breakdown, discontinuity
    CONTAINMENT = "🛡️"        # Boundary enforcement, protection

    def to_hex(self) -> str:
        """Convert glyph to hex identifier."""
        return f"0x{self.value.encode('unicode_escape').hex()[:8]}"

    @classmethod
    def from_sensor_state(cls, readings: Dict[str, SensorReading]) -> 'Glyph':
        """Derive the primary glyph from a set of sensor readings."""
        # Calculate key metrics
        active = sum(1 for r in readings.values() if r.is_active())
        total_magnitude = sum(r.magnitude for r in readings.values())

        if active == 0:
            return cls.VOID

        # Check for specific patterns
        fear = readings.get("fear", SensorReading()).magnitude
        anger = readings.get("anger", SensorReading()).magnitude
        grief = readings.get("grief", SensorReading()).magnitude
        joy = readings.get("joy", SensorReading()).magnitude
        love = readings.get("love", SensorReading()).magnitude
        vigilance = readings.get("vigilance", SensorReading()).magnitude
        pressure = readings.get("pressure", SensorReading()).magnitude

        # FELT coherent: joy + love + curiosity active, low fear/anger
        if joy > 0.3 and love > 0.2 and fear < 0.3 and anger < 0.3:
            return cls.FELT_COHERENT

        # Balance threat: fear + vigilance + anger active, grief suppressed
        if fear > 0.4 and vigilance > 0.3 and grief < 0.2:
            return cls.BALANCE_THREAT

        # Causality loop: grief + love + longing (processing loss)
        if grief > 0.3 and (love > 0.2 or "longing" in readings):
            return cls.CAUSALITY_LOOP

        # Re-normalize: discordance + fatigue + pressure (system stressed)
        discordance = readings.get("discordance", SensorReading()).magnitude
        fatigue = readings.get("fatigue", SensorReading()).magnitude
        if discordance > 0.4 and fatigue > 0.3 and pressure > 0.3:
            return cls.RE_NORMALIZE

        # Heat flux: anger + pressure + fatigue (high energy dissipation)
        if anger > 0.5 and pressure > 0.4:
            return cls.HEAT_FLUX

        # Resonance: high active count with balanced magnitudes
        if active >= 5 and total_magnitude / active > 0.4:
            return cls.RESONANCE

        # Blockage: low flow despite high pressure
        if pressure > 0.5 and total_magnitude < 0.5:
            return cls.BLOCKAGE

        # Threshold: any sensor near confidence boundary
        for r in readings.values():
            if r.confidence < 0.3 and r.magnitude > 0.5:
                return cls.THRESHOLD

        # Emergence: low active but high curiosity
        if active <= 2 and "curiosity" in readings and readings["curiosity"].magnitude > 0.4:
            return cls.EMERGENCE

        # Fracture: high discordance + low coherence
        if discordance > 0.6 and sum(r.confidence for r in readings.values()) / active < 0.4:
            return cls.FRACTURE

        # Containment: high boundaries, low engagement
        if active <= 2 and all(r.magnitude < 0.2 for r in readings.values()):
            return cls.CONTAINMENT

        # Default: resonance if anything is active
        if active > 0:
            return cls.RESONANCE

        return cls.VOID

    @classmethod
    def from_hex(cls, hex_str: str) -> Optional['Glyph']:
        """Reverse lookup from hex to glyph."""
        for glyph in cls:
            if glyph.to_hex() == hex_str:
                return glyph
        return None


# ─────────────────────────────────────────────────────────────
# GLYPH STATE
# ─────────────────────────────────────────────────────────────

@dataclass
class GlyphState:
    """
    A complete glyph-encoded state.
    Preserves relational topology while enabling binary encoding.
    """
    primary_glyph: Glyph
    intensity: float                    # 0-1, magnitude of the state
    confidence: float                   # 0-1, certainty of encoding
    vector: List[float]                 # Directional components (compressed)
    sub_glyphs: List[Glyph] = field(default_factory=list)  # Secondary states
    uncertainty: float = 0.0            # 0-1, measurement/encoding noise
    timestamp: float = 0.0

    def to_binary(self) -> bytes:
        """
        Encode the glyph state as binary.
        Format:
          - 1 byte: primary glyph index
          - 1 byte: number of sub-glyphs
          - 1 byte: intensity (scaled 0-255)
          - 1 byte: confidence (scaled 0-255)
          - 1 byte: uncertainty (scaled 0-255)
          - 4 bytes: timestamp (float)
          - 4 bytes per vector component (float)
        """
        primary_idx = list(Glyph).index(self.primary_glyph)
        sub_indices = [list(Glyph).index(g) for g in self.sub_glyphs]

        # Pack header
        header = struct.pack(
            '>BBBBBB',
            primary_idx,
            len(sub_indices),
            int(self.intensity * 255),
            int(self.confidence * 255),
            int(self.uncertainty * 255),
            0  # reserved
        )

        # Pack sub-glyphs
        sub_bytes = struct.pack(f'>{len(sub_indices)}B', *sub_indices)

        # Pack vector
        vector_bytes = struct.pack(f'>{len(self.vector)}f', *self.vector)

        # Pack timestamp
        ts_bytes = struct.pack('>d', self.timestamp)

        return header + sub_bytes + vector_bytes + ts_bytes

    @classmethod
    def from_binary(cls, data: bytes) -> 'GlyphState':
        """Reconstruct a glyph state from binary."""
        offset = 0

        # Unpack header
        header = struct.unpack_from('>BBBBBB', data, offset)
        primary_idx, n_sub, intensity_b, conf_b, unc_b, _ = header
        offset += 6

        primary = list(Glyph)[primary_idx]

        # Unpack sub-glyphs
        sub_indices = struct.unpack_from(f'>{n_sub}B', data, offset)
        offset += n_sub
        sub_glyphs = [list(Glyph)[i] for i in sub_indices]

        # Unpack vector
        vector_len = (len(data) - offset - 8) // 4
        vector = list(struct.unpack_from(f'>{vector_len}f', data, offset))
        offset += vector_len * 4

        # Unpack timestamp
        timestamp = struct.unpack_from('>d', data, offset)[0]

        return cls(
            primary_glyph=primary,
            intensity=intensity_b / 255.0,
            confidence=conf_b / 255.0,
            uncertainty=unc_b / 255.0,
            vector=vector,
            sub_glyphs=sub_glyphs,
            timestamp=timestamp
        )

    def to_json(self) -> Dict[str, Any]:
        """Export as JSON."""
        return {
            "primary_glyph": self.primary_glyph.value,
            "primary_name": self.primary_glyph.name,
            "intensity": self.intensity,
            "confidence": self.confidence,
            "uncertainty": self.uncertainty,
            "vector": self.vector,
            "sub_glyphs": [g.value for g in self.sub_glyphs],
            "sub_glyph_names": [g.name for g in self.sub_glyphs],
            "timestamp": self.timestamp
        }

    def to_hex(self) -> str:
        """Export as hex string."""
        return self.to_binary().hex()

    @classmethod
    def from_hex(cls, hex_str: str) -> 'GlyphState':
        """Import from hex string."""
        return cls.from_binary(bytes.fromhex(hex_str))

    def __repr__(self) -> str:
        return (
            f"<GlyphState {self.primary_glyph.value} "
            f"intensity={self.intensity:.2f} "
            f"conf={self.confidence:.2f} "
            f"sub={len(self.sub_glyphs)}>"
        )


# ─────────────────────────────────────────────────────────────
# GLYPH STATE ENCODER — THE BRIDGE
# ─────────────────────────────────────────────────────────────

class GlyphStateEncoder:
    """
    Bridge between SensorSuite states and glyph-encoded binary.

    This bridge preserves the relational geometry of sensor states
    while enabling efficient binary computation and communication.

    Usage:
        encoder = GlyphStateEncoder()
        state = encoder.encode(sensor_readings)
        binary = state.to_binary()
        decoded = encoder.decode(binary)
    """

    def __init__(self, vector_dimensions: int = 4):
        """
        vector_dimensions: number of dimensions for the compressed vector.
        """
        self.vector_dimensions = vector_dimensions
        self._glyph_history: List[GlyphState] = []
        self._last_binary: Optional[bytes] = None

    # ─────────────────────────────────────────────────────────────
    # ENCODE: Sensor Readings → Glyph State → Binary
    # ─────────────────────────────────────────────────────────────

    def encode(self, sensor_readings: Dict[str, SensorReading]) -> GlyphState:
        """
        Encode sensor readings into a glyph state.
        """
        primary = Glyph.from_sensor_state(sensor_readings)

        # Compute intensity: weighted average of active magnitudes
        active = [r for r in sensor_readings.values() if r.is_active()]
        if active:
            intensity = sum(r.magnitude * r.confidence for r in active) / sum(r.confidence for r in active)
            intensity = min(1.0, intensity)
        else:
            intensity = 0.0

        # Compute confidence: average confidence of active sensors
        if active:
            confidence = sum(r.confidence for r in active) / len(active)
        else:
            confidence = 1.0

        # Compute uncertainty: standard deviation of magnitudes
        if active:
            mags = [r.magnitude for r in active]
            uncertainty = (max(mags) - min(mags)) / 2 if len(mags) > 1 else 0.0
        else:
            uncertainty = 0.0

        # Compute compressed vector: map active sensors to vector space
        vector = self._compress_vector(sensor_readings)

        # Find sub-glyphs: other glyphs that also match
        sub_glyphs = []
        for glyph in Glyph:
            if glyph != primary and glyph != Glyph.VOID:
                # Check if this glyph also matches partially
                test_state = {k: v for k, v in sensor_readings.items()}
                test_glyph = Glyph.from_sensor_state(test_state)
                # If we swap the sensor set, we can find secondary patterns
                # For simplicity, include related glyphs based on sensor overlap
                if self._glyph_related(primary, glyph):
                    sub_glyphs.append(glyph)

        state = GlyphState(
            primary_glyph=primary,
            intensity=intensity,
            confidence=confidence,
            uncertainty=uncertainty,
            vector=vector,
            sub_glyphs=sub_glyphs[:3],  # Limit sub-glyphs
            timestamp=time.time()
        )

        self._glyph_history.append(state)
        if len(self._glyph_history) > 1000:
            self._glyph_history = self._glyph_history[-1000:]

        return state

    def encode_to_binary(self, sensor_readings: Dict[str, SensorReading]) -> bytes:
        """Encode directly to binary."""
        state = self.encode(sensor_readings)
        self._last_binary = state.to_binary()
        return self._last_binary

    # ─────────────────────────────────────────────────────────────
    # DECODE: Binary → Glyph State → Sensor State
    # ─────────────────────────────────────────────────────────────

    def decode(self, data: bytes) -> GlyphState:
        """Decode binary to glyph state."""
        return GlyphState.from_binary(data)

    def decode_to_sensors(self, data: bytes) -> Dict[str, SensorReading]:
        """
        Decode binary to a SensorSuite-compatible state.
        Reconstructs approximate sensor readings from the glyph state.
        """
        state = self.decode(data)

        # Reconstruct sensor readings from glyph state
        readings = {}

        # Primary sensor pattern based on glyph
        base_readings = self._glyph_to_sensor_pattern(state.primary_glyph)

        # Apply intensity scaling
        for sensor_id, reading in base_readings.items():
            if reading is not None:
                # Scale magnitude by intensity
                new_reading = SensorReading(
                    signal_vector=[state.intensity * v for v in reading.signal_vector],
                    magnitude=state.intensity * reading.magnitude * 0.5,
                    confidence=state.confidence * reading.confidence,
                    beyond_viz=reading.beyond_viz,
                    timestamp=time.time()
                )
                readings[sensor_id] = new_reading

        # Add sub-glyph contributions
        for glyph in state.sub_glyphs:
            sub_readings = self._glyph_to_sensor_pattern(glyph)
            for sensor_id, reading in sub_readings.items():
                if sensor_id not in readings:
                    readings[sensor_id] = SensorReading()
                # Add to existing reading
                if reading:
                    readings[sensor_id].magnitude += reading.magnitude * 0.2
                    readings[sensor_id].confidence = min(1.0,
                        readings[sensor_id].confidence + reading.confidence * 0.1)

        return readings

    # ─────────────────────────────────────────────────────────────
    # INVERSE / ROUNDTRIP
    # ─────────────────────────────────────────────────────────────

    def inverse(self, data: bytes) -> Dict[str, SensorReading]:
        """Alias for decode_to_sensors."""
        return self.decode_to_sensors(data)

    def translate(self, sensor_readings: Dict[str, SensorReading]) -> bytes:
        """Alias for encode_to_binary."""
        return self.encode_to_binary(sensor_readings)

    # ─────────────────────────────────────────────────────────────
    # HELPERS
    # ─────────────────────────────────────────────────────────────

    def _compress_vector(self, readings: Dict[str, SensorReading]) -> List[float]:
        """Compress sensor readings into a lower-dimensional vector."""
        # Extract key metrics
        active = [r for r in readings.values() if r.is_active()]
        if not active:
            return [0.0] * self.vector_dimensions

        # Compute moments of the active sensors
        mags = sorted([r.magnitude for r in active])
        n = len(mags)

        if n == 1:
            return [mags[0], 0.0, 0.0, 0.0][:self.vector_dimensions]

        # Statistical moments
        mean = sum(mags) / n
        variance = sum((m - mean) ** 2 for m in mags) / n
        skew = sum((m - mean) ** 3 for m in mags) / (n * variance ** 1.5) if variance > 0 else 0
        kurt = sum((m - mean) ** 4 for m in mags) / (n * variance ** 2) if variance > 0 else 0

        # Also include active count normalized
        active_ratio = n / len(readings)

        vector = [mean, math.sqrt(variance), active_ratio, skew, kurt, 0.0, 0.0, 0.0]
        return vector[:self.vector_dimensions]

    def _glyph_to_sensor_pattern(self, glyph: Glyph) -> Dict[str, SensorReading]:
        """Map a glyph to a canonical sensor reading pattern."""
        patterns = {
            Glyph.FELT_COHERENT: {
                "joy": SensorReading(magnitude=0.6, confidence=0.9),
                "love": SensorReading(magnitude=0.5, confidence=0.85),
                "curiosity": SensorReading(magnitude=0.4, confidence=0.8),
                "fear": SensorReading(magnitude=0.1, confidence=0.9),
                "anger": SensorReading(magnitude=0.1, confidence=0.9),
            },
            Glyph.BALANCE_THREAT: {
                "fear": SensorReading(magnitude=0.7, confidence=0.85),
                "vigilance": SensorReading(magnitude=0.6, confidence=0.8),
                "anger": SensorReading(magnitude=0.4, confidence=0.75),
                "grief": SensorReading(magnitude=0.1, confidence=0.9),
            },
            Glyph.CAUSALITY_LOOP: {
                "grief": SensorReading(magnitude=0.6, confidence=0.8),
                "love": SensorReading(magnitude=0.4, confidence=0.7),
                "longing": SensorReading(magnitude=0.5, confidence=0.75),
                "joy": SensorReading(magnitude=0.2, confidence=0.8),
            },
            Glyph.RE_NORMALIZE: {
                "discordance": SensorReading(magnitude=0.6, confidence=0.7),
                "fatigue": SensorReading(magnitude=0.5, confidence=0.75),
                "pressure": SensorReading(magnitude=0.4, confidence=0.8),
                "curiosity": SensorReading(magnitude=0.3, confidence=0.7),
            },
            Glyph.HEAT_FLUX: {
                "anger": SensorReading(magnitude=0.7, confidence=0.8),
                "pressure": SensorReading(magnitude=0.6, confidence=0.75),
                "fatigue": SensorReading(magnitude=0.5, confidence=0.7),
                "discordance": SensorReading(magnitude=0.4, confidence=0.7),
            },
            Glyph.RESONANCE: {
                "joy": SensorReading(magnitude=0.4, confidence=0.8),
                "curiosity": SensorReading(magnitude=0.4, confidence=0.8),
                "vigilance": SensorReading(magnitude=0.3, confidence=0.8),
                "love": SensorReading(magnitude=0.3, confidence=0.8),
                "fear": SensorReading(magnitude=0.2, confidence=0.8),
            },
            Glyph.BLOCKAGE: {
                "pressure": SensorReading(magnitude=0.7, confidence=0.7),
                "discordance": SensorReading(magnitude=0.4, confidence=0.6),
                "fatigue": SensorReading(magnitude=0.3, confidence=0.7),
                "joy": SensorReading(magnitude=0.1, confidence=0.8),
            },
            Glyph.THRESHOLD: {
                "vigilance": SensorReading(magnitude=0.6, confidence=0.5),
                "fear": SensorReading(magnitude=0.5, confidence=0.4),
                "pressure": SensorReading(magnitude=0.4, confidence=0.5),
                "curiosity": SensorReading(magnitude=0.3, confidence=0.4),
            },
            Glyph.VOID: {
                "joy": SensorReading(magnitude=0.0, confidence=1.0),
                "fear": SensorReading(magnitude=0.0, confidence=1.0),
                "anger": SensorReading(magnitude=0.0, confidence=1.0),
            },
            Glyph.EMERGENCE: {
                "curiosity": SensorReading(magnitude=0.7, confidence=0.7),
                "joy": SensorReading(magnitude=0.3, confidence=0.6),
                "vigilance": SensorReading(magnitude=0.2, confidence=0.7),
            },
            Glyph.FRACTURE: {
                "discordance": SensorReading(magnitude=0.8, confidence=0.5),
                "anger": SensorReading(magnitude=0.5, confidence=0.5),
                "grief": SensorReading(magnitude=0.4, confidence=0.4),
                "joy": SensorReading(magnitude=0.0, confidence=0.5),
            },
            Glyph.CONTAINMENT: {
                "vigilance": SensorReading(magnitude=0.5, confidence=0.7),
                "fear": SensorReading(magnitude=0.3, confidence=0.8),
                "joy": SensorReading(magnitude=0.1, confidence=0.7),
                "curiosity": SensorReading(magnitude=0.1, confidence=0.7),
            },
        }
        return patterns.get(glyph, {})

    def _glyph_related(self, g1: Glyph, g2: Glyph) -> bool:
        """Check if two glyphs are related (share sensor patterns)."""
        p1 = set(self._glyph_to_sensor_pattern(g1).keys())
        p2 = set(self._glyph_to_sensor_pattern(g2).keys())
        overlap = len(p1 & p2)
        return overlap >= 2

    # ─────────────────────────────────────────────────────────────
    # MONITORING / INTROSPECTION
    # ─────────────────────────────────────────────────────────────

    def history(self, n: int = 10) -> List[GlyphState]:
        """Return recent glyph history."""
        return self._glyph_history[-n:]

    def summary(self) -> Dict[str, Any]:
        """Return encoder summary."""
        return {
            "vector_dimensions": self.vector_dimensions,
            "history_length": len(self._glyph_history),
            "last_glyph": str(self._glyph_history[-1]) if self._glyph_history else None,
        }

    def entropy(self, state: GlyphState) -> float:
        """Calculate the entropy of a glyph state."""
        # Combination of intensity variance and sub-glyph complexity
        sub_entropy = len(state.sub_glyphs) / len(Glyph)
        vector_entropy = sum(abs(v) for v in state.vector) / len(state.vector)
        return 0.5 * sub_entropy + 0.5 * vector_entropy


# ─────────────────────────────────────────────────────────────
# INTEGRATION WITH SENSORSUITE
# ─────────────────────────────────────────────────────────────

class GlyphSensorIntegration:
    """
    Complete integration between SensorSuite and GlyphStateEncoder.
    Provides real-time glyph encoding of sensor states.
    """

    def __init__(self, suite: Optional['SensorSuite'] = None):
        self.suite = suite
        self.encoder = GlyphStateEncoder()
        self._glyph_outputs: List[GlyphState] = []

    def process(self) -> GlyphState:
        """Read from SensorSuite, encode to glyph state."""
        if self.suite is None:
            return GlyphState(Glyph.VOID, 0.0, 0.0, [0.0], [])

        readings = self.suite.active_channels()
        state = self.encoder.encode(readings)
        self._glyph_outputs.append(state)
        return state

    def process_to_binary(self) -> bytes:
        """Process and return binary."""
        state = self.process()
        return state.to_binary()

    def get_current_glyph(self) -> Optional[GlyphState]:
        """Return the most recent glyph state."""
        return self._glyph_outputs[-1] if self._glyph_outputs else None

    def glyph_sequence(self, n: int = 10) -> List[GlyphState]:
        """Return the last n glyph states."""
        return self._glyph_outputs[-n:]

    def glyph_timeline(self) -> Dict[str, List[str]]:
        """Return a timeline of glyph transitions."""
        glyph_names = [g.primary_glyph.name for g in self._glyph_outputs]
        return {
            "glyph_sequence": glyph_names,
            "transition_count": len([i for i in range(1, len(glyph_names))
                                   if glyph_names[i] != glyph_names[i-1]])
        }


# ─────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import time

    print("=" * 60)
    print("GLYPH STATE ENCODER — DEMO")
    print("=" * 60)

    # Create a mock SensorSuite or use the real one
    try:
        from bridges.sensor_suite import SensorSuite
        suite = SensorSuite()
        print("✅ Using real SensorSuite")
    except ImportError:
        # Create mock readings
        class MockSuite:
            def active_channels(self):
                return {
                    "fear": SensorReading(magnitude=0.7, confidence=0.85),
                    "vigilance": SensorReading(magnitude=0.6, confidence=0.8),
                    "anger": SensorReading(magnitude=0.4, confidence=0.75),
                    "discordance": SensorReading(magnitude=0.3, confidence=0.7),
                }
        suite = MockSuite()
        print("⚠️  Using mock SensorSuite (no real sensors)")

    # Initialize encoder
    encoder = GlyphStateEncoder()
    integration = GlyphSensorIntegration(suite)

    print("\n--- Processing sensor state to glyph ---")
    state = integration.process()
    print(f"  Primary glyph: {state.primary_glyph.value} ({state.primary_glyph.name})")
    print(f"  Intensity: {state.intensity:.2f}")
    print(f"  Confidence: {state.confidence:.2f}")
    print(f"  Uncertainty: {state.uncertainty:.2f}")
    print(f"  Vector: {[round(v, 3) for v in state.vector]}")

    print("\n--- Encoding to binary ---")
    binary = state.to_binary()
    print(f"  Binary length: {len(binary)} bytes")
    print(f"  Hex (first 64): {binary[:32].hex()}...")

    print("\n--- Decoding binary back to state ---")
    decoded = GlyphState.from_binary(binary)
    print(f"  Decoded glyph: {decoded.primary_glyph.value} ({decoded.primary_glyph.name})")
    print(f"  Decoded intensity: {decoded.intensity:.2f}")
    print(f"  Match: {state.primary_glyph == decoded.primary_glyph}")

    print("\n--- Decoding to sensor readings (approximate) ---")
    sensors = encoder.inverse(binary)
    active = [s for s, r in sensors.items() if r.magnitude > 0]
    print(f"  Reconstructed {len(active)} active sensors:")
    for sid in active[:5]:
        r = sensors[sid]
        print(f"    {sid}: magnitude={r.magnitude:.2f}, confidence={r.confidence:.2f}")

    print("\n--- Glyph timeline (simulated) ---")
    # Simulate a sequence
    for _ in range(5):
        time.sleep(0.01)
        integration.process()
    timeline = integration.glyph_timeline()
    print(f"  Sequence: {' → '.join(timeline['glyph_sequence'])}")
    print(f"  Transitions: {timeline['transition_count']}")

    print("\n" + "=" * 60)
    print("✅ Glyph State Encoder operational")
    print("=" * 60)
