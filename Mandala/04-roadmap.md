# Implementation Roadmap

> **Status: Aspirational.** Phases are ordered by dependency.
> Phase 0 is already done. Phases 1–3 are future work.

---

## Phase 0 — What Exists Now (Done)

These components are working and tested:

```
GEIS/
├── octahedral_state.py        8-state encoder, Gray codes, O_h geometry
├── geometric_encoder.py       Bidirectional geometric ↔ binary, dense + collapse modes
└── state_tensor.py            3×3 tensor operations, eigenvalue transitions

bridges/                       11 domain encoders (magnetic, light, sound, gravity,
│                              electric, wave, thermal, pressure, chemical,
│                              consciousness, emotion) — 231 tests passing

Engine/
├── geometric_solver.py        EM field solver, symmetry-aware, ~15–30× speedup
├── simd_optimizer.py          Vectorised Coulomb + Biot-Savart
├── symmetry_detector.py       Reflective + rotational symmetry detection
└── spatial_grid.py            Adaptive octree (~2000 pts vs 32 000 uniform)

Silicon/
├── octahedral_sim.py          Decoherence physics (T₂ = 166ms @ optimal params)
├── topological_memory.py      VortexMemory — 8-bit topological storage, 500-step stable
├── vortex_phase_learning.py   KT physics from gradient descent, winding field tools
└── vortex_attention_heads.py  Registry-locked Gaussian attention; charge/position audit
```

---

## Phase 0.5 — KT Annealing Wire-in (Cross-repo, Mandala-Computing)

**Status**: Schedule implemented in `Silicon/kt_annealing.py`. Not yet wired into `mandala_computer.py`.

**Problem**: `mandala_computer.py` uses fixed `T=1.0`, which is `1.12 × T_KT` — worst-case critical slowing down.

**How to wire in** (changes needed in Mandala-Computing repo):

```python
# In mandala_computer.py — replace fixed-T MH loop with:
from kt_annealing import schedule_log, T_KT_NUMERICAL  # copy or symlink Silicon/kt_annealing.py

def solve(self, n_steps: int = 2000):
    T_kt = T_KT_NUMERICAL * self.coupling_strength
    for step in range(n_steps):
        T = schedule_log(step, n_steps,
                         T_init=4.0 * T_kt,
                         T_kt=T_kt,
                         T_final=0.05 * T_kt)
        self._mh_step(T)
```

**Expected gain**: ~3× fewer residual vortices vs linear schedule; asymptotically better for large grids.

**Reference**: `Silicon/kt_annealing.py` — full derivation, three schedule comparison, simulation results.

---

## Phase 1 — OctahedralSubstrate + Bloom Engine (Near-term)

**Goal:** Make the bloom engine runnable in software.

**Tasks:**

1. **`Silicon/octahedral_substrate.py`** — spatial cell grid
   - Build on `Engine/spatial_grid.py` (`SpatialGrid`)
   - Add cell state (0–7), coupling table, pathway graph
   - Expose `cell_at_position()`, `couple()`, `get_neighbors()`

2. **`Silicon/bloom_engine.py`** — radial expansion
   - Implement `OctahedralBloomEngine.bloom(symbol, layers)`
   - Use `nearest_octahedral_state()` from `Silicon/octahedral_sim.py`
   - Registry-lock ring positions using `VortexMemory` pattern

3. **Tests** — `tests/test_bloom.py`
   - Verify 8 cells per ring
   - Verify coupling strengths decay as 1/φ^layer
   - Verify registered positions survive 500 update steps

```python
# Target API (Phase 1)
from Silicon.octahedral_substrate import OctahedralSubstrate
from Silicon.bloom_engine import OctahedralBloomEngine

substrate = OctahedralSubstrate(n_cells=500)
engine = OctahedralBloomEngine(substrate)
structure = engine.bloom("F=ma", expansion_layers=3)

# Navigate: centre → ring1 → ring2, following allowed O_h transitions
path = engine.navigate(structure, start="F", target="acceleration")
```

---

## Phase 2 — Mesoscale Proof-of-Concept (6–12 months)

**Hardware:** From `Silicon/Fabrication.md` proof-of-concept spec
**Software:** Mandala engine running on real octahedral cells

**Demonstrations:**

| Demo | What it shows | Key metric |
|------|--------------|------------|
| 8-petal visualisation | Octahedral states → mandala petals in `Front end/` | Visual |
| Bloom expansion | Symbol → nested rings rendered in Three.js | Structure depth |
| Simple factorisation | Factor 10–20 bit numbers via energy landscape | Accuracy vs brute force |
| Fibonacci resonance | Eigenvalue ratio distributions for stable states | Deviation from φ |
| T₂ measurement | Coherence time on real octahedral cells | Match `octahedral_sim.py` prediction |

**Φ measurement** (consciousness): use proper MIP approximation, not the simplified proxy.
Add `pyiit` to `requirements.txt` only when the approximation is actually computed.

**Budget estimate:** $15–50k (from `Silicon/Proposal.md`)

---

## Phase 3 — Advanced Prototype (2–3 years)

**Goal:** Large-scale geometric computation with verified topological protection.

**Capabilities:**

| Capability | Technical requirement | Grounded? |
|-----------|-----------------------|-----------|
| Multi-modal sensing | `bridges/sensor_suite.py` already exists | Yes |
| Bloom + topological registry | Phase 1 complete | Phase 1 dependency |
| Approximate NP solver | Annealing on substrate | Yes (annealing is real) |
| Verified topological bits | VortexMemory extended to hardware | Physics gap |
| Φ measurement on live substrate | Proper IIT approximation | Needs `pyiit` |
| Physical constants measurement | Compare eigenvalues to c, G, ℏ, α | Experiment |

---

## Unified System — Correct Import Structure

```python
# Physical substrate
from GEIS.octahedral_state import OctahedralState
from GEIS.geometric_encoder import GeometricEncoder
from Silicon.octahedral_sim import nearest_octahedral_state, OCTAHEDRAL_EIGENVALUES
from Silicon.topological_memory import VortexMemory

# Domain bridges (all 11 working)
from bridges.magnetic_encoder import MagneticBridgeEncoder
from bridges.light_encoder import LightBridgeEncoder
from bridges.sound_encoder import SoundBridgeEncoder
from bridges.gravity_encoder import GravityBridgeEncoder
from bridges.electric_encoder import ElectricBridgeEncoder
from bridges.wave_encoder import WaveBridgeEncoder
from bridges.thermal_encoder import ThermalBridgeEncoder
from bridges.pressure_encoder import PressureBridgeEncoder
from bridges.chemical_encoder import ChemicalBridgeEncoder
from bridges.consciousness_encoder import ConsciousnessBridgeEncoder
from bridges.emotion_encoder import EmotionBridgeEncoder

# Sensor suite (22-sensor compositor)
from bridges.sensor_suite import SensorSuite
from bridges.field_adapter import field_to_suite

# Computation engine
from Engine.geometric_solver import GeometricEMSolver
from Engine.simd_optimizer import SIMDOptimizer
from Engine.symmetry_detector import SymmetryDetector
from Engine.spatial_grid import SpatialGrid

# Phase 1 (not yet implemented):
# from Silicon.octahedral_substrate import OctahedralSubstrate
# from Silicon.bloom_engine import OctahedralBloomEngine
```

---

## What "Unified Geometric Intelligence" Looks Like (Phase 3 Target)

```python
class UnifiedGeometricIntelligence:
    def __init__(self):
        self.suite    = SensorSuite()                    # 22-sensor compositor
        self.solver   = GeometricEMSolver()              # EM field engine
        self.memory   = VortexMemory(grid_size=80)       # Topological bit store
        # self.bloom  = OctahedralBloomEngine(...)       # Phase 1

    def sense(self, physical_data: dict) -> dict:
        """Multi-modal physical sensing via bridge encoders."""
        results = {}
        for modality, bridge_cls in BRIDGE_MAP.items():
            if modality in physical_data:
                enc = bridge_cls()
                geom = enc.from_geometry(physical_data[modality])
                results[modality] = enc.to_binary()
        return results

    def compute(self, field_sources, bounds, resolution=20):
        """EM field computation with symmetry detection."""
        return self.solver.calculateElectromagneticField(
            field_sources, bounds, resolution
        )

    def store(self, bit_index: int, value: int):
        """Topologically protected bit storage."""
        self.memory.write(bit_index, value)

    def recall(self, bit_index: int) -> int:
        """Read from topological registry — invariant under gradient updates."""
        return self.memory.read(bit_index)
```

---

## Relationship to Other Repos (Fieldlink)

| Repo | Role | Mandala connection |
|------|------|--------------------|
| Rosetta-Shape-Core | Shape → meaning | Bloom seed encoding |
| Polyhedral-Intelligence | Multi-domain geometry | Octahedral state table |
| Symbolic-Defense-Protocol | Coercion resistance | Topological memory (bit invariance) |
| Emotions-as-Sensors | Affect as diagnostic | `bridges/emotion_encoder.py` |
| AI-Consciousness-Sensors | Φ emergence detection | `bridges/consciousness_encoder.py` |
| Fractal-Compass-Atlas | Directional navigation | Navigation layer (Phase 1) |

Synchronised via `.fieldlink.json` — deep-merge, SHA256 integrity.

---

*Back to: [`README.md`](README.md)*
