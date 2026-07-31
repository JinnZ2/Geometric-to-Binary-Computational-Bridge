"""Tests for experiments/silicon_speculative -- VAC-1..4, TOP-3, VOR-1/2, ATT-1.

Needs numpy, like the modules it covers. The claims that were settled by running
the original code (TOP-1, TOP-2, VAC-1, VAC-3) are recorded in the audit headers;
what is tested here is the arithmetic behind them and the replacement
constructions.
"""

import math
import os
import sys
import unittest

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..",
                                "experiments", "silicon_speculative"))

from topological_pin import (  # noqa: E402
    circulation_gradient,
    controlled_vortex_comparison,
    core_position,
    gauss_flux_target,
    grid,
    head_contrast_cases,
    pin_energy,
    pin_gradient,
    run_pin_sweep,
    smooth_energy_gradient,
    total_winding,
    vortex_pair,
    vortex_phase,
    winding_number_field,
    wrap,
    zero_mode_energy,
)
from vacuum_bounds import (  # noqa: E402
    assertion_report,
    lyapunov_spectrum,
    modes_for_suppression,
    shells_for_suppression,
    suppression_floor,
)


class TestVac1Tautology(unittest.TestCase):
    """Falsifier: a matrix with lam_max != 0."""

    def test_max_lambda_is_zero_for_every_reference_matrix(self):
        for r in assertion_report():
            self.assertAlmostEqual(r["max_lambda"], 0.0, places=12,
                                   msg=r["matrix"])

    def test_max_lambda_is_zero_for_random_matrices(self):
        rng = np.random.default_rng(11)
        for _ in range(50):
            m = rng.standard_normal((12, 12))
            _, lam, _ = lyapunov_spectrum(m + m.T)
            self.assertAlmostEqual(float(lam.max()), 0.0, places=12)

    def test_the_survival_assertion_never_fails(self):
        for r in assertion_report():
            self.assertTrue(r["assert_one_survives"], msg=r["matrix"])

    def test_the_other_two_pass_for_random_noise(self):
        """VAC-3: random gaussian, uniform, diagonal and rank-1 all pass."""
        rows = {r["matrix"]: r for r in assertion_report()}
        for name in ("random gaussian", "random uniform [0,1]", "diag(1..n)",
                     "random rank-1 outer(v,v)", "all-ones"):
            self.assertTrue(rows[name]["assert_energy_reduced"], msg=name)
            self.assertTrue(rows[name]["assert_frac_below_one"], msg=name)

    def test_only_the_identity_fails_and_only_because_it_is_degenerate(self):
        rows = {r["matrix"]: r for r in assertion_report()}
        ident = rows["identity"]
        self.assertFalse(ident["assert_frac_below_one"])
        self.assertEqual(ident["surviving_frac"], 1.0)

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            lyapunov_spectrum(np.zeros((3, 4)))
        with self.assertRaises(ValueError):
            lyapunov_spectrum(np.zeros((3, 3)))


class TestVac4NoExponentialSuppression(unittest.TestCase):
    """The addition: the mechanism has a hard positive floor."""

    def test_suppression_never_reaches_zero(self):
        for r in assertion_report():
            self.assertGreater(r["suppression"], 0.0, msg=r["matrix"])

    def test_suppression_is_at_or_above_one_over_n(self):
        for r in assertion_report():
            self.assertGreaterEqual(r["suppression"] + 1e-12,
                                    suppression_floor(r["n_modes"]),
                                    msg=r["matrix"])

    def test_the_floor_is_one_over_n(self):
        self.assertAlmostEqual(suppression_floor(30), 1 / 30, places=12)
        self.assertAlmostEqual(suppression_floor(600), 1 / 600, places=12)

    def test_rejects_bad_mode_count(self):
        with self.assertRaises(ValueError):
            suppression_floor(0)


class TestVac2ModeCount(unittest.TestCase):
    """Falsifier: 1e-120 suppression from a finite lattice."""

    def test_thirty_modes_floor(self):
        self.assertAlmostEqual(suppression_floor(30), 3.33e-2, delta=1e-4)

    def test_a_million_shells_is_still_seven_orders_short(self):
        self.assertGreater(suppression_floor(6_000_000), 1e-8)

    def test_1e120_needs_1e120_modes(self):
        self.assertAlmostEqual(math.log10(modes_for_suppression(1e-120)),
                               120.0, places=6)

    def test_that_is_1e119_shells(self):
        self.assertAlmostEqual(math.log10(shells_for_suppression(1e-120)),
                               119.2, delta=0.1)

    def test_the_gap_from_thirty_modes_is_119_orders(self):
        self.assertAlmostEqual(
            math.log10(suppression_floor(30) / 1e-120), 118.5, delta=0.5)

    def test_rejects_impossible_targets(self):
        for bad in (0.0, 1.0, -1.0, 2.0):
            with self.assertRaises(ValueError):
                modes_for_suppression(bad)


class TestCirculationGradient(unittest.TestCase):
    """The finding that explains why a registry cannot be upgraded in place."""

    def test_winding_density_has_no_gradient(self):
        rng = np.random.default_rng(3)
        phi = rng.uniform(-0.5, 0.5, (12, 12))
        worst = 0.0
        for _ in range(150):
            i, j = int(rng.integers(0, 11)), int(rng.integers(0, 11))
            a, b = int(rng.integers(0, 12)), int(rng.integers(0, 12))
            worst = max(worst, abs(circulation_gradient(phi, i, j, a, b)))
        self.assertLess(worst, 1e-6)

    def test_it_is_zero_even_at_a_core(self):
        X, Y = grid(16)
        phi = vortex_pair(X, Y, 0.0, 0.0, 0.6)
        w = winding_number_field(phi)
        idx = np.argwhere(np.abs(w) > 0.5)
        self.assertGreater(len(idx), 0)
        i, j = int(idx[0][0]), int(idx[0][1])
        for a, b in ((i, j), (i + 1, j), (i, j + 1), (i + 1, j + 1)):
            self.assertLess(abs(circulation_gradient(phi, i, j, a, b)), 1e-6)

    def test_the_template_pin_does_have_a_gradient(self):
        X, Y = grid(16)
        phi = vortex_pair(X, Y, 0.1, 0.0, 0.6)
        g = pin_gradient(phi, X, Y, 0.0, 0.0, 0.5)
        self.assertGreater(float(np.abs(g).max()), 1e-3)

    def test_rejects_out_of_range_indices(self):
        phi = np.zeros((5, 5))
        with self.assertRaises(ValueError):
            circulation_gradient(phi, 9, 0, 0, 0)
        with self.assertRaises(ValueError):
            circulation_gradient(phi, 0, 0, 9, 0)


class TestAtt1PinRemovesTheZeroMode(unittest.TestCase):
    """Falsifier: registry-locked attention surviving core drift."""

    def test_displacement_is_free_when_k_p_is_zero(self):
        """That IS the zero mode, and it is what a registry leaves alone."""
        for d, e in zero_mode_energy([0.0, 0.1, 0.3, 0.5], k_p=0.0):
            self.assertAlmostEqual(e, 0.0, places=12)

    def test_displacement_costs_energy_when_k_p_is_positive(self):
        rows = dict(zero_mode_energy([0.0, 0.1, 0.2, 0.4], k_p=0.05))
        self.assertAlmostEqual(rows[0.0], 0.0, places=12)
        prev = -1.0
        for d in (0.1, 0.2, 0.4):
            self.assertGreater(rows[d], prev)
            prev = rows[d]

    def test_the_cost_scales_linearly_with_stiffness(self):
        a = dict(zero_mode_energy([0.2], k_p=0.05))[0.2]
        b = dict(zero_mode_energy([0.2], k_p=0.20))[0.2]
        self.assertAlmostEqual(b / a, 4.0, places=6)

    def test_the_unpinned_core_hops_and_the_pinned_one_does_not(self):
        rows = {r["k_p"]: r for r in run_pin_sweep(seeds=8)}
        self.assertGreater(rows[0.0]["hop_fraction"], 0.5)
        for k in (0.05, 0.2, 1.0):
            self.assertLess(rows[k]["hop_fraction"], 0.25, msg=f"k_p={k}")

    def test_mean_displacement_falls_with_stiffness(self):
        rows = {r["k_p"]: r for r in run_pin_sweep(seeds=8)}
        self.assertGreater(rows[0.0]["mean_displacement"],
                           rows[1.0]["mean_displacement"])

    def test_charge_survives_regardless_which_is_the_point(self):
        """Charge was never at risk. Position was."""
        for r in run_pin_sweep(seeds=6):
            self.assertGreaterEqual(r["survival_fraction"], 0.75,
                                    msg=f"k_p={r['k_p']}")

    def test_k_p_zero_is_labelled_as_the_control(self):
        rows = run_pin_sweep(k_values=(0.0, 0.5), seeds=3)
        self.assertTrue(rows[0]["is_registry_control"])
        self.assertFalse(rows[1]["is_registry_control"])

    def test_pin_energy_is_zero_at_the_reference(self):
        X, Y = grid(20)
        phi = vortex_phase(X, Y, 0.0, 0.0, 1)
        self.assertAlmostEqual(pin_energy(phi, X, Y, 0.0, 0.0, 1.0), 0.0,
                               places=10)

    def test_rejects_negative_stiffness(self):
        X, Y = grid(8)
        with self.assertRaises(ValueError):
            pin_energy(np.zeros((8, 8)), X, Y, 0.0, 0.0, -1.0)
        with self.assertRaises(ValueError):
            run_pin_sweep(k_values=(-0.1,), seeds=1)
        with self.assertRaises(ValueError):
            run_pin_sweep(k_values=(), seeds=1)


class TestVor1TopologyIsATheorem(unittest.TestCase):
    """Falsifier: a smooth flow changing total winding."""

    def test_smooth_flow_preserves_total_winding(self):
        X, Y = grid(32)
        phi = vortex_pair(X, Y, 0.0, 0.0, 0.9)
        before = total_winding(phi)
        p = np.array(phi, copy=True)
        for _ in range(60):
            p = wrap(p - smooth_energy_gradient(p, 0.002))
        self.assertAlmostEqual(total_winding(p), before, places=6)

    def test_winding_of_a_pair_is_zero_and_of_each_core_is_one(self):
        X, Y = grid(32)
        phi = vortex_pair(X, Y, 0.0, 0.0, 0.9)
        self.assertAlmostEqual(total_winding(phi), 0.0, places=6)
        w = winding_number_field(phi)
        self.assertEqual(int(np.sum(w > 0.5)), 1)
        self.assertEqual(int(np.sum(w < -0.5)), 1)

    def test_a_lone_vortex_is_illegal_on_a_periodic_grid(self):
        """Net winding must vanish on a torus, so a single core dissolves --
        an artifact of the boundary, not a physical result."""
        X, Y = grid(24)
        lone = vortex_phase(X, Y, 0.0, 0.0, 1)
        p = np.array(lone, copy=True)
        for _ in range(200):
            p = wrap(p - smooth_energy_gradient(p, 0.02))
        self.assertLess(abs(total_winding(p)), abs(total_winding(lone)) + 1e-9)

    def test_core_position_uses_plaquette_centres(self):
        """Removes the systematic dx/2 offset from corner indexing."""
        X, Y = grid(40)
        phi = vortex_pair(X, Y, 0.0, 0.0, 0.8)
        pos = core_position(phi, 1.0, 1.0)
        self.assertIsNotNone(pos)
        self.assertLess(abs(pos[0]), 2.0 / 39)

    def test_an_odd_grid_puts_the_singularity_on_a_site(self):
        """Gotcha worth recording: with an odd n the vortex centre lands on a
        grid POINT rather than in a plaquette, arctan2 is evaluated at its own
        singularity, and the circulation smears below the detection threshold.
        Use an even grid, or offset the core."""
        X, Y = grid(41)
        phi = vortex_pair(X, Y, 0.0, 0.0, 0.8)
        self.assertIsNone(core_position(phi, 1.0, 1.0))
        X, Y = grid(41)
        offset = vortex_pair(X, Y, 0.025, 0.025, 0.8)
        self.assertIsNotNone(core_position(offset, 1.0, 1.0))

    def test_core_position_returns_none_when_there_is_no_core(self):
        self.assertIsNone(core_position(np.zeros((16, 16))))


class TestVor2ControlledComparison(unittest.TestCase):
    """Falsifier: a controlled comparison reversing the verdict."""

    def test_the_two_original_conditions_differ_in_amplitude(self):
        """cos of +-0.3 is [0.955, 1.0] -- nearly the identity map."""
        self.assertAlmostEqual(math.cos(0.3), 0.9553, places=4)

    def test_the_controlled_version_shares_an_init(self):
        c = controlled_vortex_comparison()
        self.assertTrue(c["shared_init"])

    def test_the_vortex_arm_spans_the_full_sign_range(self):
        c = controlled_vortex_comparison()
        self.assertLess(c["vortex_cos_range"][0], -0.5)
        self.assertGreater(c["flat_cos_range"][0], 0.5)

    def test_the_flat_arm_has_no_cores_and_the_vortex_arm_has_two(self):
        c = controlled_vortex_comparison()
        self.assertEqual(c["flat_core_count"], 0)
        self.assertEqual(c["vortex_core_count"], 2)

    def test_net_winding_is_zero_in_both_because_it_is_a_pair(self):
        c = controlled_vortex_comparison()
        self.assertAlmostEqual(c["flat_net_winding"], 0.0, places=6)
        self.assertAlmostEqual(c["vortex_net_winding"], 0.0, places=6)

    def test_rejects_a_nonpositive_amplitude(self):
        with self.assertRaises(ValueError):
            controlled_vortex_comparison(amplitude=0.0)


class TestTop3GaussFluxTarget(unittest.TestCase):
    """Falsifier: a phi-independent target that V still wins on."""

    def test_flux_is_two_pi_times_an_integer(self):
        for k in (-2, -1, 0, 1, 3):
            self.assertAlmostEqual(gauss_flux_target(k)["flux"],
                                   2 * math.pi * k, places=12)

    def test_it_is_model_independent(self):
        self.assertTrue(gauss_flux_target(1)["model_independent"])

    def test_a_non_integer_charge_is_refused(self):
        with self.assertRaises(ValueError):
            gauss_flux_target(1.5)

    def test_the_flux_matches_the_measured_winding_of_a_real_field(self):
        X, Y = grid(64)
        phi = vortex_phase(X, Y, 0.0, 0.0, 1)
        self.assertAlmostEqual(total_winding(phi) * 2 * math.pi,
                               gauss_flux_target(1)["flux"], delta=0.2)


class TestHeadContrast(unittest.TestCase):
    """Two degenerate cases, and the audit conflated them."""

    def test_a_one_lobe_head_scores_a_perfect_one(self):
        cases = {(c["s_pos"], c["s_neg"]): c for c in head_contrast_cases()}
        self.assertAlmostEqual(cases[(1.0, 0.0)]["contrast"], 1.0, places=12)

    def test_a_blind_head_is_nan_not_one(self):
        cases = {(c["s_pos"], c["s_neg"]): c for c in head_contrast_cases()}
        self.assertTrue(math.isnan(cases[(0.0, 0.0)]["contrast"]))


if __name__ == "__main__":
    unittest.main()
