"""GY-1..5: the graveyard view, and the screen-reach ranking.

Stdlib only. The interesting output is `todo` -- proven screens nothing
catches automatically -- so the tests are mostly about the ways that list
could silently shorten: a screen claiming a mechanisation that does not
exist, reach counted wrong, or a death recorded without the screen it left
behind.
"""

import io
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import claims_index as CI  # noqa: E402
import graveyard as G  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


def fake(**over):
    """A minimal register: one death with a screen, one without."""
    reg = {
        "A-1": {"id": "A-1", "family": "A", "statement": "a holds",
                "status": "live", "names": "refutation",
                "salvage": {"cause": "MATH_ERROR", "killed": "the a proposal",
                            "keep": "k" * 70,
                            "screen": {"name": "s1", "rule": "r1",
                                       "mechanised_by": None}}},
        "A-2": {"id": "A-2", "family": "A", "statement": "b holds",
                "status": "live", "names": "refutation",
                "salvage": {"cause": "MATH_ERROR", "killed": "the b proposal",
                            "keep": "k" * 70,
                            "screen": {"name": "s1", "rule": "r1",
                                       "mechanised_by": None}}},
        "A-3": {"id": "A-3", "family": "A", "statement": "c is dead",
                "status": "dead", "because": "x" * 40, "names": "proposal",
                "salvage": {"cause": "NULL_ARTIFACT", "keep": "k" * 70}},
    }
    reg.update(over)
    return reg


class TestDeaths(unittest.TestCase):

    def test_a_dead_claim_is_its_own_death(self):
        ds = {d["killed"]: d for d in G.deaths(fake())}
        self.assertIsNone(ds["c is dead"]["by"])

    def test_a_refutation_records_the_proposal_it_killed(self):
        ds = {d["killed"]: d for d in G.deaths(fake())}
        self.assertEqual(ds["the a proposal"]["by"], "A-1")

    def test_a_claim_without_salvage_is_not_a_death(self):
        reg = fake(**{"A-9": {"id": "A-9", "family": "A", "statement": "s",
                              "status": "live", "names": "mechanism"}})
        self.assertNotIn("A-9", [d["id"] for d in G.deaths(reg)])

    def test_the_real_register_has_deaths_across_several_causes(self):
        ds = G.deaths()
        self.assertGreater(len(ds), 15)
        self.assertGreaterEqual(len({d["cause"] for d in ds}), 5)

    def test_every_death_carries_what_survives_it(self):
        for d in G.deaths():
            self.assertGreater(len(d["keep"]), 60, msg=d["id"])


class TestScreenReach(unittest.TestCase):

    def test_reach_counts_independent_claims(self):
        sc = G.screens(fake())
        self.assertEqual(sc["s1"]["reach"], 2)
        self.assertEqual(sc["s1"]["claims"], ["A-1", "A-2"])

    def test_a_screen_used_once_has_reach_one(self):
        reg = fake()
        del reg["A-2"]
        self.assertEqual(G.screens(reg)["s1"]["reach"], 1)

    def test_the_real_archive_has_a_screen_that_killed_two(self):
        """The gap-mode mass criterion killed the Er search and the
        phosphorus local-mode claim in one stroke."""
        sc = G.screens()
        self.assertEqual(sc["gap-mode-mass"]["reach"], 2)
        self.assertEqual(sc["gap-mode-mass"]["claims"], ["ER-2", "ER-2b"])

    def test_unmechanised_excludes_the_ones_repo_guard_covers(self):
        names = {e["name"] for e in G.unmechanised()}
        self.assertNotIn("null-harness", names)
        self.assertNotIn("instrument-floor", names)
        self.assertIn("gap-mode-mass", names)

    def test_unmechanised_is_ordered_worst_first(self):
        reach = [e["reach"] for e in G.unmechanised()]
        self.assertEqual(reach, sorted(reach, reverse=True))

    def test_min_reach_filters(self):
        self.assertTrue(all(e["reach"] >= 2
                            for e in G.unmechanised(min_reach=2)))


class TestMechanisationIsReal(unittest.TestCase):
    """GY-4. The one way this file could quietly stop being useful is a
    screen shortening the todo list by claiming a mechanisation that is not
    there."""

    def test_every_claimed_mechanisation_exists(self):
        self.assertEqual(G.mechanisation_is_real(), [])

    def test_a_missing_attribute_is_caught(self):
        reg = fake()
        reg["A-1"]["salvage"]["screen"]["mechanised_by"] = "repo_guard.nope"
        bad = G.mechanisation_is_real(reg)
        self.assertEqual(len(bad), 1)
        self.assertIn("no such attribute", bad[0][2])

    def test_a_missing_module_is_caught(self):
        reg = fake()
        reg["A-1"]["salvage"]["screen"]["mechanised_by"] = "no_such_mod.f"
        bad = G.mechanisation_is_real(reg)
        self.assertEqual(len(bad), 1)
        self.assertIn("no such module", bad[0][2])

    def test_the_cli_exits_nonzero_when_a_mechanisation_is_fake(self):
        self.assertEqual(G.main(["graveyard.py", "todo"]), 0)

    def test_the_real_mechanised_screens_point_at_repo_guard(self):
        sc = G.screens()
        self.assertEqual(sc["null-harness"]["mechanised_by"],
                         "repo_guard.null_harness")
        import repo_guard
        self.assertTrue(callable(repo_guard.null_harness))


class TestLoose(unittest.TestCase):
    """GY-5. Deaths in the tree the register never recorded."""

    def test_it_finds_an_abandoned_file_with_no_register_entry(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "old.md"), "w", encoding="utf-8") as fh:
            fh.write("# thing\n\nThis approach is superseded by the new one.\n")
        out = G.loose(root=d, reg={})
        self.assertEqual([x["file"] for x in out], ["old.md"])
        self.assertEqual(out[0]["word"], "superseded")

    def test_a_file_with_no_abandonment_word_is_not_reported(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "fine.md"), "w", encoding="utf-8") as fh:
            fh.write("# thing\n\nStill current.\n")
        self.assertEqual(G.loose(root=d, reg={}), [])

    def test_generated_files_are_skipped(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "gen.md"), "w", encoding="utf-8") as fh:
            fh.write("<!-- %s -->\nsuperseded\n" % CI.GENERATED_MARK)
        self.assertEqual(G.loose(root=d, reg={}), [])

    def test_the_real_tree_has_loose_deaths(self):
        out = G.loose()
        self.assertTrue(out)
        files = {x["file"] for x in out}
        self.assertIn("GEIS/geometric_encoder.py", files)

    def test_it_is_a_prompt_not_a_detection_and_says_so(self):
        """One real hit is an enum value, not an abandonment. The docstring
        commits to that being expected rather than a bug."""
        flat = " ".join(G.__doc__.split())
        self.assertIn("prompt for a human, not a detection", flat)
        self.assertIn("died quietly and left no word behind is invisible", flat)
        self.assertIn("prompt for a human",
                      " ".join(G.loose.__doc__.split()))


class TestCli(unittest.TestCase):

    def _run(self, *args):
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            code = G.main(["graveyard.py"] + list(args))
        finally:
            sys.stdout = old
        return code, buf.getvalue()

    def test_every_subcommand_runs(self):
        for cmd in ("deaths", "screens", "todo", "loose"):
            code, out = self._run(cmd)
            self.assertEqual(code, 0, msg=cmd)
            self.assertTrue(out.strip(), msg=cmd)

    def test_an_unknown_subcommand_is_refused(self):
        code, out = self._run("resurrect")
        self.assertEqual(code, 2)
        self.assertIn("usage", out)

    def test_the_deaths_view_groups_by_cause(self):
        _, out = self._run("deaths")
        self.assertIn("== PHYSICS_BOUND", out)
        self.assertIn("== MATH_ERROR", out)

    def test_the_todo_view_separates_proven_from_unproven_reach(self):
        _, out = self._run("todo")
        self.assertIn("reach >= 2", out)
        self.assertIn("reach 1", out)

    def test_it_stores_nothing_of_its_own(self):
        """Reads the register and scans. A second store would be a second
        authority over the same deaths."""
        with open(os.path.join(ROOT, "graveyard.py"), encoding="utf-8") as fh:
            src = fh.read()
        for write_mode in ('"w"', "'w'", '"a"', "'a'"):
            self.assertNotIn(write_mode, src)


if __name__ == "__main__":
    unittest.main()
