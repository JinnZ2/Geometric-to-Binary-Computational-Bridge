"""Tests for the numpy tier of Negentropic/.

Covers negentropic_engine.py and the Fokker-Planck integrator in
negentropic_dynamics.py. The stdlib tier has its own suite in
test_negentropic_stdlib.py, which runs without numpy installed.
"""

import unittest
import sys
import os
from datetime import date

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from Negentropic.negentropic_dynamics import FokkerPlanck1D, spurious_drift
from Negentropic.negentropic_engine import (
    compute_resonance,
    compute_adaptability,
    compute_diversity,
    compute_loss,
    compute_M,
    GeometricAgent,
    GeometricNetwork,
    fibonacci_schedule,
)


class TestCoreCalculations(unittest.TestCase):
    def setUp(self):
        self.patterns = np.array([0.5, 1.2, 0.8, 1.5, 0.3])
        self.signals = np.array([1.0, 0.8, 1.2, 0.9, 1.1])

    def test_compute_resonance_returns_float(self):
        r = compute_resonance(self.patterns, self.signals)
        self.assertIsInstance(float(r), float)

    def test_compute_resonance_positive(self):
        r = compute_resonance(self.patterns, self.signals)
        self.assertGreater(r, 0)

    def test_compute_adaptability_returns_float_in_range(self):
        a = compute_adaptability(self.patterns, alpha=1.0)
        self.assertIsInstance(float(a), float)
        self.assertGreaterEqual(a, 0.0)
        self.assertLessEqual(a, 1.0)

    def test_compute_diversity_returns_nonnegative(self):
        d = compute_diversity(self.patterns)
        self.assertIsInstance(float(d), float)
        self.assertGreaterEqual(d, 0.0)

    def test_compute_diversity_identical_is_zero(self):
        d = compute_diversity(np.array([1.0, 1.0, 1.0]))
        self.assertAlmostEqual(d, 0.0)

    def test_compute_loss_returns_nonnegative(self):
        a = compute_adaptability(self.patterns, alpha=1.0)
        loss = compute_loss(0.05, a, 0.1)
        self.assertIsInstance(float(loss), float)
        self.assertGreaterEqual(loss, 0.0)

    def test_compute_M_returns_tuple(self):
        result = compute_M(self.patterns, self.signals, alpha=1.0,
                           noise_power=0.05, lambda_param=0.1)
        self.assertEqual(len(result), 5)
        M, R_e, A, D, L = result
        for val in result:
            self.assertIsInstance(float(val), float)

    def test_compute_M_components_consistent(self):
        M, R_e, A, D, L = compute_M(self.patterns, self.signals, alpha=1.0,
                                      noise_power=0.05, lambda_param=0.1)
        expected_M = (R_e * A * D) - L
        self.assertAlmostEqual(float(M), float(expected_M), places=10)


class TestGeometricAgent(unittest.TestCase):
    def test_agent_creation(self):
        agent = GeometricAgent(dim=3, signal_strength=1.0)
        self.assertEqual(agent.dim, 3)
        self.assertEqual(agent.signal, 1.0)
        self.assertEqual(len(agent.pattern), 3)

    def test_update_curiosity_respects_cmax(self):
        agent = GeometricAgent(dim=3, signal_strength=1.0)
        agent.C = 99.0
        agent.R_e = 10.0
        agent.update_curiosity(alpha_0=1.0, E=2.0, E_crit=1.0, C_max=100.0)
        self.assertLessEqual(agent.C, 100.0)

    def test_update_curiosity_no_growth_below_ecrit(self):
        agent = GeometricAgent(dim=3, signal_strength=1.0)
        initial_C = agent.C
        agent.R_e = 1.0
        agent.update_curiosity(alpha_0=1.0, E=0.5, E_crit=1.0, C_max=100.0)
        # alpha=0 when E < E_crit, so C = C * (1 + 0) = C
        self.assertAlmostEqual(agent.C, initial_C)

    def test_couple_with_returns_float(self):
        a = GeometricAgent(dim=3, signal_strength=1.0)
        b = GeometricAgent(dim=3, signal_strength=1.0)
        val = a.couple_with(b, alpha=1.0)
        self.assertIsInstance(float(val), float)

    def test_compute_joy_returns_float(self):
        agent = GeometricAgent(dim=3, signal_strength=1.0)
        joy = agent.compute_joy(diversity=0.5)
        self.assertIsInstance(float(joy), float)


class TestGeometricNetwork(unittest.TestCase):
    def test_network_creation(self):
        net = GeometricNetwork(n_agents=4, dim=3)
        self.assertEqual(len(net.agents), 4)

    def test_step_returns_float(self):
        net = GeometricNetwork(n_agents=3, dim=2)
        M = net.step(alpha=1.0, beta=0.1, alpha_0=0.5, E=2.0)
        self.assertIsInstance(float(M), float)

    def test_history_populated_after_steps(self):
        net = GeometricNetwork(n_agents=3, dim=2)
        for _ in range(5):
            net.step()
        self.assertEqual(len(net.history["M"]), 5)
        self.assertEqual(len(net.history["R_e"]), 5)


class TestCorrectedKernels(unittest.TestCase):
    """Regressions for the defects listed in Negentropic/corrections.md."""

    def test_resonance_wraps_phase_differences(self):
        """corrections.md §5: the cosine kernel must be single-valued."""
        signals = np.array([1.0, 1.0])
        near = compute_resonance(np.array([0.0, 0.3]), signals)
        far = compute_resonance(np.array([0.0, 0.3 + 2 * np.pi]), signals)
        self.assertAlmostEqual(float(near), float(far), places=10)

    def test_adaptability_is_monotone_in_separation(self):
        """A Euclidean distance must not wrap: further apart is always weaker."""
        signals_free = [
            compute_adaptability(np.array([0.0, d]), alpha=1.0)
            for d in (0.0, 1.0, np.pi, 2 * np.pi, 4 * np.pi)
        ]
        for earlier, later in zip(signals_free, signals_free[1:]):
            self.assertGreater(earlier, later)

    def test_adaptability_accepts_vector_patterns(self):
        patterns = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])
        a = compute_adaptability(patterns, alpha=1.0)
        self.assertGreater(a, 0.0)
        self.assertLessEqual(a, 1.0)

    def test_adaptability_rejects_nonpositive_alpha(self):
        with self.assertRaises(ValueError):
            compute_adaptability(np.array([0.0, 1.0]), alpha=0.0)

    def test_coupling_decays_with_distance(self):
        a = GeometricAgent(dim=2, signal_strength=1.0)
        b = GeometricAgent(dim=2, signal_strength=1.0)
        a.pattern = np.array([0.0, 0.0])
        values = []
        for d in (0.0, 1.0, 2 * np.pi, 4 * np.pi):
            b.pattern = np.array([d, 0.0])
            values.append(a.couple_with(b, alpha=1.0))
        for earlier, later in zip(values, values[1:]):
            self.assertGreater(earlier, later)

    def test_curiosity_saturates_asymptotically(self):
        """corrections.md §9: the old form pinned C to C_max within a few steps."""
        agent = GeometricAgent(dim=3, signal_strength=1.0)
        agent.C = 1.0
        agent.R_e = 1.0
        for _ in range(5):
            agent.update_curiosity(alpha_0=0.5, E=2.0, C_max=100.0)
        self.assertLess(agent.C, 100.0)
        self.assertGreater(agent.C, 1.0)

    def test_curiosity_never_exceeds_cmax(self):
        agent = GeometricAgent(dim=3, signal_strength=1.0)
        agent.C = 1.0
        agent.R_e = 5.0
        for _ in range(500):
            agent.update_curiosity(alpha_0=1.0, E=2.0, C_max=10.0)
        self.assertLessEqual(agent.C, 10.0)

    def test_network_adaptability_is_not_resonance(self):
        """corrections.md §8: A was set equal to avg R_e, collapsing M."""
        net = GeometricNetwork(n_agents=6, dim=3)
        net.step()
        patterns = np.array([a.pattern for a in net.agents])
        a = compute_adaptability(patterns, alpha=1.0)
        avg_r_e = float(np.mean([agent.R_e for agent in net.agents]))
        self.assertNotAlmostEqual(a, avg_r_e, places=6)

    def test_network_loss_responds_to_exploration(self):
        """corrections.md §8: L was the constant 0.1; it now tracks injected noise."""
        quiet = GeometricNetwork(n_agents=5, dim=3)
        loud = GeometricNetwork(n_agents=5, dim=3)
        for agent in loud.agents:
            agent.C = 20.0
        quiet.step(beta=0.01)
        loud.step(beta=0.5)
        self.assertGreater(loud.history["L"][-1], quiet.history["L"][-1])
        self.assertNotAlmostEqual(quiet.history["L"][-1], 0.1)

    def test_network_records_all_components(self):
        net = GeometricNetwork(n_agents=4, dim=2)
        for _ in range(3):
            net.step()
        for key in ("M", "R_e", "C", "J", "A", "D", "L"):
            self.assertEqual(len(net.history[key]), 3, msg=key)


class TestFokkerPlanck(unittest.TestCase):
    """corrections.md §2 and §4: the equation form and probability conservation."""

    def _relax(self, d_coeff, steps=20000, **kwargs):
        fp = FokkerPlanck1D(n_grid=128, dt=0.0005, **kwargs)
        for _ in range(steps):
            fp.step(-fp.x, d_coeff)
        return fp

    def test_recovers_ornstein_uhlenbeck_variance(self):
        for d in (0.5, 0.1):
            fp = self._relax(d)
            variance = float(np.trapezoid(fp.p * fp.x ** 2, fp.x))
            self.assertAlmostEqual(variance, d, delta=0.01 * d + 0.002)

    def test_collapse_as_diffusion_vanishes(self):
        wide = self._relax(0.5)
        narrow = self._relax(0.01)
        var_wide = float(np.trapezoid(wide.p * wide.x ** 2, wide.x))
        var_narrow = float(np.trapezoid(narrow.p * narrow.x ** 2, narrow.x))
        self.assertLess(var_narrow, var_wide)
        self.assertLess(narrow.entropy(), wide.entropy())

    def test_uniform_is_not_a_fixed_point(self):
        """The old scheme returned the uniform distribution unchanged forever."""
        fp = FokkerPlanck1D(n_grid=128, dt=0.0005)
        before = fp.p.copy()
        for _ in range(2000):
            fp.step(-fp.x, 0.5)
        self.assertGreater(float(np.max(np.abs(fp.p - before))), 1e-6)

    def test_probability_is_conserved(self):
        fp = FokkerPlanck1D(n_grid=128, dt=0.0005)
        for _ in range(1000):
            fp.step(-fp.x, 0.5)
            self.assertAlmostEqual(float(np.trapezoid(fp.p, fp.x)), 1.0, places=9)

    def test_density_stays_non_negative(self):
        fp = FokkerPlanck1D(n_grid=128, dt=0.0005)
        for _ in range(2000):
            fp.step(-fp.x, 0.1)
        self.assertGreaterEqual(float(np.min(fp.p)), 0.0)

    def test_conventions_differ_for_state_dependent_diffusion(self):
        profiles = {}
        for convention in ("ito", "stratonovich"):
            fp = FokkerPlanck1D(n_grid=128, dt=0.0005, convention=convention)
            d_profile = 0.1 + 0.4 * np.exp(-fp.x ** 2)
            for _ in range(20000):
                fp.step(-fp.x, d_profile)
            profiles[convention] = float(np.trapezoid(fp.p * fp.x ** 2, fp.x))
        self.assertNotAlmostEqual(profiles["ito"], profiles["stratonovich"], places=3)

    def test_conventions_agree_for_constant_diffusion(self):
        variances = []
        for convention in ("ito", "stratonovich"):
            fp = self._relax(0.5, convention=convention)
            variances.append(float(np.trapezoid(fp.p * fp.x ** 2, fp.x)))
        self.assertAlmostEqual(variances[0], variances[1], places=4)

    def test_rejects_bad_diffusion_input(self):
        fp = FokkerPlanck1D(n_grid=32)
        with self.assertRaises(ValueError):
            fp.step(-fp.x, np.ones(8))
        with self.assertRaises(ValueError):
            fp.step(-fp.x, -1.0)
        with self.assertRaises(ValueError):
            FokkerPlanck1D(convention="nonsense")

    def test_spurious_drift_is_half_the_gradient(self):
        x = np.linspace(0.0, 1.0, 101)
        dx = float(x[1] - x[0])
        drift = spurious_drift(3.0 * x, dx)
        self.assertTrue(np.allclose(drift[1:-1], 1.5, atol=1e-9))

    def test_spurious_drift_vanishes_for_constant_diffusion(self):
        drift = spurious_drift(np.full(50, 0.7), 0.1)
        self.assertTrue(np.allclose(drift, 0.0))


class TestFibonacciSchedule(unittest.TestCase):
    def test_returns_correct_length(self):
        start = date(2026, 1, 1)
        schedule, fib = fibonacci_schedule(start, 6)
        self.assertEqual(len(schedule), 6)
        self.assertGreaterEqual(len(fib), 6)

    def test_first_entry_is_start_date(self):
        start = date(2026, 1, 1)
        schedule, fib = fibonacci_schedule(start, 4)
        self.assertEqual(schedule[0], start)

    def test_fibonacci_values(self):
        start = date(2026, 1, 1)
        _, fib = fibonacci_schedule(start, 7)
        self.assertEqual(fib[0], 1)
        self.assertEqual(fib[1], 1)
        for i in range(2, len(fib)):
            self.assertEqual(fib[i], fib[i-1] + fib[i-2])


if __name__ == "__main__":
    unittest.main()
