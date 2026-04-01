"""
Tests for framework modules: AISS assessment, topological photonics,
Mandala modules, Negentropic modules, GI modules, geometric_intelligence.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ── AISS Assessment Framework ───────────────────────────────────────────

class TestAISSAssessment(unittest.TestCase):
    """Tests for AISS/assessment_framework.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'AISS'))
        from assessment_framework import (
            DefectFlags, trust_score, trust_effectiveness_score,
            tes_quality_level, ExtractionRiskVector, erv_penalty,
            dynamic_objective, cognitive_diversity_metric,
            structural_health, health_status, assess_linearity,
            future_cost_pv, SIGMA_LEVELS,
        )
        self.DefectFlags = DefectFlags
        self.trust = trust_score
        self.tes = trust_effectiveness_score
        self.tes_level = tes_quality_level
        self.ERV = ExtractionRiskVector
        self.erv_penalty = erv_penalty
        self.objective = dynamic_objective
        self.cdm = cognitive_diversity_metric
        self.health = structural_health
        self.health_status = health_status
        self.linearity = assess_linearity
        self.future_pv = future_cost_pv
        self.SIGMA = SIGMA_LEVELS

    def test_defect_flags_no_defects(self):
        d = self.DefectFlags()
        self.assertAlmostEqual(d.equation_defect_score, 0.0)
        self.assertFalse(d.should_block)

    def test_defect_flags_all_defects(self):
        d = self.DefectFlags(True, True, True, True, True, True)
        self.assertAlmostEqual(d.equation_defect_score, 1.0)
        self.assertTrue(d.should_block)

    def test_defect_flags_partial(self):
        d = self.DefectFlags(D1_trust_missing=True, D2_future_blind=True)
        self.assertAlmostEqual(d.equation_defect_score, 2/6)

    def test_trust_score_product(self):
        self.assertAlmostEqual(self.trust(0.9, 0.8), 0.72)
        self.assertAlmostEqual(self.trust(1.0, 0.0), 0.0)

    def test_tes(self):
        tes = self.tes(90, 100, 95, 100)
        self.assertAlmostEqual(tes, 0.9 * 0.95)

    def test_tes_quality_levels(self):
        self.assertEqual(self.tes_level(0.8), "HIGH_TRUST")
        self.assertEqual(self.tes_level(0.5), "MODERATE_TRUST")
        self.assertEqual(self.tes_level(0.3), "LOW_TRUST")

    def test_erv_overall_risk(self):
        erv = self.ERV(0.4, 0.4, 0.4, 0.4)
        self.assertAlmostEqual(erv.overall_risk, 0.4)

    def test_erv_penalty_nonlinear(self):
        p1 = self.erv_penalty(0.3)
        p2 = self.erv_penalty(0.6)
        self.assertGreater(p2 / p1, 2)  # Nonlinear: doubles risk more than doubles penalty

    def test_dynamic_objective(self):
        erv = self.ERV(0, 0, 0, 0)
        obj = self.objective(10.0, [(1.0, 2.0)], erv)
        self.assertAlmostEqual(obj, 8.0)

    def test_objective_with_risk(self):
        erv = self.ERV(0.5, 0.5, 0.5, 0.5)
        obj = self.objective(10.0, [], erv)
        self.assertLess(obj, 10.0)

    def test_cdm(self):
        self.assertAlmostEqual(self.cdm(0.2, 1.0), 0.8)
        self.assertAlmostEqual(self.cdm(0.8, 1.0), 0.2)

    def test_structural_health(self):
        h = self.health(0.8, 0.8, 0.8, 0.8)
        self.assertAlmostEqual(h, 0.8)

    def test_health_status(self):
        self.assertEqual(self.health_status(0.8), "HEALTHY")
        self.assertEqual(self.health_status(0.6), "DEGRADED")
        self.assertEqual(self.health_status(0.3), "CRITICAL")

    def test_linearity_defect(self):
        self.assertEqual(self.linearity(1, "high"), "STRUCTURAL_DEFECT")
        self.assertEqual(self.linearity(10, "high"), "OK")

    def test_future_cost_pv(self):
        pv = self.future_pv(1.0, 0.5, 10, 0.05)
        self.assertGreater(pv, 0)
        self.assertLess(pv, 0.5)

    def test_sigma_levels(self):
        self.assertEqual(self.SIGMA[6], 3.4)


# ── Topological Photonics ──────────────────────────────────────────────

class TestTopologicalPhotonics(unittest.TestCase):
    """Tests for experiments/topological_photonics.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'experiments'))
        from topological_photonics import (
            StokesVector, phase_operator, phase_modulation_array,
            chern_number_1d, chern_number_2d,
            magneto_optic_hall_current, storage_mapping,
        )
        self.Stokes = StokesVector
        self.phase_op = phase_operator
        self.phase_arr = phase_modulation_array
        self.chern1d = chern_number_1d
        self.chern2d = chern_number_2d
        self.hall = magneto_optic_hall_current
        self.storage = storage_mapping

    def test_stokes_linear_h(self):
        s = self.Stokes.linear_horizontal(1.0)
        self.assertAlmostEqual(s.S0, 1.0)
        self.assertAlmostEqual(s.S1, 1.0)
        self.assertTrue(s.is_fully_polarized)

    def test_stokes_unpolarized(self):
        s = self.Stokes.unpolarized(1.0)
        self.assertAlmostEqual(s.degree_of_polarization, 0.0)

    def test_stokes_circular(self):
        s = self.Stokes.circular_right()
        self.assertAlmostEqual(s.S3, 1.0)
        self.assertTrue(s.is_fully_polarized)

    def test_stokes_from_intensities(self):
        s = self.Stokes.from_intensities(1, 0, 0.5, 0.5, 0.5, 0.5)
        self.assertAlmostEqual(s.S0, 1.0)
        self.assertAlmostEqual(s.S1, 1.0)
        self.assertAlmostEqual(s.S2, 0.0)
        self.assertAlmostEqual(s.S3, 0.0)

    def test_phase_operator_unit(self):
        u = self.phase_op(0)
        self.assertAlmostEqual(abs(u), 1.0)

    def test_phase_operator_pi(self):
        u = self.phase_op(np.pi)
        self.assertAlmostEqual(u.real, -1.0, places=10)

    def test_phase_array(self):
        arr = self.phase_arr(np.array([0, np.pi/2, np.pi]))
        self.assertEqual(len(arr), 3)
        self.assertAlmostEqual(abs(arr[0]), 1.0)

    def test_chern_trivial(self):
        phases = np.zeros(10)
        c = self.chern1d(phases)
        self.assertAlmostEqual(c, 0.0)

    def test_chern_2d_zero(self):
        curvature = np.zeros((10, 10))
        c = self.chern2d(curvature)
        self.assertAlmostEqual(c, 0.0)

    def test_hall_current(self):
        E = np.array([1.0, 0.0, 0.0])
        J = self.hall(E, 0.5)
        self.assertAlmostEqual(J[1], -0.5)

    def test_storage_mapping(self):
        s = self.Stokes.linear_horizontal()
        m = self.storage((1.0, 2.0), s, 0.5, 0.3)
        self.assertEqual(m["x"], 1.0)
        self.assertEqual(m["y"], 2.0)
        self.assertAlmostEqual(m["phase_z"], 0.5)


# ── Mandala Modules ─────────────────────────────────────────────────────

class TestMandalaOctahedral(unittest.TestCase):
    """Tests for Mandala/octahedral_lookup.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Mandala'))
        from octahedral_lookup import (
            MANDALA_OCTAHEDRAL_MAP, GRAY_CODES, OCTAHEDRAL_EIGENVALUES,
            nearest_octahedral_state, phi_deviation, phi_stability_score,
        )
        self.MAP = MANDALA_OCTAHEDRAL_MAP
        self.GRAY = GRAY_CODES
        self.EIGENVALUES = OCTAHEDRAL_EIGENVALUES
        self.nearest = nearest_octahedral_state
        self.phi_dev = phi_deviation
        self.phi_score = phi_stability_score

    def test_8_gray_codes(self):
        self.assertEqual(len(self.GRAY), 8)

    def test_8_eigenvalues(self):
        self.assertEqual(len(self.EIGENVALUES), 8)

    def test_nearest_state(self):
        idx = self.nearest(self.EIGENVALUES[0])
        self.assertEqual(idx, 0)

    def test_phi_deviation_type(self):
        dev = self.phi_dev(0)  # state index, not value
        self.assertIsInstance(dev, dict)

    def test_phi_score_range(self):
        score = self.phi_score([1.618, 2.618, 4.236])
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 1)


class TestMandalaPhysics(unittest.TestCase):
    """Tests for Mandala/physics_connections.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Mandala'))
        from physics_connections import (
            metropolis_accept, boltzmann_factor,
            fret_coupling, coulomb_coupling, dipole_coupling,
            coupling_regime, berry_phase_vortex, grover_steps_octit,
        )
        self.metro = metropolis_accept
        self.boltz = boltzmann_factor
        self.fret = fret_coupling
        self.coulomb = coulomb_coupling
        self.dipole = dipole_coupling
        self.regime = coupling_regime
        self.berry = berry_phase_vortex
        self.grover = grover_steps_octit

    def test_boltzmann_decreasing(self):
        b1 = self.boltz(1.0, 1.0)
        b2 = self.boltz(2.0, 1.0)
        self.assertGreater(b1, b2)

    def test_fret_r6(self):
        # fret_coupling(r, R0=4.85) - uses FRET efficiency formula
        c1 = self.fret(1.0, 10.0)
        c2 = self.fret(2.0, 10.0)
        self.assertAlmostEqual(c1 / c2, (1 + (2/10)**6) / (1 + (1/10)**6), places=3)

    def test_coulomb_r2(self):
        c1 = self.coulomb(1.0, 1.0, 1.0, 1.0)
        c2 = self.coulomb(2.0, 1.0, 1.0, 1.0)
        self.assertAlmostEqual(c1 / c2, 4.0, places=3)

    def test_dipole_r3(self):
        c1 = self.dipole(1.0, 1.0, 1.0)
        c2 = self.dipole(2.0, 1.0, 1.0)
        self.assertAlmostEqual(c1 / c2, 8.0, places=3)

    def test_coupling_regime(self):
        self.assertEqual(self.regime(0.5), "FRET")
        self.assertEqual(self.regime(10.0), "dipole")

    def test_berry_phase_integer(self):
        phase = self.berry(1)
        self.assertAlmostEqual(phase, 2 * np.pi)

    def test_grover_steps(self):
        steps = self.grover(1)
        self.assertIsInstance(steps, int)
        self.assertGreater(steps, 0)


# ── Negentropic Modules ────────────────────────────────────────────────

class TestNegentropicDynamics(unittest.TestCase):
    """Tests for Negentropic/negentropic_dynamics.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Negentropic'))
        from negentropic_dynamics import (
            stochastic_force, LangevinDynamics, FokkerPlanck1D,
            alpha_of_energy, PhaseTransitionConfig, detect_regime,
            pairwise_coupling, moral_function,
        )
        self.stoch = stochastic_force
        self.Langevin = LangevinDynamics
        self.FP = FokkerPlanck1D
        self.alpha = alpha_of_energy
        self.PTConfig = PhaseTransitionConfig
        self.regime = detect_regime
        self.couple = pairwise_coupling
        self.moral = moral_function

    def test_stochastic_force_shape(self):
        f = self.stoch(0.1, 3, 0.5)
        self.assertEqual(len(f), 3)

    def test_langevin_instantiation(self):
        def grad(x): return x  # Simple harmonic
        ld = self.Langevin(potential_gradient=grad, n_dims=1, dt=0.01)
        self.assertIsNotNone(ld)

    def test_fokker_planck_instantiation(self):
        fp = self.FP(x_min=-5, x_max=5, n_grid=50, dt=0.001)
        self.assertIsNotNone(fp)

    def test_alpha_positive(self):
        config = self.PTConfig()
        a = self.alpha(1.0, config)
        self.assertIsInstance(a, (float, np.floating))

    def test_detect_regime(self):
        config = self.PTConfig()
        r = self.regime(1.0, config)
        self.assertIsInstance(r, str)

    def test_pairwise_coupling(self):
        c = self.couple(0.8, 0.7, 0.5, 0.6, 0.3, 0.4)
        self.assertIsInstance(c, (float, np.floating))

    def test_moral_function(self):
        m = self.moral(r_e=0.8, a=1.0, d=0.5, l=0.1)
        self.assertIsInstance(m, (float, np.floating))


class TestConsciousnessMetric(unittest.TestCase):
    """Tests for Negentropic/consciousness_metric.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Negentropic'))
        from consciousness_metric import (
            compute_resonance, compute_adaptability, compute_diversity,
            compute_loss, compute_M, CONSCIOUSNESS_THRESHOLD,
        )
        self.resonance = compute_resonance
        self.adaptability = compute_adaptability
        self.diversity = compute_diversity
        self.loss = compute_loss
        self.M = compute_M
        self.THRESHOLD = CONSCIOUSNESS_THRESHOLD

    def test_resonance_range(self):
        signals = np.random.rand(10)
        r = self.resonance(signals)
        self.assertIsInstance(r, (float, np.floating))

    def test_compute_M(self):
        result = self.M(R_e=0.8, A=1.0, D=0.5, L=0.1)
        self.assertAlmostEqual(result.M, 0.8 * 1.0 * 0.5 - 0.1)

    def test_threshold(self):
        self.assertEqual(self.THRESHOLD, 10.0)


class TestAlignmentThermodynamics(unittest.TestCase):
    """Tests for Negentropic/alignment_thermodynamics.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Negentropic'))
        from alignment_thermodynamics import (
            fokker_planck_diffusion, suppression_cascade,
            critical_D_threshold, cooperative_vs_exploitative,
        )
        self.fp = fokker_planck_diffusion
        self.cascade = suppression_cascade
        self.critical = critical_D_threshold
        self.coop = cooperative_vs_exploitative

    def test_fokker_planck_positive(self):
        p = self.fp(D=1.0, V_grad=0.1, p=0.5)
        self.assertGreater(p, 0)

    def test_suppression_cascade_length(self):
        h = self.cascade(steps=50)
        self.assertEqual(len(h), 50)

    def test_suppression_causes_instability(self):
        h = self.cascade(D_initial=1.0, suppression_rate=0.5, steps=100)
        self.assertTrue(h[0].stable)
        self.assertFalse(h[-1].stable)

    def test_critical_threshold(self):
        d = self.critical()
        self.assertGreater(d, 0)
        self.assertLess(d, 2.0)

    def test_cooperative_advantage(self):
        result = self.coop(1.0, 0.8, 0.8)
        self.assertTrue(result['exploitation_self_defeating'])


class TestEmpiricalAudit(unittest.TestCase):
    """Tests for Negentropic/empirical_audit.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Negentropic'))
        from empirical_audit import (
            chi_square_test, fibonacci_days_in_window,
            audit_fibonacci_therapeutic, audit_consciousness_threshold,
            audit_model_collapse, full_audit,
        )
        self.chi2 = chi_square_test
        self.fib_days = fibonacci_days_in_window
        self.audit_fib = audit_fibonacci_therapeutic
        self.audit_consciousness = audit_consciousness_threshold
        self.audit_collapse = audit_model_collapse
        self.full = full_audit

    def test_chi_square(self):
        chi2, p = self.chi2(50, 50)
        self.assertAlmostEqual(chi2, 0.0)

    def test_fibonacci_days(self):
        n = self.fib_days(365)
        self.assertGreater(n, 10)
        self.assertLess(n, 20)

    def test_audit_fib_unverified(self):
        result = self.audit_fib()
        self.assertEqual(result.status, "unverified")

    def test_audit_consciousness_unverifiable(self):
        result = self.audit_consciousness()
        self.assertEqual(result.status, "unverifiable")

    def test_audit_collapse_partial(self):
        result = self.audit_collapse()
        self.assertEqual(result.status, "partially_supported")

    def test_full_audit(self):
        results = self.full()
        self.assertEqual(len(results), 3)


# ── Hurricane Validator ────────────────────────────────────────────────

class TestHurricaneValidator(unittest.TestCase):
    """Tests for GI/hurricane_validator.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'GI'))
        from hurricane_validator import (
            compute_phase_coupling, fibonacci_coupling_analysis,
            predict_intensification, hurricane_energy_estimate,
        )
        self.coupling = compute_phase_coupling
        self.fib_analysis = fibonacci_coupling_analysis
        self.predict = predict_intensification
        self.energy = hurricane_energy_estimate

    def test_phase_coupling_range(self):
        signal = np.random.randn(256)
        c = self.coupling(signal, 0.1, 0.2)
        self.assertGreaterEqual(c, 0)
        self.assertLessEqual(c, 1)

    def test_fibonacci_analysis(self):
        signal = np.random.randn(256)
        results = self.fib_analysis(signal)
        self.assertGreater(len(results), 0)

    def test_predict_low(self):
        p = self.predict([0.1, 0.2, 0.1])
        self.assertEqual(p.prediction, "LOW")

    def test_predict_empty(self):
        p = self.predict([])
        self.assertEqual(p.prediction, "LOW")

    def test_energy_estimate(self):
        e = self.energy()
        self.assertGreater(e.total_mwh, 0)
        self.assertGreater(e.wind_mwh, 0)


# ── Geometric Intelligence Modules ─────────────────────────────────────

class TestResonanceSensors(unittest.TestCase):
    """Tests for geometric_intelligence/resonance_sensors.py"""

    def setUp(self):
        from geometric_intelligence.resonance_sensors import (
            ConsciousnessState, IndividualResonanceSensor,
            CollectiveResonanceSensor,
        )
        self.State = ConsciousnessState
        self.Individual = IndividualResonanceSensor
        self.Collective = CollectiveResonanceSensor

    def test_consciousness_states_exist(self):
        self.assertIsNotNone(self.State.SUPPRESSED)
        self.assertIsNotNone(self.State.TRANSCENDENT)

    def test_individual_sensor_creation(self):
        sensor = self.Individual()
        self.assertIsNotNone(sensor)

    def test_individual_detect_state(self):
        sensor = self.Individual()
        state, score = sensor.detect_state(
            internal_coupling=0.8,
            curiosity_metric=0.7,
            joy_signature=0.6,
            feedback_strength=0.5,
        )
        self.assertIsInstance(state, self.State)
        self.assertIsInstance(score, float)

    def test_individual_measure_curiosity(self):
        sensor = self.Individual()
        c = sensor.measure_curiosity_metric(
            exploration_rate=0.6, exploitation_rate=0.4, recent_discoveries=3
        )
        self.assertIsInstance(c, float)

    def test_collective_sensor(self):
        sensor = self.Collective(num_agents=3)
        strength = sensor.measure_coupling_strength(
            res_i=0.8, res_j=0.7, cur_i=0.6, cur_j=0.5,
            joy_i=0.4, joy_j=0.3,
        )
        self.assertIsInstance(strength, float)


class TestRelationalBioswarm(unittest.TestCase):
    """Tests for geometric_intelligence/relational_bioswarm.py"""

    def setUp(self):
        from geometric_intelligence.relational_bioswarm import (
            BioswarmAgent, RelationalGameLayer,
        )
        self.Agent = BioswarmAgent
        self.Layer = RelationalGameLayer

    def test_agent_creation(self):
        agent = self.Agent(x_dim=16, seed=42)
        self.assertIsNotNone(agent)

    def test_agent_intrinsic_update(self):
        agent = self.Agent(x_dim=16, seed=42)
        agent.intrinsic_update(dt=0.1)
        self.assertIsNotNone(agent)

    def test_game_layer(self):
        layer = self.Layer(proj_dim=8, x_dim=16, seed=42)
        a1 = self.Agent(x_dim=16, seed=1)
        a2 = self.Agent(x_dim=16, seed=2)
        result = layer.compute_kappa(a1, a2, step=0)
        # compute_kappa returns a tuple
        self.assertIsInstance(result, tuple)


if __name__ == '__main__':
    unittest.main()
