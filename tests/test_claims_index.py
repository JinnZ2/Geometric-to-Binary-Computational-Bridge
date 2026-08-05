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


if __name__ == "__main__":
    unittest.main()
