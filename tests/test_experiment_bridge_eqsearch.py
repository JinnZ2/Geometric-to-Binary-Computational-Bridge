"""equation_search round 2 and the exact tier: generated data only. Co-authored.

Run from repository root: python tests/test_experiment_bridge_eqsearch.py
"""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from experiments.experiment_bridge.eqsearch import exact as X  # noqa: E402
from experiments.experiment_bridge.eqsearch import round2 as R  # noqa: E402

BENCH = ROOT / "experiments" / "experiment_bridge"
SPEC_DIR = BENCH / "evidence" / "equation_search_as_received"
RUNS = BENCH / "eqsearch" / "runs"
ROUND2 = json.loads((RUNS / "round2.json").read_text())
EXACT = json.loads((RUNS / "exact.json").read_text())


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


class TestSpecimen(unittest.TestCase):
    def test_kept_as_received_and_declared_first(self):
        m = json.loads((SPEC_DIR / "MANIFEST.json").read_text())
        data = (SPEC_DIR / "equation_search.py").read_bytes()
        self.assertEqual((len(data), hashlib.sha256(data).hexdigest()),
                         (m["files"][0]["bytes"], m["files"][0]["sha256"]))
        self.assertIsNone(m["received_record"])                   # none came with it
        self.assertIn("not retyped", m["provenance_note"])
        d = json.loads((BENCH / "eqsearch" / "DECLARED.json").read_text())
        self.assertIn("BEFORE", d["what"])
        self.assertEqual(d["round2"]["f3_stlsq"]["threshold"], "0.1")
        self.assertTrue(all(a["changes_a_declared_value"] is False for a in d["amendments"]))

    def test_specimen_replays_and_its_greedy_f3_still_fails(self):
        s = ROUND2["specimen_replay"]
        self.assertTrue(s["claims_equal_between_runs"])
        got = {c["scope"].split("::", 2)[2]: c for c in s["claims"]}
        self.assertEqual(got["f3::structure_recovery"]["verdict"], "fail")   # kept, not hidden
        self.assertEqual(got["f2::parameter_recovery"]["verdict_with_source"],
                         "pass (tol unsourced)")
        self.assertEqual(got["f1::exact_recovery"]["verdict_with_source"], "pass")
        self.assertEqual(len(s["f1_constant_hits"]), 8)


class TestRound2(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.traj = R.lorenz_traj()
        cls.f3 = R.f3_branches(cls.traj, 0.005)

    def test_three_branches_and_stlsq_recovers_lorenz(self):
        got = {k: v["components_recovered"] for k, v in self.f3.items()}
        self.assertEqual(got, {"greedy_bic": 1, "noise_floor": 1, "stlsq": 3})
        self.assertEqual([set(c) for c in self.f3["stlsq"]["chosen"]], R.TRUTH)
        # the greedy failure stays logged with its cause
        self.assertEqual(self.f3["greedy_bic"]["failure_causes"],
                         {"x": "OVER_SELECTION", "z": "OTHER"})
        self.assertEqual(self.f3["greedy_bic"]["chosen"], ROUND2["specimen_replay"]["f3_chosen"])
        self.assertEqual({k: v["chosen"] for k, v in self.f3.items()},
                         {k: v["chosen"] for k, v in ROUND2["f3_branches"].items()})

    def test_any_branch_claim_and_per_branch_claims(self):
        claims = {c["scope"].split("r2::")[1]: c for c in R.deterministic_claims(self.f3)}
        top = claims["f3::structure_recovery_any_branch"]
        self.assertEqual((top["verdict"], top["branches_at_3_of_3"]), ("pass", ["stlsq"]))
        self.assertEqual(claims["f3::greedy_bic::structure_recovery"]["verdict"], "fail")
        self.assertEqual(claims["f3::noise_floor::structure_recovery"]["verdict"], "fail")

    def test_any_branch_claim_fails_when_no_branch_recovers(self):
        broken = {k: dict(v, components_recovered=min(v["components_recovered"], 2))
                  for k, v in self.f3.items()}
        top = R.deterministic_claims(broken)[0]
        self.assertEqual((top["verdict"], top["branches_at_3_of_3"]), ("fail", []))

    def test_cause_labels(self):
        self.assertIsNone(R.cause(["y", "x"], {"x", "y"}))
        self.assertEqual(R.cause(["x", "y", "yz"], {"x", "y"}), "OVER_SELECTION")
        self.assertEqual(R.cause(["x", "z"], {"x", "y"}), "SWAP")
        self.assertEqual(R.cause(["y2", "1", "xy"], {"xy", "z"}), "OTHER")

    def test_richardson_error_is_the_noise_floor(self):
        # x(t) = t^3 sampled at dt: the central difference error is dt^2 exactly
        dt = 0.1
        traj = [[(i * dt) ** 3] for i in range(9)]
        _, ders, errs = R.derivatives(traj, dt, 1)
        for i, (d, e) in enumerate(zip(ders[0], errs[0]), 2):
            self.assertAlmostEqual(d - 3 * (i * dt) ** 2, dt ** 2)
            self.assertAlmostEqual(e, dt ** 2)
        self.assertEqual(len(self.f3["noise_floor"]["sigma2_per_component"]), 3)
        self.assertTrue(all(s > 0 for s in self.f3["noise_floor"]["sigma2_per_component"]))

    def test_nulls_abstain_only_through_the_gate(self):
        n = R.run_nulls(0)
        self.assertTrue(same_to_last_digits(json.loads(json.dumps(n)), ROUND2["nulls_by_seed"]["0"]))
        for name, row in n.items():
            self.assertEqual((row["trials"], row["false_discoveries"]), (40, 0), name)
            self.assertLess(row["r2_max"], R.R2_MIN)
        # without the gate most branches select something on pure noise
        self.assertEqual((n["f2"]["selected_any_term"], n["f3::stlsq"]["selected_any_term"],
                          n["f3::noise_floor"]["selected_any_term"]), (40, 40, 40))
        self.assertGreater(n["f4"]["selected_any_term"], 30)
        self.assertGreater(n["f3::greedy_bic"]["selected_any_term"], 0)
        self.assertFalse(R.discovered(True, [0.49]))
        self.assertTrue(R.discovered(True, [0.51]))
        self.assertFalse(R.discovered(False, [0.99]))             # nothing selected

    def test_the_gate_does_not_block_planted_data(self):
        rows = R.f2_rows(0)
        self.assertTrue(all(r["r2"] >= R.R2_MIN for r in rows))
        self.assertTrue(all(r["r2"] >= R.R2_MIN for r in R.f4_rows(0)))
        self.assertTrue(all(r > 0.99 for r in self.f3["stlsq"]["r2_per_component"]))

    def test_f4_sweep_and_solver_check(self):
        rows = R.f4_rows(0)
        self.assertEqual([r["label"] for r in rows], ["SOLVER_CHECK", "RECOVERY", "RECOVERY"])
        self.assertEqual([r["band"] for r in rows], [1e-6, 0.02, 0.02])
        self.assertTrue(all(r["within_band"] for r in rows))
        self.assertLess(rows[0]["rel_err"], 1e-9)
        claims = {c["scope"].split("r2::")[1]: c for c in R.seed_claims(0)[0]}
        self.assertEqual(claims["f4::solver_check_noiseless"]["tol_source"], "DECLARED_PRE_RUN")
        self.assertEqual(claims["f4::map_recovery_noise_0.01"]["verdict_with_source"],
                         "pass (tol unsourced)")

    def test_f1_constant_is_non_unique_and_void_never_pass(self):
        c = next(x for x in R.deterministic_claims(self.f3)
                 if x["scope"].endswith("identifiability_constant"))
        self.assertEqual((c["verdict"], c["state"], c["hit_count"]), ("void", "NON_UNIQUE", 8))
        self.assertTrue(all(a + b == 1 for a, b in c["hits"]))
        self.assertIsNone(c["measured"])

    def test_tol_source_on_every_claim(self):
        every = ROUND2["deterministic_claims"] + ROUND2["claims_by_seed"]["0"]
        self.assertTrue(all(c["tol_source"] in R.TOL_SOURCES for c in every))
        self.assertEqual(ROUND2["tol_source_counts"],
                         {"DEFINITION": 5, "PHYSICS_BOUND": 0, "DECLARED_PRE_RUN": 6,
                          "UNSOURCED": 3})
        f2 = next(c for c in every if c["scope"].endswith("f2::parameter_recovery"))
        self.assertEqual((f2["tol_source"], f2["verdict_with_source"]),
                         ("UNSOURCED", "pass (tol unsourced)"))
        for c in every:                                            # never a plain pass
            if c["tol_source"] == "UNSOURCED" and c["verdict"] == "pass":
                self.assertNotEqual(c["verdict_with_source"], "pass")
        with self.assertRaises(ValueError):
            R.claim("s", 0, 0, "pass", "BECAUSE", "x")

    def test_ten_seeds_and_stability(self):
        self.assertEqual(ROUND2["seeds"], list(range(10)))
        self.assertEqual(sorted(ROUND2["claims_by_seed"]), sorted(str(s) for s in range(10)))
        for s in ROUND2["verdict_stability"]:
            self.assertEqual(len(s["verdicts"]), 10)
            self.assertEqual(s["stable"], len(set(s["verdicts"])) == 1)
        self.assertTrue(all(s["stable"] for s in ROUND2["verdict_stability"]))
        self.assertEqual((ROUND2["human_interest"], ROUND2["ai_interest"]), (None, None))


class TestExactTier(unittest.TestCase):
    def test_trigger(self):
        ok, log, parsed = X.engage(X.LORENZ)
        self.assertTrue(ok)
        self.assertEqual(parsed["coefficients"]["beta"], Fraction(8, 3))
        self.assertIn("auto", log["reason"])
        for bad in (dict(X.LORENZ, dt=0.005),
                    dict(X.LORENZ, coefficients=dict(X.LORENZ["coefficients"], beta=8 / 3)),
                    dict(X.LORENZ, start=["1", 1.0, "1"]), dict(X.LORENZ, dt="fast")):
            ok, log, parsed = X.engage(bad, forced=True)           # --exact does not convert
            self.assertEqual((ok, log["state"], parsed), (False, "NOT_ENGAGED", None))
        self.assertIn("float", X.run(system=dict(X.LORENZ, dt=0.005))["trigger"]["reason"])

    def test_planted_map_recovered_exactly_three_of_three_unique(self):
        r = X.run()
        self.assertEqual((r["branch"], r["verdict"], r["components_equal_to_planted"],
                          r["unique"]), ("EXACT", "PASS", 3, True))
        self.assertEqual(r["recovered_step_map"],
                         [{"x": "19/20", "y": "1/20"},
                          {"x": "7/50", "y": "199/200", "xz": "-1/200"},
                          {"z": "74/75", "xy": "1/200"}])
        self.assertEqual(r["ode_coefficients_read_back"],
                         [{"x": "-10", "y": "10"}, {"x": "28", "y": "-1", "xz": "-1"},
                          {"z": "-8/3", "xy": "1"}])
        self.assertEqual(r["verification"], {"steps_checked_exactly": 12, "mismatch": None,
                                             "rule": "exact equality at every step; "
                                                     "no tolerance, no BIC"})
        self.assertEqual(r, EXACT["runs"]["exact_12_steps"])
        self.assertNotIn("bic", json.dumps(r["verification"]).lower().replace("no bic", ""))

    def test_null_one_perturbed_coefficient_fails_located(self):
        r = X.run()
        n = r["null_perturbation"]
        self.assertEqual((n["trials"], n["check_failed"], n["not_caught"]), (30, 30, []))
        parsed = X.engage(X.LORENZ)[2]
        states = X.exact_states(parsed, 12)[0]
        good = X.planted_map(parsed["coefficients"], parsed["dt"])
        self.assertEqual(X.verify_exact(states, good), (12, None))
        bent = [list(row) for row in good]
        bent[1][X.TERMS.index("xz")] += Fraction(1, 10 ** 12)       # far below any float band
        steps, miss = X.verify_exact(states, bent)
        self.assertEqual((miss["step"], miss["component"]), (0, "y"))

    def test_a_different_system_fails_the_planted_check(self):
        other = X.engage(dict(X.LORENZ, coefficients=dict(X.LORENZ["coefficients"],
                                                          rho="28001/1000")))[2]
        ref = X.engage(X.LORENZ)[2]
        miss = X.verify_exact(X.exact_states(other, 6)[0],
                              X.planted_map(ref["coefficients"], ref["dt"]))[1]
        self.assertEqual(miss["component"], "y")

    def test_growth_is_logged_and_the_cap_stops_generation(self):
        r = X.run(steps=40)
        g = r["growth"]
        self.assertEqual(g["denominator_bits_per_step"][:7], [1, 7, 18, 39, 68, 114, 194])
        self.assertTrue(all(b <= X.DENOM_CAP_BITS for b in g["denominator_bits_per_step"]))
        self.assertEqual((g["cap_hit_at_step"], g["exact_transitions"], r["branch"]),
                         (19, 18, "EXACT"))

    def test_cap_then_modular_branch_agrees_with_the_exact_map(self):
        r = X.run(steps=40, cap=256)
        self.assertEqual((r["branch"], r["verdict"], r["unique"]), ("MODULAR", "PASS", True))
        self.assertEqual(r["exact_solve"]["rank"], 6)               # not enough exact steps
        self.assertEqual(len(r["modular"]["primes"]), 4)
        for p in r["modular"]["primes"]:
            self.assertTrue(X.is_prime(p["prime"]) and p["prime"] < 2 ** 61)
            self.assertEqual((p["rank"], p["all_transitions_consistent"]), (10, True))
        self.assertEqual(r["recovered_step_map"], X.run()["recovered_step_map"])
        self.assertEqual(r["modular"]["checked_exactly"]["steps"], 6)
        self.assertEqual(r["modular"]["checked_modulo_each_prime"]["steps"], 40)

    def test_cap_with_no_branch_is_void_not_a_float_fallback(self):
        r = X.run(steps=40, cap=256, modular=False)
        self.assertEqual((r["branch"], r["verdict"]), ("VOID", "VOID"))
        self.assertIn("no float fallback", r["void_reason"])
        self.assertNotIn("recovered_step_map", r)

    def test_rational_reconstruction(self):
        m = 2305843009213693951 * 2305843009213693921
        for q in (Fraction(-8, 3), Fraction(199, 200), Fraction(0), Fraction(74, 75)):
            residue = q.numerator * pow(q.denominator, -1, m) % m
            self.assertEqual(X.reconstruct(residue, m), q)
        self.assertEqual(X.crt([2, 3], [5, 7])[0] % 5, 2)
        self.assertEqual([X.is_prime(n) for n in (1, 2, 91, 97, 2 ** 61 - 1)],
                         [False, True, False, True, True])

    def test_snapshot_claims_and_cli(self):
        self.assertEqual({c["scope"].split("::")[-1]: c["verdict"] for c in EXACT["claims"]},
                         {"step_map_recovery": "pass", "null_perturbed_coefficient": "pass",
                          "modular_branch_agrees": "pass", "cap_without_branch_is_void": "pass",
                          "float_system_not_engaged": "pass"})
        r = subprocess.run([sys.executable, "-m", "experiments.experiment_bridge.eqsearch.exact",
                            "--selftest"], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout)
        r = subprocess.run([sys.executable, "-m", "experiments.experiment_bridge.eqsearch.exact",
                            "--output", str(RUNS / "exact.json")], cwd=ROOT,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)                          # refuses to overwrite


if __name__ == "__main__":
    unittest.main()
