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

*Back to: [README.md](README.md)*
