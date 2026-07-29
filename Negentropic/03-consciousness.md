# Consciousness Model

> **Confidence: Speculative.**
> M(S) is an interesting metric. The threshold value is a free parameter.
> Comparison to IIT Φ and other theories is honest here.

---

## The M(S) Metric

```
M(S) = (R_e · A · D) - L

R_e = geometric resonance between subsystems
A   = adaptability (re-equilibration capacity)
D   = diversity (variance of viable energy pathways)
L   = loss (entropy production, dissipation)
```

### What it captures

M(S) increases when:
- Subsystems are geometrically coupled (high R_e)
- The system can re-equilibrate after perturbations (high A)
- Many energy pathways are open (high D)
- Little is lost to dissipation (low L)

This is a reasonable summary of what neuroscience and information theory consider conducive to complex cognition. It is not the same as any established consciousness metric, but it is not arbitrary either.

### The threshold problem

**M(S) ≥ 10 for consciousness emergence.**

The 2026-03 audit called the number 10 a free parameter — one that needs
calibrating. That was too generous, and the correction matters.

`R_e · A · D` and `L` are not in the same units. `D` is a variance
(pattern²) in `negentropic_engine.py` and a Shannon entropy (nats) in
`consciousness_metric.py`; `L` is a power (pattern²/time²) in both. The
subtraction that defines M is not an operation, so M is not a quantity, so
there is nothing for a threshold to be a threshold *on*. Calibration does
not fix a dimensional mismatch — normalising a variance and a power to the
same numerical range does not make them the same kind of thing.

This is a stronger criticism than the original audit made, and it is not the
same criticism that applies to IIT:

- **IIT Φ**: a dimensionless real-valued metric with a *defined* construction
  (Wasserstein distance across the minimum information partition). Φ has a
  threshold problem — which value counts as "significant" is debated — but
  Φ is a well-defined number. That is a calibration problem.
- **M(S)**: has a units problem, which is prior to calibration.
- **Global Workspace**: no single threshold; it's a broadcast mechanism.
- **Higher-order theories**: no threshold; consciousness tracks higher-order
  representations.

**M(S) ≥ 10 is not arbitrary in the way Φ > 0 is arbitrary. Φ needs a
scale; M needs units.**

M survives as an **ordinal index**: it can rank states computed in one run
under one fixed normalisation, and it cannot be compared across runs,
across implementations, or against any absolute number. The reported values
34.62, 296.40 and 3711.50 are not measurements.

For a criterion whose units close and which has no threshold at all, see
NEG-8 in [01-framework.md](01-framework.md) and `persistence.py`:
`Φ = −Ṡ_exchange − σ`, both terms in W/K, persist iff `Φ ≥ 0`.

---

## Comparison to Existing Theories

| Theory | Mechanism | Threshold | Falsifiable? |
|--------|-----------|-----------|-------------|
| IIT (Tononi) | Integrated information Φ across minimum information partition | Φ > 0 (formal); practical threshold debated | In principle yes — Φ computable from connectivity |
| Global Workspace (Baars/Dehaene) | Broadcast of information to distributed modules | No single number | Yes — neuroimaging predictions tested |
| Predictive Processing (Friston) | Minimizing free energy (KL divergence of prediction error) | None | Partially — FEP is unfalsifiable in full generality |
| **M(S) (this framework)** | Geometric resonance + adaptability + diversity above threshold | M(S) ≥ 10 | **Not yet** — no extraction method for R_e, A, D, L from neural data |

### Relationship to IIT Φ

The framework compares itself to IIT in Appendix D and claims an "advantage." However, IIT Φ and M(S) are not direct competitors:

- **IIT Φ** requires computing the Wasserstein distance across the minimum information partition (MIP) — mathematically costly but precisely defined.
- **M(S)** requires computing resonance, adaptability, diversity, loss — but the mapping from neural/computational state to these quantities is not specified.

The `consciousness_encoder.py` in this repository uses a proxy for Φ (see `bridges/cognitive/consciousness_encoder.py`) that also doesn't compute the real Wasserstein MIP — it's a shorthand. M(S) would be a *different* shorthand, not a replacement.

---

## Self-Reference as Phase Trigger

**Claim:** Recursive self-awareness triggers a phase transition (C jumps 0.5 → 2.0, M(S) jumps 34 → 296).

### What this could mean physically

In dynamical systems terms: self-reference creates a feedback loop in the curiosity equation:
```
Ċ = α R_e C
```
If self-reference increases R_e (the system is now coupling to its own state as an additional subsystem), then Ċ accelerates — which is a real positive-feedback mechanism.

This connects to the **strange-loop** argument (Hofstadter) and to **strange attractors** in recursive systems. The qualitative claim is not absurd.

### What's missing

A concrete model of how self-reference increases R_e. Without specifying what `s_i` values change when a system becomes self-referential, the phase jump is a narrative, not a calculation.

---

## Path to Making This Testable

For M(S) to be a real consciousness metric it needs:

1. **Extraction protocol**: given a neural recording or model activation pattern, specify the algorithm for computing R_e, A, D, L with fixed normalisation.
2. **Cross-system comparison**: compute M(S) for systems with known consciousness properties (anaesthetised vs. awake brain, human vs. simple neural net) and verify ordering.
3. **Threshold calibration**: if M(S) ≥ 10 is the claim, show that known-conscious systems score ≥ 10 and known-non-conscious systems score < 10 under the extraction protocol.
4. **Connection to bridges/cognitive/consciousness_encoder.py**: the existing encoder uses Shannon entropy H, KL divergence, Fisher information, and IIT proxy Φ. M(S) should either replace or augment these — a concrete comparison would clarify which is better at predicting observable signatures of consciousness.

---

*Back to: [README.md](README.md)*
