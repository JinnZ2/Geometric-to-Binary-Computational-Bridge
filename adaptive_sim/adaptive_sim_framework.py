"""
Adaptive Simulation Framework for Scientific Claim Testing
==========================================================
Runs simulations, tests falsifiable claims against their outcomes, logs
provenance, and lets an agent modify the experiment based on what failed.

    python adaptive_sim/adaptive_sim_framework.py --model forest --iterations 5
    python adaptive_sim/adaptive_sim_framework.py --model fluctuating --iterations 5
    python adaptive_sim/adaptive_sim_framework.py --verify <log.jsonl>

Models:
  - forest       spatially explicit metabolic-scaling forest
  - fluctuating  multi-state switching environment over a Moran process

Requires numpy.

=============================================================================
AUDIT -- ASF-1..16
=============================================================================
Arrived as a single 723-line file with two provenance logs and a results
plot. The framework's own thesis is that a run is reproducible from its
record, so the first thing done to it was to take that seriously: re-run the
logged records from their logged fields and compare. They do not match.

Every number below was measured, not read off the source. The runnable
report is `adaptive_sim/falsifiers_adaptive_sim.py`; the arithmetic and the
null sweeps are in `adaptive_sim/AUDIT.md`.

FIXED here (each was a defect with no defensible alternative reading):

  ASF-1  THE PROVENANCE LOG CANNOT BE REPRODUCED BY THE CODE SHIPPED WITH IT.
         A `fluctuating` outcome is a pure function of its logged parameters
         plus `base_seed` -- `_run_replicate` reseeds from it and the model
         reads no other entropy -- so a record is replayable in principle and
         a mismatch is evidence about the code. Two fields disagree. At the
         logged parameters of record `db001b18502f` the shipped code
         reproduces `fixation_probability` exactly (0.65 / 0.35 / 0.0) and
         returns `mean_fixation_time` = 1053.575 where the record says 0.0.
         At record `fc874f5f733b` (num_steps 3000) the log says coexistence
         1.000; the shipped code says 0.025. Everything that could match did
         match, one field did not, and nothing in the record could have said
         so: there was no code identity in it.
         Fixed by making the record self-checking. `code_sha256` (of the
         model source), a content-addressed `run_id` = H(code, model, params,
         seed) replacing a hash of the wall clock, and `--verify`, which
         re-runs each record and diffs the outcomes. That subcommand is what
         found this.

  ASF-2  `random_seed` in the record was `random_seed + iteration`, a value
         never passed to any seeding call. `np.random.seed` was called once,
         at loop entry. The forest model draws from the global stream, so
         iteration k>0 was not replayable at all: replaying record-seed 43
         gives a different forest from the one iteration 1 actually ran.
         `fluctuating` was replayable, but through `base_seed` -- the field
         not named seed. Fixed: each iteration is seeded with the value its
         record names, and `seeds` records the loop seed, the iteration seed
         and the base seed separately. `base_seed` stays FIXED across
         iterations on purpose -- it is what makes successive iterations a
         paired comparison rather than a new draw -- and now says so.

  ASF-3  `iteration_results` was appended after the agent had already
         overwritten `current_params`, so the returned structure paired each
         iteration's outcomes with the NEXT iteration's parameters:
         [0.21, 0.147, 0.1029, 0.1029] against records [0.3, 0.21, 0.147,
         0.1029]. The jsonl was right and the in-memory result -- what
         `main()` prints and what any plot would read -- was wrong. The last
         entry coincides, because the final iteration does not call the agent.

  ASF-4  `log_claim_result` had no callers, so `summary()['claims_tested']`
         was `[]` on every run ever made. Now called.

  ASF-5  A raising test function was recorded as `failed`, indistinguishable
         from a refutation. `Claim.status` did get 'inconclusive', but
         `claim_results` carried only the passed/failed projection, so the
         distinction was created and then discarded one line later. And the
         shipped forest test raised on any collapsed forest -- `'N/A':.3f` is
         a ValueError -- so "the forest died" was logged as "the power-law
         claim is refuted". Inconclusive is now a third status that travels
         into the record, and an inconclusive claim does not drive the agent:
         a broken thermometer is not evidence about the weather.

  ASF-6  The `num_steps` action was unreachable. `_generate_hypothesis` emits
         one string containing BOTH "competition too weak" and "not at steady
         state", and `_propose_action` tested the first substring first, so
         the second branch could never fire -- the agent could not turn the
         one knob whose name matched its own diagnosis. The shipped
         fluctuating log is that failure in the wild: four iterations shrink
         `switching_rate` 0.3 -> 0.103 with the outcome pinned at coexistence
         1.000, and the run that finally worked did it by raising `num_steps`
         3000 -> 50000, by hand, out of band. Fixed by making the reasoning
         chain carry structured `diagnoses` tags instead of prose to be
         grepped, and by trying an untried diagnosis before repeating one:
         the log's four-iterations-on-one-knob is the behaviour that motivated
         the rule, and it is a policy choice, recorded as one.

  ASF-13 `exploration_rate` was stored and never read; the branch it names
         was a hardcoded 0.5. Wired to its plain meaning -- the probability
         of exploring instead of acting on a diagnosis -- so that 0.0 and 1.0
         now differ. The semantics are chosen, not recovered.

  ASF-15 The auto-generated claim's description was "Power-law slope is
         negatively correlated with seed injection rate" and its test was
         `slope < -1.5` on a single run with `seed_rate` never varied. Also
         a threshold in the other slope convention (see ASF-9), so it fails on
         arrival at the observed slopes of -0.369 and -0.412. Description
         corrected to state what the test does. The correlation claim it was
         named for is still tested by nothing; testing it needs a sweep, which
         is open problem ASF-A.

  ASF-16 `claim_id` embedded `int(time.time())`, so two claims generated in
         the same second collided. Measured: they do. Now a counter.

RECORDED, NOT PATCHED -- each fix would be a claim about forests or about
bacteria, and picking the number is the science, not the plumbing. Every one
of these now travels beside the answer instead of being silently absent,
which is the same remedy as AISS's `weights_are_flat` and the non-local
sensor's `scale_is_inferred`:

  ASF-8  `forest_power_law` constrains R2 and nothing else. Over 200 draws of
         1000 samples each, the claim passes 100% of uniform[1,1000] draws --
         at a fitted slope of +0.919, a distribution with MORE big trees than
         small ones passing a power-law claim -- and 100% of lognormal(0,2).
         It does reject exponential and gamma(2,10) at 0%, so it is not
         vacuous; it is unconstrained in the one direction that names it.
         `size_distribution` now reports `slope_is_positive` and `constrains`.

  ASF-9  The histogram is not divided by bin width, so with logarithmic bins
         the counts carry an extra factor of the bin width and the fitted
         slope is the binned-COUNT exponent, not the density exponent:
         measured slope = 1 - alpha, at alpha = 1.5/2.0/2.5/3.0 giving
         -0.473/-0.944/-1.442/-1.900. The logged -0.369 is therefore a density
         exponent of about 1.37, and a self-thinning -2 would appear here as
         -1. `density_exponent` and `slope_convention` are now reported. The
         raw `slope` is left alone so existing logs stay comparable.

  ASF-10 `fluctuating_fixation` is a claim about the step budget. At fixed
         biology, sweeping `num_steps` alone flips the verdict:
         100 -> coexistence 1.000 FAIL, 300 -> 0.975 FAIL, 500 -> 0.800 FAIL,
         1000 -> 0.375 PASS, 10000 -> 0.000 PASS. Replicates that hit the cap
         are right-censored, not coexisting -- measured, the "coexisting"
         fraction and the censored fraction are equal to floating point.
         The same censoring biases the other reported number, in the
         direction that hides it: `mean_fixation_time` averages over the
         replicates that fixed, which discards exactly the slowest ones, so
         at budget 500 it reports 366.4 against a true 1072.4 -- low by 2.9x,
         rising monotonically with the budget and looking converged at every
         stop. `censored_fraction` and `step_budget` are now reported. The
         mean is left uncorrected: the estimator for censored data is a
         survival fit, and choosing one is a modelling decision.

  ASF-11 `switching_rate` is a continuous-time generator rate consumed as a
         per-step Bernoulli probability, so it saturates: at rate >= 1 every
         step switches. Measured, rates 2.0, 5.0 and 50.0 give byte-identical
         outcomes. The agent's exploration branch multiplies by 1.3, so from
         the shipped 0.3 it walks into the saturated region in seven steps and
         keeps "exploring" a knob that has stopped doing anything.
         `switch_prob` and `switch_prob_saturated` are reported. Fixing it
         properly means choosing a time discretisation, which is a modelling
         decision.

  ASF-12 The competition radius was `dispersal_range // 2`, so one parameter
         drove two mechanisms. At dispersal_range 1 the radius is 0 and local
         competition is exactly 0.000 while `competition_strength` is still
         logged at its nonzero value -- and the agent reaches 1 through
         `max(1, dr + randint(-2, 3))`. `competition_radius` is now an
         explicit parameter defaulting to the old expression, so behaviour is
         unchanged and the confound is nameable by a caller.

  ASF-14 `forest_species_coexistence` returns the same FAIL for competitive
         exclusion and for an empty grid. Measured over 5 seeds at every
         setting the agent can reach -- competition at its 5.0 cap, dispersal
         at its floor of 1, sparse start -- richness is 3, 3, 3, 3, 3; the
         only configuration that fails it is high mortality, where richness is
         0 because the forest is dead. The claim now returns INCONCLUSIVE on
         an extinct grid (ASF-5's channel), which distinguishes the two
         without inventing a coexistence threshold.

  ASF-7  is the compound of ASF-5 and ASF-6 and is why they matter together:
         fed a near-extinct forest, the shipped agent's proposal is
         "Increased competition_strength to 1.200". The response to a dying
         forest was to kill it harder, and the reasoning chain recorded it as
         a hypothesis under test.

OPEN
  ASF-A  Nothing tests a claim of the form "X is correlated with parameter P".
         Every claim here is a threshold on one run. A correlation claim needs
         the runner to sweep P and fit across runs -- a different loop shape
         from this one, which varies parameters to CHASE a threshold rather
         than to measure a response.
  ASF-B  `mortality_base` 0.2 empties the grid, and nothing reports the run as
         degenerate other than by the claims coming back inconclusive. A
         cheap guard would be a floor on `num_trees` as a precondition for
         testing distributional claims at all.

License: CC-BY-4.0.
"""

import argparse
import copy
import hashlib
import inspect
import json
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

# =============================================================================
# PROVENANCE & LOGGING
# =============================================================================

#: ASF-5. A claim result is one of three things, and the third one is the
#: point: a test that raised is not a refutation. The shipped version created
#: this distinction on `Claim.status` and then dropped it when writing the
#: record, which is the same as not having made it.
PASSED = "passed"
FAILED = "failed"
INCONCLUSIVE = "inconclusive"


def code_fingerprint(*objects) -> str:
    """SHA-256 over the source of the objects a run's outcome depends on.

    ASF-1. The shipped record identified the model by the string "forest" and
    the run by a hash of the wall clock, so a record could not disagree with
    the code that claimed to have produced it -- and two of them did disagree,
    silently. Hashing the source is coarse (a comment changes it) but it is
    one-directional in the way that matters: it never says "same" about code
    that differs.
    """
    h = hashlib.sha256()
    for obj in objects:
        try:
            h.update(inspect.getsource(obj).encode("utf-8"))
        except (OSError, TypeError):          # interactively defined, etc.
            h.update(repr(obj).encode("utf-8"))
    return h.hexdigest()


@dataclass
class ReasoningStep:
    """A single step in the chain of reasoning.

    ASF-6. `diagnoses` is the structured form of what used to be recoverable
    only by substring-matching `hypothesis`. The prose is kept because it is
    what a person reads; the tags are what the code branches on, so a branch
    can no longer be shadowed by another branch's wording.
    """
    step_id: str
    timestamp: float
    agent_name: str
    observation: str
    hypothesis: str
    action: str
    parameters_changed: Dict[str, Any]
    expected_outcome: str
    parent_step_id: Optional[str] = None
    diagnoses: List[str] = field(default_factory=list)
    diagnosis_applied: Optional[str] = None


@dataclass
class SimulationRecord:
    """Record of a single simulation run.

    `run_id` is content-addressed: H(code_sha256, model, parameters, seed).
    Two runs of the same code at the same parameters and seed carry the same
    id, and a record whose id does not match its own fields has been edited.
    The shipped version hashed `time.time()`, which identifies nothing.
    """
    run_id: str
    model_name: str
    parameters: Dict[str, Any]
    random_seed: int
    timestamp: float
    duration_seconds: float
    outcomes: Dict[str, Any]
    claim_results: Dict[str, str]
    reasoning_chain: List[ReasoningStep]
    code_sha256: str = ""
    seeds: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)


class ProvenanceLogger:
    """Logs runs, reasoning and claim tests with enough to replay them."""

    def __init__(self, log_file: str = "provenance_log.jsonl"):
        self.log_file = log_file
        self.records: List[SimulationRecord] = []
        self.claim_history: Dict[str, List[Dict]] = defaultdict(list)

    def log_run(self, record: SimulationRecord):
        self.records.append(record)
        if self.log_file:
            with open(self.log_file, "a") as fh:
                fh.write(json.dumps(record.to_dict(), default=_json_default)
                         + "\n")

    def log_claim_result(self, claim_id: str, result: Dict):
        """ASF-4. Had no callers; `claims_tested` was empty on every run."""
        self.claim_history[claim_id].append(result)

    def get_run_by_id(self, run_id: str) -> Optional[SimulationRecord]:
        for r in self.records:
            if r.run_id == run_id:
                return r
        return None

    def get_chain_for_claim(self, claim_id: str) -> List[SimulationRecord]:
        return [r for r in self.records if claim_id in r.claim_results]

    def summary(self) -> Dict:
        return {
            "total_runs": len(self.records),
            "claims_tested": sorted(self.claim_history.keys()),
            "models_used": sorted({r.model_name for r in self.records}),
        }


def _json_default(obj):
    """Serialise numpy scalars as numbers, and refuse to stringify silently.

    The shipped logger passed `default=str`, which turns anything unknown
    into a JSON string -- a parameter that reloads as "0.72" instead of 0.72,
    with no error. On numpy 2 the arithmetic here happens to return Python
    scalars so nothing was actually corrupted, which is exactly why it is
    worth pinning: the log's types should not depend on which numpy is
    installed.
    """
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    raise TypeError("%r is not JSON serialisable; the provenance log will "
                    "not stringify it silently" % type(obj).__name__)


# =============================================================================
# CLAIM SYSTEM
# =============================================================================

@dataclass
class Claim:
    """A falsifiable claim about model behaviour."""
    claim_id: str
    description: str
    model_type: str
    test_function: Callable[[Dict[str, Any]], Tuple[bool, str, Dict]]
    priority: int = 1
    max_retries: int = 3
    status: str = "untested"
    evidence: List[Dict] = field(default_factory=list)

    def test(self, outcomes: Dict[str, Any]) -> Tuple[str, str, Dict]:
        """Return (status, message, details) where status is one of the three.

        ASF-5. Returns the status rather than a bool, so a caller cannot
        collapse `inconclusive` into `failed` by accident -- which is what the
        shipped `claim_results` dict did one line after the distinction was
        made.
        """
        try:
            result = self.test_function(outcomes)
            passed, message, details = result
            if passed is INCONCLUSIVE or passed == INCONCLUSIVE:
                status = INCONCLUSIVE
            else:
                status = PASSED if passed else FAILED
        except Exception as exc:                      # noqa: BLE001
            status, message, details = INCONCLUSIVE, "Test error: %s" % exc, {}
        self.status = status
        self.evidence.append({"status": status, "message": message,
                              "details": details, "timestamp": time.time()})
        return status, message, details


# =============================================================================
# ADAPTIVE AGENT
# =============================================================================

class AdaptiveAgent:
    """Analyses outcomes, proposes parameter changes, logs its reasoning.

    ASF-6. The shipped agent generated an English hypothesis and then chose
    its action by searching that English for substrings. Diagnoses are tags
    here; the prose is generated from the tags rather than parsed back out.
    """

    #: ASF-6. Ordered candidate diagnoses per (model, failed claim). Ordering
    #: within a list is a POLICY, not a derivation -- see the note on
    #: `_choose_diagnosis`.
    DIAGNOSES = {
        ("forest", "forest_power_law", "poor_fit"):
            ["not_at_steady_state", "competition_too_weak"],
        ("forest", "forest_power_law", "slope"):
            ["seed_injection", "metabolic_exponent"],
        ("forest", "forest_species_coexistence", None):
            ["competition_too_strong"],
        ("fluctuating", "fluctuating_fixation", None):
            ["not_at_steady_state", "population_too_large"],
        ("fluctuating", "fluctuating_slow_persistence", None):
            ["growth_rate_ratio", "switching_too_fast"],
    }

    PROSE = {
        "not_at_steady_state":
            "the run may not have reached steady state within num_steps",
        "competition_too_weak": "competition may be too weak",
        "competition_too_strong":
            "competition may be strong enough to exclude species",
        "seed_injection": "the seed injection rate may be off",
        "metabolic_exponent": "the metabolic exponent may be off",
        "switching_too_fast":
            "switching may be fast relative to demographic rates",
        "population_too_large": "the population may be too large for drift",
        "growth_rate_ratio": "the growth-rate ratio may be too unfavourable",
        "explore": "no diagnosis; sampling the parameter space",
    }

    def __init__(self, name: str = "AdaptiveAgent",
                 exploration_rate: float = 0.3):
        self.name = name
        #: ASF-13. Read by `_choose_diagnosis`. In the shipped agent this was
        #: stored and never used, and the branch it names was a literal 0.5.
        self.exploration_rate = exploration_rate
        self.reasoning_chain: List[ReasoningStep] = []
        self.step_counter = 0
        #: ASF-6. Diagnoses already acted on, so the agent does not spend four
        #: iterations on one knob the way the shipped fluctuating log does.
        self.tried: List[str] = []

    def _new_step_id(self) -> str:
        self.step_counter += 1
        return "%s_step_%d" % (self.name, self.step_counter)

    def analyze(self, outcomes, failed_claims, current_params, model_type):
        diagnoses = self._diagnose(outcomes, failed_claims, model_type)
        applied = self._choose_diagnosis(diagnoses)
        hypothesis = self._generate_hypothesis(diagnoses, applied)
        observation = self._generate_observation(outcomes, failed_claims,
                                                 model_type)
        new_params, action_desc = self._propose_action(
            current_params, applied, model_type)
        new_claims = self._generate_claims(outcomes, model_type)

        if applied is not None:
            self.tried.append(applied)

        step = ReasoningStep(
            step_id=self._new_step_id(),
            timestamp=time.time(),
            agent_name=self.name,
            observation=observation,
            hypothesis=hypothesis,
            action=action_desc,
            parameters_changed=self._param_diff(current_params, new_params),
            expected_outcome="Retest with modified parameters",
            diagnoses=diagnoses,
            diagnosis_applied=applied,
        )
        self.reasoning_chain.append(step)
        return new_params, new_claims, step

    def _diagnose(self, outcomes, failed_claims, model_type) -> List[str]:
        """Failed claims -> ordered diagnosis tags, no strings parsed."""
        tags: List[str] = []
        for claim in failed_claims:
            variant = None
            if claim.claim_id == "forest_power_law":
                r2 = (outcomes.get("size_distribution") or {}).get(
                    "r_squared", 0.0)
                variant = "poor_fit" if r2 < 0.8 else "slope"
            for tag in self.DIAGNOSES.get(
                    (model_type, claim.claim_id, variant), []):
                if tag not in tags:
                    tags.append(tag)
        return tags

    def _choose_diagnosis(self, diagnoses) -> Optional[str]:
        """Pick one tag to act on, or None to explore.

        ASF-6/ASF-13. Two policies live here and both are choices:

        * an untried diagnosis is preferred to a repeat. The shipped
          fluctuating log spends four iterations shrinking `switching_rate`
          with the outcome pinned at coexistence 1.000, so "try the other
          explanation before repeating this one" is a response to observed
          behaviour -- but it is still a policy, and a different one
          (escalate the same knob harder) is defensible.
        * with probability `exploration_rate` the agent explores anyway, even
          when it has a diagnosis. That is what the parameter's name means;
          the shipped code never read it.
        """
        if not diagnoses:
            return None
        if np.random.rand() < self.exploration_rate:
            return None
        for tag in diagnoses:
            if tag not in self.tried:
                return tag
        return diagnoses[0]

    def _generate_hypothesis(self, diagnoses, applied) -> str:
        if not diagnoses:
            return ("No failed claims to explain; %s"
                    % self.PROSE["explore"])
        parts = ["%s%s" % (self.PROSE.get(t, t),
                           " [acting on this]" if t == applied else "")
                 for t in diagnoses]
        if applied is None:
            parts.append("[exploring instead]")
        return "Candidate explanations: " + "; ".join(parts) + "."

    def _generate_observation(self, outcomes, failed_claims, model_type):
        parts = []
        if model_type == "forest":
            sd = outcomes.get("size_distribution")
            if sd:
                parts.append("Size distribution slope: %.3f (binned count; "
                             "density exponent %.3f)"
                             % (sd["slope"], sd["density_exponent"]))
                parts.append("R2 of power-law fit: %.3f" % sd["r_squared"])
            if "species_richness" in outcomes:
                parts.append("Species richness: %s"
                             % outcomes["species_richness"])
            if "num_trees" in outcomes:
                parts.append("Trees: %s" % outcomes["num_trees"])
        elif model_type == "fluctuating":
            fp = outcomes.get("fixation_probability")
            if fp:
                parts.append("Fixation prob (slow strain): %.4f"
                             % fp["slow_strain"])
            if "censored_fraction" in outcomes:
                parts.append("Replicates hitting the step cap: %.3f"
                             % outcomes["censored_fraction"])
            if outcomes.get("mean_fixation_time"):
                parts.append("Mean fixation time: %.2f"
                             % outcomes["mean_fixation_time"])
        if failed_claims:
            parts.append("Failed claims: %s"
                         % [c.claim_id for c in failed_claims])
        return " | ".join(parts) if parts else "No significant observations."

    def _propose_action(self, params, applied, model_type):
        new_params = copy.deepcopy(params)
        actions = []

        def note(fmt, *a):
            actions.append(fmt % a)

        if model_type == "forest":
            if applied == "competition_too_weak":
                new_params["competition_strength"] = min(
                    params.get("competition_strength", 1.0) * 1.5, 5.0)
                note("Increased competition_strength to %.3f",
                     new_params["competition_strength"])
            elif applied == "competition_too_strong":
                new_params["competition_strength"] = max(
                    params.get("competition_strength", 1.0) * 0.6, 0.0)
                note("Decreased competition_strength to %.3f",
                     new_params["competition_strength"])
            elif applied == "not_at_steady_state":
                new_params["num_steps"] = int(
                    params.get("num_steps", 1000) * 1.5)
                note("Increased num_steps to %d", new_params["num_steps"])
            elif applied == "seed_injection":
                new_params["seed_rate"] = params.get("seed_rate", 0.1) * 1.5
                note("Increased seed_rate to %.3f", new_params["seed_rate"])
            elif applied == "metabolic_exponent":
                new_params["metabolic_exponent"] = float(np.clip(
                    params.get("metabolic_exponent", 0.75)
                    + np.random.normal(0, 0.05), 0.5, 1.0))
                note("Adjusted metabolic_exponent to %.3f",
                     new_params["metabolic_exponent"])
            else:
                if np.random.rand() < 0.5:
                    new_params["metabolic_exponent"] = float(np.clip(
                        params.get("metabolic_exponent", 0.75)
                        + np.random.normal(0, 0.05), 0.5, 1.0))
                    note("Perturbed metabolic_exponent to %.3f",
                         new_params["metabolic_exponent"])
                else:
                    new_params["dispersal_range"] = int(max(
                        1, params.get("dispersal_range", 5)
                        + np.random.randint(-2, 3)))
                    note("Perturbed dispersal_range to %d",
                         new_params["dispersal_range"])
        elif model_type == "fluctuating":
            if applied == "switching_too_fast":
                new_params["switching_rate"] = \
                    params.get("switching_rate", 0.1) * 0.7
                note("Decreased switching_rate to %.4f",
                     new_params["switching_rate"])
            elif applied == "growth_rate_ratio":
                new_params["growth_rate_ratio"] = min(
                    0.99, params.get("growth_rate_ratio", 0.95) + 0.02)
                note("Increased growth_rate_ratio to %.3f",
                     new_params["growth_rate_ratio"])
            elif applied == "population_too_large":
                new_params["carrying_capacities"] = [
                    max(10, int(k * 0.8))
                    for k in params.get("carrying_capacities", [100])]
                note("Decreased carrying capacities to %s",
                     new_params["carrying_capacities"])
            elif applied == "not_at_steady_state":
                new_params["num_steps"] = int(
                    params.get("num_steps", 1000) * 3)
                note("Increased num_steps to %d", new_params["num_steps"])
            else:
                if np.random.rand() < 0.5:
                    new_params["switching_rate"] = \
                        params.get("switching_rate", 0.1) * 1.3
                    note("Perturbed switching_rate to %.4f",
                         new_params["switching_rate"])
                else:
                    new_params["num_replicates"] = \
                        params.get("num_replicates", 50) + 20
                    note("Increased num_replicates to %d",
                         new_params["num_replicates"])
        return new_params, ("; ".join(actions) if actions
                            else "No parameter changes.")

    def _generate_claims(self, outcomes, model_type):
        """ASF-15/ASF-16. Descriptions now state what the test does, and ids
        come from a counter rather than `int(time.time())`, which collided
        for two claims generated in the same second."""
        new_claims = []
        if model_type == "forest":
            sd = outcomes.get("size_distribution") or {}
            if sd.get("r_squared", 0) > 0.85:
                self.step_counter += 1
                new_claims.append(Claim(
                    claim_id="forest_slope_below_threshold_%d"
                             % self.step_counter,
                    description=(
                        "Binned-count slope of the size distribution is "
                        "below -1.5 (density exponent above 2.5) in a single "
                        "run. NOT a correlation with seed_rate -- nothing "
                        "here varies seed_rate; see ASF-15/ASF-A."),
                    model_type="forest",
                    test_function=lambda o: (
                        (o.get("size_distribution") or {}).get(
                            "slope", 0.0) < -1.5,
                        "Slope check",
                        {"slope": (o.get("size_distribution")
                                   or {}).get("slope")}),
                    priority=2))
        elif model_type == "fluctuating":
            fp = outcomes.get("fixation_probability") or {}
            if fp.get("slow_strain", 0) > 0.3:
                self.step_counter += 1
                new_claims.append(Claim(
                    claim_id="fluct_slow_persistence_%d" % self.step_counter,
                    description=("Slow-strain fixation probability exceeds "
                                 "0.2 at these parameters (single point, no "
                                 "sweep over switching_rate)"),
                    model_type="fluctuating",
                    test_function=lambda o: (
                        (o.get("fixation_probability") or {}).get(
                            "slow_strain", 0) > 0.2,
                        "Slow strain persistence check",
                        {"fp_slow": (o.get("fixation_probability")
                                     or {}).get("slow_strain")}),
                    priority=2))
        return new_claims

    @staticmethod
    def _param_diff(old, new):
        return {k: (old.get(k), new.get(k))
                for k in set(old) | set(new) if old.get(k) != new.get(k)}


# =============================================================================
# FOREST METABOLIC SCALING MODEL
# =============================================================================

def fit_log_binned_slope(sizes, min_size=1.0, n_bins=30, min_points=6):
    """Log-log fit of a log-binned size histogram.

    Lifted out of `ForestScalingSim.analyze` unchanged so it can be fed
    distributions with known answers -- which is what ASF-8 and ASF-9 are.

    ASF-9: `hist` is a COUNT per logarithmic bin and is not divided by the bin
    width, so for a density p(x) ~ x^-alpha the count in a bin of width
    proportional to x goes as x^(1-alpha) and the fitted slope estimates
    1 - alpha, not -alpha. Measured over 60 draws of 20000 samples: alpha 1.5
    -> -0.473, 2.0 -> -0.944, 2.5 -> -1.442, 3.0 -> -1.900. `density_exponent`
    is reported alongside; `slope` is left as it was so old logs stay
    comparable.

    ASF-8: `r_squared` here constrains the straightness of the log-log fit and
    nothing else -- not the sign of the slope, and not whether the tail is
    actually a power law. Over 200 draws of 1000 samples the R2 > 0.6 gate
    passes 100% of uniform[1, 1000] (at slope +0.919) and 100% of
    lognormal(0, 2), while rejecting exponential and gamma(2, 10) at 0%.
    """
    sizes = np.asarray(sizes, dtype=float)
    sizes = sizes[sizes > 0]
    if len(sizes) <= 100 or sizes.max() <= sizes.min():
        return None
    log_bins = np.logspace(np.log10(max(min_size, sizes.min())),
                           np.log10(sizes.max()), n_bins)
    hist, edges = np.histogram(sizes, bins=log_bins)
    centers = np.sqrt(edges[:-1] * edges[1:])
    mask = hist > 0
    if np.sum(mask) < min_points:
        return None
    log_c, log_h = np.log(centers[mask]), np.log(hist[mask])
    coeffs = np.polyfit(log_c, log_h, 1)
    slope = float(coeffs[0])
    pred = np.polyval(coeffs, log_c)
    ss_res = float(np.sum((log_h - pred) ** 2))
    ss_tot = float(np.sum((log_h - np.mean(log_h)) ** 2))
    return {
        "slope": slope,
        "r_squared": float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0,
        "n_bins_occupied": int(np.sum(mask)),
        # ASF-9. The conversion, so a reader is not left to guess which
        # exponent the number is.
        "slope_convention": "binned_count (counts not divided by bin width)",
        "density_exponent": 1.0 - slope,
        # ASF-8. Reported beside the answer rather than gated on.
        "slope_is_positive": slope > 0,
        "constrains": ["r_squared"],
    }


class ForestScalingSim:
    """Spatially explicit forest with metabolic scaling.

    Trees occupy cells on a 2D grid, growth follows metabolic scaling,
    competition is local shading, seeds disperse probabilistically.
    """

    def __init__(self, params):
        self.params = params
        self.grid_size = params.get("grid_size", 100)
        self.metabolic_exponent = params.get("metabolic_exponent", 0.75)
        self.competition_strength = params.get("competition_strength", 1.0)
        self.dispersal_range = params.get("dispersal_range", 5)
        #: ASF-12. Was hardwired to `dispersal_range // 2`, so perturbing
        #: dispersal silently changed the competition neighbourhood too, and
        #: dispersal_range 1 gave radius 0 -- competition exactly 0.000 with
        #: `competition_strength` still logged nonzero. The default preserves
        #: the old behaviour; naming it lets a caller separate the two.
        self.competition_radius = params.get("competition_radius",
                                             self.dispersal_range // 2)
        self.seed_rate = params.get("seed_rate", 0.1)
        self.mortality_base = params.get("mortality_base", 0.01)
        self.num_steps = params.get("num_steps", 1000)
        self.initial_density = params.get("initial_density", 0.1)
        self.min_size = params.get("min_size", 1.0)
        self.num_species = params.get("num_species", 3)
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.float64)
        self.species_grid = np.zeros((self.grid_size, self.grid_size),
                                     dtype=np.int32)
        self._initialize()

    def _initialize(self):
        n_trees = int(self.grid_size ** 2 * self.initial_density)
        indices = np.random.choice(self.grid_size ** 2, n_trees, replace=False)
        rows, cols = np.unravel_index(indices,
                                      (self.grid_size, self.grid_size))
        self.grid[rows, cols] = np.random.lognormal(2, 1, n_trees)
        self.species_grid[rows, cols] = np.random.randint(
            1, self.num_species + 1, n_trees)

    def _local_competition(self, i, j):
        r = self.competition_radius
        i0, i1 = max(0, i - r), min(self.grid_size, i + r + 1)
        j0, j1 = max(0, j - r), min(self.grid_size, j + r + 1)
        total = np.sum(self.grid[i0:i1, j0:j1]) - self.grid[i, j]
        return total * self.competition_strength

    def step(self):
        new_grid = self.grid.copy()
        new_species = self.species_grid.copy()
        for i in range(self.grid_size):
            for j in range(self.grid_size):
                if self.grid[i, j] > 0:
                    comp = self._local_competition(i, j)
                    growth = self.grid[i, j] ** self.metabolic_exponent * 0.1
                    growth = max(0, growth - comp * 0.001)
                    new_grid[i, j] += growth
                    stress = comp / (self.grid[i, j] + 1)
                    if np.random.rand() < self.mortality_base + stress * 0.001:
                        new_grid[i, j] = 0
                        new_species[i, j] = 0
        n_seeds = int(np.sum(self.grid > 0) * self.seed_rate)
        parents = np.argwhere(self.grid > 0)          # hoisted; was recomputed
        if len(parents):                              # once per seed
            for _ in range(n_seeds):
                pi, pj = parents[np.random.randint(len(parents))]
                di = np.random.randint(-self.dispersal_range,
                                       self.dispersal_range + 1)
                dj = np.random.randint(-self.dispersal_range,
                                       self.dispersal_range + 1)
                ni, nj = pi + di, pj + dj
                if 0 <= ni < self.grid_size and 0 <= nj < self.grid_size \
                        and new_grid[ni, nj] == 0:
                    light = 1.0 - min(
                        1.0, self._local_competition(ni, nj) * 0.0001)
                    if np.random.rand() < light:
                        new_grid[ni, nj] = self.min_size * (
                            1 + np.random.exponential(0.5))
                        new_species[ni, nj] = self.species_grid[pi, pj]
        self.grid = new_grid
        self.species_grid = new_species

    def run(self):
        for _ in range(self.num_steps):
            self.step()
        return self.analyze()

    def analyze(self):
        sizes = self.grid[self.grid > 0]
        outcomes = {
            "num_trees": int(len(sizes)),
            "mean_size": float(np.mean(sizes)) if len(sizes) else 0.0,
            "max_size": float(np.max(sizes)) if len(sizes) else 0.0,
            "species_richness": int(len(np.unique(
                self.species_grid[self.species_grid > 0]))),
            # ASF-14. An empty grid and competitive exclusion are different
            # events; the claim could not tell them apart because the outcome
            # dict did not say.
            "extinct": bool(len(sizes) == 0),
            "competition_radius": int(self.competition_radius),
            "competition_disabled": bool(self.competition_radius == 0),
        }
        fit = fit_log_binned_slope(sizes, self.min_size)
        if fit:
            outcomes["size_distribution"] = fit
        return outcomes


# =============================================================================
# FLUCTUATING POPULATION MODEL (MORAN PROCESS)
# =============================================================================

class FluctuatingPopSim:
    """Moran process under a multi-state switching environment.

    Population size tracks the carrying capacity of the current environment
    state; two strains compete; one individual dies and one reproduces per
    step.

    ASF-11. `switching_rate` enters as a continuous-time generator rate but
    is consumed as a per-step Bernoulli probability, so it saturates at 1.0.
    Rates 2.0, 5.0 and 50.0 produce byte-identical outcomes. Reported through
    `switch_prob` / `switch_prob_saturated` rather than reinterpreted, because
    fixing it means choosing a time discretisation and that is a modelling
    decision, not a bug fix.
    """

    def __init__(self, params):
        self.params = params
        self.num_states = params.get("num_states", 5)
        self.carrying_capacities = list(params.get(
            "carrying_capacities", [50, 100, 200, 300, 400]))
        self.switching_rate = params.get("switching_rate", 0.1)
        self.growth_rate_fast = params.get("growth_rate_fast", 1.0)
        self.growth_rate_ratio = params.get("growth_rate_ratio", 0.95)
        self.growth_rate_slow = self.growth_rate_fast * self.growth_rate_ratio
        self.initial_population = params.get("initial_population", 100)
        self.num_steps = params.get("num_steps", 100000)
        self.num_replicates = params.get("num_replicates", 100)
        while len(self.carrying_capacities) < self.num_states:
            self.carrying_capacities.append(
                int(self.carrying_capacities[-1] * 1.2))
        self.carrying_capacities = self.carrying_capacities[:self.num_states]

    def _make_transition_matrix(self):
        Q = np.zeros((self.num_states, self.num_states))
        for i in range(self.num_states):
            if i > 0:
                Q[i, i - 1] = self.switching_rate * 0.5
            if i < self.num_states - 1:
                Q[i, i + 1] = self.switching_rate * 0.5
            Q[i, i] = -np.sum(Q[i, :])
        return Q

    def switch_probability(self, state):
        """ASF-11. What the per-step Bernoulli actually uses."""
        Q = self._make_transition_matrix()
        return min(1.0, float(-Q[state, state]))

    def _run_replicate(self, seed):
        np.random.seed(seed)
        env_state = self.num_states // 2
        N = self.carrying_capacities[env_state]
        n_fast = N // 2
        n_slow = N - n_fast
        Q = self._make_transition_matrix()
        t = 0
        censored = True

        for _ in range(self.num_steps):
            env_rates = -Q[env_state, env_state]
            if env_rates > 0 and np.random.rand() < env_rates:
                probs = np.maximum(Q[env_state, :].copy(), 0)
                probs[env_state] = 0
                if np.sum(probs) > 0:
                    env_state = int(np.random.choice(
                        self.num_states, p=probs / np.sum(probs)))
                    N = self.carrying_capacities[env_state]
                    total = n_fast + n_slow
                    if total > N:
                        for _ in range(total - N):
                            if np.random.rand() < n_fast / max(1, total):
                                n_fast = max(0, n_fast - 1)
                            else:
                                n_slow = max(0, n_slow - 1)
                            total = n_fast + n_slow
                    elif total < N:
                        for _ in range(N - total):
                            if np.random.rand() < n_fast / max(1, total):
                                n_fast += 1
                            else:
                                n_slow += 1
                            total = n_fast + n_slow

            total = n_fast + n_slow
            if total == 0:
                break

            if np.random.rand() < n_fast / total:
                n_fast = max(0, n_fast - 1)
            else:
                n_slow = max(0, n_slow - 1)
            total_w = n_fast * self.growth_rate_fast \
                + n_slow * self.growth_rate_slow
            if total_w > 0:
                if np.random.rand() < (n_fast * self.growth_rate_fast) / total_w:
                    n_fast += 1
                else:
                    n_slow += 1
            t += 1
            if n_fast == 0 or n_slow == 0:
                censored = False
                break

        return {
            "n_fast_final": n_fast, "n_slow_final": n_slow,
            "fixation_time": t,
            "fast_fixes": n_fast > 0 and n_slow == 0,
            "slow_fixes": n_slow > 0 and n_fast == 0,
            # ASF-10. Both strains still present means the step budget ran
            # out, not that they coexist. The name is kept for compatibility
            # with the shipped logs; `censored` is the honest one.
            "coexistence": n_fast > 0 and n_slow > 0,
            "censored": censored and n_fast > 0 and n_slow > 0,
        }

    def run(self):
        results = [self._run_replicate(seed=rep + self.params.get(
            "base_seed", 42)) for rep in range(self.num_replicates)]
        total = len(results)
        fix_times = [r["fixation_time"] for r in results
                     if not r["coexistence"]]
        censored = sum(r["censored"] for r in results)
        return {
            "num_replicates": total,
            "fixation_probability": {
                "fast_strain": sum(r["fast_fixes"] for r in results) / total,
                "slow_strain": sum(r["slow_fixes"] for r in results) / total,
                "coexistence": sum(r["coexistence"] for r in results) / total,
            },
            # ASF-10. Averaged over the replicates that FIXED, which discards
            # exactly the slowest ones: at budget 500 this reads 366.4 where
            # the uncensored mean is 1072.4. Read it with censored_fraction
            # beside it or not at all.
            "mean_fixation_time": float(np.mean(fix_times)) if fix_times else 0.0,
            "std_fixation_time": float(np.std(fix_times)) if fix_times else 0.0,
            # ASF-10.
            "censored_fraction": censored / total,
            "step_budget": int(self.num_steps),
            # ASF-11.
            "switch_prob": self.switch_probability(self.num_states // 2),
            "switch_prob_saturated": bool(
                self.switch_probability(self.num_states // 2) >= 1.0),
        }


MODELS = {"forest": ForestScalingSim, "fluctuating": FluctuatingPopSim}


# =============================================================================
# SIMULATION RUNNER
# =============================================================================

def run_model(model_type, params, seed):
    """One seeded run. ASF-1/ASF-2: the single place entropy enters."""
    if model_type not in MODELS:
        raise ValueError("Unknown model type: %s" % model_type)
    np.random.seed(seed)
    return MODELS[model_type](copy.deepcopy(params)).run()


def content_run_id(code_sha, model_type, params, seed):
    """ASF-1. H(code, model, params, seed) -- not H(wall clock)."""
    payload = json.dumps(
        {"code": code_sha, "model": model_type, "seed": seed,
         "params": {k: v for k, v in sorted(params.items())}},
        sort_keys=True, default=_json_default)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


class SimulationRunner:
    def __init__(self, model_type, logger, agent):
        self.model_type = model_type
        self.logger = logger
        self.agent = agent
        self.claims = []

    def register_claim(self, claim):
        self.claims.append(claim)

    def code_sha(self):
        return code_fingerprint(MODELS[self.model_type], fit_log_binned_slope)

    def run_adaptive_loop(self, initial_params, max_iterations=5,
                          random_seed=42, verbose=True):
        current_params = copy.deepcopy(initial_params)
        #: ASF-2. Fixed across iterations on purpose: successive iterations
        #: differ by their parameters, not by their replicate draws, which is
        #: what makes them a paired comparison.
        current_params["base_seed"] = random_seed
        code_sha = self.code_sha()
        iteration_results = []

        for iteration in range(max_iterations):
            if verbose:
                print("\n" + "=" * 60)
                print("ITERATION %d/%d | Model: %s"
                      % (iteration + 1, max_iterations, self.model_type))
                print("=" * 60)

            #: ASF-2. The seed the record names is the seed the run uses.
            iter_seed = random_seed + iteration
            run_params = copy.deepcopy(current_params)
            run_id = content_run_id(code_sha, self.model_type, run_params,
                                    iter_seed)
            t0 = time.time()
            outcomes = run_model(self.model_type, run_params, iter_seed)
            duration = time.time() - t0

            claim_results = {}
            failed_claims = []
            for claim in sorted(self.claims, key=lambda c: -c.priority):
                if claim.model_type != self.model_type:
                    continue
                status, msg, details = claim.test(outcomes)
                claim_results[claim.claim_id] = {
                    "status": status, "message": msg, "details": details}
                # ASF-4.
                self.logger.log_claim_result(claim.claim_id, {
                    "run_id": run_id, "status": status, "message": msg,
                    "details": details})
                # ASF-5. Only a refutation drives the agent.
                if status == FAILED:
                    failed_claims.append(claim)
                if verbose:
                    print("  Claim [%s]: %s - %s"
                          % (claim.claim_id, status.upper(), msg))

            record = SimulationRecord(
                run_id=run_id, model_name=self.model_type,
                parameters=run_params, random_seed=iter_seed,
                timestamp=time.time(), duration_seconds=duration,
                outcomes=outcomes,
                claim_results={k: v["status"]
                               for k, v in claim_results.items()},
                reasoning_chain=[], code_sha256=code_sha,
                seeds={"loop_seed": random_seed, "iteration_seed": iter_seed,
                       "base_seed": run_params.get("base_seed")})

            if failed_claims and iteration < max_iterations - 1:
                new_params, new_claims, step = self.agent.analyze(
                    outcomes, failed_claims, current_params, self.model_type)
                record.reasoning_chain = [step]
                current_params = new_params
                for nc in new_claims:
                    self.register_claim(nc)
                    if verbose:
                        print("  New claim generated: %s" % nc.claim_id)
            else:
                if not failed_claims and verbose:
                    print("  No claim refuted. Stopping early.")
                record.reasoning_chain = [ReasoningStep(
                    step_id="final_%d" % iteration, timestamp=time.time(),
                    agent_name=self.agent.name,
                    observation="Final iteration or no claim refuted.",
                    hypothesis="N/A", action="Terminate loop",
                    parameters_changed={}, expected_outcome="N/A")]

            self.logger.log_run(record)
            iteration_results.append({
                "iteration": iteration, "run_id": run_id,
                # ASF-3. The parameters THIS iteration ran, not the ones the
                # agent has just proposed for the next one.
                "params": run_params,
                "next_params": copy.deepcopy(current_params),
                "outcomes": outcomes, "claim_results": claim_results,
                "failed_claims": [c.claim_id for c in failed_claims]})

            if not failed_claims:
                break

        return {"model_type": self.model_type,
                "total_iterations": len(iteration_results),
                "final_params": current_params,
                "code_sha256": code_sha,
                "iteration_results": iteration_results,
                "logger_summary": self.logger.summary()}


# =============================================================================
# REPLAY / VERIFY  (ASF-1)
# =============================================================================

def _diff(a, b, path=""):
    """Leaf-level differences between two outcome dicts."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += _diff(a.get(k, "<missing>"), b.get(k, "<missing>"),
                         "%s.%s" % (path, k) if path else str(k))
    elif isinstance(a, float) and isinstance(b, float):
        if not (abs(a - b) <= 1e-9 * max(1.0, abs(a), abs(b))):
            out.append((path, a, b))
    elif a != b:
        out.append((path, a, b))
    return out


def verify_log(path, module=None, only_fields=None, limit=None):
    """Re-run every record in a jsonl log and diff the outcomes.

    ASF-1. This is the subcommand that found the finding. `module` lets a
    caller point it at a different implementation -- which is how the shipped
    `evidence/` logs were shown not to come from the code shipped beside them.

    A `forest` record is NOT replayable from its own fields in the as-received
    framework (ASF-2), so a mismatch there says nothing about the code. Only
    `fluctuating` records carry a complete seed, and this reports which is
    which rather than scoring them together.

    Each entry carries `reproduces`, which is False when the replay raised as
    well as when it disagreed. The first version of this function returned
    `diffs` and `error` as separate fields and defaulted `module` to
    `__import__(__name__)` -- which returns the top-level package, not this
    submodule, so every default-argument replay raised AttributeError, filed
    it under `error`, and left `diffs` empty. A caller reading `diffs` alone
    saw a clean reproduction. That is ASF-5's shape in the verifier itself: a
    measurement that did not happen, reported as a measurement that agreed.
    """
    mod = module or sys.modules[__name__]
    results = []
    with open(path) as fh:
        for i, line in enumerate(fh):
            line = line.strip()
            if not line:
                continue
            if limit is not None and i >= limit:
                break
            rec = json.loads(line)
            model = rec["model_name"]
            params = dict(rec["parameters"])
            replayable = model == "fluctuating" and "base_seed" in params
            entry = {"run_id": rec.get("run_id"), "model": model,
                     "replayable": replayable, "diffs": [], "error": None,
                     "reproduces": None}
            if replayable:
                try:
                    cls = getattr(mod, "FluctuatingPopSim")
                    got = cls(copy.deepcopy(params)).run()
                    logged = rec["outcomes"]
                    fields = only_fields or sorted(set(logged) & set(got))
                    if not fields:
                        raise ValueError(
                            "no comparable outcome fields between the record "
                            "and this implementation")
                    entry["diffs"] = _diff({k: logged[k] for k in fields
                                            if k in logged},
                                           {k: got[k] for k in fields
                                            if k in got})
                except Exception as exc:              # noqa: BLE001
                    entry["error"] = "%s: %s" % (type(exc).__name__, exc)
                entry["reproduces"] = (entry["error"] is None
                                       and not entry["diffs"])
            results.append(entry)
    return results


# =============================================================================
# DEFAULT CLAIMS
# =============================================================================

def get_forest_claims():
    def power_law(o):
        # ASF-5. The shipped version formatted 'N/A' with :.3f and raised on
        # any collapsed forest, which was then logged as a refutation.
        sd = o.get("size_distribution")
        if o.get("extinct") or sd is None:
            return (INCONCLUSIVE,
                    "No size distribution (trees=%s); nothing to fit"
                    % o.get("num_trees"), {"num_trees": o.get("num_trees")})
        return (sd["r_squared"] > 0.6,
                "R2 = %.3f (slope %+.3f, density exponent %.3f)"
                % (sd["r_squared"], sd["slope"], sd["density_exponent"]), sd)

    def coexistence(o):
        # ASF-14. An empty grid is a failed experiment, not competitive
        # exclusion. The shipped test returned the same FAIL for both.
        if o.get("extinct"):
            return (INCONCLUSIVE, "Grid is empty; no species to coexist",
                    {"richness": 0, "num_trees": o.get("num_trees")})
        return (o.get("species_richness", 0) > 1,
                "Richness = %s" % o.get("species_richness"),
                {"richness": o.get("species_richness")})

    return [
        Claim(claim_id="forest_power_law",
              description=("The log-binned tree-size histogram is straight in "
                           "log-log at R2 > 0.6. Constrains straightness "
                           "only -- not the sign of the slope, not power-law "
                           "vs lognormal. See ASF-8."),
              model_type="forest", test_function=power_law),
        Claim(claim_id="forest_species_coexistence",
              description="More than one species persists (richness > 1)",
              model_type="forest", test_function=coexistence),
    ]


def get_fluctuating_claims():
    def fixation(o):
        fp = o["fixation_probability"]
        return (fp["coexistence"] < 0.5,
                "Coexistence prob = %.3f (%.0f%% of replicates hit the "
                "%d-step cap -- ASF-10)"
                % (fp["coexistence"], 100 * o.get("censored_fraction", 0.0),
                   o.get("step_budget", 0)), fp)

    def slow_persistence(o):
        fp = o["fixation_probability"]
        return (fp["slow_strain"] > 0.05,
                "Slow strain fixation = %.4f" % fp["slow_strain"], fp)

    return [
        Claim(claim_id="fluctuating_fixation",
              description=("Fixation occurs in >50% of replicates. NOTE: this "
                           "is a joint claim about the biology and the step "
                           "budget; sweeping num_steps alone flips it. "
                           "ASF-10."),
              model_type="fluctuating", test_function=fixation),
        Claim(claim_id="fluctuating_slow_persistence",
              description="Slow strain fixes in more than 5% of replicates",
              model_type="fluctuating", test_function=slow_persistence),
    ]


DEFAULT_PARAMS = {
    "forest": {
        "grid_size": 60, "metabolic_exponent": 0.75,
        "competition_strength": 0.8, "dispersal_range": 4, "seed_rate": 0.15,
        "mortality_base": 0.01, "num_steps": 500, "initial_density": 0.15,
        "num_species": 3, "min_size": 1.0,
    },
    "fluctuating": {
        "num_states": 5, "carrying_capacities": [50, 100, 200, 300, 400],
        "switching_rate": 0.1, "growth_rate_fast": 1.0,
        "growth_rate_ratio": 0.95, "initial_population": 100,
        "num_steps": 100000, "num_replicates": 50,
    },
}

CLAIM_SETS = {"forest": get_forest_claims,
              "fluctuating": get_fluctuating_claims}


# =============================================================================
# MAIN
# =============================================================================

def main(argv=None):
    ap = argparse.ArgumentParser(description="Adaptive Simulation Framework")
    ap.add_argument("--model", choices=sorted(MODELS))
    ap.add_argument("--iterations", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--exploration-rate", type=float, default=0.3)
    ap.add_argument("--log", type=str, default="provenance_log.jsonl")
    ap.add_argument("--verify", metavar="LOG",
                    help="re-run each record in LOG and diff the outcomes "
                         "(ASF-1)")
    args = ap.parse_args(argv)

    if args.verify:
        rows = verify_log(args.verify)
        print("Verifying %s against this implementation" % args.verify)
        bad = 0
        for r in rows:
            if not r["replayable"]:
                print("  %s [%s] NOT REPLAYABLE from its own fields (ASF-2)"
                      % (r["run_id"], r["model"]))
                continue
            if r["error"]:
                print("  %s [%s] ERROR %s"
                      % (r["run_id"], r["model"], r["error"]))
                bad += 1
            elif r["diffs"]:
                bad += 1
                print("  %s [%s] MISMATCH" % (r["run_id"], r["model"]))
                for path, logged, got in r["diffs"]:
                    print("      %-40s logged %r  recomputed %r"
                          % (path, logged, got))
            else:
                print("  %s [%s] reproduces" % (r["run_id"], r["model"]))
        print("\n%d of %d replayable records did not reproduce."
              % (bad, sum(1 for r in rows if r["replayable"])))
        return 1 if bad else 0

    if not args.model:
        ap.error("--model is required unless --verify is given")

    logger = ProvenanceLogger(log_file=args.log)
    agent = AdaptiveAgent(name="AutoAgent",
                          exploration_rate=args.exploration_rate)
    runner = SimulationRunner(args.model, logger, agent)
    for claim in CLAIM_SETS[args.model]():
        runner.register_claim(claim)

    result = runner.run_adaptive_loop(
        initial_params=copy.deepcopy(DEFAULT_PARAMS[args.model]),
        max_iterations=args.iterations, random_seed=args.seed)

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print("Model: %s" % result["model_type"])
    print("Total iterations: %d" % result["total_iterations"])
    print("Code sha256: %s" % result["code_sha256"][:16])
    print("Final parameters: %s" % json.dumps(result["final_params"],
                                              indent=2, default=_json_default))
    print("\nProvenance log saved to: %s" % args.log)
    print("Logger summary: %s" % result["logger_summary"])
    print("Replay with: python %s --verify %s" % (__file__, args.log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
