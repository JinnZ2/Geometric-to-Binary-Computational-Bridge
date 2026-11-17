"""equation_search round 3: the shuffle guard, the rename, the sweep, the noisy run. Co-authored.

Run from repository root: python tests/test_experiment_bridge_eqsearch_round3.py
"""
from fractions import Fraction
import json
from pathlib import Path
import random
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.eqsearch import exact as X  # noqa: E402
from experiments.experiment_bridge.eqsearch import round2 as R  # noqa: E402
from experiments.experiment_bridge.eqsearch import round3 as T  # noqa: E402

RUNS = ROOT / "experiments" / "experiment_bridge" / "eqsearch" / "runs"
SNAP = json.loads((RUNS / "round3.json").read_text())
ROUND2 = json.loads((RUNS / "round2.json").read_text())


class TestShuffleGuard(unittest.TestCase):
    def test_declared_before_the_run(self):
        d = R.DECLARED["round3"]
        self.assertIn("before any round-3 code was run", d["note"])
        self.assertEqual((T.SHUFFLES, T.SEEDS, T.TRIALS), (19, [0, 1, 2], 40))
        self.assertEqual(SNAP["a_time_shuffle_guard"]["shuffles"], 19)

    def test_the_rule_is_rank_one_of_twenty(self):
        g = random.Random(1)
        items = list(range(30))
        cost = lambda order: float(sum(abs(a - b) for a, b in zip(order, order[1:])))   # noqa: E731
        ordered = T.shuffle_guard(cost(items), cost, items, g)        # time structure
        self.assertEqual((ordered["passes"], ordered["rank"], ordered["of"]), (True, 1, 20))
        g.shuffle(items)
        self.assertFalse(T.shuffle_guard(cost(items) + 1e9, cost, items, g)["passes"])
        self.assertFalse(T.shuffle_guard(None, cost, items, g)["passes"])   # nothing to compare

    def test_planted_data_passes_and_the_guard_does_not_read_r2(self):
        power = SNAP["a_time_shuffle_guard"]["power"]
        self.assertEqual(sorted(power), ["f2_planted_noise_0.01", "f3_planted_stlsq", "f4_planted"])
        for v in power.values():
            self.assertEqual((v["passes_shuffle_guard"], v["rank"], v["of"]), (True, 1, 20))
        row = {"selected": True, "r2": 0.01, "shuffle": {"passes": True}}   # low R^2, passes
        self.assertEqual(T.tally([row])["false_discoveries"],
                         {"r2_only": 0, "shuffle_only": 1, "both": 0})
        row = {"selected": True, "r2": 0.9, "shuffle": {"passes": False}}
        self.assertEqual(T.tally([row])["false_discoveries"],
                         {"r2_only": 1, "shuffle_only": 0, "both": 0})
        row = {"selected": False, "r2": 0.9, "shuffle": {"passes": True}}   # nothing selected
        self.assertEqual(T.tally([row])["false_discoveries"],
                         {"r2_only": 0, "shuffle_only": 0, "both": 0})

    def test_false_discoveries_with_each_guard_alone_and_both(self):
        total = SNAP["a_time_shuffle_guard"]["false_discoveries_total"]
        self.assertEqual({f: (t["r2_only"], t["shuffle_only"], t["both"]) for f, t in total.items()},
                         {"f2": (0, 8, 0), "f3::greedy_bic": (0, 4, 0), "f3::noise_floor": (0, 11, 0),
                          "f3::stlsq": (0, 10, 0), "f4": (0, 5, 0)})
        self.assertTrue(all(t["datasets"] == 120 for t in total.values()))
        # the shuffle guard alone lets noise through, as declared; both together: none
        self.assertGreater(sum(t["shuffle_only"] for t in total.values()), 0)
        self.assertEqual(sum(t["both"] for t in total.values()), 0)
        for seed in ("0", "1", "2"):
            for f, t in SNAP["a_time_shuffle_guard"]["nulls_by_seed"][seed].items():
                self.assertLessEqual(t["false_discoveries"]["both"],
                                     min(t["false_discoveries"]["r2_only"],
                                         t["false_discoveries"]["shuffle_only"]))

    def test_one_null_recomputes(self):
        g = T.rng(0, "null-f4-0")
        got = T.f4_case([g.random() for _ in range(401)], g)
        self.assertLess(got["r2"], R.R2_MIN)
        self.assertEqual(got["shuffle"]["of"], 20)


class TestLinearComparison(unittest.TestCase):
    def test_renamed_and_the_398_of_400_recorded(self):
        b = SNAP["b_linear_comparison"]
        self.assertEqual((b["name"], b["was"], b["quadratic_beats_linear"], b["series"]),
                         ("linear_comparison", "linear_guard", 398, 400))
        # the same number round 2 measured, from round 2's own snapshot
        self.assertEqual(sum(n["f4"]["selected_any_term"]
                             for n in ROUND2["nulls_by_seed"].values()), 398)
        src = (ROOT / "experiments" / "experiment_bridge" / "eqsearch" / "round3.py").read_text()
        self.assertIn("def linear_comparison(", src)
        self.assertNotIn("def linear_guard", src)

    def test_seed_zero_recomputes(self):
        wins = 0
        for i in range(R.NULL_TRIALS):
            g = R.rng(0, f"null-f4-{i}")
            wins += T.linear_comparison([g.random() for _ in range(401)])[1]
        self.assertEqual(wins, ROUND2["nulls_by_seed"]["0"]["f4"]["selected_any_term"])
        self.assertGreater(wins, 35)                              # wins on noise: not a guard


class TestSweep(unittest.TestCase):
    def test_lorenz_recovers_from_001_to_05_and_breaks_at_1(self):
        s = SNAP["c_stlsq_sweep"]["lorenz"]
        self.assertEqual([r["threshold"] for r in s["rows"]], [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0])
        self.assertEqual((s["lowest"], s["highest"]), (0.01, 0.5))
        self.assertEqual(s["breaks_at"], [{"threshold": 1.0, "causes": {
            "y": "UNDER_SELECTION", "z": "UNDER_SELECTION"}}])

    def test_the_planted_005_term_is_lost_at_threshold_005(self):
        s = SNAP["c_stlsq_sweep"]["lorenz_small_term"]
        self.assertEqual(s["planted_small_coefficient"], 0.05)
        self.assertEqual(s["recovers_3_of_3_at"], [0.01, 0.02])
        first = s["breaks_at"][0]
        self.assertEqual((first["threshold"], first["causes"]), (0.05, {"z": "UNDER_SELECTION"}))
        kept = [r for r in s["rows"] if r["threshold"] == 0.02][0]
        self.assertAlmostEqual(kept["smallest_kept_coefficient"], 0.05, places=3)
        self.assertLess(kept["smallest_kept_coefficient"], 0.05)   # the estimate sits just under

    def test_one_sweep_point_recomputes(self):
        small = T.EQ.integrate(T.small_term_rhs, [1.0, 1.0, 1.0], 0.005, 11000)[1000:]
        chosen, _ = T.stlsq(small, 0.005, 0.02)
        self.assertEqual([set(c) for c in chosen], T.TRUTH_SMALL)
        chosen, _ = T.stlsq(small, 0.005, 0.1)
        self.assertEqual(T.cause(chosen[2], T.TRUTH_SMALL[2]), "UNDER_SELECTION")
        self.assertEqual(T.cause(["x", "y", "yz"], {"x", "y"}), "OVER_SELECTION")
        self.assertEqual(T.cause(["x", "z"], {"x", "y"}), "SWAP")


class TestNoisyLorenz(unittest.TestCase):
    def test_stlsq_on_noise_1e3(self):
        n = SNAP["d_noisy_lorenz"]
        self.assertEqual((n["noise"], n["stlsq"]["components_recovered"],
                          n["stlsq"]["failure_causes"]), (0.001, 3, {}))

    def test_exact_tier_never_passes_noisy_data(self):
        ex = SNAP["d_noisy_lorenz"]["exact_tier"]
        self.assertEqual((ex["float_states"]["branch"], ex["float_states"]["verdict"]),
                         ("NOT_ENGAGED", None))
        bent = ex["rationalised_noisy_states"]
        self.assertEqual((bent["verdict"], bent["located_error"]["step"],
                          bent["equals_planted_map"]), ("FAIL", 10, False))
        self.assertEqual((ex["control_no_noise"]["verdict"],
                          ex["control_no_noise"]["equals_planted_map"]), ("PASS", True))
        self.assertTrue(all(SNAP["checks"].values()))

    def test_exact_fit_states_recomputes(self):
        clean = X.exact_states(X.engage(X.LORENZ)[2], 13)[0]
        self.assertEqual(T.exact_fit_states(clean)["verdict"], "PASS")
        bent = [list(s) for s in clean]
        bent[12][1] += Fraction(1, 10 ** 9)                        # one state, one part in 1e9
        got = T.exact_fit_states(bent)
        self.assertEqual((got["verdict"], got["located_error"]["step"]), ("FAIL", 11))
        floats = [[float(v) for v in s] for s in clean]            # even exact values, as floats
        self.assertEqual(T.exact_fit_states(floats)["branch"], "NOT_ENGAGED")
        self.assertEqual((SNAP["human_interest"], SNAP["ai_interest"]), (None, None))


if __name__ == "__main__":
    unittest.main()
