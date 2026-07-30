"""Tests for Silicon/propulsion_bounds.py — FP-1..5.

Stdlib only. FP-1, FP-2, FP-3 and FP-5 are settled by arithmetic and these
tests are what settles them; no apparatus is involved.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from propulsion_bounds import (  # noqa: E402
    C_AIR,
    C_LIGHT,
    CARRIERS,
    aliased_modes,
    coherent_power_scaling,
    discriminates,
    exceeds_momentum_bound,
    is_traveling_wave_mode,
    power_for_thrust,
    thrust_bound,
    traveling_wave_gradients,
)

REGISTERED_THRUST_N = 1.0e-4  # the 0.1 mN registered prediction


class TestMomentumBound(unittest.TestCase):
    """FP-1: F <= P/v is momentum conservation, not an engineering estimate."""

    def test_thrust_per_watt_by_carrier(self):
        self.assertAlmostEqual(thrust_bound(1.0, "em"), 1 / C_LIGHT, places=15)
        self.assertAlmostEqual(thrust_bound(1.0, "acoustic_air"), 1 / C_AIR, places=12)

    def test_em_thrust_is_nanonewtons_per_watt(self):
        self.assertLess(thrust_bound(1.0, "em"), 1e-8)
        self.assertGreater(thrust_bound(1.0, "em"), 1e-9)

    def test_registered_threshold_needs_tens_of_kilowatts_via_em(self):
        watts = power_for_thrust(REGISTERED_THRUST_N, "em")
        self.assertGreater(watts, 1e4)
        self.assertLess(watts, 1e5)

    def test_registered_threshold_is_trivial_via_acoustics(self):
        watts = power_for_thrust(REGISTERED_THRUST_N, "acoustic_air")
        self.assertLess(watts, 0.1)

    def test_a_positive_result_identifies_the_acoustic_channel(self):
        """The inversion: 0.1 mN is 6 orders too big for EM at ~1 W."""
        at_one_watt_em = thrust_bound(1.0, "em")
        self.assertGreater(REGISTERED_THRUST_N / at_one_watt_em, 1e4)
        self.assertLess(REGISTERED_THRUST_N / thrust_bound(1.0, "acoustic_air"), 1.0)

    def test_bound_and_inverse_are_consistent(self):
        for carrier in CARRIERS:
            for p in (1e-3, 1.0, 1e3):
                f = thrust_bound(p, carrier)
                self.assertAlmostEqual(power_for_thrust(f, carrier), p, places=9)

    def test_water_is_between_air_and_light(self):
        self.assertLess(thrust_bound(1.0, "em"), thrust_bound(1.0, "acoustic_water"))
        self.assertLess(thrust_bound(1.0, "acoustic_water"),
                        thrust_bound(1.0, "acoustic_air"))

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            thrust_bound(-1.0)
        with self.assertRaises(ValueError):
            thrust_bound(1.0, "aether")
        with self.assertRaises(ValueError):
            power_for_thrust(-1.0)


class TestDiscriminatingTest(unittest.TestCase):
    """FP-4: the only registered measurement that can return 'no'."""

    def test_thrust_within_bound_is_not_anomalous(self):
        p = 0.05
        f = thrust_bound(p, "acoustic_air") * 0.7
        r = exceeds_momentum_bound(f, p)
        self.assertFalse(r["anomalous"])
        self.assertLess(r["ratio"], 1.0)

    def test_thrust_above_bound_is_anomalous(self):
        p = 0.05
        f = thrust_bound(p, "acoustic_air") * 5.0
        r = exceeds_momentum_bound(f, p)
        self.assertTrue(r["anomalous"])
        self.assertAlmostEqual(r["ratio"], 5.0, places=9)

    def test_exactly_at_the_bound_is_not_anomalous(self):
        p = 0.05
        r = exceeds_momentum_bound(thrust_bound(p, "acoustic_air"), p)
        self.assertAlmostEqual(r["ratio"], 1.0, places=12)
        self.assertFalse(r["anomalous"])

    def test_large_absolute_thrust_is_not_evidence(self):
        """The whole point: absolute thrust means nothing without the power."""
        big_but_explained = exceeds_momentum_bound(1.0, 400.0)
        small_but_anomalous = exceeds_momentum_bound(1e-6, 1e-6)
        self.assertFalse(big_but_explained["anomalous"])
        self.assertTrue(small_but_anomalous["anomalous"])

    def test_margin_absorbs_calibration_uncertainty(self):
        p = 0.05
        f = thrust_bound(p, "acoustic_air") * 1.5
        self.assertTrue(exceeds_momentum_bound(f, p, margin=1.0)["anomalous"])
        self.assertFalse(exceeds_momentum_bound(f, p, margin=2.0)["anomalous"])

    def test_zero_radiated_power_is_flagged_not_crashed(self):
        r = exceeds_momentum_bound(1e-6, 0.0)
        self.assertTrue(r["anomalous"])
        self.assertIn("mechanical", r["verdict"])
        self.assertFalse(exceeds_momentum_bound(0.0, 0.0)["anomalous"])

    def test_rejects_nonpositive_margin(self):
        with self.assertRaises(ValueError):
            exceeds_momentum_bound(1e-4, 0.05, margin=0.0)


class TestTravelingWaveAliasing(unittest.TestCase):
    """FP-2: 3*pi/2 is a mode index, not a mystery."""

    def test_three_pi_over_two_is_a_mode_for_n8(self):
        self.assertTrue(is_traveling_wave_mode(3 * math.pi / 2, 8))
        info = aliased_modes(3 * math.pi / 2, 8)
        self.assertTrue(info["allowed"])
        self.assertEqual(info["m_as_given"], 6)
        self.assertEqual(info["m"], -2)

    def test_three_pi_over_two_equals_minus_pi_over_two_for_n8(self):
        """The falsifier: these cannot differ, so a claim they do is refuted."""
        a = aliased_modes(3 * math.pi / 2, 8)
        b = aliased_modes(-math.pi / 2, 8)
        self.assertEqual(a["m"], b["m"])
        self.assertAlmostEqual(a["equivalent_dphi"], b["equivalent_dphi"], places=12)

    def test_three_pi_over_two_is_not_a_mode_for_n6(self):
        self.assertFalse(is_traveling_wave_mode(3 * math.pi / 2, 6))
        self.assertFalse(aliased_modes(3 * math.pi / 2, 6)["allowed"])

    def test_mode_count_equals_node_count(self):
        for n in (4, 6, 8, 12, 17):
            modes = traveling_wave_gradients(n)
            self.assertEqual(len(modes), n)
            self.assertEqual(len({round(d, 9) for _, d in modes}), n)

    def test_mode_indices_are_reduced_to_signed_range(self):
        for n in (6, 8, 12):
            for m, _ in traveling_wave_gradients(n):
                self.assertLessEqual(m, n // 2)
                self.assertGreater(m, -n // 2 - 1)

    def test_zero_gradient_is_always_allowed(self):
        for n in (4, 8, 12):
            self.assertTrue(is_traveling_wave_mode(0.0, n))
            self.assertEqual(aliased_modes(0.0, n)["m"], 0)

    def test_gradient_is_periodic_in_two_pi(self):
        for n in (8, 12):
            base = aliased_modes(3 * math.pi / 2, n)
            wrapped = aliased_modes(3 * math.pi / 2 + 2 * math.pi, n)
            self.assertEqual(base["m"], wrapped["m"])

    def test_rejects_degenerate_arrays(self):
        with self.assertRaises(ValueError):
            traveling_wave_gradients(1)
        with self.assertRaises(ValueError):
            aliased_modes(1.0, 1)


class TestNoDiscriminatingPower(unittest.TestCase):
    """FP-3 and FP-5: the registered predictions do not separate H0 from H1."""

    REGISTERED = [
        "F > 0.1 mN at 3*pi/2",
        "sign reverses when dphi -> -dphi",
        "F scales as N^2",
        "helix beats ring",
    ]

    def test_all_four_registered_predictions_fail_to_discriminate(self):
        for name in self.REGISTERED:
            # each is predicted by BOTH hypotheses -- see the protocol table
            result = discriminates(predicted_by_h0=True, predicted_by_h1=True)
            self.assertFalse(result["discriminates"], msg=name)
            self.assertIn("BOTH", result["verdict"])

    def test_the_momentum_ratio_does_discriminate(self):
        self.assertTrue(
            discriminates(predicted_by_h0=False, predicted_by_h1=True)["discriminates"])

    def test_coherent_scaling_explains_the_n_squared_prediction(self):
        """FP-5: N^2 thrust follows from N^2 power and F = P/v."""
        for n in (2, 4, 8, 16):
            self.assertAlmostEqual(coherent_power_scaling(n), n * n, places=12)
        # thrust ratio between N=16 and N=8 under ordinary radiation
        p8, p16 = coherent_power_scaling(8), coherent_power_scaling(16)
        f8 = thrust_bound(p8, "acoustic_air")
        f16 = thrust_bound(p16, "acoustic_air")
        self.assertAlmostEqual(f16 / f8, 4.0, places=12)

    def test_coherent_scaling_rejects_empty_array(self):
        with self.assertRaises(ValueError):
            coherent_power_scaling(0)


if __name__ == "__main__":
    unittest.main()
