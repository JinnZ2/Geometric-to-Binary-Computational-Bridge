"""T4 snapshot_class: classes and the resume rule, from EBR_016 to EBR_019. Co-authored.

Run from repository root: python tests/test_experiment_bridge_snapshot.py
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.snapshot import snapshot_class as S  # noqa: E402

BENCH = ROOT / "experiments" / "experiment_bridge"
RECORD = json.loads(S.RECORD.read_text())
ROWS = {r["scope"].split("snapshot::")[1]: r for r in S.classify_claims(RECORD)}

EXACT = {"content": "FULL_STATE", "fidelity": "EXACT", "growth": None}
SINK = {"content": "FULL_STATE", "fidelity": "LOSSY",
        "growth": RECORD["drift_sink"]["horizon_error_over_delta"]}
LORENZ = {"content": "FULL_STATE", "fidelity": "LOSSY",
          "growth": RECORD["drift_lorenz"]["horizon_error_over_delta"]}
COUNTS = {"content": "SUMMARY", "fidelity": None, "growth": None}


class TestFromTheFindings(unittest.TestCase):
    def test_ebr_016_exact_resume_is_always_allowed(self):
        for name in ("fib::word_resume_exact", "fib::count_resume_exact", "float::bitwise_resume"):
            r = ROWS[name]
            self.assertEqual(r["class"], "CONTEXT_FREE_EXACT", name)
            self.assertEqual({k: v["decision"] for k, v in r["resume"].items()},
                             {"bare": "ALLOWED", "with_bound": "ALLOWED", "with_refresh": "ALLOWED"})
        # the measurements behind the class: zero mismatches in the record
        a = RECORD["system_a"]
        self.assertEqual((a["word_resume"]["mismatched_levels"],
                          a["count_resume"]["mismatched_levels"],
                          RECORD["drift_sink"]["bitwise_resume_mismatches"],
                          RECORD["drift_lorenz"]["bitwise_resume_mismatches"]), (0, 0, 0, 0))

    def test_ebr_017_lossy_on_the_decaying_system_needs_a_stated_bound(self):
        r = ROWS["sink::lossy_snapshot_drift"]
        self.assertEqual(r["class"], "STABLE_LOSSY")
        self.assertAlmostEqual(r["snapshot"]["growth"], 0.0498, places=4)
        self.assertEqual(r["resume"]["bare"]["decision"], "REFUSED")
        self.assertIn("stated bound", r["resume"]["bare"]["reason"])
        ok = S.resume(SINK, {"bound": 3.0})
        self.assertEqual((ok["decision"], ok["condition"]), ("ALLOWED", {"bound": 3.0}))
        ok = S.resume(SINK, {"refresh_tau": 0.1})                  # a threshold is a bound
        self.assertEqual((ok["decision"], ok["condition"]), ("ALLOWED", {"refresh_tau": 0.1}))

    def test_ebr_018_lorenz_needs_refresh_and_a_bound_alone_is_refused(self):
        r = ROWS["lorenz::lossy_snapshot_drift"]
        self.assertEqual(r["class"], "CHAOTIC_REFRESH")
        self.assertGreater(r["snapshot"]["growth"], 16000)
        self.assertEqual(S.resume(LORENZ)["decision"], "REFUSED")
        bound = S.resume(LORENZ, {"bound": 100.0})                 # the specimen's own band
        self.assertEqual(bound["decision"], "REFUSED")
        self.assertIn("a bound alone does not hold", bound["reason"])
        ok = S.resume(LORENZ, {"refresh_tau": 0.5})
        self.assertEqual((ok["decision"], ok["condition"]["refresh_tau"]), ("ALLOWED", 0.5))
        # the refresh claim in the record carries its own tau and is allowed with it
        ad = ROWS["lorenz::adaptive_refresh_bound"]
        self.assertEqual((ad["class"], ad["refresh_declared_by_the_claim"],
                          ad["resume"]["with_refresh"]["decision"]),
                         ("CHAOTIC_REFRESH", 0.5, "ALLOWED"))

    def test_ebr_019_a_summary_is_void_whatever_is_offered(self):
        r = ROWS["fib::word_from_counts"]
        self.assertEqual((r["class"], r["claim_verdict"]), ("SUMMARY_ONLY", "void"))
        for request in (None, {"bound": 1.0}, {"refresh_tau": 0.5},
                        {"bound": 1.0, "refresh_tau": 0.5}):
            got = S.resume(COUNTS, request)
            self.assertEqual(got["decision"], "VOID", request)
        self.assertIn("does not determine the state", S.resume(COUNTS)["reason"])
        # the same counts are the full state of the count chain: a different snapshot
        self.assertEqual(ROWS["fib::count_resume_exact"]["class"], "CONTEXT_FREE_EXACT")


class TestRule(unittest.TestCase):
    def test_all_ten_claims_classified_and_counted(self):
        self.assertEqual(len(ROWS), 10)
        rec = S.build()
        self.assertEqual(rec["unclassified"], [])
        self.assertEqual(rec["counts"], {"CONTEXT_FREE_EXACT": 5, "STABLE_LOSSY": 2,
                                         "CHAOTIC_REFRESH": 2, "SUMMARY_ONLY": 1})
        self.assertEqual(sum(rec["counts"].values()), 10)
        self.assertEqual((rec["human_interest"], rec["ai_interest"], rec["status"]),
                         (None, None, "PROPOSED"))
        self.assertEqual(rec, json.loads((BENCH / "snapshot" / "classes_seed0.json").read_text()))
        self.assertEqual(rec["record"]["sha256"], hashlib.sha256(S.RECORD.read_bytes()).hexdigest())

    def test_the_growth_limit_is_one_and_the_edge_is_stable(self):
        lossy = lambda g: {"content": "FULL_STATE", "fidelity": "LOSSY", "growth": g}   # noqa: E731
        self.assertEqual(S.classify(lossy(1.0))["class"], "STABLE_LOSSY")
        self.assertEqual(S.classify(lossy(1.0000001))["class"], "CHAOTIC_REFRESH")
        self.assertEqual(S.classify(lossy(0))["class"], "STABLE_LOSSY")

    def test_growth_is_never_assumed(self):
        for g in (None, "small", True, float("nan"), float("inf"), -0.1):
            c = S.classify({"content": "FULL_STATE", "fidelity": "LOSSY", "growth": g})
            self.assertIsNone(c["class"], g)
            got = S.resume({"content": "FULL_STATE", "fidelity": "LOSSY", "growth": g},
                           {"bound": 1.0, "refresh_tau": 1.0})
            self.assertEqual(got["decision"], "VOID", g)            # never ALLOWED

    def test_bad_snapshots_and_requests_are_void(self):
        for bad in (None, "exact", {"content": "PARTIAL", "fidelity": "EXACT"},
                    {"content": "FULL_STATE", "fidelity": "ROUGH"},
                    dict(EXACT, lossless=True), {}):
            self.assertEqual(S.resume(bad)["decision"], "VOID", bad)
        for request in ({"bound": -1}, {"bound": 0}, {"refresh_tau": "often"},
                        {"bound": True}, {"budget": 3}, "soon"):
            self.assertEqual(S.resume(SINK, request)["decision"], "VOID", request)
        self.assertEqual(S.resume(EXACT, {"bound": -1})["decision"], "VOID")   # also when exact

    def test_growth_is_looked_up_not_typed(self):
        for key, (content, fidelity, path, _) in S.READ.items():
            self.assertEqual(path is not None, fidelity == "LOSSY", key)
        r = ROWS["sink::lossy_snapshot_drift"]
        self.assertEqual((r["growth_from"], r["snapshot"]["growth"]),
                         ("drift_sink/horizon_error_over_delta",
                          RECORD["drift_sink"]["horizon_error_over_delta"]))
        changed = json.loads(json.dumps(RECORD))                   # another record, another class
        changed["drift_sink"]["horizon_error_over_delta"] = 5.0
        rows = {x["scope"].split("snapshot::")[1]: x for x in S.classify_claims(changed)}
        self.assertEqual(rows["sink::lossy_snapshot_drift"]["class"], "CHAOTIC_REFRESH")

    def test_a_claim_with_no_reading_is_unclassified_not_guessed(self):
        extra = json.loads(json.dumps(RECORD))
        extra["claims"].append({"scope": "fab::snapshot::new::thing", "verdict": "pass",
                                "value": 1.0})
        rows = S.classify_claims(extra)
        self.assertEqual((rows[-1]["class"], rows[-1]["resume"]), (None, None))

    def test_cli(self):
        run = [sys.executable, "-m", "experiments.experiment_bridge.snapshot.snapshot_class"]
        r = subprocess.run(run + ["--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        r = subprocess.run(run + ["--output", str(BENCH / "snapshot" / "classes_seed0.json")],
                           cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)                          # refuses to overwrite


if __name__ == "__main__":
    unittest.main()
