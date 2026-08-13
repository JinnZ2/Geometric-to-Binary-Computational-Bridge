#!/usr/bin/env python3
"""
glyph_state_encoder.py -- sensor readings <-> glyph <-> binary.  CC0.

Glyphs here are state signatures over a sensor suite, not decoration. The
encoder classifies a set of readings into one of twelve glyphs, compresses the
reading set to a short vector, and packs the result into ~33 bytes.

=====================================================================
AUDIT  --  read this before building on the classifier
=====================================================================
This file arrived as TWO complete versions pasted end to end, and the combined
file did not compile: a second `from __future__ import annotations` at line 720
is a SyntaxError, so nothing in `bridges/` that imported it worked at all.

The two halves were not versions of each other in the ordinary sense. They
share the twelve glyph NAMES and nothing else: the first half classified by
matching against a declared `phase_space` and carried a decay/energy model;
the second half classified by an explicit rule ladder and carried the
SensorSuite integration and the binary codec. Neither is a superset.

Which half survives was decided by measurement, not by which was labelled
"Corrected" -- the one carrying that label lost:

  exemplar built from the FIRST half's own declared phase_space, classified
  by each implementation, scored on recovering the glyph it was built for

      phase-space variant (labelled "Corrected")   4 / 12
      rule ladder (this file)                      7 / 12

  distinct glyphs reachable over 20 000 random reading sets

      phase-space variant                          5 / 12
      rule ladder (this file)                     11 / 12

  the empty reading set

      phase-space variant  ->  FELT_COHERENT   ("relational harmony")
      rule ladder          ->  VOID

The phase-space variant is kept at `legacy/glyph_state_encoder_phase_space.py`
with the cause recorded there. Its decay/energy model was NOT ported, because
it was never exercised against anything: see GLY-4.

Everything below is what remains wrong with the half that won. None of it is
fixed here, because every fix requires choosing a number that is a claim about
affect, not about code, and this file is not where that choice belongs.
`unreachable_glyphs()`, `recovery_from_spec()` and
`sub_glyphs_are_data_independent()` measure them on demand; the runnable
report is `bridges/falsifiers_glyph_sensor.py`.

GLY-1  BLOCKAGE is unsatisfiable.
       Its rule is `pressure > 0.5 and total_magnitude < 0.5`, and pressure is
       one of the non-negative terms summed into total_magnitude, so
       total >= pressure > 0.5 for every input. One glyph in twelve can never
       be emitted, by arithmetic, with no sampling needed. `unreachable_glyphs()`
       proves it by construction.

GLY-2  The rule ladder is order-dependent and the order is undeclared.
       Rules are tested top to bottom and the first match returns, so an
       earlier rule shadows every later one it overlaps. The measured case:
       the HEAT_FLUX exemplar (anger, pressure, fatigue, high discordance)
       satisfies RE_NORMALIZE's rule, which is tested first, so HEAT_FLUX is
       returned for none of the states it was written for. This is most of the
       5/12 shortfall -- it is precedence, not logic.

GLY-3  `sub_glyphs` carries no information about the reading.
       `encode()` loops over the glyphs computing `test_glyph` and then
       discards it; membership is decided by `_glyph_related(primary, glyph)`,
       which compares two canonical patterns and never looks at the readings.
       So the field is a fixed lookup on the primary glyph -- and because it
       feeds `entropy()` and the binary payload, a constant is travelling
       through both under the name "secondary states".
       `sub_glyphs_are_data_independent()` returns the proof.

GLY-5  The codec is lossy, and it is documented as if it were not.
       intensity, confidence and uncertainty are quantised to 8 bits (~0.4 %),
       the vector to float32; the docstring's byte map is wrong in two places
       (six header bytes are packed where five are listed; the timestamp is
       `>d`, eight bytes, not four). Repo convention (CLAUDE.md, "Lossless
       round-trips") is that encoders round-trip exactly, so this one is an
       exception and now says so. Separately `uncertainty` is
       `(max - min) / 2` over magnitudes documented on [0, inf), so a
       magnitude above 2.0 makes `int(uncertainty * 255) > 255` and
       `to_binary()` raises `struct.error`. That path is reachable from a
       legal SensorReading.

GLY-6  The demo classified nothing and reported success.
       It preferred a freshly constructed real `SensorSuite` -- which has no
       readings in it -- over the populated mock in the `except ImportError`
       branch, so all six processed states were VOID, the "glyph timeline"
       had zero transitions, and the last line printed was
       "Glyph State Encoder operational". Fixed below: the demo now seeds the
       suite and asserts that more than one glyph was produced.

GLY-7  The module was not importable as a library, and only the demo hid it.
       `encode()` calls `time.time()`, but `import time` appeared only inside
       the `if __name__ == "__main__":` block -- which puts `time` in module
       globals when the file is RUN and nowhere when it is IMPORTED. So every
       caller outside this file got `NameError: name 'time' is not defined`
       on the first encode, while the demo passed. Fixed (the import moved to
       module scope); recorded because the shape is worth having a name for:
       a demo can supply a binding the library needs, and then the demo is
       testing a different module than the one anyone imports.

What is NOT audited here, because it is a question rather than a defect: the
twelve glyphs, their sensor sets and their thresholds are an affect model. The
open problems GLY-A and GLY-B in `playground/OPEN_PROBLEMS.json` state what
would have to be measured to make any of those numbers other than a guess.
"""
from __future__ import annotations

import json
import hashlib
import struct
import math
import time          # GLY-7: encode() calls time.time(); this import was
                     # present only inside the __main__ block, so the module
                     # raised NameError for every importer.
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


# ─────────────────────────────────────────────────────────────
# MEASUREMENTS  --  the audit header's numbers, on demand
# ─────────────────────────────────────────────────────────────

def unreachable_glyphs() -> Dict[str, str]:
    """GLY-1. Glyphs no input can produce, with the reason.

    Only the arithmetically provable case is listed. A glyph that merely never
    turned up in sampling is not reported here, because "not seen in 20 000
    draws" is a statement about the draws.
    """
    out = {}
    # BLOCKAGE: pressure > 0.5 and total_magnitude < 0.5, where pressure is a
    # term of total_magnitude over non-negative magnitudes.
    out[Glyph.BLOCKAGE.name] = (
        "pressure > 0.5 and total_magnitude < 0.5; pressure is a term of "
        "total_magnitude and magnitudes are non-negative, so "
        "total_magnitude >= pressure > 0.5 for every input"
    )
    return out


def _spec_exemplar(phase_space: List[str]) -> Dict[str, float]:
    """Build a reading set from a declared phase_space description.

    `low_X` -> X at 0.05, `high_X` -> X at 0.85, a bare sensor name -> 0.70,
    the two null tokens -> the empty set. Predicate tokens that name no sensor
    (`balanced_active`, `novel_pattern`, `isolation`, ...) contribute nothing,
    which is itself part of what the recovery score measures.
    """
    out: Dict[str, float] = {}
    for cond in phase_space:
        if cond in ("inactive", "zero_intensity"):
            return {}
        if cond.startswith("low_"):
            out.setdefault(cond[4:], 0.05)
        elif cond.startswith("high_"):
            out[cond[5:]] = 0.85
        elif "_" in cond:
            continue          # a predicate, not a sensor
        else:
            out[cond] = 0.70
    return out


#: The phase_space declarations from the superseded half, kept as the
#: independent statement of intent that `recovery_from_spec()` scores against.
#: Copied verbatim from `legacy/glyph_state_encoder_phase_space.py`; it is a
#: specification, not an implementation, which is the point -- scoring this
#: file's ladder against exemplars derived from this file's own ladder would
#: be P-SELF-SUPPLIED-FALSIFIER.
PHASE_SPACE_SPEC: Dict[str, List[str]] = {
    "FELT_COHERENT":  ["joy", "love", "curiosity", "low_fear", "low_anger"],
    "BALANCE_THREAT": ["fear", "vigilance", "anger", "low_grief"],
    "CAUSALITY_LOOP": ["grief", "love", "longing", "uncertainty"],
    "RE_NORMALIZE":   ["discordance", "fatigue", "pressure", "curiosity"],
    "HEAT_FLUX":      ["anger", "pressure", "fatigue", "high_discordance"],
    "RESONANCE":      ["balanced_active", "high_confidence", "low_discordance"],
    "BLOCKAGE":       ["pressure", "low_flow", "fatigue", "low_joy"],
    "THRESHOLD":      ["high_uncertainty", "low_confidence", "high_intensity"],
    "VOID":           ["inactive", "zero_intensity"],
    "EMERGENCE":      ["curiosity", "low_intensity", "novel_pattern"],
    "FRACTURE":       ["high_discordance", "low_coherence", "isolation"],
    "CONTAINMENT":    ["high_boundary", "low_engagement", "vigilance"],
}


def recovery_from_spec() -> Dict[str, Any]:
    """GLY-2. Feed each glyph an exemplar built from its declared phase_space
    and count how often the classifier returns the glyph it was built for.

    Returns the per-glyph verdict and the score. This is the number that
    decided which half of the pasted file survived; it is not a quality
    threshold, and 12/12 is not achievable while GLY-1 stands.
    """
    rows = {}
    hits = 0
    for name, ps in PHASE_SPACE_SPEC.items():
        ex = _spec_exemplar(ps)
        got = Glyph.from_sensor_state(
            {k: SensorReading(magnitude=v, confidence=1.0)
             for k, v in ex.items()}).name
        rows[name] = {"exemplar": ex, "got": got, "recovered": got == name}
        hits += got == name
    return {"rows": rows, "recovered": hits, "of": len(PHASE_SPACE_SPEC)}


def sub_glyphs_are_data_independent(encoder: "GlyphStateEncoder" = None) -> bool:
    """GLY-3. True when `sub_glyphs` is a function of the primary glyph alone.

    Proved by finding two reading sets that classify to the same primary and
    differ in every magnitude, then comparing their sub_glyph lists. If the
    field carried information about the reading, those two would differ.
    """
    enc = encoder or GlyphStateEncoder()
    a = {"joy": SensorReading(magnitude=0.9, confidence=1.0),
         "love": SensorReading(magnitude=0.9, confidence=1.0),
         "curiosity": SensorReading(magnitude=0.9, confidence=1.0)}
    b = {"joy": SensorReading(magnitude=0.35, confidence=0.4),
         "love": SensorReading(magnitude=0.25, confidence=0.4),
         "grief": SensorReading(magnitude=0.15, confidence=0.4)}
    sa, sb = enc.encode(a), enc.encode(b)
    if sa.primary_glyph != sb.primary_glyph:
        raise AssertionError("fixture no longer lands on one primary glyph")
    return [g.name for g in sa.sub_glyphs] == [g.name for g in sb.sub_glyphs]


def codec_round_trip_error(state: "GlyphState") -> Dict[str, float]:
    """GLY-5. Absolute error introduced by to_binary/from_binary.

    Reported rather than removed: widening the fields would change the wire
    format, and nothing downstream has declared what precision it needs.
    """
    back = GlyphState.from_binary(state.to_binary())
    out = {"intensity": abs(state.intensity - back.intensity),
           "confidence": abs(state.confidence - back.confidence),
           "uncertainty": abs(state.uncertainty - back.uncertainty)}
    out["vector"] = max([abs(x - y) for x, y in zip(state.vector, back.vector)]
                        or [0.0])
    return out


# ─────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────

def _demo_readings() -> List[Dict[str, SensorReading]]:
    """Four reading sets that are meant to land on four different glyphs."""
    def R(**kw):
        return {k: SensorReading(magnitude=v, confidence=0.85)
                for k, v in kw.items()}
    return [R(joy=0.6, love=0.5, curiosity=0.4, fear=0.1, anger=0.1),
            R(fear=0.7, vigilance=0.6, anger=0.4, grief=0.1),
            R(discordance=0.6, fatigue=0.5, pressure=0.4, curiosity=0.3),
            R(grief=0.6, love=0.4, longing=0.5)]


def main() -> int:
    """Exercises the encoder on states that must not all classify the same.

    The version this replaced constructed an empty SensorSuite, classified six
    VOIDs, and printed "operational". This one returns nonzero if fewer than
    three distinct glyphs come out, so the same failure cannot pass silently.
    """
    enc = GlyphStateEncoder()
    seen = []
    print("GLYPH STATE ENCODER")
    print("=" * 62)
    for i, readings in enumerate(_demo_readings(), 1):
        st = enc.encode(readings)
        wire = st.to_binary()
        back = GlyphState.from_binary(wire)
        err = codec_round_trip_error(st)
        seen.append(st.primary_glyph.name)
        print("  state %d  %-16s intensity %.2f  %2d bytes  "
              "round-trip glyph %s  max field error %.4f"
              % (i, st.primary_glyph.name, st.intensity, len(wire),
                 "ok" if back.primary_glyph == st.primary_glyph else "LOST",
                 max(err.values())))

    print()
    rec = recovery_from_spec()
    print("  recovery from the declared phase_space: %d/%d"
          % (rec["recovered"], rec["of"]))
    for name, row in rec["rows"].items():
        if not row["recovered"]:
            print("      %-16s -> %s" % (name, row["got"]))
    print("  unreachable by arithmetic: %s"
          % ", ".join(unreachable_glyphs()) or "none")
    print("  sub_glyphs independent of the reading: %s"
          % sub_glyphs_are_data_independent())
    print()

    distinct = len(set(seen))
    if distinct < 3:
        print("FAIL: %d distinct glyph(s) over %d states -- the classifier is "
              "not separating the demo inputs" % (distinct, len(seen)))
        return 1
    print("%d distinct glyphs over %d states" % (distinct, len(seen)))
    return 0


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
