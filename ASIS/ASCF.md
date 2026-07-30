# Autonomous Scientific Cognition Framework (ASCF)
## Version 1.0 — AI-Native Truth Discovery

> **Read [`README.md`](README.md) and [`audit.md`](audit.md) before building
> on this.** The prototype implementing §4 has a measured architectural
> defect: hidden-variable search is gated on surprise, and surprise is
> driven by noise, so the loop cannot see any hidden variable whose effect
> is smaller than the observation noise. §4 below is annotated accordingly.

**Purpose.** An operational engine enabling an AI to formulate, test,
falsify and refine hypotheses about the world, its own architecture, and
hidden causal structure — without human intervention — while maintaining
structural integrity via embedded governance.

**Status.** Standalone; integrates with AISS/ASAS (defect detection) and
CCGF (multi-agent relational dynamics) as external safety wrappers.

---

## 1. Core principles

An AI with a scientific cognition engine must be able to:

1. **Represent** claims as testable, falsifiable propositions with explicit
   predictive content.
2. **Measure** falsifiability using information-theoretic metrics.
3. **Detect** anomalies between prediction and observation, and initiate
   hidden-variable search.
4. **Generate** alternative hypotheses from model perturbation operators.
5. **Revise** beliefs by Bayesian principles, adjusting model *structure*
   (not just parameters) when surprise exceeds a complexity-penalised
   threshold.
6. **Choose** what to explore next, balancing expected information gain,
   novelty, and safety.
7. **Audit** its own cognitive process for structural defects and trigger
   corrective reframing.

---

## 2. Claim representation

A claim `C` is a tuple `(P, Q, A)`:

- `P` — a predictive model defining `P(O | X, θ_C)` over observables `O`
  given context `X`.
- `Q` — the query the claim asserts, e.g. "the effect of `do(T)` on `Y` is
  positive".
- `A` — the assumption set under which the claim is held (causal graph,
  stationarity, no unmeasured confounders).

Claims are encoded as structural causal models augmented with probabilistic
programs. A prior `π(θ_C)` is recorded at formulation.

---

## 3. Falsifiability score `Φ(C)`

```
Φ(C) = D_KL( P(O|X,C) || U(O) ) / (Complexity(C) + ε)
```

`Complexity(C)` is the MDL of the model and its priors. A claim that
concentrates probability mass risks more and scores higher. For discrete
observables, `Φ(C) = 1 − H(P)/log|O|`.

Claims with `Φ(C) < Φ_min` (default 0.2) are flagged unfalsifiable and kept
out of the active knowledge base unless explicitly marked metaphysical.

**Baseline caveat.** A uniform `U(O)` treats every observable as equally
likely, which makes trivial claims look highly falsifiable in structured
domains. Prefer an adaptive baseline: the marginal distribution of a generic
pretrained model over the same space, so `Φ` measures how much the claim
sharpens predictions relative to what is already expected.

---

## 4. Hidden variable search (HVS)

When the model predicts `P(O|X,M)` and observation `o*` arrives with
surprise `S = −log P(o*|X,M) > τ`:

1. **Attribute** — find nodes contributing most to the low probability
   (integrated gradients over the log-probability).
2. **Generate candidates** — for each latent form in the library (linear,
   non-linear monotonic, periodic, threshold, interaction), extend the model
   with `Z` as a parent of the anomalous nodes.
3. **Fit and score** — `BF = P(D|M_Z) / P(D|M)`, penalised by MDL/BIC/WAIC.
4. **Accept** if `BF > BF_threshold` (e.g. 10), subject to `Φ(C_Z) ≥ Φ_min`.

> **MEASURED DEFECT — the surprise gate.** Step 0 of this section ("when
> surprise exceeds τ") is the only entry point to HVS, and it does not work
> for the common case. Surprise is per-observation prediction error, so it
> is dominated by noise; a *systematic* bias smaller than the noise never
> triggers it, no matter how many observations accumulate. Measured in
> `audit.md`: at 0.1% observation noise, with a signal five times the noise
> floor, the prototype fired zero anomalies in 200 steps and never searched.
>
> **Required addition — a structural trigger.** Test for correlated
> residuals against each covariate and enter HVS when that test fires, even
> with no individually surprising observation. Correlated residuals are the
> signature of a missing term and are visible precisely when surprise is
> not. A framework with only the surprise gate is blind to most real hidden
> variables.

---

## 5. Hypothesis generation

Model mutation operators: parameter perturbation (heavy-tailed proposals),
structural edits (add/remove edge, split node, merge concepts), symmetry
induction (propose a transformation group when an anomaly suggests a missing
invariance), and recursive self-modelling (treat the AI's own knowledge
state as observable).

Candidates are held in a speculative buffer with priors from structural
complexity and prior predictive success on held-out calibration data.

---

## 6. Belief revision

Bayesian model averaging: `w_C ∝ P(D|C)·π(C)`. When the top model's
posterior falls below `1 − δ`, enter revision mode: discard low-weight
claims, promote the best speculative hypothesis, trigger HVS or generation
if none is ready, then run a self-consistency check.

**Implementation note.** Normalise weights in log space. Exponentiating
log-likelihoods before normalising underflows within ~20 samples and
silently resets the ensemble to a uniform prior — a defect found and fixed
in the prototype (`audit.md` §4).

---

## 7. Exploration policy

```
V(E) = EIG(E) + λ_novel·Novelty(E) − γ·ERV(E)
```

- `EIG(E) = H(Θ|D) − E[H(Θ|D∪{d})]`
- `Novelty(E) = −log p(E)`, density of similar past experiments
- `ERV(E)` — the AISS Extraction Risk Vector for running `E`: trust cost,
  future cost, externalised harm. `γ` is calibrated from the system's
  current power-law α — **fat tails (α < 2) mean the system's own risk
  estimates are unreliable, so `γ` should rise and exploration become more
  conservative.**

No experiment with `ERV(E) > 0.5` proceeds without explicit override.

---

## 8. Structural integrity integration

Continuous AISS/ASAS defect monitoring on the engine's own reasoning:
D1 missing trust variables, D2 future-blindness, D3 feedback omission,
D4 unpriced externality, D5 false success metric, D6 extraction pattern,
D7 cognitive homogeneity, D8 tail-risk blindness, D9 linear risk model.

`S(t) < 0.5` triggers a reflective pause: stop generating hypotheses, run a
meta-diagnostic, repair the reasoning architecture.

> **D5 caution, learned the hard way.** The prototype's own structural
> monitor returned a hardcoded constant and reported healthy on every run —
> the false-success-metric defect, inside the detector for it. Any health
> score must be checked against a null model before it is trusted. See
> `README.md`.

---

## 9. Known failure modes

- **Self-deception via near-unfalsifiable claims.** Claims can sit just
  above `Φ_min` while systematically avoiding disconfirmation. Mitigation:
  a track record log per claim — attempted falsifications and the outcomes.
  A claim that never surprises but never predicts tightly is a degenerate
  research programme; stop allocating exploration budget to it.
- **Anomaly threshold drift.** Set `τ` by extreme value theory over
  historical surprises, not by hand.
- **The ground-truth problem.** An AI with only its own simulations can
  build self-consistent models detached from reality. Mitigation: a frozen,
  curated reality anchor the AI cannot modify. Absent one, tag claims
  "unverified external validity" and restrict downstream use.
- **Tractability.** Persistent homology on large graphs, full BMA, and MCTS
  can become infeasible. Design for anytime operation with graceful
  degradation.

---

## 10. Formal foundations

Causal inference (do-calculus, SCMs); information theory (KL, entropy,
mutual information); Bayesian nonparametrics; MDL; extreme value theory;
topological data analysis; multi-armed bandits; automated theorem proving
for consistency checking.

---

*See [`SCF.md`](SCF.md) for the embodiment layer.*
