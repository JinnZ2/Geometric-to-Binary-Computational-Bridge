"""
tests/test_light_drivers.py
===========================

Covers the Tier-2 light layer:

* :class:`~sensing.firmware.sensor_drivers.light_spectrum.AS7341Driver`
  — multispectral driver, *no* hidden channel (amplitude-only).
* :class:`~sensing.firmware.sensor_drivers.light_polarization.RotatingPolarizerDriver`
  — declares the ``polarization_linear`` shape channel; its
  Stokes-recovery math round-trips for synthetic ideal beams.
* :mod:`bridges.hidden_channel_detector` flags the polarization
  driver as having a hidden channel and lets the AS7341 pass.
* End-to-end: a Primitive whose ``claim_ref="polarization_malus"``
  verifies cleanly against the shipped CLAIM_TABLE through the
  default :class:`~bridges.claim_evidence.MeasurementVocabulary`.
"""

from __future__ import annotations

import math
import time
import unittest
from unittest import mock

from bridges.hidden_channel_detector import (
    SHAPE_CHANNEL_REGISTRY,
    HiddenChannelReport,
    detect_hidden_channels,
    shape_channels_of,
)
from sensing.firmware.sensor_drivers import (
    AS7341_CHANNELS_NM,
    AS7341Driver,
    RotatingPolarizerDriver,
)
from sensing.firmware.sensor_drivers.light_polarization import (
    _dolp_aop,
    _stokes_from_intensities,
)


# ---------------------------------------------------------------------------
# AS7341 (spectrum, amplitude-only)
# ---------------------------------------------------------------------------

class TestAS7341Driver(unittest.TestCase):

    def test_returns_all_nine_channels(self):
        d = AS7341Driver(mock=True, seed=42)
        r = d.read()
        for name, _ in AS7341_CHANNELS_NM:
            self.assertIn(name, r.values)
        self.assertEqual(len(r.values), len(AS7341_CHANNELS_NM))

    def test_advertises_no_shape_channel(self):
        d = AS7341Driver(mock=True, seed=42)
        self.assertEqual(shape_channels_of(d), [])

    def test_detector_marks_scalar_sufficient(self):
        d = AS7341Driver(mock=True, seed=42)
        report = detect_hidden_channels(d, claimed_channel="intensity")
        self.assertTrue(report.scalar_sufficient)
        self.assertEqual(report.hidden_channels, ())

    def test_seeded_repeatable(self):
        a = AS7341Driver(mock=True, seed=99).read()
        b = AS7341Driver(mock=True, seed=99).read()
        for name in a.values:
            self.assertAlmostEqual(a.values[name], b.values[name], places=4)


# ---------------------------------------------------------------------------
# RotatingPolarizerDriver (polarization, hidden channel)
# ---------------------------------------------------------------------------

class TestRotatingPolarizerDriver(unittest.TestCase):

    def test_advertises_polarization_linear_channel(self):
        d = RotatingPolarizerDriver(mock=True, seed=42)
        channels = shape_channels_of(d)
        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0].name, "polarization_linear")

    def test_detector_flags_hidden_channel(self):
        d = RotatingPolarizerDriver(mock=True, seed=42)
        report = detect_hidden_channels(d, claimed_channel="intensity")
        self.assertFalse(report.scalar_sufficient)
        names = [c.name for c in report.hidden_channels]
        self.assertIn("polarization_linear", names)
        self.assertTrue(any("Scalar model insufficient" in n for n in report.notes))

    def test_extras_list_can_suppress_flag(self):
        # An audit caller who has *already* accounted for polarization
        # passes that explicitly; the report should then mark scalar
        # as sufficient (no NEW hidden channels surfaced).
        d = RotatingPolarizerDriver(mock=True, seed=42)
        report = detect_hidden_channels(
            d, claimed_channel="intensity",
            extra_known_channels=("polarization_linear",),
        )
        self.assertTrue(report.scalar_sufficient)

    def test_returns_dolp_aop_intensity(self):
        d = RotatingPolarizerDriver(mock=True, seed=42)
        r = d.read()
        for k in ("intensity", "dolp", "aop_degrees"):
            self.assertIn(k, r.values)

    def test_note_carries_shape_channel_marker(self):
        d = RotatingPolarizerDriver(mock=True, seed=42)
        r = d.read()
        self.assertIn("shape_channel=polarization_linear", r.note)


class TestStokesRecovery(unittest.TestCase):
    """Verify the Stokes-decomposition math against a synthetic ideal
    beam — no driver, no diurnal envelope, just the physics."""

    def _build_intensities(self, s0, s1, s2, angles_deg=(0, 45, 90, 135)):
        """Inverse of the recovery — produce I(θ) for a known Stokes vector."""
        angles_rad = tuple(math.radians(d) for d in angles_deg)
        intensities = [
            0.5 * (s0 + s1 * math.cos(2 * theta) + s2 * math.sin(2 * theta))
            for theta in angles_rad
        ]
        return intensities, angles_rad

    def test_unpolarised_beam_gives_zero_dolp(self):
        intensities, angles = self._build_intensities(s0=1.0, s1=0.0, s2=0.0)
        s0, s1, s2 = _stokes_from_intensities(intensities, angles)
        dolp, _aop = _dolp_aop(s0, s1, s2)
        self.assertAlmostEqual(s0, 1.0, places=6)
        self.assertAlmostEqual(dolp, 0.0, places=6)

    def test_fully_polarised_horizontal(self):
        # S₀=1, S₁=1, S₂=0 — fully linearly polarised at θ₀=0°.
        intensities, angles = self._build_intensities(s0=1.0, s1=1.0, s2=0.0)
        s0, s1, s2 = _stokes_from_intensities(intensities, angles)
        dolp, aop = _dolp_aop(s0, s1, s2)
        self.assertAlmostEqual(dolp, 1.0, places=6)
        self.assertAlmostEqual(math.degrees(aop), 0.0, places=4)

    def test_fully_polarised_45deg(self):
        intensities, angles = self._build_intensities(s0=1.0, s1=0.0, s2=1.0)
        s0, s1, s2 = _stokes_from_intensities(intensities, angles)
        dolp, aop = _dolp_aop(s0, s1, s2)
        self.assertAlmostEqual(dolp, 1.0, places=6)
        self.assertAlmostEqual(math.degrees(aop), 45.0, places=4)

    def test_partially_polarised_50_percent(self):
        intensities, angles = self._build_intensities(s0=2.0, s1=1.0, s2=0.0)
        s0, s1, s2 = _stokes_from_intensities(intensities, angles)
        dolp, _aop = _dolp_aop(s0, s1, s2)
        self.assertAlmostEqual(dolp, 0.5, places=6)


# ---------------------------------------------------------------------------
# CLAIM_SCHEMA bridge — light Primitives verify against shipped table
# ---------------------------------------------------------------------------

class TestLightClaimVerification(unittest.TestCase):
    """The polarization driver should produce Primitives whose
    ``claim_ref="polarization_malus"`` verifies cleanly against the
    shipped CLAIM_TABLE through the default measurement vocabulary."""

    def _force_daytime(self):
        """Force the diurnal envelope into solar-noon range so the
        mock polarization mock has a non-trivial intensity to work
        with. Patches ``time.time`` to a fixed UTC noon."""
        import datetime as _dt
        noon_utc = _dt.datetime(
            2026, 6, 21, 12, 0, 0, tzinfo=_dt.timezone.utc,
        )
        return mock.patch.object(
            time, "time", return_value=noon_utc.timestamp(),
        )

    def test_polarization_primitive_verifies_against_polarization_malus(self):
        from sensing.firmware.sensor_drivers import RotatingPolarizerDriver
        from sensing.processing.primitives_encoder import build_primitive
        from sensing.processing.claim_match import verify_primitive

        with self._force_daytime():
            d = RotatingPolarizerDriver(mock=True, seed=42)
            reading = d.read()

        prim = build_primitive(
            concept_id="optical_axis_pol",
            domain="measured_kinesthetic",
            role="direct_observation",
            couplings=("polarization_basis",),
            bounds=("Superior_MN", "2026_June", "outdoor"),
            readings=[reading],
            base_confidence_grades=[d.confidence_grade],
            claim_ref="polarization_malus",
        )
        result = verify_primitive(prim)
        self.assertTrue(result.ok, msg=str(result.reasons))
        self.assertIn("rotating_polarizer", result.matched_meas)

    def test_as7341_primitive_verifies_against_photon_energy(self):
        from sensing.firmware.sensor_drivers import AS7341Driver
        from sensing.processing.primitives_encoder import build_primitive
        from sensing.processing.claim_match import verify_primitive

        with self._force_daytime():
            d = AS7341Driver(mock=True, seed=42)
            reading = d.read()

        prim = build_primitive(
            concept_id="canopy_spectrum",
            domain="measured_kinesthetic",
            role="direct_observation",
            couplings=("spectral_intensity",),
            bounds=("Superior_MN", "2026_June", "outdoor"),
            readings=[reading],
            base_confidence_grades=[d.confidence_grade],
            claim_ref="photon_energy",
        )
        result = verify_primitive(prim)
        self.assertTrue(result.ok, msg=str(result.reasons))
        self.assertIn("spectrometer", result.matched_meas)


# ---------------------------------------------------------------------------
# ShapeChannel registry sanity
# ---------------------------------------------------------------------------

class TestShapeChannelRegistry(unittest.TestCase):

    def test_registered_channels_have_consistent_dof(self):
        for name, channel in SHAPE_CHANNEL_REGISTRY.items():
            self.assertEqual(
                len(channel.basis_axes), channel.dof,
                f"{name}: basis_axes count != dof",
            )
            self.assertGreater(channel.dof, 0)

    def test_polarization_channels_present(self):
        self.assertIn("polarization", SHAPE_CHANNEL_REGISTRY)
        self.assertIn("polarization_linear", SHAPE_CHANNEL_REGISTRY)

    def test_full_polarization_has_four_dof(self):
        pol = SHAPE_CHANNEL_REGISTRY["polarization"]
        self.assertEqual(pol.dof, 4)
        self.assertEqual(pol.basis_axes, ("S_0", "S_1", "S_2", "S_3"))

    def test_linear_polarization_has_three_dof(self):
        pol = SHAPE_CHANNEL_REGISTRY["polarization_linear"]
        self.assertEqual(pol.dof, 3)


# ---------------------------------------------------------------------------
# detect_hidden_channels on objects without the protocol
# ---------------------------------------------------------------------------

class TestDetectorOnUnknownObjects(unittest.TestCase):

    def test_object_without_protocol_is_scalar_sufficient(self):
        report = detect_hidden_channels(
            object(), claimed_channel="intensity",
        )
        self.assertTrue(report.scalar_sufficient)
        self.assertEqual(report.hidden_channels, ())

    def test_misbehaving_protocol_raise_is_swallowed(self):
        class BrokenDriver:
            def shape_channels(self):
                raise RuntimeError("intentional")

        # shape_channels_of swallows the error → empty list →
        # scalar_sufficient.
        report = detect_hidden_channels(
            BrokenDriver(), claimed_channel="intensity",
        )
        self.assertTrue(report.scalar_sufficient)


if __name__ == "__main__":
    unittest.main()
