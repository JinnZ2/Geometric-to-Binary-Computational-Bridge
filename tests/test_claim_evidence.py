"""
tests/test_claim_evidence.py
============================

Covers the claim_ref ↔ Primitive verifier:

* :mod:`bridges.claim_evidence` core API.
* :mod:`sensing.processing.claim_match` repo-aware wrapper.
* CI-style gate that asserts every shipped ``sensing/examples/*.obs``
  file is fully verified against the shipped ``.claims`` table.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from bridges.claim_evidence import (
    BulkVerificationReport,
    MeasurementVocabulary,
    VerificationResult,
    default_vocabulary,
    find_applicable_claims,
    verify_primitive_against_claim,
    verify_primitives_bulk,
)
from sensing.firmware.sensor_drivers.base import SensorReading
from sensing.processing.claim_match import (
    claim_for,
    load_repo_claims,
    suggest_claims,
    verify_obs_file,
    verify_primitive,
)
from sensing.processing.primitives_encoder import build_primitive


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLES_DIR = REPO_ROOT / "sensing" / "examples"


def _real_reading(values, sid):
    return SensorReading(
        timestamp_iso="2026-04-27T00:00:00+00:00",
        sensor_id=sid,
        values=values,
        is_mock=False,
    )


def _build(claim_ref="fourier_heat", devices=("DS18B20.surface",)):
    readings = [
        _real_reading({"celsius": 12.5}, sid=sid) for sid in devices
    ]
    return build_primitive(
        concept_id="x",
        domain="measured_kinesthetic",
        role="direct_observation",
        couplings=(),
        bounds=("Superior_MN", "2026_April", "0-30cm"),
        readings=readings,
        base_confidence_grades=[0.95] * len(readings),
        claim_ref=claim_ref,
    )


# ---------------------------------------------------------------------------
# MeasurementVocabulary
# ---------------------------------------------------------------------------

class TestMeasurementVocabulary(unittest.TestCase):

    def test_default_known_devices(self):
        vocab = default_vocabulary()
        self.assertIn("DS18B20", vocab.known_devices())
        self.assertIn("MLX90614", vocab.known_devices())

    def test_supports_lookup(self):
        vocab = default_vocabulary()
        self.assertTrue(vocab.supports("DS18B20", "thermocouple_array"))
        self.assertFalse(vocab.supports("DS18B20", "spectrogram"))

    def test_with_extension_does_not_mutate(self):
        original = default_vocabulary()
        extended = original.with_extension(
            {"CustomSensor": ("FFT", "phase_locked_loop")}
        )
        self.assertNotIn("CustomSensor", original.known_devices())
        self.assertIn("CustomSensor", extended.known_devices())
        self.assertTrue(extended.supports("CustomSensor", "FFT"))


# ---------------------------------------------------------------------------
# verify_primitive_against_claim
# ---------------------------------------------------------------------------

class TestVerifyAgainstClaim(unittest.TestCase):

    def test_matched_temperature_primitive(self):
        claim = {
            "id": "fourier_heat",
            "meas": ["thermocouple_array", "IR_camera"],
        }
        prim = _build(claim_ref="fourier_heat")
        result = verify_primitive_against_claim(prim, claim)
        self.assertTrue(result.ok)
        self.assertIn("thermocouple_array", result.matched_meas)

    def test_wrong_claim_ref_is_rejected(self):
        claim = {
            "id": "fourier_heat",
            "meas": ["thermocouple_array"],
        }
        prim = _build(claim_ref="larmor_precess")
        result = verify_primitive_against_claim(prim, claim)
        self.assertFalse(result.ok)
        self.assertTrue(any("does not match" in r for r in result.reasons))

    def test_no_claim_ref_is_rejected(self):
        claim = {"id": "fourier_heat", "meas": ["thermocouple_array"]}
        prim = _build(claim_ref=None)
        result = verify_primitive_against_claim(prim, claim)
        self.assertFalse(result.ok)
        self.assertTrue(any("no claim_ref" in r for r in result.reasons))

    def test_vocabulary_mismatch_is_rejected(self):
        # Microphone cannot back the Fourier heat claim — nothing in
        # its vocabulary maps to a thermal measurement.
        claim = {"id": "fourier_heat", "meas": ["thermocouple_array"]}
        prim = _build(
            claim_ref="fourier_heat",
            devices=("Microphone.ambient",),
        )
        result = verify_primitive_against_claim(prim, claim)
        self.assertFalse(result.ok)
        self.assertTrue(any(
            "produces any of" in r or "vocabulary" in r
            for r in result.reasons
        ))

    def test_optional_bounds_overlap(self):
        claim = {
            "id": "fourier_heat",
            "meas": ["thermocouple_array"],
            "bounds": "solid_or_static_fluid,isotropic",
        }
        prim = _build(claim_ref="fourier_heat")
        # Without bounds-overlap requirement: passes.
        self.assertTrue(verify_primitive_against_claim(prim, claim).ok)
        # With bounds-overlap requirement: fails (Superior_MN ≠ solid).
        self.assertFalse(
            verify_primitive_against_claim(
                prim, claim, require_bounds_overlap=True,
            ).ok,
        )


# ---------------------------------------------------------------------------
# find_applicable_claims
# ---------------------------------------------------------------------------

class TestFindApplicableClaims(unittest.TestCase):

    def test_returns_thermal_claims_for_temp_sensor(self):
        prim = _build(claim_ref=None, devices=("DS18B20.surface",))
        claims = [
            {"id": "fourier_heat", "meas": ["thermocouple_array"]},
            {"id": "doppler_shift", "meas": ["spectrogram"]},
            {"id": "thermal_rad",  "meas": ["bolometer", "IR_spectrometer"]},
        ]
        applicable = find_applicable_claims(prim, claims)
        self.assertIn("fourier_heat", applicable)
        self.assertNotIn("doppler_shift", applicable)


# ---------------------------------------------------------------------------
# verify_primitives_bulk
# ---------------------------------------------------------------------------

class TestVerifyBulk(unittest.TestCase):

    def test_aggregates_outcomes(self):
        claims = [
            {"id": "fourier_heat", "meas": ["thermocouple_array"]},
            {"id": "doppler_shift", "meas": ["spectrogram"]},
        ]
        prims = [
            _build(claim_ref="fourier_heat"),               # ok
            _build(claim_ref="fourier_heat",
                   devices=("Microphone.ambient",)),         # vocab fail
            _build(claim_ref=None),                          # unattributed
            _build(claim_ref="nonexistent_law"),             # missing claim
        ]
        report = verify_primitives_bulk(prims, claims)
        self.assertEqual(report.total_primitives, 4)
        self.assertEqual(report.verified, 1)
        self.assertEqual(report.rejected, 1)
        self.assertEqual(report.unattributed, 1)
        self.assertEqual(report.missing_claim, 1)


# ---------------------------------------------------------------------------
# Sensing-side wrapper
# ---------------------------------------------------------------------------

class TestSensingClaimMatch(unittest.TestCase):

    def test_load_repo_claims_returns_dicts(self):
        claims = load_repo_claims()
        self.assertGreater(len(claims), 0)
        self.assertIn("id", claims[0])
        self.assertIn("rate", claims[0])
        self.assertIn("meas", claims[0])

    def test_claim_for_resolves_real_id(self):
        prim = _build(claim_ref="fourier_heat")
        c = claim_for(prim)
        self.assertIsNotNone(c)
        self.assertEqual(c["id"], "fourier_heat")

    def test_claim_for_returns_none_when_missing(self):
        prim = _build(claim_ref="nonexistent_law")
        self.assertIsNone(claim_for(prim))

    def test_verify_primitive_with_repo_table(self):
        prim = _build(claim_ref="fourier_heat")
        result = verify_primitive(prim)
        self.assertTrue(result.ok)

    def test_suggest_claims_for_temp_only_primitive(self):
        prim = _build(claim_ref=None)
        suggestions = suggest_claims(prim)
        # DS18B20 → thermocouple_array → fourier_heat ∪ thermal_rad ∪ etc.
        self.assertIn("fourier_heat", suggestions)


# ---------------------------------------------------------------------------
# Shipped sample .obs gate
# ---------------------------------------------------------------------------

class TestShippedExamplesAreVerified(unittest.TestCase):
    """CI gate: every ``sensing/examples/*.obs`` file must verify
    100% against the shipped claim table. A regression here means
    either a sample was generated against a stale catalogue, or the
    catalogue lost a claim a sample relies on."""

    def test_all_examples_fully_verified(self):
        obs_files = sorted(EXAMPLES_DIR.glob("*.obs"))
        self.assertGreater(len(obs_files), 0,
                           f"no .obs files under {EXAMPLES_DIR}")
        for path in obs_files:
            with self.subTest(file=path.name):
                report = verify_obs_file(path)
                self.assertEqual(
                    report.rejected, 0,
                    f"{path.name}: {report.failures}",
                )
                self.assertEqual(
                    report.missing_claim, 0,
                    f"{path.name}: {report.failures}",
                )
                # Unattributed Primitives are allowed (some samples
                # legitimately have None claim_ref), but the verified
                # count should equal total - unattributed.
                self.assertEqual(
                    report.verified,
                    report.total_primitives - report.unattributed,
                    f"{path.name}: not every attributed primitive verified",
                )


if __name__ == "__main__":
    unittest.main()
