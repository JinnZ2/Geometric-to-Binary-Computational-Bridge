"""
processing — turn raw SensorReadings into Primitives + detect anomalies.

Three modules:

* :mod:`epi_classifier` — classify the *epistemology* of an
  observation (measured / inferred / derived / asserted) and assign
  a confidence value. Drivers carry a ``confidence_grade``; the
  classifier may downgrade it based on context (e.g. mock-mode reading,
  missing calibration, near a sensor's saturation point).

* :mod:`primitives_encoder` — bundle a list of SensorReadings into a
  :class:`Primitive` with bounds, couplings, epistemology, and
  optional ``claim_ref`` linking to a CLAIM_SCHEMA law in the repo
  root. Serialise to ``.obs`` (one Primitive per line) or to JSON.

* :mod:`anomaly_detector` — compare a fresh reading against a
  rolling baseline and flag deviations big enough to escalate to
  the next priority level. Lightweight (mean ± k·σ + EWMA) so it
  runs on a Pi Zero.
"""
