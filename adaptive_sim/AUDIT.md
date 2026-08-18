# ASF-1..16 — the adaptive simulation framework

What arrived: `adaptive_sim_framework.py` (723 lines), two provenance logs,
and a results plot. A framework for running simulations, testing falsifiable
claims against their outcomes, logging provenance, and letting an agent
modify the experiment based on what failed.

The framework's own thesis is that a run is reproducible from its record, so
the first thing done to it was to take that seriously — re-run the logged
records from their logged fields and compare.

Every number here was measured. The runnable report is
`falsifiers_adaptive_sim.py` (35 checks); the suite is
`tests/test_adaptive_sim.py` (63 cases). Both need numpy.

```bash
python adaptive_sim/falsifiers_adaptive_sim.py
python tests/test_adaptive_sim.py
python adaptive_sim/adaptive_sim_framework.py --verify \
    adaptive_sim/evidence/provenance_fluctuating.jsonl
```

---

## ASF-1 — the provenance log does not reproduce under the code shipped with it

A `fluctuating` outcome is a pure function of its logged parameters plus
`base_seed`: `_run_replicate` calls `np.random.seed(rep + base_seed)` and the
model reads no other entropy. So a record is replayable **in principle**, and
a mismatch is evidence about the code rather than about the seeding. All five
replayable records fail:

| record | field | logged | recomputed |
|---|---|---|---|
| `fc874f5f733b` | coexistence | 1.000 | 0.025 |
| `b2cbf41a3249` | coexistence | 1.000 | 0.050 |
| `1999232f8ea6` | coexistence | 1.000 | 0.175 |
| `de30bb5fed18` | coexistence | 1.000 | 0.325 |
| `db001b18502f` | `mean_fixation_time` | 0.0 | 1053.575 |

The last row is the decisive one. At its parameters the shipped code
reproduces `fixation_probability` **exactly** — 0.65 / 0.35 / 0.0, to the
digit — and disagrees only about the timing fields. This is not a log of
some other experiment: the dynamics are the same code, and one field is not.
Two independent signatures of the difference are visible in the log itself:
`mean_fixation_time` is `0.0` (a float, so `float(np.mean(fix_times))` ran on
a non-empty list of zeros) rather than the `0` integer the empty-list branch
writes, and the four `num_steps = 3000` runs record nothing fixing at all
where the shipped code fixes 97.5% of replicates.

Nothing in the record could have said so. `run_id` was
`sha256(model + iteration + time.time())` — a hash of the wall clock, which
identifies nothing — and there was no code identity in the record at all.

**Fixed** by making the record self-checking: `code_sha256` over the model
source, `run_id = H(code, model, params, seed)`, and a `--verify` subcommand
that re-runs each record and diffs the outcomes. That subcommand is what
found this finding.

A note on what was *not* concluded. The logged wall-clock durations (0.3 s
for the 3000-step runs, 1.6 s for the 50000-step one) invert under the
shipped code, which is suggestive — but runtimes are not comparable across
machines and that line of evidence was dropped rather than cited.

## ASF-2 — the field named `random_seed` was not the seed of the run

Records claim seeds 123, 124, 125, 126. `np.random.seed(random_seed)` appears
once in the file, at loop entry. The value `random_seed + iteration` was
written into the record and passed to nothing.

The forest model draws from the global stream, so iteration *k* > 0 was not
replayable at all — seeding a fresh run with the record's seed 43 gives a
different forest from the one iteration 1 ran (measured: 375 trees against
383). `fluctuating` *was* replayable, but through `base_seed`, the field not
named seed.

**Fixed.** Each iteration is seeded with the value its record names, and
`seeds` carries the loop seed, the iteration seed and the base seed
separately. `base_seed` stays fixed across iterations **on purpose** — it is
what makes successive iterations a paired comparison rather than a fresh draw
— and now says so instead of being an accident of one assignment.

## ASF-3 — outcomes paired with the next iteration's parameters

`iteration_results.append(...)` ran after `current_params = new_params`, so
the returned structure paired each iteration's outcomes with the parameters
the agent had just proposed for the *next* one:

```
results['params'] : [0.21, 0.147, 0.1029, 0.1029]
record.parameters : [0.3,  0.21,  0.147,  0.1029]
```

The jsonl was right. The in-memory result — what `main()` prints and what any
plot reads — was shifted by one. The last entry coincides because the final
iteration does not call the agent, which is how a shift like this survives a
glance at the tail of the output.

## ASF-4 — `log_claim_result` had no callers

Defined once, called never, so `summary()['claims_tested']` was `[]` on every
run ever made. Now called on every claim test.

## ASF-5 — a broken test was recorded as a refutation

`Claim.test` caught exceptions, set `status = "inconclusive"`, and returned
`False`. One line later the runner wrote
`{'status': 'passed' if passed else 'failed'}` — the distinction was created
and then discarded.

It was reachable on the shipped defaults: the forest power-law test formats
`o.get('size_distribution', {}).get('r_squared', 'N/A')` with `:.3f`, which
raises `ValueError` for any collapsed forest. So "the forest died" was logged
as "the power-law claim is refuted."

**Fixed.** `inconclusive` is a third status that travels into the record, and
an inconclusive claim does not drive the agent. A broken thermometer is not
evidence about the weather.

## ASF-6 — the agent could not turn the one knob its own diagnosis named

`_generate_hypothesis` emitted a single string:

> "Power-law fit poor; hypothesis: competition too weak or simulation **not
> at steady state**."

`_propose_action` then chose its branch by searching that string, testing
`"competition too weak"` first. The string contains both substrings, so the
`num_steps` branch could never fire.

The shipped fluctuating log is that failure in the wild. Four iterations
shrink `switching_rate` 0.3 → 0.21 → 0.147 → 0.103 with the outcome pinned at
coexistence 1.000 the whole way, and the run that finally worked did it by
raising `num_steps` 3000 → 50000 — by hand, out of band, by the person
running it.

**Fixed** by making the reasoning chain carry structured `diagnoses` tags
instead of prose to be grepped, so a branch can no longer be shadowed by
another branch's wording. Two policies were added and both are choices, not
derivations: an untried diagnosis is preferred to a repeat (the log's
four-iterations-on-one-knob is what motivated it), and `exploration_rate`
governs exploring anyway. The landed loop on the same failing configuration:

```
iter 0  num_steps  150  coexistence 1.000  applied not_at_steady_state
iter 1  num_steps  450  coexistence 0.850  applied population_too_large
iter 2  num_steps  450  coexistence 0.675  applied not_at_steady_state
iter 3  num_steps 1350  coexistence 0.075
```

## ASF-7 — the response to a dying forest was to kill it harder

ASF-5 and ASF-6 compound. Fed a near-extinct forest, the shipped agent's
proposal is `Increased competition_strength to 1.200`, and the reasoning
chain records it as a hypothesis under test.

## ASF-8 — `forest_power_law` constrains straightness, not power-law-ness

`R² > 0.6` on a log-log fit of a log-binned histogram. 200 draws of 1000
samples each, through the fitting code lifted out unchanged as
`fit_log_binned_slope`:

| distribution | R² mean | claim passes | mean slope |
|---|---|---|---|
| power law α = 2.0 | 0.930 | **100%** | −0.879 |
| power law α = 3.0 | 0.927 | **100%** | −1.748 |
| lognormal(0, 2) | 0.891 | **100%** | −0.674 |
| uniform[1, 1000] | 0.940 | **100%** | **+0.919** |
| lognormal(2, 1) | 0.375 | 0% | −0.503 |
| exponential | 0.165 | 0% | −0.305 |
| gamma(2, 10) | 0.154 | 0% | +0.393 |

The gate is not vacuous — it rejects exponential and gamma outright. It is
unconstrained in the one direction that names it: **a uniform size
distribution, which has more big trees than small, passes a power-law claim
at a positive slope.**

Not patched. Choosing a slope constraint is a claim about forests, and the
observed slopes are nowhere near any self-thinning prediction anyway (see
ASF-9). `slope_is_positive` and `constrains` now travel with the answer —
the same remedy as AISS's `weights_are_flat` and the non-local sensor's
`scale_is_inferred`.

## ASF-9 — the fitted slope is off by one from the density exponent

`np.histogram` returns counts per bin, and the bins are logarithmic, so bin
width grows in proportion to *x*. For a density p(x) ∝ x^−α the count in a
bin at *x* goes as x^(1−α), and the fit estimates **1 − α**, not −α. The
histogram is never divided by the bin width. Measured over 60 draws of
20 000 samples:

| true α | fitted slope | 1 − α |
|---|---|---|
| 1.5 | −0.473 | −0.5 |
| 2.0 | −0.944 | −1.0 |
| 2.5 | −1.442 | −1.5 |
| 3.0 | −1.900 | −2.0 |

So the logged slopes of −0.369 and −0.412 are density exponents of about
**1.37 and 1.41**, and a self-thinning −2 would appear here as −1. The
auto-generated claim's threshold of `slope < -1.5` is a density exponent of
2.5 — it is written in the other convention, which is how a threshold ends up
failing on arrival (ASF-15).

Not patched: the raw `slope` is left alone so existing logs stay comparable.
`density_exponent` and `slope_convention` are reported alongside.

## ASF-10 — the fixation claim is a claim about the step budget

Replicates that hit `num_steps` without fixing were labelled "coexistence".
That is right-censoring, not biology. Sweeping the step budget alone, with
every biological parameter held fixed, flips the verdict:

| num_steps | coexistence | verdict |
|---|---|---|
| 100 | 1.000 | FAIL |
| 300 | 0.975 | FAIL |
| 500 | 0.800 | FAIL |
| 1000 | 0.375 | **PASS** |
| 10 000 | 0.000 | PASS |
| 300 000 | 0.000 | PASS |

Every "coexisting" replicate is exactly a censored one — measured, the two
fractions are equal to floating-point precision.

The same censoring biases the *other* reported number, in the direction that
hides it. `mean_fixation_time` averages over the replicates that fixed, which
discards precisely the slowest ones:

| num_steps | censored | reported mean fixation time |
|---|---|---|
| 500 | 0.800 | 366.4 |
| 1000 | 0.375 | 627.2 |
| 2000 | 0.125 | 848.4 |
| 5000 | 0.000 | **1072.4** |
| 100 000 | 0.000 | 1072.4 |

At budget 500 the reported mean is low by **2.9×**, and it looks like a
converged number at every stop along the way — nothing in the output says the
sample was truncated. This is `P-CENSORED-INPUT` exactly: filtering before
analysis does not blind the estimate, it shifts it while keeping its
confidence.

`censored_fraction` and `step_budget` are now reported and the claim's
message names them. Neither the threshold nor the mean was changed — the
estimator for censored data is a survival fit, and choosing one is a
modelling decision.

## ASF-11 — a rate consumed as a probability, and it saturates

`switching_rate` builds a continuous-time generator `Q`, and then
`np.random.rand() < -Q[i,i]` uses the diagonal as a per-step Bernoulli
probability. Above 1.0 every step switches. Measured: rates 2.0, 5.0 and 50.0
give byte-identical outcomes.

The agent's exploration branch multiplies `switching_rate` by 1.3, so from
the shipped 0.3 it reaches saturation in seven steps and then keeps
"exploring" a knob that has stopped doing anything.

Not patched — fixing it means choosing a time discretisation, which is a
modelling decision. `switch_prob` and `switch_prob_saturated` are reported.

## ASF-12 — one parameter driving two mechanisms

The competition radius was `dispersal_range // 2`. Perturbing dispersal
silently resized the competition neighbourhood, and at `dispersal_range = 1`
the radius is 0, so local competition is **exactly 0.000** while
`competition_strength` is still logged at its nonzero value:

| dispersal_range | radius | competition at centre |
|---|---|---|
| 1 | 0 | **0.000** |
| 2 | 1 | 26.905 |
| 4 | 2 | 124.665 |
| 8 | 4 | 359.857 |

The agent reaches 1 through `max(1, dr + randint(-2, 3))`.
`competition_radius` is now an explicit parameter defaulting to the old
expression, so behaviour is unchanged and a caller can separate the two.
`competition_disabled` is reported.

## ASF-13 — an unread constructor parameter

`exploration_rate` was assigned in `__init__` and referenced nowhere else;
the branch it names was a literal `0.5`. Values 0.0 and 1.0 gave identical
behaviour. This is the `bands_per_octave` shape from GR-2 and the
`sub_glyphs` shape from GLY-3.

Wired to its plain meaning — the probability of exploring instead of acting
on a diagnosis. The semantics are chosen, not recovered.

## ASF-14 — extinction and competitive exclusion returned the same verdict

`richness > 1` fails identically for "one species won" and "the grid is
empty". Measured over 5 seeds at every setting the agent can reach:

| setting | richness | claim |
|---|---|---|
| shipped-like | 3, 3, 3, 3, 3 | passes 5/5 |
| competition at its 5.0 cap | 3, 3, 3, 3, 3 | passes 5/5 |
| dispersal at its floor of 1 | 3, 3, 3, 3, 3 | passes 5/5 |
| sparse start (density 0.01) | 3, 3, 3, 3, 3 | passes 5/5 |
| high mortality (0.2) | 0, 0, 0, 0, 0 | fails 5/5 |

The only configuration that fails the coexistence claim is the one where
there is no forest. The claim now returns **inconclusive** on an empty grid,
using ASF-5's channel — which separates the two without inventing a
coexistence threshold.

## ASF-15 — a generated claim whose description was not its test

Description: *"Power-law slope is negatively correlated with seed injection
rate."* Test: `slope < -1.5`, on a single run, with `seed_rate` never varied.
It is also written in the other slope convention (ASF-9), so at the observed
slopes of −0.369 and −0.412 it fails the moment it is created.

Description corrected to state what the test does. The correlation claim it
was named for is still tested by nothing — that is open problem ASF-A.

## ASF-16 — claim ids collided

`claim_id` embedded `int(time.time())`. Two claims generated in the same
second get the same id; measured, they do. Now a counter.

---

## One of my own, recorded rather than quietly fixed

`verify_log` defaulted `module` to `__import__(__name__)`, which returns the
**top-level package** and not the submodule, so every default-argument replay
raised `AttributeError`, filed it under `error`, and left `diffs` empty. A
caller reading `diffs` alone saw a clean reproduction — ASF-5's exact shape,
in the verifier written to catch ASF-5's shape.

It was not found by reading the code. It was found by
`test_verify_log_reports_a_mismatch_when_there_is_one`, which writes a record,
tampers with one field, and requires the verifier to notice. Entries now carry
`reproduces`, which is False when the replay raised as well as when it
disagreed, and two tests pin both directions.

---

## Open

**ASF-A — nothing here can test a claim about a *response*.** Every claim in
the framework is a threshold on a single run. "Slope is correlated with seed
rate" needs the runner to sweep a parameter and fit across runs, which is a
different loop shape from this one: this loop varies parameters to *chase* a
threshold, which is the shape that manufactures a fit rather than measuring
one. Until that exists, a generated claim of that form is prose.

**ASF-B — a degenerate run is not flagged as degenerate.** `mortality_base`
0.2 empties the grid and the only symptom is claims coming back inconclusive.
A floor on `num_trees` as a precondition for testing distributional claims
would be cheap.

**ASF-C — the null direction for the forest claims is unmeasured.** ASF-8
nulls the *fitting code* against known distributions, which is what makes the
R² gate's blindness visible. It does not null the *model*: what tree-size
distribution does this grid produce when the metabolic scaling is replaced by
a constant growth rate? If R² > 0.6 survives that substitution, the claim is
measuring the binning and not the biology. This is `repo_guard`'s null-harness
stage, and it has not been run here.

---

## What is reusable from this

The screen that produced ASF-1 is the general one, and it is cheap: **re-run
the log**. It needs no domain knowledge, it is mechanical, and it asks the
question a provenance format exists to answer. Anything in this archive that
writes a record claiming to describe a computation can be asked whether the
record and the computation still agree — and the answer here was no, for
every record, in a file whose entire purpose was provenance.

The second is **the diagnosis-to-action reachability check** (ASF-6): take
every diagnosis a system can emit, and confirm each one changes something.
`tests/test_adaptive_sim.py::test_every_diagnosis_tag_reaches_an_action` is
the mechanised form. That is `enumerate-reachable-outputs`, which
`graveyard.py todo` lists at reach 4 with nothing catching it automatically;
this is a fifth instance and a partial mechanisation for one shape of it.
