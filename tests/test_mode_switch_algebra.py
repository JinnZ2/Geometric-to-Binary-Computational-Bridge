"""
tests/test_mode_switch_algebra.py
=================================

Covers the recognition note's open questions 3 and 4:

* :mod:`bridges.mode_switch_algebra` — answer to question 3
  ("is spin-separation the same algebra as the K⁺ mode-switch?")
  is "no, two distinct flavours". The module names them
  THRESHOLD_CROSSING (DmAlka, EDC × heat) and LATENT_BASIS
  (vectorial spin-separation), provides three concrete instances,
  and ships a classifier.

* :class:`bridges.hidden_channel_detector.LeverageProbe` — answer
  to question 4 ("auto-flag whisper-redirects-hurricane regime").
  The detector now reads ``current_leverage()`` off any receiver
  that implements the protocol, surfaces it in
  :class:`HiddenChannelReport`, and flags
  ``is_high_leverage = True`` when the value is ≥
  :data:`HIGH_LEVERAGE_THRESHOLD`.
"""

from __future__ import annotations

import math
import unittest

from bridges.edc_thermal_coupling import (
    EDCConfig,
    EDCThermalCouplingState,
    ThermalContext,
    apparent_Kd,
    simulate,
)
from bridges.hidden_channel_detector import (
    HIGH_LEVERAGE_THRESHOLD,
    LeverageProbe,
    current_leverage_of,
    detect_hidden_channels,
)
from bridges.mode_switch_algebra import (
    MODE_SWITCH_REGISTRY,
    ModeSwitch,
    ModeSwitchPattern,
    classify_pattern,
    get_mode_switch,
    known_instances_by_pattern,
)


# ---------------------------------------------------------------------------
# Mode-switch registry
# ---------------------------------------------------------------------------

class TestModeSwitchRegistry(unittest.TestCase):

    def test_three_known_instances(self):
        self.assertEqual(
            sorted(MODE_SWITCH_REGISTRY),
            ["dmalka_k_plus", "edc_thermal", "vectorial_spin"],
        )

    def test_dmalka_is_threshold_crossing(self):
        ms = get_mode_switch("dmalka_k_plus")
        self.assertEqual(ms.pattern, ModeSwitchPattern.THRESHOLD_CROSSING)
        self.assertEqual(ms.shape_channel.name, "ion_coordination")
        self.assertIsNotNone(ms.threshold)

    def test_edc_thermal_is_threshold_crossing(self):
        ms = get_mode_switch("edc_thermal")
        self.assertEqual(ms.pattern, ModeSwitchPattern.THRESHOLD_CROSSING)
        self.assertEqual(ms.shape_channel.name, "hormone_geometry")
        # Leverage peak is ln(10)/4 ≈ 0.5757 (Hill-1 analytic).
        self.assertAlmostEqual(ms.leverage_peak, math.log(10) / 4.0, places=4)

    def test_vectorial_spin_is_latent_basis(self):
        ms = get_mode_switch("vectorial_spin")
        self.assertEqual(ms.pattern, ModeSwitchPattern.LATENT_BASIS)
        self.assertEqual(ms.shape_channel.name, "spin_separation")
        # Latent-basis instances have no single threshold.
        self.assertIsNone(ms.threshold)
        # And no analytic leverage peak (leverage is roughly flat).
        self.assertIsNone(ms.leverage_peak)

    def test_unknown_lookup_raises(self):
        with self.assertRaises(KeyError):
            get_mode_switch("not_a_real_switch")

    def test_known_by_pattern_partitions_registry(self):
        thresh = known_instances_by_pattern(
            ModeSwitchPattern.THRESHOLD_CROSSING,
        )
        latent = known_instances_by_pattern(
            ModeSwitchPattern.LATENT_BASIS,
        )
        self.assertEqual(len(thresh) + len(latent), len(MODE_SWITCH_REGISTRY))
        self.assertEqual({m.name for m in thresh},
                         {"dmalka_k_plus", "edc_thermal"})
        self.assertEqual({m.name for m in latent}, {"vectorial_spin"})


# ---------------------------------------------------------------------------
# Pattern classifier
# ---------------------------------------------------------------------------

class TestClassifyPattern(unittest.TestCase):

    def test_hill_one_leverage_profile_classified_as_threshold(self):
        # The canonical Hill-1 leverage profile has a clear peak at
        # log(L/Kd) = 0.
        def hill_leverage(log_L_over_Kd):
            occ = 1.0 / (1.0 + 10 ** (-log_L_over_Kd))
            return math.log(10) * occ * (1 - occ)

        ops = [i / 5.0 for i in range(-30, 31)]  # 6 decades, 0.2 step
        self.assertEqual(
            classify_pattern(hill_leverage, ops),
            ModeSwitchPattern.THRESHOLD_CROSSING,
        )

    def test_flat_leverage_classified_as_latent(self):
        ops = [float(i) for i in range(-10, 11)]
        self.assertEqual(
            classify_pattern(lambda _x: 0.5, ops),
            ModeSwitchPattern.LATENT_BASIS,
        )

    def test_all_zero_leverage_classified_as_latent(self):
        ops = [float(i) for i in range(-5, 6)]
        self.assertEqual(
            classify_pattern(lambda _x: 0.0, ops),
            ModeSwitchPattern.LATENT_BASIS,
        )

    def test_too_few_points_rejected(self):
        with self.assertRaises(ValueError):
            classify_pattern(lambda _x: 0.5, [0.0, 1.0])


# ---------------------------------------------------------------------------
# LeverageProbe protocol
# ---------------------------------------------------------------------------

class TestLeverageProtocol(unittest.TestCase):

    def test_object_without_protocol_returns_none(self):
        self.assertIsNone(current_leverage_of(object()))

    def test_protocol_returns_value(self):
        class FixedLeverage:
            def current_leverage(self) -> float:
                return 0.42

        self.assertAlmostEqual(
            current_leverage_of(FixedLeverage()), 0.42,
        )

    def test_misbehaving_protocol_returns_none(self):
        class Broken:
            def current_leverage(self) -> float:
                raise RuntimeError("intentional")

        self.assertIsNone(current_leverage_of(Broken()))

    def test_non_numeric_return_returns_none(self):
        class Weird:
            def current_leverage(self):
                return "high"

        self.assertIsNone(current_leverage_of(Weird()))

    def test_protocol_is_runtime_checkable(self):
        class A:
            def current_leverage(self) -> float:
                return 0.5

        class B:
            pass

        self.assertIsInstance(A(), LeverageProbe)
        self.assertNotIsInstance(B(), LeverageProbe)


# ---------------------------------------------------------------------------
# Detector — leverage flow into the report
# ---------------------------------------------------------------------------

class TestDetectorLeverageFlow(unittest.TestCase):

    def _bpa_state(self, occupancy: float) -> EDCThermalCouplingState:
        bpa = EDCConfig(
            name="BPA", Kd_intrinsic_M=1e-7, log_P=3.3,
            enthalpy_partition_kJ_per_mol=20.0,
            receptor_target="estrogen",
        )
        thermal = ThermalContext(
            temperature_K=298.15, ambient_K=298.15,
        )
        Kd = apparent_Kd(bpa, thermal)
        # Solve: occ = L/(Kd + L) → L = occ*Kd/(1-occ).
        target_L = occupancy * Kd / (1.0 - occupancy)
        return EDCThermalCouplingState(
            edc=bpa, thermal=thermal,
            env_concentration_M=1e-15,  # dummy; tissue is set below
            tissue_concentration_M=target_L,
            k_in_per_s=1e-9, k_out_per_s=1.0,  # don't drift in 1 step
        )

    def test_high_leverage_at_half_occupancy_raises_flag(self):
        state = self._bpa_state(occupancy=0.5)
        # Single-step "simulation" so the diagnostic exists.
        result = simulate(state, t_total_seconds=1.0, dt_seconds=1.0)
        report = detect_hidden_channels(result, claimed_channel="concentration")
        self.assertTrue(report.is_high_leverage)
        self.assertGreater(report.current_leverage, HIGH_LEVERAGE_THRESHOLD)
        # The flag should produce a *separate* note from the
        # structural finding.
        self.assertTrue(any("high-leverage" in n for n in report.notes))

    def test_low_leverage_in_saturation_does_not_raise_flag(self):
        state = self._bpa_state(occupancy=0.99)
        result = simulate(state, t_total_seconds=1.0, dt_seconds=1.0)
        report = detect_hidden_channels(result, claimed_channel="concentration")
        self.assertFalse(report.is_high_leverage)
        self.assertLess(report.current_leverage, HIGH_LEVERAGE_THRESHOLD)
        # Structural finding still surfaces — the hidden channel is
        # there even if leverage isn't high.
        self.assertFalse(report.scalar_sufficient)

    def test_object_without_leverage_protocol_reports_none(self):
        # An object that advertises shape channels but does NOT
        # implement LeverageProbe should still produce a valid
        # report — current_leverage = None, is_high_leverage = False.
        from bridges.hidden_channel_detector import (
            SHAPE_CHANNEL_REGISTRY,
        )

        class ChannelOnly:
            def shape_channels(self):
                return [SHAPE_CHANNEL_REGISTRY["polarization_linear"]]

        report = detect_hidden_channels(
            ChannelOnly(), claimed_channel="intensity",
        )
        self.assertIsNone(report.current_leverage)
        self.assertFalse(report.is_high_leverage)

    def test_high_leverage_without_shape_channel_still_flags(self):
        # A purely-scalar receiver in a high-leverage regime should
        # still get a warning. The structural finding says "scalar
        # is sufficient by basis count"; the leverage finding adds
        # "but you're amplifying — review anyway".
        class ScalarHighLev:
            def current_leverage(self) -> float:
                return 0.55

        report = detect_hidden_channels(
            ScalarHighLev(), claimed_channel="amplitude",
        )
        self.assertTrue(report.scalar_sufficient)  # no shape channel
        self.assertTrue(report.is_high_leverage)
        # Note explicitly mentions BUT to flag the tension.
        self.assertTrue(any("BUT" in n for n in report.notes))


# ---------------------------------------------------------------------------
# Polarization driver implements LeverageProbe
# ---------------------------------------------------------------------------

class TestPolarizationLeverage(unittest.TestCase):

    def test_polarization_driver_implements_protocol(self):
        from sensing.firmware.sensor_drivers import RotatingPolarizerDriver

        d = RotatingPolarizerDriver(mock=True, seed=42)
        self.assertIsInstance(d, LeverageProbe)
        # Before any read, leverage is 0.0 (cached).
        self.assertEqual(d.current_leverage(), 0.0)

    def test_polarization_leverage_tracks_dolp(self):
        from sensing.firmware.sensor_drivers import RotatingPolarizerDriver
        # Fully-polarised synthetic source — DoLP should be near 1.
        # We bypass the driver's diurnal mock by supplying our own
        # intensity_at_angle callable.
        s0, s1, s2 = 1.0, 1.0, 0.0  # fully polarised at θ₀ = 0°.
        def intensity_at(theta_rad: float) -> float:
            return 0.5 * (
                s0 + s1 * math.cos(2 * theta_rad)
                + s2 * math.sin(2 * theta_rad)
            )

        d = RotatingPolarizerDriver(
            intensity_at_angle=intensity_at, seed=1,
        )
        d.read()
        self.assertAlmostEqual(d.current_leverage(), 1.0, places=4)


if __name__ == "__main__":
    unittest.main()
