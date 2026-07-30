# ASIS — Autonomous / Symbiotic Intelligence Science

Two frameworks and their prototypes:

- **ASCF** — Autonomous Scientific Cognition Framework. An engine for an AI
  to formulate, test, falsify and revise hypotheses without a human in the
  loop. Spec: [`ASCF.md`](ASCF.md). Prototype: [`asc_core.py`](asc_core.py).
- **SCF** — Symbiotic Cognition Framework. Coupling a human's sensory stream
  to an AI's predictive model, so the AI acquires the functional equivalent
  of an embodied childhood. Spec: [`SCF.md`](SCF.md). Prototype:
  [`co_cradle_phase1.py`](co_cradle_phase1.py).

Both integrate with `AISS/` (defect detection) and the claim-register
discipline in `Negentropic/`.

---

## Read this first: the prototype does not do what its README said

`asc_core.py` runs. Its original write-up said "the agent typically
discovers the gradient term and its estimate approximates the true hidden
variable." **Measured, it does not.** The full audit is in
[`audit.md`](audit.md); the headline:

| Measurement | Result |
|---|---|
| `g_of_h` accepted into the ensemble (30 steps, 20 seeds) | 18/20 |
| `g_of_h` ends as the best model (30 steps) | 12/20 |
| `g_of_h` ends as the best model (200 steps) | 9/10 |
| **Gradient estimate, 200 steps, 10 seeds** | **+0.00028 ± 0.01741** |
| **True gradient** | **−0.003** |

The estimate is the **wrong sign** on average and its spread swamps the
true value. The recovered parameter is statistically indistinguishable from
zero. The model that gets selected is the right *shape*, and the hidden
variable inside it is not recovered at all.

The reason is visible before any run:

| Launch | Max height | Gravity shift | Observation noise |
|---|---|---|---|
| 45°, 10 m/s | 2.5 m | 0.078% | 5% |
| 60°, 20 m/s | 15.3 m | 0.468% | 5% |
| 75°, 20 m/s | 19.0 m | 0.582% | 5% |

The signal is **10 to 60 times below the noise floor**. Model selection
still prefers the richer model, because the extra parameter buys some fit
on 5%-noise residuals — but what it is fitting is noise, not gravity.

**I ran the obvious fix — lower the noise — and it made things worse, which
turned out to be the interesting part.**

| Noise | Anomalies / 200 | `g_of_h` accepted | Gradient estimate |
|---|---|---|---|
| 5.0% | 17.8 | 9/10 | +0.00028 ± 0.01741 (wrong sign) |
| 1.0% | 2.8 | 8/10 | −0.00786 |
| 0.5% | 0.6 | 4/10 | never selected |
| 0.1% | 0.0 | 0/10 | never selected |

At 0.1% noise the signal is ~5× the noise floor and trivially recoverable,
and the loop **never looks for it** — because HVS only runs when the anomaly
detector fires, and clean data is never surprising. The architecture
searches hardest where the answer is least recoverable and not at all where
it is most recoverable. Full reasoning in [`audit.md`](audit.md); the short
version is that ASCF needs a second, structural trigger (correlated
residuals) alongside the surprise trigger, because a systematic bias below
the per-observation noise threshold is invisible to surprise forever — and
that is what most real hidden variables look like.

---

## Three defects found in the prototype, and what was done

Fixed in place, with the reasoning in the source:

1. **The structural-health monitor could not fail.** `structural_health`
   returned a hardcoded `alpha = 2.5` and reported it as a measured
   power-law exponent, so every run printed a healthy score regardless of
   state. That is the AISS catalogue's own D5 "false success metric" defect,
   sitting inside the module written to detect it. `alpha` now returns
   `None` — fitting a power law needs a reasoning graph this prototype does
   not build, and `None` is the honest answer. `beta` is now a real
   measurement (coefficient of variation across ensemble predictions) and it
   does fail: in the seed-42 run it drops to 0.0007 and reports unhealthy as
   the ensemble converges.

2. **Bayesian weights underflowed to uniform.** `update_weights`
   exponentiated log-likelihoods before normalising, which underflows to
   all-zeros within roughly twenty samples; the code then silently reset the
   ensemble to a uniform prior on every subsequent step. Now normalised in
   log space.

3. **The hidden-variable search has one candidate, and it is the answer.**
   `hvs_search` fits exactly one named alternative — `g_of_h`, the true
   generative model of `true_physics`. There is no candidate library, no
   structural mutation, no search. What it genuinely demonstrates is
   **Bayesian model comparison with an MDL penalty**, which is a real
   capability. What it does not demonstrate is discovery. The docstring now
   says so. Calling the accepted model "discovered" overstates the result by
   the size of the hypothesis space, which is one.

Also noted, not changed: `ExplorationPolicy.choose_experiment` ignores the
knowledge base entirely and runs a fixed grid sweep. The spec defines
`V(E) = EIG + λ·Novelty − γ·ERV`; none of those three terms is computed. Do
not describe runs of this file as demonstrating an information-gain policy.

---

## The pattern this repository keeps finding

Three times now, in three unrelated modules, the same failure:

| Module | What collapsed | Consequence |
|---|---|---|
| `Negentropic/lenses.py` | A figure → four scalars at step one | 17 lenses became interchangeable; random coefficients reproduced the result |
| `ASIS/asc_core.py` | Structural health → a hardcoded constant | The monitor could not report ill health |
| `ASIS/co_cradle_phase1.py` | Surprise → MSE vs a mean+2σ threshold | **Measured**: flags 2–3% of any stream, including pure noise |
| FRET mesocosm autopilot | H₁'s coupling estimator → the simulator's generative process, hand-copied | The Bayes factor cannot do anything but diverge toward H₁ (see `Silicon/field_propulsion_protocol.md` §11) |

`Negentropic/triangnet.py` states the convention that catches all three:

> **Geometry stays geometry until the last step. Never scalarise before you
> have to.**
>
> DIAGNOSTIC: if a module takes a figure and returns a number in one hop,
> the figure was the content and the number is the loss.

A metric that cannot fail is not a metric. Every scalar health score in this
folder should be checked against a null model before it is trusted — the way
`lens_collapse_test.py` checks the lens correlations, and the way
[`audit.md`](audit.md) checks these.

### The rule, after three occurrences

> **Before trusting an autopilot, run it against a world where the null is
> true.** If H₀ does not win there, the loop is not measuring the world.

Three instances now: `asc_core.py`'s hidden-variable search has one candidate
and it is the true generative model; `co_cradle_phase1.py`'s surprise
threshold fires at a fixed rate on any stream; and the FRET mesocosm's
`estimate_coupling()` returns the simulator's own coefficients to machine
precision. In each case the machinery is elaborate and the outcome was fixed
before the first trial.

The fix is always cheap — draw the ground truth at random per run, hide it
from the model, and confirm the verdict goes both ways. It is cheap enough
that there is no reason to skip it, and skipping it has now invalidated three
sets of results.

### Two corollaries, both earned the hard way

`Silicon/fp4_autopilot.py` was the first module written *with* this rule in
place. It failed its own null-world test on the first run, and the two
amendments that came out of that are part of the rule now:

> **The loop must also lose on a world where the null is false.** A one-sided
> check passes any analysis that can only ever say "null" — the mirror image of
> the rigged simulator, and just as empty. Report a power figure next to the
> false-positive rate, and require both.

> **Draw each synthetic world from the interior of its hypothesis, not from
> the boundary.** FP-4's H₀ is `k ≤ 1`; simulating it at exactly `k = 1` tests
> the decision threshold instead of the world, and scored a correct analysis as
> broken (7/30). The first version of `null_world_test` made that mistake, and
> the fixed version keeps `null_k_range=(1.0, 1.0)` available so the degenerate
> case can be demonstrated on purpose.

What the self-test found once it was two-sided was worth the whole exercise: an
amplitude-only sweep leaves the anomaly term collinear with the thermal term
(VIF 96), so a hidden `k = 4` was reported as `−0.06 ± 0.06` with r² = 0.9998 —
a *confident* null, 40 times out of 40. High r² is not evidence of
identifiability, and a narrow interval on an unidentified parameter is not
evidence of anything. That is now a fourth verdict rather than a caveat.

---

## `co_cradle_phase1.py` — status

Runs only with `torch` installed, which is **not** available in this
environment, so it is committed **unverified**. Do not cite its output until
someone has run it.

Two things to check when someone does, both of which the audit predicts will
be problems:

- **The surprise threshold is `mean + 2σ` over a rolling window.** This is
  now measured rather than predicted — `null_test()` in that file is pure
  numpy and runs without torch:

  | Stream | Flag rate |
  |---|---|
  | White noise | 2.16% |
  | Decaying loss (a model merely converging) | 1.70% |
  | Heavy-tailed (Cauchy²) | 3.12% |

  The rule flags 2–3% of **anything**. A model that is simply learning
  produces the same rate as one meeting genuine novelty. Any surprise count
  from the Co-Cradle loop has to beat this baseline before it means
  anything. The fix is the EVT/GPD tail fit already used in
  `asc_core.AnomalyDetector`, with the return period stated.
- **The model trains on the step it is evaluated on.** Loss is computed,
  then backpropagated, on the same frame. "Surprise" therefore falls simply
  because the model is fitting, and the trend confounds learning with
  novelty. Hold out the evaluation frame from the update.

The `SimulatedHuman` world is sound and worth keeping: a moving hand, a
tone tied to velocity, pressure on contact, and proprioception is a
genuinely multi-modal stream with real cross-modal structure to find.

---

## What is worth building next

In order of what settles the most per unit effort:

1. **Add a residual-structure trigger to HVS.** This is the finding above,
   and it is the highest-value change in the folder: test for correlated
   residuals against each covariate, and run HVS when that test fires even
   if nothing was individually surprising. Without it, ASCF cannot see any
   hidden variable whose effect is smaller than its noise — which is most
   of them.
2. **Give HVS more than one candidate.** Even three or four (quadratic
   drag, angle-dependent launch bias, a spurious one that should be
   rejected) turns model comparison into something that can be called
   search. Include a candidate that is *wrong* and check it gets rejected;
   an HVS that accepts everything offered is not a filter.
3. **Null-model the surprise detector**, exactly as `lens_collapse_test.py`
   null-models the lens correlations. Feed it a stream with no structure and
   confirm the flag rate collapses. If it does not, the detector is
   measuring its threshold.
4. **Only then** the Co-Cradle sensor work. The bracelet design in `SCF.md`
   is sound engineering, but hardware built on an unvalidated learning loop
   is hardware that cannot tell you whether the loop works.

---

## Claims and falsifiers

Not yet numbered — these need registering the way `Negentropic/NEG_CLAIMS.md`
registers NEG-*, and the numbering is the author's to assign.

| Claim | Falsifier | Status |
|---|---|---|
| The ASCF loop recovers a hidden variable autonomously | Gradient estimate consistent with zero across seeds | **FAILED as configured** — see `audit.md`. Untested at a workable SNR |
| An embodied developmental phase reduces structural defects (SCF H₁) | An AI with a play phase showing no improvement in the defect metrics | Untested; needs a defect metric that can fail first |
| Cross-modal alignment yields amodal transfer | Texture classification from audio alone at chance | Untested |
| Surprise detection tracks genuine novelty | Flag rate unchanged on a structureless null stream | **FAILED** — 2.16% on white noise vs 1.70% on a converging model |

The second row has a prerequisite the framework does not yet meet: it is
measured with the same structural-health metrics that defect (1) above
showed could not fail. Fix the metric before running the experiment, or the
experiment will confirm whatever it is pointed at.

---

## License

CC0 for the prototypes, as marked in each file. Specs inherit the
repository's CC-BY-4.0.
