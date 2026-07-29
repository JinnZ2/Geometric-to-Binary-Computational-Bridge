"""Tests for the stdlib tier of Negentropic/.

Imports nothing outside the standard library, so this suite runs in an
environment with no numpy installed -- which is the point of the tier.

Covers: core.DissipativeCore and its coupling kernels, bounds (TUR/KUR),
landauer (finite-time erasure), maintenance (NEG-2), persistence (NEG-8),
lenses, lens_collapse_test (NEG-7 falsifier), emit_ising.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Negentropic import bounds, landauer, maintenance, persistence
from Negentropic.core import (
    DissipativeCore,
    distance_kernel,
    phase_alignment,
    wrap_phase,
)
from Negentropic.emit_ising import (
    IsingSpec,
    anneal,
    energy,
    flip_cost_floor,
    from_core,
    octahedral_bits,
    phase_to_octahedral_gray,
    pbit_sweep,
    spins_to_bits,
)
from Negentropic.lens_collapse_test import (
    compare,
    matched_verdict,
    named_floor,
    pearson,
    random_lens,
    run,
    verdict,
)
from Negentropic.lenses import (
    CANONICAL_FORM_EXCEPTIONS,
    LENS_COEFFICIENTS,
    LENS_REGISTRY,
    canonical_lens,
)
from Negentropic.precession import (
    CATALOG,
    OBLIQUITY,
    POLE_ECLIPTIC_LATITUDE,
    PRECESSION_PERIOD,
    alignment_window,
    closest_approach,
    declination_at,
    drift_years_per_degree,
    equatorial_to_ecliptic,
    is_circumpolar,
    limiting_latitude,
    pole_ecliptic_longitude,
    separation_from_pole,
)
from Negentropic.rebase import Archive


# ---------------------------------------------------------------------------
# Coupling kernels -- the cos-wrap defect
# ---------------------------------------------------------------------------

class TestCouplingKernels(unittest.TestCase):
    def test_wrap_phase_maps_into_interval(self):
        for delta in (-10.0, -math.pi, 0.0, 3.0, 7.0, 100.0):
            w = wrap_phase(delta)
            self.assertGreater(w, -math.pi - 1e-12)
            self.assertLessEqual(w, math.pi + 1e-12)

    def test_wrap_phase_preserves_cosine(self):
        for delta in (-10.0, 0.3, 7.0, 100.0):
            self.assertAlmostEqual(math.cos(wrap_phase(delta)), math.cos(delta), places=10)

    def test_phase_alignment_bounds(self):
        self.assertAlmostEqual(phase_alignment(0.0), 1.0)
        self.assertAlmostEqual(phase_alignment(math.pi), 0.0)
        for delta in (-5.0, -1.0, 0.0, 1.0, 5.0, 12.0):
            self.assertGreaterEqual(phase_alignment(delta), 0.0)
            self.assertLessEqual(phase_alignment(delta), 1.0)

    def test_phase_alignment_is_periodic(self):
        # A phase difference genuinely lives on the circle, so 2pi
        # equivalence here is correct rather than a defect.
        self.assertAlmostEqual(phase_alignment(0.4), phase_alignment(0.4 + 2 * math.pi))

    def test_distance_kernel_is_strictly_decreasing(self):
        # The defect: 0.5*(cos(d)+1) gave 1.0 at d = 0, 2pi and 4pi alike.
        values = [distance_kernel(d) for d in (0.0, 1.0, math.pi, 2 * math.pi, 4 * math.pi)]
        for earlier, later in zip(values, values[1:]):
            self.assertGreater(earlier, later)
        self.assertAlmostEqual(values[0], 1.0)

    def test_distance_kernel_never_reaches_zero(self):
        self.assertGreater(distance_kernel(50.0), 0.0)

    def test_distance_kernel_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            distance_kernel(-1.0)
        with self.assertRaises(ValueError):
            distance_kernel(1.0, scale=0.0)


# ---------------------------------------------------------------------------
# DissipativeCore
# ---------------------------------------------------------------------------

class TestDissipativeCore(unittest.TestCase):
    def setUp(self):
        self.core = DissipativeCore(n=30, K=1.5, Dn=0.045, dt=0.02, seed=1)

    def test_order_parameter_in_unit_interval(self):
        for _ in range(20):
            r, psi = self.core.order()
            self.assertGreaterEqual(r, 0.0)
            self.assertLessEqual(r, 1.0)
            self.assertGreaterEqual(psi, -math.pi)
            self.assertLessEqual(psi, math.pi)
            self.core.step()

    def test_entropy_bounded_by_log_bins(self):
        ceiling = math.log(self.core.bins)
        for _ in range(20):
            h = self.core.entropy()
            self.assertGreaterEqual(h, 0.0)
            self.assertLessEqual(h, ceiling + 1e-12)
            self.core.step()

    def test_entropy_zero_when_fully_collapsed(self):
        self.core.theta = [0.11] * self.core.n
        self.assertAlmostEqual(self.core.entropy(), 0.0)

    def test_coupling_is_attractive(self):
        """Sign check: strong coupling with no noise must raise R, not lower it.

        This is the FATAL defect from the old UniversalCore -- the sign was
        inverted, so the population desynchronised.
        """
        core = DissipativeCore(n=40, K=8.0, Dn=1e-6, dt=0.01, seed=5)
        start, _ = core.order()
        for _ in range(600):
            core.step()
        end, _ = core.order()
        self.assertGreater(end, start)
        self.assertGreater(end, 0.8)

    def test_zero_coupling_does_not_synchronise(self):
        core = DissipativeCore(n=40, K=0.0, Dn=1e-6, dt=0.01, seed=5)
        for _ in range(600):
            core.step()
        end, _ = core.order()
        self.assertLess(end, 0.5)

    def test_entropy_and_order_are_not_the_same_channel(self):
        core = DissipativeCore(n=50, K=2.0, Dn=0.05, dt=0.02, seed=9)
        trace = core.run(steps=200, burn_in=100)
        rs = [row["R"] for row in trace]
        hs = [row["H"] for row in trace]
        self.assertLess(abs(pearson(rs, hs)), 0.999)

    def test_sigma_is_positive(self):
        for row in self.core.run(steps=50, burn_in=10):
            self.assertGreater(row["sigma"], 0.0)

    def test_seeded_runs_are_reproducible(self):
        a = DissipativeCore(n=20, seed=42).run(steps=30, burn_in=5)
        b = DissipativeCore(n=20, seed=42).run(steps=30, burn_in=5)
        self.assertEqual([r["R"] for r in a], [r["R"] for r in b])

    def test_instance_rng_ignores_global_seed(self):
        random.seed(1)
        a = DissipativeCore(n=20, seed=7).run(steps=20, burn_in=5)
        random.seed(999)
        b = DissipativeCore(n=20, seed=7).run(steps=20, burn_in=5)
        self.assertEqual([r["R"] for r in a], [r["R"] for r in b])

    def test_undriven_core_absorbs_no_work(self):
        trace = self.core.run(steps=40, burn_in=10)
        self.assertAlmostEqual(trace[-1]["w_abs"], 0.0)

    def test_driven_core_absorbs_work(self):
        driven = DissipativeCore(n=30, K=1.5, Dn=0.045, dt=0.02,
                                 drive_amp=0.9, drive_freq=1.0, seed=1)
        trace = driven.run(steps=200, burn_in=100)
        self.assertNotAlmostEqual(trace[-1]["w_abs"], 0.0)

    def test_constructor_rejects_bad_parameters(self):
        for kwargs in ({"n": 1}, {"Dn": 0.0}, {"dt": -1.0}, {"bins": 1}):
            with self.assertRaises(ValueError):
                DissipativeCore(**kwargs)

    def test_legacy_trace_shape_and_degeneracy(self):
        trace = self.core.legacy_rad_trace(steps=40, burn_in=10)
        self.assertEqual(len(trace), 40)
        self.assertTrue(all(len(row) == 4 for row in trace))
        # D was var(omega), fixed at construction: constant along the run.
        ds = {row[2] for row in trace}
        self.assertEqual(len(ds), 1)

    def test_legacy_trace_clipping_is_off_by_default(self):
        core = DissipativeCore(n=30, Dn=2.0, seed=3)
        unclipped = core.legacy_rad_trace(steps=30, burn_in=5, clip=False)
        core2 = DissipativeCore(n=30, Dn=2.0, seed=3)
        clipped = core2.legacy_rad_trace(steps=30, burn_in=5, clip=True)
        self.assertTrue(all(row[3] <= 2.0 for row in clipped))
        self.assertGreater(max(row[3] for row in unclipped), 2.0)


# ---------------------------------------------------------------------------
# bounds -- TUR / KUR
# ---------------------------------------------------------------------------

class TestBounds(unittest.TestCase):
    def test_precision_definition(self):
        self.assertAlmostEqual(bounds.precision(10.0, 4.0), 5.0)

    def test_tur_floor_and_ceiling_are_inverses(self):
        floor = bounds.tur_entropy_floor(100.0, 4.0)
        self.assertAlmostEqual(bounds.tur_precision_ceiling(floor),
                               bounds.precision(100.0, 4.0), places=6)

    def test_more_precision_costs_more_entropy(self):
        loose = bounds.tur_entropy_floor(10.0, 4.0)
        tight = bounds.tur_entropy_floor(100.0, 4.0)
        self.assertGreater(tight, loose)

    def test_energy_floor_scales_with_temperature(self):
        cold = bounds.tur_dissipated_energy_floor(100.0, 4.0, 100.0)
        hot = bounds.tur_dissipated_energy_floor(100.0, 4.0, 300.0)
        self.assertAlmostEqual(hot / cold, 3.0, places=9)

    def test_kur_activity_floor(self):
        self.assertAlmostEqual(bounds.kur_activity_floor(100.0, 4.0), 2500.0)

    def test_combined_ceiling_takes_the_tighter_bound(self):
        result = bounds.combined_precision_ceiling(sigma_total=1e-19, activity=1.0)
        self.assertEqual(result["binding"], "KUR")
        self.assertAlmostEqual(result["ceiling"], 1.0)

    def test_regime_check_flags_non_ness(self):
        self.assertIsNone(bounds.tur_valid_regime(True, True, True))
        self.assertIn("steady state", bounds.tur_valid_regime(False, True, True))
        self.assertIn("driving", bounds.tur_valid_regime(True, False, True))
        self.assertIn("Markov", bounds.tur_valid_regime(True, True, False))

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            bounds.precision(1.0, 0.0)
        with self.assertRaises(ValueError):
            bounds.tur_precision_ceiling(-1.0)


# ---------------------------------------------------------------------------
# landauer -- NEG-3
# ---------------------------------------------------------------------------

class TestLandauer(unittest.TestCase):
    def test_landauer_floor_value(self):
        self.assertAlmostEqual(landauer.landauer_floor(300.0),
                               landauer.KB * 300.0 * math.log(2.0))

    def test_cost_exceeds_floor_and_converges_to_it(self):
        floor = landauer.landauer_floor(300.0)
        fast = landauer.erase_cost(300.0, 1e-3, 1e-22)
        slow = landauer.erase_cost(300.0, 1e3, 1e-22)
        self.assertGreater(fast, slow)
        self.assertGreater(slow, floor)
        self.assertAlmostEqual(slow / floor, 1.0, places=3)

    def test_excess_exponent_is_minus_one(self):
        taus = [1e-3, 1e-2, 1e-1, 1.0, 10.0]
        fit = landauer.fit_excess_exponent(taus, [landauer.excess(t, 3.0) for t in taus])
        self.assertAlmostEqual(fit["exponent"], -1.0, places=9)
        self.assertAlmostEqual(fit["r_squared"], 1.0, places=9)

    def test_excess_power_exponent_is_minus_two(self):
        taus = [1e-3, 1e-2, 1e-1, 1.0]
        fit = landauer.fit_excess_exponent(taus, [landauer.excess_power(t, 3.0) for t in taus])
        self.assertAlmostEqual(fit["exponent"], -2.0, places=9)

    def test_flat_series_fits_exponent_zero(self):
        """The NEG-3 falsifier's dead case: resurfacing flat in tau."""
        taus = [1.0, 2.0, 4.0, 8.0]
        fit = landauer.fit_excess_exponent(taus, [5.0] * 4)
        self.assertAlmostEqual(fit["exponent"], 0.0, places=9)

    def test_protocol_constant_units_close(self):
        # C = k_B T W2^2 / D has units of energy*time, so C/tau is an energy.
        c = landauer.protocol_constant(1e-7, 1e-12, 300.0)
        self.assertGreater(c, 0.0)
        self.assertAlmostEqual(landauer.excess(2.0, c), c / 2.0)

    def test_resurfacing_rate_scales_inversely(self):
        self.assertAlmostEqual(landauer.resurfacing_rate(2.0, k=6.0), 3.0)

    def test_fit_requires_enough_distinct_points(self):
        with self.assertRaises(ValueError):
            landauer.fit_excess_exponent([1.0, 2.0], [1.0, 0.5])
        with self.assertRaises(ValueError):
            landauer.fit_excess_exponent([2.0, 2.0, 2.0], [1.0, 1.0, 1.0])


# ---------------------------------------------------------------------------
# maintenance -- NEG-2
# ---------------------------------------------------------------------------

class TestMaintenance(unittest.TestCase):
    def test_no_care_gives_budget_over_sigma(self):
        self.assertAlmostEqual(maintenance.archive_lifetime(1.0, 0.5, 0.0, 300.0), 2.0)

    def test_care_extends_lifetime(self):
        low = maintenance.archive_lifetime(1e-3, 1e-9, 0.0, 293.0)
        high = maintenance.archive_lifetime(1e-3, 1e-9, 1e-7, 293.0)
        self.assertGreater(high, low)

    def test_steady_state_care_gives_indefinite_lifetime(self):
        care = maintenance.steady_state_care(1e-9, 293.0)
        self.assertIsNone(maintenance.archive_lifetime(1e-3, 1e-9, care, 293.0))
        self.assertIsNone(maintenance.archive_lifetime(1e-3, 1e-9, care * 2, 293.0))

    def test_lifetime_ratio_is_none_when_either_is_indefinite(self):
        care = maintenance.steady_state_care(1e-9, 293.0)
        self.assertIsNone(maintenance.lifetime_ratio(1e-3, 1e-9, 0.0, care, 293.0))

    def test_lifetime_ratio_prediction(self):
        # NEG-2: the ratio is set by (sigma - W/T), not by the material.
        ratio = maintenance.lifetime_ratio(1e-3, 1e-9, 0.0, 1e-7, 293.0)
        self.assertIsNotNone(ratio)
        self.assertLess(ratio, 1.0)

    def test_expanding_schedule_shape(self):
        offsets, intervals = maintenance.expanding_schedule(1.0, 6, ratio=2.0)
        self.assertEqual(len(offsets), 6)
        self.assertEqual(len(intervals), 5)
        self.assertAlmostEqual(offsets[0], 0.0)
        self.assertEqual(intervals, [1.0, 2.0, 4.0, 8.0, 16.0])

    def test_ratio_one_is_uniform(self):
        _, intervals = maintenance.expanding_schedule(3.0, 5, ratio=1.0)
        self.assertEqual(intervals, [3.0] * 4)

    def test_fit_recovers_the_generating_ratio(self):
        _, intervals = maintenance.expanding_schedule(1.0, 9, ratio=maintenance.PHI)
        fit = maintenance.fit_ratio(intervals)
        self.assertAlmostEqual(fit["ratio"], maintenance.PHI, places=9)
        self.assertFalse(bool(fit["excludes_phi"]))

    def test_fit_excludes_phi_for_uniform_spacing(self):
        fit = maintenance.fit_ratio([3.0, 3.05, 2.98, 3.02, 3.0])
        self.assertTrue(bool(fit["excludes_phi"]))

    def test_fit_needs_three_intervals(self):
        with self.assertRaises(ValueError):
            maintenance.fit_ratio([1.0, 2.0])


# ---------------------------------------------------------------------------
# persistence -- NEG-8
# ---------------------------------------------------------------------------

class TestPersistence(unittest.TestCase):
    def test_margin_sign_convention(self):
        self.assertAlmostEqual(persistence.persistence_margin(-3.0, 1.0), 2.0)
        self.assertAlmostEqual(persistence.persistence_margin(-0.5, 1.0), -0.5)

    def test_boundary_case_persists(self):
        self.assertTrue(persistence.persists(-1.0, 1.0))
        self.assertFalse(persistence.persists(-0.999, 1.0))

    def test_negative_sigma_rejected(self):
        with self.assertRaises(ValueError):
            persistence.persistence_margin(-1.0, -0.1)

    def test_required_export_matches_production(self):
        self.assertAlmostEqual(persistence.required_export_rate(0.4), 0.4)

    def test_sigma_conversion_to_watts_per_kelvin(self):
        self.assertAlmostEqual(persistence.sigma_to_watts_per_kelvin(1.0), persistence.KB)

    def test_sustained_deficit_respects_duration(self):
        margins = [1.0, -0.1, -0.2, -0.3, 1.0, -0.5, 1.0]
        self.assertEqual(persistence.sustained_deficit(margins, 1.0, 3.0), [(1, 4, 3.0)])
        self.assertEqual(persistence.sustained_deficit(margins, 1.0, 5.0), [])

    def test_sustained_deficit_catches_trailing_window(self):
        windows = persistence.sustained_deficit([1.0, -1.0, -1.0, -1.0], 1.0, 2.0)
        self.assertEqual(windows, [(1, 4, 3.0)])

    def test_relaxation_report_monotone(self):
        report = persistence.relaxation_report([1.0, 0.6, 0.36, 0.22])
        self.assertTrue(report["monotone"])
        self.assertTrue(report["fit_exponential_ok"])
        self.assertEqual(report["reversals"], [])

    def test_relaxation_report_flags_crossing(self):
        report = persistence.relaxation_report([1.0, 0.6, 0.7, 0.2])
        self.assertFalse(report["monotone"])
        self.assertFalse(report["fit_exponential_ok"])
        self.assertEqual(report["reversals"], [2])
        self.assertAlmostEqual(report["largest_reversal"], 0.1)

    def test_tolerance_suppresses_noise_but_not_crossings(self):
        noisy = [1.0, 0.6, 0.6001, 0.2]
        self.assertTrue(persistence.relaxation_report(noisy, tolerance=0.01)["monotone"])
        self.assertFalse(persistence.relaxation_report(noisy, tolerance=0.0)["monotone"])


# ---------------------------------------------------------------------------
# lenses and the NEG-7 falsifier
# ---------------------------------------------------------------------------

class TestLenses(unittest.TestCase):
    def test_registry_has_seventeen(self):
        self.assertEqual(len(LENS_REGISTRY), 17)

    def test_every_lens_is_callable_and_returns_a_number(self):
        for name, fn in LENS_REGISTRY.items():
            value = fn(0.5, 0.4, 0.3, 0.2)
            self.assertIsInstance(value, float, msg=name)

    def test_canonical_and_exceptions_partition_the_registry(self):
        self.assertEqual(set(LENS_COEFFICIENTS) | set(CANONICAL_FORM_EXCEPTIONS),
                         set(LENS_REGISTRY))
        self.assertFalse(set(LENS_COEFFICIENTS) & set(CANONICAL_FORM_EXCEPTIONS))

    def test_coefficients_reproduce_their_lenses(self):
        for name, coeffs in LENS_COEFFICIENTS.items():
            rebuilt = canonical_lens(*coeffs)
            for state in ((0.5, 0.4, 0.3, 0.2), (0.9, 0.1, 1.2, 0.05)):
                self.assertAlmostEqual(rebuilt(*state), LENS_REGISTRY[name](*state),
                                       places=10, msg=name)


class TestLensCollapse(unittest.TestCase):
    def setUp(self):
        core = DissipativeCore(n=40, K=1.5, Dn=0.045, dt=0.02, seed=42)
        self.trace = core.legacy_rad_trace(steps=120, burn_in=60)

    def test_pearson_matches_known_values(self):
        self.assertAlmostEqual(pearson([1, 2, 3], [2, 4, 6]), 1.0)
        self.assertAlmostEqual(pearson([1, 2, 3], [6, 4, 2]), -1.0)
        self.assertTrue(math.isnan(pearson([1, 1, 1], [1, 2, 3])))

    def test_random_lens_is_deterministic_under_a_seed(self):
        a = random_lens(random.Random(3))(0.5, 0.4, 0.3, 0.2)
        b = random_lens(random.Random(3))(0.5, 0.4, 0.3, 0.2)
        self.assertAlmostEqual(a, b)

    def test_named_floor_reports_a_pair(self):
        result = named_floor(self.trace)
        self.assertIn("vs", result["floor_pair"])
        self.assertEqual(int(result["n_pairs"]), 17 * 16 // 2)
        self.assertLessEqual(result["floor"], result["median"])

    def test_run_reports_the_absolute_statistic(self):
        result = run(self.trace, n_lenses=17, trials=40, seed=7)
        for key in ("median_floor", "worst_floor", "frac_above_0.88"):
            self.assertIn(key, result)
        self.assertGreaterEqual(result["frac_above_0.88"], 0.0)
        self.assertLessEqual(result["frac_above_0.88"], 1.0)
        self.assertLessEqual(result["worst_floor"], result["median_floor"])

    def test_named_lenses_are_indistinguishable_from_random_ones(self):
        """The NEG-7 result, in the form that does not depend on trace length.

        The absolute 0.88 rule moves with n and trace length because it
        measures the trajectory as well as the lenses. The matched
        comparison puts both arms on the same trace, and the named floor
        lands at or below the random median in every configuration tried.
        """
        for n, steps in ((30, 120), (40, 250), (50, 250)):
            core = DissipativeCore(n=n, K=1.5, Dn=0.045, dt=0.02, seed=42)
            trace = core.legacy_rad_trace(steps=steps, burn_in=60)
            result = compare(trace, n_lenses=17, trials=40, seed=7)
            self.assertLessEqual(result["named_percentile"], 0.9,
                                 msg=f"n={n} steps={steps}")
            self.assertLessEqual(result["named_floor"], result["random_median"],
                                 msg=f"n={n} steps={steps}")
            self.assertIn("DEAD", matched_verdict(result["named_percentile"]))

    def test_verdict_thresholds(self):
        self.assertIn("DEAD", verdict(0.95))
        self.assertIn("SURVIVES", verdict(0.1))
        self.assertIn("INCONCLUSIVE", verdict(0.5))

    def test_matched_verdict_thresholds(self):
        self.assertIn("DEAD", matched_verdict(0.4))
        self.assertIn("DEAD", matched_verdict(0.9))
        self.assertIn("INCONCLUSIVE", matched_verdict(0.95))
        self.assertIn("SURVIVES", matched_verdict(0.995))

    def test_run_rejects_short_traces(self):
        with self.assertRaises(ValueError):
            run(self.trace[:2])
        with self.assertRaises(ValueError):
            compare(self.trace[:2])


# ---------------------------------------------------------------------------
# emit_ising
# ---------------------------------------------------------------------------

class TestEmitIsing(unittest.TestCase):
    def setUp(self):
        self.core = DissipativeCore(n=12, K=1.5, Dn=0.045, dt=0.02, seed=4)
        self.spec = from_core(self.core)

    def test_spec_shape_and_symmetry(self):
        self.assertEqual(self.spec.n, 12)
        self.assertEqual(len(self.spec.biases), 12)
        for i in range(12):
            self.assertAlmostEqual(self.spec.couplings[i][i], 0.0)
            for k in range(12):
                self.assertAlmostEqual(self.spec.couplings[i][k],
                                       self.spec.couplings[k][i])

    def test_spec_validates_dimensions(self):
        with self.assertRaises(ValueError):
            IsingSpec(n=2, couplings=[[0.0, 1.0]], biases=[0.0, 0.0])
        with self.assertRaises(ValueError):
            IsingSpec(n=2, couplings=[[0.0, 1.0], [1.0, 0.0]], biases=[0.0])
        with self.assertRaises(ValueError):
            IsingSpec(n=2, couplings=[[0.0, 1.0], [1.0, 0.0]],
                      biases=[0.0, 0.0], beta=0.0)

    def test_energy_of_aligned_ferromagnet(self):
        spec = IsingSpec(n=2, couplings=[[0.0, 1.0], [1.0, 0.0]], biases=[0.0, 0.0])
        self.assertAlmostEqual(energy(spec, [1, 1]), -1.0)
        self.assertAlmostEqual(energy(spec, [1, -1]), 1.0)

    def test_energy_rejects_wrong_length(self):
        with self.assertRaises(ValueError):
            energy(self.spec, [1, -1])

    def test_annealing_does_not_increase_best_energy(self):
        start = [1, -1] * 6
        result = anneal(self.spec, sweeps=150, spins=start, seed=2)
        self.assertLessEqual(result["best_energy"], energy(self.spec, start))
        self.assertGreaterEqual(result["flips"], 0)
        self.assertEqual(len(result["best_spins"]), 12)

    def test_cold_sweep_is_greedy(self):
        spins = [1, -1] * 6
        before = energy(self.spec, list(spins))
        for _ in range(50):
            pbit_sweep(self.spec, spins, random.Random(0), beta=200.0)
        self.assertLess(energy(self.spec, spins), before)

    def test_spins_to_bits(self):
        self.assertEqual(spins_to_bits([1, -1, 1, 1]), "1011")

    def test_octahedral_gray_is_single_bit_adjacent(self):
        codes = [phase_to_octahedral_gray(-math.pi + (k + 0.5) * math.pi / 4)
                 for k in range(8)]
        self.assertEqual(len(set(codes)), 8)
        for a, b in zip(codes, codes[1:] + codes[:1]):
            self.assertEqual(bin(a ^ b).count("1"), 1)

    def test_octahedral_bits_width(self):
        for theta in (-3.0, -1.0, 0.0, 1.0, 3.0, 9.0):
            self.assertEqual(len(octahedral_bits(theta)), 3)

    def test_flip_cost_floor_scales_with_flips(self):
        one = flip_cost_floor(1, 300.0)
        self.assertAlmostEqual(one, landauer.landauer_floor(300.0))
        self.assertAlmostEqual(flip_cost_floor(1000, 300.0), 1000 * one)
        with self.assertRaises(ValueError):
            flip_cost_floor(-1, 300.0)


# ---------------------------------------------------------------------------
# rebase -- NEG-4, NEG-9, NEG-10, NEG-11
# ---------------------------------------------------------------------------

def _chain(n, validated=2020):
    """Archive shaped as a chain: c0 <- c1 <- ... <- c(n-1)."""
    a = Archive()
    a.add("c0", validated=validated)
    for i in range(1, n):
        a.radiate(f"c{i}", rests_on=[f"c{i-1}"], validated=validated)
    return a


def _star(n, validated=2020):
    """Archive shaped as a star: every leaf rests directly on s0."""
    a = Archive()
    a.add("s0", validated=validated)
    for i in range(1, n):
        a.radiate(f"s{i}", rests_on=["s0"], validated=validated)
    return a


class TestArchiveConstruction(unittest.TestCase):
    def test_first_added_node_becomes_center(self):
        a = Archive()
        a.add("only")
        self.assertEqual(a.center, "only")

    def test_unknown_parents_are_created_unvalidated(self):
        a = Archive()
        a.add("top", rests_on=["implied"], validated=2020)
        self.assertIn("implied", a.dep)
        self.assertEqual(a.validated["implied"], 0)

    def test_self_dependency_rejected(self):
        a = Archive()
        with self.assertRaises(ValueError):
            a.add("x", rests_on=["x"])

    def test_foundations_are_nodes_with_no_dependencies(self):
        a = _chain(4)
        self.assertEqual(a.foundations(), {"c0"})
        self.assertEqual(_star(4).foundations(), {"s0"})

    def test_readding_updates_validation_epoch(self):
        a = Archive()
        a.add("x", validated=1900)
        a.add("x", validated=2020)
        self.assertEqual(a.validated["x"], 2020)


class TestRadiate(unittest.TestCase):
    """NEG-4, operation 1: cheap, local, cannot move the base."""

    def test_radiate_requires_existing_parents(self):
        a = _chain(2)
        with self.assertRaises(KeyError):
            a.radiate("new", rests_on=["nonexistent"])

    def test_radiate_requires_at_least_one_parent(self):
        a = _chain(2)
        with self.assertRaises(ValueError):
            a.radiate("new", rests_on=[])

    def test_radiate_rejects_existing_node(self):
        a = _chain(3)
        with self.assertRaises(ValueError):
            a.radiate("c1", rests_on=["c0"])

    def test_radiate_never_moves_the_base(self):
        a = _chain(4)
        base_before, center_before = a.foundations(), a.center
        a.radiate("leaf", rests_on=["c2"], validated=2020)
        self.assertEqual(a.foundations(), base_before)
        self.assertEqual(a.center, center_before)

    def test_radiate_reports_depth(self):
        a = _chain(4)
        self.assertEqual(a.radiate("leaf", rests_on=["c2"])["depth"], 3)


class TestRecenter(unittest.TestCase):
    """NEG-4, operation 2: reverse every edge on paths v -> center."""

    def test_recenter_reverses_the_path_and_moves_the_base(self):
        a = Archive()
        a.add("T1", validated=1850)
        a.add("T2", rests_on=["T1"], validated=1900)
        a.add("T3", rests_on=["T2"], validated=1960)
        a.radiate("T4", rests_on=["T2"], validated=2010)

        result = a.recenter("T4", now=2026, v_max_gap=90)
        self.assertEqual(result["status"], "OK")
        self.assertEqual(result["work"], 2)
        self.assertEqual(result["from"], "T1")
        self.assertEqual(result["to"], "T4")
        self.assertEqual(a.foundations(), {"T4"})

    def test_recenter_cost_predicts_work(self):
        a = _chain(6)
        predicted = a.recenter_cost("c5")
        self.assertEqual(a.recenter("c5", now=2026)["work"], predicted)

    def test_recentering_on_the_center_is_free(self):
        a = _chain(5)
        self.assertEqual(a.recenter(a.center, now=2026)["work"], 0)

    def test_recenter_is_involutive_in_shape(self):
        a = _chain(5)
        original = {n: set(d) for n, d in a.dep.items()}
        a.recenter("c4", now=2026)
        a.recenter("c0", now=2026)
        self.assertEqual(a.dep, original)

    def test_recenter_unknown_node_raises(self):
        with self.assertRaises(KeyError):
            _chain(3).recenter("absent")

    def test_recenter_records_history(self):
        a = _chain(5)
        a.recenter("c4", now=2026)
        a.recenter("c0", now=2027)
        self.assertEqual(len(a.history), 2)
        self.assertEqual(a.mean_recenter_cost(), 4.0)

    def test_mean_cost_is_none_before_any_recenter(self):
        self.assertIsNone(_chain(3).mean_recenter_cost())


class TestContradictionDetection(unittest.TestCase):
    """NEG-9: a cycle after inversion means one of the claims is wrong."""

    def test_inversion_closing_a_loop_is_reported_not_stored(self):
        a = Archive()
        a.add("ground", validated=2020)
        a.add("mid", rests_on=["ground"], validated=2020)
        a.add("top", rests_on=["mid", "ground"], validated=2020)

        before = {n: set(d) for n, d in a.dep.items()}
        result = a.invert("top", "ground")

        self.assertEqual(result["status"], "CONTRADICTION")
        self.assertIn("ground", result["cycle"])
        self.assertEqual(result["cycle"][0], result["cycle"][-1])
        self.assertEqual(a.dep, before)

    def test_safe_inversion_succeeds_and_flips_the_edge(self):
        a = Archive()
        a.add("b", validated=2020)
        a.add("a", rests_on=["b"], validated=2020)
        self.assertEqual(a.invert("a", "b")["status"], "OK")
        self.assertIn("a", a.dep["b"])
        self.assertNotIn("b", a.dep["a"])

    def test_inverting_a_missing_edge_reports_no_edge(self):
        a = _chain(3)
        self.assertEqual(a.invert("c0", "c2")["status"], "NO_EDGE")

    def test_cycle_report_is_reproducible(self):
        results = []
        for _ in range(3):
            a = Archive()
            a.add("ground", validated=2020)
            a.add("mid", rests_on=["ground"], validated=2020)
            a.add("top", rests_on=["mid", "ground"], validated=2020)
            results.append(tuple(a.invert("top", "ground")["cycle"]))
        self.assertEqual(len(set(results)), 1)

    def test_no_cycle_in_a_well_formed_archive(self):
        self.assertIsNone(_chain(6)._cycle())
        self.assertIsNone(_star(6)._cycle())


class TestTopology(unittest.TestCase):
    """NEG-10: recenter cost scales with depth, so depth is under pressure."""

    def test_chain_is_deep_and_star_is_wide(self):
        chain, star = _chain(8).topology(), _star(8).topology()
        self.assertEqual(chain["depth"], 7.0)
        self.assertEqual(chain["width"], 1.0)
        self.assertEqual(star["depth"], 1.0)
        self.assertEqual(star["width"], 7.0)
        self.assertGreater(chain["aspect"], star["aspect"])

    def test_recenter_cost_tracks_depth(self):
        self.assertEqual(_chain(8).recenter_cost("c7"), 7)
        self.assertEqual(_star(8).recenter_cost("s7"), 1)

    def test_deeper_archives_cost_more_to_reroot(self):
        costs = [_chain(n).recenter_cost(f"c{n-1}") for n in (3, 5, 9)]
        for earlier, later in zip(costs, costs[1:]):
            self.assertLess(earlier, later)

    def test_depth_of_a_foundation_is_zero(self):
        self.assertEqual(_chain(5).depth_of("c0"), 0)

    def test_depth_takes_the_longest_path(self):
        a = Archive()
        a.add("base", validated=2020)
        a.radiate("short", rests_on=["base"], validated=2020)
        a.radiate("mid", rests_on=["base"], validated=2020)
        a.radiate("long", rests_on=["mid"], validated=2020)
        a.radiate("join", rests_on=["short", "long"], validated=2020)
        self.assertEqual(a.depth_of("join"), 3)

    def test_empty_archive_topology(self):
        self.assertEqual(Archive().topology()["nodes"], 0.0)


class TestValidationGate(unittest.TestCase):
    """NEG-11: an unconfirmed claim cannot become the base."""

    def test_stale_node_is_refused_as_base(self):
        a = Archive()
        a.add("T1", validated=1850)
        a.add("T2", rests_on=["T1"], validated=2010)
        a.recenter("T2", now=2026, v_max_gap=90)

        result = a.recenter("T1", now=2026, v_max_gap=90)
        self.assertEqual(result["status"], "V_GATE")
        self.assertEqual(result["gap"], 176)
        self.assertEqual(result["limit"], 90)
        self.assertEqual(a.center, "T2")

    def test_fresh_node_passes_the_gate(self):
        a = _chain(3, validated=2020)
        self.assertEqual(a.recenter("c2", now=2026, v_max_gap=90)["status"], "OK")

    def test_gate_is_off_when_no_limit_given(self):
        a = Archive()
        a.add("ancient", validated=1000)
        a.add("recent", rests_on=["ancient"], validated=2020)
        a.recenter("recent", now=2026)
        self.assertEqual(a.recenter("ancient", now=2026)["status"], "OK")

    def test_validation_gap_and_base_gap(self):
        a = Archive()
        a.add("old", validated=1900)
        a.add("new", rests_on=["old"], validated=2020)
        self.assertEqual(a.validation_gap("old", 2026), 126)
        self.assertEqual(a.base_validation_gap(2026), 126)
        a.recenter("new", now=2026)
        self.assertEqual(a.base_validation_gap(2026), 6)

    def test_base_gap_of_empty_archive_is_none(self):
        self.assertIsNone(Archive().base_validation_gap(2026))


# ---------------------------------------------------------------------------
# precession -- dating a sky datum and its re-datum interval
# ---------------------------------------------------------------------------

def _ecl(name):
    return equatorial_to_ecliptic(*CATALOG[name])


class TestPrecessionModel(unittest.TestCase):
    """Validated against the three standard pole-star epochs."""

    def test_polaris_closest_approach(self):
        year, sep = closest_approach(*_ecl("Polaris"), near_year=2000)
        self.assertAlmostEqual(year, 2100, delta=40)
        self.assertAlmostEqual(sep, 0.45, delta=0.1)

    def test_thuban_closest_approach(self):
        year, sep = closest_approach(*_ecl("Thuban"), near_year=0)
        self.assertAlmostEqual(year, -2750, delta=120)
        self.assertLess(sep, 0.5)

    def test_vega_late_glacial(self):
        year, sep = closest_approach(*_ecl("Vega"), near_year=-12000)
        self.assertAlmostEqual(year, -12000, delta=200)
        self.assertAlmostEqual(sep, 4.8, delta=0.6)

    def test_closest_approach_is_periodic(self):
        lam, beta = _ecl("Vega")
        past, _ = closest_approach(lam, beta, near_year=-12000)
        future, _ = closest_approach(lam, beta, near_year=14000)
        self.assertAlmostEqual(future - past, PRECESSION_PERIOD, delta=1.0)

    def test_pole_longitude_advances_uniformly(self):
        self.assertAlmostEqual(pole_ecliptic_longitude(2000), 90.0, places=9)
        one_degree = drift_years_per_degree()
        self.assertAlmostEqual(one_degree, 71.6, delta=0.1)
        self.assertAlmostEqual(pole_ecliptic_longitude(2000 + one_degree), 89.0,
                               places=6)

    def test_pole_returns_after_one_full_cycle(self):
        lam, beta = _ecl("Thuban")
        now = separation_from_pole(lam, beta, 2000)
        later = separation_from_pole(lam, beta, 2000 + PRECESSION_PERIOD)
        self.assertAlmostEqual(now, later, places=6)

    def test_minimum_separation_matches_ecliptic_latitude_gap(self):
        for name in CATALOG:
            lam, beta = _ecl(name)
            _, sep = closest_approach(lam, beta)
            self.assertAlmostEqual(sep, abs(beta - POLE_ECLIPTIC_LATITUDE),
                                   places=9, msg=name)

    def test_ecliptic_conversion_of_the_ecliptic_pole(self):
        # RA 18h, Dec 90 - obliquity is the north ecliptic pole: beta = 90.
        lam, beta = equatorial_to_ecliptic(270.0, 90.0 - OBLIQUITY)
        self.assertAlmostEqual(beta, 90.0, delta=1e-4)

    def test_declination_is_ninety_minus_polar_distance(self):
        lam, beta = _ecl("Polaris")
        self.assertAlmostEqual(declination_at(lam, beta, 2000),
                               CATALOG["Polaris"][1], delta=0.05)


class TestAlignmentWindow(unittest.TestCase):
    """The window is both a dating method and a re-datum interval."""

    def test_window_brackets_the_closest_approach(self):
        lam, beta = _ecl("Polaris")
        window = alignment_window(lam, beta, tolerance=1.0)
        self.assertLess(window["start"], window["center"])
        self.assertLess(window["center"], window["end"])
        self.assertAlmostEqual(window["duration"],
                               window["end"] - window["start"], places=6)

    def test_looser_tolerance_gives_a_longer_window(self):
        lam, beta = _ecl("Polaris")
        durations = [alignment_window(lam, beta, t)["duration"]
                     for t in (0.5, 1.0, 2.0, 4.0)]
        for earlier, later in zip(durations, durations[1:]):
            self.assertLess(earlier, later)

    def test_tolerance_below_minimum_separation_has_no_window(self):
        lam, beta = _ecl("Vega")           # never closer than ~4.8 degrees
        self.assertIsNone(alignment_window(lam, beta, tolerance=1.0))
        self.assertIsNotNone(alignment_window(lam, beta, tolerance=6.0))

    def test_separation_stays_within_tolerance_across_the_window(self):
        lam, beta = _ecl("Thuban")
        window = alignment_window(lam, beta, tolerance=1.0, near_year=0)
        for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
            year = window["start"] + frac * window["duration"]
            self.assertLessEqual(separation_from_pole(lam, beta, year), 1.0 + 1e-6)

    def test_separation_exceeds_tolerance_just_outside_the_window(self):
        lam, beta = _ecl("Thuban")
        window = alignment_window(lam, beta, tolerance=1.0, near_year=0)
        for year in (window["start"] - 50, window["end"] + 50):
            self.assertGreater(separation_from_pole(lam, beta, year), 1.0)

    def test_redatum_interval_is_generations_not_millennia(self):
        """The point of NEG-4 at archive scale: the base needs re-establishing."""
        lam, beta = _ecl("Polaris")
        self.assertLess(alignment_window(lam, beta, 0.5)["duration"], 200)

    def test_rejects_nonpositive_tolerance(self):
        lam, beta = _ecl("Polaris")
        with self.assertRaises(ValueError):
            alignment_window(lam, beta, tolerance=0.0)


class TestCircumpolarity(unittest.TestCase):
    """Whether the Bear never sets depends on the epoch, not only the latitude."""

    def test_alkaid_limiting_latitude_today(self):
        lam, beta = _ecl("Alkaid")
        self.assertAlmostEqual(limiting_latitude(lam, beta, 2000), 40.7, delta=0.3)

    def test_alkaid_limiting_latitude_late_glacial_is_higher(self):
        lam, beta = _ecl("Alkaid")
        now = limiting_latitude(lam, beta, 2000)
        glacial = limiting_latitude(lam, beta, -12000)
        self.assertGreater(glacial, now)
        self.assertAlmostEqual(glacial, 47.8, delta=1.0)

    def test_circumpolar_iff_separation_below_latitude(self):
        lam, beta = _ecl("Alkaid")
        for year in (2000, -6000, -12000):
            sep = separation_from_pole(lam, beta, year)
            self.assertTrue(is_circumpolar(lam, beta, sep + 1.0, year))
            self.assertFalse(is_circumpolar(lam, beta, sep - 1.0, year))

    def test_bear_stays_circumpolar_at_glacial_margin_latitude(self):
        """True, but the margin at 14000 BCE is under a degree."""
        lam, beta = _ecl("Alkaid")
        for year in (-10000, -12000, -14000):
            self.assertTrue(is_circumpolar(lam, beta, 55.0, year))
        self.assertLess(55.0 - limiting_latitude(lam, beta, -14000), 1.0)

    def test_pointer_stars_are_closer_to_the_pole_than_alkaid(self):
        alkaid = separation_from_pole(*_ecl("Alkaid"), year=2000)
        dubhe = separation_from_pole(*_ecl("Dubhe"), year=2000)
        self.assertLess(dubhe, alkaid)


if __name__ == "__main__":
    unittest.main()
