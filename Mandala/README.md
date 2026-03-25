# Mandala Computing — Octahedral Substrate

> **Mandala Computing** (symbolic framework) and **Octahedral Silicon Substrate** (physical implementation) are two views of the same geometric intelligence system.

This folder organises that mapping honestly — separating what is grounded from what is theoretical, and what is aspirational.

---

## Navigation

| File | What it contains | Confidence |
|------|-----------------|------------|
| [`01-octahedral-mapping.md`](01-octahedral-mapping.md) | O_h symmetry ↔ 8 petals, 3 bits/unit, Gray codes, eigenvalue table | **Grounded** |
| [`02-bloom-engine.md`](02-bloom-engine.md) | Radial expansion architecture, topological attention connection | **Design** |
| [`03-theoretical.md`](03-theoretical.md) | P=NP via relaxation, consciousness Φ, physical constants — with honest caveats | **Speculative** |
| [`04-roadmap.md`](04-roadmap.md) | Implementation phases, updated code examples matching actual repo | **Aspirational** |
| [`05-physics-connections.md`](05-physics-connections.md) | Real physics unifying all layers: MH↔KT, FRET↔Coulomb, Berry phase↔winding, qudit-octit | **Physics** |

---

## What Exists Right Now

| Component | File | Status |
|-----------|------|--------|
| 8-state octahedral encoder | `GEIS/octahedral_state.py` | Working |
| Gray-coded eigenvalue table | `Silicon/octahedral_sim.py` | Working |
| Topological memory (vortex bits) | `Silicon/topological_memory.py` | Working, 8-bit round-trip verified |
| Topological attention heads | `Silicon/vortex_attention_heads.py` | Working |
| Domain bridge encoders (11) | `bridges/` | Working, 231 tests passing |
| EM field engine + SIMD | `Engine/` | Working, 42 tests passing |
| Berry phase / winding number | `Silicon/vortex_phase_learning.py` | Working — KT physics emergent |

---

## Core Claim (Grounded)

Silicon's natural octahedral coordination provides **8 discrete states** (O_h symmetry group).
8 states = 3 bits per unit.
State transitions are operations on 3×3 tensors.
The foundational angle is **109.47°** (sp3 tetrahedral hybridisation).

This is not speculative. It is the geometry of the silicon crystal.

---

## What Connects Mandala ↔ Octahedral (Summary)

| Mandala Concept | Octahedral Reality | Grounded? |
|-----------------|--------------------|-----------|
| 8 Sacred Petals | 8 O_h vertex states | Yes |
| Golden Ratio φ | Fibonacci eigenvalue ratios (minimum strain) | Partially — needs DFT verification |
| Fractal Depth | Multi-cell FRET-like coupling | Design intent |
| Bloom Engine | Radial tensor expansion | Design intent |
| Navigation Layer | Berry phase / winding number pathways | Now implemented — `Silicon/` |
| Reflection Field | Topological protection (winding invariant) | Now implemented — `Silicon/topological_memory.py` |
| Consciousness Φ | IIT integrated information | Theoretical — Φ computation is NP-hard |
| P=NP via relaxation | Ground-state energy minimisation | Overclaimed — see `03-theoretical.md` |

---

## Key Physical Insight (from vortex work)

Topological **charge** (winding number ±1) is invariant under smooth deformation.
Topological **position** (where that charge sits) is NOT — it is a free collective coordinate.

The correct design anchors attention/computation to a **registry** of positions recorded at write-time,
not re-detected each step. This is exactly what `VortexMemory` implements.

This is the concrete realisation of the mandala "Reflection Field" concept.

---

*Original file: `Mandala-octahedral.md` (root) — superseded by this folder.*
