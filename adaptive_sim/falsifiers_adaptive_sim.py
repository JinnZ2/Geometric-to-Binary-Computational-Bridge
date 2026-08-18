#!/usr/bin/env python3
"""
falsifiers_adaptive_sim.py -- runnable report for ASF-1..16.

    python adaptive_sim/falsifiers_adaptive_sim.py

Needs numpy. Each line asserts the state the AUDIT header in
`adaptive_sim/adaptive_sim_framework.py` records -- for a defect that was
fixed, that the fix is still there; for one deliberately left in place, that
it is still there exactly as described. Exits nonzero when any of them stops
holding, so a later change that contradicts the header fails here instead of
leaving the header quietly wrong.

A PASS is not "this framework is correct". Several checks assert defects
(ASF-8, ASF-10, ASF-11, ASF-12): fixing one is expected to fail this report,
and the response is to amend the finding, not to delete the check.

Two implementations are loaded. `A` is the landed framework; `R` is
`evidence/adaptive_sim_framework_asreceived.py`, the file as it arrived,
loaded by path because ASF-1 and ASF-7 are claims about THAT code and cannot
be checked against its replacement.
"""
import copy
import importlib.util
import io
import json
import os
import sys
import contextlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

from adaptive_sim import adaptive_sim_framework as A          # noqa: E402

EVIDENCE = os.path.join(HERE, "evidence")


def _load_as_received():
    path = os.path.join(EVIDENCE, "adaptive_sim_framework_asreceived.py")
    spec = importlib.util.spec_from_file_location("asf_as_received", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


R = _load_as_received()

FAILURES = []
CHECKS = []


def check(cid, claim, ok, detail=""):
    CHECKS.append(cid)
    print("  %-8s %-58s %s" % (cid, claim, "holds" if ok else "BROKEN"))
    if detail:
        for line in str(detail).splitlines():
            print("           %s" % line)
    if not ok:
        FAILURES.append(cid)


def quiet(fn, *a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*a, **kw)


FLUCT = {"num_states": 5, "carrying_capacities": [50, 100, 200, 300, 400],
         "switching_rate": 0.3, "growth_rate_fast": 1.0,
         "growth_rate_ratio": 0.95, "num_steps": 3000, "num_replicates": 40,
         "base_seed": 123}

FOREST_SMALL = {"grid_size": 20, "metabolic_exponent": 0.75,
                "competition_strength": 0.8, "dispersal_range": 4,
                "seed_rate": 0.15, "mortality_base": 0.01, "num_steps": 30,
                "initial_density": 0.15, "num_species": 3, "min_size": 1.0}


# ---------------------------------------------------------------- provenance

print("\nPROVENANCE -- can a record be reproduced from its own fields?")

log = os.path.join(EVIDENCE, "provenance_fluctuating.jsonl")
rows = A.verify_log(log, module=R)
replayable = [r for r in rows if r["replayable"]]
bad = [r for r in replayable if not r["reproduces"]]
check("ASF-1", "shipped log does not reproduce under the shipped code",
      len(replayable) == 5 and len(bad) == 5,
      "%d of %d replayable records mismatch under the AS-RECEIVED file"
      % (len(bad), len(replayable)))

# The decisive record: identical dynamics, one field disagrees. If the whole
# log simply came from different parameters, this would differ everywhere.
dec = [r for r in rows if r["run_id"] == "db001b18502f"]
paths = sorted(p for p, _, _ in dec[0]["diffs"]) if dec else []
check("ASF-1", "record db001b18502f differs ONLY in the timing fields",
      paths == ["mean_fixation_time", "std_fixation_time"],
      "fixation_probability reproduces exactly (0.65 / 0.35 / 0.0); "
      "mean_fixation_time logged 0.0, recomputed %.3f"
      % (dec[0]["diffs"][0][2] if dec and dec[0]["diffs"] else float("nan")))

check("ASF-1", "the landed record carries a code fingerprint",
      "code_sha256" in A.SimulationRecord.__dataclass_fields__
      and "code_sha256" not in R.SimulationRecord.__dataclass_fields__,
      "as-received records had no code identity, so nothing could disagree")

rid1 = A.content_run_id("abc", "forest", {"a": 1}, 42)
rid2 = A.content_run_id("abc", "forest", {"a": 1}, 42)
rid3 = A.content_run_id("abc", "forest", {"a": 2}, 42)
check("ASF-1", "run_id is content-addressed, not a hash of the wall clock",
      rid1 == rid2 and rid1 != rid3,
      "same code+params+seed -> %s; changed params -> %s" % (rid1, rid3))

# ASF-2 -----------------------------------------------------------------
seeds_named = [json.loads(l)["random_seed"]
               for l in open(log) if l.strip()]
src = open(os.path.join(EVIDENCE,
                        "adaptive_sim_framework_asreceived.py")).read()
check("ASF-2", "as-received: record names a seed nothing was seeded with",
      seeds_named[:4] == [123, 124, 125, 126]
      and src.count("np.random.seed(random_seed)") == 1,
      "records claim seeds %s; np.random.seed(random_seed) appears once, at "
      "loop entry" % seeds_named[:4])

o1 = A.run_model("forest", FOREST_SMALL, 7)
o2 = A.run_model("forest", FOREST_SMALL, 7)
o3 = A.run_model("forest", FOREST_SMALL, 8)
check("ASF-2", "landed: a run is a pure function of (params, recorded seed)",
      o1 == o2 and o1 != o3,
      "seed 7 twice -> num_trees %d, %d; seed 8 -> %d"
      % (o1["num_trees"], o2["num_trees"], o3["num_trees"]))


# ------------------------------------------------------------------ the loop

print("\nTHE ADAPTIVE LOOP")

FLUCT_FAIL = dict(FLUCT, num_steps=150)


def _loop(mod, iterations=4, seed=123, exploration_rate=0.0):
    lg = mod.ProvenanceLogger(log_file=None if mod is A else os.devnull)
    ag = mod.AdaptiveAgent("T", exploration_rate=exploration_rate)
    rn = mod.SimulationRunner("fluctuating", lg, ag)
    for c in mod.get_fluctuating_claims():
        rn.register_claim(c)
    res = quiet(rn.run_adaptive_loop, copy.deepcopy(FLUCT_FAIL),
                max_iterations=iterations, random_seed=seed)
    return res, lg


res_r, lg_r = _loop(R)
in_mem = [round(it["params"]["switching_rate"], 4)
          for it in res_r["iteration_results"]]
logged = [round(rc.parameters["switching_rate"], 4) for rc in lg_r.records]
check("ASF-3", "as-received: in-memory results lag the record by one "
      "iteration", in_mem[:-1] == logged[1:],
      "results['params'] %s vs record.parameters %s" % (in_mem, logged))

res_a, lg_a = _loop(A)
# num_steps, not switching_rate: it is the parameter the landed agent moves,
# so this comparison exercises something. Against switching_rate the landed
# loop leaves the value at 0.3 throughout and the assertion would pass
# without testing the pairing at all.
in_mem_a = [it["params"]["num_steps"] for it in res_a["iteration_results"]]
next_a = [it["next_params"]["num_steps"] for it in res_a["iteration_results"]]
logged_a = [rc.parameters["num_steps"] for rc in lg_a.records]
check("ASF-3", "landed: results['params'] is what that iteration ran",
      in_mem_a == logged_a and len(set(in_mem_a)) > 1
      and next_a[:-1] == in_mem_a[1:],
      "ran %s ; logged %s ; proposed-next %s" % (in_mem_a, logged_a, next_a))

check("ASF-4", "as-received: claims_tested is empty after a full loop",
      res_r["logger_summary"]["claims_tested"] == []
      and src.count("log_claim_result") == 1,
      "log_claim_result is defined once and called never")
check("ASF-4", "landed: claims_tested lists the claims actually tested",
      sorted(res_a["logger_summary"]["claims_tested"])
      == ["fluctuating_fixation", "fluctuating_slow_persistence"],
      res_a["logger_summary"]["claims_tested"])


# ------------------------------------------------------------------- claims

print("\nCLAIM STATUS -- a broken test is not a refutation")


def boom(_o):
    raise ValueError("instrument fault")


status, msg, _ = A.Claim("x", "", "forest", boom).test({})
check("ASF-5", "landed: a raising test is INCONCLUSIVE, not FAILED",
      status == A.INCONCLUSIVE, "status=%r  message=%r" % (status, msg))

r_claim = R.Claim("x", "", "forest", boom)
passed_r, _, _ = r_claim.test({})
check("ASF-5", "as-received: the same test is recorded as a refutation",
      passed_r is False and r_claim.status == "inconclusive",
      "Claim.status became 'inconclusive' but run_adaptive_loop wrote "
      "{'status': 'passed' if passed else 'failed'}, discarding it")

dead = {"num_trees": 0, "species_richness": 0, "extinct": True}
pl, coex = A.get_forest_claims()
check("ASF-5", "landed: the forest claims survive a collapsed grid",
      pl.test(dead)[0] == A.INCONCLUSIVE, pl.test(dead)[1])
r_pl = R.get_forest_claims()[0]
_, r_msg, _ = r_pl.test({"num_trees": 12, "species_richness": 1})
check("ASF-5", "as-received: the same input raises inside the test",
      "Test error" in r_msg, r_msg)

check("ASF-14", "landed: extinction is INCONCLUSIVE, exclusion is FAILED",
      coex.test(dead)[0] == A.INCONCLUSIVE
      and coex.test({"num_trees": 900, "species_richness": 1,
                     "extinct": False})[0] == A.FAILED,
      "an empty grid and competitive exclusion are different events")
r_coex = R.get_forest_claims()[1]
check("ASF-14", "as-received: both return the same verdict",
      r_coex.test({"species_richness": 0})[0] is False
      and r_coex.test({"species_richness": 1})[0] is False,
      "richness 0 (dead) and richness 1 (excluded) both -> failed")


# ------------------------------------------------------------------- agent

print("\nAGENT -- reachability of its own diagnoses")

h = R.AdaptiveAgent()._generate_hypothesis(
    {"size_distribution": {"r_squared": 0.5}},
    [R.Claim("forest_power_law", "", "forest", lambda o: (False, "", {}))],
    "forest")
base = {"competition_strength": 0.8, "num_steps": 500}
np.random.seed(0)
r_new, r_act = R.AdaptiveAgent()._propose_action(base, h, "forest", {})
check("ASF-6", "as-received: the num_steps branch is unreachable",
      "competition too weak" in h and "not at steady state" in h
      and r_new["num_steps"] == base["num_steps"],
      "one hypothesis string contains both substrings; the first tested wins\n"
      "action taken: %s" % r_act)

ag = A.AdaptiveAgent("T", exploration_rate=0.0)
tags = ag._diagnose({"size_distribution": {"r_squared": 0.5}},
                    [A.Claim("forest_power_law", "", "forest", None)],
                    "forest")
applied = ag._choose_diagnosis(tags)
a_new, a_act = ag._propose_action(base, applied, "forest")
check("ASF-6", "landed: num_steps is reachable from the same diagnosis",
      applied == "not_at_steady_state"
      and a_new["num_steps"] > base["num_steps"],
      "diagnoses %s -> %s" % (tags, a_act))

ag2 = A.AdaptiveAgent("T", exploration_rate=0.0)
ag2.tried = ["not_at_steady_state"]
check("ASF-6", "landed: an untried diagnosis is preferred to a repeat",
      ag2._choose_diagnosis(tags) == "competition_too_weak",
      "the shipped fluctuating log spends four iterations on one knob")

near_dead = {"num_trees": 12, "species_richness": 1}
np.random.seed(1)
h7 = R.AdaptiveAgent()._generate_hypothesis(
    near_dead, [R.get_forest_claims()[0]], "forest")
_, act7 = R.AdaptiveAgent()._propose_action(
    {"competition_strength": 0.8, "num_steps": 500}, h7, "forest", near_dead)
check("ASF-7", "as-received: a dying forest is answered with more "
      "competition", "Increased competition_strength" in act7, act7)

np.random.seed(0)
low = A.AdaptiveAgent("T", exploration_rate=0.0)
np.random.seed(0)
high = A.AdaptiveAgent("T", exploration_rate=1.0)
check("ASF-13", "landed: exploration_rate is read",
      low._choose_diagnosis(tags) is not None
      and high._choose_diagnosis(tags) is None,
      "0.0 -> acts on a diagnosis, 1.0 -> explores; as-received stored the "
      "parameter and branched on a literal 0.5")
check("ASF-13", "as-received: exploration_rate is never read",
      "self.exploration_rate" not in
      src.split("def _propose_action")[1].split("def _generate_claims")[0],
      "assigned in __init__ and referenced nowhere else")

a = A.AdaptiveAgent("T")
ids = [a._generate_claims({"size_distribution": {"r_squared": 0.9}},
                          "forest")[0].claim_id for _ in range(2)]
r_ids = [R.AdaptiveAgent()._generate_claims(
    {"size_distribution": {"r_squared": 0.9}}, "forest", {})[0].claim_id
    for _ in range(2)]
check("ASF-16", "landed ids are unique; as-received ids collide",
      ids[0] != ids[1] and r_ids[0] == r_ids[1],
      "landed %s ; as-received %s" % (ids, r_ids))

desc = A.AdaptiveAgent("T")._generate_claims(
    {"size_distribution": {"r_squared": 0.9}}, "forest")[0].description
r_desc = R.AdaptiveAgent()._generate_claims(
    {"size_distribution": {"r_squared": 0.9}}, "forest", {})[0].description
check("ASF-15", "the generated claim no longer describes a correlation it "
      "does not test", "correlated" in r_desc and "NOT a correlation" in desc,
      "as-received: %r" % r_desc)


# ------------------------------------------------- what the claims measure

print("\nWHAT THE CLAIMS ACTUALLY MEASURE  (defects left in place, on purpose)")

rng = np.random.default_rng(0)
N, TRIALS = 1000, 60


def pass_rate(gen):
    hits, slopes = 0, []
    for _ in range(TRIALS):
        fit = A.fit_log_binned_slope(gen())
        if fit:
            hits += fit["r_squared"] > 0.6
            slopes.append(fit["slope"])
    return hits / TRIALS, float(np.mean(slopes))


uni_rate, uni_slope = pass_rate(lambda: rng.uniform(1, 1000, N))
ln_rate, _ = pass_rate(lambda: rng.lognormal(0, 2, N))
exp_rate, _ = pass_rate(lambda: 1 + rng.exponential(10, N))
check("ASF-8", "R2>0.6 passes a distribution with MORE big trees than small",
      uni_rate > 0.95 and uni_slope > 0,
      "uniform[1,1000] passes %.0f%% of draws at mean slope %+.3f"
      % (100 * uni_rate, uni_slope))
check("ASF-8", "the same gate is not vacuous -- it does reject some shapes",
      ln_rate > 0.95 and exp_rate < 0.05,
      "lognormal(0,2) passes %.0f%%, exponential passes %.0f%%"
      % (100 * ln_rate, 100 * exp_rate))
check("ASF-8", "the degeneracy travels with the answer",
      A.fit_log_binned_slope(rng.uniform(1, 1000, N))["slope_is_positive"]
      is True, "size_distribution reports slope_is_positive and constrains")

err = []
for alpha in (1.5, 2.0, 2.5, 3.0):
    s = [A.fit_log_binned_slope(
        (1 - rng.random(20000)) ** (-1 / (alpha - 1)))["slope"]
        for _ in range(8)]
    err.append((alpha, float(np.mean(s))))
check("ASF-9", "the fitted slope is 1-alpha, not -alpha (no bin-width "
      "division)",
      all(abs((1 - alpha) - m) < 0.15 for alpha, m in err),
      "; ".join("alpha=%.1f -> slope %+.3f (1-alpha = %+.1f)"
                % (a_, m, 1 - a_) for a_, m in err))
fit = A.fit_log_binned_slope((1 - rng.random(20000)) ** (-1 / 1.0))
check("ASF-9", "the conversion is reported beside the raw slope",
      abs(fit["density_exponent"] - (1 - fit["slope"])) < 1e-12
      and "binned_count" in fit["slope_convention"],
      "density_exponent = 1 - slope = %.3f" % fit["density_exponent"])

verdicts = []
for ns in (100, 300, 1000, 10000):
    out = A.FluctuatingPopSim(dict(FLUCT, num_steps=ns)).run()
    verdicts.append((ns, out["fixation_probability"]["coexistence"],
                     out["censored_fraction"]))
flips = {c < 0.5 for _, c, _ in verdicts}
check("ASF-10", "the fixation claim's verdict flips on num_steps alone",
      len(flips) == 2,
      "; ".join("num_steps=%d coexist %.3f censored %.3f -> %s"
                % (n, c, f, "PASS" if c < 0.5 else "FAIL")
                for n, c, f in verdicts))
check("ASF-10", "censoring is reported, so 'coexistence' cannot be read as "
      "biology",
      all(abs(c - f) < 1e-12 for _, c, f in verdicts),
      "every 'coexisting' replicate is one that hit the step cap")

means = [(ns, A.FluctuatingPopSim(dict(FLUCT, num_steps=ns)).run())
         for ns in (500, 1000, 5000)]
true_mean = means[-1][1]["mean_fixation_time"]
check("ASF-10", "mean_fixation_time is biased low by the same censoring",
      means[-1][1]["censored_fraction"] == 0.0
      and means[0][1]["mean_fixation_time"] < 0.4 * true_mean
      and means[0][1]["mean_fixation_time"] < means[1][1]["mean_fixation_time"]
      < true_mean,
      "; ".join("budget %d censored %.3f -> mean %.1f"
                % (ns, o["censored_fraction"], o["mean_fixation_time"])
                for ns, o in means)
      + "\nit averages only the replicates that fixed, discarding exactly "
        "the slowest, and looks converged at every stop")

outs = [A.FluctuatingPopSim(dict(FLUCT, switching_rate=sr, num_steps=20000,
                                 growth_rate_ratio=0.9, num_replicates=20,
                                 base_seed=7)).run()["fixation_probability"]
        for sr in (2.0, 5.0, 50.0)]
check("ASF-11", "switching_rate saturates: 2.0, 5.0 and 50.0 are identical",
      outs[0] == outs[1] == outs[2], "all three -> %s" % outs[0])
sat = A.FluctuatingPopSim(dict(FLUCT, switching_rate=5.0))
check("ASF-11", "saturation is reported",
      sat.switch_probability(2) == 1.0
      and sat.run()["switch_prob_saturated"] is True,
      "a CTMC rate consumed as a per-step Bernoulli probability")

zero = A.ForestScalingSim(dict(FOREST_SMALL, dispersal_range=1,
                               initial_density=0.5))
default = A.ForestScalingSim(dict(FOREST_SMALL, dispersal_range=4,
                                  initial_density=0.5))
check("ASF-12", "dispersal_range 1 disables competition entirely",
      zero.competition_radius == 0
      and zero._local_competition(10, 10) == 0.0
      and default._local_competition(10, 10) > 0,
      "competition_strength is still logged at %.1f while the neighbourhood "
      "is empty" % zero.competition_strength)
check("ASF-12", "the default preserves as-received behaviour, explicitly",
      A.ForestScalingSim(dict(FOREST_SMALL,
                              dispersal_range=9)).competition_radius == 4
      and A.ForestScalingSim(dict(FOREST_SMALL, dispersal_range=9,
                                  competition_radius=1)
                             ).competition_radius == 1,
      "competition_radius defaults to dispersal_range // 2 and is settable")


# ------------------------------------------------------------------ summary

print("\n%d checks over %d findings." % (len(CHECKS), len(set(CHECKS))))
if FAILURES:
    print("BROKEN: %s" % ", ".join(sorted(set(FAILURES))))
    print("A finding stopped holding. Amend the AUDIT header rather than "
          "deleting the check.")
    raise SystemExit(1)
print("All findings hold as recorded.")
