"""Tests for Silicon/keating_cluster.py and Silicon/seed_influence.py.

KEA-1..7 and SEED-1..5. Stdlib only; everything here is settled by arithmetic.
"""

import itertools
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from keating_cluster import (  # noqa: E402
    ALPHA_EV_A2,
    BETA_EV_A2,
    BOND_DIRS,
    BRIDGES,
    CUBE_CORNERS,
    D0,
    PHI,
    bridge_verdicts,
    clamped_neighbours,
    coupling_hessian_is_symmetric,
    energy_is_even,
    ev_a2_to_n_per_m,
    find_minima,
    gate_set_coverage,
    keating_energy,
    linear_response,
    minimise,
    nearest_separations,
    phi_spacing,
    self_weight_strain,
    toffoli_is_degree_two,
)
from seed_influence import (  # noqa: E402
    axis_directions,
    cube_corner_directions,
    channel_response,
    influence_matrix,
    is_identity,
    max_offdiagonal,
    precision_gap_orders,
    proportions,
    proportions_invariant,
    quantisation_step,
    row_sums,
    row_sums_equal,
)


class TestKeatingParameters(unittest.TestCase):
    """Credit where due: these are right, which is rare in this set."""

    def test_alpha_matches_the_standard_value(self):
        self.assertAlmostEqual(ev_a2_to_n_per_m(ALPHA_EV_A2), 48.1, delta=0.3)

    def test_beta_is_close_to_the_standard_value(self):
        self.assertAlmostEqual(ev_a2_to_n_per_m(BETA_EV_A2), 12.0, delta=0.3)

    def test_both_are_within_a_factor_of_the_literature(self):
        for got, std in ((ev_a2_to_n_per_m(ALPHA_EV_A2), 48.50),
                         (ev_a2_to_n_per_m(BETA_EV_A2), 13.81)):
            self.assertLess(abs(math.log10(got / std)), math.log10(1.2))


class TestKea1UniqueMinimum(unittest.TestCase):
    """Falsifier: a second local minimum at any alpha, beta > 0."""

    def test_energy_vanishes_at_the_ideal_centre(self):
        self.assertLess(keating_energy((0.0, 0.0, 0.0)), 1e-20)

    def test_energy_is_non_negative_everywhere(self):
        import random
        rng = random.Random(5)
        for _ in range(500):
            p = tuple(rng.uniform(-2.0, 2.0) for _ in range(3))
            self.assertGreaterEqual(keating_energy(p), 0.0)

    def test_energy_grows_monotonically_outward_along_a_bond(self):
        prev = -1.0
        for d in (0.0, 0.05, 0.1, 0.2, 0.5, 0.8):
            e = keating_energy(tuple(d * c for c in BOND_DIRS[0]))
            self.assertGreater(e, prev)
            prev = e

    def test_exactly_one_minimum_from_two_hundred_starts(self):
        mins = find_minima(starts=200)
        self.assertEqual(len(mins), 1)
        self.assertLess(math.dist(mins[0][0], (0.0, 0.0, 0.0)), 1e-3)

    def test_the_minimum_is_the_ideal_centre_for_other_parameters(self):
        for alpha, beta in ((1.0, 0.25), (5.0, 2.0), (3.0, 0.01)):
            mins = find_minima(starts=40, alpha=alpha, beta=beta)
            self.assertEqual(len(mins), 1, msg=f"alpha={alpha} beta={beta}")
            self.assertLess(math.dist(mins[0][0], (0.0, 0.0, 0.0)), 1e-2)

    def test_local_minimisation_from_a_face_direction_returns_to_centre(self):
        """The document says a face-directed push finds a new stable position."""
        start = tuple(-0.4 * c for c in BOND_DIRS[0])
        p, e = minimise(start)
        self.assertLess(math.dist(p, (0.0, 0.0, 0.0)), 1e-3)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            keating_energy((0.0, 0.0))
        with self.assertRaises(ValueError):
            keating_energy((0.0, 0.0, 0.0), alpha=-1.0)
        with self.assertRaises(ValueError):
            clamped_neighbours(0.0)
        with self.assertRaises(ValueError):
            find_minima(starts=0)


class TestKea7ExactInversionSymmetry(unittest.TestCase):
    """The structural version: the model cannot tell vertex from face at all."""

    def test_the_four_clamped_vectors_sum_to_zero(self):
        v = clamped_neighbours()
        for k in range(3):
            self.assertAlmostEqual(sum(vk[k] for vk in v), 0.0, places=15)

    def test_every_pairwise_dot_is_exactly_minus_d0_squared_over_three(self):
        v = clamped_neighbours()
        for k, l in itertools.combinations(range(4), 2):
            self.assertAlmostEqual(sum(a * b for a, b in zip(v[k], v[l])),
                                   -D0 * D0 / 3.0, places=12)

    def test_energy_is_exactly_even_in_the_displacement(self):
        r = energy_is_even(samples=1500)
        self.assertTrue(r["is_even"])
        self.assertLess(r["worst_relative"], 1e-12)

    def test_vertex_and_face_displacements_are_degenerate(self):
        """The four (+t) and four (-t) directions give identical energies."""
        for d in (0.05, 0.1, 0.3, 0.6):
            for u in BOND_DIRS:
                a = keating_energy(tuple(d * c for c in u))
                b = keating_energy(tuple(-d * c for c in u))
                self.assertAlmostEqual(a, b, places=12)

    def test_all_eight_cube_corner_directions_split_into_four_equal_pairs(self):
        d = 0.25
        energies = {}
        for u in CUBE_CORNERS:
            energies[u] = keating_energy(tuple(d * c for c in u))
        distinct = sorted({round(v, 10) for v in energies.values()})
        self.assertLessEqual(len(distinct), 2)

    def test_this_is_the_same_degeneracy_as_gies1(self):
        """outer(v,v) == outer(-v,-v) there; E(p) == E(-p) here."""
        def outer(v):
            return [[x * y for y in v] for x in v]
        u = BOND_DIRS[0]
        self.assertEqual(outer(u), outer(tuple(-c for c in u)))
        self.assertAlmostEqual(keating_energy(tuple(0.2 * c for c in u)),
                               keating_energy(tuple(-0.2 * c for c in u)),
                               places=12)


class TestKea3PhiSpacing(unittest.TestCase):
    """Falsifier: a lattice site pair at 8.788 A."""

    def test_phi_times_lattice_constant(self):
        self.assertAlmostEqual(phi_spacing(), 8.7875, delta=0.001)
        self.assertAlmostEqual(PHI, 1.6180339887, places=9)

    def test_the_nearest_realisable_separation_is_detuned_by_over_one_percent(self):
        near = nearest_separations()
        self.assertAlmostEqual(near[0][0], 8.903, delta=0.005)
        self.assertGreater(abs(near[0][1]), 0.01)

    def test_no_realisable_separation_lands_on_the_target(self):
        for d, frac in nearest_separations(count=6):
            self.assertGreater(abs(frac), 1e-3)

    def test_the_second_nearest_is_detuned_the_other_way(self):
        near = nearest_separations()
        self.assertLess(near[1][1], 0.0)
        self.assertAlmostEqual(near[1][0], 8.587, delta=0.005)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            phi_spacing(0.0)
        with self.assertRaises(ValueError):
            nearest_separations(target=-1.0)


class TestKea2Reciprocity(unittest.TestCase):
    """Falsifier: a non-reciprocal static spring pair."""

    def test_cross_derivatives_are_equal(self):
        c = coupling_hessian_is_symmetric(2.5)
        self.assertEqual(c["d2E_d1d2"], c["d2E_d2d1"])
        self.assertTrue(c["symmetric"])

    def test_symmetry_holds_for_every_spring_constant(self):
        for k in (0.1, 1.0, PHI, PHI ** -2, 100.0):
            c = coupling_hessian_is_symmetric(k)
            self.assertTrue(c["symmetric"])
            self.assertAlmostEqual(c["d2E_d1d2"], -k, places=12)

    def test_rejects_nonpositive_constant(self):
        with self.assertRaises(ValueError):
            coupling_hessian_is_symmetric(0.0)


class TestKea4GateCoverage(unittest.TestCase):
    """Falsifier: S4 generating all 3-bit permutations."""

    def test_s4_has_24_elements_and_s8_has_40320(self):
        g = gate_set_coverage(bits=3, group_order=24)
        self.assertEqual(g["group_order"], 24)
        self.assertEqual(g["reversible_gates"], 40320)

    def test_coverage_is_one_in_1680(self):
        self.assertEqual(gate_set_coverage()["one_in"], 1680)

    def test_it_does_not_generate_all_reversible_gates(self):
        self.assertFalse(gate_set_coverage()["generates_all"])

    def test_full_oh_is_still_far_short(self):
        self.assertFalse(gate_set_coverage(group_order=48)["generates_all"])
        self.assertEqual(gate_set_coverage(group_order=48)["one_in"], 840)

    def test_most_boolean_functions_are_not_permutations(self):
        g = gate_set_coverage()
        self.assertEqual(g["boolean_functions"], 256)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            gate_set_coverage(bits=0)


class TestKea5Toffoli(unittest.TestCase):
    """Falsifier: Toffoli from a quadratic energy form alone."""

    def test_and_is_degree_two(self):
        t = toffoli_is_degree_two()
        self.assertEqual(t["degree"], 2)

    def test_no_linear_map_reproduces_and(self):
        t = toffoli_is_degree_two()
        self.assertEqual(t["linear_fits_found"], [])
        self.assertFalse(t["linear_suffices"])

    def test_quadratic_minimisation_gives_an_additive_response(self):
        both = linear_response(2.0, (1.0, 1.0), (1.0, 1.0))
        one = linear_response(2.0, (1.0, 1.0), (1.0, 0.0))
        other = linear_response(2.0, (1.0, 1.0), (0.0, 1.0))
        self.assertAlmostEqual(both, one + other, places=12)

    def test_and_is_not_additive_which_is_the_whole_point(self):
        self.assertNotEqual(1 & 1, (1 & 0) + (0 & 1))

    def test_rejects_a_non_minimum(self):
        with self.assertRaises(ValueError):
            linear_response(0.0, (1.0,), (1.0,))
        with self.assertRaises(ValueError):
            linear_response(1.0, (1.0, 1.0), (1.0,))


class TestKea6Bridges(unittest.TestCase):
    """Falsifier: measured direct or inverse piezo effect in undoped Si."""

    def test_only_the_harmonic_bridge_is_allowed(self):
        allowed = [k for k, v in BRIDGES.items() if v["allowed"]]
        self.assertEqual(allowed, ["harmonic"])

    def test_light_and_electric_bridges_have_named_replacements(self):
        self.assertIn("photothermal", BRIDGES["light"]["replacement"])
        self.assertIn("lectrostriction", BRIDGES["electric"]["replacement"])

    def test_electrostriction_is_the_even_order_survivor(self):
        """A centrosymmetric crystal forbids odd-rank tensors, not even ones."""
        self.assertFalse(BRIDGES["electric"]["allowed"])
        self.assertIsNotNone(BRIDGES["electric"]["replacement"])

    def test_gravitational_bridge_is_eight_orders_short(self):
        rows = {r["bridge"]: r for r in bridge_verdicts()}
        g = rows["gravitational"]
        self.assertGreater(g["orders_short"], 7.0)
        self.assertLess(g["achievable_strain"], 1e-9)

    def test_self_weight_strain_scales_with_length_and_inverse_modulus(self):
        self.assertAlmostEqual(self_weight_strain(2e-3) / self_weight_strain(1e-3),
                               2.0, places=12)
        self.assertAlmostEqual(
            self_weight_strain(youngs_pa=65e9) / self_weight_strain(youngs_pa=130e9),
            2.0, places=12)

    def test_rejects_bad_geometry(self):
        with self.assertRaises(ValueError):
            self_weight_strain(0.0)


class TestSeed1IdentityMatrix(unittest.TestCase):
    """Falsifier: any nonzero off-diagonal."""

    def test_axis_directions_give_the_identity_in_3d(self):
        w = influence_matrix(axis_directions(3))
        self.assertTrue(is_identity(w))
        self.assertEqual(max_offdiagonal(w), 0.0)

    def test_axis_directions_give_the_identity_in_8d(self):
        w = influence_matrix(axis_directions(8))
        self.assertEqual(len(w), 16)
        self.assertTrue(is_identity(w))

    def test_it_is_the_identity_in_every_dimension_tested(self):
        for dim in range(1, 9):
            self.assertTrue(is_identity(influence_matrix(axis_directions(dim))),
                            msg=f"dim {dim}")

    def test_the_reason_is_the_max_with_zero(self):
        """Antiparallel gives -1, and max(0,-1) = 0."""
        self.assertEqual(max(0.0, -1.0), 0.0)
        self.assertEqual(max(0.0, 0.0), 0.0)

    def test_rejects_an_empty_direction_set(self):
        with self.assertRaises(ValueError):
            influence_matrix([])
        with self.assertRaises(ValueError):
            axis_directions(0)


class TestSeed2Tautology(unittest.TestCase):
    """Falsifier: a seed whose proportions change across shells."""

    def test_proportions_are_invariant_under_the_identity(self):
        r = proportions_invariant(axis_directions(3))
        self.assertTrue(r["invariant"])
        self.assertTrue(r["tautological"])
        self.assertLess(r["worst_proportion_drift"], 1e-12)

    def test_invariance_holds_for_any_envelope(self):
        for env in (lambda r: math.exp(-r), lambda r: 1.0 / (1.0 + r ** 3),
                    lambda r: math.exp(-r * r * 7.0)):
            self.assertTrue(proportions_invariant(axis_directions(3),
                                                  envelope=env)["invariant"])

    def test_invariance_holds_in_8d_too(self):
        self.assertTrue(proportions_invariant(axis_directions(8))["invariant"])

    def test_proportions_sum_to_one(self):
        w = influence_matrix(axis_directions(3))
        p = proportions(channel_response(w, 1.0))
        self.assertAlmostEqual(sum(p), 1.0, places=12)

    def test_all_zero_response_is_refused(self):
        with self.assertRaises(ValueError):
            proportions([0.0, 0.0, 0.0])

    def test_needs_two_radii_to_compare(self):
        with self.assertRaises(ValueError):
            proportions_invariant(axis_directions(3), radii=(1.0,))


class TestSeed5FixIsInsufficient(unittest.TestCase):
    """The addition: making W non-trivial does not restore falsifiability."""

    def test_cube_corners_give_a_non_trivial_matrix(self):
        w = influence_matrix(cube_corner_directions())
        entries = sorted({round(v, 6) for row in w for v in row})
        self.assertEqual(entries, [0.0, 0.333333, 1.0])
        self.assertFalse(is_identity(w))
        self.assertGreater(max_offdiagonal(w), 0.3)

    def test_but_every_row_sums_to_two(self):
        w = influence_matrix(cube_corner_directions())
        self.assertTrue(row_sums_equal(w))
        for s in row_sums(w):
            self.assertAlmostEqual(s, 2.0, places=12)

    def test_so_proportions_are_still_invariant(self):
        r = proportions_invariant(cube_corner_directions())
        self.assertTrue(r["invariant"])
        self.assertTrue(r["tautological"])
        self.assertFalse(r["identity"])

    def test_vertex_transitive_sets_always_have_equal_row_sums(self):
        for dirs in (axis_directions(3), axis_directions(5),
                     cube_corner_directions()):
            self.assertTrue(row_sums_equal(influence_matrix(dirs)))

    def test_direction_dependent_profiles_do_break_it(self):
        corners = cube_corner_directions()
        profiles = [(lambda r, k=k: math.exp(-r * r * (1.0 + 0.35 * k)))
                    for k in range(len(corners))]
        r = proportions_invariant(corners, per_channel=profiles)
        self.assertFalse(r["invariant"])
        self.assertFalse(r["tautological"])
        self.assertGreater(r["worst_proportion_drift"], 0.01)

    def test_a_non_transitive_set_has_unequal_row_sums(self):
        dirs = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                (0.6, 0.8, 0.0)]
        self.assertFalse(row_sums_equal(influence_matrix(dirs)))

    def test_per_channel_profile_count_is_checked(self):
        w = influence_matrix(cube_corner_directions())
        with self.assertRaises(ValueError):
            channel_response(w, 1.0, per_channel=[lambda r: 1.0])


class TestSeed3Precision(unittest.TestCase):
    """Falsifier: lossless recovery below 1/256 resolution."""

    def test_eight_bit_step(self):
        self.assertAlmostEqual(quantisation_step(8), 3.90625e-3, places=9)

    def test_the_gap_to_the_claimed_fidelity_is_thirteen_orders(self):
        self.assertAlmostEqual(precision_gap_orders(8, 1e-16), 13.6, delta=0.1)

    def test_more_bits_narrow_the_gap_but_not_by_enough(self):
        self.assertLess(precision_gap_orders(16, 1e-16),
                        precision_gap_orders(8, 1e-16))
        self.assertGreater(precision_gap_orders(16, 1e-16), 10.0)

    def test_rejects_bad_inputs(self):
        with self.assertRaises(ValueError):
            quantisation_step(0)
        with self.assertRaises(ValueError):
            precision_gap_orders(8, 0.0)


if __name__ == "__main__":
    unittest.main()
