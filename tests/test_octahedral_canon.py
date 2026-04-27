"""
tests/test_octahedral_canon.py
==============================

Verifies the GEIS ↔ Engine octahedral bijection in
:mod:`bridges.octahedral_canon`:

* The bit-level transformation is a true involution.
* Every GEIS index maps to a *distinct* Engine index (i.e. it's a
  permutation, not a many-to-one collapse).
* The mapping agrees with the physical signs of the real
  ``GEIS.octahedral_state.OctahedralState.POSITIONS`` and the real
  ``Engine.gaussian_splats.octahedral.OctahedralStateEncoder.state_centers``
  tables — so the canon stays accountable to the live data, not just
  to its own claim.
* Position-vector helpers preserve sign and (configurable) magnitude.

If anyone touches either coordinate convention, this test catches the
drift before downstream code starts placing field sources at the
wrong place.
"""

from __future__ import annotations

import unittest

from bridges.octahedral_canon import (
    NUM_VERTICES,
    engine_position_to_geis_position,
    engine_to_geis,
    geis_position_to_engine_position,
    geis_to_engine,
    is_bijection_intact,
    reconciliation_table,
    swap_geis_engine,
)


class TestBitLevelBijection(unittest.TestCase):

    def test_involution(self):
        for i in range(NUM_VERTICES):
            self.assertEqual(swap_geis_engine(swap_geis_engine(i)), i)

    def test_is_permutation(self):
        outputs = {swap_geis_engine(i) for i in range(NUM_VERTICES)}
        self.assertEqual(outputs, set(range(NUM_VERTICES)))

    def test_helper_reports_intact(self):
        self.assertTrue(is_bijection_intact())

    def test_aliases_are_consistent(self):
        for i in range(NUM_VERTICES):
            self.assertEqual(geis_to_engine(i), engine_to_geis(i))

    def test_rejects_out_of_range(self):
        for bad in (-1, 8, 99):
            with self.assertRaises(ValueError):
                swap_geis_engine(bad)

    def test_known_endpoints(self):
        # GEIS 0 = (+,+,+) ↔ Engine 7 = (+1,+1,+1)
        self.assertEqual(geis_to_engine(0), 7)
        # GEIS 7 = (-,-,-) ↔ Engine 0 = (-1,-1,-1)
        self.assertEqual(geis_to_engine(7), 0)


class TestAgainstLiveTables(unittest.TestCase):
    """The canon is only useful if it tracks the *real* data tables.
    These tests pull in the live POSITIONS / state_centers and verify
    sign agreement at every index."""

    @classmethod
    def setUpClass(cls):
        from GEIS.octahedral_state import OctahedralState
        from Engine.gaussian_splats.octahedral import OctahedralStateEncoder

        cls.geis_pos = OctahedralState.POSITIONS
        cls.eng_centers = OctahedralStateEncoder()._build_state_centers()

    def test_signs_agree_at_every_index(self):
        for g in range(NUM_VERTICES):
            e = geis_to_engine(g)
            gx, gy, gz = self.geis_pos[g]
            ex, ey, ez = self.eng_centers[e]
            for axis_name, gv, ev in (
                ("x", gx, ex), ("y", gy, ey), ("z", gz, ez),
            ):
                self.assertEqual(
                    (gv > 0), (ev > 0),
                    msg=(
                        f"sign drift on axis {axis_name}: "
                        f"GEIS index {g} pos={self.geis_pos[g]}, "
                        f"Engine index {e} pos={tuple(self.eng_centers[e])}"
                    ),
                )


class TestPositionVectorHelpers(unittest.TestCase):

    def test_geis_to_engine_position(self):
        self.assertEqual(
            geis_position_to_engine_position((0.25, -0.25, 0.25)),
            (1.0, -1.0, 1.0),
        )
        self.assertEqual(
            geis_position_to_engine_position((-0.25, -0.25, -0.25)),
            (-1.0, -1.0, -1.0),
        )

    def test_engine_to_geis_position_default_magnitude(self):
        self.assertEqual(
            engine_position_to_geis_position((1.0, -1.0, 1.0)),
            (0.25, -0.25, 0.25),
        )

    def test_engine_to_geis_position_custom_magnitude(self):
        self.assertEqual(
            engine_position_to_geis_position(
                (1.0, 1.0, -1.0), magnitude=2.0,
            ),
            (2.0, 2.0, -2.0),
        )

    def test_position_round_trip(self):
        for g_index in range(NUM_VERTICES):
            from GEIS.octahedral_state import OctahedralState
            geis_pos = OctahedralState.POSITIONS[g_index]
            engine_pos = geis_position_to_engine_position(geis_pos)
            back = engine_position_to_geis_position(engine_pos)
            self.assertEqual(back, geis_pos)

    def test_position_helpers_reject_wrong_length(self):
        for fn in (
            geis_position_to_engine_position,
            engine_position_to_geis_position,
        ):
            with self.assertRaises(ValueError):
                fn((0.25, -0.25))  # 2-tuple, not 3-tuple


class TestReconciliationTable(unittest.TestCase):

    def test_table_has_every_index(self):
        table = reconciliation_table()
        self.assertEqual(len(table), NUM_VERTICES)
        self.assertEqual(
            sorted(row[0] for row in table),
            list(range(NUM_VERTICES)),
        )
        self.assertEqual(
            sorted(row[1] for row in table),
            list(range(NUM_VERTICES)),
        )

    def test_table_signs_match_geis(self):
        from GEIS.octahedral_state import OctahedralState

        for g_index, _e_index, signs in reconciliation_table():
            x_sign, y_sign, z_sign = signs
            gx, gy, gz = OctahedralState.POSITIONS[g_index]
            self.assertEqual(x_sign, +1 if gx > 0 else -1)
            self.assertEqual(y_sign, +1 if gy > 0 else -1)
            self.assertEqual(z_sign, +1 if gz > 0 else -1)


if __name__ == "__main__":
    unittest.main()
