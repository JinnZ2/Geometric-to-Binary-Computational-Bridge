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
