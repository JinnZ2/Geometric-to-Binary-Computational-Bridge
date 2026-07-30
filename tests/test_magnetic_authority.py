"""Tests for Silicon/magnetic_authority.py -- FAB-1..7, BRG-1..7.

Stdlib only. Every claim here is arithmetic, and these tests are what settle
them; no apparatus is involved. Where a test asserts an order-of-magnitude gap
it also asserts the SIGN of the gap, because a shortfall that came out as a
surplus would be the interesting result.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from magnetic_authority import (  # noqa: E402
    CHI_SI,
    GYRO_HZ_PER_T,
    MUB_EV,
    PI_11,
    PI_L_110,
    QE,
    XI_U_EV,
    arrhenius_lifetime,
    authority_ratio,
    barrier_authority,
    cell_moment,
    coil_field,
    curie_susceptibility,
    current_density,
    dipole_field,
    eddy_diffusion_time,
    electromigration_life,
    er_vs_host,
    flux_concentrator_gain,
    gradient_addressing,
    landauer_ev,
    piezoresistive_response,
    rabi_time,
    readout_shortfall,
    retention_barrier_ev,
    rf_power_for_b1,
    stored_energy,
    switching_power,
    valley_splitting_ev,
    zeeman_ev,
)

CELL_V = 5e-6 * 5e-6 * 100e-9          # the documented 5um x 5um x 100nm cell


class TestFab1ReadoutGap(unittest.TestCase):
    """The whole $15-50k proof-of-concept rests on this signal existing."""

    def test_cell_moment_is_sub_femto(self):
        m = cell_moment(CELL_V, 0.050)
        self.assertLess(abs(m), 1e-18)
        self.assertAlmostEqual(abs(m), 3.98e-19, delta=2e-20)

    def test_moment_is_diamagnetic_ie_negative(self):
        """Sign matters: the induced moment OPPOSES the applied field."""
        self.assertLess(cell_moment(CELL_V, 0.050), 0.0)
        self.assertLess(CHI_SI, 0.0)

    def test_field_at_one_mm_is_sub_femtotesla(self):
        b = dipole_field(cell_moment(CELL_V, 0.050), 1e-3)
        self.assertLess(b, 1e-15)
        self.assertAlmostEqual(b, 7.96e-17, delta=5e-18)

    def test_hall_shortfall_is_about_twelve_orders(self):
        r = readout_shortfall(cell_moment(CELL_V, 0.050))
        self.assertGreater(r["hall_orders"], 11.0)
        self.assertLess(r["hall_orders"], 12.0)
        self.assertLess(r["hall_snr"], 1e-11)

    def test_squid_does_not_rescue_it(self):
        r = readout_shortfall(cell_moment(CELL_V, 0.050))
        self.assertGreater(r["squid_orders"], 7.0)
        self.assertLess(r["squid_orders"], 8.0)

    def test_no_benchtop_field_closes_the_gap(self):
        """Linear in B, so even 10 T leaves ~9 orders. Not a field problem."""
        r = readout_shortfall(cell_moment(CELL_V, 10.0))
        self.assertGreater(r["hall_orders"], 8.0)

    def test_dipole_field_falls_as_r_cubed(self):
        m = 1e-18
        self.assertAlmostEqual(dipole_field(m, 1e-3) / dipole_field(m, 2e-3),
                               8.0, places=9)

    def test_rejects_bad_geometry(self):
        with self.assertRaises(ValueError):
            cell_moment(0.0, 0.05)
        with self.assertRaises(ValueError):
            dipole_field(1e-18, 0.0)


class TestFab2Erbium(unittest.TestCase):
    """The one genuinely paramagnetic dopant, and it still loses 500x."""

    def test_curie_susceptibility_at_the_stated_dose(self):
        chi = curie_susceptibility(1e22, 9.6, 300.0)
        self.assertAlmostEqual(chi, 8.0e-9, delta=3e-10)

    def test_host_diamagnetism_dominates_by_about_500x(self):
        r = er_vs_host()
        self.assertGreater(r["host_larger_by"], 400.0)
        self.assertLess(r["host_larger_by"], 600.0)

    def test_the_signal_has_the_opposite_sign_to_the_host(self):
        r = er_vs_host()
        self.assertGreater(r["chi_er"], 0.0)
        self.assertLess(r["chi_host"], 0.0)

    def test_the_dose_that_would_win_exceeds_solubility(self):
        r = er_vs_host()
        self.assertTrue(r["n_exceeds_solubility"])
        self.assertGreater(r["n_needed_per_cm3"], 1e18)

    def test_the_temperature_that_would_win_is_cryogenic(self):
        self.assertLess(er_vs_host()["temp_needed_k"], 4.2)

    def test_curie_scales_inversely_with_temperature(self):
        hot = curie_susceptibility(1e22, 9.6, 300.0)
        cold = curie_susceptibility(1e22, 9.6, 3.0)
        self.assertAlmostEqual(cold / hot, 100.0, places=6)

    def test_rejects_zero_temperature(self):
        with self.assertRaises(ValueError):
            curie_susceptibility(1e22, 9.6, 0.0)


class TestWriteAuthority(unittest.TestCase):
    """FAB-7 and BRG-1: nothing magnetic moves the barrier."""

    def test_two_tesla_gives_a_quarter_meV(self):
        self.assertAlmostEqual(zeeman_ev(2.0) * 1e3, 0.2315, places=3)

    def test_two_tesla_is_at_most_a_few_percent_of_the_barrier(self):
        self.assertLess(barrier_authority(2.0, 0.010)["percent"], 3.0)
        self.assertLess(barrier_authority(2.0, 0.100)["percent"], 0.3)

    def test_coil_at_the_electromigration_limit_gives_millitesla(self):
        i_max = 1e10 * (100e-9 * 200e-9)
        b = coil_field(10, i_max, 250e-9)
        self.assertAlmostEqual(b * 1e3, 5.03, delta=0.05)
        self.assertGreater(1.0 / b, 150.0)          # ~200x short of 1 T

    def test_that_coil_has_essentially_no_barrier_authority(self):
        i_max = 1e10 * (100e-9 * 200e-9)
        b = coil_field(10, i_max, 250e-9)
        self.assertLess(barrier_authority(b, 0.100)["percent"], 0.01)

    def test_the_two_documents_disagree_and_this_quantifies_it(self):
        """Fabrication.md runs 10 mA; Magnetic-bridge.md states 1e6 A/cm^2."""
        j_fab = current_density(10e-3, 50e-9 * 200e-9) / 1e4
        self.assertAlmostEqual(j_fab, 1e8, delta=1e6)
        self.assertAlmostEqual(j_fab / 1e6, 100.0, delta=1.0)

    def test_black_equation_turns_ten_years_into_hours(self):
        life = electromigration_life(1e8)
        self.assertLess(life["hours"], 12.0)
        self.assertGreater(life["hours"], 6.0)
        self.assertLess(life["days_at_1pct_duty"], 60.0)

    def test_at_the_limit_the_rated_life_is_recovered(self):
        self.assertAlmostEqual(electromigration_life(1e6)["years"], 10.0,
                               places=9)

    def test_flux_concentrator_gain_is_bounded_by_area_ratio(self):
        r = flux_concentrator_gain(1e-6, 1e-8, mu_r=5000.0, b_in_t=0.0)
        self.assertAlmostEqual(r["gain"], 100.0, places=9)
        self.assertAlmostEqual(r["claimed_if_mu_r_multiplied"], 5e5, places=0)

    def test_concentrator_saturates_before_the_claimed_field(self):
        r = flux_concentrator_gain(1e-6, 1e-8, b_in_t=0.050, b_sat_t=1.0)
        self.assertTrue(r["saturated"])
        self.assertGreater(r["b_out_t"], r["b_sat_t"])

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            barrier_authority(1.0, 0.0)
        with self.assertRaises(ValueError):
            coil_field(10, 1e-3, 0.0)
        with self.assertRaises(ValueError):
            current_density(1.0, 0.0)


class TestEnergyArithmetic(unittest.TestCase):

    def test_the_aJ_conversion_was_off_by_a_thousand(self):
        self.assertAlmostEqual(0.01 * QE * 1e18, 0.0016, places=4)
        self.assertAlmostEqual(1.6e-18 / QE, 10.0, delta=0.05)

    def test_the_stated_write_energy_is_below_landauer(self):
        self.assertAlmostEqual(landauer_ev(300.0), 0.0179, places=4)
        self.assertLess(0.01, landauer_ev(300.0))

    def test_landauer_scales_linearly_with_temperature(self):
        self.assertAlmostEqual(landauer_ev(600.0) / landauer_ev(300.0), 2.0,
                               places=9)

    def test_ten_year_retention_at_85C_needs_1_5_eV(self):
        self.assertAlmostEqual(retention_barrier_ev(10.0, 358.15), 1.53,
                               delta=0.02)

    def test_the_stated_barriers_give_picosecond_retention(self):
        for ea in (0.01, 0.1):
            self.assertLess(arrhenius_lifetime(ea, 358.15), 1e-11)

    def test_the_qual_spec_and_the_physics_spec_differ_by_twenty_orders(self):
        ten_years = 10 * 365.25 * 24 * 3600
        actual = arrhenius_lifetime(0.1, 358.15)
        self.assertGreater(math.log10(ten_years / actual), 19.0)

    def test_retention_and_lifetime_are_inverses(self):
        ea = retention_barrier_ev(10.0, 358.15)
        self.assertAlmostEqual(arrhenius_lifetime(ea, 358.15),
                               10 * 365.25 * 24 * 3600, delta=1e3)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            landauer_ev(0.0)
        with self.assertRaises(ValueError):
            retention_barrier_ev(0.0, 300.0)


class TestTimingAndEnergy(unittest.TestCase):
    """BRG-2 and BRG-7."""

    def test_eddy_decay_at_package_scale_is_microseconds(self):
        self.assertGreater(eddy_diffusion_time(1e-3), 1e-6)
        self.assertLess(eddy_diffusion_time(1e-3), 1e-5)

    def test_five_nanoseconds_is_three_orders_optimistic(self):
        self.assertGreater(math.log10(eddy_diffusion_time(1e-3) / 5e-9), 3.0)

    def test_eddy_time_scales_as_length_squared(self):
        self.assertAlmostEqual(
            eddy_diffusion_time(1e-3) / eddy_diffusion_time(1e-4), 100.0,
            places=6)

    def test_read_floor_is_four_ramps_not_one(self):
        """The read protocol budgets 50 ns for four 100 ns rotations."""
        self.assertAlmostEqual(4 * 100e-9, 400e-9, places=12)
        self.assertGreater(400e-9 / 50e-9, 7.0)

    def test_two_tesla_over_a_cubic_cm_stores_1_6_joules(self):
        self.assertAlmostEqual(stored_energy(2.0, 1e-6), 1.59, delta=0.02)

    def test_switching_that_in_100ns_needs_megawatts(self):
        self.assertGreater(switching_power(2.0, 1e-6, 100e-9), 1e7)

    def test_stability_and_slew_specs_are_incompatible_in_magnitude(self):
        """dB/B < 1e-5 at 2 T is 20 uT, while the slew is 2e7 T/s."""
        self.assertAlmostEqual(2.0 * 1e-5, 20e-6, places=12)
        self.assertAlmostEqual(2.0 / 100e-9, 2e7, places=0)

    def test_energy_scales_as_b_squared(self):
        self.assertAlmostEqual(stored_energy(4.0, 1e-6) / stored_energy(2.0, 1e-6),
                               4.0, places=9)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            eddy_diffusion_time(0.0)
        with self.assertRaises(ValueError):
            switching_power(1.0, 1e-6, 0.0)


class TestGradientAddressing(unittest.TestCase):
    """BRG-5, with the audit's own factor-of-1000 corrected."""

    def test_gyromagnetic_ratio_is_28_GHz_per_tesla(self):
        self.assertAlmostEqual(GYRO_HZ_PER_T / 1e9, 28.0, delta=0.1)

    def test_offset_is_megahertz_not_kilohertz(self):
        """The audited figure was 1.4 kHz. It is 1.4 MHz."""
        g = gradient_addressing(1000.0, 50e-9)
        self.assertAlmostEqual(g["offset_hz"] / 1e6, 1.40, delta=0.02)
        self.assertGreater(g["offset_hz"], 1e6)

    def test_shortfall_is_hundreds_not_hundreds_of_thousands(self):
        g = gradient_addressing(1000.0, 50e-9)
        self.assertGreater(g["shortfall"], 500.0)
        self.assertLess(g["shortfall"], 1000.0)
        self.assertFalse(g["resolvable"])

    def test_required_gradient_is_near_mfm_tip_state_of_the_art(self):
        """7e5 T/m, not 7e8: comparable to ~1e6 T/m tip records."""
        g = gradient_addressing(1000.0, 50e-9)
        self.assertAlmostEqual(g["gradient_needed_t_per_m"] / 1e5, 7.14,
                               delta=0.1)
        self.assertLess(g["gradient_needed_t_per_m"], 1e6)

    def test_the_specified_range_is_still_short(self):
        """BRG-5 survives the correction; it just survives by 714x, not 7e5x."""
        for gradient in (10.0, 100.0, 1000.0):
            self.assertFalse(gradient_addressing(gradient, 50e-9)["resolvable"])

    def test_offset_is_linear_in_gradient_and_pitch(self):
        a = gradient_addressing(1000.0, 50e-9)["offset_hz"]
        b = gradient_addressing(2000.0, 50e-9)["offset_hz"]
        c = gradient_addressing(1000.0, 100e-9)["offset_hz"]
        self.assertAlmostEqual(b / a, 2.0, places=9)
        self.assertAlmostEqual(c / a, 2.0, places=9)

    def test_rejects_bad_geometry(self):
        with self.assertRaises(ValueError):
            gradient_addressing(1000.0, 0.0)


class TestDrive(unittest.TestCase):
    """BRG-4."""

    def test_rabi_time_is_hundreds_of_picoseconds(self):
        self.assertAlmostEqual(rabi_time(0.1) * 1e12, 179.0, delta=2.0)

    def test_the_documented_value_was_off_by_330x(self):
        self.assertAlmostEqual(rabi_time(0.1) / 0.54e-12, 331.0, delta=5.0)

    def test_composite_sequence_is_over_half_a_nanosecond(self):
        self.assertGreater(3 * rabi_time(0.1), 500e-12)

    def test_rabi_time_scales_inversely_with_b1(self):
        self.assertAlmostEqual(rabi_time(0.05) / rabi_time(0.1), 2.0, places=9)

    def test_power_for_a_tenth_tesla_b1_is_hundreds_of_kilowatts(self):
        p = rf_power_for_b1(0.1)
        self.assertGreater(p["power_w"], 1e5)
        self.assertLess(p["power_w"], 1e7)

    def test_that_is_about_five_orders_over_the_budget(self):
        p = rf_power_for_b1(0.1)
        self.assertGreater(math.log10(p["power_w"] / 10.0), 4.0)

    def test_esr_calibration_agrees_within_an_order(self):
        """Empirical cross-check: 1 kW gives ~1 mT, and B1 ~ sqrt(P)."""
        p = rf_power_for_b1(0.1)
        self.assertAlmostEqual(p["esr_calibrated_w"], 1e7, delta=1e6)
        self.assertLess(abs(math.log10(p["esr_calibrated_w"] / p["power_w"])), 1.5)

    def test_power_scales_as_b1_squared(self):
        a = rf_power_for_b1(0.1)["power_w"]
        b = rf_power_for_b1(0.2)["power_w"]
        self.assertAlmostEqual(b / a, 4.0, places=6)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            rabi_time(0.0)
        with self.assertRaises(ValueError):
            rf_power_for_b1(0.1, q=0.0)


class TestStrainChannel(unittest.TestCase):
    """BRG-6: the replacement, and the coefficient the audit mislabelled."""

    def test_pi_l_110_is_twelve_times_pi_11(self):
        """6e-11 is the <100> coefficient; <110> longitudinal is 7.18e-10."""
        self.assertAlmostEqual(PI_L_110 / 1e-10, 7.18, delta=0.02)
        self.assertGreater(PI_L_110 / PI_11, 10.0)

    def test_gauge_factor_matches_the_audits_own_figure(self):
        """GF ~ 100 requires the <110> coefficient, not pi_11."""
        gf = piezoresistive_response(0.001)["gauge_factor"]
        self.assertAlmostEqual(gf, 93.0, delta=3.0)
        self.assertLess(piezoresistive_response(0.001, pi_l=6e-11)["gauge_factor"],
                        10.0)

    def test_response_at_a_realistic_strain(self):
        r = piezoresistive_response(0.001)
        self.assertAlmostEqual(r["percent"], 9.3, delta=0.5)
        self.assertFalse(r["fractures"])

    def test_one_percent_strain_is_flagged_as_fracture_range(self):
        r = piezoresistive_response(0.01)
        self.assertTrue(r["fractures"])
        self.assertGreater(r["percent"], 50.0)

    def test_response_is_linear_in_strain(self):
        a = piezoresistive_response(0.001)["dr_over_r"]
        b = piezoresistive_response(0.002)["dr_over_r"]
        self.assertAlmostEqual(b / a, 2.0, places=9)

    def test_valley_splitting_beats_two_tesla_by_orders(self):
        self.assertAlmostEqual(valley_splitting_ev(0.01) * 1e3, 91.6, delta=0.5)
        self.assertGreater(authority_ratio(0.01, 2.0), 300.0)
        self.assertGreater(authority_ratio(0.001, 2.0), 30.0)

    def test_strain_beats_the_legal_coil_by_four_orders(self):
        b_coil = coil_field(10, 1e10 * (100e-9 * 200e-9), 250e-9)
        self.assertGreater(authority_ratio(0.001, b_coil), 1e4)

    def test_piezoresistive_signal_dwarfs_the_magnetic_readout(self):
        """8 orders: a percent-level resistance change against 1e-12 SNR."""
        r = readout_shortfall(cell_moment(CELL_V, 0.050))
        self.assertGreater(piezoresistive_response(0.001)["dr_over_r"], 0.01)
        self.assertLess(r["hall_snr"], 1e-11)

    def test_deformation_potential_is_the_documented_value(self):
        self.assertAlmostEqual(XI_U_EV, 9.16, places=6)
        self.assertAlmostEqual(zeeman_ev(1.0), 2 * MUB_EV, places=12)


if __name__ == "__main__":
    unittest.main()
