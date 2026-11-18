"""Planted-semantics sim: SYNTHETIC ONLY, no neural model. Co-authored.

Run from repository root: python tests/test_experiment_bridge_sim.py
"""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.sim import planted as P  # noqa: E402

BENCH = ROOT / "experiments" / "experiment_bridge"
RUN = BENCH / "sim" / "runs" / "seed0"
N_TRAIN, N_HELD = P.SMALL["n_train"], P.SMALL["n_held"]
ROWS = P.truth_table(0, N_TRAIN, N_HELD)
_CACHE = {}


def cell(sigma=0.1, fault=True, label_source=None):
    key = (sigma, fault, label_source)
    if key not in _CACHE:
        _CACHE[key] = P.run_sigma(0, sigma, ROWS, N_TRAIN, fault, label_source)
    return _CACHE[key]


def same_to_last_digits(a, b, rel=1e-9):
    """Equal, with floats compared to a relative 1e-9.

    The committed runs were written under Python 3.13. Python 3.12 changed
    sum() of floats to compensated summation, so 3.11 (the CI interpreter)
    differs from the committed numbers in the last digits. Everything that is
    not a float (keys, counts, strings, list lengths) must match exactly.
    """
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, float) or isinstance(b, float):
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            return False
        return abs(a - b) <= rel * max(abs(a), abs(b), 1e-300)
    if isinstance(a, dict):
        return isinstance(b, dict) and a.keys() == b.keys() and all(
            same_to_last_digits(a[k], b[k], rel) for k in a)
    if isinstance(a, list):
        return isinstance(b, list) and len(a) == len(b) and all(
            same_to_last_digits(x, y, rel) for x, y in zip(a, b))
    return a == b


class TestGroundTruth(unittest.TestCase):
    def test_predicates_come_from_the_received_reference(self):
        ref = P.read_reference()
        raw = (BENCH / "raw" / "lojban_wordslot_reference.json").read_bytes()
        self.assertEqual(ref["sha256"], hashlib.sha256(raw).hexdigest())
        rows = json.loads(raw)["place_structures"]
        observed = {r["gismu"] for r in rows if r["structure_status"] == "OBSERVED"}
        self.assertTrue(set(P.PREDICATES) <= observed)
        void = next(r for r in rows if r["english"] == P.VOID_WORD)
        self.assertEqual((void["gismu"], void["structure_status"]), (None, "VOID"))

    def test_truth_table_is_reproducible_from_its_seed(self):
        self.assertEqual(P.truth_table(0, 50, 20), P.truth_table(0, 50, 20))
        self.assertNotEqual(P.truth_table(0, 50, 20), P.truth_table(1, 50, 20))
        self.assertEqual([r["split"] for r in ROWS].count("train"), N_TRAIN)
        self.assertEqual({r["label"] for r in ROWS}, set(P.PREDICATES) | {P.VOID_LABEL})

    def test_embedding_is_signature_plus_slots_plus_noise(self):
        sigs = P.signatures(0, fault=False)
        for v in sigs.values():
            self.assertAlmostEqual(sum(x * x for x in v), P.PRED_AMP ** 2)
        row = {"label": "snura", "x1": 2, "x2": 0}
        v = P.embed([row], sigs, 0.0, 0)[0]
        self.assertEqual(v[:P.PRED_DIMS], sigs["snura"])
        self.assertEqual(v[P.PRED_DIMS:], [0, 0, P.SLOT1_AMP, P.SLOT2_AMP, 0, 0])
        self.assertEqual(P.embed([row], sigs, 1.0, 0), P.embed([row], sigs, 1.0, 0))
        self.assertNotEqual(P.embed([row], sigs, 1.0, 0), P.embed([row], sigs, 1.0, 1))

    def test_the_fault_makes_the_twin_identical_and_only_the_twin(self):
        a, b = P.FAULT_TWIN
        clean, faulted = P.signatures(0, False), P.signatures(0, True)
        self.assertNotEqual(clean[a], clean[b])
        self.assertEqual(faulted[a], faulted[b])
        for label in clean:
            if label != b:
                self.assertEqual(clean[label], faulted[label])


class TestAssignment(unittest.TestCase):
    def test_majority_rule_and_confused_keys(self):
        paths = [(0, 1)] * 6 + [(1, 1)] * 4 + [(None, 2)]
        labels = ["a"] * 5 + ["b"] + ["b", "b", "a", "a"] + ["a"]
        m = P.assign(paths, labels, 1)
        self.assertEqual(sorted(m), [(0,), (1,)])                 # the rejected key: none
        self.assertEqual((m[(0,)]["label"], m[(0,)]["quality"]), ("a", "CLEAN"))
        self.assertEqual((m[(1,)]["label"], m[(1,)]["quality"]), ("a", "CONFUSED"))  # tie: first
        self.assertEqual(m[(1,)]["runner_up"], "b")

    def test_four_states_per_sample(self):
        mapping = {(0,): {"label": "snura", "quality": "CLEAN"},
                   (1,): {"label": P.VOID_LABEL, "quality": "CLEAN"}}
        reads = P.read_out([(0, 3), (1, 3), (2, 3), (None, 3)], mapping, 1)
        self.assertEqual([r[0] for r in reads],
                         ["ACCEPTED", "LEXICAL_VOID", "UNMAPPED", "REJECTED"])
        s = P.score(reads, ["snura", P.VOID_LABEL, "snura", "snura"])
        self.assertEqual((s["strict_accuracy"], s["covered_accuracy"], s["coverage"]),
                         (0.5, 1.0, 0.5))                          # abstentions count wrong
        self.assertEqual(s["states"], {"ACCEPTED": 1, "REJECTED": 1, "UNMAPPED": 1,
                                       "LEXICAL_VOID": 1})

    def test_every_held_out_sample_gets_one_state(self):
        c, samples = cell()
        self.assertEqual(len(samples), N_HELD)
        self.assertTrue(all(s["state"] in P.STATES for s in samples))
        self.assertEqual(sum(c["primary"]["states"].values()), N_HELD)
        for s in samples:
            self.assertEqual(s["assigned"] is None, s["state"] in ("REJECTED", "UNMAPPED"))
            if s["state"] == "LEXICAL_VOID":
                self.assertEqual(s["assigned"], P.VOID_LABEL)
        deep = c["by_depth"]["4"]                                  # deeper keys: more unmapped
        self.assertGreater(deep["states"]["UNMAPPED"], c["primary"]["states"]["UNMAPPED"])


class TestAgainstNulls(unittest.TestCase):
    def test_low_noise_beats_every_permuted_label_run(self):
        c, _ = cell()
        self.assertEqual(c["permuted_null"]["n"], P.N_PERMUTATIONS)
        self.assertGreaterEqual(P.N_PERMUTATIONS, 100)
        self.assertGreater(c["primary"]["strict_accuracy"], c["permuted_null"]["max"])
        self.assertTrue(c["beats_permuted_null"])
        self.assertGreater(c["primary"]["strict_accuracy"],
                           c["majority_label_baseline"]["strict_accuracy"])
        self.assertGreater(c["primary"]["strict_accuracy"],
                           c["random_codebook_baseline"]["strict_accuracy"])
        self.assertEqual(P.verdict([c])["verdict"], "NOT_FALSIFIED_ON_THIS_GENERATOR")

    def test_the_falsifier_can_fire(self):
        broken, _ = cell(label_source="shuffled")                  # a broken assigner
        v = P.verdict([broken])
        self.assertEqual(v["verdict"], "METHOD_FAILS")
        self.assertFalse(broken["beats_permuted_null"])
        self.assertEqual(v["first_sigma_not_beating_null"], 0.1)

    def test_high_noise_does_not_beat_the_null_and_is_reported(self):
        low, high = cell(0.1)[0], cell(8.0)[0]
        self.assertFalse(high["beats_permuted_null"])
        v = P.verdict([low, high])
        self.assertEqual((v["verdict"], v["first_sigma_not_beating_null"]),
                         ("NOT_FALSIFIED_ON_THIS_GENERATOR", 8.0))  # read at the lowest sigma


class TestPlantedFault(unittest.TestCase):
    def test_the_twin_reads_as_confused_not_as_two_clean_mappings(self):
        twin = sorted(P.FAULT_TWIN)
        faulted, control = cell(fault=True)[0], cell(fault=False)[0]
        self.assertIn(twin, [p["pair"] for p in faulted["confused_pairs"]])
        self.assertGreater(faulted["keys"]["CONFUSED"], 0)
        recalls = [faulted["per_label"][t]["recall_strict"] for t in twin]
        self.assertLess(min(recalls), 0.75)                        # not two clean mappings
        self.assertEqual(control["confused_pairs"], [])            # and clean without it
        for t in twin:
            self.assertGreater(control["per_label"][t]["recall_strict"], 0.9)
        r = P.fault_reading([faulted], [control])
        self.assertTrue(r["reads_as_confused"])

    def test_the_other_labels_are_not_called_confused(self):
        faulted = cell(fault=True)[0]
        self.assertEqual([p["pair"] for p in faulted["confused_pairs"]],
                         [sorted(P.FAULT_TWIN)])


class TestSlots(unittest.TestCase):
    def test_mutual_information(self):
        self.assertAlmostEqual(P.mutual_information([0, 0, 1, 1], ["a", "a", "b", "b"]), 1.0)
        self.assertAlmostEqual(P.mutual_information([0, 1, 0, 1], ["a", "a", "b", "b"]), 0.0)

    def test_level_one_holds_the_predicate_at_low_noise(self):
        info = cell()[0]["level_information"]
        self.assertEqual([r["level"] for r in info], [1, 2, 3, 4])
        first = info[0]
        self.assertEqual(first["holds_most"], "predicate")
        self.assertGreater(first["predicate"]["mi_bits"], 2.0)
        self.assertGreater(first["predicate"]["mi_bits"], first["slot_x1"]["mi_bits"])
        later = max(r["slot_x1"]["mi_bits"] + r["slot_x2"]["mi_bits"] for r in info[1:])
        self.assertGreater(later, first["slot_x2"]["mi_bits"])     # slots show up after level 1
        for r in info:                                             # the bias is reported beside it
            for t in ("predicate", "slot_x1", "slot_x2"):
                self.assertGreaterEqual(r[t]["shuffled_max_bits"], r[t]["shuffled_mean_bits"])
            self.assertEqual(r["holds_most"] is None, not r["above_shuffle"])


class TestCommittedRun(unittest.TestCase):
    def test_truth_table_hash_and_scope(self):
        truth = json.loads((RUN / "truth_table.json").read_text())
        res = json.loads((RUN / "results.json").read_text())
        self.assertEqual(res["truth_table_sha256"], P.sha(truth))
        self.assertEqual(truth["rows"], P.truth_table(res["seed"], P.N_TRAIN, P.N_HELD))
        self.assertIn("SYNTHETIC ONLY", res["scope"])
        self.assertEqual((res["status"], res["human_interest"], res["ai_interest"]),
                         ("PROPOSED", None, None))
        self.assertEqual(res["reference"]["sha256"], P.read_reference()["sha256"])
        self.assertEqual(res["parameters"]["sigmas"], list(P.SIGMAS))

    def test_states_file_matches_the_counts(self):
        res = json.loads((RUN / "results.json").read_text())
        states = json.loads((RUN / "states.json").read_text())
        for c in res["with_fault"]["cells"]:
            rows = states[str(c["sigma"])]
            self.assertEqual(len(rows), P.N_HELD)
            for name in P.STATES:
                self.assertEqual(sum(1 for r in rows if r["state"] == name),
                                 c["primary"]["states"][name], (c["sigma"], name))

    def test_one_committed_cell_recomputes(self):
        res = json.loads((RUN / "results.json").read_text())
        truth = json.loads((RUN / "truth_table.json").read_text())
        want = res["with_fault"]["cells"][0]
        got, _ = P.run_sigma(res["seed"], want["sigma"], truth["rows"], P.N_TRAIN, True)
        self.assertTrue(same_to_last_digits(json.loads(json.dumps(got)), want))



def specimen_hashes():
    """sha256 of every received or earlier-version file the sim must leave alone."""
    out = {}
    for folder in ("raw", "evidence", "v1", "v1_1", "audit", "adversarial"):
        for path in sorted((BENCH / folder).rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                out[str(path.relative_to(BENCH))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return out


class TestCli(unittest.TestCase):
    def test_selftest_and_output_dir(self):
        run = [sys.executable, "-m", "experiments.experiment_bridge.sim.planted"]
        r = subprocess.run(run + ["--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("failed: 0", r.stdout)
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "occupied").write_text("x")
            r = subprocess.run(run + ["--small", "--output-dir", d], cwd=ROOT,
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)                   # refuses a used directory
            self.assertEqual(sorted(p.name for p in Path(d).iterdir()), ["occupied"])

    def test_a_run_leaves_the_specimens_untouched(self):
        before = specimen_hashes()
        self.assertGreater(len(before), 40)
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "run"
            truth, results, states = P.run(0, small=True)
            P.write_run(out, truth, results, states)
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ["results.json", "states.json", "truth_table.json"])
            self.assertEqual(results["truth_table_sha256"],
                             P.sha(json.loads((out / "truth_table.json").read_text())))
        self.assertEqual(specimen_hashes(), before)


if __name__ == "__main__":
    unittest.main()
