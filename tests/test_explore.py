"""EX-1..4: the cross-folder view, and the line it must not cross.

Stdlib only. The risk this file guards is not a wrong number -- it is scope.
A coverage matrix that started proposing combinations would emit a
cross-product of plausible pairs with no way to rank them and no way to be
wrong, which is P-UNFALSIFIABLE wearing the shape of a research assistant.
So several tests here are about what explore.py refuses to do.
"""

import io
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import claims_index as CI  # noqa: E402
import explore as EX  # noqa: E402
from playground import principles as PR  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def fake():
    def entry(cid, fam, screen=None, cause="MATH_ERROR"):
        c = {"id": cid, "family": fam, "statement": "s", "status": "live",
             "names": "refutation",
             "salvage": {"cause": cause, "keep": "k" * 70}}
        if screen:
            c["salvage"]["screen"] = {"name": screen, "rule": "r",
                                      "applies_when": "w",
                                      "mechanised_by": None}
        return c
    return {"A-1": entry("A-1", "A", "s1"),
            "B-1": entry("B-1", "B", "s1"),
            "B-2": entry("B-2", "B", "s2", cause="UNITS"),
            "C-1": entry("C-1", "C")}


class TestCoverage(unittest.TestCase):

    def test_a_screen_used_in_two_families_shows_in_both(self):
        cov, _ = EX.screen_coverage(fake())
        self.assertEqual(sorted(cov["s1"]), ["A", "B"])

    def test_a_claim_without_a_screen_contributes_no_cell(self):
        cov, _ = EX.screen_coverage(fake())
        self.assertNotIn("C", cov.get("s1", {}))
        self.assertNotIn("C", cov.get("s2", {}))

    def test_families_come_from_the_register_not_a_list(self):
        self.assertEqual(EX.families(fake()), ["A", "B", "C"])

    def test_the_real_matrix_is_sparse_and_that_is_the_finding(self):
        """13 screens over 15 families, mostly confined to one. The screens
        have barely travelled -- which is what the view exists to show."""
        cov, _ = EX.screen_coverage()
        spread = [len(v) for v in cov.values()]
        self.assertGreater(len(cov), 10)
        self.assertLess(sum(spread) / float(len(spread)), 2.0)

    def test_metadata_carries_the_precondition(self):
        _, meta = EX.screen_coverage()
        for name, m in meta.items():
            self.assertTrue(m["applies_when"], msg=name)
            self.assertGreater(len(m["applies_when"]), 25, msg=name)


class TestGaps(unittest.TestCase):

    def test_absent_from_is_the_complement_of_applied_in(self):
        for e in EX.gaps(fake()):
            self.assertEqual(sorted(e["applied_in"] + e["absent_from"]),
                             EX.families(fake()))
            self.assertFalse(set(e["applied_in"]) & set(e["absent_from"]))

    def test_every_gap_carries_the_precondition_to_judge_it(self):
        """An empty cell without its precondition IS a suggestion, which is
        the thing this file refuses to be."""
        for e in EX.gaps():
            self.assertTrue(e["applies_when"], msg=e["screen"])

    def test_gaps_are_ordered_by_reach(self):
        reach = [e["reach"] for e in EX.gaps()]
        self.assertEqual(reach, sorted(reach, reverse=True))

    def test_a_screen_used_everywhere_has_no_gap(self):
        reg = fake()
        reg["C-1"]["salvage"]["screen"] = {"name": "s1", "rule": "r",
                                           "applies_when": "w",
                                           "mechanised_by": None}
        g = {e["screen"]: e for e in EX.gaps(reg)}
        self.assertEqual(g["s1"]["absent_from"], [])


class TestBridges(unittest.TestCase):

    def test_a_principle_spanning_folders_is_ranked_first(self):
        bs = EX.bridges()
        self.assertEqual(bs[0]["spans"], max(e["spans"] for e in bs))

    def test_every_principle_appears_once(self):
        bs = EX.bridges()
        self.assertEqual(len(bs), len(PR.principles()))
        self.assertEqual(len({e["principle"] for e in bs}), len(bs))

    def test_folders_are_derived_from_the_instance_paths(self):
        bs = {e["principle"]: e for e in EX.bridges()}
        self.assertEqual(bs["P-SYMMETRY-COLLAPSE"]["folders"],
                         ["GEIS", "Silicon"])

    def test_the_worked_example_spans_two_folders_that_share_no_code(self):
        bs = {e["principle"]: e for e in EX.bridges()}
        self.assertEqual(bs["P-SYMMETRY-COLLAPSE"]["spans"], 2)
        self.assertEqual(bs["P-SYMMETRY-COLLAPSE"]["instances"], 2)


class TestNeighbours(unittest.TestCase):

    def test_it_finds_the_claim_sharing_a_screen(self):
        n = EX.neighbours("KEA-7")
        self.assertIn("GIES-2", n["by_screen"])

    def test_it_finds_the_principle_partner_in_another_folder(self):
        n = EX.neighbours("KEA-7")
        pairs = {p["principle"]: p["with"] for p in n["by_principle"]}
        self.assertEqual(pairs["P-SYMMETRY-COLLAPSE"], ["GIES-1"])

    def test_it_does_not_list_the_claim_as_its_own_neighbour(self):
        n = EX.neighbours("KEA-7")
        self.assertNotIn("KEA-7", n["by_screen"])
        self.assertNotIn("KEA-7", n["by_cause"])
        for p in n["by_principle"]:
            self.assertNotIn("KEA-7", p["with"])

    def test_an_unregistered_id_says_where_to_look(self):
        with self.assertRaises(KeyError) as ctx:
            EX.neighbours("FAB-4")
        self.assertIn("unregistered", str(ctx.exception))

    def test_a_claim_with_no_screen_still_has_cause_neighbours(self):
        n = EX.neighbours("B-1" if False else "SEED-1")
        self.assertTrue(n["by_cause"])


class TestFrontier(unittest.TestCase):

    def test_every_open_problem_is_listed(self):
        import json
        with open(os.path.join(ROOT, "playground", "OPEN_PROBLEMS.json"),
                  encoding="utf-8") as fh:
            n = len(json.load(fh)["problems"])
        self.assertEqual(len(EX.frontier()), n)

    def test_a_problem_in_a_screened_family_names_the_screens(self):
        f = {e["problem"]: e for e in EX.frontier()}
        self.assertTrue(f["FCL-9"]["screens_in_family"])

    def test_a_problem_in_an_unscreened_family_names_none(self):
        f = {e["problem"]: e for e in EX.frontier()}
        self.assertEqual(f["AISS-1"]["screens_in_family"], [])


class TestItRefusesToPropose(unittest.TestCase):
    """EX-4. The scope guard. These are the assertions that keep this file
    from becoming a generator."""

    def setUp(self):
        with open(os.path.join(ROOT, "explore.py"), encoding="utf-8") as fh:
            self.src = fh.read()

    def test_it_stores_nothing(self):
        for write_mode in ('"w"', "'w'", '"a"', "'a'"):
            self.assertNotIn(write_mode, self.src)

    def test_the_docstring_states_the_line_it_will_not_cross(self):
        flat = " ".join(EX.__doc__.split())
        self.assertIn("does not propose combinations", flat)
        self.assertIn("P-UNFALSIFIABLE", flat)
        self.assertIn("Deciding which empty cell is worth an afternoon is a "
                      "judgement", flat)

    def test_it_refuses_the_higher_dimensional_generator_reading(self):
        """8 states to 32 to some larger polytope is a physics question. A
        script that enumerated them with no falsifier attached would be the
        same defect the archive keeps removing."""
        flat = " ".join(EX.__doc__.split())
        self.assertIn("higher dimensions", flat)
        self.assertIn("not something a script can enumerate", flat)

    def test_no_output_asserts_that_a_gap_should_be_filled(self):
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            for cmd in ("coverage", "gaps", "bridges", "frontier"):
                EX.main(["explore.py", cmd])
        finally:
            sys.stdout = old
        out = buf.getvalue().lower()
        for pushy in ("you should", "recommend", "try applying",
                      "consider applying", "likely to work"):
            self.assertNotIn(pushy, out)

    def test_the_matrix_says_an_empty_cell_is_not_a_suggestion(self):
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            EX.main(["explore.py", "coverage"])
        finally:
            sys.stdout = old
        self.assertIn("not a suggestion", buf.getvalue())


class TestCli(unittest.TestCase):

    def _run(self, *args):
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            code = EX.main(["explore.py"] + list(args))
        finally:
            sys.stdout = old
        return code, buf.getvalue()

    def test_every_subcommand_runs(self):
        for cmd in (("coverage",), ("gaps",), ("bridges",), ("frontier",),
                    ("neighbours", "ER-1")):
            code, out = self._run(*cmd)
            self.assertEqual(code, 0, msg=cmd)
            self.assertTrue(out.strip(), msg=cmd)

    def test_an_unknown_subcommand_is_refused(self):
        code, out = self._run("imagine")
        self.assertEqual(code, 2)
        self.assertIn("usage", out)

    def test_neighbours_without_an_id_is_refused(self):
        self.assertEqual(self._run("neighbours")[0], 2)

    def test_it_reads_the_same_register_the_other_tools_do(self):
        self.assertEqual(EX.families(), sorted({c["family"] for c
                                                in CI.register().values()}))


if __name__ == "__main__":
    unittest.main()
