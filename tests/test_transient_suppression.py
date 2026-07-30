"""Tests for Silicon/transient_suppression.py -- R2-1..8.

Stdlib only. Everything here is arithmetic; these tests are what settle it.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from transient_suppression import (  # noqa: E402
    COIL_FIELD_T,
    GAMMA_HZ_PER_T,
    N_SI,
    PROBES,
    PULSE_S,
    area_stability_for_infidelity,
    cmrr,
    coil_size_for_rejection,
    combine_mismatch,
    field_for_pi_pulse,
    from_db,
    infidelity_from_area_error,
    matching_for_rejection,
    path_length_for_skew,
    probe_shortfall,
    pulse_bandwidth,
    rejection_from_mismatch,
    rotation_angle,
    selectivity,
    skew_for_rejection,
    skew_rejection_at,
    to_db,
    write_pulse_authority,
    zeeman_hz,
)


class TestR2_8WritePulseAuthority(unittest.TestCase):
    """The finding that inverts the document's premise."""

    def test_write_pulse_rotates_the_spin_by_milliradians(self):
        w = write_pulse_authority()
        self.assertAlmostEqual(w["theta_mrad"], 4.42, delta=0.05)
        self.assertLess(w["fraction_of_pi"], 0.002)

    def test_a_five_ps_pi_pulse_needs_several_tesla(self):
        self.assertAlmostEqual(field_for_pi_pulse(PULSE_S), 3.57, delta=0.02)

    def test_the_coil_is_about_700x_short_of_a_pi_pulse(self):
        w = write_pulse_authority()
        self.assertGreater(w["field_shortfall"], 600.0)
        self.assertLess(w["field_shortfall"], 800.0)

    def test_therefore_there_is_no_coherence_to_collapse(self):
        """0.14% of pi cannot destroy a state. The stated worry is inverted."""
        self.assertLess(write_pulse_authority()["percent_of_pi"], 1.0)

    def test_pulse_area_is_what_is_conserved(self):
        """B*t is the invariant: 0.1 T for 178 ps == 3.57 T for 5 ps."""
        a = 0.1 * 178e-12
        b = field_for_pi_pulse(PULSE_S) * PULSE_S
        self.assertAlmostEqual(a / b, 1.0, delta=0.01)

    def test_rotation_is_linear_in_field_and_time(self):
        self.assertAlmostEqual(rotation_angle(2e-3, 1e-12) * 2,
                               rotation_angle(4e-3, 1e-12), places=15)
        self.assertAlmostEqual(rotation_angle(2e-3, 1e-12) * 3,
                               rotation_angle(2e-3, 3e-12), places=15)

    def test_gyromagnetic_ratio(self):
        self.assertAlmostEqual(GAMMA_HZ_PER_T / 1e9, 28.0, delta=0.1)

    def test_rejects_bad_duration(self):
        with self.assertRaises(ValueError):
            field_for_pi_pulse(0.0)
        with self.assertRaises(ValueError):
            rotation_angle(1e-3, -1.0)


class TestR2_3Mismatch(unittest.TestCase):
    """Falsifier: 60 dB measured at sub-um matching."""

    def test_rejection_is_the_reciprocal_of_mismatch(self):
        self.assertAlmostEqual(rejection_from_mismatch(1e-3), 1000.0, places=9)
        self.assertAlmostEqual(rejection_from_mismatch(1e-2), 100.0, places=9)

    def test_sixty_db_needs_one_part_in_a_thousand(self):
        self.assertAlmostEqual(to_db(rejection_from_mismatch(1e-3)), 60.0,
                               places=9)

    def test_hundred_nm_on_a_ten_micron_coil_gives_forty_db(self):
        d = 100e-9 / 10e-6
        self.assertAlmostEqual(to_db(rejection_from_mismatch(d)), 40.0, places=9)

    def test_one_micron_on_a_ten_micron_coil_gives_only_twenty_db(self):
        """'sub-um' read literally. The shortfall is 20-40 dB, not 20."""
        d = 1e-6 / 10e-6
        self.assertAlmostEqual(to_db(rejection_from_mismatch(d)), 20.0, places=9)

    def test_sixty_db_at_ten_microns_needs_ten_nm_matching(self):
        self.assertAlmostEqual(matching_for_rejection(1e3, 10e-6) * 1e9, 10.0,
                               places=6)

    def test_sixty_db_at_hundred_nm_needs_a_hundred_micron_coil(self):
        self.assertAlmostEqual(coil_size_for_rejection(1e3, 100e-9) * 1e6,
                               100.0, places=6)

    def test_growing_the_coil_is_the_trap(self):
        """10x the dimension relaxes tolerance 10x but costs field per amp."""
        self.assertAlmostEqual(
            coil_size_for_rejection(1e3, 100e-9)
            / coil_size_for_rejection(1e3, 10e-9), 10.0, places=9)

    def test_channels_add_in_quadrature(self):
        self.assertAlmostEqual(combine_mismatch(1e-2, 1e-2), math.sqrt(2) * 1e-2,
                               places=12)

    def test_two_channels_at_one_percent_give_37_db_not_40(self):
        d = combine_mismatch(1e-2, 1e-2)
        self.assertAlmostEqual(to_db(1 / d), 37.0, delta=0.1)

    def test_one_good_channel_does_not_rescue_a_bad_one(self):
        d = combine_mismatch(1e-3, 1e-2)
        self.assertAlmostEqual(to_db(1 / d), 40.0, delta=0.1)

    def test_db_conversions_are_amplitude_not_power(self):
        self.assertAlmostEqual(to_db(1000.0), 60.0, places=9)
        self.assertAlmostEqual(from_db(60.0), 1000.0, places=6)
        self.assertAlmostEqual(from_db(to_db(37.3)), 37.3, places=9)

    def test_rejects_bad_inputs(self):
        for bad in (0.0, -1e-3):
            with self.assertRaises(ValueError):
                rejection_from_mismatch(bad)
        with self.assertRaises(ValueError):
            to_db(0.0)
        with self.assertRaises(ValueError):
            combine_mismatch()


class TestR2_4Timing(unittest.TestCase):
    """Falsifier: 60 dB with >5 fs skew."""

    def test_time_domain_criterion_matches_the_audits_five_fs(self):
        tau = skew_for_rejection(1e3, criterion="time_domain")
        self.assertAlmostEqual(tau * 1e15, 3.57, delta=0.05)

    def test_spectral_criterion_is_about_six_times_tighter(self):
        td = skew_for_rejection(1e3, criterion="time_domain")
        sp = skew_for_rejection(1e3, criterion="spectral")
        self.assertLess(sp, td)
        self.assertAlmostEqual(td / sp, 2 * math.pi / 1.4, delta=0.05)
        self.assertAlmostEqual(sp * 1e15, 0.80, delta=0.02)

    def test_on_chip_path_length_for_the_time_domain_figure(self):
        tau = skew_for_rejection(1e3, criterion="time_domain")
        self.assertAlmostEqual(path_length_for_skew(tau) * 1e6, 0.306,
                               delta=0.005)

    def test_five_fs_is_about_half_a_micron_on_chip(self):
        self.assertAlmostEqual(path_length_for_skew(5e-15) * 1e6, 0.428,
                               delta=0.005)

    def test_index_slows_the_wave(self):
        self.assertAlmostEqual(path_length_for_skew(5e-15, index=1.0)
                               / path_length_for_skew(5e-15, index=N_SI),
                               N_SI, places=9)

    def test_rejection_degrades_with_frequency(self):
        prev = float("inf")
        for f in (1e9, 1e10, 1e11, 2e11):
            r = to_db(skew_rejection_at(f, 5e-15))
            self.assertLess(r, prev)
            prev = r

    def test_five_fs_skew_gives_90_db_at_1_ghz_but_44_at_200(self):
        """Why a single R_2 number is underspecified."""
        self.assertAlmostEqual(to_db(skew_rejection_at(1e9, 5e-15)), 90.1,
                               delta=0.2)
        self.assertAlmostEqual(to_db(skew_rejection_at(2e11, 5e-15)), 44.0,
                               delta=0.3)

    def test_a_low_frequency_cmrr_measurement_flatters_by_46_db(self):
        gain = (to_db(skew_rejection_at(1e9, 5e-15))
                - to_db(skew_rejection_at(2e11, 5e-15)))
        self.assertGreater(gain, 40.0)

    def test_zero_skew_is_infinite_rejection(self):
        self.assertEqual(skew_rejection_at(1e11, 0.0), float("inf"))

    def test_rejects_bad_criterion_and_inputs(self):
        with self.assertRaises(ValueError):
            skew_for_rejection(1e3, criterion="vibes")
        with self.assertRaises(ValueError):
            skew_rejection_at(0.0, 1e-15)
        with self.assertRaises(ValueError):
            path_length_for_skew(-1e-15)


class TestR2_5Selectivity(unittest.TestCase):
    """Falsifier: selective transition driving with a 5 ps pulse."""

    def test_inverse_convention_gives_two_hundred_ghz(self):
        self.assertAlmostEqual(pulse_bandwidth() / 1e9, 200.0, places=6)

    def test_gaussian_transform_limit_is_lower(self):
        self.assertAlmostEqual(pulse_bandwidth(convention="gaussian") / 1e9,
                               88.2, delta=0.1)
        self.assertLess(pulse_bandwidth(convention="sech2"),
                        pulse_bandwidth(convention="gaussian"))

    def test_zeeman_splitting_at_one_and_two_tesla(self):
        self.assertAlmostEqual(zeeman_hz(1.0) / 1e9, 28.0, delta=0.1)
        self.assertAlmostEqual(zeeman_hz(2.0) / 1e9, 56.0, delta=0.2)

    def test_not_selective_in_any_convention(self):
        for conv in ("inverse", "gaussian", "sech2"):
            for b in (1.0, 2.0):
                self.assertFalse(selectivity(b, convention=conv)["selective"],
                                 msg=f"{conv} at {b} T")

    def test_the_four_to_seven_x_figure_is_the_inverse_convention(self):
        self.assertAlmostEqual(selectivity(1.0)["ratio"], 7.14, delta=0.05)
        self.assertAlmostEqual(selectivity(2.0)["ratio"], 3.57, delta=0.05)

    def test_gaussian_convention_gives_a_smaller_but_still_failing_ratio(self):
        r1 = selectivity(1.0, convention="gaussian")["ratio"]
        r2 = selectivity(2.0, convention="gaussian")["ratio"]
        self.assertAlmostEqual(r1, 3.15, delta=0.05)
        self.assertAlmostEqual(r2, 1.58, delta=0.05)
        self.assertGreater(r2, 1.0)

    def test_selectivity_would_need_a_much_longer_pulse(self):
        """At 2 T, 1/dt < 56 GHz needs dt > 17.9 ps."""
        self.assertTrue(selectivity(2.0, pulse_s=200e-12)["selective"])
        self.assertFalse(selectivity(2.0, pulse_s=10e-12)["selective"])

    def test_thz_band_is_orders_above_esr(self):
        self.assertGreater(1e12 / zeeman_hz(2.0), 15.0)
        self.assertGreater(1e13 / zeeman_hz(1.0), 300.0)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            pulse_bandwidth(convention="magic")
        with self.assertRaises(ValueError):
            pulse_bandwidth(0.0)
        with self.assertRaises(ValueError):
            selectivity(0.0)


class TestAreaStability(unittest.TestCase):
    """The well-posed criterion, with the audit's factor of pi corrected."""

    def test_infidelity_1e4_needs_two_percent_in_radians(self):
        a = area_stability_for_infidelity(1e-4)
        self.assertAlmostEqual(a["dtheta_rad"], 0.02, places=6)

    def test_but_the_fractional_area_stability_is_0_64_percent(self):
        """0.02 rad on a pi rotation is 0.64%, not 2%."""
        a = area_stability_for_infidelity(1e-4)
        self.assertAlmostEqual(a["percent"], 0.637, delta=0.005)

    def test_two_percent_corresponds_to_infidelity_1e3(self):
        """The audit's number is the right answer to a different question."""
        a = area_stability_for_infidelity(1e-3)
        self.assertAlmostEqual(a["percent"], 2.013, delta=0.01)

    def test_round_trip_area_error_to_infidelity(self):
        for inf in (1e-3, 1e-4, 1e-5):
            frac = area_stability_for_infidelity(inf)["fractional"]
            self.assertAlmostEqual(infidelity_from_area_error(frac), inf,
                                   places=12)

    def test_infidelity_is_quadratic_in_area_error(self):
        a = infidelity_from_area_error(0.01)
        b = infidelity_from_area_error(0.02)
        self.assertAlmostEqual(b / a, 4.0, places=9)

    def test_tighter_infidelity_needs_tighter_area(self):
        self.assertLess(area_stability_for_infidelity(1e-5)["percent"],
                        area_stability_for_infidelity(1e-4)["percent"])

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            area_stability_for_infidelity(0.0)
        with self.assertRaises(ValueError):
            infidelity_from_area_error(-0.1)


class TestR2_6Probes(unittest.TestCase):
    """Falsifier: a >1 GHz OPM."""

    def test_opm_is_eight_orders_short(self):
        self.assertAlmostEqual(math.log10(2e11 / PROBES["opm_typical"]), 8.3,
                               delta=0.05)
        self.assertGreater(math.log10(2e11 / PROBES["opm_best"]), 7.0)

    def test_no_electronic_probe_reaches_200_ghz(self):
        for name in ("opm_typical", "opm_best", "sampling_scope",
                     "realtime_scope_fastest"):
            self.assertLess(PROBES[name], 2e11, msg=name)

    def test_magneto_optic_sampling_does(self):
        self.assertGreater(PROBES["mo_sampling_100fs"], 2e11)

    def test_shortfall_table_is_sorted_and_flags_adequacy(self):
        rows = probe_shortfall(2e11)
        self.assertEqual([r[0] for r in rows][0], "opm_typical")
        self.assertTrue(all(rows[i][1] <= rows[i + 1][1]
                            for i in range(len(rows) - 1)))
        self.assertEqual([r[3] for r in rows].count(True), 1)

    def test_pickup_loop_geometry_is_not_the_binding_constraint(self):
        """lambda/10 at 200 GHz is 150 um -- buildable. The digitizer is not."""
        lam = 2.99792458e8 / 2e11
        self.assertAlmostEqual(lam / 10 * 1e6, 150.0, delta=1.0)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            probe_shortfall(0.0)


class TestR2_2Cmrr(unittest.TestCase):
    """Falsifier: a measurement of B_CM,input on the cancelling structure."""

    def test_cmrr_is_dm_over_cm_so_bigger_is_better(self):
        good = cmrr(dm_response=1.0, cm_response=1e-3)
        poor = cmrr(dm_response=1.0, cm_response=1e-1)
        self.assertGreater(good["cmrr"], poor["cmrr"])
        self.assertAlmostEqual(good["db"], 60.0, places=6)
        self.assertAlmostEqual(poor["db"], 20.0, places=6)

    def test_the_inverted_definition_would_shrink_as_it_improves(self):
        """CM/DM tends to zero for a good structure -- the wrong direction."""
        self.assertLess(1e-3 / 1.0, 1e-1 / 1.0)

    def test_both_terms_are_measured_quantities(self):
        r = cmrr(dm_response=2.5e-6, cm_response=2.5e-9)
        self.assertEqual(r["dm"], 2.5e-6)
        self.assertEqual(r["cm"], 2.5e-9)
        self.assertAlmostEqual(r["db"], 60.0, places=6)

    def test_a_zero_common_mode_reading_is_refused_not_reported_as_infinite(self):
        with self.assertRaises(ValueError) as ctx:
            cmrr(1.0, 0.0)
        self.assertIn("probe", str(ctx.exception))

    def test_rejects_nonpositive_differential(self):
        with self.assertRaises(ValueError):
            cmrr(0.0, 1e-3)


class TestConstants(unittest.TestCase):

    def test_coil_field_matches_the_magnetic_authority_result(self):
        self.assertAlmostEqual(COIL_FIELD_T * 1e3, 5.03, places=2)

    def test_pulse_is_five_picoseconds(self):
        self.assertAlmostEqual(PULSE_S * 1e12, 5.0, places=9)


if __name__ == "__main__":
    unittest.main()
