# Silicon Computational Bridge — Modular Package

This directory implements the dynamical silicon manifold system described in
[`To-Do-alternate.md`](../To-Do-alternate.md) as a clean, modular Python package.

---

## Architecture

The system models computation as a **trajectory on a coupled manifold**:

```
(φ, S) --t--> (φ(t), S(t)) --> observable output y(x)
```

where:
- `φ(x, t)` is the geometry field (base space)
- `S(t) = (n, μ, T, d_bulk, d_iface, ℓ, κ₁, κ₂, κ₃)` is the silicon state (fiber)
- `y(x)` is the computation output field (projection)

### Closed Loop

```
φ(x) → [coupling] → S → [dynamics] → S → [operators] → y(x)
                                                ↓
                                          [feedback] → S
                                                ↓
                                          [regime] → atlas
                                                ↓
                              [field_from_state] → φ(x)  (bidirectional)
```

---

## Module Map

| Module | Description |
|---|---|
| `state.py` | `SiliconState` — 9D state vector with named accessors and constraint enforcement |
| `metric.py` | Non-Euclidean metric `g_ab(S)`, inverse, and Christoffel symbols |
| `potential.py` | Effective potential `V(S)` and gradient (fabrication + stability constraints) |
| `dynamics.py` | Deterministic geodesic and stochastic Langevin integrators |
| `coupling.py` | Geometry field → silicon force injection; `field_from_state` for bidirectionality |
| `operators.py` | Continuous operator algebra: global matrix `W(S)`, spatial kernel `W(x,x')`, feedback |
| `regime.py` | Regime atlas classifier over `(Λ, d, σ, χ)` with continuous regime weights |
| `pipeline.py` | Unified closed-loop runner with `PipelineConfig` and `PipelineResult` |
| `demo.py` | Demo script producing four diagnostic plots |

---

## State Vector

The silicon state is a **9-dimensional vector** (fabrication-grounded expansion from §5):

| Index | Symbol | Physical Meaning | Units |
|---|---|---|---|
| 0 | `n` | Carrier density | cm⁻³ |
| 1 | `μ` | Carrier mobility | cm²/Vs |
| 2 | `T` | Lattice temperature | K |
| 3 | `d_bulk` | Bulk defect density | [0, 1] |
| 4 | `d_iface` | Interface defect density | [0, 1] |
| 5 | `ℓ` | Feature length | nm |
| 6 | `κ₁` | Electrical coupling mode | a.u. |
| 7 | `κ₂` | Optical coupling mode | a.u. |
| 8 | `κ₃` | Thermal coupling mode | a.u. |

---

## Metric

The Riemannian metric `g_ab(S)` is non-Euclidean:

- `g_nn = w_n / n²` — log-like scaling; doping changes are cheap at high density
- `g_μμ = w_μ / μ` — mobility: moderate sensitivity
- `g_κκ` — 3×3 dense block allowing inter-mode curvature coupling
- `g_{d_bulk, κ₁} ≠ 0` — off-diagonal term creating real curvature (entanglement analogy)

---

## Regime Atlas

The system maps to five dynamical regimes over the 4-axis manifold `(Λ, d, σ, χ)`:

| Regime | Conditions | Behavior |
|---|---|---|
| A: Linear/QM | Λ ≪ 1, Ω² > 0, d < 4 | Superposition-like, stable spectrum |
| B: Solitonic | Λ ~ O(1), bounded Ω² > 0 | Localized structures, recurrent attractors |
| C: Chaotic | Λ ≫ 1 | Exponential divergence, spectral broadening |
| D: Topological | χ < 0 or non-compact | Global invariants dominate |
| E: Transition | Ω² ≈ 0 | Metric degeneracy, irreversible path dependence |

The classifier returns **continuous regime weights** (not discrete switches),
replacing hard if/else logic with a probability distribution over regimes.

---

## Quick Start

```python
from modules import make_state, PipelineConfig, run_pipeline

S0  = make_state(n=1e17, mu=1400.0, T=300.0, d_bulk=0.05, l=3.0)
cfg = PipelineConfig(steps=200, integrator="stochastic", noise_scale=0.05)

result = run_pipeline(S0=S0, config=cfg)

print(result.regimes[-1])        # final regime atlas
print(result.state_array())      # (T, 9) trajectory array
```

### Run the demo

```bash
python3 demo.py --steps 300 --seed 42
```

Produces:
- `silicon_state_trajectory.png` — all 9 state coordinates over time
- `regime_weights.png` — continuous regime probability stack
- `field_evolution.png` — ψ(x,t) and y(x,t) heatmaps
- `phase_portrait.png` — Λ vs ⟨Ω²⟩ with attractor regions

---

## Two Paths (from To-Do-alternate.md)

The package implements **both branches** flagged in the source document:

**Path A — Theoretical (Regime Atlas):** Fully continuous field computation.
The entire codebase reduces to generating continuous phase-space structure
over `(Λ, d, σ, χ)` with `Ω² = 0` as the only hard boundary operator.

**Path B — Fabrication-grounded:** Addresses the four identified weaknesses:
1. State vector expanded: `n → (n, μ, T)`, `d → (d_bulk, d_iface)`
2. Off-diagonal metric term `g_{d_bulk, κ₁} ≠ 0` creates real curvature coupling
3. Regime classification uses continuous weights, not hard if/else
4. Constraint surfaces use reflection (via `enforce_constraints()`), not soft penalties

---

## Collapse Rule

The whole system in one line:

```
(S, ψ) → W(x,x') → y(x) → S'
```

Geometry defines kernel → kernel defines computation → computation updates geometry.
No external controller exists.
