"""Tests for GEIS/gies_core.py and GEIS/gies_codec.py -- GIES-1..7.

Stdlib only. Every claim here is arithmetic or crystallography and these tests
are what settle them. The codec is tested exhaustively over all 128 tokens,
because the original suite validated exactly one token that happened to work.
"""

import itertools
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "GEIS"))

from gies_codec import (  # noqa: E402
    IOPS,
    ISYMS,
    OPS,
    SYMS,
    TOKEN_BITS,
    all_tokens,
    decode,
    decode_stream,
    encode,
    encode_stream,
)
from gies_core import (  # noqa: E402
    BONDS,
    CORNERS,
    SI_BOND_A,
    Cell,
    closed_form_eigenvalues,
    corner_index,
    decode_tensor,
    frenkel,
    hamming_weight_pairs,
    parity,
    site_type,
)

LATTICE_A = 5.431


def _outer(v):
    return [[x * y for y in v] for x in v]


def _diamond_basis():
    fcc = [(0, 0, 0), (0, .5, .5), (.5, 0, .5), (.5, .5, 0)]
    return fcc + [(x + .25, y + .25, z + .25) for x, y, z in fcc]


def _occupied(frac, tol=1e-6):
    f = tuple(c % 1.0 for c in frac)
    for b in _diamond_basis():
        bb = tuple(c % 1.0 for c in b)
        if all(min(abs(f[k] - bb[k]), 1 - abs(f[k] - bb[k])) < tol
               for k in range(3)):
            return True
    return False


def _min_image_distance(frac, a=LATTICE_A):
    best = float("inf")
    for shift in itertools.product((-1, 0, 1), repeat=3):
        p = [(frac[k] + shift[k]) * a for k in range(3)]
        best = min(best, math.sqrt(sum(x * x for x in p)))
    return best


def _shell(frac, rmax=3.0, a=LATTICE_A):
    ds = []
    for shift in itertools.product((-2, -1, 0, 1, 2), repeat=3):
        for b in _diamond_basis():
            q = [(b[k] + shift[k] - frac[k]) * a for k in range(3)]
            d = math.sqrt(sum(x * x for x in q))
            if 1e-6 < d < rmax:
                ds.append(round(d, 6))
    return sorted(ds)


class TestGies1Collapse(unittest.TestCase):
    """The bug: outer(v,v) == outer(-v,-v), and the table is antipodal."""

    POSITIONS = {0: (.25, .25, .25), 1: (.25, -.25, .25), 2: (-.25, .25, .25),
                 3: (-.25, -.25, .25), 4: (.25, .25, -.25),
                 5: (.25, -.25, -.25), 6: (-.25, .25, -.25),
                 7: (-.25, -.25, -.25)}

    def test_position_table_is_antipodal_in_pairs(self):
        for i in range(4):
            self.assertEqual(tuple(-c for c in self.POSITIONS[i]),
                             self.POSITIONS[7 - i])

    def test_outer_product_cannot_see_the_sign(self):
        for i, j in hamming_weight_pairs():
            self.assertEqual(_outer(self.POSITIONS[i]), _outer(self.POSITIONS[j]))

    def test_all_eight_share_one_trace(self):
        traces = {round(sum(_outer(self.POSITIONS[i])[k][k] for k in range(3)), 12)
                  for i in range(8)}
        self.assertEqual(traces, {0.1875})

    def test_all_eight_share_one_eigenvalue_set(self):
        """Rank 1, so {0, 0, |v|^2} for every state."""
        for i in range(8):
            v = self.POSITIONS[i]
            self.assertAlmostEqual(sum(c * c for c in v), 0.1875, places=12)

    def test_projections_are_identical_for_inversion_pairs(self):
        for i, j in hamming_weight_pairs():
            for n in ((1, 0, 0), (1, 1, 0), (1, 2, 3), (0, 0, 1)):
                a = sum(n[x] * _outer(self.POSITIONS[i])[x][y] * n[y]
                        for x in range(3) for y in range(3))
                b = sum(n[x] * _outer(self.POSITIONS[j])[x][y] * n[y]
                        for x in range(3) for y in range(3))
                self.assertAlmostEqual(a, b, places=15)

    def test_not_maps_each_state_to_its_indistinguishable_partner(self):
        """NOT(i) = 7-i is exactly the map outer(v,v) cannot detect."""
        for i in range(8):
            self.assertEqual(7 - i, ~i & 0b111)


class TestGies2SiteParity(unittest.TestCase):
    """Falsifier: a listed position whose parity does not match its site."""

    POSITIONS = TestGies1Collapse.POSITIONS

    def test_index_parity_equals_negative_coordinate_parity(self):
        for i in range(8):
            n_neg = sum(1 for c in self.POSITIONS[i] if c < 0)
            self.assertEqual(n_neg & 1, parity(i), msg=f"index {i}")

    def test_even_parity_positions_are_occupied_atoms(self):
        for i in (0, 3, 5, 6):
            self.assertEqual(parity(i), 0)
            self.assertTrue(_occupied(self.POSITIONS[i]), msg=f"index {i}")
            self.assertEqual(site_type(i), "lattice")

    def test_odd_parity_positions_are_empty(self):
        for i in (1, 2, 4, 7):
            self.assertEqual(parity(i), 1)
            self.assertFalse(_occupied(self.POSITIONS[i]), msg=f"index {i}")
            self.assertEqual(site_type(i), "interstitial")

    def test_all_eight_sit_at_the_bond_length(self):
        for i in range(8):
            self.assertAlmostEqual(_min_image_distance(self.POSITIONS[i]),
                                   SI_BOND_A, places=3)

    def test_the_empty_site_is_a_tetrahedral_interstitial(self):
        """Same coordination shell as the T site at (1/2,1/2,1/2)."""
        anti = _shell((-.25, -.25, -.25))
        tsite = _shell((.5, .5, .5))
        self.assertEqual(anti, tsite)
        self.assertEqual(len([d for d in anti if d < 2.4]), 4)

    def test_four_lattice_and_four_interstitial(self):
        sites = [site_type(i) for i in range(8)]
        self.assertEqual(sites.count("lattice"), 4)
        self.assertEqual(sites.count("interstitial"), 4)

    def test_the_four_even_directions_are_the_sp3_bonds(self):
        """Consistency with CLAUDE.md's '4 A-bonds + 4 B-bonds' note.

        As directions the eight are both sublattices' bonds; from a FIXED atom
        only the four even-parity ones terminate on an atom. Both hold.
        """
        even = {tuple(CORNERS[i]) for i in range(8) if parity(i) == 0}
        bonds = {tuple(round(c * math.sqrt(3)) for c in b) for b in BONDS}
        self.assertEqual(even, bonds)

    def test_parity_is_a_single_bit_error_detecting_code(self):
        """Any one-bit index error flips parity, hence flips site type."""
        for i in range(8):
            for bit in range(3):
                self.assertNotEqual(parity(i), parity(i ^ (1 << bit)))

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            parity(8)
        with self.assertRaises(ValueError):
            parity(-1)


class TestGies3NotIsFrenkel(unittest.TestCase):
    """Falsifier: a NOT that stays on one sublattice."""

    def test_every_not_crosses_sublattices(self):
        for i in range(8):
            self.assertTrue(frenkel(i, 7 - i), msg=f"index {i}")

    def test_frenkel_is_exactly_parity_difference(self):
        for i in range(8):
            for j in range(8):
                self.assertEqual(frenkel(i, j), parity(i) != parity(j))

    def test_single_bit_flips_are_always_frenkel(self):
        """So is every one-bit transition, not just NOT."""
        for i in range(8):
            for bit in range(3):
                self.assertTrue(frenkel(i, i ^ (1 << bit)))

    def test_two_bit_flips_are_never_frenkel(self):
        for i in range(8):
            for a in range(3):
                for b in range(3):
                    if a != b:
                        self.assertFalse(frenkel(i, i ^ (1 << a) ^ (1 << b)))

    def test_same_state_is_not_frenkel(self):
        for i in range(8):
            self.assertFalse(frenkel(i, i))


class TestGies5TensorSeparates(unittest.TestCase):
    """Falsifier: a kappa != 0 leaving inversion pairs degenerate."""

    def test_inversion_pairs_are_separated(self):
        for i, j in hamming_weight_pairs():
            self.assertNotEqual(Cell(i).tensor(), Cell(j).tensor())

    def test_closed_form_matches_the_construction(self):
        for kappa in (0.1, 0.5, 0.9):
            for i in range(8):
                want = closed_form_eigenvalues(parity(i) == 0, kappa)
                got = Cell(i, kappa).eigenvalues()
                for a, b in zip(got, want):
                    self.assertAlmostEqual(a, b, places=12)

    def test_documented_eigenvalues_at_kappa_half(self):
        self.assertEqual([round(e, 4) for e in Cell(0).eigenvalues()],
                         [1.7778, 1.1111, 1.1111])
        self.assertEqual([round(e, 4) for e in Cell(7).eigenvalues()],
                         [1.5556, 1.5556, 0.8889])

    def test_two_eigenvalues_are_degenerate_by_c3v_symmetry(self):
        """Not a defect: the axial symmetry of a <111> direction.

        Which slot holds the pair depends on the sublattice, since the unique
        eigenvalue is the largest on the lattice side and the smallest on the
        interstitial side. So the invariant claim is that the spectrum has
        exactly two distinct values with multiplicities 2 and 1.
        """
        for i in range(8):
            ev = [round(e, 12) for e in Cell(i).eigenvalues()]
            distinct = sorted({ev.count(v) for v in set(ev)})
            self.assertEqual(len(set(ev)), 2, msg=f"index {i}: {ev}")
            self.assertEqual(distinct, [1, 2], msg=f"index {i}: {ev}")

    def test_the_unique_eigenvalue_is_max_on_lattice_min_on_interstitial(self):
        """Which is how one bit of site type is read off the spectrum."""
        for i in range(8):
            ev = [round(e, 12) for e in Cell(i).eigenvalues()]
            unique = [v for v in set(ev) if ev.count(v) == 1][0]
            if parity(i) == 0:
                self.assertEqual(unique, max(ev), msg=f"index {i}")
            else:
                self.assertEqual(unique, min(ev), msg=f"index {i}")

    def test_bonds_are_a_spherical_2_design(self):
        """SUM_i t_i (x) t_i = (4/3) I, which is what makes the sum telescope."""
        acc = [[0.0] * 3 for _ in range(3)]
        for t in BONDS:
            for a in range(3):
                for b in range(3):
                    acc[a][b] += t[a] * t[b]
        for a in range(3):
            for b in range(3):
                self.assertAlmostEqual(acc[a][b], (4 / 3) if a == b else 0.0,
                                       places=12)

    def test_kappa_zero_collapses_again_and_that_is_correct(self):
        base = Cell(0, kappa=0.0).tensor()
        for i in range(8):
            self.assertEqual(Cell(i, kappa=0.0).tensor(), base)
        self.assertIsNone(decode_tensor(Cell(3, kappa=0.0).tensor()))

    def test_separation_grows_with_kappa(self):
        def gap(k):
            return abs(Cell(0, k).eigenvalues()[0] - Cell(7, k).eigenvalues()[0])
        self.assertLess(gap(0.1), gap(0.5))
        self.assertLess(gap(0.5), gap(0.9))

    def test_rejects_bad_index(self):
        for bad in (-1, 8, 99):
            with self.assertRaises(ValueError):
                Cell(bad)


class TestGies7InformationSplit(unittest.TestCase):
    """Falsifier: an invariant distinguishing two same-parity states."""

    def test_trace_carries_no_bit(self):
        """4.0 for all eight: the anisotropic part is traceless."""
        traces = {round(Cell(i).trace(), 10) for i in range(8)}
        self.assertEqual(traces, {4.0})

    def test_j2_carries_no_bit(self):
        j2s = {round(Cell(i).j2(), 10) for i in range(8)}
        self.assertEqual(len(j2s), 1)

    def test_j3_sign_is_exactly_the_parity_bit(self):
        """This is the invariant that carries the check bit."""
        for i in range(8):
            if parity(i) == 0:
                self.assertGreater(Cell(i).j3(), 0.0, msg=f"index {i}")
            else:
                self.assertLess(Cell(i).j3(), 0.0, msg=f"index {i}")

    def test_j3_magnitude_is_common(self):
        mags = {round(abs(Cell(i).j3()), 10) for i in range(8)}
        self.assertEqual(len(mags), 1)

    def test_eigenvalues_alone_give_exactly_one_bit(self):
        """Two distinct spectra over eight states: 1 bit, no more."""
        spectra = {tuple(round(e, 10) for e in Cell(i).eigenvalues())
                   for i in range(8)}
        self.assertEqual(len(spectra), 2)

    def test_same_parity_states_are_invariant_identical(self):
        """So the remaining 2 bits must live in the eigenframe, and they do."""
        for group in ((0, 3, 5, 6), (1, 2, 4, 7)):
            ref = Cell(group[0])
            for i in group[1:]:
                c = Cell(i)
                self.assertAlmostEqual(c.trace(), ref.trace(), places=12)
                self.assertAlmostEqual(c.j2(), ref.j2(), places=12)
                self.assertAlmostEqual(c.j3(), ref.j3(), places=12)
                self.assertNotEqual(c.tensor(), ref.tensor())

    def test_unique_axis_gives_the_other_two_bits(self):
        axes = {}
        for i in range(8):
            axes.setdefault(tuple(round(c, 9) for c in Cell(i).unique_axis()),
                            []).append(i)
        self.assertEqual(len(axes), 4)
        for group in axes.values():
            self.assertEqual(len(group), 2)
            self.assertEqual(group[1], 7 - group[0])

    def test_full_three_bit_recovery_from_the_tensor(self):
        for kappa in (0.2, 0.5, 0.8):
            for i in range(8):
                self.assertEqual(decode_tensor(Cell(i, kappa).tensor()), i,
                                 msg=f"index {i}, kappa {kappa}")

    def test_four_bond_projections_suffice_inside_this_family(self):
        """Not a contradiction of TTM-2, which is about GENERAL tensors."""
        for i in range(8):
            p = Cell(i).bond_projections()
            self.assertEqual(len(p), 4)
            self.assertGreater(max(p) - min(p), 1e-6)


class TestGies6RelabellingBreaksTheGate(unittest.TestCase):
    """Falsifier: a relabelling of 0-7 that preserves the gate table."""

    @staticmethod
    def _and_table(perm):
        """AND under a relabelling: decode, AND the labels, re-encode."""
        inv = {v: k for k, v in enumerate(perm)}
        return {(a, b): inv[perm[a] & perm[b]] if (perm[a] & perm[b]) in inv
                else None
                for a in range(8) for b in range(8)}

    def test_bitwise_and_is_a_property_of_labels_not_geometry(self):
        """Relabel and the gate changes, so it is not a geometric operation."""
        identity = list(range(8))
        swapped = [0, 2, 1, 3, 4, 5, 6, 7]        # exchange labels 1 and 2
        self.assertNotEqual(self._and_table(identity), self._and_table(swapped))

    def test_geometric_relations_are_untouched_by_relabelling(self):
        """The angle between two states' directions cannot depend on labels."""
        def angle(i, j):
            u, v = Cell(i).u, Cell(j).u
            return round(math.degrees(math.acos(
                max(-1.0, min(1.0, sum(a * b for a, b in zip(u, v)))))), 6)
        # states 1 and 2 are geometrically interchangeable: same parity, and
        # the same angle to every other state up to permutation
        self.assertEqual(sorted(angle(1, k) for k in range(8)),
                         sorted(angle(2, k) for k in range(8)))

    def test_and_is_not_injective_so_it_cannot_be_reversible(self):
        """The direct contradiction: §7.5 AND is lossy, §9.2 claims reversible."""
        images = {a & b for a in range(8) for b in range(8)}
        self.assertLess(len(images), 64)
        collisions = [(a, b) for a in range(8) for b in range(8) if (a & b) == 0]
        self.assertGreater(len(collisions), 1)

    def test_nand_is_functionally_complete_which_is_the_problem(self):
        """{NOT, AND} = NAND, so §11.1's Turing-completeness question is yes,
        trivially -- and answering it exposes the issue: completeness comes from
        the relabelling to bits, not from the geometry."""
        def nand(a, b):
            return ~(a & b) & 0b111
        self.assertEqual(nand(0b111, 0b111), 0b000)
        self.assertEqual(nand(0b000, 0b111), 0b111)
        self.assertEqual(nand(0b101, 0b011), 0b110)

    def test_the_not_step_of_every_nand_is_a_frenkel_pair(self):
        """So the cost is not incidental: NAND cannot avoid it."""
        for a in range(8):
            for b in range(8):
                anded = a & b
                self.assertTrue(frenkel(anded, ~anded & 0b111))


class TestCodecBijection(unittest.TestCase):
    """GIES-4, and the fix. Exhaustive, not one example."""

    def test_all_128_tokens_are_distinct(self):
        seen = {}
        for tok in all_tokens():
            b = encode(tok)
            self.assertNotIn(b, seen, msg=f"{seen.get(b)} and {tok} -> {b}")
            seen[b] = tok
        self.assertEqual(len(seen), 8 * 4 * 4)
        self.assertEqual(len(seen), 128)

    def test_round_trip_over_every_token(self):
        for tok in all_tokens():
            self.assertEqual(decode(encode(tok)), tok)

    def test_all_four_operators_are_representable(self):
        self.assertEqual(set(OPS), {"|", "||", "/", ":"})
        codes = {encode("001" + op + "O") for op in OPS}
        self.assertEqual(len(codes), 4)

    def test_colon_and_slash_no_longer_collide(self):
        """The actual non-bijection in the old encoder."""
        self.assertNotEqual(encode("001:O"), encode("001/O"))

    def test_double_bar_does_not_collapse_onto_single_bar(self):
        self.assertNotEqual(encode("001||O"), encode("001|O"))

    def test_every_token_is_the_same_width(self):
        for tok in all_tokens():
            self.assertEqual(len(encode(tok)), TOKEN_BITS)

    def test_streams_are_unambiguous(self):
        """The defect fixed width removes: variable-width codes are not
        prefix-free, so '1' is a prefix of '11'."""
        toks = ["001||O", "001|O", "111:D", "000/X"]
        self.assertEqual(decode_stream(encode_stream(toks)), toks)

    def test_stream_length_must_be_a_multiple_of_the_token_width(self):
        with self.assertRaises(ValueError):
            decode_stream("0" * 13)

    def test_unicode_delta_is_accepted_and_normalised(self):
        self.assertEqual(encode("001|Δ"), encode("001|D"))
        self.assertEqual(decode(encode("001|Δ")), "001|D")

    def test_maps_are_mutually_inverse(self):
        for k, v in OPS.items():
            self.assertEqual(IOPS[v], k)
        for k, v in SYMS.items():
            self.assertEqual(ISYMS[v], k)

    def test_rejects_malformed_tokens(self):
        for bad in ("", "01", "0011O", "001?O", "001|Q", "abc|O", "001"):
            with self.assertRaises(ValueError):
                encode(bad)

    def test_rejects_malformed_bitstrings(self):
        for bad in ("", "0" * 6, "0" * 8, "001010x"):
            with self.assertRaises(ValueError):
                decode(bad)

    def test_wider_vertex_fields_still_bijective(self):
        seen = set()
        for tok in all_tokens(width=4):
            b = encode(tok, width=4)
            self.assertEqual(len(b), 8)
            self.assertNotIn(b, seen)
            seen.add(b)
            self.assertEqual(decode(b, width=4), tok)
        self.assertEqual(len(seen), 16 * 4 * 4)


class TestCornerNaming(unittest.TestCase):
    """The sixth occurrence of the octahedron/cube conflation."""

    def test_positions_are_cube_corners(self):
        corners = set(itertools.product((-1, 1), repeat=3))
        self.assertEqual({tuple(v) for v in CORNERS.values()}, corners)
        self.assertEqual(len(corners), 8)

    def test_an_octahedron_has_six_vertices(self):
        octa = set()
        for axis in range(3):
            for sign in (1, -1):
                v = [0, 0, 0]
                v[axis] = sign
                octa.add(tuple(v))
        self.assertEqual(len(octa), 6)
        self.assertNotEqual(len(octa), len(CORNERS))

    def test_corner_index_inverts_the_table(self):
        for i in range(8):
            self.assertEqual(corner_index(CORNERS[i]), i)
            self.assertEqual(corner_index(Cell(i).u), i)

    def test_corner_index_rejects_octahedron_vertices(self):
        with self.assertRaises(ValueError):
            corner_index((1, 0, 0))


if __name__ == "__main__":
    unittest.main()
