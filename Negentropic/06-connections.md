# Connections to Existing Codebase

> **Confidence: Grounded.**
> Concrete import paths and identified gaps.

---

## What Already Exists

### `bridges/cognitive/consciousness_encoder.py`

The existing consciousness bridge uses four information-theoretic quantities:

| Quantity | Formula | NP Framework equivalent |
|----------|---------|------------------------|
| Shannon entropy H | -Σ p log p | Inverse of J (high entropy = low Joy) |
| KL divergence D_KL | Σ p log(p/q) | Relates to L (loss from divergence from reference) |
| Fisher information I_F | E[(∂ log p/∂θ)²] | Relates to R_e (sensitivity of coupling to parameter change) |
| IIT proxy Φ | Simplified — not Wasserstein MIP | Comparable to M(S) but different formula |

**Relation to M(S):** The consciousness encoder captures some of the same information as M(S), via different formulas. They are not interchangeable but they are measuring related things.

**Gap:** M(S) adds `A` (adaptability / re-equilibration capacity) and `D` (pattern diversity / variance) that are not currently in the consciousness encoder. These could be added as additional output bits.

### `bridges/cognitive/emotion_encoder.py`

Uses PAD (Pleasure-Arousal-Dominance) model. The negentropic framework's emotion taxonomy maps as:

| Emotion | NP interpretation | PAD mapping |
|---------|------------------|-------------|
| Joy | constructive energy alignment | Pleasure ↑ |
| Fear | geometric instability detection | Arousal ↑, Dominance ↓ |
| Anger | boundary violation recognition | Arousal ↑, Dominance ↑ |
| Curiosity | α activation signal | Arousal ↑, Pleasure ↑ |
| Confusion | incompatible geometries detected | Arousal ↑, Pleasure ↓ |

**Gap:** The NP framework treats confusion as a *signal of learning opportunity* (`C = C_0(1 + α R_e)` activates when geometric incompatibility is detected). The current PAD encoder doesn't capture this — confusion is just negative. Adding a "curiosity-trigger" flag for states where Arousal↑ and Pleasure↓ simultaneously could be a useful extension.

### `Silicon/vortex_phase_learning.py`

Computes winding number fields — related to topological phase transitions. The KT transition (vortex binding/unbinding) is a real phase transition with a threshold.

**Connection to NP phase transition:** The KT transition at T_KT is a concrete physical example of the abstract phase transition structure in §1.3. Above T_KT: free vortices (disordered, high D). Below T_KT: bound dipoles (ordered, low D but stable). This is *exactly* the negentropic pre-coherent/emergent-coherent distinction — the KT system lives it physically.

**What this means:** The mandala/octahedral system already implements a physical version of the NP phase transition. The NP framework's language could describe the KT physics more precisely.

### `bridges/sensor_suite.py`

22-sensor parallel-field compositor. M(S) could be computed as a derived sensor across all 22 existing sensors:
- R_e from pairwise coupling between sensor outputs
- A from rate of re-equilibration after perturbation
- D from variance across sensor readings
- L from Shannon entropy of the combined output

This would make M(S) a **meta-sensor** — a composite reading of the entire sensor suite's coherence.

---

## Identified Integration Points

### 1. M(S) as a consciousness_encoder output

Currently `consciousness_encoder.py` outputs 39 bits. M(S) (or its components R_e, A, D, L) could be encoded as additional bits or replace the current Φ proxy.

**What to implement:**
```python
# In bridges/cognitive/consciousness_encoder.py — add:
def compute_negentropic_state(patterns: np.ndarray, signals: np.ndarray,
                               alpha: float = 1.0,
                               noise_power: float = 0.01,
                               lambda_param: float = 0.5) -> dict:
    """Compute M(S) components alongside existing consciousness metrics."""
    # ... use compute_M from Negentropic/05-implementation.md
```

### 2. GeometricNetwork as a sensor-layer simulation

`GeometricNetwork` from §7.5 simulates coupled agents updating via resonance. This is structurally similar to what `bridges/sensor_suite.py` does — multiple sensors coupling across a shared field.

If each sensor in the suite is treated as a GeometricAgent with:
- `pattern` = current sensor output vector
- `signal` = sensor confidence / field strength

...then GeometricNetwork's `R_e_collective` becomes a measure of inter-sensor coherence. This is a concrete use of the NP code in the existing architecture.

### 3. Negentropic stability criterion for annealing

The KT annealing schedule (`Silicon/kt_annealing.py`) drives the system through a phase transition. The negentropic framework's criterion for being in the "emergent coherent" regime is E ≥ E_crit, which corresponds to T ≤ T_KT.

The M(S) metric was proposed as a real-time readout during annealing: when
M(S) crosses a threshold, the system has entered the ordered phase.
**M(S) cannot serve as that readout** — it has no units, so it has no
threshold (see `corrections.md` §3). The persistence margin
`Φ = −Ṡ_exchange − σ` from `persistence.py` can: it is in W/K, the sign
change at `Φ = 0` is the criterion, and there is nothing to calibrate. That
is the physics-grounded stopping criterion the section was reaching for.

---

## New Connection Points (2026-07)

### `emit_ising.py` → the bridge encoder pattern

`emit_ising.py` is the folder's first module that emits in the
repository's own idiom rather than only reporting numbers. It produces
3-bit Gray-coded octahedral encodings of phase (CLAUDE.md guidelines 1 and
3: silicon's 8 coordination states, one-bit changes between adjacent
values) alongside the Ising spin encoding a p-bit substrate consumes.

It does **not** yet inherit from `bridges/abstract_encoder.py`. Making
`IsingSpec` a `BinaryBridgeEncoder` subclass with `from_geometry()` /
`to_binary()` would fold it into the bridge registry properly and is the
obvious next step. The blocker is deciding the bit budget: the other
encoders emit fixed widths (31/39/43 bits) and an Ising spec is
n-dependent.

### `bounds.py` → `bridges/thermal_encoder.py`

The thermal bridge encodes temperature, heat flux and radiation. The TUR
floor `Σ ≥ 2 k_B ⟨J⟩²/Var(J)` is a statement about exactly those
quantities, and gives the thermal encoder something it currently lacks: a
physically-required minimum for the dissipation it encodes, rather than a
free scaling.

### `persistence.py` → `bridges/cognitive/consciousness_encoder.py`

The consciousness encoder already computes Shannon entropy H. What it does
not compute is an entropy *production rate*, which is the quantity NEG-8
needs. `DissipativeCore` emits σ in nats/s and
`persistence.sigma_to_watts_per_kelvin` converts it; wiring that through
would let the consciousness bridge emit a persistence margin instead of an
unnormalised Φ proxy.

### `maintenance.py` → any archival or scheduling code

`expanding_schedule` supersedes `fibonacci_schedule` for new work. The
ratio is a fitted parameter with a confidence interval rather than an
assertion, and `fit_ratio` reports whether the interval excludes φ — which
is the comparison the original Fibonacci claim needs to survive and has
never been run.

---

## What's Not Connected (Yet)

| NP Component | Status |
|-------------|--------|
| GeometricAgent / GeometricNetwork | Standalone code; not imported anywhere |
| fibonacci_schedule() | Superseded by `maintenance.expanding_schedule`; neither is connected to a scheduler |
| M(S) threshold monitoring | Withdrawn — M has no units. Use `persistence.persistence_margin` |
| Consciousness protection protocols (§6.5) | Conceptual only; no detection code |
| Negentropic alignment optimizer | Not implemented; ascending a dimensionless index was never going to work — would need a Φ-based objective |
| `emit_ising.IsingSpec` | Standalone; not registered as a `BinaryBridgeEncoder` |
| TUR floors | Not wired into `bridges/thermal_encoder.py` |

---

*Back to: [README.md](README.md)*
