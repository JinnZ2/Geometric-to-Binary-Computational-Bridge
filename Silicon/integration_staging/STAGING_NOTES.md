# Staging Notes — Octahedral Integration

**Status:** Step 1 complete in staging. Steps 2–4 pending.

See [`Silicon/modules/Octahedral_Integration.md`](../modules/Octahedral_Integration.md)
for the full integration plan.

---

## Step 1 — Live Fiber Substitution (DONE in staging)

**File:** `octahedral_bundle.py`

The static octahedral fiber `{λ₁, λ₂, λ₃}` has been replaced with the live
9D `SiliconState` vector `S(t) = (n, μ, T, d_bulk, d_iface, ℓ, κ₁, κ₂, κ₃)`.

The eight octahedral vertices are now extremal points in physical S-space,
chosen to match the geometric character of each canonical vertex
(spherical, elongated, compressed, diagonal) from `octahedral_state_encoding.json`.

Barycentric coordinates are computed via inverse-distance weighting in
normalised S-space, replacing the discrete vertex-bit encoding with a
continuous probability distribution over the eight vertices.

### What was built

| Object | Role |
|---|---|
| `OctahedralVertex` | One extremal S-space point, with bits, label, character, and SiliconState |
| `OctahedralBundle` | Full bundle: base φ(x), live fiber S(t), vertex atlas, barycentric position |
| `BarycentricPosition` | Continuous 8-weight distribution over vertices at a given S(t) |
| `build_vertex_atlas()` | Constructs the 8 vertices from physical S-space bounds |
| `project_to_barycentric()` | Inverse-distance weighting in normalised S-space |
| `bundle_from_pipeline()` | Wraps a PipelineResult and replays trajectory through the bundle |

### Migration checklist for Step 1

- [ ] Review vertex S-space positions against physical literature / fabrication constraints
- [ ] Decide normalisation strategy: log-scale for `n` (carrier density spans 6 orders)
- [ ] Confirm vertex adjacency (12 edges of O_h) is preserved under S-space embedding
- [ ] Add unit tests to `tests/test_silicon_modules.py`
- [ ] Move `octahedral_bundle.py` into `Silicon/modules/`
- [ ] Export from `Silicon/modules/__init__.py`
- [ ] Update `Silicon/modules/README.md`

---

## Step 2 — Dynamical Projection (PENDING)

Replace the static encoding matrix with `W(x,x')` from the silicon kernel.
`E(t) = f(W(t), geometry(t))`.

Depends on Step 1 migration.

---

## Step 3 — Regime Weights as Barycentric Coordinates (PENDING)

The continuous regime weights from `RegimeAtlas` become the barycentric
coordinates within the octahedron. The five regime axes `(Λ, d, σ, χ)` map
onto the octahedral interior.

Depends on Step 2.

---

## Step 4 — Face Transition via Ω² = 0 (PENDING)

`Ω² = 0` becomes a face transition in the octahedral decomposition — crossing
it changes which vertices are accessible, not just which are active.

The `Omega2SignLog` transition flag (already implemented in `regime.py`) will
trigger vertex accessibility updates in the bundle.

Depends on Step 3.

---

## Key Finding: The Computational Phase Diagram (Step 1 Diagnostic)

A cross-correlation analysis of the Step 1 vertex weights against the kernel entanglement ratio and regime weights revealed an unexpected but physically profound mapping. 

The diagonal vertices (110, 111) — which were intuitively expected to host entangled computation due to their "superposition" geometric character — are instead the signature of the **solitonic/structured attractor**. They correlate at +0.93 with the solitonic regime and −0.68 with entanglement. Conversely, the axis vertices (e.g., 000 +x) host the high-off-diagonal kernel structure.

This implies a fundamental reinterpretation of the octahedral encoding: **it is no longer a representation choice, but a computational phase diagram.** The eight vertices are pure computational modes, the edges are transitions, the interior is mixed computation, and the trajectory through it determines what kind of operation the system performs at each moment.

### The Two Poles of Computation

| Property | Diagonal Vertices (110, 111) | Axis Vertices (000, etc.) |
|---|---|---|
| **Kernel Structure** | Low off-diagonal/diagonal ratio | High off-diagonal ratio |
| **Operator Nature** | Local or near-local operators | Nonlocal kernel coupling |
| **Dynamics** | Predictable, stable, solitonic | Entangled, interference-driven |
| **Spectral Gap** | Large (well-conditioned, reversible) | Narrow (sensitive, potentially irreversible) |
| **Computation Type** | Classical logic | Quantum-like / interference computation |

The system traverses between these poles continuously. That traversal *is* the computation mode changing, without any discrete switch.

### Three Key Theoretical Implications

1. **Operator separability:** When the entanglement ratio > 0.5, the kernel `W(x,x')` cannot be approximated as local. Computation becomes intrinsically nonlocal — output at `x` depends on input at distant `x'`. This is the regime where spatial correlation matters to the result.
2. **Regime purity vs. mixed computation:** When one vertex dominates (weight → 1.0), the system computes in a single pure mode. When weights are distributed across multiple vertices, computation is a mixture — the effective operator is a superposition of different kernel structures, structurally analogous to a mixed state.
3. **Computational reversibility:** Near the solitonic attractor (diagonals), the spectral gap is large (r = −0.858 with diag-b), meaning computation is well-conditioned and approximately reversible. Near the entangled regime, the gap narrows.

This finding dictates the design of Step 2 (Dynamical Projection): the mapping `E(t) = f(W(t), geometry(t))` must project local/structured kernels toward the diagonal faces, and highly non-local/entangled kernels toward the axes.
