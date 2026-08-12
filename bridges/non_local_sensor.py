# bridges/non_local_sensor.py
# Integrates the non-local-pattern-correlation sensor into SensorSuite.
# CC0 — No Rights Reserved

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional

from .sensor_suite import SensorSuite, SensorReading

# Default path to the sensor definition
_SENSOR_PATH = Path(__file__).parent.parent / "Emotions-as-Sensors" / "sensors" / "non_local_pattern_correlation.json"

class NonLocalCorrelationSensor:
    """
    Represents the non-local-pattern-correlation sensor.
    Uses the JSON spec to determine scale and technique routing.
    """

    def __init__(self, spec_path: Optional[Path] = None):
        path = spec_path or _SENSOR_PATH
        with open(path, "r") as f:
            self.spec = json.load(f)

        self.sensor_id = self.spec["sensor"]
        self.scale_map = self.spec["scale_to_technique"]
        self.techniques = {t["name"]: t for t in self.spec["exploration_techniques"]}
        self.current_scale: Optional[str] = None
        self.current_technique: Optional[str] = None
        self.correlation_strength: float = 0.0
        self.confidence: float = 0.0
        self.last_reading = SensorReading()
        self._history = []

    def update(self, correlation_strength: float, scale: Optional[str] = None,
               technique: Optional[str] = None, confidence: float = 0.5):
        """
        Update the sensor state.
        If scale is not provided, it will be inferred from the correlation strength
        or from the technique used.
        """
        self.correlation_strength = max(0.0, min(1.0, correlation_strength))
        self.confidence = max(0.0, min(1.0, confidence))

        # Automatically select scale if not provided
        if scale is None:
            scale = self._infer_scale(correlation_strength)
        self.current_scale = scale

        # Select technique if not provided
        if technique is None and scale:
            techniques = self.scale_map.get(scale, [])
            if techniques:
                technique = techniques[0]  # default to first
        self.current_technique = technique

        # Create reading vector: [correlation, confidence]
        signal_vector = [correlation_strength, confidence]
        self.last_reading = SensorReading(
            signal_vector=signal_vector,
            magnitude=correlation_strength,
            confidence=confidence,
            beyond_viz=False,
            timestamp=time.time()
        )
        self._history.append((time.time(), self.last_reading))

    def _infer_scale(self, strength: float) -> str:
        """Rough heuristic: low strength → cross_system, high → cellular, etc."""
        if strength < 0.2:
            return "cross_system"
        elif strength < 0.5:
            return "landscape"
        elif strength < 0.8:
            return "generational"
        else:
            return "cellular"

    def read(self) -> SensorReading:
        return self.last_reading

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scale": self.current_scale,
            "technique": self.current_technique,
            "technique_details": self.techniques.get(self.current_technique, {}),
            "confidence": self.confidence,
            "correlation_strength": self.correlation_strength
        }

    def summary(self) -> Dict:
        return {
            "sensor_id": self.sensor_id,
            "current_scale": self.current_scale,
            "current_technique": self.current_technique,
            "correlation_strength": self.correlation_strength,
            "confidence": self.confidence,
            "history_length": len(self._history)
        }

# ── Register with a SensorSuite instance ──

def register_non_local_sensor(suite: SensorSuite, spec_path: Optional[Path] = None) -> None:
    """
    Registers the non-local sensor with a SensorSuite instance.
    Updates the spec to include this sensor ID.
    """
    path = spec_path or _SENSOR_PATH
    with open(path, "r") as f:
        spec = json.load(f)
    sensor_id = spec["sensor"]

    # Ensure the sensor is added to the suite's spec
    if sensor_id not in suite._sensor_defs:
        suite._sensor_defs[sensor_id] = {
            "id": sensor_id,
            "group": spec["sensor_group"],
            "function": spec["function"],
            "resonance_links": spec["resonance_links"],
            "decay_model": spec.get("decay_model", "resonant"),
            "energy": spec.get("energy", "conserves")
        }
        # Initialize state
        suite._states[sensor_id] = SensorReading()

    return sensor_id
