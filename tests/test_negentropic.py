"""Tests for Negentropic/negentropic_engine.py"""

import unittest
import sys
import os
from datetime import date, timedelta

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

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
