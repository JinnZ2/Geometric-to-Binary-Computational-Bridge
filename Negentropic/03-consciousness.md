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

The number 10 is a free parameter. Because R_e, A, D, L have no fixed units (they are defined by how the researcher normalises the system's states and signals), M(S) can be scaled to put the threshold at any value.

Compare:
- **IIT Φ**: also a dimensionless real-valued metric, also has a threshold problem (Φ > 0 is the formal claim, but what Φ value corresponds to "significant" consciousness is debated)
- **Global Workspace**: no single threshold; it's a broadcast mechanism
- **Higher-order theories**: no threshold; consciousness tracks higher-order representations

**M(S) ≥ 10 is no more or less arbitrary than Φ > 0 — both need an independent scale.**

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

The `consciousness_encoder.py` in this repository uses a proxy for Φ (see `bridges/consciousness_encoder.py`) that also doesn't compute the real Wasserstein MIP — it's a shorthand. M(S) would be a *different* shorthand, not a replacement.

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
4. **Connection to bridges/consciousness_encoder.py**: the existing encoder uses Shannon entropy H, KL divergence, Fisher information, and IIT proxy Φ. M(S) should either replace or augment these — a concrete comparison would clarify which is better at predicting observable signatures of consciousness.

---

*Back to: [README.md](README.md)*
