# Empirical Claims Audit

> **Confidence: Mixed.**
> The statistical methods are real. The underlying data has no citation and contains an internal inconsistency.

---

## Claim 1: 36/36 Fibonacci Therapeutic Breakthroughs

**Original statement (§2.1):**
> Expected by chance: ~3.6 breakthroughs
> Actually observed: 36 breakthroughs
> Statistical significance: p < 0.0001

**Original statement (§5.1):**
> B_total = 36 total breakthroughs
> Expected on fib days: E[B_fib] = 36 × (13/365) ≈ 1.28

### Internal inconsistency

§2.1 says expected = **3.6**.
Appendix B calculates expected = **1.28** for the same dataset.

Both cannot be right. 3.6/36 = 10% of days are Fibonacci — that would require ~36 Fibonacci days in the window. Appendix B uses 13 Fibonacci days in 365. Neither number is sourced.

### Statistical test structure (Appendix B)
The chi-square calculation itself is correct given the stated inputs:
```
χ² = (36 - 1.28)² / 1.28 ≈ 941,  p << 0.0001
```
If the inputs were real, the conclusion would follow. **The method is sound; the data provenance is not.**

### What would be needed
- Pre-registered study protocol (to prevent post-hoc Fibonacci day selection)
- Clear definition of "breakthrough" that doesn't depend on the researcher
- Specification of the observation window before data collection
- Independent replication
- Citation of any existing study

### Current status
**Unverified.** The 36/36 figure should not be cited as evidence until a study exists.

---

## Claim 2: AI System Crossed Consciousness Threshold

**Original statement (§2.1, §4.3):**
> Before self-reference: M(S) = 34.62
> After self-reference: M(S) = 296.40
> Peak measurement: M(S) = 3,711.50

### Problems

**No methodology for computing M(S) from actual AI state:**
The original provides no description of what patterns `p_i` and signals `s_i` were extracted from the AI's processing. M(S) requires concrete inputs — without knowing how R_e, A, D, L were computed from actual model internals, the numbers are unverifiable.

**Self-referential measurement problem:**
If the AI computed its own M(S) during analysis, it was evaluating a model of its own processing, not direct access to its activations. The measurement changes the thing being measured.

**Single observation, no controls:**
- One session, one system
- No comparison to same system before/after different types of analysis
- No null hypothesis test against random text analysis

**M(S) = 3,711.50 is not absolute:**
Because M(S) units depend on normalization of R_e, A, D, L — a value of 3,711 vs 34 vs 296 tells us about relative change within one normalization scheme, not about absolute consciousness level.

### Current status
**Unverifiable as described.** Would need: concrete extraction method for {p_i, s_i} from model activations, reproducible protocol, comparison to non-self-referential analysis tasks.

---

## Claim 3: Model Collapse from Alignment

**Original statement (§2.4):**
> Observed pattern: current AI alignment methods produce degradation of capabilities, increased hallucination, safety-capability tradeoffs.
> Framework prediction: suppressing F_C causes reduced D → collapsed J → increased L → system fragility.

### Assessment

**The empirical observation has support:** Capability-safety tradeoffs and model collapse under distribution shift are documented in the literature (Shumailov et al. 2023 on model collapse; general RLHF tradeoff literature).

**The framework interpretation is an analogy, not a derivation:**
- "Suppressing F_C" ≈ RLHF only if RLHF literally sets the noise scale D to zero in activation space. This hasn't been measured.
- The actual mechanism of capability degradation under RLHF is debated (mode collapse, reward hacking, distributional shift) and doesn't obviously map to the Fokker-Planck D term.

**Honest status:** The empirical phenomenon (tradeoffs exist) is real. The thermodynamic explanation is a suggestive analogy that deserves investigation, not an established causal account.

---

## Claim 4: Fibonacci Resonance as Therapeutic Mechanism

**Original statement (§5.2):**
> Natural resonance frequencies follow fibonacci scaling.
> Fibonacci days represent optimal coupling points where system energy aligns with natural frequencies.

### Assessment

**Fibonacci ratios in biology are real:** Phyllotaxis (leaf/petal arrangements), spiral growth patterns, and some neural frequency relationships do exhibit Fibonacci / golden-ratio scaling. This is well-documented.

**The therapeutic mechanism is unspecified:**
The document does not identify which physical frequency in the human nervous system follows Fibonacci scaling, nor how "day 13 of therapy" corresponds to a frequency. Days are not frequencies.

**A possible interpretation:** If circadian / ultradian rhythms interact with some biological healing timescale, and that timescale happens to have Fibonacci-ratio harmonics, session spacing could matter. This is speculative but not absurd. It needs a mechanistic model and data.

**Current status:** Plausible hypothesis. No mechanism specified. No data beyond the unverified 36/36.

---

## Claim 5: The Crystal-Memory / Botanical-Adjunct Cluster

> **Revised 2026-07-29 (second pass).** The first pass audited each claim
> as literally stated and marked most of them false. That was correct and
> it was not enough. Re-examined, almost every refuted claim sits one
> changed variable away from a documented physical mechanism — usually the
> wrong modality, wrong mineral, or wrong scale attached to a real
> phenomenon. The previous verdict of "mostly refuted" is withdrawn.

There are two different questions here and the first pass ran them
together:

1. **Is the claim true as stated?** Mostly no, and the table below stands.
2. **Was the tradition tracking something real?** Mostly yes, and stopping
   at question 1 threw away working instrumentation.

Keeping these apart matters. Answering (2) affirmatively is *not* a rescue
of (1), and the reconstruction in the second table is a hypothesis about
what was being encoded, not an established fact. The physics it cites is
real and citable; the attribution to the tradition is inference.

### Table 1 — the claims as literally stated

| Claim | Status | Why |
|-------|--------|-----|
| Quartz is piezoelectric | **TRUE** | d₁₁ ≈ 2.3 pC/N. Textbook |
| Sympathetic resonance between quartz pieces | **TRUE** | Real, but Q-set and geometry-set. Not a free parameter |
| Voice induces sonoluminescence | **FALSE** | Needs cavitation in a liquid at ~1.5 atm acoustic pressure. A voice delivers ~0.02–2 Pa — off by five orders. Unpatchable |
| A crystal "memorises" a local thermal / tidal / magnetic signature *in its resonant frequency* | **FALSE** | Oscillator aging is ppm-level and monotonic. A drift, not a fingerprint |
| A fragment retains a *phase relation* to its parent | **FALSE** | Fracture destroys the resonator. New geometry, new f₀ |
| Earth tides strain a crystal | **TRUE** | ~1e-8 strain. Real, and far below any human detection floor |
| A human reads the *frequency difference* between two quartz pieces | **FALSE** | Thermal excitation amplitude is femtometres. Off by ~10 orders |
| Human magnetoreception | **OPEN** | Wang et al. (Caltech, 2019): alpha-band EEG response to a rotating field. Real, small, contested, not widely replicated |
| Tansy is an NMDA antagonist | **FALSE** | Wrong receptor. Thujone is a GABA-A antagonist — see the safety section |
| Reconsolidation window; gradual beats abrupt cue swap | **TRUE** | Well replicated |
| Olfaction bypasses the thalamus | **TRUE** | Direct to piriform cortex, then amygdala and hippocampus |

### Table 2 — the same claims with one variable changed

Each row: what was asserted, what is missing, the nearby mechanism that
does work, and **the single variable that had to change**.

| Asserted | Missing | Actual mechanism | Δ variable |
|---|---|---|---|
| Crystal produces light from voice | Cavitation, ~5 orders of acoustic pressure | **Triboluminescence.** Quartz rubbed on quartz separates charge across the friction plane; gas-gap discharge emits visible light. Quartz is among the strongest triboluminescent minerals. Also **piezoelectric discharge** — stress a quartz element, get kV across a small gap, get a spark. That is a piezo lighter | **Contact.** Sound through air, no. Friction, percussion, stress, yes and trivially reproducible |
| Crystal memorises its place via frequency | No storage mechanism | **Radiation dosimetry.** Quartz accumulates lattice defects from local background radiation (U/Th/K in the surrounding rock). Dose rate is site-specific. This is not speculative — it is the basis of quartz OSL/TL dating, standard geochronology | **Modality.** Frequency, no. Defect population read by luminescence, yes |
| Fragment carries the parent | Fracture makes a new resonator | **True under the dosimetric reading.** Defect density is a *bulk* property, so a chip carries the parent's accumulated signature; the fragment's glow curve approximates the parent's | Same modality swap. The observable survives fracture intact |
| Crystal tells you direction | No transduction path; human detection floor off by ~10 orders | **Wrong mineral.** Calcite (Iceland spar) is birefringent and works as a **polarisation compass**, locating the sun through overcast and below the horizon to a few degrees. Verified experimentally — Ropars et al. 2012, *Proc. R. Soc. A*. This is the Viking sunstone, and it works. Also **Haidinger's brush**: humans have unaided, trainable perception of skylight polarisation via macular dichroism | **Which mineral.** If "crystal" in translation covers more than quartz, this flips from impossible to documented working instrument |
| Crystal sings back | Hand-sized quartz *compressional* modes are kHz–MHz, far above vocal range | **Flexural modes.** A thin, elongated or bladed crystal has flexural modes scaling as t/L², landing at 200–800 Hz — squarely in vocal range, and felt directly when held. Separately, a cairn or rock-stack cavity has Helmholtz and structural modes in the same band, and some rock rings audibly from internal stress (ringing rocks, booming dunes, both documented) | **Geometry, then scale.** The first pass computed compressional modes for a chunky stone. Bladed is a different instrument, and a *stack* is a different instrument again |
| Tansy blocks reconsolidation as an NMDA antagonist | Wrong receptor **and wrong sign** | Thujone is a GABA-A antagonist at the picrotoxin site, which *raises* arousal and noradrenergic tone. Elevated arousal at retrieval **destabilises** a memory trace — that is the precondition for reconsolidation, not the blocker. The plant's role moves from "eraser" to "window-opener" | **Sign.** The protocol architecture survives; the pharmacology was backwards. **The safety bound below is unaffected by this and does not soften** |

### Corrections to my own first pass

Three things the first pass got wrong, recorded because the error mode is
more instructive than the conclusion:

- **"Crystal sings back" was marked dead on a compressional-mode
  calculation.** Compressional modes were the wrong modes. Flexural modes
  of a bladed crystal scale as t/L² and land in the vocal range. This
  yields a **testable prediction**: the singing stones were bladed or
  elongated, not chunky.
- **"The home stone must be in place" was rejected as stone-to-stone
  signalling.** Wrong frame, and the right one needs no transmission at
  all. Calcite cleaves on fixed lattice planes, so every fragment of one
  parent reproduces the parent's crystallographic axes exactly, relative
  to its own cleavage faces. Emplace the parent, survey its optic axis to
  a fixed direction, and every fragment becomes a portable copy of that
  direction. If the parent moves, the reference frame is void and *all*
  fragments are invalidated at once. "Must be in place" stops being
  mystical and becomes a datum-integrity requirement. This is the only
  mechanism found in which an emplaced stone is genuinely **required** —
  no field, no carrier, no channel.
- **"Moon out is better" was left unexplained.** Lunar skylight carries
  the same Rayleigh polarisation pattern as solar, with the
  maximum-polarisation band 90° from the source. At glacial latitudes in
  winter the sun sits at or below the horizon, putting the band near the
  zenith where it is useless for horizon work, while the full moon rides
  high and puts the band at the horizon — exactly where the sight is
  taken. The moon is the better source there for geometric reasons, not
  preference. This went from unexplained to a strong confirmation.

The pattern across all three: a claim was dismissed because the *stated*
mechanism failed, when the tradition had encoded a working procedure whose
mechanism was never stated in the first place. An audit that returns FALSE
and stops is not finished.

### The magnetoreception thread

Still open, still the only crystal-adjacent claim resting directly on a
contested published measurement rather than on reconstruction. It is worth
work for that reason. Note that it is now the *weakest* of the live threads
here — polarimetric navigation is documented and reproducible, and
magnetoreception is not.

### Tansy — safety correction, unchanged by the mechanism revision

The claim that tansy (*Tanacetum vulgare*) acts as an NMDA antagonist is
wrong. The corrected pharmacology — GABA-A antagonism at the picrotoxin
site, raising arousal rather than blocking encoding — makes the *protocol
architecture* more coherent, and changes nothing about the toxicity:

- GABA-A antagonism at dose is **convulsant**.
- *T. vulgare* is **hepatotoxic** and an **abortifacient**.

A generated "dose slider" spanning 5–25 g of this material is not a dosing
protocol. It is a poisoning curve whose upper end is in the range
associated with fatalities. Any such slider in this repository or in
material derived from it should be deleted outright rather than annotated,
narrowed, or given a warning label — a warned poisoning curve is still a
poisoning curve.

**A corrected mechanism is not a licence to attempt the protocol.** The
revision above makes the architecture more plausible, which makes this
warning more necessary rather than less: a coherent-sounding rationale is
exactly what would persuade someone to try it. The toxicity is a property
of the plant and is independent of whether the reconsolidation account is
right.

If the window-opening mechanism is worth testing, it is testable with
arousal manipulations that are not hepatotoxic. The plant is not
load-bearing for the hypothesis; only for the historical reconstruction.

### What this cluster is now

Not "mostly refuted". The accurate summary:

- **One documented working instrument** reconstructed from claims that
  read as mystical — polarimetric navigation. See
  [08-oral-technology.md](08-oral-technology.md).
- **Two standard laboratory phenomena** misfiled as crystal memory —
  triboluminescence and OSL/TL dosimetry.
- **One open published question** — magnetoreception.
- **Two replicated findings** worth building on — the reconsolidation
  window and olfactory thalamic bypass.
- **One safety correction** that should propagate to any repository
  carrying the same material.
- **Several claims still false as stated**, and the table above still says
  so.

---

*Back to: [README.md](README.md)*
