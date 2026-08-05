"""CI-1..5: the claim index, and the tags it makes resolvable.

Stdlib only. The index is DERIVED by scanning -- there is no maintained list
here to drift -- so these tests check the derivation rules rather than a
snapshot of their output. A test that pins the exact id count would fail on
every new claim, which trains people to loosen it.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import claims_index as CI  # noqa: E402
from playground import principles as PR  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")


class TestScanRules(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.idx = CI.scan()

    def test_it_finds_the_claim_families_this_archive_uses(self):
        fams = {k.split("-")[0] for k in self.idx}
        for f in ("FCL", "NEG", "GIES", "KEA", "ER", "R2", "EPG", "FAB",
                  "BRG", "SEED", "TTM", "SIL", "VAC"):
            self.assertIn(f, fams)

    def test_a_falsifier_call_outranks_a_mere_mention(self):
        """FCL-1 is checked by a runnable report, not just written about."""
        self.assertEqual(CI.evidence("FCL-1", self.idx), "FALSIFIER")
        self.assertIn("field/falsifiers_field_loop.py",
                      self.idx["FCL-1"]["FALSIFIER"])

    def test_a_claim_named_only_in_a_suite_is_classed_that_way(self):
        """NAMED_IN_TEST is deliberately weak: it detects that a suite
        mentions the id, not that anything asserts it."""
        by = CI.index_by_class(self.idx)
        self.assertTrue(by.get("NAMED_IN_TEST"))
        for cid in by["NAMED_IN_TEST"]:
            self.assertFalse(self.idx[cid].get("FALSIFIER"), msg=cid)
            self.assertTrue(self.idx[cid]["NAMED_IN_TEST"], msg=cid)

    def test_a_register_row_is_recorded_even_when_outranked(self):
        """NEG-2 has a test AND a register row; the row is not lost."""
        self.assertIn("Negentropic/NEG_CLAIMS.md",
                      self.idx["NEG-2"]["REGISTER"])

    def test_prose_only_claims_exist_and_are_listed(self):
        by = CI.index_by_class(self.idx)
        self.assertTrue(by.get("PROSE"))
        for cid in by["PROSE"]:
            self.assertFalse(self.idx[cid].get("FALSIFIER"), msg=cid)
            self.assertFalse(self.idx[cid].get("NAMED_IN_TEST"), msg=cid)

    def test_most_claims_have_something_executable_on_them(self):
        by = CI.index_by_class(self.idx)
        execd = len(by.get("FALSIFIER", [])) + len(by.get("NAMED_IN_TEST", []))
        self.assertGreater(execd, len(by.get("PROSE", [])))

    def test_an_unknown_id_resolves_to_not_known(self):
        # Built at runtime: a literal here would be scanned into the index
        # this test is checking, and would then resolve. The scanner reads
        # its own tests.
        r = CI.resolve("Z" * 3 + "-9", self.idx)
        self.assertFalse(r["known"])
        self.assertIsNone(r["evidence"])

    def test_a_known_id_resolves_with_its_evidence_and_files(self):
        r = CI.resolve("FCL-4", self.idx)
        self.assertTrue(r["known"])
        self.assertIn(r["evidence"], CI.CLASSES)
        self.assertTrue(r["files"])


class TestFamilyDerivation(unittest.TestCase):
    """The rule that keeps licences and hashes out without a denylist."""

    @classmethod
    def setUpClass(cls):
        cls.idx = CI.scan()

    def test_non_claim_shapes_are_excluded(self):
        """A hash, a licence and a PCB laminate all match the id pattern and
        none is a claim. Names built at runtime; see SKIP_FILES."""
        for junk in ("FNV" + "-1a", "AGPL" + "-3", "FR" + "-4",
                     "CR4" + "-5", "DC" + "-6"):
            self.assertNotIn(junk, self.idx)

    def test_a_family_qualifies_on_executable_evidence_not_a_list(self):
        fams = CI.claim_families(self.idx)
        for f in fams:
            members = [c for c in self.idx if c.split("-")[0] == f]
            self.assertTrue(
                any(self.idx[c].get("FALSIFIER")
                    or self.idx[c].get("NAMED_IN_TEST")
                    for c in members), msg=f)

    def test_a_prose_only_member_rides_in_on_its_family(self):
        """EPG-2 has no test, but EPG-1 does, so the family is real and EPG-2
        is a prose-only claim rather than noise."""
        self.assertIn("EPG-2", self.idx)
        self.assertEqual(CI.evidence("EPG-2", self.idx), "PROSE")

    def test_the_derivation_is_empty_on_an_empty_tree(self):
        d = tempfile.mkdtemp()
        self.assertEqual(CI.scan(d), {})

    def test_a_lone_prose_family_in_isolation_is_dropped(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "doc.md"), "w", encoding="utf-8") as fh:
            fh.write("we use %s laminate and the %s idea\n"
                     % ("FR" + "-4", "XYZ" + "-1"))
        self.assertEqual(CI.scan(d), {})

    def test_one_falsifier_call_admits_its_whole_family(self):
        d = tempfile.mkdtemp()
        with open(os.path.join(d, "f.py"), "w", encoding="utf-8") as fh:
            fh.write('check("%s: something", True)\n' % ("XYZ" + "-1"))
        with open(os.path.join(d, "doc.md"), "w", encoding="utf-8") as fh:
            fh.write("%s is written down only\n" % ("XYZ" + "-2"))
        idx = CI.scan(d)
        self.assertEqual(CI.evidence("XYZ" + "-1", idx), "FALSIFIER")
        self.assertEqual(CI.evidence("XYZ" + "-2", idx), "PROSE")


class TestPrincipleInstancesResolve(unittest.TestCase):
    """CI-5. The reason any of this exists: 19 of 36 instance tags were
    shorthand invented at writing time and pointed at nothing."""

    def test_every_instance_points_at_something_that_exists(self):
        bad = PR.unresolved()
        self.assertEqual(bad, [], msg="unresolved: %s" % bad)

    def test_every_instance_carries_a_location(self):
        for p in PR.principles():
            for i in p["instances"]:
                self.assertTrue(i.get("where"), msg=p["id"])
                self.assertTrue(os.path.exists(os.path.join(ROOT, i["where"])),
                                msg="%s -> %s" % (p["id"], i["where"]))

    def test_an_id_is_optional_and_absent_rather_than_invented(self):
        """16 of 36 have no real claim id. Omitting it is the honest form;
        the previous version made one up for each."""
        n = sum(len(p["instances"]) for p in PR.principles())
        withid = sum(1 for p in PR.principles() for i in p["instances"]
                     if i.get("claim"))
        self.assertGreater(withid, 0)
        self.assertLess(withid, n)

    def test_a_bad_path_is_caught(self):
        d = tempfile.mkdtemp()
        lib = {"principles": [{"id": "P-X", "name": "n", "status": "PROVISIONAL",
                               "statement": "s", "detector": "d",
                               "provisional_because": "b",
                               "instances": [{"where": "no/such/file.py",
                                              "what": "x" * 30}]}]}
        path = os.path.join(d, "P.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(lib, fh)
        bad = PR.unresolved(path)
        self.assertEqual(len(bad), 1)
        self.assertIn("no such path", bad[0][2])

    def test_a_made_up_claim_id_is_caught(self):
        d = tempfile.mkdtemp()
        lib = {"principles": [{"id": "P-X", "name": "n", "status": "PROVISIONAL",
                               "statement": "s", "detector": "d",
                               "provisional_because": "b",
                               "instances": [{"where": "README.md",
                                              "claim": "KEA-kwell",
                                              "what": "x" * 30}]}]}
        path = os.path.join(d, "P.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(lib, fh)
        bad = PR.unresolved(path)
        self.assertEqual(len(bad), 1)
        self.assertIn("resolves to no claim", bad[0][2])

    def test_cited_ids_resolve_against_claims_or_open_problems(self):
        """Two namespaces: claim ids have falsifiers, problem ids are in
        OPEN_PROBLEMS.json. AISS-1 and SI-E are the latter."""
        idx = CI.scan()
        with open(os.path.join(ROOT, "playground",
                               "OPEN_PROBLEMS.json"), encoding="utf-8") as fh:
            probs = {q["id"] for q in json.load(fh)["problems"]}
        for cid in PR.tags():
            self.assertTrue(cid in idx or cid in probs, msg=cid)

    def test_tags_omits_location_only_instances(self):
        n = sum(len(p["instances"]) for p in PR.principles())
        self.assertLess(sum(len(v) for v in PR.tags().values()), n)



class TestRegister(unittest.TestCase):
    """CI-6..8. The register carries only what scanning cannot establish."""

    @classmethod
    def setUpClass(cls):
        cls.idx = CI.scan()
        cls.reg = CI.register()

    def test_every_registered_claim_exists_in_the_tree(self):
        rep = CI.status_report(self.idx, self.reg)
        self.assertEqual(rep["ORPHANED"], [])

    def test_nothing_is_live_that_nothing_can_falsify(self):
        """The check that makes the register more than bookkeeping. It fired
        on real data: R2-8 was recorded live while the index saw only prose,
        because a Python class name cannot contain a hyphen."""
        rep = CI.status_report(self.idx, self.reg)
        self.assertEqual(rep["UNSUPPORTED_LIVE"], [])

    def test_a_dead_claim_must_say_how_it_died(self):
        rep = CI.status_report(self.idx, self.reg)
        self.assertEqual(rep["MISSING_BECAUSE"], [])
        dead = [c for c in self.reg.values() if c["status"] == "dead"]
        self.assertTrue(dead)
        for c in dead:
            self.assertGreater(len(c["because"]), 30, msg=c["id"])

    def test_the_unsupported_live_check_can_actually_fire(self):
        fake = {"XX-1": {"id": "XX-1", "family": "XX", "statement": "s",
                         "status": "live", "names": "proposal"}}
        idx = {"XX-1": {"PROSE": ["doc.md"]}}
        self.assertEqual(CI.status_report(idx, fake)["UNSUPPORTED_LIVE"],
                         ["XX-1"])

    def test_a_prose_only_claim_is_recorded_open_not_live(self):
        for cid, c in self.reg.items():
            if CI.evidence(cid, self.idx) == "PROSE":
                self.assertNotEqual(c["status"], "live", msg=cid)

    def test_every_status_is_a_known_value(self):
        for c in self.reg.values():
            self.assertIn(c["status"], CI.STATUSES, msg=c["id"])

    def test_the_namespace_ambiguity_is_recorded_not_smoothed_over(self):
        """Some ids name a proposal, some name the refutation that killed one.
        NEG-7 is dead as a proposal; ER-1 is live as a refutation."""
        self.assertEqual(self.reg["NEG-7"]["names"], "proposal")
        self.assertEqual(self.reg["NEG-7"]["status"], "dead")
        self.assertEqual(self.reg["ER-1"]["names"], "refutation")
        self.assertEqual(self.reg["ER-1"]["status"], "live")

    def test_statements_are_derived_where_they_could_be(self):
        derived = [c for c in self.reg.values()
                   if c["source"].startswith("derived:")]
        self.assertGreater(len(derived), 30)

    def test_the_neg_family_is_sourced_from_its_own_register(self):
        """NEG_CLAIMS.md predates this and stays the authority for NEG/TRI."""
        for cid, c in self.reg.items():
            if cid.split("-")[0] in ("NEG", "TRI"):
                self.assertIn("NEG_CLAIMS.md", c["source"], msg=cid)

    def test_unregistered_claims_are_reported_not_invented(self):
        rep = CI.status_report(self.idx, self.reg)
        self.assertTrue(rep["UNREGISTERED"])
        self.assertLess(len(self.reg), len(self.idx))


class TestUnderscoreForm(unittest.TestCase):
    """A Python identifier cannot contain a hyphen."""

    def test_a_claim_named_only_in_a_class_name_is_found(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "tests"))
        fam = "QQ"
        with open(os.path.join(d, "f.py"), "w", encoding="utf-8") as fh:
            fh.write('check("%s-1: it holds", True)\n' % fam)
        with open(os.path.join(d, "tests", "test_x.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("class Test%s_2Thing:\n    pass\n" % fam)
        idx = CI.scan(d)
        self.assertEqual(CI.evidence(fam + "-2", idx), "NAMED_IN_TEST")

    def test_it_only_applies_to_families_the_hyphen_form_established(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "test_x.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("FIG_2 = 1\nPART_3 = 2\n")
        self.assertEqual(CI.scan(d), {})

    def test_an_uppercase_prefix_does_not_smuggle_a_family_in(self):
        d = tempfile.mkdtemp()
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "f.py"), "w", encoding="utf-8") as fh:
            fh.write('check("QQ-1: it holds", True)\n')
        with open(os.path.join(d, "tests", "test_x.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("XQQ_9 = 1\n")
        self.assertNotIn("QQ-9", CI.scan(d))

    def test_the_real_case_that_found_this(self):
        idx = CI.scan()
        self.assertEqual(CI.evidence("R2-8", idx), "NAMED_IN_TEST")
        self.assertIn("tests/test_transient_suppression.py",
                      idx["R2-8"]["NAMED_IN_TEST"])


class TestRender(unittest.TestCase):

    def test_it_writes_one_file_per_folder_not_per_family(self):
        w = CI.render(write=False)
        self.assertIn(os.path.join("Silicon", "CLAIMS.md"), w)
        body = w[os.path.join("Silicon", "CLAIMS.md")]
        for fam in ("ER", "KEA", "R2", "TTM", "FAB"):
            self.assertIn("## %s" % fam, body)

    def test_generated_output_is_not_scanned_back_in(self):
        """Rendered tables are markdown rows shaped exactly like a register
        entry. Reading them back made the index cite its own output."""
        idx = CI.scan()
        self.assertNotIn("REGISTER", idx.get("FCL-13b", {}))

    def test_rendering_is_idempotent(self):
        a = CI.render(write=False)
        CI.render(write=True)
        self.assertEqual(a, CI.render(write=False))

    def test_unregistered_rows_are_shown_not_omitted(self):
        body = CI.render(write=False)[os.path.join("field", "CLAIMS.md")]
        self.assertIn("_no recorded statement_", body)

    def test_negentropic_is_not_overwritten(self):
        """NEG_CLAIMS.md is the source this register parses; generating a
        table there would invert the authority."""
        self.assertNotIn("Negentropic", CI.FAMILY_HOME.values())
        self.assertNotIn(os.path.join("Negentropic", "CLAIMS.md"),
                         CI.render(write=False))

    def test_every_generated_file_declares_that_it_is_generated(self):
        for path, body in CI.render(write=False).items():
            self.assertIn(CI.GENERATED_MARK, body[:400], msg=path)

if __name__ == "__main__":
    unittest.main()
