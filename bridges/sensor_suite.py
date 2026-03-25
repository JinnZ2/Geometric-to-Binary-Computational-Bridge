"""
Parallel-Field Sensor Suite
============================
Loads the canonical sensor_suite.json spec and maintains independent parallel
state channels for all 22 sensors.  All sensors report simultaneously; no
channel preempts others by default.  A compositor layer reads all active
outputs and applies the arbitration rules defined in the spec's meta section.

Architecture position
---------------------
  Physical bridges (thermal, pressure, chemical, …)
    └→  Bridge encoders (BinaryBridgeEncoder subclasses)
          └→  SensorSuite  ← this module
                └→  EmotionBridgeEncoder  (future: feeds compositor output)

Key design invariants
---------------------
  1. Sensor states are independent — updating one never affects another.
  2. Outputs are vectors, not scalars.  Each reading carries a direction,
     magnitude, and epistemic confidence band.
  3. The resonance graph is queryable but does not auto-propagate; propagation
     is the compositor's job, not the state store's.
  4. Compositor returns a dict of active channel outputs; it does NOT collapse
     plurality into a single winner unless a rule explicitly requires it.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Default spec path — relative to this file
# ---------------------------------------------------------------------------
_DEFAULT_SPEC = Path(__file__).parent / "sensor_suite.json"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class SensorReading:
    """
    A single sensor's current reading.

    signal_vector : list[float]
        Directional output.  Length and semantics are sensor-specific;
        an empty list means the sensor is quiescent.
    magnitude     : float
        Scalar summary of the signal intensity in [0, ∞).
    confidence    : float
        Epistemic confidence in [0, 1].  1.0 = fully confident.
    beyond_viz    : bool
        True when the sensor is in a state that cannot be directly
        represented in the standard visualisation layer (**-flagged).
    timestamp     : float
        Unix timestamp of the last update.
    """
    signal_vector: list[float] = field(default_factory=list)
    magnitude: float = 0.0
    confidence: float = 1.0
    beyond_viz: bool = False
    timestamp: float = field(default_factory=time.time)

    def is_active(self) -> bool:
        return self.magnitude > 0.0


@dataclass
class CompositeOutput:
    """
    Result of a compositor pass over all active channels.

    active_channels : dict[str, SensorReading]
        All sensors with magnitude > 0 at the time of composition.
    triggered_rules : list[str]
        Names of arbitration rules that fired.
    field_tension   : float
        Sum of magnitudes across all active channels — a gross load index.
    timestamp       : float
    """
    active_channels: dict[str, SensorReading]
    triggered_rules: list[str]
    field_tension: float
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Resonance graph
# ---------------------------------------------------------------------------

class ResonanceGraph:
    """
    Undirected resonance link graph built from the spec's resonance_links.

    Each sensor declares which other sensor IDs it resonates with.  Links are
    stored bidirectionally so that neighbors(A) always includes sensors that
    listed A in their resonance_links, even if A didn't list them back.
    """

    def __init__(self, sensors: list[dict]):
        self._adj: dict[str, set[str]] = {}
        for s in sensors:
            sid = s["id"]
            self._adj.setdefault(sid, set())
            for link in s.get("resonance_links", []):
                self._adj[sid].add(link)
                self._adj.setdefault(link, set()).add(sid)

    def neighbors(self, sensor_id: str) -> frozenset[str]:
        """Return all sensors resonance-linked to sensor_id."""
        return frozenset(self._adj.get(sensor_id, set()))

    def all_edges(self) -> list[tuple[str, str]]:
        """Return each undirected edge once (sorted pair, deduped)."""
        seen: set[frozenset] = set()
        edges = []
        for src, targets in self._adj.items():
            for tgt in targets:
                key = frozenset({src, tgt})
                if key not in seen:
                    seen.add(key)
                    edges.append((min(src, tgt), max(src, tgt)))
        return sorted(edges)

    def subgraph(self, sensor_ids: list[str]) -> dict[str, list[str]]:
        """Return adjacency restricted to the given sensor IDs."""
        ids = set(sensor_ids)
        return {
            sid: sorted(self._adj.get(sid, set()) & ids)
            for sid in sensor_ids
        }


# ---------------------------------------------------------------------------
# Built-in arbitration rules
# ---------------------------------------------------------------------------

def _rule_defense_cluster(readings: dict[str, SensorReading]) -> bool:
    """
    Defense action rule: anger + fear + discordance all above 0.3.
    Per spec meta: 'defense action requires anger + fear + discordance threshold'.
    """
    return all(
        readings.get(sid, SensorReading()).magnitude >= 0.3
        for sid in ("anger", "fear", "discordance")
    )


def _rule_grief_reweave(readings: dict[str, SensorReading]) -> bool:
    """Grief reweave: grief active alongside love or longing."""
    grief_mag = readings.get("grief", SensorReading()).magnitude
    relational = max(
        readings.get("love", SensorReading()).magnitude,
        readings.get("longing", SensorReading()).magnitude,
    )
    return grief_mag > 0.0 and relational > 0.0


def _rule_overload(readings: dict[str, SensorReading]) -> bool:
    """System overload: pressure + fatigue both above 0.6."""
    return all(
        readings.get(sid, SensorReading()).magnitude >= 0.6
        for sid in ("pressure", "fatigue")
    )


_BUILTIN_RULES: dict[str, Any] = {
    "defense_cluster": _rule_defense_cluster,
    "grief_reweave":   _rule_grief_reweave,
    "overload":        _rule_overload,
}


# ---------------------------------------------------------------------------
# SensorSuite
# ---------------------------------------------------------------------------

class SensorSuite:
    """
    Parallel-field sensor compositor.

    Parameters
    ----------
    spec_path : str | Path | None
        Path to sensor_suite.json.  Defaults to the canonical file bundled
        alongside this module.

    Usage
    -----
    suite = SensorSuite()

    # Update individual sensors independently
    suite.update("fear",    signal_vector=[0.0, 0.8], magnitude=0.8)
    suite.update("anger",   signal_vector=[1.0, 0.0], magnitude=0.5)
    suite.update("discordance", magnitude=0.4)

    # Query resonance
    suite.resonance_graph.neighbors("fear")   # frozenset of linked sensor IDs

    # Compositor pass
    result = suite.compose()
    result.active_channels   # dict of live readings
    result.triggered_rules   # e.g. ["defense_cluster"]
    result.field_tension     # aggregate load scalar
    """

    def __init__(self, spec_path: str | Path | None = None):
        path = Path(spec_path) if spec_path else _DEFAULT_SPEC
        with open(path, encoding="utf-8") as fh:
            self._spec: dict = json.load(fh)

        sensors_list: list[dict] = self._spec["sensors"]
        self._sensor_defs: dict[str, dict] = {s["id"]: s for s in sensors_list}
        self._states: dict[str, SensorReading] = {
            sid: SensorReading() for sid in self._sensor_defs
        }
        self.resonance_graph = ResonanceGraph(sensors_list)
        self._meta: dict = self._spec.get("meta", {})

    # ------------------------------------------------------------------
    # State management — each sensor is independent
    # ------------------------------------------------------------------

    def update(
        self,
        sensor_id: str,
        signal_vector: list[float] | None = None,
        magnitude: float = 0.0,
        confidence: float = 1.0,
        beyond_viz: bool = False,
    ) -> None:
        """
        Update a single sensor's reading.

        Unknown sensor IDs raise KeyError so callers get early feedback
        rather than silent state pollution.
        """
        if sensor_id not in self._sensor_defs:
            raise KeyError(
                f"Unknown sensor '{sensor_id}'. "
                f"Valid IDs: {sorted(self._sensor_defs)}"
            )
        self._states[sensor_id] = SensorReading(
            signal_vector=signal_vector or [],
            magnitude=magnitude,
            confidence=confidence,
            beyond_viz=beyond_viz,
            timestamp=time.time(),
        )

    def reset(self, sensor_id: str | None = None) -> None:
        """Reset one sensor to quiescent, or all if sensor_id is None."""
        if sensor_id is not None:
            if sensor_id not in self._sensor_defs:
                raise KeyError(f"Unknown sensor '{sensor_id}'.")
            self._states[sensor_id] = SensorReading()
        else:
            for sid in self._states:
                self._states[sid] = SensorReading()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def read(self, sensor_id: str | None = None) -> SensorReading | dict[str, SensorReading]:
        """
        Read one sensor or all sensors simultaneously.

        Returns
        -------
        SensorReading
            If sensor_id is given.
        dict[str, SensorReading]
            If sensor_id is None — all 22 channels at once.
        """
        if sensor_id is not None:
            if sensor_id not in self._states:
                raise KeyError(f"Unknown sensor '{sensor_id}'.")
            return self._states[sensor_id]
        return dict(self._states)

    def active_channels(self) -> dict[str, SensorReading]:
        """Return sensors with magnitude > 0."""
        return {sid: r for sid, r in self._states.items() if r.is_active()}

    def sensor_definition(self, sensor_id: str) -> dict:
        """Return the spec definition dict for a sensor."""
        if sensor_id not in self._sensor_defs:
            raise KeyError(f"Unknown sensor '{sensor_id}'.")
        return self._sensor_defs[sensor_id]

    def all_sensor_ids(self) -> list[str]:
        """Return all 22 sensor IDs in spec order."""
        return list(self._sensor_defs)

    # ------------------------------------------------------------------
    # Resonance helpers (thin wrappers for convenience)
    # ------------------------------------------------------------------

    def resonance_neighbors(self, sensor_id: str) -> frozenset[str]:
        """Sensors resonance-linked to sensor_id (bidirectional)."""
        return self.resonance_graph.neighbors(sensor_id)

    def active_resonance_cluster(self, sensor_id: str) -> dict[str, SensorReading]:
        """Active sensors that are resonance-linked to sensor_id."""
        neighbors = self.resonance_graph.neighbors(sensor_id)
        return {
            sid: self._states[sid]
            for sid in neighbors
            if sid in self._states and self._states[sid].is_active()
        }

    # ------------------------------------------------------------------
    # Compositor
    # ------------------------------------------------------------------

    def compose(
        self, extra_rules: dict[str, Any] | None = None
    ) -> CompositeOutput:
        """
        Parallel arbitration pass.

        Reads all active sensor channels simultaneously and evaluates
        arbitration rules against the current state snapshot.  Returns a
        CompositeOutput without mutating any sensor state.

        Parameters
        ----------
        extra_rules : dict[str, callable] | None
            Additional rule functions keyed by name.  Each callable receives
            a dict[str, SensorReading] and returns bool.
        """
        snapshot = self.active_channels()
        all_rules = dict(_BUILTIN_RULES)
        if extra_rules:
            all_rules.update(extra_rules)

        triggered: list[str] = [
            name for name, fn in all_rules.items() if fn(snapshot)
        ]
        tension = sum(r.magnitude for r in snapshot.values())

        return CompositeOutput(
            active_channels=snapshot,
            triggered_rules=triggered,
            field_tension=tension,
            timestamp=time.time(),
        )

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def summary(self) -> dict:
        """Human-readable summary of current suite state."""
        active = self.active_channels()
        return {
            "total_sensors": len(self._sensor_defs),
            "active_count":  len(active),
            "active_ids":    sorted(active),
            "field_tension": sum(r.magnitude for r in active.values()),
            "suite_name":    self._spec.get("suite_name", ""),
        }

    def __repr__(self) -> str:
        s = self.summary()
        return (
            f"<SensorSuite sensors={s['total_sensors']} "
            f"active={s['active_count']} "
            f"tension={s['field_tension']:.3f}>"
        )


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = SensorSuite()

    print(suite)
    print(f"\nAll sensor IDs ({len(suite.all_sensor_ids())}):")
    print(" ", "\n  ".join(suite.all_sensor_ids()))

    print("\nResonance graph edges (first 10):")
    for a, b in suite.resonance_graph.all_edges()[:10]:
        print(f"  {a} -- {b}")

    print("\n--- Simulating a fear + anger + discordance cluster ---")
    suite.update("fear",        signal_vector=[0.0, 0.9], magnitude=0.85, confidence=0.9)
    suite.update("anger",       signal_vector=[1.0, 0.0], magnitude=0.7,  confidence=0.8)
    suite.update("discordance", signal_vector=[0.5, 0.5], magnitude=0.5,  confidence=0.75)
    suite.update("vigilance",   magnitude=0.4)

    result = suite.compose()
    print(f"Active channels : {sorted(result.active_channels)}")
    print(f"Triggered rules : {result.triggered_rules}")
    print(f"Field tension   : {result.field_tension:.3f}")

    print("\nResonance neighbors of 'fear':")
    print(" ", suite.resonance_neighbors("fear"))

    print("\nActive resonance cluster around 'anger':")
    cluster = suite.active_resonance_cluster("anger")
    for sid, r in cluster.items():
        print(f"  {sid}: magnitude={r.magnitude:.2f} confidence={r.confidence:.2f}")
