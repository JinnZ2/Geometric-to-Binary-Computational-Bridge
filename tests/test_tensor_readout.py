"""Tests for Silicon/tensor_readout.py — TTM-2 and TTM-3.

Stdlib only; runs without numpy. TTM-2 and TTM-3 are the two TTM claims that
needed no experiment, and these tests are what settles them.
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "Silicon"))

from tensor_readout import (  # noqa: E402
    HKL110_DIRECTIONS,
    SP3_DIRECTIONS,
    components_to_tensor,
    design_matrix,
    matrix_rank,
    normalize,
    project,
    projections,
    recover_tensor,
    tensor_to_components,
    traceless_rank,
)

E_STATE = [[1.0, 0.0, 0.0], [0.0, -1.0, 0.0], [0.0, 0.0, 0.0]]
T2_STATE = [[0.0, 0.5, 0.0], [0.5, 0.0, 0.0], [0.0, 0.0, 0.0]]
ZERO = [[0.0] * 3 for _ in range(3)]


def _random_symmetric(rng, scale=1.0):
    m = [[rng.uniform(-scale, scale) for _ in range(3)] for _ in range(3)]
    return [[(m[i][j] + m[j][i]) / 2 for j in range(3)] for i in range(3)]


def _traceless(T):
    tr = sum(T[i][i] for i in range(3)) / 3.0
    return [[T[i][j] - (tr if i == j else 0.0) for j in range(3)] for i in range(3)]


class TestSp3Blindness(unittest.TestCase):
    """TTM-2: falsifier is 'any E-type state distinguished by {s_i}'."""

    def test_the_counterexample(self):
        """diag(1,-1,0) and 0 produce the same fingerprint."""
        self.assertEqual([round(v, 12) for v in projections(E_STATE)], [0.0] * 4)
        self.assertEqual([round(v, 12) for v in projections(ZERO)], [0.0] * 4)

    def test_sp3_diagonal_weights_are_identical_in_every_row(self):
        """The structural reason: rx^2 = ry^2 = rz^2 = 1/3 for all four."""
        for row in design_matrix(SP3_DIRECTIONS):
            self.assertAlmostEqual(row[0], 1 / 3, places=12)
            self.assertAlmostEqual(row[1], 1 / 3, places=12)
            self.assertAlmostEqual(row[2], 1 / 3, places=12)

    def test_sp3_projections_sum_to_zero_on_traceless_tensors(self):
        rng = random.Random(3)
        for _ in range(300):
            T = _traceless(_random_symmetric(rng))
            self.assertAlmostEqual(sum(projections(T)), 0.0, places=12)

    def test_sp3_ranks_full_space_four_traceless_three(self):
        """Both ranks are true in their own domain; state which is quoted."""
        self.assertEqual(matrix_rank(design_matrix(SP3_DIRECTIONS)), 4)
        self.assertEqual(traceless_rank(SP3_DIRECTIONS), 3)

    def test_sp3_sees_only_off_diagonals_for_traceless_input(self):
        """s_i must depend on Txy, Txz, Tyz alone."""
        rng = random.Random(11)
        for _ in range(200):
            off = [rng.uniform(-1, 1) for _ in range(3)]
            for diag in ([1.0, -1.0, 0.0], [2.0, -3.0, 1.0], [0.0, 0.0, 0.0]):
                d = [x - sum(diag) / 3 for x in diag]
                T = components_to_tensor([d[0], d[1], d[2]] + off)
                base = components_to_tensor([0.0, 0.0, 0.0] + off)
                for a, b in zip(projections(T), projections(base)):
                    self.assertAlmostEqual(a, b, places=12)

    def test_sp3_closed_form_matches_the_audit(self):
        """s1 = (2/3)(Txy + Txz + Tyz), and the three sign patterns."""
        rng = random.Random(5)
        for _ in range(200):
            xy, xz, yz = (rng.uniform(-1, 1) for _ in range(3))
            T = components_to_tensor([0.0, 0.0, 0.0, xy, xz, yz])
            s = projections(T)
            expect = [(2 / 3) * (xy + xz + yz), (2 / 3) * (-xy - xz + yz),
                      (2 / 3) * (-xy + xz - yz), (2 / 3) * (xy - xz - yz)]
            for a, b in zip(s, expect):
                self.assertAlmostEqual(a, b, places=12)

    def test_e_type_states_all_collapse_to_zero(self):
        """The whole E doublet is in the null space, not just one example."""
        for a, b in ((1.0, -1.0), (2.0, -2.0), (0.5, 0.5)):
            # (Txx - Tyy) and (2Tzz - Txx - Tyy) generators, traceless
            for T in (components_to_tensor([a, -a, 0.0, 0, 0, 0]),
                      components_to_tensor([b, b, -2 * b, 0, 0, 0])):
                self.assertEqual([round(v, 12) for v in projections(T)], [0.0] * 4)


class TestHkl110Completeness(unittest.TestCase):
    """TTM-3: falsifier is 'a symmetric tensor not recovered from the six'."""

    def test_design_matrix_is_full_rank(self):
        self.assertEqual(matrix_rank(design_matrix(HKL110_DIRECTIONS)), 6)
        self.assertEqual(traceless_rank(HKL110_DIRECTIONS), 5)

    def test_recovers_the_state_sp3_could_not_see(self):
        rec = recover_tensor(projections(E_STATE, HKL110_DIRECTIONS))
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(rec[i][j], E_STATE[i][j], places=12)

    def test_recovers_random_symmetric_tensors(self):
        rng = random.Random(17)
        for _ in range(500):
            T = _random_symmetric(rng)
            rec = recover_tensor(projections(T, HKL110_DIRECTIONS))
            for i in range(3):
                for j in range(3):
                    self.assertAlmostEqual(rec[i][j], T[i][j], places=10)

    def test_recovers_across_scales(self):
        """Strain lives at 1e-4; the solve must not be scale-fragile."""
        rng = random.Random(23)
        for scale in (1e-6, 1e-4, 1.0, 1e3):
            T = _random_symmetric(rng, scale)
            rec = recover_tensor(projections(T, HKL110_DIRECTIONS))
            worst = max(abs(rec[i][j] - T[i][j])
                        for i in range(3) for j in range(3))
            self.assertLess(worst, 1e-9 * max(scale, 1.0))

    def test_recovery_is_exact_for_pure_modes(self):
        for T in (E_STATE, T2_STATE, ZERO,
                  [[1.0, 0, 0], [0, 1.0, 0], [0, 0, 1.0]]):
            rec = recover_tensor(projections(T, HKL110_DIRECTIONS))
            for i in range(3):
                for j in range(3):
                    self.assertAlmostEqual(rec[i][j], T[i][j], places=12)

    def test_refuses_a_rank_deficient_basis(self):
        """Better to refuse than return one of infinitely many tensors."""
        with self.assertRaises(ValueError) as ctx:
            recover_tensor(projections(E_STATE), SP3_DIRECTIONS)
        self.assertIn("rank", str(ctx.exception))

    def test_rejects_mismatched_measurement_count(self):
        with self.assertRaises(ValueError):
            recover_tensor([0.0, 0.0, 0.0])


class TestPrimitives(unittest.TestCase):
    def test_projection_is_the_rayleigh_quotient(self):
        T = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]
        self.assertAlmostEqual(project(T, (1, 0, 0)), 2.0)
        self.assertAlmostEqual(project(T, (0, 0, 1)), -1.0)

    def test_projection_is_normalisation_invariant(self):
        T = _random_symmetric(random.Random(1))
        for k in (0.5, 1.0, 7.0):
            self.assertAlmostEqual(project(T, (1, 2, 3)),
                                   project(T, (k, 2 * k, 3 * k)), places=12)

    def test_projection_lies_between_extreme_eigenvalues(self):
        T = [[2.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, -1.0]]
        rng = random.Random(9)
        for _ in range(200):
            v = [rng.uniform(-1, 1) for _ in range(3)]
            if math.sqrt(sum(x * x for x in v)) < 1e-9:
                continue
            self.assertLessEqual(project(T, v), 2.0 + 1e-12)
            self.assertGreaterEqual(project(T, v), -1.0 - 1e-12)

    def test_component_roundtrip(self):
        T = _random_symmetric(random.Random(31))
        rec = components_to_tensor(tensor_to_components(T))
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(rec[i][j], T[i][j], places=12)

    def test_normalize_rejects_zero(self):
        with self.assertRaises(ValueError):
            normalize((0.0, 0.0, 0.0))

    def test_components_to_tensor_validates_length(self):
        with self.assertRaises(ValueError):
            components_to_tensor([1.0, 2.0])

    def test_matrix_rank_edge_cases(self):
        self.assertEqual(matrix_rank([]), 0)
        self.assertEqual(matrix_rank([[0.0, 0.0], [0.0, 0.0]]), 0)
        self.assertEqual(matrix_rank([[1.0, 0.0], [0.0, 1.0]]), 2)
        self.assertEqual(matrix_rank([[1.0, 2.0], [2.0, 4.0]]), 1)


if __name__ == "__main__":
    unittest.main()
