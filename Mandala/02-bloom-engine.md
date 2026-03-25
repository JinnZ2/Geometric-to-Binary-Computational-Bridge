# Bloom Engine — Radial Expansion Architecture

> **Status: Design intent.** The concept is coherent. The full implementation
> (`OctahedralBloomEngine`, `OctahedralSubstrate`) does not yet exist as runnable code.
> The topological layer described in §4 IS implemented — see `Silicon/`.

---

## 1. What the Bloom Engine Does

A symbol (seed state) placed at the centre of an octahedral grid expands outward
into a nested radial structure. Each concentric ring inherits state from the centre,
scaled by φ per layer. Rings couple back inward (reflection field).

```
Symbol Core (seed)
    ↓
Centre cell initialised to matching octahedral state
    ↓
Ring 1 (8 cells at radius r₁): states scaled by φ⁰ = 1
Ring 2 (8 cells at radius r₂): states scaled by φ¹
Ring 3 (8 cells at radius r₃): states scaled by φ²
    ...
    ↓
Navigation pathways: within-ring + cross-ring transitions
    ↓
Reflection field: outer rings couple back to centre
```

Each layer is accessible at a coupling strength `1/φ^layer` — weaker the further out,
preserving the information gradient.

---

## 2. Architectural Sketch

```python
class OctahedralBloomEngine:
    """
    Expands a symbol into a nested radial octahedral structure.
    OctahedralSubstrate is the missing dependency (not yet implemented).
    """

    def bloom(self, symbol_core: str, expansion_layers: int = 5):
        center_cell = self.substrate.n_cells // 2
        initial_state = self._encode_symbol(symbol_core)
        self.substrate.cells[center_cell]["state"] = initial_state

        structure = {"center": center_cell, "layers": []}

        for layer in range(expansion_layers):
            radius = (layer + 1) * 8       # 8 cells per ring (O_h symmetry)
            ring_cells = self._octahedral_ring(center_cell, radius)

            # Eigenvalues scale by φ per layer
            centre_ev = OCTAHEDRAL_EIGENVALUES[initial_state]
            scaled_ev = tuple(e * (PHI ** layer) for e in centre_ev)
            ring_state = nearest_octahedral_state(scaled_ev)

            for cell_id in ring_cells:
                self.substrate.cells[cell_id]["state"] = ring_state
                self.substrate.couple(
                    center_cell, cell_id,
                    strength=1.0 / (PHI ** layer)
                )

            structure["layers"].append({
                "layer": layer,
                "radius": radius,
                "cells": ring_cells,
                "coupling": 1.0 / (PHI ** layer),
            })

        return structure

    def _octahedral_ring(self, center, radius):
        """
        8 cells at O_h vertex positions scaled to given radius.
        Uses the 6 octahedral vertices + 2 diagonal midpoints for 8-fold symmetry.
        """
        directions = [
            ( 1,  0,  0), (-1,  0,  0),
            ( 0,  1,  0), ( 0, -1,  0),
            ( 0,  0,  1), ( 0,  0, -1),
            ( 1,  1,  0), (-1, -1,  0),
        ]
        return [
            self.substrate.cell_at(center, *(radius * np.array(d)))
            for d in directions
        ]
```

**What's missing:** `OctahedralSubstrate` — the spatial grid of cells with coupling
and state storage. The `Engine/spatial_grid.py` (`SpatialGrid`) is the closest
existing component; wiring it into a bloom topology is Phase 1 work.

---

## 3. Navigation Layer

Within the bloomed structure, three pathway types exist:

| Pathway | Cells | Transition cost |
|---------|-------|----------------|
| Same-ring | Adjacent in ring (8-fold) | Low — same coupling radius |
| Inward | Ring N → Ring N-1 → centre | Medium — crosses φ-scaled boundary |
| Outward | Ring N → Ring N+1 | High — moves away from seed information |

Navigation is defined by O_h symmetry: only transitions along allowed 12 edges
(face-adjacent vertices) are single-step. Diagonal transitions are two-step.

```python
# Allowed single-step transitions (12 edges of octahedron)
ALLOWED_TRANSITIONS = {
    0: [2, 3, 4, 5],   # +x → ±y, ±z
    1: [2, 3, 4, 5],   # -x → ±y, ±z
    2: [0, 1, 4, 5],   # +y → ±x, ±z
    3: [0, 1, 4, 5],   # -y → ±x, ±z
    4: [0, 1, 2, 3],   # +z → ±x, ±y
    5: [0, 1, 2, 3],   # -z → ±x, ±y
    6: [0, 2, 4, 7],   # diagonal → neighbours
    7: [1, 3, 5, 6],   # diagonal → neighbours
}
```

---

## 4. Topological Layer (Implemented)

The mandala's "Reflection Field" — the mechanism that makes the bloom structure
self-referential and error-resistant — is now concretely implemented as
**topological memory via vortex-antivortex dipoles**.

Key finding from `Silicon/vortex_attention_heads.py`:

> Topological **charge** (winding number ±1) is invariant under smooth phi deformation.
> Topological **position** (where that charge sits) is a free collective coordinate — it drifts.
> The correct design anchors computation to a **registry** recorded at write-time.

Applied to the bloom engine:

```
Traditional bloom:         re-detect ring positions each step  ← drifts
Registry-locked bloom:     record ring positions at bloom time  ← stable

at bloom():
    for each ring_cell:
        registry[cell_id] = {"winding": +1, "x": xc, "y": yc}  ← written once

at read():
    use registry[cell_id]["x"], registry[cell_id]["y"]          ← never re-detected
```

This is precisely what `VortexMemory` implements for bit storage:

```python
# Silicon/topological_memory.py
from Silicon.topological_memory import VortexMemory

memory = VortexMemory(grid_size=40, min_separation=5)
memory.write(0, value=1)   # injects vortex, records position in registry
memory.update(steps=500)   # gradient descent — winding number preserved
bit = memory.read(0)       # reads from registry, not from winding field re-scan
```

The bloom engine's reflection field is the multi-cell extension of this:
each ring cell has a registered topological address that survives gradient updates.

---

## 5. Example: Encoding F = ma

```python
engine = OctahedralBloomEngine(substrate)
structure = engine.bloom("F=ma", expansion_layers=3)

# Layer 0 (centre): F=ma encoded as state 3 (elongated +z)
# Layer 1 (8 cells, coupling=1.0): F, m, a, force_type,
#                                   mass_type, accel_type, units, ref_frame
# Layer 2 (8 cells, coupling=0.618): vector_components, Newton's law,
#                                    conservation, relativity, quantum, ...
# Layer 3 (8 cells, coupling=0.382): applications, edge_cases, derivations, ...
```

Querying the structure means navigating from a ring cell inward toward the centre
along allowed O_h transitions — following the coupling gradient toward the seed state.

---

## 6. Implementation Gap Summary

| Component | Exists | File |
|-----------|--------|------|
| 8-state octahedral unit | Yes | `GEIS/octahedral_state.py` |
| Spatial grid (adaptive octree) | Yes | `Engine/spatial_grid.py` |
| Topological registry | Yes | `Silicon/topological_memory.py` |
| Radial ring topology (bloom) | No | Needs `OctahedralSubstrate` class |
| Cross-ring navigation | No | Needs pathway graph on top of `SpatialGrid` |
| Bloom + topological registry | No | Merge of above two |

Phase 1 work: wire `SpatialGrid` into a bloom topology, add registry-based
position locking from `VortexMemory`, expose `bloom()` / `navigate_to()` API.

---

*Next: [`03-theoretical.md`](03-theoretical.md) — P=NP, consciousness, physical constants.*
