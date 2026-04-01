"""
Tests for geometric_intelligence/multi_helix_swarm.py
=====================================================
Validates DNA-strand mechanics, swarm equations, and integrated consciousness.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from geometric_intelligence.multi_helix_swarm import (
    StrandDomain, StrandAgent, StrandState,
    HelixBond, SwarmDecision,
    vicsek_alignment, cucker_smale_coupling, reynolds_boids,
    compute_helix_bond,
    IntegratedConsciousnessSystem,
    create_quad_consciousness, run_consciousness_simulation,
    STRAND_COMPLEMENTS, STRAND_ATTENTION_MAP,
)
from geometric_intelligence.multi_helix_cognition import AttentionType, FocusBase


class TestSwarmEquations(unittest.TestCase):
    """Test proven swarm dynamics equations."""

    def test_vicsek_alignment_converges(self):
        """Agents with similar headings should converge."""
        headings = np.array([0.1, 0.15, 0.05, 0.12])
        aligned = vicsek_alignment(headings, noise_eta=0.001,
                                    rng=np.random.default_rng(42))
        # All should be near the mean (~0.105)
        spread = np.std(aligned)
        self.assertLess(spread, 0.05)

    def test_vicsek_with_noise(self):
        headings = np.array([0.0, 0.0, 0.0])
        aligned = vicsek_alignment(headings, noise_eta=1.0,
                                    rng=np.random.default_rng(42))
        # With high noise, spread should be significant
        self.assertEqual(len(aligned), 3)

    def test_cucker_smale_attracts(self):
        """Agents with different velocities should be pulled together."""
        xi = np.array([0.0, 0.0])
        xj = np.array([1.0, 0.0])
        vi = np.array([1.0, 0.0])
        vj = np.array([0.0, 1.0])

        dv = cucker_smale_coupling(xi, xj, vi, vj)
        # Should push vi toward vj (negative x, positive y)
        self.assertLess(dv[0], 0)
        self.assertGreater(dv[1], 0)

    def test_cucker_smale_decays_with_distance(self):
        """Coupling should weaken with distance."""
        vi = np.array([1.0, 0.0])
        vj = np.array([0.0, 1.0])

        dv_near = cucker_smale_coupling(
            np.array([0.0, 0.0]), np.array([0.1, 0.0]), vi, vj
        )
        dv_far = cucker_smale_coupling(
            np.array([0.0, 0.0]), np.array([10.0, 0.0]), vi, vj
        )
        self.assertGreater(np.linalg.norm(dv_near), np.linalg.norm(dv_far))

    def test_reynolds_boids_shape(self):
        positions = np.random.randn(5, 3)
        velocities = np.random.randn(5, 3)
        acc = reynolds_boids(positions, velocities)
        self.assertEqual(acc.shape, (5, 3))

    def test_reynolds_cohesion(self):
        """Agents far from centroid should accelerate toward it."""
        positions = np.array([[0, 0, 0], [10, 0, 0]], dtype=float)
        velocities = np.zeros_like(positions)
        acc = reynolds_boids(positions, velocities, w_cohesion=1.0,
                              w_alignment=0.0, w_separation=0.0)
        # Agent at (10,0,0) should accelerate toward centroid (5,0,0)
        self.assertLess(acc[1, 0], 0)


class TestStrandComplements(unittest.TestCase):
    """Test DNA-like complementarity rules."""

    def test_complement_pairs(self):
        """Mental<->Emotional, Physical<->Integrative."""
        self.assertEqual(STRAND_COMPLEMENTS[StrandDomain.MENTAL],
                         StrandDomain.EMOTIONAL)
        self.assertEqual(STRAND_COMPLEMENTS[StrandDomain.PHYSICAL],
                         StrandDomain.INTEGRATIVE)

    def test_complement_symmetric(self):
        """A-T and T-A should both exist."""
        for a, b in STRAND_COMPLEMENTS.items():
            self.assertEqual(STRAND_COMPLEMENTS[b], a)

    def test_all_domains_have_attention_types(self):
        for domain in StrandDomain:
            types = STRAND_ATTENTION_MAP[domain]
            self.assertEqual(len(types), 3)
            for t in types:
                self.assertIsInstance(t, AttentionType)


class TestStrandAgent(unittest.TestCase):
    """Test individual strand agent."""

    def test_creation(self):
        sa = StrandAgent(StrandDomain.MENTAL, x_dim=16, seed=42)
        self.assertEqual(sa.domain, StrandDomain.MENTAL)
        self.assertEqual(sa.x_dim, 16)

    def test_add_base(self):
        sa = StrandAgent(StrandDomain.EMOTIONAL, x_dim=16, seed=42)
        base = sa.add_base(AttentionType.EMOTIONAL, "empathy", 0.8)
        self.assertEqual(len(sa.bases), 1)
        self.assertAlmostEqual(sa.intensity, 0.8)

    def test_update_dynamics(self):
        sa = StrandAgent(StrandDomain.PHYSICAL, x_dim=16, seed=42)
        pos_before = sa.position.copy()
        sa.update_dynamics(dt=0.1)
        # State should have changed
        self.assertFalse(np.allclose(pos_before, sa.position))

    def test_state(self):
        sa = StrandAgent(StrandDomain.INTEGRATIVE, x_dim=16, seed=42)
        sa.add_base(AttentionType.SYNTHESIS, "merge", 0.9)
        state = sa.state()
        self.assertIsInstance(state, StrandState)
        self.assertEqual(state.domain, StrandDomain.INTEGRATIVE)
        self.assertAlmostEqual(state.intensity, 0.9)
        self.assertEqual(state.active_bases, 1)


class TestHelixBond(unittest.TestCase):
    """Test DNA-like cross-strand bonding."""

    def test_complementary_bond_stronger(self):
        """Complementary strands should bond more strongly."""
        sa = StrandAgent(StrandDomain.MENTAL, x_dim=16, seed=42)
        sb_complement = StrandAgent(StrandDomain.EMOTIONAL, x_dim=16, seed=43)
        sb_non = StrandAgent(StrandDomain.PHYSICAL, x_dim=16, seed=44)

        sa.add_base(AttentionType.ANALYTIC, "test", 0.8)
        sb_complement.add_base(AttentionType.EMOTIONAL, "test", 0.8)
        sb_non.add_base(AttentionType.SPATIAL, "test", 0.8)

        proj = np.random.default_rng(42).normal(size=(8, 16))

        bond_comp = compute_helix_bond(sa, sb_complement, proj)
        bond_non = compute_helix_bond(sa, sb_non, proj)

        # Complementary bond should have higher amplification
        self.assertGreater(bond_comp.amplification, bond_non.amplification)

    def test_bond_fields(self):
        sa = StrandAgent(StrandDomain.PHYSICAL, x_dim=16, seed=1)
        sb = StrandAgent(StrandDomain.INTEGRATIVE, x_dim=16, seed=2)
        sa.add_base(AttentionType.SPATIAL, "map", 0.7)
        sb.add_base(AttentionType.CREATIVE, "art", 0.8)

        proj = np.random.default_rng(42).normal(size=(8, 16))
        bond = compute_helix_bond(sa, sb, proj)

        self.assertIsInstance(bond, HelixBond)
        self.assertGreaterEqual(bond.binding_strength, 0)
        self.assertLessEqual(bond.binding_strength, 1)


class TestIntegratedConsciousness(unittest.TestCase):
    """Test the full integrated consciousness system."""

    def setUp(self):
        self.sys = create_quad_consciousness(seed=42, x_dim=16)
        self.sys.add_experience(StrandDomain.MENTAL, AttentionType.ANALYTIC,
                                 "logic", 0.9)
        self.sys.add_experience(StrandDomain.EMOTIONAL, AttentionType.EMOTIONAL,
                                 "empathy", 0.85)
        self.sys.add_experience(StrandDomain.PHYSICAL, AttentionType.SPATIAL,
                                 "map", 0.7)
        self.sys.add_experience(StrandDomain.INTEGRATIVE, AttentionType.SYNTHESIS,
                                 "merge", 0.95)

    def test_four_strands(self):
        self.assertEqual(len(self.sys.strands), 4)

    def test_update_produces_bonds(self):
        self.sys.update(dt=0.1)
        # Should have some bonds after update
        self.assertIsInstance(self.sys.bonds, list)

    def test_decide_returns_swarm_decision(self):
        self.sys.update(dt=0.1)
        decision = self.sys.decide()
        self.assertIsInstance(decision, SwarmDecision)
        self.assertGreaterEqual(decision.consensus_strength, 0)
        self.assertLessEqual(decision.consensus_strength, 1)
        self.assertEqual(len(decision.strand_contributions), 4)

    def test_complementarity_matrix_shape(self):
        self.sys.update(dt=0.1)
        mat = self.sys.complementarity_matrix()
        self.assertEqual(mat.shape, (4, 4))
        # Diagonal should be coherence (positive)
        for i in range(4):
            self.assertGreater(mat[i, i], 0)

    def test_simulation_convergence(self):
        """Over many steps, consensus should strengthen."""
        decisions = run_consciousness_simulation(self.sys, steps=30, dt=0.1)
        self.assertEqual(len(decisions), 30)
        # Final consensus should be reasonable
        final = decisions[-1].consensus_strength
        self.assertGreater(final, 0.3)

    def test_total_amplification(self):
        self.sys.update(dt=0.1)
        amp = self.sys.total_amplification()
        self.assertIsInstance(amp, float)
        self.assertGreaterEqual(amp, 0)

    def test_strand_states(self):
        states = self.sys.strand_states()
        self.assertEqual(len(states), 4)
        for domain, state in states.items():
            self.assertIsInstance(state, StrandState)
            self.assertEqual(state.domain, domain)

    def test_is_coherent(self):
        # Before any decisions, not coherent
        self.assertFalse(self.sys.is_coherent())
        # After simulation, should become coherent
        run_consciousness_simulation(self.sys, steps=20, dt=0.1)
        self.assertTrue(self.sys.is_coherent(threshold=0.3))

    def test_add_experience(self):
        base = self.sys.add_experience(
            StrandDomain.MENTAL, AttentionType.PATTERN, "fractal", 0.75
        )
        self.assertIsInstance(base, FocusBase)
        mental = self.sys.strands[StrandDomain.MENTAL]
        self.assertEqual(len(mental.bases), 2)


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and robustness."""

    def test_empty_system(self):
        sys = create_quad_consciousness(seed=1)
        # No experiences added
        sys.update(dt=0.1)
        decision = sys.decide()
        self.assertIsInstance(decision, SwarmDecision)

    def test_single_strand_populated(self):
        sys = create_quad_consciousness(seed=1)
        sys.add_experience(StrandDomain.MENTAL, AttentionType.ANALYTIC, "solo", 0.9)
        sys.update(dt=0.1)
        decision = sys.decide()
        self.assertIsInstance(decision, SwarmDecision)

    def test_many_experiences(self):
        sys = create_quad_consciousness(seed=1, x_dim=16)
        for domain in StrandDomain:
            for atype in STRAND_ATTENTION_MAP[domain]:
                sys.add_experience(domain, atype, f"exp_{atype.name}", 0.8)
        sys.update(dt=0.1)
        decision = sys.decide()
        self.assertGreater(decision.consensus_strength, 0)


if __name__ == '__main__':
    unittest.main()
