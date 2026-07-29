# ASCF Prototype Audit

Measurements behind the claims in [`README.md`](README.md). Reproduce with
`python asc_core.py` and the script at the bottom of this file.

## 1. Effect size against the noise floor

`true_physics` adds Gaussian noise at 5% of the range. The hidden variable
shifts effective gravity by:

| Launch | Max height | Gravity shift | Noise |
|---|---|---|---|
| 45°, 10 m/s | 2.5 m | 0.078% | 5% |
| 60°, 20 m/s | 15.3 m | 0.468% | 5% |
| 75°, 20 m/s | 19.0 m | 0.582% | 5% |

The signal is 10–60× below the noise. This is knowable before running
anything, and it determines everything below.

## 2. Does the true model win?

30 steps, 20 seeds:

```
g_of_h accepted into the ensemble : 18/20
g_of_h ends as the best model     : 12/20
gradient estimate                 : +0.01655 +- 0.03104   (true -0.003)
```

200 steps, 10 seeds:

```
g_of_h ends as the best model     : 9/10
gradient estimate                 : +0.00028 +- 0.01741   (true -0.003)
```

**The gradient estimate is the wrong sign and consistent with zero.** More
data selects the right model *shape* more reliably while leaving the
parameter unrecovered — the extra degree of freedom is absorbing noise.

Selecting the correct model family is not the same as measuring the hidden
variable, and only the first of those is happening.

## 3. Structural health could not fail

Before: `alpha = 2.5  # placeholder`, returned and printed as a measured
power-law exponent. Every run reported healthy.

After: `alpha` returns `None` (no reasoning graph is built, so it cannot be
fitted), and `beta` is the mean coefficient of variation of ensemble
predictions across six test inputs. In the seed-42 run `beta` falls from
0.0025 to 0.0007 and flips to `healthy=False` as the ensemble converges —
the monitor now reports something.

## 4. Bayesian weights underflowed

`update_weights` computed `exp(log_lik)` before normalising. With
`sigma = 0.5 * std(y)` and a growing history, the log-likelihood reaches
about −750 within twenty samples, `exp` underflows to 0.0 for every model,
and the original code's `total > 0` guard then reset all weights to uniform
on every subsequent step. Normalising in log space fixes it.

This mattered: before the fix, ensemble weights carried no evidence at all
after the first ~20 steps.

## 5. Surprise detector null test (co_cradle_phase1.py)

The `mean + 2*sigma` rolling threshold, run on streams with no structure to
detect (pure numpy; needs no torch):

| Stream | Flag rate |
|---|---|
| White noise | 2.16% |
| Decaying loss (a model that is simply learning) | 1.70% |
| Heavy-tailed (Cauchy squared) | 3.12% |

The rule flags 2-3% of **anything**. Any surprise count from the Co-Cradle
loop must be compared against this baseline before it is called a detection;
a rate in the same range is the threshold reporting itself, not novelty in
the world. Reproduce with `null_test()` in `co_cradle_phase1.py`.

Note the second row in particular: a model that is merely converging
produces the same flag rate as one encountering genuine novelty.

---

## The architectural finding: discovery is gated on noise

This came out of running the fix recommended above, and it inverts the
recommendation.

Lowering the observation noise makes the true model selected **less** often,
not more:

| Noise | Anomalies / 200 steps | `g_of_h` accepted | Gradient estimate | Sign |
|---|---|---|---|---|
| 5.0% | 17.8 | 9/10 | +0.00028 ± 0.01741 | **wrong** |
| 1.0% | 2.8 | 8/10 | −0.00786 | right |
| 0.5% | 0.6 | 4/10 | never selected | — |
| 0.1% | 0.0 | 0/10 | never selected | — |

At 0.1% noise the gravity signal is roughly five times the noise floor and
trivially recoverable — and the loop never looks for it, because **HVS only
runs when the anomaly detector fires, and with clean data nothing is ever
surprising enough to fire it.**

So the architecture has a catch-22:

- **Surprise is driven by noise.** The anomaly detector triggers on
  prediction error, and at low noise a decent model produces little.
- **Discovery is gated on surprise.** `hvs_search` is only called inside
  `if anomaly:`.
- Therefore the loop **searches hardest exactly where the answer is least
  recoverable, and not at all where it is most recoverable.**

The 5%-noise run that looks like a success is the loop being triggered by
noise and then fitting noise. The 0.1%-noise run that looks like a failure is
the loop never being triggered at all, on data where the answer is sitting
in plain view.

### What this implies for ASCF

The framework's Section 4 makes surprise the entry condition for hidden
variable search. That is right for *anomaly-driven* discovery and wrong as
the only path, because a systematic bias too small to trigger a
per-observation surprise threshold is invisible to it forever — and
systematic-bias-below-the-noise is what most hidden variables in real
science look like.

A second trigger is needed, and it is a structural one rather than a
surprise one: **residual structure**. Even when no single observation is
surprising, correlated residuals against a covariate (here, launch angle)
say a term is missing. That test does not need an anomaly, it needs a
pattern — which is the same "keep the geometry, do not scalarise" point from
`Negentropic/triangnet.py`, arriving from a completely different direction.
Collapsing a residual *field* to a per-step scalar surprise threw away the
structure that would have found the answer.

This is registered but not yet numbered; it is a claim about the framework,
and the numbering is the author's to assign.

## 6. What would settle it

Set `noise = 0.005 * range_val` in `true_physics` and re-run §2. Predicted:
the gradient becomes recoverable and the sign comes out right. If it does
not, the problem is in the estimator rather than the SNR, which is the more
interesting outcome and worth knowing either way.

## Reproduction

```python
import numpy as np, asc_core as A
for steps in (30, 200):
    wins, grads = 0, []
    for s in range(20 if steps == 30 else 10):
        r = A.main(steps=steps, seed=s, verbose=False)
        if r["best"] == "g_of_h":
            wins += 1; grads.append(r["params"][1])
    print(steps, wins, np.mean(grads), np.std(grads))
```
