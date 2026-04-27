"""
epi_classifier — confidence tagging for sensor-derived observations.

Every Primitive carries an explicit epistemology label so downstream
consumers can decide how much weight to give it. The four levels are
ordered by descending strength:

1. ``measured``  — direct sensor reading from real hardware.
2. ``inferred``  — derived from a measurement via a calibrated model
                   (e.g. VWC from raw resistance).
3. ``derived``   — derived from inferred values (regime classification,
                   anomaly score). Two layers removed from raw signal.
4. ``asserted``  — claimed without sensor support. Use sparingly;
                   exists so external knowledge can be threaded into
                   the pipeline without lying about its source.

A Primitive's confidence is the driver's ``confidence_grade`` (a
property on :class:`SensorDriver` subclasses) modified by the context
penalties described in :func:`classify_confidence`. Mock-mode readings
are *always* downgraded to keep them out of any decision the network
makes about real conditions on the ground.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Optional

from sensing.firmware.sensor_drivers.base import SensorReading


class Epistemology(str, Enum):
    """Provenance / certainty class for a Primitive."""

    MEASURED = "measured"
    INFERRED = "inferred"
    DERIVED  = "derived"
    ASSERTED = "asserted"


@dataclass
class ConfidenceFactors:
    """Knobs that pull the final confidence away from the driver's
    headline ``confidence_grade``."""

    mock_penalty: float = 0.40         # mock readings cap at ~0.5
    uncalibrated_penalty: float = 0.10
    saturation_penalty: float = 0.20   # near sensor rail
    missing_baseline_penalty: float = 0.05


def classify_confidence(
    base_grade: float,
    reading: SensorReading,
    *,
    is_calibrated: bool = True,
    near_saturation: bool = False,
    has_baseline: bool = True,
    factors: Optional[ConfidenceFactors] = None,
) -> float:
    """
    Combine a driver's headline confidence grade with context penalties.

    Returns a confidence in ``[0, 1]``. Mock-mode penalty is applied
    first because every other downgrade depends on the result; the
    other penalties stack additively (small enough that order does
    not matter).
    """
    f = factors or ConfidenceFactors()
    grade = max(0.0, min(1.0, base_grade))

    if reading.is_mock:
        # Cap mock readings at base * (1 - mock_penalty). Mock data
        # should never feed a confident decision.
        grade *= (1.0 - f.mock_penalty)

    if not is_calibrated:
        grade -= f.uncalibrated_penalty
    if near_saturation:
        grade -= f.saturation_penalty
    if not has_baseline:
        grade -= f.missing_baseline_penalty

    return max(0.0, min(1.0, round(grade, 3)))


def epi_for_readings(readings: Iterable[SensorReading]) -> Epistemology:
    """
    Pick the appropriate :class:`Epistemology` level for a Primitive
    composed of one or more raw readings.

    * Any non-mock reading → ``MEASURED``.
    * All readings mock → ``INFERRED`` (the values are still grounded
      in driver code; the *substrate* is synthetic).
    * Empty list → ``ASSERTED`` (no sensor support at all — caller
      is making a bare claim).
    """
    samples = list(readings)
    if not samples:
        return Epistemology.ASSERTED
    if all(r.is_mock for r in samples):
        return Epistemology.INFERRED
    return Epistemology.MEASURED


__all__ = [
    "Epistemology",
    "ConfidenceFactors",
    "classify_confidence",
    "epi_for_readings",
]
