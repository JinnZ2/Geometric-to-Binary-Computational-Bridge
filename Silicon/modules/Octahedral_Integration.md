# Octahedral Integration (In Progress)

This document outlines the planned integration between the static octahedral encoding of computation and the continuous dynamical silicon manifold system implemented in the `Silicon/modules` package.

## Current State vs. Integrated Vision

Currently, the two models operate as separate conceptual layers:
- **Octahedral encoding:** A static decomposition of computation into three discrete components: geometry, fiber, and projection.
- **Silicon dynamics:** An evolving state manifold `S(t) = (n, d, ℓ, κ)` that generates a kernel `W(x,x')` and computation output `y(x)`.

**After integration:**
- The silicon state `S(t)` becomes the fiber in the octahedral decomposition.
- The geometry field `φ(x)` serves as the base manifold.
- The continuous kernel `W(x,x')` acts as the projection operator.
- The entire system evolves as a single, unified bundle, eliminating the separation between layers.

Crucially, the octahedral encoding stops being a fixed, static frame and transforms into a **dynamical section of the bundle**.

---

## Mapping Points

The integration relies on a direct structural correspondence between the octahedral components and the dynamical counterparts in the silicon model.

| Octahedral Component | Dynamical Counterpart | Integration Mechanism |
|---|---|---|
| Base manifold | Geometry fields `φ(x)`, `ψ(x)` | Already shared across models. |
| Fiber | Silicon state `S = (n, μ, T, d_bulk, d_iface, ℓ, κ₁, κ₂, κ₃)` | Direct substitution of the static fiber with the evolving 9D state vector. |
| Projection | Kernel `W(x,x')` | Replaces the static encoding matrix with the state-dependent spatial kernel. |
| Phase structure | Regime atlas `(Λ, d, σ, χ)` | The static encoding becomes regime-dependent based on the continuous classifier. |
| Signature | `Ω²(x)` | Determines the fiber metric signature (Riemannian vs. Lorentzian). |

---

## Minimal Integration Steps

The integration will proceed through four targeted steps to replace static constructs with their dynamical equivalents.

### Step 1: Replace the Fiber
Replace the abstract octahedral fiber with the silicon state `S` directly. The 9D state vector that is already evolving on the manifold becomes the explicit fiber coordinates in the encoding. No new structural framework is needed.

### Step 2: Make the Projection Dynamical
Instead of a fixed decomposition matrix, the encoding projection becomes dynamical. Use `W(x,x')` from the silicon kernel. The encoding at time `t` is defined as `E(t) = f(W(t), geometry(t))`.

### Step 3: Barycentric Regime Weights
The eight octahedral vertices correspond to extremal points in the `(n, d, ℓ, κ)` state space. The trajectory's position relative to those vertices determines which computational regime is active. The continuous regime weights currently computed by the `RegimeAtlas` become the **barycentric coordinates** within the octahedron.

### Step 4: Face Transitions via Signature
The signature transition boundary `Ω² = 0` becomes a **face transition** in the octahedral decomposition. Crossing this boundary (from positive-definite Riemannian to indefinite Lorentzian) changes which vertices are accessible to the system, rather than just shifting which ones are currently active.

---

## What This Unlocks

Integrating the octahedral encoding with the continuous silicon dynamics yields four major theoretical and functional advantages:

- **Continuous octahedral encoding:** There is no longer any discrete switching between vertices. The system interpolates smoothly through the interior of the octahedron based on the continuous evolution of `S(t)`.
- **Regime-aware decomposition:** The encoding structurally adapts to the active regime. It operates differently in the linear/QM regime versus the solitonic or entangled regimes because the underlying kernel `W(x,x')` changes its structural properties.
- **Dynamical vertex significance:** The eight vertices of the octahedron are no longer equally weighted or statically relevant. They possess time-dependent significance based on the trajectory's current attractor basin.
- **Feedback closure:** The loop is fully closed. Computation output `y(x)` reshapes the silicon state `S`, which in turn moves the octahedral encoding, which subsequently alters the computation. The encoding co-evolves with the process it encodes.
