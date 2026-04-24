# Advanced Computation Sim — Working Notes

> Companion design doc for `experiments/advanced_computation_sim.py`.
> Captures the phase-space model, the heuristics that are currently
> placeholders, and the open questions to resolve before the skeleton
> becomes a production simulator.

---

## 1. What the sim models

A computational task is a trajectory through a 2D **computational
phase space** spanned by:

* **Entanglement ratio** (x-axis): how nonlocal the kernel is.
  `0` = separable / diagonal. `1` = fully entangled / off-diagonal.
* **Operator purity** (y-axis): how pure the computational mode is.
  `1` = a single octahedral vertex dominates. `1/8 ≈ 0.125` = fully
  mixed across all 8 vertices.

The four quadrants:

|                | Low entanglement                                  | High entanglement                                |
|----------------|---------------------------------------------------|--------------------------------------------------|
| **High purity** | Structured single-mode. Boolean / solitonic.     | Nonlocal pure. Entangled but coherent.           |
| **Low purity**  | Mixed separable. Probabilistic classical.        | Mixed entangled. Maximally non-classical. Peak ECP. |

`ECP = entanglement_ratio × (1 − purity)` peaks in the bottom-right
quadrant — nonlocal and not confined to a single mode.

## 2. Independent steering dimensions

From the measured correlation structure that motivated this design:

1. **Entanglement ratio** — steer via axis-vs-diagonal vertex targeting.
2. **Purity** — steer via single-vertex vs distributed-weight control.
3. **Spectral gap** — partially independent from (1, 2); controls
   sensitivity / reversibility. `r(purity, spectral_gap) ≈ +0.17`
   (weak positive).
4. **Ω²** — controls whether the system is on a stable Riemannian
   sheet. Not yet represented in the skeleton's observables.

`r(entanglement, spectral_gap) ≈ −0.99` in the demo output is the
strongest signal in the phase space: entangled kernels crush their
smallest eigenvalue. Useful as a reversibility alarm.

## 3. Operational map (target regimes per task)

| Desired computation          | Purity target | Entanglement target | Octahedral target                       |
|------------------------------|---------------|---------------------|-----------------------------------------|
| Boolean logic                | `> 0.35`      | `< 0.3`             | Diagonal vertices (`P110`, `P111`)      |
| Entangled unitary            | `> 0.35`      | `> 0.5`             | Axis vertices (`P000`, `P010`, `P011`)  |
| Probabilistic inference      | `~ 0.125–0.2` | `< 0.3`             | Interior, multiple non-entangled vertices |
| Non-classical mixed          | `~ 0.125–0.2` | `> 0.5`             | Interior near axis vertices, peak ECP  |
| Readout / sensing            | any           | any                 | Near `Ω² = 0` boundary                  |

This is encoded in `OPERATION_MAP` inside the skeleton. Revise the
mapping when the real attractor coordinates land.

## 4. Placeholder heuristics in the skeleton

Every one of these is deliberate and should be refined with real data
before the sim is trusted quantitatively.

### 4.1 `VERTEX_POSITIONS`

Currently hand-written 6D coordinates. Must be replaced by fitted
coordinates from the measured attractor data. Constraints to preserve:

* Axis vertices must dot-product near zero with each other.
* Diagonal vertices must pair with each other more strongly than
  with axis vertices (captures the `+0.93` solitonic correlation).
* Every vertex should sit on the unit sphere in the normalised 6D
  subspace so distance comparisons stay scale-free.

### 4.2 Control law

Today: proportional steering to the nearest target vertex
(`control_force_multi_target`). Next steps, in order:

1. **PID** with integral anti-windup so the state holds a target
   rather than orbiting.
2. **Model-predictive** using the Christoffel + potential model — plan
   a short horizon, pick `u(t)` that minimises path integral of the
   residual to the target basin.
3. **Basin-aware** variant that treats the task not as a vertex
   sequence but as a region sequence in the `(purity, entanglement)`
   phase space itself, letting the controller pick the cheapest vertex
   per region.

### 4.3 Noise model

Today: isotropic Gaussian at `noise_scale`. Real silicon noise should
be **state-dependent** — higher near chaotic / transition regimes,
lower when `Ω²` puts the state on a stable Riemannian sheet. A simple
first upgrade is `scale(S) = base * (1 + α · |gradV(S)|)`.

### 4.4 Christoffel approximation

Only `Γⁿ_nn = −1/n` is kept. The full connection on the 6D manifold
has many more terms; the approximation is tractable but loses all
cross-axis geodesic coupling. Revisit once the metric on `(d, ℓ, κ)`
is calibrated.

### 4.5 Kernel construction

`build_kernel` is a product of a Gaussian in sequence distance, a
Gaussian in field-value difference, an exponential damping in `d`,
and a scalar coupling from `k1..k3`. Works for the phase-space
observables, but the actual physical kernel derives from a FRET /
Coulomb / exchange composition that lives in `Silicon/core/` —
replace with the real composition once the silicon-side bridge is
routed through here.

## 5. Observables and their meaning

| Observable              | Function                      | Meaning                                             |
|-------------------------|-------------------------------|-----------------------------------------------------|
| Vertex weights          | `compute_vertex_weights`      | Softmin over 6D distance to each vertex (length-8 probability). |
| Operator purity         | `operator_purity`             | `max(weights)`. `1/8` = uniform, `1` = one-hot.     |
| Entanglement ratio      | `entanglement_ratio`          | Off-diagonal / (diagonal + off-diagonal) mass.     |
| Spectral gap            | `spectral_gap`                | Smallest `|λ|` of the kernel.                       |
| ECP                     | `ecp`                         | `ent_ratio × (1 − purity)`.                         |

The purity / ECP correlation is negative by construction — that is
expected, not a finding. The **interesting** number is how ECP peaks
align (or fail to) with specific octahedral transitions during a
task.

## 6. Cross-references

The skeleton does not yet talk to the rest of the repo; these are the
natural connection points.

* **`Engine/gaussian_splats/octahedral.py`** —
  `OctahedralStateEncoder` already defines the canonical 8-vertex
  positions on the tetrahedral `(x, y, z)` basis. The current
  `VERTEX_POSITIONS` is a distinct 6D embedding; reconciliation means
  either lifting the encoder's vectors into 6D (via FRET coupling
  axes) or collapsing the sim's state to 3D when the non-silicon
  dimensions are idle.
* **`GEIS/octahedral_state.py`** — `OctahedralState` is the canonical
  discrete 8-state container elsewhere in the repo. A trajectory's
  `dominant_vertex` sequence could be emitted as a stream of
  `OctahedralState` values so GEIS-layer tooling consumes it
  directly.
* **`bridges/intersection/`** — once the sim is runnable end-to-end,
  a trajectory segment becomes a domain in its own right. Add an
  `advanced_computation_rule.py` that emits a `BasinSignature` from a
  `(purity, entanglement)` window so the sim can participate in
  `resonate()` alongside the physical bridges.
* **`Silicon/core/regime_mediated_qec.py`** — the `CodePerformance`
  dataclass and `compute_threshold_surface` are the obvious source
  of truth for *which* vertex corresponds to a fault-tolerant regime.
  Pull those labels through `operation_to_vertex`.

## 7. Open questions

1. **What's the correct 6D metric?** Today `metric_inverse` only
   populates the `(n, d, ℓ)` diagonal. The `κ` block is assumed
   Euclidean — probably wrong given the known curvature along the
   coherence axis.

2. **Is ECP really the right figure of merit?** It penalises purity.
   For Boolean / solitonic tasks that is backwards — purity is a
   feature there, not a bug. The sim probably needs **per-regime**
   figures of merit: `FOM_boolean = purity − 0.5 · entanglement`,
   `FOM_entangled = entanglement × purity`, etc.

3. **How does `Ω²` enter the control law?** A readout-mode task
   wants `Ω² ≈ 0`. The current control law has no handle on it.
   Probably needs a second target scalar alongside the vertex target.

4. **Does the vertex-weight softmin capture phase coherence?**
   Distance-based weighting ignores relative phase between vertex
   modes. A phase-aware variant would weight vertices by complex
   amplitudes and take `|amplitude|²`, which would also let ECP
   express interference.

5. **How is a trajectory validated against real silicon data?**
   The correlations in the demo output (`r ≈ −0.99` for entanglement
   / spectral gap) are artefacts of the kernel construction, not of
   steered dynamics. A real validation needs measured trajectories
   with known correct correlation structure, and then a goodness-of-
   fit metric that the sim is calibrated against.

## 8. Immediate next actions

* [ ] Replace `VERTEX_POSITIONS` with coordinates fitted from
  attractor data.
* [ ] Swap the proportional controller for PID; measure how close
  the sim tracks a held vertex target.
* [ ] Wire `dominant_vertex` emission into `GEIS/octahedral_state.py`.
* [ ] Write `bridges/intersection/advanced_computation_rule.py` so
  the sim participates in RESONATE.
* [ ] Add per-regime figures of merit (point 2 above).
* [ ] Add an `Ω²` scalar observable and thread it through the
  control objective (point 3).
