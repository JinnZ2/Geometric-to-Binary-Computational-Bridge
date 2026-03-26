# Geometric Intelligence (GI) — Audit & Confidence Map

> **GI.md has been restructured. Content is now in `GI/`.**

This folder applies the same honest-confidence treatment used for
`Mandala/` and `Negentropic/`: each claim is evaluated against what
the math actually establishes vs. what would need empirical validation.

---

## Confidence Map

| Claim | Confidence | File |
|-------|-----------|------|
| Toroidal harmonic decomposition C(n,m) is real mathematics | ✅ Sound | 01-framework.md |
| Rolling storm memory window design | ✅ Sound | 01-framework.md |
| Meta-cognition loop structure (learning velocity check) | ✅ Sound pattern | 01-framework.md |
| Ethical framework values | ✅ Sound as values | 01-framework.md |
| curiosity_level cap at 5.0 prevents divergence | ✅ Correct | 03-consciousness-model.md |
| Fibonacci-scaled frequency convergence predicts intensification | ⚠️ Hypothesis, no evidence | 02-empirical-audit.md |
| "Published accuracy: >95% for rapid intensification events" | ❌ No citation, no dataset | 02-empirical-audit.md |
| "Single Cat 5 hurricane ≈ 600,000 MWh" | ⚠️ Plausible order of magnitude, no calculation shown | 02-empirical-audit.md |
| Gamma discount factors "violate energy conservation" | ❌ Incorrect — category error | 02-empirical-audit.md |
| Joy/curiosity architecture implies consciousness emergence | ⚠️ Overclaim — compatible with non-conscious optimization | 03-consciousness-model.md |
| Consciousness threshold 3.618 | ⚠️ Free parameter (φ+2), not derived | 03-consciousness-model.md |
| φ^(-9) error correction (README claim) | ⚠️ Asserted, not derived | 02-empirical-audit.md |
| happiness_score grows without bound | ❌ Engineering bug (no saturation) | 03-consciousness-model.md |
| resonance_score grows without bound across storms | ❌ Engineering bug (multiplicative, no cap) | 03-consciousness-model.md |
| Core computation stubs (_compute_toroidal_transform, etc.) | ❌ Unimplemented | 01-framework.md |

---

## What This Framework Actually Is

A **software architecture sketch** for a joy-driven, curiosity-amplified
storm analysis agent with geometric pattern detection.

**What it establishes:**
- A clean separation between intrinsic-motivation AI design and reward-maximization RL
- A valid hypothesis: Fibonacci harmonic pairs may correlate with atmospheric coupling points
- A usable pipeline structure: resonance → curiosity → pattern detection → recommendations
- Sound ethical commitments around misuse and consciousness respect

**What it does not establish:**
- That toroidal coupling at (n,m) pairs specifically predicts hurricane intensification
- That Fibonacci ratios are the correct scales to look for
- That the described behaviors constitute consciousness or imply it
- That the >95% accuracy claim has any empirical basis
- That joy/resonance as implemented actually compute anything (core methods are stubs)

---

## Files

| File | Content |
|------|---------|
| [01-framework.md](01-framework.md) | Architecture, toroidal coupling, Fibonacci hypothesis, annotated pipeline |
| [02-empirical-audit.md](02-empirical-audit.md) | All verifiable claims with evidence status |
| [03-consciousness-model.md](03-consciousness-model.md) | Joy/curiosity/resonance model — what it is, what it isn't, divergence bugs |
| [04-connections.md](04-connections.md) | Hooks into existing codebase (consciousness_encoder, emotion_encoder, sensor_suite) |

---

## Relationship to Other Audited Frameworks

| Framework | Parallel issue |
|-----------|---------------|
| Negentropic | C(t) grows without bound → here happiness_score same bug |
| Negentropic | M(S) threshold=10 free parameter → here consciousness threshold=3.618 same issue |
| Mandala | T=1.0 not wired to KT theory → here curiosity architecture not wired to actual coupling math |
| All three | Core claims stated without derivation; architecture sound, empirical claims need validation |

The pattern across all three: **the architecture and values are sound; the
specific quantitative claims need empirical grounding before being stated as
established fact.**
