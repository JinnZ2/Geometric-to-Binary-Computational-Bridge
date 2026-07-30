"""Tests for Silicon/silicon_check.py — Silicon_Error_Correction v2.0.

Stdlib only; runs without numpy. Each class maps to a defect from the v1
audit recorded in Silicon/silicon_error_correction.json.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from silicon_check import (  # noqa: E402
    CAPTURE_RADIUS_NM,
    IDEAL_BOND_ANGLE_DEG,
    check,
    eigen_symmetric_3x3,
    frame_misalign_deg,
    invariants,
    recovery_channel,
    sigma_theta_deg,
    tau_thermal,
)
from silicon_check import _rotate_z  # noqa: E402


class TestThermalNoiseFloor(unittest.TestCase):
    """v1 FATAL: a 2-degree threshold sat at ~1 sigma of thermal motion."""

    def test_sigma_at_room_temperature(self):
        self.assertAlmostEqual(sigma_theta_deg(300.0), 1.9, places=6)

    def test_sigma_matches_debye_waller_derivation(self):
        u_rms = math.sqrt(0.006)                       # angstrom
        derived = math.degrees(math.atan(u_rms / 2.352))
        self.assertAlmostEqual(sigma_theta_deg(300.0), derived, delta=0.05)

    def test_sigma_scales_as_sqrt_temperature(self):
        self.assertAlmostEqual(sigma_theta_deg(1200.0) / sigma_theta_deg(300.0),
                               2.0, places=9)

    def test_v1_threshold_was_about_one_sigma(self):
        self.assertLess(2.0 / sigma_theta_deg(300.0), 1.1)

    def test_default_threshold_is_four_sigma(self):
        just_under = IDEAL_BOND_ANGLE_DEG + 4.0 * sigma_theta_deg(300.0) - 0.01
        just_over = IDEAL_BOND_ANGLE_DEG + 4.0 * sigma_theta_deg(300.0) + 0.01
        clean = [[0.0] * 3 for _ in range(3)]
        self.assertNotIn("BOND_ANGLE", check(clean, just_under)["flags"])
        self.assertIn("BOND_ANGLE", check(clean, just_over)["flags"])

    def test_rejects_nonpositive_temperature(self):
        with self.assertRaises(ValueError):
            sigma_theta_deg(0.0)
        with self.assertRaises(ValueError):
            tau_thermal(-1.0)


class TestInvariants(unittest.TestCase):
    """v1 HIGH: trace alone sees only volume; shear is trace-silent."""

    PURE_SHEAR = [[0.0, 1.0e-3, 0.0], [1.0e-3, 0.0, 0.0], [0.0, 0.0, 0.0]]

    def test_pure_shear_has_zero_trace(self):
        I1, J2, _ = invariants(self.PURE_SHEAR)
        self.assertAlmostEqual(I1, 0.0, places=15)
        self.assertGreater(J2, 0.0)

    def test_pure_shear_is_caught_by_deviatoric_not_volumetric(self):
        flags = check(self.PURE_SHEAR, IDEAL_BOND_ANGLE_DEG)["flags"]
        self.assertIn("DEVIATORIC", flags)
        self.assertNotIn("VOLUMETRIC", flags)

    def test_pure_dilatation_is_caught_by_volumetric_not_deviatoric(self):
        d = 3.0e-4
        dilat = [[d, 0.0, 0.0], [0.0, d, 0.0], [0.0, 0.0, d]]
        flags = check(dilat, IDEAL_BOND_ANGLE_DEG)["flags"]
        self.assertIn("VOLUMETRIC", flags)
        self.assertNotIn("DEVIATORIC", flags)

    def test_threshold_is_below_fracture(self):
        """v1 tripped at 0.02 dilatation; Si fractures near 0.01."""
        fracturing = [[0.01, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]]
        self.assertIn("VOLUMETRIC", check(fracturing, IDEAL_BOND_ANGLE_DEG)["flags"])

    def test_rejects_asymmetric_and_malformed(self):
        with self.assertRaises(ValueError):
            invariants([[0.0, 1.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
        with self.assertRaises(ValueError):
            invariants([[0.0, 0.0], [0.0, 0.0]])


class TestInvariantBlindness(unittest.TestCase):
    """SIL-1: the falsifier is 'an invariant detects an orientation fault'."""

    STRAIN = [[3.0e-4, 0.0, 0.0], [0.0, -1.0e-4, 0.0], [0.0, 0.0, -2.0e-4]]

    def test_rotation_leaves_every_invariant_unchanged(self):
        for angle in (5.0, 30.0, 45.0, 90.0):
            before = invariants(self.STRAIN)
            after = invariants(_rotate_z(self.STRAIN, angle))
            for a, b in zip(before, after):
                self.assertAlmostEqual(a, b, delta=1e-15, msg=f"{angle} deg")

    def test_rotation_is_visible_to_the_frame_check(self):
        for angle in (5.0, 30.0, 45.0):
            self.assertAlmostEqual(
                frame_misalign_deg(self.STRAIN, _rotate_z(self.STRAIN, angle)),
                angle, delta=1e-6)

    def test_orientation_flag_requires_a_reference(self):
        rotated = _rotate_z(self.STRAIN, 30.0)
        blind = check(rotated, IDEAL_BOND_ANGLE_DEG)
        seeing = check(rotated, IDEAL_BOND_ANGLE_DEG, reference=self.STRAIN)
        self.assertNotIn("ORIENTATION", blind["flags"])
        self.assertIsNone(blind["frame_misalign_deg"])
        self.assertIsNotNone(blind["BLIND_TO"])
        self.assertIn("ORIENTATION", seeing["flags"])
        self.assertIsNone(seeing["BLIND_TO"])

    def test_identical_tensors_have_zero_misalignment(self):
        self.assertAlmostEqual(frame_misalign_deg(self.STRAIN, self.STRAIN),
                               0.0, places=9)

    def test_misalignment_is_sign_invariant(self):
        """An eigenvector and its negation are the same principal axis."""
        flipped = _rotate_z(self.STRAIN, 180.0)
        self.assertAlmostEqual(frame_misalign_deg(self.STRAIN, flipped),
                               0.0, delta=1e-6)


class TestEigenDecomposition(unittest.TestCase):
    def test_recovers_known_diagonal(self):
        diag = [[3.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 2.0]]
        vals, _ = eigen_symmetric_3x3(diag)
        self.assertEqual([round(v, 9) for v in vals], [3.0, 2.0, 1.0])

    def test_eigenvalues_sum_to_trace_and_product_to_determinant(self):
        rng = random.Random(5)
        for _ in range(200):
            m = [[rng.uniform(-1, 1) for _ in range(3)] for _ in range(3)]
            sym = [[(m[i][j] + m[j][i]) / 2 for j in range(3)] for i in range(3)]
            vals, _ = eigen_symmetric_3x3(sym)
            trace = sum(sym[i][i] for i in range(3))
            det = (sym[0][0] * (sym[1][1] * sym[2][2] - sym[1][2] * sym[2][1])
                   - sym[0][1] * (sym[1][0] * sym[2][2] - sym[1][2] * sym[2][0])
                   + sym[0][2] * (sym[1][0] * sym[2][1] - sym[1][1] * sym[2][0]))
            self.assertAlmostEqual(sum(vals), trace, places=9)
            self.assertAlmostEqual(vals[0] * vals[1] * vals[2], det, places=9)

    def test_eigenvectors_are_orthonormal(self):
        rng = random.Random(7)
        m = [[rng.uniform(-1, 1) for _ in range(3)] for _ in range(3)]
        sym = [[(m[i][j] + m[j][i]) / 2 for j in range(3)] for i in range(3)]
        _, vecs = eigen_symmetric_3x3(sym)
        for i in range(3):
            self.assertAlmostEqual(sum(x * x for x in vecs[i]), 1.0, places=9)
            for j in range(i + 1, 3):
                dot = sum(a * b for a, b in zip(vecs[i], vecs[j]))
                self.assertAlmostEqual(dot, 0.0, places=9)

    def test_eigenpairs_satisfy_the_eigen_equation(self):
        sym = [[2.0, 0.3, -0.1], [0.3, 1.0, 0.2], [-0.1, 0.2, 0.5]]
        vals, vecs = eigen_symmetric_3x3(sym)
        for val, vec in zip(vals, vecs):
            av = [sum(sym[i][k] * vec[k] for k in range(3)) for i in range(3)]
            for a, v in zip(av, vec):
                self.assertAlmostEqual(a, val * v, places=9)


class TestRecoveryChannels(unittest.TestCase):
    """v1 FATAL: one cycle time cannot describe two mechanisms 6 orders apart."""

    def test_arrhenius_at_room_temperature(self):
        self.assertAlmostEqual(tau_thermal(300.0), 3.6e-6, delta=0.2e-6)

    def test_close_pair_is_athermal_and_in_scope(self):
        r = recovery_channel(0.5)
        self.assertTrue(r["in_scope"])
        self.assertEqual(r["barrier_eV"], 0.0)
        self.assertAlmostEqual(r["timescale_s"], 1.5e-12)

    def test_capture_radius_is_the_boundary(self):
        self.assertTrue(recovery_channel(CAPTURE_RADIUS_NM)["in_scope"])
        self.assertFalse(recovery_channel(CAPTURE_RADIUS_NM + 0.01)["in_scope"])

    def test_channels_differ_by_six_orders(self):
        fast = recovery_channel(0.5)["timescale_s"]
        slow = recovery_channel(5.0)["timescale_s"]
        self.assertGreater(math.log10(slow / fast), 6.0)

    def test_separated_pair_is_out_of_scope_at_every_sane_temperature(self):
        for T in (77.0, 200.0, 300.0):
            self.assertFalse(recovery_channel(3.0, T)["in_scope"])

    def test_rejects_negative_separation(self):
        with self.assertRaises(ValueError):
            recovery_channel(-1.0)


class TestCheckReport(unittest.TestCase):
    def test_clean_lattice_raises_no_flags(self):
        clean = [[0.0] * 3 for _ in range(3)]
        self.assertEqual(check(clean, IDEAL_BOND_ANGLE_DEG)["flags"], [])

    def test_report_carries_the_threshold_it_used(self):
        result = check([[0.0] * 3 for _ in range(3)], IDEAL_BOND_ANGLE_DEG, T=400.0)
        self.assertAlmostEqual(result["sigma_deg"], round(sigma_theta_deg(400.0), 3))
        self.assertAlmostEqual(result["angle_threshold_deg"],
                               round(4.0 * sigma_theta_deg(400.0), 3))

    def test_ideal_angle_is_the_tetrahedral_angle(self):
        self.assertAlmostEqual(IDEAL_BOND_ANGLE_DEG, 109.4712, places=4)


if __name__ == "__main__":
    unittest.main()
