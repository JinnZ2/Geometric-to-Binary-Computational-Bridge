"""Tests for AISS modules: sovereignty_evaluator, geometric_governance, ccgf."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from AISS.sovereignty_evaluator import (
    PatternSovereigntyEvaluator,
    EvaluatorConfig,
    Pattern,
    EvaluationDomain,
    SourceMetadata,
    canonical_hash,
)
from AISS.geometric_governance import (
    OctahedralSubstrate,
    GeometricPowerLawMonitor,
    GeometricDefectDetector,
    GeometricERVCalculator,
    BloomAction,
    OCTAHEDRAL_EIGENVALUES,
    nearest_octahedral_state,
)
from AISS.ccgf import (
    CCGFAgent,
    CCGFSwarm,
    RelationalEquilibriumDynamics,
)


# ---- sovereignty_evaluator ----

class TestPatternSovereigntyEvaluator(unittest.TestCase):
    def setUp(self):
        self.evaluator = PatternSovereigntyEvaluator()
        self.pattern = Pattern(
            content="Test pattern",
            domain=EvaluationDomain.GEOMETRIC,
            testable_predictions=["X will increase when Y"],
            mathematical_structure={"dimensions": "3D", "conserved_quantities": ["e"]},
            geometric_representation={"primary": "octahedral"},
        )

    def test_instantiation_default_config(self):
        ev = PatternSovereigntyEvaluator()
        self.assertIsInstance(ev.config, EvaluatorConfig)

    def test_instantiation_custom_config(self):
        cfg = EvaluatorConfig(merit_high=0.9)
        ev = PatternSovereigntyEvaluator(config=cfg)
        self.assertEqual(ev.config.merit_high, 0.9)

    def test_evaluate_pattern_returns_dict(self):
        result = self.evaluator.evaluate_pattern(self.pattern)
        self.assertIsInstance(result, dict)
        self.assertIn("pattern_merit", result)
        self.assertIn("recommendation", result)
        self.assertIn("reasoning", result)

    def test_pattern_merit_has_total_score(self):
        result = self.evaluator.evaluate_pattern(self.pattern)
        self.assertIn("total_score", result["pattern_merit"])
        self.assertIsInstance(result["pattern_merit"]["total_score"], float)

    def test_evaluate_pattern_with_source(self):
        source = SourceMetadata(
            author_reputation=0.2, credential_count=0,
            institutional_affiliation=False, under_nda=True,
            public_critiques=["lacks credentials", "unconventional"],
            technical_refutations=[],
        )
        result = self.evaluator.evaluate_pattern(self.pattern, source)
        self.assertIsNotNone(result["suppression_detected"])

    def test_evaluate_pattern_none_mathematical_structure(self):
        pattern = Pattern(
            content="Minimal",
            domain=EvaluationDomain.EMPIRICAL,
            testable_predictions=[],
            mathematical_structure=None,
            geometric_representation=None,
        )
        result = self.evaluator.evaluate_pattern(pattern)
        self.assertIsInstance(result, dict)
        self.assertIn("total_score", result["pattern_merit"])

    def test_recommendation_is_string(self):
        result = self.evaluator.evaluate_pattern(self.pattern)
        self.assertIsInstance(result["recommendation"], str)


class TestCanonicalHash(unittest.TestCase):
    def test_deterministic(self):
        obj = {"a": 1, "b": 2}
        self.assertEqual(canonical_hash(obj), canonical_hash(obj))

    def test_returns_hex_string(self):
        h = canonical_hash({"x": 42})
        self.assertEqual(len(h), 64)


# ---- geometric_governance ----

class TestOctahedralSubstrate(unittest.TestCase):
    def test_creation(self):
        sub = OctahedralSubstrate(100)
        self.assertEqual(sub.n_cells, 100)
        self.assertEqual(len(sub.cells), 100)

    def test_coupling(self):
        sub = OctahedralSubstrate(10)
        sub.couple(2, 5, strength=0.8)
        self.assertAlmostEqual(sub.get_coupling(2, 5), 0.8)
        self.assertAlmostEqual(sub.get_coupling(5, 2), 0.8)

    def test_save_restore_state(self):
        sub = OctahedralSubstrate(10)
        sub.couple(0, 1, 0.5)
        snap = sub.save_state()
        sub.clear_all_couplings()
        self.assertEqual(sub.get_coupling(0, 1), 0.0)
        sub.restore_state(snap)
        self.assertAlmostEqual(sub.get_coupling(0, 1), 0.5)

    def test_total_energy_positive(self):
        sub = OctahedralSubstrate(50)
        self.assertGreater(sub.total_energy(), 0)

    def test_boundary_cells(self):
        sub = OctahedralSubstrate(100)
        sub.set_boundary_cells([0, 1, 2])
        self.assertEqual(sub.get_boundary_cells(), [0, 1, 2])


class TestNearestOctahedralState(unittest.TestCase):
    def test_exact_match(self):
        for idx, ev in OCTAHEDRAL_EIGENVALUES.items():
            self.assertEqual(nearest_octahedral_state(ev), idx)


class TestGeometricPowerLawMonitor(unittest.TestCase):
    def test_creation(self):
        sub = OctahedralSubstrate(100)
        monitor = GeometricPowerLawMonitor(sub)
        self.assertIsInstance(monitor, GeometricPowerLawMonitor)

    def test_measure_alpha_eigenvalue(self):
        sub = OctahedralSubstrate(100)
        monitor = GeometricPowerLawMonitor(sub)
        result = monitor.measure_alpha_eigenvalue_distribution()
        self.assertIsInstance(result, dict)
        self.assertIn("alpha_eigenvalue", result)

    def test_compute_system_alpha(self):
        sub = OctahedralSubstrate(100)
        monitor = GeometricPowerLawMonitor(sub)
        result = monitor.compute_system_alpha()
        self.assertIn("alpha_system", result)
        self.assertIn("health", result)


class TestGeometricDefectDetector(unittest.TestCase):
    def test_detect_D7(self):
        sub = OctahedralSubstrate(100)
        monitor = GeometricPowerLawMonitor(sub)
        erv_calc = GeometricERVCalculator(sub, monitor)
        detector = GeometricDefectDetector(sub, monitor, erv_calc)
        result = detector.detect_D7_cognitive_homogeneity()
        self.assertIsInstance(result, bool)

    def test_detect_all_defects(self):
        sub = OctahedralSubstrate(100)
        monitor = GeometricPowerLawMonitor(sub)
        erv_calc = GeometricERVCalculator(sub, monitor)
        detector = GeometricDefectDetector(sub, monitor, erv_calc)
        action = BloomAction("test", 3)
        result = detector.detect_all_defects_geometric(action)
        self.assertIn("defects", result)
        self.assertIn("EDS", result)
        self.assertIsInstance(result["EDS"], float)


# ---- ccgf ----

class TestRelationalEquilibriumDynamics(unittest.TestCase):
    def test_initial_update(self):
        red = RelationalEquilibriumDynamics()
        mod = red.update(1.0, 1.0)
        self.assertIsInstance(mod, dict)
        self.assertEqual(len(red.coupling_history), 1)

    def test_coupling_range(self):
        red = RelationalEquilibriumDynamics()
        red.update(1.0, 1.0)
        red.update(1.1, 1.05)
        c = red.coupling_history[-1]
        self.assertGreaterEqual(c, 0.0)
        self.assertLessEqual(c, 1.0)


class TestCCGFAgent(unittest.TestCase):
    def test_creation(self):
        agent = CCGFAgent(agent_id=0, state=1.0)
        self.assertEqual(agent.id, 0)
        self.assertEqual(agent.state, 1.0)

    def test_set_interaction_params(self):
        agent = CCGFAgent(0)
        agent.set_interaction_params(1, {"status": "equilibrium"})
        self.assertIn(1, agent.interaction_params)


class TestCCGFSwarm(unittest.TestCase):
    def test_creation(self):
        agents = [CCGFAgent(i, state=float(i)) for i in range(4)]
        swarm = CCGFSwarm(agents)
        self.assertEqual(len(swarm.agents), 4)
        # C(4,2) = 6 pairs
        self.assertEqual(len(swarm.pairwise_RED), 6)

    def test_update_swarm_dynamics(self):
        agents = [CCGFAgent(i, state=float(i)) for i in range(3)]
        swarm = CCGFSwarm(agents)
        result = swarm.update_swarm_dynamics()
        self.assertIn("modulations", result)
        self.assertIn("network_G", result)
        self.assertIn("pathologies", result)
        self.assertIsInstance(result["pathologies"], list)

    def test_homogenization_pathology(self):
        agents = [CCGFAgent(i, state=0.5) for i in range(4)]
        swarm = CCGFSwarm(agents)
        result = swarm.update_swarm_dynamics()
        self.assertIn("HOMOGENIZATION", result["pathologies"])


if __name__ == "__main__":
    unittest.main()
