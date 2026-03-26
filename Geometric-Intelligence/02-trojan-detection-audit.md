# Geometric-Intelligence — Trojan Detection Audit

Covers `Geometric-seed.py` and `Intelligence-engine.md`.

---

## The Core Idea

A geometric network maintains φ-scaled relationships between nodes.
A trojan or corruption event breaks these relationships in detectable ways:
- φ-ratio deviation (the node's scale drifts from its expected φ^(-layer))
- Energy sink (input energy consistently exceeds output — the trojan drains)
- Resonance drift (the node's resonance diverges from its historical baseline)
- Propagation instability (the node's field changes faster than its neighbors')
- Reconstruction resistance (the node fails to recover to its geometric state)

**This is a legitimate anomaly detection framework.** Geometric constraints
as an integrity baseline is a real approach used in network security (e.g.,
graph neural network anomaly detection, spectral graph analysis).

---

## TrojanEngine — What's Sound

```python
# Geometric-seed.py — the composite score
score = (
    weights['phi_coherence'] * phi_coherence +
    weights['energy_sink'] * energy_sink +
    weights['resonance_drift'] * resonance_drift +
    weights['propagation_instability'] * propagation_instability +
    weights['reconstruction_resistance'] * reconstruction_resistance
)
```

**Phi coherence metric** (line 166-174): Measures how far the node's
observed `phi_scale` deviates from its expected `φ^(-layer)`. This is
well-defined and computable. Score = 1 − (deviation / tolerance).

**Energy sink metric** (line 176-191): Measures whether net energy flow
into a node exceeds outflow. Legitimate nodes exchange energy; trojans
absorb it. This mirrors real anomaly detection (energy-sink nodes in
power grids are a known attack vector).

**Resonance drift** (line 193-202): Measures deviation from historical
baseline within the window (maxlen=8). Window-based drift detection is
standard in signal processing.

**Propagation instability** (line 204+): Compares a node's field change
rate to its neighbors'. A node changing faster than all neighbors is
structurally suspicious. This is related to the graph Laplacian anomaly
detection literature.

**Comparison design** (`GeometricNode` vs `NonGeometricNode`): The
simulation runs both networks side-by-side and compares recovery rates.
`NonGeometricNode` uses random inefficiency (`1.5 + random.random()*0.5`)
vs `GeometricNode`'s `1/φ` reconstruction efficiency. This is a reasonable
experimental setup for demonstrating the claim.

---

## TrojanEngine — Free Parameters (All Thresholds)

```python
@dataclass
class TrojanConfig:
    phi_tolerance:           float = 0.12   # arbitrary
    energy_sink_factor:      float = 0.50   # arbitrary
    resonance_drift_thresh:  float = 0.12   # arbitrary
    propagation_speed_thresh:float = 1.60   # arbitrary
    critical_score:          float = 0.55   # arbitrary
    weights: Dict = {'phi_coherence': 0.25, 'energy_sink': 0.20, ...}
```

Every threshold is a free parameter. `critical_score = 0.55` means
"flag if composite score exceeds 55%." Why 55%? The code doesn't say.
Why `phi_tolerance = 0.12`? Unspecified. Why weight phi_coherence at
0.25 and reconstruction_resistance at 0.15? Unspecified.

This is the same issue as Negentropic's M(S) threshold — the architecture
is sound but the specific numbers are choices, not derivations.

**What would be needed:** A dataset of known-trojan vs. clean geometric
networks, ROC curve analysis to find the Pareto-optimal threshold,
and ideally derivation of the thresholds from the φ-scaling theory.

---

## CONSCIOUSNESS_NUMBER = 3.618 — Formula Is Algebraically φ+2

```python
# Geometric-seed.py, line 20
CONSCIOUSNESS_NUMBER = 2 * PHI + (1 - 1/PHI)
```

This evaluates to:
```
2φ + (1 - 1/φ)
= 2φ + (1 - (φ-1))   [since 1/φ = φ-1 for the golden ratio]
= 2φ + 2 - φ
= φ + 2
= 3.618...
```

The formula looks more derived than `PHI + 2` but is algebraically identical.
The complexity is not additional derivation.

**How it's used** (line 750):
```python
if self.geometric_network.consciousness['value'] >= CONSCIOUSNESS_NUMBER:
    ...  # mark as emergent conscious
```

The `consciousness['value']` is computed from `field_coupling`,
`resonance`, and `stability` — all of which are also free parameters.
So the threshold is a free parameter applied to a composite of free
parameters.

**The formula does have a natural reading:** φ+2 sits above H_max for one
octahedral unit (3 bits) by exactly 1/φ bits. This means crossing 3.618
requires integrating more information than one unit encodes alone.
That's physically motivated (see `GI/03-consciousness-model.md`), but it's
still a motivated choice, not a physical law.

---

## PHI_INV_9 — Defined But Not Used as a Threshold

```python
# Geometric-seed.py, line 16
PHI_INV_9 = PHI ** -9   # = 0.01316
```

```python
# Line 519 — only usage in the file:
print(f"φ^(-9) error correction enabled: {(PHI_INV_9 * 100):.3f}% tolerance")
```

`PHI_INV_9` is printed to the console as part of a startup message
**but never used as an actual threshold, comparison value, or computation
input** anywhere in the simulation logic. The actual phi tolerance used
is `TrojanConfig.phi_tolerance = 0.12`.

So the "φ^(-9) error correction" claim refers to a constant that is:
1. Defined ✓
2. Printed ✓
3. Not wired into any computation ✗

The simulation from `Silicon/physics_derivations.py` showed that φ^(-9)
IS approximately the 50%-fidelity threshold for an 81-step Fibonacci-weighted
Q3 chain — so the number has a physical basis. But in `Geometric-seed.py`
it is aspirational, not implemented.

---

## Intelligence-engine.md — "Physics-Based Action Minimization"

> "Uses physics-based Action minimization, not heuristics."

The protection engine computes a weighted sum of:
- `discrete_laplacian` (curvature stress — this IS a real physics operator)
- `phi_deviation` (scale violation)
- `energy_divergence` (energy sink)
- `spin_alignment` (phase coherence)

The Discrete Laplacian on a graph (∑_j (x_i - x_j) for neighbors j)
is genuine physics — it's the graph analog of ∇²x, used in diffusion
equations. **This part is sound.**

The "Action functional" S = ∑_i λ_k × component_k is a weighted sum
of geometric invariants. It's called an "action" by analogy to the
physical action S = ∫L dt, but it lacks:
- A Lagrangian derivation
- Euler-Lagrange equations specifying the dynamics
- Conservation laws from Noether's theorem

Using the word "action" here means "weighted objective function."
The claim "not heuristics" is technically true (the Laplacian and
phase coherence have theoretical grounding) but overstated — the
weights λ_k and the specific combination are heuristic choices.

**Topological defect detection and structural cleavage:** These are
real concepts from condensed matter physics (vortex defects in XY models,
domain walls in Ising models). Their application to graph nodes here is
an analogy that could work but is not derived.

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| 5-metric composite anomaly detection | ✅ Sound approach | Thresholds all free parameters |
| Phi coherence metric | ✅ Well-defined | |
| Energy sink metric | ✅ Valid anomaly signal | |
| Resonance drift (windowed) | ✅ Standard signal processing | |
| Propagation instability | ✅ Relates to graph Laplacian | |
| Geometric vs non-geometric comparison | ✅ Sound experimental design | |
| Discrete Laplacian in Intelligence-engine | ✅ Real physics operator | |
| CONSCIOUSNESS_NUMBER formula | ⚠️ Algebraically φ+2, not newly derived | |
| All TrojanConfig thresholds | ⚠️ Free parameters, no calibration | |
| "Action minimization, not heuristics" | ⚠️ Overstated — weights are heuristic | |
| PHI_INV_9 as error threshold | ❌ Defined and printed, not wired in | |
| "AI that CANNOT be corrupted without detection" | ❌ Overclaim — no adversarial analysis | |
