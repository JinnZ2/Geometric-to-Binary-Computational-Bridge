"""RV-1..6: the archive, and whether the review can actually fire.

Stdlib only. A verdict is not a fact -- it is a fact under a set of gates, at
a commit, with stated tolerances, and all three move. The review exists to
notice when they have, so every finding it can emit is tested by constructing
the situation that must produce it.

The one that matters most is RV-2. The dangerous case is not "a rejected
candidate now passes" -- knowledge moves, that is fine and expected. It is a
candidate that still passes because it quietly loosened its own tolerance.
"""

import io
import json
import os
import sys
import tempfile
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from playground import playground as P  # noqa: E402
from playground import review as R  # noqa: E402


def synthetic(**kw):
    m = types.ModuleType(kw.pop("name", "synthetic"))
    m.PROBLEM = kw.pop("PROBLEM", "FCL-12b")
    m.CLAIM = "a claim"
    m.KIND = "CODE"
    m.AUTHOR = "test"
    m.NEEDS_NULL = False
    m.MATERIAL = None
    m.THRESH = kw.pop("THRESH", 1.0)
    m.solve = lambda: 5.0
    m.broken = lambda: -5.0
    m.checks = kw.pop("checks", lambda a: [("positive", a > 0, str(a))])
    return m


class TestThresholdExtraction(unittest.TestCase):
    """What gets diffed, and what deliberately does not."""

    def test_it_picks_up_module_level_constants(self):
        self.assertEqual(P.thresholds(synthetic(THRESH=0.25))["THRESH"], 0.25)

    def test_it_excludes_the_contract_fields(self):
        t = P.thresholds(synthetic())
        for f in P.CONTRACT_FIELDS:
            self.assertNotIn(f, t)

    def test_it_keeps_sequences_of_scalars(self):
        m = synthetic()
        m.RIDERS = (6.0, 12.0)
        self.assertEqual(P.thresholds(m)["RIDERS"], [6.0, 12.0])

    def test_the_real_candidate_exposes_the_numbers_that_decide_it(self):
        t = P.thresholds(P.load("lomb_scargle_gls"))
        self.assertIn("TOL_FRAC", t)
        self.assertIn("NOISE_95", t)

    def test_a_docstring_edit_does_not_move_the_thresholds(self):
        """Hashing whole source would fire on a typo fix. This must not."""
        a = synthetic()
        b = synthetic()
        b.__doc__ = "completely different prose"
        self.assertEqual(P.thresholds(a), P.thresholds(b))


class TestArchiveWriting(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "A.jsonl")

    def test_it_records_the_verdict_and_the_reasoning(self):
        r = P.archive("tautology_demo", "ARCHIVED", "kept for provenance",
                      "checks cannot fail", "different checks", path=self.path)
        self.assertEqual(r["verdict"], "REJECTED_UNFALSIFIABLE")
        self.assertEqual(r["residence"], "ARCHIVED")
        self.assertEqual(r["residence_reason"], "kept for provenance")

    def test_it_records_the_numbers_that_decided_it(self):
        r = P.archive("lomb_scargle_gls", "ACTIVE", "x", "y", "z",
                      path=self.path)
        self.assertEqual(r["thresholds"]["TOL_FRAC"], 0.01)
        self.assertTrue(r["checks_sha"])

    def test_an_unknown_residence_is_refused(self):
        with self.assertRaises(ValueError):
            P.archive("tautology_demo", "SOMEWHERE", "x", "y", "z",
                      path=self.path)

    def test_the_reasoning_fields_cannot_be_left_blank(self):
        """The whole point is the part a machine cannot supply."""
        for blank in ("", "   "):
            for i in range(3):
                args = ["a reason"] * 3
                args[i] = blank
                with self.assertRaises(ValueError):
                    P.archive("tautology_demo", "ARCHIVED", *args,
                              path=self.path)

    def test_the_last_write_wins(self):
        P.archive("tautology_demo", "ARCHIVED", "first", "y", "z",
                  path=self.path)
        P.archive("tautology_demo", "ACTIVE", "second", "y", "z",
                  path=self.path)
        recs = P.archive_records(self.path)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs["tautology_demo"]["residence_reason"], "second")

    def test_a_missing_archive_is_empty_not_an_error(self):
        self.assertEqual(P.archive_records(self.path + ".nope"), {})


class TestReviewFindings(unittest.TestCase):

    def _rec(self, name, **over):
        mod = P.load(name)
        r = {"candidate": name, "problem": mod.PROBLEM, "residence": "ACTIVE",
             "verdict": P.evaluate(name)["verdict"],
             "thresholds": P.thresholds(mod), "checks_sha": P.checks_sha(mod),
             "revisit_if_changed": [], "would_change_verdict": "-"}
        r.update(over)
        return r

    def test_an_unchanged_candidate_is_unchanged(self):
        r = R.review_one("tautology_demo", self._rec("tautology_demo"))
        self.assertEqual(r["finding"], "UNCHANGED")

    def test_a_changed_verdict_is_reported(self):
        r = R.review_one("tautology_demo",
                         self._rec("tautology_demo", verdict="SURVIVES"))
        self.assertEqual(r["finding"], "VERDICT_CHANGED")
        self.assertEqual(r["was"], "SURVIVES")
        self.assertEqual(r["now"], "REJECTED_UNFALSIFIABLE")

    def test_a_loosened_tolerance_fires_even_though_the_verdict_holds(self):
        """RV-2. The case the whole file exists for."""
        rec = self._rec("lomb_scargle_gls")
        rec["thresholds"] = dict(rec["thresholds"], TOL_FRAC=0.001)
        r = R.review_one("lomb_scargle_gls", rec)
        self.assertEqual(r["was"], r["now"])
        self.assertEqual(r["finding"], "THRESHOLDS_MOVED")
        self.assertIn("TOL_FRAC 0.001 -> 0.01", r["deltas"])

    def test_a_watched_constant_upgrades_the_finding_to_triggered(self):
        rec = self._rec("lomb_scargle_gls",
                        revisit_if_changed=["TOL_FRAC"])
        rec["thresholds"] = dict(rec["thresholds"], TOL_FRAC=0.001)
        r = R.review_one("lomb_scargle_gls", rec)
        self.assertEqual(r["finding"], "TRIGGERED")
        self.assertEqual(r["triggered"], ["TOL_FRAC 0.001 -> 0.01"])

    def test_an_unwatched_constant_does_not_trigger(self):
        rec = self._rec("lomb_scargle_gls", revisit_if_changed=["NOISE_95"])
        rec["thresholds"] = dict(rec["thresholds"], TOL_FRAC=0.001)
        r = R.review_one("lomb_scargle_gls", rec)
        self.assertEqual(r["finding"], "THRESHOLDS_MOVED")
        self.assertEqual(r["triggered"], [])

    def test_rewritten_checks_are_reported(self):
        r = R.review_one("tautology_demo",
                         self._rec("tautology_demo", checks_sha="deadbeef"))
        self.assertEqual(r["finding"], "CHECKS_REWRITTEN")

    def test_an_added_constant_is_a_delta_too(self):
        rec = self._rec("tautology_demo")
        rec["thresholds"] = {}
        r = R.review_one("tautology_demo", rec)
        self.assertTrue(all("<absent> ->" in d for d in r["deltas"])
                        or r["finding"] == "UNCHANGED")

    def test_verdict_change_outranks_a_threshold_change(self):
        rec = self._rec("tautology_demo", verdict="SURVIVES")
        rec["thresholds"] = {"GONE": 1}
        self.assertEqual(R.review_one("tautology_demo", rec)["finding"],
                         "VERDICT_CHANGED")


class TestReviewSweep(unittest.TestCase):

    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "A.jsonl")

    def test_a_candidate_with_no_archive_entry_is_unrecorded(self):
        rows = R.review(self.path)
        self.assertTrue(rows)
        self.assertTrue(all(r["finding"] == "UNRECORDED" for r in rows))

    def test_an_archive_entry_with_no_module_is_orphaned(self):
        with open(self.path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"candidate": "long_gone",
                                 "verdict": "FAILED", "problem": "FCL-9",
                                 "residence": "ARCHIVED"}) + "\n")
        rows = {r["candidate"]: r["finding"] for r in R.review(self.path)}
        self.assertEqual(rows["long_gone"], "ORPHANED")

    def test_the_shipped_archive_describes_reality(self):
        """If this fails, re-record; do not loosen it."""
        stale = [r for r in R.review() if r["finding"] not in R.CLEAN]
        self.assertEqual(stale, [], msg="stale: %s"
                         % [(r["candidate"], r["finding"]) for r in stale])

    def test_the_report_returns_the_stale_count_and_prints(self):
        buf = io.StringIO()
        n = R.report(R.review(self.path), out=buf)
        self.assertGreater(n, 0)
        self.assertIn("UNRECORDED", buf.getvalue())

    def test_a_clean_report_says_so(self):
        buf = io.StringIO()
        n = R.report(R.review(), out=buf)
        self.assertEqual(n, 0)
        self.assertIn("archive describes reality", buf.getvalue())

    def test_the_cli_exit_code_tracks_staleness(self):
        self.assertEqual(R.main(["--quiet"]), 0)


class TestShippedArchiveContent(unittest.TestCase):
    """The reasoning fields are the deliverable; check they carry weight."""

    def setUp(self):
        self.recs = P.archive_records()

    def test_every_candidate_on_disk_is_recorded(self):
        self.assertEqual(set(self.recs), set(P.candidates()))

    def test_every_record_names_a_real_problem_and_residence(self):
        ids = {p["id"] for p in P.problems()["problems"]}
        for n, r in self.recs.items():
            self.assertIn(r["problem"], ids, msg=n)
            self.assertIn(r["residence"], P.RESIDENCE, msg=n)

    def test_every_record_says_what_would_flip_it(self):
        for n, r in self.recs.items():
            self.assertGreater(len(r["would_change_verdict"]), 40, msg=n)

    def test_the_self_test_candidate_is_marked_as_not_provisional(self):
        r = self.recs["tautology_demo"]
        self.assertEqual(r["verdict"], "REJECTED_UNFALSIFIABLE")
        self.assertIn("not provisional", r["would_change_verdict"])

    def test_the_passing_candidate_records_that_it_was_not_graduated(self):
        r = self.recs["lomb_scargle_gls"]
        self.assertEqual(r["verdict"], "SURVIVES")
        self.assertEqual(r["residence"], "ACTIVE")
        self.assertIn("NOT graduated", r["residence_reason"])

    def test_records_carry_the_commit_they_were_scored_at(self):
        for n, r in self.recs.items():
            self.assertTrue(r.get("commit"), msg=n)



class TestPrinciples(unittest.TestCase):
    """PR-1..5: the compressed failure shapes, and the rule that keeps the
    library from inflating."""

    def setUp(self):
        from playground import principles as PR
        self.PR = PR

    def test_a_principle_needs_two_independent_instances(self):
        """One instance is an anecdote. The status is COMPUTED from the
        instance count, so an entry cannot be promoted by editing a field."""
        for p in self.PR.principles():
            want = ("ESTABLISHED" if len(p["instances"]) >= self.PR.MIN_INSTANCES
                    else "PROVISIONAL")
            self.assertEqual(self.PR.status_of(p), want, msg=p["id"])

    def test_the_declared_status_matches_the_computed_one(self):
        self.assertEqual(self.PR.disagreements(), [])

    def test_a_provisional_entry_says_why_it_is_provisional(self):
        for p in self.PR.principles():
            if self.PR.status_of(p) == "PROVISIONAL":
                self.assertTrue(p.get("provisional_because"), msg=p["id"])

    def test_every_principle_is_well_formed(self):
        for p in self.PR.principles():
            for k in ("id", "name", "statement", "detector", "instances"):
                self.assertIn(k, p, msg=p.get("id"))
            self.assertTrue(p["detector"].strip(), msg=p["id"])
            for i in p["instances"]:
                self.assertTrue(i["tag"].strip(), msg=p["id"])
                self.assertGreater(len(i["what"]), 20, msg=p["id"])

    def test_ids_are_unique_and_so_are_instance_tags_within_a_principle(self):
        ids = [p["id"] for p in self.PR.principles()]
        self.assertEqual(len(ids), len(set(ids)))
        for p in self.PR.principles():
            tags = [i["tag"] for i in p["instances"]]
            self.assertEqual(len(tags), len(set(tags)), msg=p["id"])

    def test_an_unmechanised_principle_says_so_rather_than_going_quiet(self):
        gaps = [p for p in self.PR.principles() if not p.get("mechanised_by")]
        self.assertTrue(gaps, "if nothing is a gap, the list has stopped "
                              "being honest")
        self.assertLess(len(gaps), len(self.PR.principles()))

    def test_coverage_counts_agree_with_the_library(self):
        c = self.PR.coverage()
        self.assertEqual(c["total"], len(self.PR.principles()))
        self.assertEqual(c["instances"],
                         sum(len(p["instances"])
                             for p in self.PR.principles()))
        self.assertEqual(len(c["gaps"]) + c["mechanised"], c["total"])

    def test_lookup_of_an_unknown_id_lists_the_known_ones(self):
        with self.assertRaises(KeyError) as ctx:
            self.PR.principle("P-NOPE")
        self.assertIn("P-UNFALSIFIABLE", str(ctx.exception))

    def test_the_shape_that_caught_its_own_auditor_is_recorded(self):
        """P-SELF-SUPPLIED-FALSIFIER cites the playground's own candidate."""
        p = self.PR.principle("P-SELF-SUPPLIED-FALSIFIER")
        self.assertIn("PG-lomb", [i["tag"] for i in p["instances"]])
        self.assertIsNone(p.get("mechanised_by"))

    def test_two_formalisms_that_never_met_share_one_principle(self):
        p = self.PR.principle("P-SYMMETRY-COLLAPSE")
        self.assertEqual({"GIES-1", "KEA-7"},
                         {i["tag"] for i in p["instances"]})

    def test_match_reports_cited_and_unknown_separately(self):
        m = self.PR.match({"principles": ["P-UNFALSIFIABLE", "P-MADE-UP"]})
        self.assertEqual(m["cited"], ["P-UNFALSIFIABLE"])
        self.assertEqual(m["unknown"], ["P-MADE-UP"])

    def test_match_does_not_infer_shapes_from_source(self):
        """Inferring a failure shape from code would look clever and be
        unfalsifiable -- which is the shape it would claim to detect."""
        self.assertEqual(self.PR.match({})["cited"], [])


class TestArchiveCitesPrinciples(unittest.TestCase):

    def setUp(self):
        self.recs = P.archive_records()
        self.path = os.path.join(tempfile.mkdtemp(), "A.jsonl")

    def test_an_unknown_principle_id_is_refused(self):
        with self.assertRaises(ValueError) as ctx:
            P.archive("tautology_demo", "ARCHIVED", "x", "y", "z",
                      principles=["P-INVENTED"], path=self.path)
        self.assertIn("unknown principle", str(ctx.exception))

    def test_the_self_test_cites_the_shape_it_demonstrates(self):
        self.assertEqual(self.recs["tautology_demo"]["principles"],
                         ["P-UNFALSIFIABLE"])

    def test_the_passing_candidate_cites_a_shape_against_itself(self):
        r = self.recs["lomb_scargle_gls"]
        self.assertEqual(r["verdict"], "SURVIVES")
        self.assertIn("P-SELF-SUPPLIED-FALSIFIER", r["principles"])

    def test_every_cited_principle_exists(self):
        from playground import principles as PR
        known = {p["id"] for p in PR.principles()}
        for n, r in self.recs.items():
            for c in r.get("principles", []):
                self.assertIn(c, known, msg=n)


class TestSourceRecovery(unittest.TestCase):
    """Compression is for transfer. Re-execution needs the source, and git
    already has it -- the archive only has to point."""

    def test_every_record_carries_a_git_blob_sha(self):
        for n, r in P.archive_records().items():
            self.assertTrue(r.get("source_sha"), msg=n)
            self.assertEqual(len(r["source_sha"]), 40, msg=n)

    def test_the_sha_resolves_to_the_current_source(self):
        import subprocess
        n = "tautology_demo"
        sha = P.archive_records()[n]["source_sha"]
        got = subprocess.run(["git", "cat-file", "-p", sha],
                             cwd=os.path.join(os.path.dirname(__file__), ".."),
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(got.returncode, 0)
        self.assertIn("REJECTED_UNFALSIFIABLE", got.stdout)

    def test_a_missing_candidate_has_no_sha(self):
        self.assertIsNone(P.source_sha("never_existed"))

    def test_an_orphan_report_names_the_recovery_command(self):
        path = os.path.join(tempfile.mkdtemp(), "A.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"candidate": "gone", "verdict": "FAILED",
                                 "problem": "FCL-9", "residence": "ARCHIVED",
                                 "source_sha": "a" * 40}) + "\n")
        buf = io.StringIO()
        R.report(R.review(path), out=buf)
        self.assertIn("git cat-file -p " + "a" * 40, buf.getvalue())

    def test_an_orphan_without_a_sha_says_it_is_unrecoverable(self):
        path = os.path.join(tempfile.mkdtemp(), "A.jsonl")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(json.dumps({"candidate": "gone", "verdict": "FAILED",
                                 "problem": "FCL-9",
                                 "residence": "ARCHIVED"}) + "\n")
        buf = io.StringIO()
        R.report(R.review(path), out=buf)
        self.assertIn("they do not restore the module", buf.getvalue())

if __name__ == "__main__":
    unittest.main()
