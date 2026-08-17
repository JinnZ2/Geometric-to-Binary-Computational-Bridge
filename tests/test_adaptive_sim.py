"""ASF-1..16: the adaptive simulation framework.

Needs numpy. Two things this file guards against, neither of which is a
wrong number:

  * A finding that quietly stops being true. Most of these assert a DEFECT --
    the R2 gate passing a rising distribution, the fixation claim measuring
    the step budget, switching_rate saturating. If someone fixes one, the
    assertion fails, and the fix is to amend the AUDIT header in
    `adaptive_sim/adaptive_sim_framework.py` so it stops describing code that
    no longer exists.

  * The framework's own thesis going unchecked. ASF-1 is the finding that the
    shipped provenance log does not reproduce under the code shipped beside
    it, so the replay path that found it is itself tested here -- including
    that `verify_log` reports a mismatch when there IS one, which is the
    direction a verifier fails silently in.

The forest model is a double Python loop over the grid, so every forest test
here runs on a small grid for a few steps. The measured sweeps quoted in
`adaptive_sim/AUDIT.md` used the shipped parameters and are not re-run here.
"""

import copy
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np  # noqa: E402

from adaptive_sim import adaptive_sim_framework as A  # noqa: E402

EVIDENCE = os.path.join(os.path.dirname(__file__), "..", "adaptive_sim",
                        "evidence")

FOREST = {"grid_size": 16, "metabolic_exponent": 0.75,
          "competition_strength": 0.8, "dispersal_range": 4,
          "seed_rate": 0.15, "mortality_base": 0.01, "num_steps": 20,
          "initial_density": 0.3, "num_species": 3, "min_size": 1.0}

FLUCT = {"num_states": 5, "carrying_capacities": [50, 100, 200, 300, 400],
         "switching_rate": 0.3, "growth_rate_fast": 1.0,
         "growth_rate_ratio": 0.95, "num_steps": 400, "num_replicates": 20,
         "base_seed": 123}


def as_received():
    path = os.path.join(EVIDENCE, "adaptive_sim_framework_asreceived.py")
    spec = importlib.util.spec_from_file_location("asf_as_received", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


class TestASF_1_ProvenanceReplay(unittest.TestCase):
    """The record does not reproduce, and the replay path that says so."""

    def test_shipped_log_does_not_reproduce_under_shipped_code(self):
        log = os.path.join(EVIDENCE, "provenance_fluctuating.jsonl")
        rows = A.verify_log(log, module=as_received())
        replayable = [r for r in rows if r["replayable"]]
        self.assertEqual(len(replayable), 5)
        self.assertTrue(all(r["diffs"] and not r["error"] for r in replayable))
        self.assertTrue(all(r["reproduces"] is False for r in replayable))

    def test_the_decisive_record_differs_only_in_timing(self):
        """Identical dynamics, one field wrong -- so it is not simply a log
        of different parameters."""
        log = os.path.join(EVIDENCE, "provenance_fluctuating.jsonl")
        rows = A.verify_log(log, module=as_received())
        rec = [r for r in rows if r["run_id"] == "db001b18502f"][0]
        self.assertEqual(sorted(p for p, _, _ in rec["diffs"]),
                         ["mean_fixation_time", "std_fixation_time"])
        logged, got = rec["diffs"][0][1], rec["diffs"][0][2]
        self.assertEqual(logged, 0.0)
        self.assertGreater(got, 1000.0)

    def test_verify_log_reports_a_mismatch_when_there_is_one(self):
        """The direction a verifier fails silently in: writing a record, then
        perturbing the model, must produce diffs."""
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "log.jsonl")
            lg = A.ProvenanceLogger(log_file=path)
            out = A.FluctuatingPopSim(copy.deepcopy(FLUCT)).run()
            lg.log_run(A.SimulationRecord(
                run_id="r0", model_name="fluctuating",
                parameters=copy.deepcopy(FLUCT), random_seed=123,
                timestamp=0.0, duration_seconds=0.0, outcomes=out,
                claim_results={}, reasoning_chain=[]))
            clean = A.verify_log(path)[0]
            self.assertIsNone(clean["error"])
            self.assertTrue(clean["reproduces"])

            tampered = json.loads(open(path).read())
            tampered["outcomes"]["fixation_probability"]["slow_strain"] = 0.999
            with open(path, "w") as fh:
                fh.write(json.dumps(tampered) + "\n")
            got = A.verify_log(path)[0]
            self.assertFalse(got["reproduces"])
            self.assertEqual([p for p, _, _ in got["diffs"]],
                             ["fixation_probability.slow_strain"])

    def test_forest_records_are_reported_unreplayable_not_scored(self):
        log = os.path.join(EVIDENCE, "provenance_forest.jsonl")
        rows = A.verify_log(log, module=as_received())
        self.assertTrue(rows and not any(r["replayable"] for r in rows))

    def test_a_raising_replay_is_not_a_reproduction(self):
        """The verifier's own ASF-5: a measurement that did not happen must
        not be reported as one that agreed. An earlier version defaulted
        `module` to `__import__(__name__)`, which returns the top-level
        package, so every default replay raised and left `diffs` empty."""
        import types
        empty = types.ModuleType("empty")
        log = os.path.join(EVIDENCE, "provenance_fluctuating.jsonl")
        rows = A.verify_log(log, module=empty)
        replayable = [r for r in rows if r["replayable"]]
        self.assertTrue(replayable)
        for r in replayable:
            self.assertIsNotNone(r["error"])
            self.assertFalse(r["reproduces"])

    def test_default_module_resolves_to_this_module(self):
        log = os.path.join(EVIDENCE, "provenance_fluctuating.jsonl")
        row = [r for r in A.verify_log(log, limit=1) if r["replayable"]][0]
        self.assertIsNone(row["error"])

    def test_run_id_is_content_addressed(self):
        a = A.content_run_id("sha", "forest", {"x": 1}, 42)
        self.assertEqual(a, A.content_run_id("sha", "forest", {"x": 1}, 42))
        self.assertNotEqual(a, A.content_run_id("sha", "forest", {"x": 2}, 42))
        self.assertNotEqual(a, A.content_run_id("sha", "forest", {"x": 1}, 43))
        self.assertNotEqual(a, A.content_run_id("other", "forest", {"x": 1}, 42))

    def test_code_fingerprint_changes_with_the_code(self):
        def f():
            return 1

        def g():
            return 2

        self.assertNotEqual(A.code_fingerprint(f), A.code_fingerprint(g))
        self.assertEqual(A.code_fingerprint(f), A.code_fingerprint(f))


class TestASF_2_Seeding(unittest.TestCase):
    def test_run_is_a_pure_function_of_params_and_seed(self):
        self.assertEqual(A.run_model("forest", FOREST, 7),
                         A.run_model("forest", FOREST, 7))
        self.assertNotEqual(A.run_model("forest", FOREST, 7),
                            A.run_model("forest", FOREST, 8))

    def test_as_received_seeds_once_for_the_whole_loop(self):
        src = open(os.path.join(
            EVIDENCE, "adaptive_sim_framework_asreceived.py")).read()
        self.assertEqual(src.count("np.random.seed(random_seed)"), 1)

    def test_record_names_the_seed_its_run_used(self):
        res, lg = _run_loop(A, iterations=3)
        for i, rec in enumerate(lg.records):
            self.assertEqual(rec.random_seed, 123 + i)
            self.assertEqual(rec.seeds["iteration_seed"], 123 + i)
            self.assertEqual(rec.seeds["loop_seed"], 123)

    def test_base_seed_is_held_fixed_across_iterations(self):
        """Deliberate: it makes successive iterations a paired comparison."""
        _, lg = _run_loop(A, iterations=3)
        self.assertEqual({r.parameters["base_seed"] for r in lg.records},
                         {123})


def _run_loop(mod, iterations=4, seed=123, exploration_rate=0.0,
              params=None, model="fluctuating"):
    lg = mod.ProvenanceLogger(log_file=None if mod is A else os.devnull)
    ag = mod.AdaptiveAgent("T", exploration_rate=exploration_rate)
    rn = mod.SimulationRunner(model, lg, ag)
    for c in (mod.get_fluctuating_claims() if model == "fluctuating"
              else mod.get_forest_claims()):
        rn.register_claim(c)
    p = copy.deepcopy(params if params is not None
                      else dict(FLUCT, num_steps=150))
    res = quiet(rn.run_adaptive_loop, p, max_iterations=iterations,
                random_seed=seed)
    return res, lg


class TestASF_3_ParameterPairing(unittest.TestCase):
    def test_as_received_pairs_outcomes_with_the_next_iterations_params(self):
        R = as_received()
        res, lg = _run_loop(R)
        in_mem = [round(it["params"]["switching_rate"], 4)
                  for it in res["iteration_results"]]
        logged = [round(r.parameters["switching_rate"], 4) for r in lg.records]
        self.assertNotEqual(in_mem, logged)
        self.assertEqual(in_mem[:-1], logged[1:])

    def test_landed_pairs_outcomes_with_the_params_that_produced_them(self):
        res, lg = _run_loop(A)
        ran = [it["params"]["num_steps"] for it in res["iteration_results"]]
        logged = [r.parameters["num_steps"] for r in lg.records]
        self.assertEqual(ran, logged)
        # non-trivially: the parameter has to actually move, or this
        # assertion would hold without testing the pairing
        self.assertGreater(len(set(ran)), 1)

    def test_next_params_is_kept_separately(self):
        res, _ = _run_loop(A)
        its = res["iteration_results"]
        self.assertEqual([i["next_params"]["num_steps"] for i in its][:-1],
                         [i["params"]["num_steps"] for i in its][1:])


class TestASF_4_ClaimHistory(unittest.TestCase):
    def test_as_received_never_records_a_claim_result(self):
        res, _ = _run_loop(as_received())
        self.assertEqual(res["logger_summary"]["claims_tested"], [])

    def test_landed_records_every_claim_tested(self):
        res, lg = _run_loop(A)
        self.assertEqual(res["logger_summary"]["claims_tested"],
                         ["fluctuating_fixation",
                          "fluctuating_slow_persistence"])
        self.assertTrue(all(lg.claim_history[c] for c in
                            res["logger_summary"]["claims_tested"]))


class TestASF_5_Inconclusive(unittest.TestCase):
    def test_raising_test_is_inconclusive(self):
        def boom(_):
            raise ValueError("instrument fault")

        status, msg, _ = A.Claim("x", "", "forest", boom).test({})
        self.assertEqual(status, A.INCONCLUSIVE)
        self.assertIn("instrument fault", msg)

    def test_as_received_collapses_inconclusive_into_failed(self):
        R = as_received()
        src = open(os.path.join(
            EVIDENCE, "adaptive_sim_framework_asreceived.py")).read()
        self.assertIn("'status': 'passed' if passed else 'failed'", src)
        c = R.Claim("x", "", "forest", lambda o: (_ for _ in ()).throw(
            ValueError("x")))
        passed, _, _ = c.test({})
        self.assertFalse(passed)
        self.assertEqual(c.status, "inconclusive")

    def test_as_received_forest_claim_raises_on_a_collapsed_forest(self):
        _, msg, _ = as_received().get_forest_claims()[0].test(
            {"num_trees": 12, "species_richness": 1})
        self.assertIn("Test error", msg)

    def test_landed_forest_claims_handle_a_collapsed_forest(self):
        dead = {"num_trees": 0, "species_richness": 0, "extinct": True}
        for claim in A.get_forest_claims():
            self.assertEqual(claim.test(dead)[0], A.INCONCLUSIVE)

    def test_inconclusive_does_not_drive_the_agent(self):
        """A broken thermometer is not evidence about the weather."""
        lg = A.ProvenanceLogger(log_file=None)
        ag = A.AdaptiveAgent("T", exploration_rate=0.0)
        rn = A.SimulationRunner("forest", lg, ag)
        rn.register_claim(A.Claim(
            "always_inconclusive", "", "forest",
            lambda o: (_ for _ in ()).throw(ValueError("fault"))))
        res = quiet(rn.run_adaptive_loop, copy.deepcopy(FOREST),
                    max_iterations=3, random_seed=1)
        self.assertEqual(res["total_iterations"], 1)
        self.assertEqual(lg.records[0].claim_results["always_inconclusive"],
                         A.INCONCLUSIVE)
        self.assertEqual(ag.reasoning_chain, [])

    def test_inconclusive_reaches_the_record(self):
        lg = A.ProvenanceLogger(log_file=None)
        rn = A.SimulationRunner("forest", lg, A.AdaptiveAgent("T"))
        rn.register_claim(A.Claim("boom", "", "forest",
                                  lambda o: (_ for _ in ()).throw(TypeError)))
        quiet(rn.run_adaptive_loop, copy.deepcopy(FOREST), max_iterations=1,
              random_seed=1)
        self.assertIn(A.INCONCLUSIVE, lg.records[0].claim_results.values())


class TestASF_6_DiagnosisReachability(unittest.TestCase):
    def test_as_received_num_steps_branch_is_unreachable(self):
        R = as_received()
        ag = R.AdaptiveAgent()
        h = ag._generate_hypothesis(
            {"size_distribution": {"r_squared": 0.5}},
            [R.Claim("forest_power_law", "", "forest", None)], "forest")
        self.assertIn("competition too weak", h)
        self.assertIn("not at steady state", h)
        base = {"competition_strength": 0.8, "num_steps": 500}
        np.random.seed(0)
        new, act = ag._propose_action(base, h, "forest", {})
        self.assertEqual(new["num_steps"], base["num_steps"])
        self.assertIn("competition_strength", act)

    def test_landed_num_steps_branch_is_reachable(self):
        ag = A.AdaptiveAgent("T", exploration_rate=0.0)
        tags = ag._diagnose({"size_distribution": {"r_squared": 0.5}},
                            [A.Claim("forest_power_law", "", "forest", None)],
                            "forest")
        self.assertEqual(tags[0], "not_at_steady_state")
        new, _ = ag._propose_action({"competition_strength": 0.8,
                                     "num_steps": 500},
                                    ag._choose_diagnosis(tags), "forest")
        self.assertGreater(new["num_steps"], 500)

    def test_every_diagnosis_tag_reaches_an_action(self):
        """The enumerate-reachable-outputs screen, applied to the tag set."""
        params = {"forest": {"competition_strength": 1.0, "num_steps": 500,
                             "seed_rate": 0.1, "metabolic_exponent": 0.75,
                             "dispersal_range": 4},
                  "fluctuating": {"switching_rate": 0.1,
                                  "growth_rate_ratio": 0.95, "num_steps": 500,
                                  "carrying_capacities": [50, 100]}}
        ag = A.AdaptiveAgent("T")
        seen = set()
        for (model, _claim, _variant), tags in A.AdaptiveAgent.DIAGNOSES.items():
            for tag in tags:
                np.random.seed(0)
                new, act = ag._propose_action(params[model], tag, model)
                self.assertNotEqual(new, params[model],
                                    "tag %r changes nothing" % tag)
                self.assertNotEqual(act, "No parameter changes.")
                seen.add(tag)
        self.assertTrue(seen)

    def test_an_untried_diagnosis_is_preferred_to_a_repeat(self):
        ag = A.AdaptiveAgent("T", exploration_rate=0.0)
        tags = ["not_at_steady_state", "competition_too_weak"]
        self.assertEqual(ag._choose_diagnosis(tags), "not_at_steady_state")
        ag.tried.append("not_at_steady_state")
        self.assertEqual(ag._choose_diagnosis(tags), "competition_too_weak")
        ag.tried.append("competition_too_weak")
        self.assertEqual(ag._choose_diagnosis(tags), "not_at_steady_state")

    def test_the_loop_turns_the_knob_the_as_received_one_could_not(self):
        res, lg = _run_loop(A, iterations=4)
        applied = [r.reasoning_chain[0].diagnosis_applied for r in lg.records]
        self.assertIn("not_at_steady_state", applied)
        steps = [r.parameters["num_steps"] for r in lg.records]
        self.assertGreater(steps[-1], steps[0])
        first = lg.records[0].outcomes["fixation_probability"]["coexistence"]
        last = lg.records[-1].outcomes["fixation_probability"]["coexistence"]
        self.assertGreater(first, last)

    def test_reasoning_chain_carries_tags_not_only_prose(self):
        _, lg = _run_loop(A, iterations=2)
        step = lg.records[0].reasoning_chain[0]
        self.assertTrue(step.diagnoses)
        self.assertIn(step.diagnosis_applied, step.diagnoses)


class TestASF_7_DyingForest(unittest.TestCase):
    def test_as_received_answers_a_dying_forest_with_more_competition(self):
        R = as_received()
        ag = R.AdaptiveAgent()
        h = ag._generate_hypothesis({"num_trees": 12},
                                    [R.get_forest_claims()[0]], "forest")
        np.random.seed(1)
        _, act = ag._propose_action({"competition_strength": 0.8,
                                     "num_steps": 500}, h, "forest", {})
        self.assertIn("Increased competition_strength", act)


class TestASF_8_PowerLawGate(unittest.TestCase):
    """Left in place: choosing a slope constraint is a claim about forests."""

    def setUp(self):
        self.rng = np.random.default_rng(0)

    def _rate(self, gen, trials=40, n=1000):
        hits, slopes = 0, []
        for _ in range(trials):
            fit = A.fit_log_binned_slope(gen(n))
            if fit:
                hits += fit["r_squared"] > 0.6
                slopes.append(fit["slope"])
        return hits / trials, float(np.mean(slopes))

    def test_a_rising_distribution_passes_the_power_law_claim(self):
        rate, slope = self._rate(lambda n: self.rng.uniform(1, 1000, n))
        self.assertGreater(rate, 0.95)
        self.assertGreater(slope, 0.0)

    def test_lognormal_passes_and_exponential_does_not(self):
        self.assertGreater(self._rate(
            lambda n: self.rng.lognormal(0, 2, n))[0], 0.95)
        self.assertLess(self._rate(
            lambda n: 1 + self.rng.exponential(10, n))[0], 0.05)

    def test_a_true_power_law_passes(self):
        self.assertGreater(self._rate(
            lambda n: (1 - self.rng.random(n)) ** (-1 / 1.0))[0], 0.95)

    def test_the_degeneracy_is_reported_beside_the_answer(self):
        fit = A.fit_log_binned_slope(self.rng.uniform(1, 1000, 1000))
        self.assertTrue(fit["slope_is_positive"])
        self.assertEqual(fit["constrains"], ["r_squared"])

    def test_the_claim_description_says_what_it_constrains(self):
        self.assertIn("straightness", A.get_forest_claims()[0].description)


class TestASF_9_SlopeConvention(unittest.TestCase):
    def test_fitted_slope_is_one_minus_the_density_exponent(self):
        rng = np.random.default_rng(1)
        for alpha in (1.5, 2.0, 3.0):
            slopes = [A.fit_log_binned_slope(
                (1 - rng.random(20000)) ** (-1 / (alpha - 1)))["slope"]
                for _ in range(6)]
            self.assertAlmostEqual(float(np.mean(slopes)), 1 - alpha,
                                   delta=0.15)

    def test_density_exponent_is_reported(self):
        rng = np.random.default_rng(2)
        fit = A.fit_log_binned_slope((1 - rng.random(20000)) ** (-1 / 1.0))
        self.assertAlmostEqual(fit["density_exponent"], 1 - fit["slope"], 12)
        self.assertAlmostEqual(fit["density_exponent"], 2.0, delta=0.15)
        self.assertIn("binned_count", fit["slope_convention"])

    def test_the_generated_claims_threshold_is_in_the_binned_count_frame(self):
        """-1.5 here is a density exponent of 2.5, not 1.5. ASF-15."""
        desc = A.AdaptiveAgent("T")._generate_claims(
            {"size_distribution": {"r_squared": 0.9}}, "forest")[0].description
        self.assertIn("density exponent above 2.5", desc)


class TestASF_10_StepBudget(unittest.TestCase):
    def test_the_verdict_flips_on_num_steps_alone(self):
        claim = A.get_fluctuating_claims()[0]
        verdicts = []
        for ns in (100, 1000):
            out = A.FluctuatingPopSim(dict(FLUCT, num_steps=ns)).run()
            verdicts.append(claim.test(out)[0])
        self.assertEqual(verdicts, [A.FAILED, A.PASSED])

    def test_coexistence_is_exactly_the_censored_set(self):
        for ns in (100, 400, 1000):
            out = A.FluctuatingPopSim(dict(FLUCT, num_steps=ns)).run()
            self.assertAlmostEqual(
                out["fixation_probability"]["coexistence"],
                out["censored_fraction"], 12)

    def test_mean_fixation_time_is_biased_low_by_censoring(self):
        """P-CENSORED-INPUT: it averages only the replicates that fixed,
        discarding exactly the slowest ones."""
        runs = {ns: A.FluctuatingPopSim(dict(FLUCT, num_steps=ns)).run()
                for ns in (500, 1000, 5000)}
        self.assertEqual(runs[5000]["censored_fraction"], 0.0)
        true_mean = runs[5000]["mean_fixation_time"]
        self.assertLess(runs[500]["mean_fixation_time"],
                        runs[1000]["mean_fixation_time"])
        self.assertLess(runs[1000]["mean_fixation_time"], true_mean)
        self.assertLess(runs[500]["mean_fixation_time"], 0.4 * true_mean)

    def test_the_claim_message_names_the_budget(self):
        out = A.FluctuatingPopSim(dict(FLUCT, num_steps=100)).run()
        self.assertIn("step cap", A.get_fluctuating_claims()[0].test(out)[1])

    def test_as_received_reports_no_censoring_at_all(self):
        out = as_received().FluctuatingPopSim(
            dict(FLUCT, num_steps=100)).run()
        self.assertNotIn("censored_fraction", out)


class TestASF_11_RateAsProbability(unittest.TestCase):
    def test_switching_rate_saturates(self):
        outs = [A.FluctuatingPopSim(
            dict(FLUCT, switching_rate=sr, num_steps=20000,
                 growth_rate_ratio=0.9, num_replicates=10, base_seed=7)
        ).run()["fixation_probability"] for sr in (2.0, 5.0, 50.0)]
        self.assertEqual(outs[0], outs[1])
        self.assertEqual(outs[1], outs[2])

    def test_saturation_is_reported(self):
        self.assertTrue(A.FluctuatingPopSim(
            dict(FLUCT, switching_rate=5.0)).run()["switch_prob_saturated"])
        self.assertFalse(A.FluctuatingPopSim(
            dict(FLUCT, switching_rate=0.3)).run()["switch_prob_saturated"])

    def test_switch_probability_matches_the_generator_diagonal(self):
        s = A.FluctuatingPopSim(dict(FLUCT, switching_rate=0.3))
        self.assertAlmostEqual(s.switch_probability(2), 0.3, 12)
        self.assertAlmostEqual(s.switch_probability(0), 0.15, 12)

    def test_the_agents_exploration_branch_reaches_saturation(self):
        rate = 0.3
        for _ in range(7):
            rate *= 1.3
        self.assertGreaterEqual(rate, 1.0)


class TestASF_12_ConfoundedRadius(unittest.TestCase):
    def test_dispersal_range_one_disables_competition(self):
        sim = A.ForestScalingSim(dict(FOREST, dispersal_range=1,
                                      initial_density=0.5))
        self.assertEqual(sim.competition_radius, 0)
        self.assertEqual(sim._local_competition(8, 8), 0.0)
        self.assertGreater(sim.competition_strength, 0)

    def test_default_preserves_as_received_behaviour(self):
        for dr in (1, 2, 4, 8, 9):
            self.assertEqual(
                A.ForestScalingSim(dict(FOREST,
                                        dispersal_range=dr)).competition_radius,
                dr // 2)

    def test_the_radius_can_now_be_set_independently(self):
        sim = A.ForestScalingSim(dict(FOREST, dispersal_range=1,
                                      competition_radius=3,
                                      initial_density=0.5))
        self.assertEqual(sim.competition_radius, 3)
        self.assertGreater(sim._local_competition(8, 8), 0.0)

    def test_the_confound_is_reported(self):
        out = A.run_model("forest", dict(FOREST, dispersal_range=1), 3)
        self.assertTrue(out["competition_disabled"])
        self.assertFalse(A.run_model("forest", FOREST, 3)
                         ["competition_disabled"])


class TestASF_13_ExplorationRate(unittest.TestCase):
    def test_exploration_rate_changes_behaviour(self):
        tags = ["not_at_steady_state", "competition_too_weak"]
        np.random.seed(0)
        self.assertIsNotNone(
            A.AdaptiveAgent("T", exploration_rate=0.0)._choose_diagnosis(tags))
        np.random.seed(0)
        self.assertIsNone(
            A.AdaptiveAgent("T", exploration_rate=1.0)._choose_diagnosis(tags))

    def test_as_received_never_reads_it(self):
        src = open(os.path.join(
            EVIDENCE, "adaptive_sim_framework_asreceived.py")).read()
        body = src.split("class AdaptiveAgent")[1].split("class ")[0]
        self.assertEqual(body.count("self.exploration_rate"), 1)


class TestASF_14_ExtinctionVsExclusion(unittest.TestCase):
    def test_landed_distinguishes_them(self):
        claim = A.get_forest_claims()[1]
        self.assertEqual(claim.test({"num_trees": 0, "species_richness": 0,
                                     "extinct": True})[0], A.INCONCLUSIVE)
        self.assertEqual(claim.test({"num_trees": 900, "species_richness": 1,
                                     "extinct": False})[0], A.FAILED)
        self.assertEqual(claim.test({"num_trees": 900, "species_richness": 3,
                                     "extinct": False})[0], A.PASSED)

    def test_as_received_returns_the_same_verdict_for_both(self):
        claim = as_received().get_forest_claims()[1]
        self.assertFalse(claim.test({"species_richness": 0})[0])
        self.assertFalse(claim.test({"species_richness": 1})[0])

    def test_extinct_is_reported_by_the_model(self):
        self.assertTrue(A.run_model(
            "forest", dict(FOREST, mortality_base=0.9), 1)["extinct"])
        self.assertFalse(A.run_model("forest", FOREST, 1)["extinct"])


class TestASF_15_16_GeneratedClaims(unittest.TestCase):
    def test_ids_no_longer_collide(self):
        ag = A.AdaptiveAgent("T")
        out = {"size_distribution": {"r_squared": 0.9}}
        ids = [ag._generate_claims(out, "forest")[0].claim_id
               for _ in range(3)]
        self.assertEqual(len(set(ids)), 3)

    def test_as_received_ids_collide_within_a_second(self):
        R = as_received()
        ag = R.AdaptiveAgent()
        out = {"size_distribution": {"r_squared": 0.9}}
        ids = [ag._generate_claims(out, "forest", {})[0].claim_id
               for _ in range(2)]
        self.assertEqual(len(set(ids)), 1)

    def test_description_matches_the_test(self):
        claim = A.AdaptiveAgent("T")._generate_claims(
            {"size_distribution": {"r_squared": 0.9}}, "forest")[0]
        self.assertIn("NOT a correlation", claim.description)
        self.assertTrue(claim.test_function(
            {"size_distribution": {"slope": -2.0}})[0])
        self.assertFalse(claim.test_function(
            {"size_distribution": {"slope": -0.37}})[0])

    def test_as_received_description_claims_an_untested_correlation(self):
        claim = as_received().AdaptiveAgent()._generate_claims(
            {"size_distribution": {"r_squared": 0.9}}, "forest", {})[0]
        self.assertIn("correlated with seed injection rate", claim.description)


class TestLoggingContract(unittest.TestCase):
    def test_log_refuses_to_stringify_silently(self):
        with self.assertRaises(TypeError):
            json.dumps({"x": object()}, default=A._json_default)

    def test_numpy_scalars_serialise_as_numbers(self):
        s = json.dumps({"a": np.float64(0.5), "b": np.int64(3),
                        "c": np.array([1, 2])}, default=A._json_default)
        self.assertEqual(json.loads(s), {"a": 0.5, "b": 3, "c": [1, 2]})

    def test_a_written_record_round_trips(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "l.jsonl")
            _, lg = _run_loop(A, iterations=2)
            lg2 = A.ProvenanceLogger(log_file=path)
            for r in lg.records:
                lg2.log_run(r)
            rows = [json.loads(x) for x in open(path) if x.strip()]
            self.assertEqual(len(rows), len(lg.records))
            self.assertTrue(all(r["code_sha256"] for r in rows))
            self.assertTrue(all("diagnoses" in s
                                for r in rows for s in r["reasoning_chain"]))


class TestSuiteIsLoaded(unittest.TestCase):
    """P-STALE-PATH: a class defined after unittest.main() never runs."""

    def test_every_declared_test_is_collected(self):
        src = open(__file__).read()
        declared = src.count("\n    def test_")
        loaded = unittest.defaultTestLoader.loadTestsFromModule(
            sys.modules[__name__]).countTestCases()
        self.assertEqual(declared, loaded)


if __name__ == "__main__":
    unittest.main(verbosity=2)
