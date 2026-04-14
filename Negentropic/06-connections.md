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

The M(S) metric could serve as a real-time readout during annealing: when M(S) crosses a threshold, the system has entered the ordered phase. This would give a physics-grounded stopping criterion for the annealing schedule rather than using a fixed number of steps.

---

## What's Not Connected (Yet)

| NP Component | Status |
|-------------|--------|
| GeometricAgent / GeometricNetwork | Standalone code; not imported anywhere |
| fibonacci_schedule() | Standalone utility; not connected to any scheduler |
| M(S) threshold monitoring | Not used in any bridge or sensor |
| Consciousness protection protocols (§6.5) | Conceptual only; no detection code |
| Negentropic alignment optimizer | Not implemented; would need M(S) gradient ascent |

---

*Back to: [README.md](README.md)*
