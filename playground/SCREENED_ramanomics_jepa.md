# Screening: Ramanomics × JEPA manifold, ten-architecture proposal

Incoming proposal, screened against this archive's existing checks before any
of it is built. Not a verdict on the ideas — a list of what the screens
already say, so the expensive parts are known first.

`python explore.py gaps` names the screens; `python graveyard.py screens`
ranks them by what they have already killed.

---

## 0. The proposal does not run on this codebase

The plan says "Leveraging Your Existing Code" and "the rest of the JEPA
manifold stays identical". Twelve named symbols, all absent from this tree:

```
EntryEncoder  binary_vec  stress_loss  prediction_loss  UnknownField
AttunementField  FrameRouter  StroboscopicScheduler  FalsificationistFrame
BayesianFrame  DiffusionFrame  LLMGatedFrame          — and "JEPA": 0 hits
```

`CLAIM_TABLE.json` exists but is not a hypothesis registry: it is a compact
table of physics rate and bound *expressions* (`dE/dt=V*I`,
`dF/dr=-2*k*q1*q2/r^3`) consumed by `CLAIM_SCHEMA.py`'s 41-byte binary codec.
Repointing it at biological hypotheses would overwrite a working encoder.

The hypothesis registry the proposal wants **does** exist — it is
`CLAIMS_REGISTER.json` plus `claims_index.py`, built in this session. That is
the right attachment point, and it already enforces the two rules the proposal
asks for informally: a claim recorded live must have something that can make it
fail, and a dead one must record what survives it.

Not a criticism of the design. A statement of integration cost: this is a new
build, not a retarget.

---

## 1. `instrument-floor` — the decisive one

**Screen:** compute the signal in the instrument's own units and divide by its
noise floor before designing anything around reading it.
Reach 2 (`FAB-1`, `R2-8`), mechanised as `repo_guard.reach`.

The design assumes a 1024-point spectrum on **every acquisition**, with a
scheduler running light frames per acquisition and heavy frames every 5 —
"perfect for live imaging where speed matters."

Photon budget, spontaneous Raman, single live cell, 785 nm at 10 mW (live-cell
tolerable), 1 µm² spot, NA 1.2 in water, optics+QE 25 %, shot-noise limited,
SNR 10 per channel:

| scatterers in 1 µm³ | σ (cm²) | detected | per channel | **s / spectrum** |
|---|---|---|---|---|
| 6e9 (dense C–H, upper bound) | 1e-29 (strong mode) | 1.7e4 ph/s | 16.5 ph/s | **6** |
| 6e9 | 1e-30 (typical) | 1.7e3 ph/s | 1.65 ph/s | **61** |
| 1.2e9 (protein+lipid, typical) | 1e-29 | 3.4e3 ph/s | 3.3 ph/s | **30** |
| 1.2e9 | 1e-30 | 3.4e2 ph/s | 0.33 ph/s | **303** |

**30–300 s per spectrum** in the realistic middle, which is where the published
single-cell Raman literature sits.

So the acquisition is the bottleneck by one to two orders, not the compute. A
`StroboscopicScheduler` that budgets model frames per acquisition is
optimising the wrong resource: at 30–300 s per point you have minutes of idle
GPU between samples.

This does not kill the idea. It **reshapes** it, and the reshaping is the
useful part:

- A "time-lapse Raman movie" is **tens to low hundreds of frames per hour**,
  not thousands. That is a small-*n* regime, and a JEPA predictor designed for
  it is a different animal from one designed for video.
- Coherent Raman (SRS/CARS) buys 1e4–1e5 and reaches video rate — but it is
  **narrowband**. It measures one or a few Raman shifts per acquisition, tuned
  by the pump–Stokes difference. Recovering 1024 points means sweeping, which
  gives the time back. Broadband CARS buys perhaps 1e2–1e3 against a worse
  nonresonant background.
- **The architecture must pick one**: full spectrum at minutes per point, or a
  handful of bands at video rate. The proposal assumes both at once.

---

## 2. `measure-the-null` — the claim predicate has no error rate

**Screen:** run the gate on data where the answer is known to be no, and count.
Reach 1 (`FCL-5`).

```json
{"predicate": "u[0] > 0.5 and u[1] < -0.2",
 "falsification_criteria": {"consecutive_failures": 3}}
```

Nothing states the false-positive rate of that predicate on unchanged cells.
`consecutive_failures: 3` is a stopping rule, not a calibration — with an
uncounted per-observation false-alarm rate *p*, three consecutive failures
happens at *p*³ under the null and nobody has measured *p*.

This is the exact shape of `FCL-5`, where `rate > 1.5 × base` fired on **34–41 %**
of null covariate sets while its own notes said only "too permissive".

**Cheapest fix:** technical replicates of one unperturbed cell, run the
predicate, count. One afternoon, and it sets every threshold downstream.

---

## 3. `null-harness` — the manifold's separation is not yet evidence

**Screen:** replace the structure you claim is doing the work with noise of the
same shape. Reach 2 (`NEG-7`, `VAC-1`), mechanised as `repo_guard.null_harness`.

"The manifold learns to distinguish cell states and predict transitions." The
null: train the identical architecture on **phase-randomised spectra**, or on
real spectra with shuffled state labels. If the latent still separates, the
separation is a property of the architecture and the batch structure, not of
the biochemistry.

`NEG-7` died exactly here — randomly-coefficiented lenses of the same
functional form reproduced the reported correlation floor.

---

## 4. `P-SELF-SUPPLIED-FALSIFIER` — the strongest unmechanised shape, and it fits

**Not mechanised.** The largest gap in `PRINCIPLES.json`.

The latent `u` is learned from the spectra. A claim written *in terms of* `u`
and tested *on* `u` has the model supplying the quantity that would falsify it.
The circularity is one indirection deep, which is why it survives review — that
is verbatim the principle's statement, and it has four prior instances here
including this playground's own passing candidate.

**What makes it not circular:** the claim predicate must be written against a
held-out split, *before* seeing it, and the latent must be frozen. Better
still, state the claim in **spectral** terms (a band, a ratio) rather than
latent terms, so it survives retraining. A claim phrased as `u[1] > 0.3` dies
the moment the encoder is retrained and the axes rotate — it is not a claim
about the cell, it is a claim about one fitting run.

---

## 5. `P-PREMATURE-SCALARIZATION` — 1024 → 2 → one coordinate

Three instances already (`FCL-9`, `GIES-1`, M(S)). The proposal maps a
1024-point spectrum to a **2D** latent, then states claims about single
coordinates of it.

`GIES-1` is the cautionary case: `T = outer(v,v)` looked like a faithful
representation and silently made half the state space degenerate, because the
projection discarded the sign. Nothing in the pipeline noticed.

**The check that would have caught it, and would catch this:** apply the
operation that is supposed to separate the states and confirm the
representation moves. Which is —

---

## 6. `test-the-distinguishing-operation` — reach 2, not mechanised

`GIES-2` and `KEA-7`: the same blindness in two formalisms that never met.

Here: add the toxin, and check `u` moves in a way that a *sham* addition does
not. Vehicle control, same handling, same laser exposure. If `u` moves for
both, the manifold learned the handling.

---

## 7. Batch effects are a systematic, not an uncertainty

The mapping table sends "spectral noise / batch effects" → `UnknownField`,
"epistemic uncertainty of the measurement".

Batch effect is a **bias**, not a variance. Modelling it as uncertainty widens
the error bars around a shifted centre — the estimate stays wrong and now looks
honest. Laser power drift, substrate autofluorescence and focus depth all
enter as systematic offsets that correlate with acquisition order, which is
also how the biology is ordered in a time-lapse.

This is the `compare-filtered-to-full` shape (`FCL-11`): the failure was not
losing sensitivity, it was **keeping** it and shifting the answer — a confident
wrong result rather than silence.

---

## 8. The ten-architecture table has no discriminating power

Every row states "Best For" and no row states *when it is the wrong choice*.
A table where every option is best at something cannot be used to choose, and
cannot be wrong. That is `P-UNFALSIFIABLE` at the level of the architecture
selection.

**What would make it decidable:** one column, *"fails when"*. Geometric
Diffusion Bridge fails when the state space is not smooth. Multi-Manifold Fleet
fails when the sensors are not conditionally independent given the state.
Neurosymbolic Reduction fails when the binary form has no compressible
structure. Those are checkable; "Best For" is not.

---

## What survives, and what to do first

The architecture is not the expensive part. The **acquisition rate** is, and it
is knowable now:

1. **Measure the photon budget on your actual rig.** One cell, one power, count
   photons per channel per second. It fixes the achievable frame rate and
   therefore *n*, and *n* decides which of the ten approaches are even
   admissible. Cheapest decisive measurement in the whole plan.
2. **Run the predicate on technical replicates** and count false alarms
   (§2). One afternoon.
3. **Vehicle control before toxin** (§6). Free — it is a tube you were going
   to pipette anyway.
4. Only then choose an architecture, and state each one's *fails when*.

The claim-table idea is the strongest part of the proposal and it is already
built here: `CLAIMS_REGISTER.json` + `claims_index.py status` enforce that
nothing is recorded live which nothing can falsify, and `playground/` scores a
candidate with `broken()` and `null()` gates. A Raman hypothesis registry
should attach there rather than to `CLAIM_TABLE.json`.
