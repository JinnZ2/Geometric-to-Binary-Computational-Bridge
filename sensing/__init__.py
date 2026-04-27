"""
sensing — direct observation → primitive → CLAIM_SCHEMA bridge.

This subpackage is the field-side counterpart to the codebase's
in-silico modules. It is built to run on whatever power you have
(Pi Zero, old phone, laptop), with whatever hardware you have today
(or none — every driver supports a mock mode). Outputs are
``Primitive`` records: timestamped, location-stamped measurements
with explicit epistemic confidence.

Three layers:

* ``firmware/sensor_drivers/`` — one driver per sensor class.
  Real hardware mode imports the device library; mock mode emits
  plausible synthetic data so the entire pipeline runs in CI.
* ``processing/`` — turn raw readings into Primitives (with
  confidence tagging) and detect anomalies relative to a baseline.
* ``transmission/`` — queue and ship Primitives over LoRa, HAM
  packet (KISS), or CB; queue manager persists everything when no
  link is available.

Outputs land in ``.obs`` files (one Primitive per line). To promote
a sustained set of Primitives into a CLAIM_SCHEMA differential law,
see ``processing/primitives_encoder.py::primitives_to_claim``.
"""

from sensing.processing.primitives_encoder import (
    Primitive,
    primitive_to_obs_line,
    obs_line_to_primitive,
)
from sensing.processing.epi_classifier import (
    Epistemology,
    classify_confidence,
)

__all__ = [
    "Primitive",
    "primitive_to_obs_line",
    "obs_line_to_primitive",
    "Epistemology",
    "classify_confidence",
]
