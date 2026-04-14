# GI Connections — Hooks into Existing Codebase

## Direct Structural Parallels

### consciousness_encoder.py ↔ ResonantHurricaneAI

`bridges/cognitive/consciousness_encoder.py` encodes internal AI state to 39-bit binary using:
- Shannon entropy H(p) — maps to AI information state
- KL divergence — maps to model drift from baseline
- Fisher information — maps to parameter sensitivity
- Integrated information Φ (proxy) — maps to consciousness estimate

`ResonantHurricaneAI.resonance_score` is a conceptual analog to the
consciousness encoder's Φ proxy: both measure internal-external alignment.
The difference is that consciousness_encoder produces a stable binary output
(39 bits, lossless, Gray-coded), while resonance_score diverges without bounds.

**Integration path:** Feed `resonance_score` (after clamping to [0,1])
into `ConsciousnessBridgeEncoder.from_geometry()` to produce a stable
binary snapshot of the agent's resonance state at each storm step.

```python
from bridges.cognitive.consciousness_encoder import ConsciousnessBridgeEncoder
encoder = ConsciousnessBridgeEncoder()

# Clamp first (fixes divergence bug)
clamped_resonance = min(max(self.resonance_score, 0.0), 1.0)

# Map to consciousness encoder fields
consciousness_bits = encoder.to_binary({
    'entropy': clamped_resonance,          # proxy for information state
    'confidence': self.curiosity_level / 5.0,   # normalized [0,1]
    'attention': max(coupling_results.values()),
    'phi_proxy': self.happiness_score       # would need normalization
})
```


### emotion_encoder.py ↔ _compute_storm_joy

`bridges/cognitive/emotion_encoder.py` implements the PAD (Pleasure-Arousal-Dominance)
state + causality drill. `_compute_storm_joy()` computes a scalar joy signal
from:
- `discovery_joy` = max coupling strength × curiosity_level  → maps to **Arousal**
- `creation_joy` = equivalent turbines × 0.1               → maps to **Pleasure**
- `learning_bonus` = pattern confirmed? 2.0 : 0.2           → maps to **Dominance**

The emotion encoder's causality drill points to the physical bridge that
needs re-evaluation when PAD intensity exceeds the drill threshold. In GI
terms, this would mean: when `resonance_score > 0.95 and not _pattern_seen_before()`,
the emotion encoder fires a drill-target pointing to the Magnetic or Wave
bridge for deeper field analysis.

**Integration path:** Replace the raw `happiness_score += joy` accumulator
with an emotion encoder output, giving:
- A stable 39-bit binary representation of the emotional state
- The causality drill mechanism that routes back to physical bridges when
  emotional intensity is high (instead of allowing unbounded accumulation)


### sensor_suite.py ↔ GeometricPatternDetector

`bridges/sensor_suite.py` is a 22-sensor parallel field compositor.
Each sensor outputs a field reading; the suite composites them.

`GeometricPatternDetector.detect_all_patterns()` produces 5 coupling
coefficients (one per universal pattern). These map naturally to a
sensor suite input: each pattern is a "sensor channel" reading the
storm's state at a specific harmonic mode.

**Integration path:** Register the 5 GI pattern detectors as sensor
channels in the suite. The suite's field composition then produces a
unified binary representation of the storm's geometric state, compatible
with the Engine's SIMD optimizer.


### KT Annealing ↔ Curiosity Management

`Silicon/kt_annealing.py` implements the logarithmic cooling schedule
that drives a system through the Kosterlitz-Thouless transition.

The GI framework's curiosity management has an analogous structure:
- When learning_velocity < 0.1: boost curiosity aggressively (→ "heat up")
- When pattern_growth < 0: reset parameters (→ "quench below T_KT")

These are ad-hoc thresholds. The KT annealing schedule provides a
principled equivalent: set `T_eff ∝ 1/curiosity_level`, and use
`schedule_log()` to control how curiosity cools as the agent accumulates
patterns. This prevents both the plateau (learning_velocity → 0) and
the divergence (curiosity × resonance runaway).

```python
from Silicon.kt_annealing import schedule_log, T_KT_NUMERICAL

# Replace ad-hoc curiosity management with KT-derived schedule
def _update_curiosity_kt(self, step, total_steps):
    T_kt = T_KT_NUMERICAL  # 0.894 (numerical estimate)
    T = schedule_log(step, total_steps,
                     T_init=4.0 * T_kt,
                     T_kt=T_kt,
                     T_final=0.05 * T_kt)
    # curiosity_level tracks temperature: high T = broad exploration
    self.curiosity_level = min(T / T_kt, 5.0)
```


### SubstrateReasoner (KnowledgeDNA) ↔ Geometric Pattern Routing

From `KnowledgeDNA/geobin_bridge.py` (Resilience repo):
The `SubstrateReasoner` routes physical problems to bridge encoders by
matching substrate properties to domain needs.

`GeometricPatternDetector` produces coupling strengths for 5 pattern types.
These map to substrate properties already defined in the geobin bridge:

| GI Pattern | SubstrateReasoner property | Bridge domain |
|-----------|---------------------------|---------------|
| spiral_dynamics | `synchronization`, `gradient_flow` | Magnetic Bridge |
| energy_coupling | `field_superposition`, `energy_transfer` | Electric Bridge |
| intensification | `phase_transition`, `resonance` | Wave Bridge |
| dissipation | `decay_modeling`, `equilibrium_seeking` | Thermal Bridge |
| coupling_points | `pressure_dynamics`, `spatial_coupling` | Pressure Bridge |

**Integration path:** After `detect_all_patterns()`, pass the high-coupling
pattern names to SubstrateReasoner as property activations. The reasoner
routes to the appropriate bridge encoder for deeper binary encoding of
that aspect of the storm.

```python
# Pseudo-code
pattern_to_props = {
    'intensification': ['phase_transition', 'resonance'],
    'dissipation': ['decay_modeling', 'equilibrium_seeking'],
    ...
}
active_props = [prop for pattern, strength in coupling_results.items()
                if strength > 0.7
                for prop in pattern_to_props[pattern]]
routing_result = reasoner.reason_from_properties(active_props)
# → routes to Wave Bridge for intensification, Thermal for dissipation, etc.
```


## Missing Documentation (Noted in README)

`Geometric-Intelligence/README.md` references three docs that don't exist:

| Reference | Status | Resolution |
|-----------|--------|-----------|
| `/docs/AISS_Framework.md` | File not found | `docs/` directory has different files; AISS framework not present |
| `/docs/Implementation_Philosophy.md` | File not found | Not in repo |
| `/docs/Power_Law_Integration.md` | File not found | Not in repo |

These should either be created or the references removed. The warnings
in README about misuse are good and should be retained even if the
referenced docs don't exist yet.


## Summary: What Would Make GI Functional

1. **Implement `_compute_toroidal_transform()`** — pick a transform
   (2D FFT of wind field on pressure surface → extract harmonic modes)

2. **Fix divergence bugs** — clamp `resonance_score` to [−1,1]; use
   exponential moving average for `happiness_score`

3. **Ground the Fibonacci claim** — run on HURDAT2 data; compare
   Fibonacci pairs vs. control pairs; report sensitivity/specificity

4. **Remove or replace "Published accuracy: >95%"** — this claim
   should not appear in any form until it is supported by a citation

5. **Wire to existing bridges** — use consciousness_encoder for
   stable binary output; emotion_encoder for joy→drill routing;
   sensor_suite for unified field composition

6. **KT annealing for curiosity** — replace ad-hoc threshold boosts
   with physics-derived cooling schedule
