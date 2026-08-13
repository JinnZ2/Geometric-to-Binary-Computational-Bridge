#!/usr/bin/env python3
"""
non_local_sensor.py -- the non-local-pattern-correlation sensor, into SensorSuite.
CC0.

=====================================================================
AUDIT
=====================================================================
NLS-1  The spec path pointed out of this repository, and nothing said so.
       `_SENSOR_PATH` resolved to
       `../Emotions-as-Sensors/sensors/non_local_pattern_correlation.json`,
       a sibling repo that is not mounted here and is not fetched by
       `fieldlink-sync.sh`. So `NonLocalCorrelationSensor()` raised
       `FileNotFoundError` on construction -- the class could not be
       instantiated anywhere in this tree, and the error named a path rather
       than the mount. It now raises `SpecUnavailable` with the sync command,
       and `spec_path` may be passed explicitly so the class is testable
       without the sibling repo. The spec itself is NOT reproduced here: its
       contents are a claim about what the scales and techniques are, and
       guessing them would put a fabricated standard in the position of the
       real one.

NLS-2  The scale/technique pairing cannot disagree with anything.
       `update()` infers `scale` from `correlation_strength`, then selects
       `technique` from `scale`. Both come from one number, so any downstream
       check of the form "does the technique suit the scale" returns a match
       for every input -- measured at 21 of 21 over the full [0, 1] domain,
       including the boundaries. A gate that no input can fail is not a gate.
       This is the same shape as AISS's flat merit weights: the fix is not to
       invent a disagreement but to report the degeneracy alongside the
       answer, so a caller cannot read a tautology as a confirmation.
       `get_metadata()` now carries `scale_is_inferred`, and
       `pairing_is_tautological()` returns the proof.

       The scale is a property of the EXPERIMENT -- what was sampled, over
       what extent, across what interval. It is knowable before the
       correlation is computed and should be supplied, not derived. Passing
       `scale=` explicitly is the non-circular path and is already supported;
       what is missing is any caller that does it. That is GLY/NLS open
       problem NLS-A, and it changes the sensor's interface, so it is not
       decided here.

NLS-3  The inferred ordering makes the interesting case unrepresentable.
       `_infer_scale` maps weak correlation to the LARGEST scale
       (`< 0.2 -> cross_system`) and strong correlation to the SMALLEST
       (`>= 0.8 -> cellular`). Correlation strength is a property of the
       measurement, not of the extent measured over, and the two are not
       related by any stated mechanism. Under this map a strong cross-system
       correlation -- the observation the sensor exists to catch -- cannot be
       recorded at all: it is relabelled cellular on the way in.
       `unrepresentable_pairs()` enumerates what the map excludes. The
       thresholds are kept rather than changed, because replacing them
       requires knowing what the scales mean, which is in the spec this repo
       does not have.

NLS-4  Silent miss when the inferred scale is not a spec key.
       `self.scale_map.get(scale, [])` returns `[]` for an unknown scale and
       `technique` stays `None`, so a spec whose `scale_to_technique` uses any
       key other than the four hard-coded in `_infer_scale` degrades to "no
       technique" without a word. The four names are now checked against the
       loaded spec at construction and a mismatch raises.
"""

import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from .sensor_suite import SensorSuite, SensorReading

#: Lives in the Emotions-as-Sensors repo, mounted by `./fieldlink-sync.sh`.
#: Absent from a bare checkout -- see NLS-1.
_SENSOR_PATH = (Path(__file__).parent.parent / "Emotions-as-Sensors" /
                "sensors" / "non_local_pattern_correlation.json")

#: The scale names `_infer_scale` can produce. Checked against the spec at
#: construction (NLS-4) rather than silently missing.
_INFERRED_SCALES = ("cross_system", "landscape", "generational", "cellular")

#: The boundaries of `_infer_scale`, as (upper_bound, scale). Kept in one
#: place so NLS-2 and NLS-3 measure the function that actually runs.
_SCALE_BANDS: Tuple[Tuple[float, str], ...] = (
    (0.2, "cross_system"),
    (0.5, "landscape"),
    (0.8, "generational"),
    (float("inf"), "cellular"),
)


class SpecUnavailable(FileNotFoundError):
    """The sensor spec is not in this tree. NLS-1."""


class NonLocalCorrelationSensor:
    """The non-local-pattern-correlation sensor.

    Reads the JSON spec for the scale -> technique routing. See the module
    audit: `scale` should be supplied by the caller from the experiment's own
    design; inferring it from `correlation_strength` is supported for
    backwards compatibility and is flagged in every metadata dict it produces.
    """

    def __init__(self, spec_path: Optional[Path] = None,
                 spec: Optional[Dict[str, Any]] = None):
        if spec is None:
            path = Path(spec_path or _SENSOR_PATH)
            if not path.exists():
                raise SpecUnavailable(
                    "%s is not in this repository. It lives in the "
                    "Emotions-as-Sensors repo; run ./fieldlink-sync.sh to "
                    "mount it, or pass spec= / spec_path= explicitly. The "
                    "spec is not reproduced here on purpose -- see NLS-1."
                    % path)
            with open(path, "r", encoding="utf-8") as fh:
                spec = json.load(fh)
        self.spec = spec

        self.sensor_id = self.spec["sensor"]
        self.scale_map = self.spec["scale_to_technique"]
        self.techniques = {t["name"]: t
                           for t in self.spec["exploration_techniques"]}

        missing = [s for s in _INFERRED_SCALES if s not in self.scale_map]
        if missing:
            raise ValueError(
                "NLS-4: _infer_scale can return %s, which the spec's "
                "scale_to_technique does not define. Left unchecked these "
                "select no technique and report none. Either the spec's scale "
                "names changed or _infer_scale's did." % ", ".join(missing))

        self.current_scale: Optional[str] = None
        self.current_technique: Optional[str] = None
        self.scale_was_inferred: bool = False
        self.correlation_strength: float = 0.0
        self.confidence: float = 0.0
        self.last_reading = SensorReading()
        self._history: List[Tuple[float, SensorReading]] = []

    def update(self, correlation_strength: float, scale: Optional[str] = None,
               technique: Optional[str] = None, confidence: float = 0.5):
        """Update the sensor state.

        `scale` is the extent the correlation was measured over and belongs to
        the experiment, not to the result. Omitting it falls back to
        `_infer_scale`, which derives it from `correlation_strength` -- after
        which any scale/technique agreement is a tautology (NLS-2) and strong
        long-range correlations are unrepresentable (NLS-3). The fallback sets
        `scale_was_inferred`, which travels with every metadata dict.
        """
        self.correlation_strength = max(0.0, min(1.0, correlation_strength))
        self.confidence = max(0.0, min(1.0, confidence))

        self.scale_was_inferred = scale is None
        if scale is None:
            scale = self._infer_scale(self.correlation_strength)
        self.current_scale = scale

        if technique is None and scale:
            techniques = self.scale_map.get(scale, [])
            if techniques:
                technique = techniques[0]
        self.current_technique = technique

        self.last_reading = SensorReading(
            signal_vector=[self.correlation_strength, self.confidence],
            magnitude=self.correlation_strength,
            confidence=self.confidence,
            beyond_viz=False,
            timestamp=time.time(),
        )
        self._history.append((time.time(), self.last_reading))

    def _infer_scale(self, strength: float) -> str:
        """Strength -> scale. Circular when its output is later compared to
        anything else derived from strength; see NLS-2 and NLS-3."""
        for upper, name in _SCALE_BANDS:
            if strength < upper:
                return name
        return _SCALE_BANDS[-1][1]

    def read(self) -> SensorReading:
        return self.last_reading

    def get_metadata(self) -> Dict[str, Any]:
        return {
            "scale": self.current_scale,
            "technique": self.current_technique,
            "technique_details": self.techniques.get(self.current_technique, {}),
            "confidence": self.confidence,
            "correlation_strength": self.correlation_strength,
            # NLS-2. True means scale and technique both descend from
            # correlation_strength, so their agreement carries no information.
            "scale_is_inferred": self.scale_was_inferred,
        }

    def summary(self) -> Dict:
        return {
            "sensor_id": self.sensor_id,
            "current_scale": self.current_scale,
            "current_technique": self.current_technique,
            "scale_is_inferred": self.scale_was_inferred,
            "correlation_strength": self.correlation_strength,
            "confidence": self.confidence,
            "history_length": len(self._history),
        }


# ── Measurements ──────────────────────────────────────────────────────

def pairing_is_tautological(sensor: "NonLocalCorrelationSensor",
                            n: int = 21) -> Dict[str, Any]:
    """NLS-2. Sweep the strength domain and count scale/technique mismatches
    when the scale is inferred.

    A mismatch is impossible by construction -- `technique` is read out of
    `scale_map[scale]` -- so the count is zero for every n. Reported as a
    measurement rather than asserted, because the number is the argument.
    """
    mismatches = []
    for i in range(n):
        s = i / float(n - 1)
        sensor.update(correlation_strength=s)
        md = sensor.get_metadata()
        allowed = sensor.scale_map.get(md["scale"], [])
        if md["technique"] not in allowed:
            mismatches.append((s, md["scale"], md["technique"]))
    return {"tested": n, "mismatches": len(mismatches),
            "examples": mismatches[:3],
            "tautological": not mismatches}


def unrepresentable_pairs() -> List[Dict[str, Any]]:
    """NLS-3. (scale, strength band) combinations the inferred map excludes.

    Each row is a real observation the sensor cannot record while the scale is
    inferred: a correlation of that strength measured at that extent gets
    relabelled to whichever scale the strength band names.
    """
    out = []
    lows = [0.0] + [b for b, _ in _SCALE_BANDS[:-1]]
    for i, (_, scale) in enumerate(_SCALE_BANDS):
        lo, hi = lows[i], _SCALE_BANDS[i][0]
        for j, (_, other) in enumerate(_SCALE_BANDS):
            if other == scale:
                continue
            out.append({
                "true_scale": other,
                "strength_band": (lo, 1.0 if hi == float("inf") else hi),
                "recorded_as": scale,
            })
    return out


# ── Register with a SensorSuite instance ──

def register_non_local_sensor(suite: SensorSuite,
                              spec_path: Optional[Path] = None,
                              spec: Optional[Dict[str, Any]] = None) -> str:
    """Register the non-local sensor with a SensorSuite instance."""
    if spec is None:
        path = Path(spec_path or _SENSOR_PATH)
        if not path.exists():
            raise SpecUnavailable(
                "%s is not in this repository; run ./fieldlink-sync.sh or "
                "pass spec= explicitly. NLS-1." % path)
        with open(path, "r", encoding="utf-8") as fh:
            spec = json.load(fh)
    sensor_id = spec["sensor"]

    if sensor_id not in suite._sensor_defs:
        suite._sensor_defs[sensor_id] = {
            "id": sensor_id,
            "group": spec["sensor_group"],
            "function": spec["function"],
            "resonance_links": spec["resonance_links"],
            "decay_model": spec.get("decay_model", "resonant"),
            "energy": spec.get("energy", "conserves"),
        }
        suite._states[sensor_id] = SensorReading()

    return sensor_id
