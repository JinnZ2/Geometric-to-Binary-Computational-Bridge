"""Tests for Silicon/er_bounds.py -- ER-1..8.

Stdlib only. ER-1..7 are settled by arithmetic and these tests are what settles
them. ER-8 lives in ``magnetic_authority.py``; the cross-check here is that the
two modules agree.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from er_bounds import (  # noqa: E402
    A_GE,
    A_SI,
    M_ER_U,
    MASSES_U,
    QE,
    SI_PHONON_MAX_CM,
    areal_density,
    bose_occupation,
    coherence_shortfall,
    dose_for_concentration,
    energy_per_bit_check,
    force_constant,
    gap_mode_possible,
    ge_fraction_for_strain,
    heavy_mass_ceiling,
    implant_concentration,
    k_omega_consistency,
    kT_wavenumber,
    landauer_aj,
    lvm_gate,
    mass_ratio,
    orbach_factor,
    orbach_regime,
    sige_mismatch,
    t2_ceiling_from_t1,
    thermal_phonon_window_thz,
    vibrational_period,
    wavenumber_from_k,
)


class TestEr1Orbach(unittest.TestCase):
    """Falsifier: observable Er3+ EPR above ~30 K in any host."""

    def test_kT_at_room_temperature_in_wavenumbers(self):
        self.assertAlmostEqual(kT_wavenumber(300.0), 208.5, delta=0.5)

    def test_crystal_field_gap_is_far_below_kT(self):
        for gap in (40.0, 60.0):
            self.assertLess(gap, kT_wavenumber(300.0) / 3.0)

    def test_orbach_is_saturated_not_activated(self):
        """The correction: Delta << kT, so the rate goes linear in T."""
        for gap in (40.0, 60.0):
            r = orbach_regime(gap)
            self.assertTrue(r["saturated"], msg=f"gap {gap}")
            self.assertLess(r["gap_over_kT"], 1.0)
            self.assertIn("linear", r["regime"])

    def test_the_exponential_factor_understates_it(self):
        """exp(-D/kT) ~ 0.8 sounds like mild suppression; n_bar is 3-5."""
        self.assertAlmostEqual(orbach_factor(40.0), 0.825, delta=0.01)
        self.assertAlmostEqual(bose_occupation(40.0), 4.73, delta=0.05)
        self.assertAlmostEqual(bose_occupation(60.0), 3.00, delta=0.05)
        self.assertGreater(bose_occupation(40.0), 1.0)

    def test_bose_occupation_grows_with_temperature(self):
        self.assertGreater(bose_occupation(40.0, 300.0),
                           bose_occupation(40.0, 4.0))

    def test_at_cryogenic_temperature_orbach_is_genuinely_shut(self):
        """Which is why Er quantum memory works below 4 K and only there."""
        r = orbach_regime(40.0, temp_k=2.0)
        self.assertFalse(r["saturated"])
        self.assertLess(r["exp_factor"], 1e-12)
        self.assertLess(bose_occupation(40.0, 2.0), 1e-12)

    def test_t2_is_capped_at_twice_t1(self):
        self.assertAlmostEqual(t2_ceiling_from_t1(1e-9), 2e-9, places=15)

    def test_claimed_t2_is_eight_orders_over_the_ceiling(self):
        s = coherence_shortfall(166e-3, 1e-9)
        self.assertTrue(s["exceeds_ceiling"])
        self.assertGreater(s["orders_over_ceiling"], 7.0)
        self.assertLess(s["orders_over_ceiling"], 9.0)

    def test_claimed_t2_is_about_100x_the_world_record(self):
        s = coherence_shortfall(166e-3, 1e-9)
        self.assertGreater(s["times_world_record"], 50.0)
        self.assertLess(s["times_world_record"], 200.0)

    def test_even_a_microsecond_t1_would_not_rescue_it(self):
        """Grant 1000x on T1 and the claim is still 5 orders out."""
        s = coherence_shortfall(166e-3, 1e-6)
        self.assertTrue(s["exceeds_ceiling"])
        self.assertGreater(s["orders_over_ceiling"], 4.0)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            kT_wavenumber(0.0)
        with self.assertRaises(ValueError):
            bose_occupation(0.0)
        with self.assertRaises(ValueError):
            t2_ceiling_from_t1(0.0)


class TestEr2MassGate(unittest.TestCase):
    """Falsifier: a sharp Er gap mode above 520 cm^-1."""

    def test_only_lighter_impurities_can_have_gap_modes(self):
        for light in ("B", "C", "N", "O"):
            self.assertTrue(gap_mode_possible(light), msg=light)
            self.assertLess(mass_ratio(light), 1.0)

    def test_er_is_six_times_heavier_than_silicon(self):
        self.assertAlmostEqual(mass_ratio("Er"), 5.96, delta=0.02)
        self.assertFalse(gap_mode_possible("Er"))

    def test_phosphorus_is_also_heavier_so_no_gap_mode(self):
        """Kills 'P local mode at ~500 cm^-1' by the same gate."""
        self.assertGreater(mass_ratio("P"), 1.0)
        self.assertFalse(gap_mode_possible("P"))

    def test_the_heavy_mass_ceiling_for_er(self):
        self.assertAlmostEqual(heavy_mass_ceiling("Er"), 213.0, delta=1.0)

    def test_the_search_window_sits_above_the_ceiling(self):
        g = lvm_gate(300.0, 400.0, "Er")
        self.assertFalse(g["window_reachable"])
        self.assertFalse(g["gap_mode_possible"])
        self.assertLess(g["ceiling_cm"], 300.0)

    def test_observed_light_impurity_modes_are_above_the_host_maximum(self):
        for imp, lo in (("B", 620.0), ("C", 607.0), ("O", 1136.0)):
            self.assertGreater(lo, SI_PHONON_MAX_CM, msg=imp)
            self.assertTrue(gap_mode_possible(imp))

    def test_no_heavy_impurity_has_an_observed_gap_mode(self):
        for imp in ("P", "Ge", "Er"):
            self.assertIsNone(lvm_gate(100.0, 600.0, imp)["observed_lvm_cm"])

    def test_ceiling_falls_as_the_impurity_gets_heavier(self):
        self.assertGreater(heavy_mass_ceiling("P"), heavy_mass_ceiling("Ge"))
        self.assertGreater(heavy_mass_ceiling("Ge"), heavy_mass_ceiling("Er"))

    def test_a_window_below_the_ceiling_is_reachable(self):
        """Not a blanket 'no' -- an in-band resonance can exist, just broadened."""
        self.assertTrue(lvm_gate(100.0, 200.0, "Er")["window_reachable"])

    def test_rejects_unknown_species_and_bad_windows(self):
        with self.assertRaises(ValueError):
            mass_ratio("Unobtainium")
        with self.assertRaises(ValueError):
            lvm_gate(400.0, 300.0)


class TestEr3ForceConstant(unittest.TestCase):
    """Falsifier: a consistent (omega, k) pair in the same table."""

    def test_350_wavenumbers_implies_1207_newtons_per_metre(self):
        self.assertAlmostEqual(force_constant(350.0), 1207.0, delta=5.0)

    def test_150_newtons_per_metre_implies_123_wavenumbers(self):
        self.assertAlmostEqual(wavenumber_from_k(150.0), 123.4, delta=0.5)

    def test_the_stated_pair_is_inconsistent_by_eight(self):
        c = k_omega_consistency(350.0, 150.0)
        self.assertFalse(c["consistent"])
        self.assertAlmostEqual(c["k_ratio"], 8.0, delta=0.1)

    def test_the_pivot_criterion_is_mis_set_by_six(self):
        self.assertAlmostEqual(wavenumber_from_k(100.0), 100.7, delta=0.5)
        self.assertAlmostEqual(force_constant(250.0), 616.0, delta=3.0)
        self.assertAlmostEqual(force_constant(250.0) / 100.0, 6.2, delta=0.1)

    def test_k_and_wavenumber_round_trip(self):
        for wn in (100.0, 250.0, 350.0, 520.7):
            self.assertAlmostEqual(wavenumber_from_k(force_constant(wn)), wn,
                                   places=6)

    def test_k_scales_as_the_square_of_frequency(self):
        self.assertAlmostEqual(force_constant(700.0) / force_constant(350.0),
                               4.0, places=9)

    def test_a_consistent_pair_is_reported_as_consistent(self):
        c = k_omega_consistency(350.0, force_constant(350.0))
        self.assertTrue(c["consistent"])
        self.assertAlmostEqual(c["k_ratio"], 1.0, places=9)

    def test_mass_matters(self):
        self.assertAlmostEqual(force_constant(350.0, mass_u=M_ER_U)
                               / force_constant(350.0, mass_u=M_ER_U / 2),
                               2.0, places=9)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            force_constant(0.0)
        with self.assertRaises(ValueError):
            wavenumber_from_k(-1.0)


class TestEr4NoLinkToT2(unittest.TestCase):
    """Falsifier: an equation linking k_well to T2."""

    def test_the_only_time_in_k_and_m_is_the_vibrational_period(self):
        self.assertAlmostEqual(vibrational_period(350.0) * 1e15, 95.3, delta=0.5)

    def test_that_period_is_twelve_orders_from_the_claimed_t2(self):
        self.assertGreater(math.log10(166e-3 / vibrational_period(350.0)), 12.0)

    def test_period_is_the_reciprocal_of_frequency(self):
        for wn in (100.0, 350.0, 520.7):
            self.assertAlmostEqual(1.0 / vibrational_period(wn),
                                   2.99792458e10 * wn, places=0)

    def test_k_carries_no_information_beyond_the_frequency(self):
        """k = m*omega^2 is a relabelling, so the map is injective and reversible
        -- which means it adds nothing that was not measured."""
        for wn in (200.0, 350.0):
            self.assertAlmostEqual(wavenumber_from_k(force_constant(wn)), wn,
                                   places=9)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            vibrational_period(0.0)


class TestEr7Implants(unittest.TestCase):
    """Falsifier: SIMS showing 1e17 cm^-3 from a 5e16 cm^-2 dose over 50 nm."""

    def test_the_er_recipe_gives_twenty_atomic_percent(self):
        r = implant_concentration(5e16, 50.0)
        self.assertAlmostEqual(r["concentration_per_cm3"], 1e22, delta=1e20)
        self.assertAlmostEqual(r["atomic_percent"], 20.0, delta=0.5)

    def test_the_p_recipe_gives_eighty_atomic_percent(self):
        r = implant_concentration(2e17, 50.0)
        self.assertAlmostEqual(r["atomic_percent"], 80.0, delta=1.0)

    def test_both_exceed_er_solubility_by_orders(self):
        for dose in (5e16, 2e17):
            self.assertTrue(implant_concentration(dose, 50.0)["exceeds_solubility"])

    def test_the_dose_for_the_documents_own_concentration(self):
        self.assertAlmostEqual(dose_for_concentration(1e17, 50.0), 5e11,
                               delta=1e9)

    def test_the_recipe_is_five_orders_too_high(self):
        need = dose_for_concentration(1e17, 50.0)
        self.assertAlmostEqual(math.log10(5e16 / need), 5.0, delta=0.05)

    def test_rbs_cannot_see_the_intended_areal_density(self):
        a = areal_density(1e17, 50.0)
        self.assertFalse(a["detectable"])
        self.assertGreater(a["shortfall"], 10.0)

    def test_rbs_could_see_the_recipe_dose_which_is_the_wrong_target(self):
        """The recipe is detectable precisely because it is 1e5x too heavy."""
        a = areal_density(1e22, 50.0)
        self.assertTrue(a["detectable"])

    def test_concentration_and_dose_are_inverses(self):
        for c in (1e17, 1e19):
            self.assertAlmostEqual(
                implant_concentration(dose_for_concentration(c, 50.0),
                                      50.0)["concentration_per_cm3"],
                c, delta=c * 1e-9)

    def test_rejects_bad_geometry(self):
        with self.assertRaises(ValueError):
            implant_concentration(1e16, 0.0)
        with self.assertRaises(ValueError):
            dose_for_concentration(1e17, -1.0)


class TestEr5Germanium(unittest.TestCase):
    """Falsifier: 1.2% strain from a 2% Ge buffer."""

    def test_two_percent_ge_gives_a_tenth_of_a_percent_mismatch(self):
        self.assertAlmostEqual(sige_mismatch(0.02) * 100, 0.084, delta=0.002)

    def test_the_document_overstates_the_mismatch_tenfold(self):
        self.assertAlmostEqual(0.8 / (sige_mismatch(0.02) * 100), 9.6, delta=0.3)

    def test_twelve_tenths_percent_strain_needs_twentynine_percent_ge(self):
        x = ge_fraction_for_strain(0.012)
        self.assertAlmostEqual(x, 0.287, delta=0.003)
        self.assertAlmostEqual(x / 0.02, 14.3, delta=0.3)

    def test_mismatch_and_fraction_are_inverses(self):
        for x in (0.02, 0.1, 0.287, 0.5):
            self.assertAlmostEqual(ge_fraction_for_strain(sige_mismatch(x)), x,
                                   places=9)

    def test_vegard_endpoints(self):
        self.assertAlmostEqual(sige_mismatch(0.0), 0.0, places=12)
        self.assertAlmostEqual(sige_mismatch(1.0) * 100,
                               (A_GE - A_SI) / A_SI * 100, places=9)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            sige_mismatch(1.5)
        with self.assertRaises(ValueError):
            ge_fraction_for_strain(0.5)      # would need x > 1


class TestEr6Phonons(unittest.TestCase):
    """Falsifier: dislocation density <1e4 cm^-2 at 1.2%, 50 nm, 1000 C RTA."""

    def test_thermal_window_at_growth_temperature(self):
        self.assertAlmostEqual(thermal_phonon_window_thz(550.0), 17.2, delta=0.2)

    def test_a_minigap_removes_about_one_percent_of_it(self):
        w = thermal_phonon_window_thz(550.0)
        self.assertLess(0.2 / w, 0.02)

    def test_window_grows_with_temperature(self):
        self.assertGreater(thermal_phonon_window_thz(1000.0),
                           thermal_phonon_window_thz(550.0))

    def test_the_rta_step_is_600_degrees_above_the_validation_anneal(self):
        self.assertEqual(1000 - 400, 600)

    def test_rejects_below_absolute_zero(self):
        with self.assertRaises(ValueError):
            thermal_phonon_window_thz(-300.0)


class TestEnergyPerBitLegality(unittest.TestCase):
    """Q4.2: three values for one quantity, and not all are physically allowed."""

    def test_landauer_bound_at_room_temperature(self):
        self.assertAlmostEqual(landauer_aj(300.0), 0.00287, delta=5e-5)

    def test_one_attojoule_is_legal_but_aggressive(self):
        r = energy_per_bit_check(1.0)
        self.assertTrue(r["above_bound"])
        self.assertAlmostEqual(r["in_kt_ln2"], 348.0, delta=3.0)

    def test_one_hundredth_eV_is_below_the_bound(self):
        r = energy_per_bit_check(0.01 * QE * 1e18)
        self.assertFalse(r["above_bound"])
        self.assertLess(r["in_kt_ln2"], 1.0)

    def test_one_tenth_eV_is_legal(self):
        r = energy_per_bit_check(0.1 * QE * 1e18)
        self.assertTrue(r["above_bound"])
        self.assertAlmostEqual(r["in_kt_ln2"], 5.58, delta=0.1)

    def test_the_three_values_span_four_orders(self):
        vals = [1.0, 0.1 * QE * 1e18, 0.01 * QE * 1e18]
        self.assertGreater(math.log10(max(vals) / min(vals)), 2.5)

    def test_a_conventional_switching_event_is_far_larger(self):
        """1-2 aJ/bit is ~300x below CV^2 at 1 fF, 0.8 V -- adiabatic territory."""
        cv2 = energy_per_bit_check(1.0)["cv2_1ff_0v8_aj"]
        self.assertAlmostEqual(cv2, 640.0, delta=1.0)
        self.assertGreater(cv2 / 1.0, 100.0)

    def test_landauer_scales_with_temperature(self):
        self.assertAlmostEqual(landauer_aj(600.0) / landauer_aj(300.0), 2.0,
                               places=9)

    def test_rejects_bad_temperature(self):
        with self.assertRaises(ValueError):
            landauer_aj(0.0)


class TestCrossModuleConsistency(unittest.TestCase):
    """ER-8 lives in magnetic_authority; the two modules must agree."""

    def test_piezoresistive_readout_beats_every_magnetic_option(self):
        from magnetic_authority import (cell_moment, piezoresistive_response,
                                        readout_shortfall)
        pr = piezoresistive_response(0.001)
        mag = readout_shortfall(cell_moment(5e-6 * 5e-6 * 100e-9, 0.050))
        self.assertGreater(pr["dr_over_r"], 0.01)
        self.assertLess(mag["hall_snr"], 1e-11)

    def test_the_er_paper_value_repeats_a_corrected_coefficient(self):
        """6e-11 Pa^-1 is pi_11 (<100>); <110> longitudinal is 7.18e-10."""
        from magnetic_authority import PI_11, PI_L_110, piezoresistive_response
        self.assertAlmostEqual(PI_11, 6.6e-11, delta=1e-12)
        self.assertGreater(PI_L_110 / PI_11, 10.0)
        self.assertAlmostEqual(piezoresistive_response(0.001)["gauge_factor"],
                               93.0, delta=3.0)

    def test_masses_table_matches_the_module_constant(self):
        self.assertEqual(MASSES_U["Er"], M_ER_U)


if __name__ == "__main__":
    unittest.main()
