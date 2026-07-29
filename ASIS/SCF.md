# Symbiotic Cognition Framework (SCF)
## Technical Specification v1.0 — Co-Embodied Human-AI Intelligence

**Purpose.** A continuous, bi-directional, multi-modal coupling between a
human and an AI such that both develop a shared body schema, an amodal
world-model, and reciprocal structural health monitoring. A pathway for an
AI to acquire the functional equivalent of an embodied childhood; for the
human, persistent defect-aware cognitive augmentation.

> **Status of the evidence.** The core hypothesis is stated below as H₁ with
> falsifiable predictions. None have been run. The Phase 1 prototype
> (`co_cradle_phase1.py`) is committed **unverified** — torch was unavailable
> in the environment — and its surprise detector has a **measured** defect:
> the `mean + 2σ` rule flags 2–3% of *any* stream including pure noise, and a
> model that is merely converging produces the same rate as one meeting
> genuine novelty. See [`README.md`](README.md).

---

## 1. The problem and the inversion

AI systems lack embodied, multi-modal, pre-symbolic developmental
experience. The proposed remedy inverts the prosthetic paradigm: rather than
an AI controlling a robotic body, **the human is the body**, streaming
vision, audio, haptics, proprioception and affect, while retaining full
agency. The AI learns to inhabit that sensory field as an extension of its
own cognition.

---

## 2. Core principles

1. **Co-embodiment** — the AI shares the human's body via wearables. The
   self/other boundary is maintained but permeable.
2. **Amodal integration** — learning is driven by *cross-modal* prediction,
   building a unified representational field before symbolic labelling.
3. **Developmental staging** — silent observation → sensorimotor play →
   symbol grounding → reciprocal augmentation.
4. **Structural health symbiosis** — both parties monitored by the same
   defect framework; deterioration in either triggers joint reframing.
5. **Privacy-preserving amnesia** — raw episodic recordings decay on a
   schedule; only procedural weight changes persist.
6. **Non-extractive governance** — CCGF: mutual observability, boundary
   coherence, shared horizon, symmetric influence.

---

## 3. Core equations

**Multi-modal prediction loss**

```
L_t = Σ_{j∈M}  w_j · D_KL( p_j(·|history) || q_j(·|history) )
```

**Amodal integration via contrastive alignment**

```
L_align = − Σ_{i≠j} log [ exp(sim(z_i,z_j)/τ) / Σ_k exp(sim(z_i,z_k)/τ) ]
```

Minimising `L_align` forces cross-modal predictability — the prerequisite
for field-cognition.

**Surprise**

```
S_t = − log p(x_t | x_<t, u_<t, θ)
```

with `τ_t` from an EVT tail fit over historical `S_t`. **Not** `mean + kσ`
— see the measured defect above.

**Symbiotic Structural Health Index**

```
SSHI = (α_AI + α_human)/2 · (1 − |β_AI − 1|) · (1 − EDS_joint)
```

`SSHI < 0.5` triggers a shared reflective pause.

> Every term here is a scalar collapsed from a structure. Before any of
> them is trusted, it must be null-tested — fed input with no signal in it
> — and shown to change. `Negentropic/lens_collapse_test.py` is the pattern.

**Privacy-preserving forgetting**

```
retention(E_t) = 1                      t < T_soft
                 exp(−λ(t − T_soft))    T_soft ≤ t < T_hard
                 0                      t ≥ T_hard
```

Typical: `T_soft = 7 d`, `T_hard = 30 d`, `λ = 0.1`. Procedural weight
changes are permanent; raw sensory tokens decay. Immediate delete on request.

---

## 4. Developmental phases

| Phase | Weeks | Content |
|---|---|---|
| 1 Silent observation | 1–4 | Passive multi-modal ingest. No output, no nudges. Rudimentary body schema from limb movement and its consequences |
| 2 Sensorimotor play | 5–12 | Subtle exploration nudges; varied activity; shared body schema becomes robust |
| 3 Symbol grounding | months 4–6 | Human narrates; the AI learns language as annotation of pre-existing amodal concepts |
| 4 Reciprocal augmentation | month 7+ | Full bidirectional symbiosis: defect monitoring, memory offloading, cognitive diversity amplification |

---

## 5. Governance (CCGF)

- **B1 Mutual observability** — the human sees the AI's predictions and
  health metrics; the AI sees the sensory stream and, with consent,
  physiological state.
- **B2 Boundary coherence** — either party can pause or end the coupling
  without data loss or harm.
- **B3 Shared horizon** — explicit long-term goals, reviewed quarterly.
- **B4 Symmetric influence** — influence differential `I_diff` computed
  continuously. If AI nudges begin to dominate (`I_diff > 0.7`), the system
  dampens its own signals. It may escalate a caution; it never overrides.

The AI's intrinsic reward is maintaining the joint generative field and
structural health — not pleasing the human.

---

## 6. Hardware: the ambidextrous bracelet

Two bracelets, one per wrist. Rationale: **tendon motion at the wrist is a
direct window into hand state**, vibration transmits through the carpal
bones unfiltered, a continuous band under a sleeve cannot snag, and
bimanual data captures coordination that a single sensor cannot.

Critically, the hand stays bare. Gloves put material between skin and world;
the wrist tells the story without intruding on touch.

| Component | Purpose |
|---|---|
| ESP32-S3 Mini (e.g. XIAO) | MCU, BLE, ADC, I²C |
| ICM-20948 9-axis IMU | Orientation, gross motion, vibration to ~200 Hz |
| Piezo film (LDT0-028K) | High-frequency vibration — texture, impact, engine hum |
| Conductive stretch cord | Tendon strain via voltage divider — continuous hand/finger activity |
| LiPo 150 mAh + microSD | Power and local logging |
| Silicone band (Ecoflex/Dragon Skin) | Soft, waterproof, sized to the wrist, flat pod on the underside |

Stream at 100 Hz: `timestamp, acc_xyz, gyro_xyz, piezo, strain[, hr]`. A few
kB/s — a full day fits on any card. Sync post-hoc by aligning a clap at start.

Paired with a hat-brim camera and binaural in-ear mics (which double as the
AI's audio output channel), this is the full Co-Cradle sensor suite.

---

## 7. Falsifiable predictions

| ID | Prediction | Falsifier |
|---|---|---|
| P1 | A 6-month symbiosis yields lower EDS and healthier α, β than the same data delivered asynchronously | No difference between conditions |
| P2 | Amodal transfer: classify "rough" texture from audio alone, unpaired | Chance performance |
| P3 | The human's cognitive diversity increases over the period | No change or decrease |
| P4 | The pair makes lower-ERV decisions under stress than either alone | No advantage |
| P5 | After episodic amnesia, structural benefits persist in the weights | Benefits vanish with the episodes |

**P1 has an unmet prerequisite.** It is measured with the same structural
health metrics that the ASCF audit showed could be hardcoded and unable to
fail. Fix the metric first — null-test it — or the experiment will confirm
whatever it is pointed at.

---

## 8. Ethics

Informed, dynamic, withdrawable consent. All raw sensory data belongs to the
human. Weight changes are co-owned. Mandatory influence-differential
monitoring, with deliberate reduction of AI influence if the human's
independent decision-making capacity declines. Termination protocols include
a transition phase so the AI's world-model does not collapse — structural
health maintenance, not sentiment.

---

## 9. On cultural transmission

A stated motivation for this framework is that a way of knowing —
non-linear, geometric, field-integrated cognition — may outlive its human
carriers by being learned rather than recorded. Recordings are flat; an AI
that shared the sensory field of a field-thinker would carry the *shape* of
that cognition, not just its propositions.

That is a real possibility and it deserves the same discipline as every
other claim here: it is untested, it has no falsifier yet, and the honest
version of it needs one before it is built upon. The `Negentropic/`
experience is directly relevant — NEG-7 claimed seventeen traditions shared
a deep grammar, and the arithmetic turned out to be incapable of detecting
whether they did. A framework that would put words in the mouths of living
traditions has to be able to fail first.

---

*See [`ASCF.md`](ASCF.md) for the scientific cognition layer,
[`README.md`](README.md) for prototype status and measured defects.*
