"""Tests for Silicon/epg_bounds.py -- EPG-4, EPG-6, EPG-7, EPG-8.

Stdlib only. EPG-1/2/3 need two copper samples and are not testable here.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from epg_bounds import (  # noqa: E402
    MECHANISMS,
    PARITY,
    SI_LATTICE_A,
    TETRAHEDRAL_DEG,
    bond_angles,
    cubic_isotropic,
    cubic_rotations,
    defect_floor,
    degenerate_pairs,
    diamond_cubic_basis,
    discriminator_power,
    maximin_bound,
    min_pairwise_angle,
    nearest_neighbours,
    reynolds_average,
    sampled_maximin_never_exceeds_bound,
    tetrahedral_vectors,
    surviving_mechanisms,
)


def _random_symmetric(rng, scale=1.0):
    m = [[rng.uniform(-scale, scale) for _ in range(3)] for _ in range(3)]
    return [[(m[i][j] + m[j][i]) / 2 for j in range(3)] for i in range(3)]


class TestEpg7CubicIsotropy(unittest.TestCase):
    """Falsifier: measured bulk anisotropy in undoped single-crystal Si."""

    def test_group_has_24_proper_rotations(self):
        self.assertEqual(len(cubic_rotations()), 24)

    def test_all_group_elements_are_orthogonal_with_unit_determinant(self):
        for r in cubic_rotations():
            for i in range(3):
                self.assertEqual(sum(abs(x) for x in r[i]), 1)
            cols = [sum(abs(r[i][j]) for i in range(3)) for j in range(3)]
            self.assertEqual(cols, [1, 1, 1])

    def test_every_cubic_invariant_rank2_tensor_is_isotropic(self):
        rng = random.Random(7)
        for _ in range(300):
            r = cubic_isotropic(_random_symmetric(rng))
            self.assertTrue(r["isotropic"])
            self.assertLess(r["worst_offdiagonal"], 1e-12)
            self.assertLess(r["diagonal_spread"], 1e-12)

    def test_the_invariant_part_is_the_mean_diagonal(self):
        t = [[3.0, 0.9, -0.2], [0.9, 1.0, 0.5], [-0.2, 0.5, -1.0]]
        r = cubic_isotropic(t)
        self.assertAlmostEqual(r["lambda"], (3.0 + 1.0 - 1.0) / 3.0, places=12)

    def test_an_isotropic_tensor_is_its_own_average(self):
        t = [[2.0, 0, 0], [0, 2.0, 0], [0, 0, 2.0]]
        avg = reynolds_average(t)
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(avg[i][j], t[i][j], places=12)

    def test_no_15x_ratio_survives_symmetrisation(self):
        """The documented kappa_[111] = 1.5 * kappa_[100] cannot exist."""
        t = [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.5]]
        avg = reynolds_average(t)
        ratio = max(avg[i][i] for i in range(3)) / min(avg[i][i] for i in range(3))
        self.assertAlmostEqual(ratio, 1.0, places=12)

    def test_scale_invariance(self):
        rng = random.Random(3)
        for scale in (1e-6, 1.0, 1e6):
            self.assertTrue(cubic_isotropic(_random_symmetric(rng, scale),
                                            tol=1e-12 * max(scale, 1.0))
                            ["isotropic"])


class TestEpg6Counts(unittest.TestCase):
    """Falsifier: an alternative tetrahedral angle that ever competed."""

    def test_tetrahedral_angle_is_arccos_minus_one_third(self):
        self.assertAlmostEqual(TETRAHEDRAL_DEG, 109.471221, places=5)

    def test_the_identity_that_forces_the_angle(self):
        """|sum(v_i)|^2 >= 0 caps the six pairwise dots at a mean of -1/3."""
        mb = maximin_bound()
        self.assertAlmostEqual(mb["dot_sum"], -2.0, places=12)
        self.assertAlmostEqual(mb["dot_mean"], -1.0 / 3.0, places=12)
        self.assertAlmostEqual(mb["resultant_norm"], 0.0, places=12)
        self.assertAlmostEqual(mb["min_dot"], mb["max_dot"], places=12)
        self.assertAlmostEqual(mb["angle_deg"], TETRAHEDRAL_DEG, places=9)

    def test_no_configuration_beats_the_bound(self):
        """The falsifiable direction: falling short means a weak search, but
        exceeding it would refute the claim."""
        r = sampled_maximin_never_exceeds_bound(samples=4000, seed=1)
        self.assertFalse(r["exceeded"])
        self.assertLessEqual(r["best_deg"], TETRAHEDRAL_DEG + 1e-9)

    def test_tetrahedral_vectors_are_unit_and_mutually_equidistant(self):
        vs = tetrahedral_vectors()
        self.assertEqual(len(vs), 4)
        for v in vs:
            self.assertAlmostEqual(math.sqrt(sum(x * x for x in v)), 1.0, places=12)
        self.assertAlmostEqual(min_pairwise_angle(vs), TETRAHEDRAL_DEG, places=9)

    def test_min_pairwise_angle_rejects_degenerate_input(self):
        with self.assertRaises(ValueError):
            min_pairwise_angle([(1.0, 0.0, 0.0)])
        with self.assertRaises(ValueError):
            min_pairwise_angle([(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)])

    def test_conventional_cell_holds_eight_atoms(self):
        self.assertEqual(len(set(diamond_cubic_basis())), 8)

    def test_the_two_sublattices_are_offset_by_a_quarter(self):
        basis = diamond_cubic_basis()
        for i in range(4):
            for k in range(3):
                self.assertAlmostEqual((basis[i][k] + 0.25) % 1,
                                       basis[i + 4][k], places=12)

    def test_four_nearest_neighbours_at_the_bond_length(self):
        nn = [d for d, _ in nearest_neighbours() if d < 2.4]
        self.assertEqual(len(nn), 4)
        self.assertAlmostEqual(nn[0], 2.3517, places=3)

    def test_bond_length_is_sqrt3_over_4_times_the_lattice_constant(self):
        expected = math.sqrt(3) / 4 * SI_LATTICE_A
        self.assertAlmostEqual(nearest_neighbours()[0][0], expected, places=9)

    def test_all_six_bond_angles_are_the_tetrahedral_angle(self):
        for a in bond_angles():
            self.assertAlmostEqual(a, TETRAHEDRAL_DEG, places=9)

    def test_eight_is_atoms_not_vertices(self):
        """The three merged counts, separated."""
        self.assertEqual(len(set(diamond_cubic_basis())), 8)     # atoms per cell
        cube = {p for p in __import__("itertools").product((-1, 1), repeat=3)}
        self.assertEqual(len(cube), 8)                            # cube corners
        octa = {(1, 0, 0), (-1, 0, 0), (0, 1, 0),
                (0, -1, 0), (0, 0, 1), (0, 0, -1)}
        self.assertEqual(len(octa), 6)                            # octa vertices

    def test_rejects_a_degenerate_lattice(self):
        with self.assertRaises(ValueError):
            bond_angles(a=1e-9)


class TestEpg4DefectFloor(unittest.TestCase):
    """Falsifier: a self-assembled phase below the entropic floor."""

    def test_logic_target_needs_about_thirty_kT(self):
        d = defect_floor(25.0, 0.01, 250.0)
        self.assertAlmostEqual(d["required_ef_over_kt"], 30.4, delta=0.3)

    def test_that_is_over_one_eV_at_anneal_temperature(self):
        self.assertGreater(defect_floor(25.0, 0.01, 250.0)["required_ef_ev"], 1.0)

    def test_measured_bcp_energies_fall_short(self):
        """A few kT to ~10 kT against a ~30 kT requirement."""
        need = defect_floor(25.0, 0.01, 250.0)["required_ef_over_kt"]
        self.assertGreater(need / 10.0, 3.0)

    def test_feature_count_scales_as_inverse_pitch_squared(self):
        a = defect_floor(20.0)["features_per_cm2"]
        b = defect_floor(40.0)["features_per_cm2"]
        self.assertAlmostEqual(a / b, 4.0, places=6)

    def test_requirement_is_weakly_sensitive_to_pitch(self):
        """Logarithmic: a 50% pitch change moves the requirement by <1 kT."""
        lo = defect_floor(20.0)["required_ef_over_kt"]
        hi = defect_floor(30.0)["required_ef_over_kt"]
        self.assertLess(abs(lo - hi), 1.0)

    def test_looser_target_lowers_the_requirement(self):
        strict = defect_floor(25.0, 0.01)["required_ef_over_kt"]
        loose = defect_floor(25.0, 1e6)["required_ef_over_kt"]
        self.assertLess(loose, strict)

    def test_hotter_anneal_raises_the_energy_requirement(self):
        self.assertGreater(defect_floor(25.0, 0.01, 350.0)["required_ef_ev"],
                           defect_floor(25.0, 0.01, 150.0)["required_ef_ev"])

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            defect_floor(0.0)
        with self.assertRaises(ValueError):
            defect_floor(25.0, 0.0)


class TestEpg8Discriminators(unittest.TestCase):
    """Falsifier: M1 surviving a polarity reversal unchanged."""

    def test_m1_and_m3_are_both_odd(self):
        """The corrected parity. The table had M1 as even, contradicting its
        own separator column."""
        self.assertEqual(PARITY["M1"], "odd")
        self.assertEqual(PARITY["M3"], "odd")

    def test_m2_and_m4_are_both_even(self):
        self.assertEqual(PARITY["M2"], "even")
        self.assertEqual(PARITY["M4"], "even")

    def test_m0_does_not_involve_the_current(self):
        self.assertEqual(PARITY["M0"], "none")
        self.assertEqual(MECHANISMS["M0"]["tracks"], "foil")

    def test_rotation_test_alone_settles_the_null(self):
        r = surviving_mechanisms(False, False, False)
        self.assertEqual(r["surviving"], ["M0"])
        self.assertTrue(r["resolved"])

    def test_the_null_verdict_is_independent_of_the_other_two_tests(self):
        for pol in (False, True):
            for pla in (False, True):
                self.assertEqual(
                    surviving_mechanisms(False, pol, pla)["surviving"], ["M0"])

    def test_polarity_reversal_does_not_separate_m1_from_m3(self):
        """Both odd, so the reversal test leaves both alive; plasma separates."""
        with_plasma = surviving_mechanisms(True, True, False)
        without = surviving_mechanisms(True, True, True)
        self.assertEqual(with_plasma["surviving"], ["M1"])
        self.assertEqual(without["surviving"], ["M3"])

    def test_even_parity_leaves_the_thermal_pair(self):
        r = surviving_mechanisms(True, False, True)
        self.assertEqual(r["surviving"], ["M2", "M4"])
        self.assertFalse(r["resolved"])
        self.assertTrue(r["consistent"])

    def test_an_impossible_observation_set_is_reported_as_such(self):
        """Even in I but dying without plasma matches no mechanism. The matrix
        is over-determined, so it can catch its own measurement errors."""
        r = surviving_mechanisms(True, False, False)
        self.assertEqual(r["surviving"], [])
        self.assertFalse(r["consistent"])
        self.assertIn("no mechanism", r["note"])

    def test_six_of_eight_cases_resolve_uniquely(self):
        dp = discriminator_power()
        self.assertEqual(dp["cases"], 8)
        self.assertEqual(dp["uniquely_resolved"], 6)

    def test_m2_m4_are_the_only_degenerate_pair(self):
        self.assertEqual(degenerate_pairs(), [("M2", "M4")])

    def test_every_mechanism_is_reachable_by_some_observation(self):
        reached = set()
        for row in discriminator_power()["rows"]:
            reached.update(row["surviving"])
        self.assertEqual(reached, set(MECHANISMS))


if __name__ == "__main__":
    unittest.main()
