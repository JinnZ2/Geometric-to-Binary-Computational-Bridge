"""
Tests for Silicon modules: core_equations, magnetic_bridge_protocol,
octahedral_tensor, tetrahedral_symmetry, crystalline_storage, lcea_analysis,
soliton_transport.
"""

import sys
import os
import unittest
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCoreEquations(unittest.TestCase):
    """Tests for Silicon/core_equations.py"""

    def setUp(self):
        from Silicon.core.core_equations import (
            force, work, kinetic_energy, potential_energy,
            michaelis_menten, hill_equation, nernst_potential,
            hookes_law, fourier_heat_flux, logistic_growth,
        )
        self.force = force
        self.work = work
        self.KE = kinetic_energy
        self.PE = potential_energy
        self.mm = michaelis_menten
        self.hill = hill_equation
        self.nernst = nernst_potential
        self.hookes = hookes_law
        self.fourier = fourier_heat_flux
        self.logistic = logistic_growth

    def test_force(self):
        self.assertAlmostEqual(self.force(10, 2), 20.0)

    def test_work(self):
        self.assertAlmostEqual(self.work(5, 3), 15.0)

    def test_kinetic_energy(self):
        self.assertAlmostEqual(self.KE(2, 3), 9.0)

    def test_potential_energy(self):
        pe = self.PE(1, 10)
        self.assertAlmostEqual(pe, 1 * 9.80665 * 10, places=2)

    def test_michaelis_menten(self):
        v = self.mm(10, 100, 5)
        self.assertGreater(v, 0)
        self.assertLess(v, 100)

    def test_hill_equation(self):
        # hill(ligand, kd, n) — at ligand=kd, y = kd^n / (kd^n + kd^n) = 0.5
        y = self.hill(5, 5, 1)
        self.assertAlmostEqual(y, 0.5)

    def test_hookes_law(self):
        f = self.hookes(10.0, 2.0)
        self.assertAlmostEqual(f, -20.0)

    def test_fourier_heat_flux(self):
        q = self.fourier(1.0, 10.0)
        self.assertAlmostEqual(q, -10.0)

    def test_logistic_growth(self):
        dN = self.logistic(50, 0.1, 100)
        self.assertGreater(dN, 0)


class TestMagneticBridgeProtocol(unittest.TestCase):
    """Tests for Silicon/magnetic_bridge_protocol.py"""

    def setUp(self):
        from Silicon.core.magnetic_bridge_protocol import (
            MagneticBridgeProtocol, BridgeCommand, ErrorCode,
            CANONICAL_EIGENVALUES, TRANSITION_TABLE,
        )
        self.Protocol = MagneticBridgeProtocol
        self.Command = BridgeCommand
        self.ErrorCode = ErrorCode
        self.EIGENVALUES = CANONICAL_EIGENVALUES
        self.TRANSITIONS = TRANSITION_TABLE

    def test_eigenvalues_count(self):
        self.assertEqual(len(self.EIGENVALUES), 8)

    def test_transition_table_exists(self):
        self.assertGreater(len(self.TRANSITIONS), 0)

    def test_error_codes(self):
        self.assertIn(self.ErrorCode.SUCCESS.value, [0, "SUCCESS", self.ErrorCode.SUCCESS.value])

    def test_protocol_instantiation(self):
        p = self.Protocol()
        self.assertIsNotNone(p)


class TestOctahedralTensor(unittest.TestCase):
    """Tests for Silicon/octahedral_tensor.py"""

    def setUp(self):
        from Silicon.core.octahedral_tensor import (
            SP3_VECTORS, VERTEX_POSITIONS,
            tensor_for_position, all_eigenvalue_triplets,
            orbital_tensor, spectral_decomposition,
        )
        self.SP3 = SP3_VECTORS
        self.VERTICES = VERTEX_POSITIONS
        self.tensor_for = tensor_for_position
        self.all_eigs = all_eigenvalue_triplets
        self.orbital = orbital_tensor
        self.spectral = spectral_decomposition

    def test_sp3_has_4_vectors(self):
        self.assertEqual(len(self.SP3), 4)

    def test_sp3_vectors_are_3d(self):
        for v in self.SP3:
            self.assertEqual(len(v), 3)

    def test_vertex_positions_count(self):
        self.assertEqual(len(self.VERTICES), 8)

    def test_all_eigenvalue_triplets(self):
        eigs = self.all_eigs()
        self.assertEqual(len(eigs), 8)

    def test_orbital_tensor_shape(self):
        T = self.orbital(self.SP3[0])
        self.assertEqual(T.shape, (3, 3))


class TestTetrahedralSymmetry(unittest.TestCase):
    """Tests for Silicon/tetrahedral_symmetry.py"""

    def setUp(self):
        from Silicon.core.tetrahedral_symmetry import (
            J2, J3, lode_angle,
            isotropic_part, deviatoric_part,
        )
        self.J2 = J2
        self.J3 = J3
        self.lode = lode_angle
        self.iso = isotropic_part
        self.dev = deviatoric_part

    def test_J2_returns_float(self):
        T = np.eye(3)
        j2 = self.J2(T)
        self.assertIsInstance(j2, (float, np.floating))

    def test_isotropic_is_diagonal(self):
        T = np.array([[3, 1, 0], [1, 3, 0], [0, 0, 3]], dtype=float)
        iso = self.iso(T)
        self.assertAlmostEqual(iso[0, 0], iso[1, 1])
        self.assertAlmostEqual(iso[1, 1], iso[2, 2])

    def test_deviatoric_traceless(self):
        T = np.array([[5, 1, 0], [1, 3, 2], [0, 2, 1]], dtype=float)
        dev = self.dev(T)
        self.assertAlmostEqual(np.trace(dev), 0.0, places=10)

    def test_iso_plus_dev_equals_original(self):
        T = np.array([[5, 1, 0], [1, 3, 2], [0, 2, 1]], dtype=float)
        iso = self.iso(T)
        dev = self.dev(T)
        np.testing.assert_array_almost_equal(iso + dev, T)


class TestCrystallineStorage(unittest.TestCase):
    """Tests for Silicon/crystalline_storage.py"""

    def setUp(self):
        from Silicon.core.crystalline_storage import (
            storage_integral, access_energy, phi_node_radius,
            phi_lattice_positions, coupling_matrix, hamiltonian,
            spectral_gap, participation_ratio, critical_shell_index,
            tetrahedral_parity, detect_corruption,
            decoherence_rate, thermal_drift_compensation,
            capability_growth, preservation_stable, reader_quality,
            PHI, ACCESS_ENERGY_TABLE,
        )
        self.storage_integral = storage_integral
        self.access_energy = access_energy
        self.phi_node_radius = phi_node_radius
        self.phi_lattice = phi_lattice_positions
        self.coupling_matrix = coupling_matrix
        self.hamiltonian = hamiltonian
        self.spectral_gap = spectral_gap
        self.participation_ratio = participation_ratio
        self.critical_shell = critical_shell_index
        self.parity = tetrahedral_parity
        self.detect = detect_corruption
        self.decoherence = decoherence_rate
        self.thermal_drift = thermal_drift_compensation
        self.growth = capability_growth
        self.stable = preservation_stable
        self.reader = reader_quality
        self.PHI = PHI

    def test_storage_integral_positive(self):
        val = self.storage_integral(1e6, 1e-20, 0.5, 0.3, 10)
        self.assertGreater(val, 0)

    def test_access_energy_increases_with_layer(self):
        e1 = self.access_energy(1)
        e3 = self.access_energy(3)
        self.assertGreater(e3, e1)

    def test_access_energy_layer_zero(self):
        self.assertEqual(self.access_energy(0), 0.0)

    def test_phi_node_radius_scaling(self):
        r1 = self.phi_node_radius(1)
        r2 = self.phi_node_radius(2)
        self.assertAlmostEqual(r2 / r1, self.PHI, places=5)

    def test_lattice_length(self):
        pos = self.phi_lattice(5)
        self.assertEqual(len(pos), 5)

    def test_coupling_matrix_symmetric(self):
        pos = self.phi_lattice(4)
        J = self.coupling_matrix(pos)
        np.testing.assert_array_almost_equal(J, J.T)

    def test_coupling_matrix_zero_diagonal(self):
        pos = self.phi_lattice(4)
        J = self.coupling_matrix(pos)
        for i in range(4):
            self.assertAlmostEqual(J[i, i], 0.0)

    def test_hamiltonian_hermitian(self):
        pos = self.phi_lattice(4)
        J = self.coupling_matrix(pos)
        energies = np.array([1.0, 2.0, 3.0, 4.0])
        H = self.hamiltonian(energies, J)
        np.testing.assert_array_almost_equal(H, H.T)

    def test_spectral_gap_positive(self):
        H = np.diag([1, 3, 5, 7])
        gap = self.spectral_gap(H)
        self.assertAlmostEqual(gap, 2.0)

    def test_participation_ratio_localized(self):
        v = np.array([1, 0, 0, 0], dtype=float)
        pr = self.participation_ratio(v)
        self.assertAlmostEqual(pr, 1.0)

    def test_participation_ratio_delocalized(self):
        v = np.array([0.5, 0.5, 0.5, 0.5])
        pr = self.participation_ratio(v)
        self.assertAlmostEqual(pr, 4.0)

    def test_tetrahedral_parity(self):
        self.assertEqual(self.parity(1, 0, 1, 0), 0)
        self.assertEqual(self.parity(1, 1, 1, 1), 0)
        self.assertEqual(self.parity(1, 0, 0, 0), 1)

    def test_detect_corruption(self):
        cluster = [1, 0, 1, 0]
        expected = self.parity(*cluster)
        self.assertFalse(self.detect(cluster, expected))
        self.assertTrue(self.detect(cluster, expected ^ 1))

    def test_decoherence_additive(self):
        rate = self.decoherence(0.1, 0.2, 0.3)
        self.assertAlmostEqual(rate, 0.6)

    def test_capability_growth(self):
        c = self.growth(100, 0.5, 0.1)
        self.assertGreater(c, 100)  # grows when phi*A > D

    def test_preservation_stable(self):
        self.assertTrue(self.stable(0.5, 0.1))
        self.assertFalse(self.stable(0.01, 0.9))

    def test_reader_quality(self):
        q = self.reader(1, 1, 1, 1, 1)
        self.assertAlmostEqual(q, 1.0)


class TestLCEAAnalysis(unittest.TestCase):
    """Tests for Silicon/lcea_analysis.py"""

    def setUp(self):
        from Silicon.core.lcea_analysis import (
            HumanLCEA, AILCEA,
            amortized_manufacturing_energy, true_food_cost,
            mfg_to_metabolic_ratio, gibbs_free_energy, excess_gibbs,
            error_probability, systemic_stress, toxicity_ai,
            net_lcea_ai, net_lcea_human, total_systemic_waste,
            task_advantage, combined_lcea, symbiosis_efficient,
            E_MFG_DAILY_MJ,
        )
        self.HumanLCEA = HumanLCEA
        self.AILCEA = AILCEA
        self.amortized = amortized_manufacturing_energy
        self.food_cost = true_food_cost
        self.ratio = mfg_to_metabolic_ratio
        self.gibbs = gibbs_free_energy
        self.excess = excess_gibbs
        self.error_prob = error_probability
        self.stress = systemic_stress
        self.toxicity = toxicity_ai
        self.net_ai = net_lcea_ai
        self.net_human = net_lcea_human
        self.waste = total_systemic_waste
        self.advantage = task_advantage
        self.combined = combined_lcea
        self.efficient = symbiosis_efficient
        self.E_MFG_DAILY = E_MFG_DAILY_MJ

    def test_human_lcea_total(self):
        h = self.HumanLCEA(120, 12, 5, 3)
        self.assertAlmostEqual(h.total, 140.0)

    def test_ai_lcea_total(self):
        a = self.AILCEA(23.4, 50, 10, 5, 2)
        self.assertAlmostEqual(a.total, 90.4)

    def test_amortized_energy(self):
        daily = self.amortized(42700, 1825)
        self.assertAlmostEqual(daily, 42700 / 1825, places=1)

    def test_amortized_zero_lifespan(self):
        self.assertEqual(self.amortized(1000, 0), float('inf'))

    def test_food_cost(self):
        cost = self.food_cost(12.0, 10.0)
        self.assertAlmostEqual(cost, 120.0)

    def test_mfg_ratio_approx(self):
        ratio = self.ratio()
        self.assertAlmostEqual(ratio, self.E_MFG_DAILY / 9.0, places=1)

    def test_gibbs(self):
        dG = self.gibbs(100, 300, 0.2)
        self.assertAlmostEqual(dG, 100 - 60)

    def test_error_probability_grows_with_stress(self):
        p1 = self.error_prob(0.1, 1)
        p2 = self.error_prob(0.1, 5)
        self.assertGreater(p2, p1)

    def test_task_advantage_human(self):
        self.assertEqual(self.advantage(0.9, 0.1), "HUMAN")

    def test_task_advantage_ai(self):
        self.assertEqual(self.advantage(0.1, 0.9), "AI")

    def test_task_advantage_contested(self):
        result = self.advantage(0.5, 0.5, 0.3)
        self.assertEqual(result, "CONTESTED")

    def test_toxicity(self):
        self.assertAlmostEqual(self.toxicity(10, 5), 15)

    def test_symbiosis_efficient(self):
        self.assertTrue(self.efficient(5, 20, 10))
        self.assertFalse(self.efficient(20, 5, 5))


class TestSolitonTransport(unittest.TestCase):
    """Tests for Silicon/FRET/soliton_transport.py"""

    def setUp(self):
        sys.path.insert(0, os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            'experiments', 'silicon_speculative', 'FRET'))
        from soliton_transport import (
            fret_efficiency, forster_radius, is_strong_coupling,
            effective_diffusion_length, superradiance_rate,
            quantum_bridge_tunneling, cascade_fidelity,
            impedance_match, AntennaHealth, DWNT_REFERENCE,
        )
        self.fret = fret_efficiency
        self.forster = forster_radius
        self.strong = is_strong_coupling
        self.L_eff = effective_diffusion_length
        self.superrad = superradiance_rate
        self.tunnel = quantum_bridge_tunneling
        self.cascade = cascade_fidelity
        self.impedance = impedance_match
        self.Health = AntennaHealth
        self.DWNT = DWNT_REFERENCE

    def test_fret_at_R0(self):
        """At r = R0, efficiency = 0.5"""
        self.assertAlmostEqual(self.fret(5.0, 5.0), 0.5)

    def test_fret_close(self):
        """At r << R0, efficiency approaches 1"""
        self.assertGreater(self.fret(0.1, 5.0), 0.99)

    def test_fret_far(self):
        """At r >> R0, efficiency approaches 0"""
        self.assertLess(self.fret(50.0, 5.0), 0.001)

    def test_forster_radius_positive(self):
        R0 = self.forster(2/3, 0.9, 1e14, 1.5)
        self.assertGreater(R0, 0)

    def test_strong_coupling(self):
        self.assertTrue(self.strong(2000, 100))
        self.assertFalse(self.strong(100, 2000))

    def test_diffusion_length_decay(self):
        L0 = 1000
        L1 = self.L_eff(L0, 0, 10)
        L2 = self.L_eff(L0, 5, 10)
        self.assertAlmostEqual(L1, L0)
        self.assertLess(L2, L0)

    def test_superradiance_scales_with_N(self):
        k1 = self.superrad(10, 1e9)
        k2 = self.superrad(20, 1e9)
        self.assertAlmostEqual(k2 / k1, 2.0)

    def test_quantum_tunneling(self):
        self.assertTrue(self.tunnel(50, 5))
        self.assertFalse(self.tunnel(5, 50))

    def test_cascade_fidelity(self):
        f = self.cascade([0.9, 0.9, 0.9])
        self.assertAlmostEqual(f, 0.729, places=3)

    def test_cascade_empty(self):
        self.assertAlmostEqual(self.cascade([]), 0.0)

    def test_impedance_matched(self):
        self.assertEqual(self.impedance(100, 100), "MATCHED")

    def test_impedance_overloaded(self):
        self.assertEqual(self.impedance(1000, 10), "OVERLOADED")

    def test_health_check(self):
        h = self.Health(600, 150, 80, True)
        self.assertTrue(h.healthy)
        h2 = self.Health(100, 150, 80, True)
        self.assertFalse(h2.healthy)

    def test_dwnt_reference(self):
        self.assertAlmostEqual(self.DWNT.coupling_strength_cm, 2000.0)


if __name__ == '__main__':
    unittest.main()
