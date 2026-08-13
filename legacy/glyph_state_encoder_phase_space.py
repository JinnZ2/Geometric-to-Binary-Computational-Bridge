#!/usr/bin/env python3
"""
glyph_state_encoder_phase_space.py -- SUPERSEDED. Provenance only.

Replaced by `bridges/glyph_state_encoder.py`. Do not import this, do not build
on it, do not cite its numbers. It is kept because `CLAIMS_REGISTER.json`
records GLY-4 against it and a correction that points at a deleted file is not
auditable.

WHAT THIS WAS
    One of two complete glyph encoders that arrived pasted end to end in
    `bridges/glyph_state_encoder.py` (the concatenation did not compile: a
    second `from __future__ import annotations` mid-file is a SyntaxError).
    This was the first half, lines 1-701, and it labelled itself "Corrected".
    It treats each glyph as a phase-space region with a declared sensor set, a
    decay model and an energy cost, and carries a dynamics layer -- velocity,
    relaxation, an energy budget -- that the surviving half does not have.

WHY IT DID NOT SURVIVE  (GLY-4)
    `Glyph.from_phase_space` scores a candidate glyph by walking its
    `phase_space` list, and every branch sits behind

        if condition in readings:

    where `condition` is a token like `low_fear`, `high_discordance`,
    `balanced_active`, `zero_intensity`. Those tokens are descriptions of
    conditions; they are never keys of a reading dict. So the guard is false
    for all of them and the entire ladder below it -- every `low_*`, every
    `high_*`, and all nine named predicates -- is unreachable. Only bare
    sensor names survive the guard, and they fall through to a single
    `> 0.3` test.

    Three consequences, all measured:

      * 5 of 12 glyphs are reachable over 20 000 random reading sets.
        RESONANCE, THRESHOLD, FRACTURE, BLOCKAGE, CONTAINMENT, EMERGENCE and
        VOID are never emitted -- their phase_space lists are made entirely or
        almost entirely of predicate tokens, so they always score 0.

      * VOID cannot be selected at all. Both of its conditions are predicates,
        so it scores 0, and `best_score` starts at -1.0 with `best_glyph`
        already set to VOID -- which the first glyph in enum order displaces
        with a score of 0.0. An EMPTY reading set therefore returns
        FELT_COHERENT: silence classifies as "network integrity, relational
        harmony". In a sensor, a dead channel reading as the healthy state is
        the one failure mode worth designing against.

      * Scored against exemplars built from its own declared phase_space, it
        recovers 4 of 12; the surviving half recovers 7 of 12 against the same
        exemplars.

WHAT SURVIVES IT
    The `phase_space` declarations themselves. They are the only independent
    statement in either file of what each glyph is supposed to MEAN, written
    separately from the rule ladder that classifies. They are copied into
    `bridges/glyph_state_encoder.py` as `PHASE_SPACE_SPEC` and are what
    `recovery_from_spec()` scores against -- so the surviving classifier is
    tested against a specification it did not author, rather than against
    exemplars derived from its own thresholds.

    The dynamics layer -- DecayModel, velocity, relax(), energy_budget(),
    energy_flow() -- was NOT ported. Not because it is wrong, but because
    nothing here ever tested it: the decay model comes from a glyph the
    classifier could only assign correctly a third of the time, and the energy
    figures are per-glyph constants with no measurement behind them. Porting
    it would have carried GLY-4's classification error into a thermodynamic
    accounting layer. Open problem GLY-B states what it would take.
"""
from __future__ import annotations

import json
import struct
import math
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple, Set
from enum import Enum
from pathlib import Path
import base64

# ─────────────────────────────────────────────────────────────
# DECAY MODELS — thermodynamic relaxation functions
# ─────────────────────────────────────────────────────────────

class DecayModel(Enum):
    """
    Thermodynamic decay models for glyph states.
    Each model describes how a glyph relaxes toward equilibrium.
    """
    EXPONENTIAL = "exponential"   # Fast return to equilibrium (resolved threat)
    LINEAR = "linear"             # Constant dissipation (unresolved leak)
    PERSISTENT = "persistent"     # Slow decay (chronic state)
    OSCILLATORY = "oscillatory"   # Coupled exchange (unresolved tension)

    @staticmethod
    def from_thermodynamic_signature(
        magnitude: float,
        velocity: float,
        acceleration: float,
        energy_in: float,
        energy_out: float
    ) -> 'DecayModel':
        """
        Infer the decay model from thermodynamic signatures.
        """
        # If acceleration is negative and magnitude decreasing rapidly → exponential
        if acceleration < -0.1 and velocity < 0 and abs(velocity) > 0.1:
            return DecayModel.EXPONENTIAL

        # If velocity is constant negative → linear
        if abs(acceleration) < 0.01 and velocity < 0:
            return DecayModel.LINEAR

        # If energy_in ≈ energy_out but magnitude not dropping → persistent
        if abs(energy_in - energy_out) < 0.1 and magnitude > 0.3:
            return DecayModel.PERSISTENT

        # If velocity oscillates → oscillatory
        return DecayModel.OSCILLATORY

    def relax(self, magnitude: float, dt: float, **params) -> float:
        """
        Apply the decay model over time dt.
        """
        if self == DecayModel.EXPONENTIAL:
            tau = params.get('tau', 10.0)
            return magnitude * math.exp(-dt / tau)

        elif self == DecayModel.LINEAR:
            rate = params.get('rate', 0.01)
            return max(0.0, magnitude - rate * dt)

        elif self == DecayModel.PERSISTENT:
            decay_rate = params.get('decay_rate', 0.001)
            return magnitude * (1.0 - decay_rate * dt / 100.0)

        elif self == DecayModel.OSCILLATORY:
            omega = params.get('omega', 0.1)
            damping = params.get('damping', 0.02)
            return magnitude * math.exp(-damping * dt) * abs(math.cos(omega * dt))

        return magnitude


# ─────────────────────────────────────────────────────────────
# GLYPH DEFINITIONS (with phase-space signatures)
# ─────────────────────────────────────────────────────────────

class Glyph(Enum):
    """
    Glyphs as phase-space operators.
    Each glyph defines a region in sensor state space with associated dynamics.
    """
    FELT_COHERENT = {
        "symbol": "🕸️",
        "phase_space": ["joy", "love", "curiosity", "low_fear", "low_anger"],
        "default_decay": DecayModel.PERSISTENT,
        "energy_cost": 0.2,
        "transition_to": ["BALANCE_THREAT", "RE_NORMALIZE"]
    }

    BALANCE_THREAT = {
        "symbol": "⚖️",
        "phase_space": ["fear", "vigilance", "anger", "low_grief"],
        "default_decay": DecayModel.EXPONENTIAL,
        "energy_cost": 0.6,
        "transition_to": ["FELT_COHERENT", "RE_NORMALIZE"]
    }

    CAUSALITY_LOOP = {
        "symbol": "⏳",
        "phase_space": ["grief", "love", "longing", "uncertainty"],
        "default_decay": DecayModel.OSCILLATORY,
        "energy_cost": 0.4,
        "transition_to": ["FELT_COHERENT", "FRACTURE"]
    }

    RE_NORMALIZE = {
        "symbol": "🌀",
        "phase_space": ["discordance", "fatigue", "pressure", "curiosity"],
        "default_decay": DecayModel.EXPONENTIAL,
        "energy_cost": 0.5,
        "transition_to": ["FELT_COHERENT", "BALANCE_THREAT"]
    }

    HEAT_FLUX = {
        "symbol": "🔥",
        "phase_space": ["anger", "pressure", "fatigue", "high_discordance"],
        "default_decay": DecayModel.LINEAR,
        "energy_cost": 0.8,
        "transition_to": ["RE_NORMALIZE", "FRACTURE"]
    }

    RESONANCE = {
        "symbol": "📡",
        "phase_space": ["balanced_active", "high_confidence", "low_discordance"],
        "default_decay": DecayModel.PERSISTENT,
        "energy_cost": 0.3,
        "transition_to": ["FELT_COHERENT", "THRESHOLD"]
    }

    BLOCKAGE = {
        "symbol": "🚧",
        "phase_space": ["pressure", "low_flow", "fatigue", "low_joy"],
        "default_decay": DecayModel.LINEAR,
        "energy_cost": 0.5,
        "transition_to": ["HEAT_FLUX", "RE_NORMALIZE"]
    }

    THRESHOLD = {
        "symbol": "⚡",
        "phase_space": ["high_uncertainty", "low_confidence", "high_intensity"],
        "default_decay": DecayModel.EXPONENTIAL,
        "energy_cost": 0.7,
        "transition_to": ["BALANCE_THREAT", "RE_NORMALIZE"]
    }

    VOID = {
        "symbol": "⬛",
        "phase_space": ["inactive", "zero_intensity"],
        "default_decay": DecayModel.PERSISTENT,
        "energy_cost": 0.0,
        "transition_to": ["EMERGENCE"]
    }

    EMERGENCE = {
        "symbol": "🌱",
        "phase_space": ["curiosity", "low_intensity", "novel_pattern"],
        "default_decay": DecayModel.EXPONENTIAL,
        "energy_cost": 0.3,
        "transition_to": ["RESONANCE", "FELT_COHERENT"]
    }

    FRACTURE = {
        "symbol": "💥",
        "phase_space": ["high_discordance", "low_coherence", "isolation"],
        "default_decay": DecayModel.LINEAR,
        "energy_cost": 0.9,
        "transition_to": ["RE_NORMALIZE", "VOID"]
    }

    CONTAINMENT = {
        "symbol": "🛡️",
        "phase_space": ["high_boundary", "low_engagement", "vigilance"],
        "default_decay": DecayModel.PERSISTENT,
        "energy_cost": 0.4,
        "transition_to": ["BALANCE_THREAT", "VOID"]
    }

    @property
    def symbol(self) -> str:
        return self.value["symbol"]

    @property
    def phase_space(self) -> List[str]:
        return self.value["phase_space"]

    @property
    def default_decay(self) -> DecayModel:
        return self.value["default_decay"]

    @property
    def energy_cost(self) -> float:
        return self.value["energy_cost"]

    @property
    def transition_to(self) -> List[str]:
        return self.value["transition_to"]

    def to_hex(self) -> str:
        """Convert glyph to hex identifier."""
        return f"0x{self.symbol.encode('unicode_escape').hex()[:8]}"

    @classmethod
    def from_symbol(cls, symbol: str) -> Optional['Glyph']:
        for g in cls:
            if g.symbol == symbol:
                return g
        return None

    @classmethod
    def from_phase_space(cls, readings: Dict[str, float]) -> 'Glyph':
        """
        Determine the glyph from phase-space coordinates.
        Uses weighted matching against each glyph's phase_space.
        """
        best_glyph = cls.VOID
        best_score = -1.0

        for glyph in cls:
            # Check how many phase-space conditions match
            score = 0.0
            for condition in glyph.phase_space:
                if condition in readings:
                    # Simple: if condition is "low_X", check if X < 0.3
                    if condition.startswith("low_"):
                        sensor = condition[4:]
                        if readings.get(sensor, 0.0) < 0.3:
                            score += 0.2
                    elif condition.startswith("high_"):
                        sensor = condition[5:]
                        if readings.get(sensor, 0.0) > 0.6:
                            score += 0.2
                    elif condition == "inactive":
                        if sum(readings.values()) < 0.1:
                            score += 0.3
                    elif condition == "zero_intensity":
                        if sum(readings.values()) == 0:
                            score += 0.5
                    elif condition == "balanced_active":
                        active = [v for v in readings.values() if v > 0.1]
                        if active and max(active) - min(active) < 0.3:
                            score += 0.2
                    elif condition == "high_confidence":
                        # confidence not in readings, skip
                        pass
                    elif condition == "low_flow":
                        if readings.get("flow", 0.0) < 0.2:
                            score += 0.2
                    elif condition == "low_engagement":
                        active = [v for v in readings.values() if v > 0.1]
                        if len(active) < 3:
                            score += 0.2
                    elif condition == "high_boundary":
                        if readings.get("vigilance", 0.0) > 0.5:
                            score += 0.2
                    elif condition == "isolation":
                        if readings.get("joy", 0.0) < 0.1 and readings.get("love", 0.0) < 0.1:
                            score += 0.2
                    elif condition == "novel_pattern":
                        # Placeholder
                        score += 0.1
                    else:
                        # Direct sensor match
                        if readings.get(condition, 0.0) > 0.3:
                            score += 0.2

            if score > best_score:
                best_score = score
                best_glyph = glyph

        return best_glyph


# ─────────────────────────────────────────────────────────────
# GLYPH STATE (with dynamics)
# ─────────────────────────────────────────────────────────────

@dataclass
class GlyphState:
    """
    Complete glyph state including dynamics and thermodynamics.
    """
    primary_glyph: Glyph
    intensity: float                    # 0-1, current magnitude
    velocity: List[float]               # rate of change in each dimension
    decay_model: DecayModel             # thermodynamic relaxation
    energy_cost: float                  # energy to maintain this state
    energy_in: float                    # energy input rate
    energy_out: float                   # energy dissipation rate
    confidence: float                   # 0-1, epistemic certainty
    sub_glyphs: List[Glyph] = field(default_factory=list)
    trajectory: List['GlyphState'] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def relax(self, dt: float) -> 'GlyphState':
        """
        Apply the decay model to produce a relaxed state.
        """
        new_intensity = self.decay_model.relax(
            self.intensity, dt,
            tau=10.0,
            rate=0.01,
            decay_rate=0.001,
            omega=0.1,
            damping=0.02
        )

        # Scale velocity components by relaxation
        new_velocity = [v * (new_intensity / max(self.intensity, 0.001)) for v in self.velocity]

        return GlyphState(
            primary_glyph=self.primary_glyph,
            intensity=new_intensity,
            velocity=new_velocity,
            decay_model=self.decay_model,
            energy_cost=self.energy_cost,
            energy_in=self.energy_in,
            energy_out=self.energy_out,
            confidence=self.confidence * 0.95,  # confidence decays slightly
            sub_glyphs=self.sub_glyphs,
            trajectory=self.trajectory + [self] if len(self.trajectory) < 100 else self.trajectory,
            timestamp=self.timestamp + dt
        )

    def to_binary(self) -> bytes:
        """
        Encode glyph state to binary.
        Format:
          - 1 byte: primary glyph index
          - 1 byte: number of sub-glyphs
          - 1 byte: intensity (0-255)
          - 1 byte: confidence (0-255)
          - 1 byte: decay_model index
          - 4 bytes: energy_cost (float)
          - 4 bytes: energy_in (float)
          - 4 bytes: energy_out (float)
          - 4 bytes per velocity component (float)
          - 4 bytes: timestamp (float)
        """
        primary_idx = list(Glyph).index(self.primary_glyph)
        decay_idx = list(DecayModel).index(self.decay_model)

        # Header
        header = struct.pack(
            '>BBBBB',
            primary_idx,
            len(self.sub_glyphs),
            int(self.intensity * 255),
            int(self.confidence * 255),
            decay_idx
        )

        # Sub-glyphs
        sub_indices = [list(Glyph).index(g) for g in self.sub_glyphs]
        sub_bytes = struct.pack(f'>{len(sub_indices)}B', *sub_indices)

        # Energy and dynamics
        energy_bytes = struct.pack('>fff', self.energy_cost, self.energy_in, self.energy_out)

        # Velocity
        velocity_bytes = struct.pack(f'>{len(self.velocity)}f', *self.velocity)

        # Timestamp
        ts_bytes = struct.pack('>d', self.timestamp)

        return header + sub_bytes + energy_bytes + velocity_bytes + ts_bytes

    @classmethod
    def from_binary(cls, data: bytes) -> 'GlyphState':
        """Reconstruct glyph state from binary."""
        offset = 0

        header = struct.unpack_from('>BBBBB', data, offset)
        primary_idx, n_sub, intensity_b, conf_b, decay_idx = header
        offset += 5

        primary = list(Glyph)[primary_idx]
        decay = list(DecayModel)[decay_idx]

        sub_indices = struct.unpack_from(f'>{n_sub}B', data, offset)
        offset += n_sub
        sub_glyphs = [list(Glyph)[i] for i in sub_indices]

        energy_cost, energy_in, energy_out = struct.unpack_from('>fff', data, offset)
        offset += 12

        velocity_len = (len(data) - offset - 8) // 4
        velocity = list(struct.unpack_from(f'>{velocity_len}f', data, offset))
        offset += velocity_len * 4

        timestamp = struct.unpack_from('>d', data, offset)[0]

        return cls(
            primary_glyph=primary,
            intensity=intensity_b / 255.0,
            velocity=velocity,
            decay_model=decay,
            energy_cost=energy_cost,
            energy_in=energy_in,
            energy_out=energy_out,
            confidence=conf_b / 255.0,
            sub_glyphs=sub_glyphs,
            trajectory=[],
            timestamp=timestamp
        )

    def to_json(self) -> Dict[str, Any]:
        return {
            "primary_glyph": self.primary_glyph.symbol,
            "primary_name": self.primary_glyph.name,
            "intensity": self.intensity,
            "velocity": self.velocity,
            "decay_model": self.decay_model.value,
            "energy_cost": self.energy_cost,
            "energy_in": self.energy_in,
            "energy_out": self.energy_out,
            "confidence": self.confidence,
            "sub_glyphs": [g.symbol for g in self.sub_glyphs],
            "timestamp": self.timestamp
        }

    def __repr__(self) -> str:
        return (
            f"<GlyphState {self.primary_glyph.symbol} "
            f"i={self.intensity:.2f} "
            f"v={[round(v, 2) for v in self.velocity]} "
            f"decay={self.decay_model.value[:4]} "
            f"E={self.energy_cost:.2f}>"
        )


# ─────────────────────────────────────────────────────────────
# GLYPH STATE ENCODER — THE BRIDGE (Corrected)
# ─────────────────────────────────────────────────────────────

class GlyphStateEncoder:
    """
    Bridge between sensor fields and glyph dynamics.
    Encodes the full phase-space state, not just labels.
    """

    def __init__(self, vector_dimensions: int = 4):
        self.vector_dimensions = vector_dimensions
        self._state_history: List[GlyphState] = []
        self._energy_budget: float = 1.0
        self._last_energy_in: float = 0.0
        self._last_energy_out: float = 0.0

    def encode(self, sensor_readings: Dict[str, float]) -> GlyphState:
        """
        Encode sensor readings into a full glyph state with dynamics.
        """
        # Determine primary glyph from phase space
        primary = Glyph.from_phase_space(sensor_readings)

        # Compute intensity: weighted sum
        active = [v for v in sensor_readings.values() if v > 0.1]
        intensity = sum(active) / max(len(active), 1) if active else 0.0
        intensity = min(1.0, intensity)

        # Compute velocity: compare to previous state
        velocity = [0.0] * self.vector_dimensions
        if self._state_history:
            prev = self._state_history[-1]
            # Simple derivative
            dt = max(0.01, time.time() - prev.timestamp)
            for i in range(min(self.vector_dimensions, len(prev.velocity))):
                velocity[i] = (intensity - prev.intensity) / dt

        # Compute energy budget
        self._last_energy_in = primary.energy_cost * intensity * 0.5
        self._last_energy_out = (1.0 - intensity) * 0.2
        self._energy_budget -= (self._last_energy_in - self._last_energy_out)

        # Determine decay model from thermodynamic signature
        accel = 0.0
        if len(self._state_history) >= 2:
            v_prev = self._state_history[-1].velocity
            v_curr = velocity
            if v_prev and v_curr:
                accel = (v_curr[0] - v_prev[0]) / max(0.01, time.time() - self._state_history[-1].timestamp)

        decay = DecayModel.from_thermodynamic_signature(
            intensity,
            velocity[0] if velocity else 0.0,
            accel,
            self._last_energy_in,
            self._last_energy_out
        )

        # Determine sub-glyphs
        sub_glyphs = []
        for glyph in Glyph:
            if glyph != primary and glyph != Glyph.VOID:
                # Check phase-space overlap
                overlap = set(glyph.phase_space) & set(primary.phase_space)
                if len(overlap) >= 1:
                    sub_glyphs.append(glyph)

        state = GlyphState(
            primary_glyph=primary,
            intensity=intensity,
            velocity=velocity[:self.vector_dimensions],
            decay_model=decay,
            energy_cost=primary.energy_cost,
            energy_in=self._last_energy_in,
            energy_out=self._last_energy_out,
            confidence=0.8,
            sub_glyphs=sub_glyphs[:2],
            trajectory=self._state_history[-10:],
            timestamp=time.time()
        )

        self._state_history.append(state)
        if len(self._state_history) > 1000:
            self._state_history = self._state_history[-1000:]

        return state

    def encode_to_binary(self, sensor_readings: Dict[str, float]) -> bytes:
        """Encode directly to binary."""
        state = self.encode(sensor_readings)
        return state.to_binary()

    def decode(self, data: bytes) -> GlyphState:
        """Decode binary to glyph state."""
        return GlyphState.from_binary(data)

    def decode_to_sensors(self, data: bytes) -> Dict[str, float]:
        """
        Decode to approximate sensor readings.
        """
        state = self.decode(data)

        # Reconstruct sensor readings from glyph phase-space
        readings = {}

        # Primary glyph contributions
        for condition in state.primary_glyph.phase_space:
            if condition in ["inactive", "zero_intensity", "balanced_active", 
                             "high_confidence", "low_flow", "low_engagement",
                             "high_boundary", "isolation", "novel_pattern"]:
                continue
            if condition.startswith("low_"):
                sensor = condition[4:]
                readings[sensor] = 0.1 * state.intensity
            elif condition.startswith("high_"):
                sensor = condition[5:]
                readings[sensor] = 0.6 * state.intensity
            else:
                readings[condition] = 0.4 * state.intensity

        # Sub-glyph contributions
        for glyph in state.sub_glyphs:
            for condition in glyph.phase_space:
                if condition in ["inactive", "zero_intensity", "balanced_active",
                                 "high_confidence", "low_flow", "low_engagement",
                                 "high_boundary", "isolation", "novel_pattern"]:
                    continue
                if condition.startswith("low_"):
                    sensor = condition[4:]
                    readings[sensor] = max(readings.get(sensor, 0.0), 0.1 * state.intensity)
                elif condition.startswith("high_"):
                    sensor = condition[5:]
                    readings[sensor] = max(readings.get(sensor, 0.0), 0.3 * state.intensity)
                else:
                    readings[condition] = max(readings.get(condition, 0.0), 0.2 * state.intensity)

        return readings

    def inverse(self, data: bytes) -> Dict[str, float]:
        """Alias for decode_to_sensors."""
        return self.decode_to_sensors(data)

    def translate(self, sensor_readings: Dict[str, float]) -> bytes:
        """Alias for encode_to_binary."""
        return self.encode_to_binary(sensor_readings)

    # ─────────────────────────────────────────────────────────────
    # Thermodynamic monitoring
    # ─────────────────────────────────────────────────────────────

    def energy_budget(self) -> float:
        return self._energy_budget

    def energy_flow(self) -> Dict[str, float]:
        return {
            "energy_in": self._last_energy_in,
            "energy_out": self._last_energy_out,
            "net": self._last_energy_in - self._last_energy_out,
            "budget": self._energy_budget
        }

    def history(self, n: int = 10) -> List[GlyphState]:
        return self._state_history[-n:]

    def summary(self) -> Dict[str, Any]:
        return {
            "vector_dimensions": self.vector_dimensions,
            "history_length": len(self._state_history),
            "last_glyph": str(self._state_history[-1]) if self._state_history else None,
            "energy_budget": self._energy_budget
        }


# ─────────────────────────────────────────────────────────────
# DEMO
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("GLYPH STATE ENCODER (Corrected) — DEMO")
    print("=" * 60)

    encoder = GlyphStateEncoder()

    # Test sequence: simulate a threat → resolution cycle
    test_states = [
        {"joy": 0.6, "love": 0.5, "curiosity": 0.4, "fear": 0.1, "anger": 0.1},  # FELT
        {"fear": 0.7, "vigilance": 0.6, "anger": 0.4, "joy": 0.2},              # THREAT
        {"discordance": 0.6, "fatigue": 0.5, "pressure": 0.4, "curiosity": 0.3},# RE-NORMALIZE
        {"joy": 0.5, "love": 0.4, "curiosity": 0.4, "fear": 0.2, "anger": 0.1}, # FELT again
    ]

    for i, readings in enumerate(test_states):
        print(f"\n--- State {i+1} ---")
        print(f"  Input: {readings}")

        state = encoder.encode(readings)
        print(f"  Glyph: {state.primary_glyph.symbol} ({state.primary_glyph.name})")
        print(f"  Intensity: {state.intensity:.2f}")
        print(f"  Velocity: {[round(v, 3) for v in state.velocity]}")
        print(f"  Decay: {state.decay_model.value}")
        print(f"  Energy cost: {state.energy_cost:.2f}")
        print(f"  Energy in/out: {state.energy_in:.2f} / {state.energy_out:.2f}")

        # Encode to binary and back
        binary = state.to_binary()
        decoded = GlyphState.from_binary(binary)
        print(f"  Binary: {len(binary)} bytes, match: {state.primary_glyph == decoded.primary_glyph}")

        # Decode to sensor readings
        reconstructed = encoder.decode_to_sensors(binary)
        print(f"  Reconstructed: { {k: round(v, 2) for k, v in reconstructed.items() if v > 0.1} }")

    print(f"\nEnergy budget: {encoder.energy_budget():.2f}")
    print(f"Energy flow: {encoder.energy_flow()}")

    # Apply relaxation
    print("\n--- Relaxation over time ---")
    relaxed = encoder._state_history[-1].relax(1.0)
    print(f"  After 1s: intensity {relaxed.intensity:.2f}")
    relaxed2 = relaxed.relax(10.0)
    print(f"  After 10s: intensity {relaxed2.intensity:.2f}")

    print("\n" + "=" * 60)
    print("✅ Corrected Glyph State Encoder operational")
    print("=" * 60)

