"""
test_processing — primitives_encoder, epi_classifier, anomaly_detector.

Coverage:

* Primitive build + serialise + parse round-trip.
* epi_classifier confidence math (mock penalty + calibration knobs).
* AnomalyTracker baseline drift + threshold flagging.
* primitives_to_claim_evidence summary shape.
"""

from __future__ import annotations

import unittest

from sensing.firmware.sensor_drivers.base import SensorReading
from sensing.processing.anomaly_detector import (
    AnomalyTracker,
    RollingBaseline,
)
from sensing.processing.epi_classifier import (
    Epistemology,
    classify_confidence,
    epi_for_readings,
)
from sensing.processing.primitives_encoder import (
    Primitive,
    build_primitive,
    obs_line_to_primitive,
    primitive_to_obs_line,
    primitives_to_claim_evidence,
)


def _real_reading(values, sid="real.x"):
    return SensorReading(
        timestamp_iso="2026-04-27T00:00:00+00:00",
        sensor_id=sid,
        values=values,
        is_mock=False,
    )


def _mock_reading(values, sid="mock.x"):
    return SensorReading(
        timestamp_iso="2026-04-27T00:00:00+00:00",
        sensor_id=sid,
        values=values,
        is_mock=True,
    )


# ---------------------------------------------------------------------------
# epi_classifier
# ---------------------------------------------------------------------------

class TestEpiClassifier(unittest.TestCase):

    def test_mock_reading_is_inferred(self):
        self.assertEqual(
            epi_for_readings([_mock_reading({"v": 1.0})]),
            Epistemology.INFERRED,
        )

    def test_any_real_reading_is_measured(self):
        self.assertEqual(
            epi_for_readings([_real_reading({"v": 1.0}),
                              _mock_reading({"v": 2.0})]),
            Epistemology.MEASURED,
        )

    def test_no_readings_is_asserted(self):
        self.assertEqual(epi_for_readings([]), Epistemology.ASSERTED)

    def test_mock_penalty_caps_confidence(self):
        # Mock reading with grade 1.0 must come back below 1.0.
        c = classify_confidence(
            base_grade=1.0, reading=_mock_reading({"v": 0.0}),
        )
        self.assertLess(c, 1.0)

    def test_real_reading_keeps_grade_when_calibrated(self):
        c = classify_confidence(
            base_grade=0.95, reading=_real_reading({"v": 0.0}),
            is_calibrated=True, near_saturation=False, has_baseline=True,
        )
        self.assertEqual(c, 0.95)

    def test_uncalibrated_penalty_applies(self):
        a = classify_confidence(
            base_grade=0.95, reading=_real_reading({"v": 0.0}),
            is_calibrated=True,
        )
        b = classify_confidence(
            base_grade=0.95, reading=_real_reading({"v": 0.0}),
            is_calibrated=False,
        )
        self.assertGreater(a, b)


# ---------------------------------------------------------------------------
# Primitive serialisation
# ---------------------------------------------------------------------------

class TestPrimitiveCodec(unittest.TestCase):

    def _build(self, **overrides):
        kwargs = dict(
            concept_id="soil_regime",
            domain="measured_kinesthetic",
            role="direct_observation",
            couplings=("temperature", "moisture"),
            bounds=("Superior_MN", "2026_ongoing", "0-50cm"),
            readings=[_real_reading({"celsius": 12.5}, sid="DS18B20.surface")],
            base_confidence_grades=[0.95],
            claim_ref="fourier_heat",
        )
        kwargs.update(overrides)
        return build_primitive(**kwargs)

    def test_obs_round_trip(self):
        p = self._build()
        line = primitive_to_obs_line(p)
        self.assertEqual(line.count("\t"), 9)  # 10 fields → 9 tabs
        back = obs_line_to_primitive(line)
        self.assertEqual(back.concept_id, p.concept_id)
        self.assertEqual(back.bounds, p.bounds)
        self.assertEqual(back.couplings, list(p.couplings))
        self.assertEqual(back.epi, p.epi)
        self.assertEqual(back.epi_confidence, p.epi_confidence)
        self.assertEqual(back.claim_ref, p.claim_ref)

    def test_claim_ref_absence_uses_dash(self):
        p = self._build(claim_ref=None)
        line = primitive_to_obs_line(p)
        self.assertTrue(line.endswith("\t-"))
        back = obs_line_to_primitive(line)
        self.assertIsNone(back.claim_ref)

    def test_tab_in_value_is_rejected(self):
        p = self._build()
        # Mutate an in-memory field to contain a tab.
        p.role = "direct\tobservation"
        with self.assertRaises(ValueError):
            primitive_to_obs_line(p)

    def test_confidence_is_min_of_inputs(self):
        # Two readings with grades 0.9 and 0.5 (both real, calibrated):
        # combined confidence is the minimum.
        p = build_primitive(
            concept_id="multi",
            domain="measured_kinesthetic",
            role="direct_observation",
            couplings=(),
            bounds=("a", "b", "c"),
            readings=[
                _real_reading({"x": 1.0}),
                _real_reading({"y": 2.0}),
            ],
            base_confidence_grades=[0.9, 0.5],
        )
        self.assertEqual(p.epi_confidence, 0.5)


# ---------------------------------------------------------------------------
# AnomalyTracker
# ---------------------------------------------------------------------------

class TestAnomalyTracker(unittest.TestCase):

    def test_warmup_suppresses_flags(self):
        tr = AnomalyTracker(warmup=8, sigma_threshold=3.0)
        # 5 wildly different values shouldn't trip during warmup.
        for v in [10, 100, -100, 50, 0]:
            self.assertFalse(tr.evaluate("ch", v).is_anomaly)

    def test_outlier_after_baseline_is_flagged(self):
        tr = AnomalyTracker(warmup=4, sigma_threshold=3.0)
        # Establish a tight baseline around 10.
        for v in [10.0, 10.1, 9.9, 10.0, 10.05, 9.95, 10.0, 10.0]:
            tr.evaluate("ch", v)
        # Big jump → flagged.
        self.assertTrue(tr.evaluate("ch", 100.0).is_anomaly)

    def test_tracker_per_channel_isolation(self):
        tr = AnomalyTracker(warmup=2, sigma_threshold=2.0)
        for v in [1.0, 1.0, 1.0]:
            tr.evaluate("a", v)
        for v in [1000.0, 1000.0, 1000.0]:
            tr.evaluate("b", v)
        # Channel "a" stays normal at 1.0; "b" stays normal at 1000.
        self.assertFalse(tr.evaluate("a", 1.0).is_anomaly)
        self.assertFalse(tr.evaluate("b", 1000.0).is_anomaly)


# ---------------------------------------------------------------------------
# Claim-evidence summary
# ---------------------------------------------------------------------------

class TestClaimEvidence(unittest.TestCase):

    def _build(self, claim_ref):
        return build_primitive(
            concept_id="x",
            domain="measured_kinesthetic",
            role="direct_observation",
            couplings=(),
            bounds=("Superior_MN", "2026_ongoing", "0-50cm"),
            readings=[_real_reading({"v": 1.0})],
            base_confidence_grades=[0.9],
            claim_ref=claim_ref,
        )

    def test_no_supporting_primitives(self):
        evidence = primitives_to_claim_evidence([], "fourier_heat")
        self.assertEqual(evidence["supporting_primitives"], 0)

    def test_summary_shape(self):
        prims = [
            self._build("fourier_heat"),
            self._build("fourier_heat"),
            self._build("ohmic_dissip"),  # different claim — excluded
        ]
        evidence = primitives_to_claim_evidence(prims, "fourier_heat")
        self.assertEqual(evidence["supporting_primitives"], 2)
        self.assertIn("mean_confidence", evidence)
        self.assertIn("earliest_timestamp", evidence)
        self.assertIn("distinct_bounds", evidence)


if __name__ == "__main__":
    unittest.main()
