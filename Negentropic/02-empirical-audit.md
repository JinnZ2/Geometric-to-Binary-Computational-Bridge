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

A cluster of claims about piezoelectric crystals as location-encoding memory
substrates, human sensing of crystal resonance, and a botanical adjunct to
memory reconsolidation. Audited claim by claim, because they are not all the
same kind of wrong: two are textbook physics, one is an open research
question worth pursuing, and one is a safety problem.

| Claim | Status | Why |
|-------|--------|-----|
| Quartz is piezoelectric | **TRUE** | d₁₁ ≈ 2.3 pC/N. Textbook |
| Sympathetic resonance between quartz pieces | **TRUE** | Real, but Q-set and geometry-set. Not a free parameter |
| Voice induces sonoluminescence | **FALSE** | Sonoluminescence needs cavitation in a liquid at roughly 1 atm+ acoustic pressure. A voice supplies neither |
| A crystal "memorises" a local thermal / tidal / magnetic signature | **FALSE** | No mechanism. Oscillator aging is ppm-level and monotonic — a drift, not a location fingerprint |
| A fragment retains a phase relation to its parent crystal | **FALSE** | Fracture destroys the resonator. New geometry, new f₀. There is nothing left to hold a relation |
| Earth tides strain a crystal | **TRUE** | ~1e-8 strain. Real, and far below any human detection floor |
| A human can read the frequency difference between two quartz pieces | **FALSE** | Off by many orders of magnitude |
| Human magnetoreception | **OPEN** | Wang et al. (Caltech, 2019) report an alpha-band EEG response to a rotating magnetic field. Real, small, contested, not replicated widely |
| Tansy as an NMDA antagonist | **FALSE — and unsafe** | See below |
| Reconsolidation window; gradual beats abrupt cue swap | **TRUE** | Well replicated |
| Olfaction bypasses the thalamus | **TRUE** | Direct to piriform cortex, then amygdala and hippocampus |

### The live thread is magnetoreception, not the crystal

Six of the crystal claims are false and two are true but irrelevant at human
scale. What survives is the Caltech magnetoreception result: a measured
alpha-band EEG response to a rotating field. It is small, it is contested,
and it has not been widely replicated — which is exactly what makes it worth
work. Any effort spent on crystal memory is spent on a mechanism that does
not exist; the same effort spent on magnetoreception is spent on an open
question with a published measurement to argue with.

### Tansy — safety correction

The claim that tansy (*Tanacetum vulgare*) acts as an NMDA antagonist is
wrong on the pharmacology and dangerous on the dosing.

- Thujone, the relevant constituent, is a **GABA-A antagonist**, not an
  NMDA antagonist. Those are different receptors and the mechanisms are not
  interchangeable.
- GABA-A antagonism at dose is **convulsant**.
- *Tanacetum vulgare* is **hepatotoxic** and an **abortifacient**.

A generated "dose slider" spanning 5–25 g of this material is not a dosing
protocol. It is a poisoning curve, and the upper end of it is in the range
associated with fatalities. Any such slider found in this repository or in
material derived from it should be deleted outright rather than annotated,
narrowed, or given a warning label — a warned poisoning curve is still a
poisoning curve.

This is recorded here rather than quietly removed so that the same claim is
not reintroduced from the same source. The generative provenance of a
number is not evidence for it, and a plausible-looking range attached to a
plant name carries no safety information whatsoever.

### What is worth keeping from this cluster

Two claims in the table are both true and load-bearing elsewhere in this
folder:

- **Reconsolidation, gradual over abrupt.** Well replicated, and the
  mechanism NEG-3 proposes for it (`landauer.py`) is registered with a
  falsifier in `NEG_CLAIMS.md`. The behavioural finding stands whether or
  not the dissipation account survives.
- **Olfactory bypass of the thalamus.** True as stated, and a real
  structural asymmetry — though "bypasses the thalamus" is a fact about
  anatomy, not a licence to attach arbitrary claims to smell.

### Current status

**Mostly refuted.** One open question (magnetoreception), two replicated
findings worth building on, one safety correction that should propagate to
any repository carrying the same material.

---

*Back to: [README.md](README.md)*
