"""Reusable evidence checks: printed-vs-executed (T1) and claim tools. Co-authored.

Run from repository root: python tests/test_experiment_bridge_tools.py
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "experiments" / "experiment_bridge" / "evidence"


def load(name):
    spec = importlib.util.spec_from_file_location(name, EVIDENCE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PVE = load("printed_vs_executed")
CT = load("claim_tools")

TOY = '''
import json, sys, time
def main():
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    claims = []
    def pack(scope, rate_var, value, tol_frac, measurement, failure, measured, extra=None):
        claims.append({"scope": scope, "value": value, "tol_frac": tol_frac,
                       "measured": measured, "ts": time.time()})
    x = seed + 0.5
    # tolerance 0.1: the spread seen over five seeds
    pack("t::computed", "dx", 1.0, 0.1, "m", "f", x)
    pack("t::literal", "dn", 0.0, 0.0, "m", "f",
         0.0)
    pack("t::negative", "dn", 0.0, TOL, "m", "f", measured=-1.5)
    json.dump({"claims": claims}, open(f"toy_seed{seed}.json", "w"))
TOL = 0.2
main()
'''


class TestLiteralMeasured(unittest.TestCase):
    def test_a_literal_is_flagged_and_a_computed_value_is_not(self):
        rows = {r["scope"]: r for r in CT.literal_measured(TOY)}
        self.assertEqual((rows["t::computed"]["flag"], rows["t::computed"]["measured_is_literal"]),
                         (None, False))
        self.assertEqual(rows["t::literal"]["flag"], "STRUCTURAL")
        self.assertEqual(rows["t::negative"]["flag"], "STRUCTURAL")     # keyword, signed
        self.assertEqual(rows["t::negative"]["measured_expression"], "-1.5")
        line = TOY.split("\n").index("         0.0)") + 1                # the literal's own line
        self.assertEqual(rows["t::literal"]["measured_line"], line)
        self.assertEqual(rows["t::literal"]["call_line"], line - 1)

    def test_round_one_void_escape_integrity_is_structural(self):
        d = json.loads((EVIDENCE / "kimi_round1_claim_tools.json").read_text())
        flagged = [r for r in d["literal_measured"] if r["flag"]]
        self.assertEqual([r["scope"] for r in flagged],
                         ["fab::contextual::rvq::void_escape_integrity"])
        self.assertEqual(flagged[0]["measured_expression"], "0.0")
        source = (EVIDENCE / "kimi_as_received" / "toy_rvq_void.py").read_text().split("\n")
        self.assertEqual(source[flagged[0]["measured_line"] - 1].strip(), "0.0,")
        # the probe named is a real one, and it recorded what the literal asserts
        self.assertIn("silent_over_threshold_snap_count", flagged[0]["backing_probe"])
        census = json.loads((EVIDENCE / "kimi_reproduction.json").read_text())["independent_census"]
        self.assertEqual(census["silent_over_threshold_snap_count"], 0)
        for r in d["literal_measured"]:
            if not r["flag"]:
                self.assertIsNone(r["backing_probe"])


class TestToleranceProvenance(unittest.TestCase):
    def test_stated_and_unsourced(self):
        rows = {r["scope"]: r for r in CT.tolerance_provenance(TOY)}
        self.assertEqual(rows["t::computed"]["tolerance_provenance"], "STATED_IN_SOURCE")
        self.assertIn("five seeds", rows["t::computed"]["stated_reason"])
        self.assertEqual((rows["t::literal"]["tolerance_provenance"],
                          rows["t::literal"]["stated_reason"]), ("UNSOURCED", None))
        self.assertEqual((rows["t::negative"]["tol_frac_expression"],
                          rows["t::negative"]["tol_frac_is_literal"]), ("TOL", False))

    def test_round_one_has_a_row_per_claim_all_unsourced(self):
        d = json.loads((EVIDENCE / "kimi_round1_claim_tools.json").read_text())
        rows = d["tolerance_provenance"]
        self.assertEqual(len(rows), d["summary"]["claims"])
        self.assertEqual([r["tol_frac_expression"] for r in rows], ["0.25", "1e-6", "0.0", "0.5"])
        self.assertEqual({r["tolerance_provenance"] for r in rows}, {"UNSOURCED"})


class TestReplay(unittest.TestCase):
    def test_compare_claims_pairs_by_scope_and_ignores_only_ts(self):
        a = {"claims": [{"scope": "s1", "measured": 1.0, "ts": 1}, {"scope": "s2", "measured": 2}]}
        b = {"claims": [{"scope": "s2", "measured": 2}, {"scope": "s1", "measured": 1.0, "ts": 9}]}
        self.assertEqual((CT.compare_claims(a, b)["equal"], CT.compare_claims(a, b)["all_equal"]),
                         (2, True))
        b["claims"][1]["measured"] = 1.0000001
        r = CT.compare_claims(a, b)
        self.assertEqual((r["equal"], r["all_equal"]), (1, False))
        self.assertEqual(r["rows"][0]["differences"][0]["path"], "$.measured")
        r = CT.compare_claims(a, {"claims": a["claims"][:1]})         # a claim is missing
        self.assertEqual((r["claims"], r["equal"]), (2, 1))
        self.assertFalse(CT.compare_claims({"claims": []}, {"claims": []})["all_equal"])

    def test_replay_runs_on_a_copy_and_catches_a_run_that_differs(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "toy.py").write_text(TOY)
            (d / "toy_seed0.json").write_text(json.dumps({"claims": [
                {"scope": "t::computed", "value": 1.0, "tol_frac": 0.1, "measured": 0.5},
                {"scope": "t::literal", "value": 0.0, "tol_frac": 0.0, "measured": 0.0},
                {"scope": "t::negative", "value": 0.0, "tol_frac": 0.2, "measured": -1.5}]}))
            saved = (d / "toy_seed0.json").read_bytes()
            r = CT.replay(d, "toy.py", "toy_seed0.json")
            self.assertEqual((r["saved_vs_replay"]["equal"], r["replay_vs_replay"]["equal"]),
                             (3, 3))
            self.assertTrue(r["specimens_unchanged"])
            self.assertEqual((d / "toy_seed0.json").read_bytes(), saved)   # the copy was written
            # a script whose measured value moves between runs
            (d / "toy.py").write_text(TOY.replace("x = seed + 0.5", "x = time.time()"))
            r = CT.replay(d, "toy.py", "toy_seed0.json")
            self.assertEqual(r["replay_vs_replay"]["equal"], 2)
            self.assertFalse(r["replay_vs_replay"]["all_equal"])
            (d / "toy.py").write_text("raise SystemExit(3)")
            with self.assertRaises(RuntimeError):
                CT.replay(d, "toy.py", "toy_seed0.json")

    def test_round_one_replay_record(self):
        d = json.loads((EVIDENCE / "kimi_round1_claim_tools.json").read_text())
        self.assertEqual(d["summary"], {
            "claims": 4, "saved_vs_replay_equal": 4, "replay_vs_replay_equal": 4,
            "structural": ["fab::contextual::rvq::void_escape_integrity"],
            "unsourced_tolerances": 4})
        self.assertTrue(d["replay"]["specimens_unchanged"])
        for name, digest in d["replay"]["specimen_sha256"].items():
            self.assertEqual(hashlib.sha256(
                (EVIDENCE / "kimi_as_received" / name).read_bytes()).hexdigest(), digest)
        self.assertEqual((d["human_interest"], d["ai_interest"]), (None, None))


class TestPrintedVsExecuted(unittest.TestCase):
    def test_compare(self):
        same = PVE.compare(["a 0.5   ", "", "b"], ["a 0.5", "b", ""])
        self.assertEqual((same["verdict"], same["lines_equal"]), ("EQUAL", 2))
        r = PVE.compare(["Dist: 0.0608 | x", "y"], ["Dist: 0.0574 | x", "y", "z"])
        self.assertEqual((r["verdict"], r["lines_differ"]), ("DIFFERS", 2))
        self.assertEqual(r["differences"][0]["numbers_differ"],
                         [{"position": 0, "printed": "0.0608", "executed": "0.0574"}])
        self.assertEqual(r["differences"][0]["first_differing_column"], 9)
        self.assertIsNone(r["differences"][1]["printed"])                 # a line only executed

    def test_blocks_are_read_from_the_notes(self):
        text = PVE.NOTES.read_text(encoding="utf-8")
        start, body = PVE.printed_block(text, "Output of the Script")
        self.assertTrue(body[0].startswith("--- TEST 1"))
        self.assertEqual(text.split("\n")[start - 1], body[0])
        with self.assertRaises(ValueError):
            PVE.printed_block(text, "No Such Heading")
        for script, _ in PVE.SCRIPTS:                                     # fence == specimen
            self.assertTrue(PVE.source_matches(text, script)["found"], script)

    def test_snapshot_records_the_differences_the_audit_names(self):
        d = json.loads((EVIDENCE / "printed_vs_executed.json").read_text())
        self.assertEqual(d["summary"], {"ncm_bridge_as_received.py": "DIFFERS",
                                        "ncm_level_walk_as_received.py": "DIFFERS"})
        self.assertEqual(d["speaker_label"]["authenticated"], False)
        bridge, walk = (s["comparison"] for s in d["scripts"])
        pairs = [(n["printed"], n["executed"]) for x in bridge["differences"]
                 for n in x["numbers_differ"]]
        self.assertIn(("0.0608", "0.0574"), pairs)
        self.assertIn(("0.6782", "0.7348"), pairs)
        # the walk: two narrated successes and one VOID printed; three VOIDs executed
        printed = [x["printed"] for x in walk["differences"]]
        executed = [x["executed"] for x in walk["differences"]]
        self.assertEqual([("| VOID " in p) for p in printed], [False, False, True])
        self.assertEqual([("| VOID " in e) for e in executed], [True, True, True])
        self.assertEqual(d["notes_sha256"], hashlib.sha256(PVE.NOTES.read_bytes()).hexdigest())

    def test_check_recomputes_and_refuses_to_overwrite(self):
        script = str(EVIDENCE / "printed_vs_executed.py")
        snap = EVIDENCE / "printed_vs_executed.json"
        r = subprocess.run([sys.executable, script, "--check", str(snap)], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        before = snap.read_bytes()
        r = subprocess.run([sys.executable, script, "--output", str(snap)], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertEqual(snap.read_bytes(), before)
        with tempfile.TemporaryDirectory() as d:                          # a changed snapshot
            bad = json.loads(before)
            bad["scripts"][0]["comparison"]["verdict"] = "EQUAL"
            (Path(d) / "s.json").write_text(json.dumps(bad))
            r = subprocess.run([sys.executable, script, "--check", str(Path(d) / "s.json")],
                               cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)


if __name__ == "__main__":
    unittest.main()
