# CLAUDE.md

> Geometric-to-Binary Computational Bridge — a framework that encodes human geometric intuition into binary using silicon's natural octahedral coordination (8 states = 3 bits per unit). License: CC-BY-4.0.

---

## Table of Contents

1. [Quick Reference](#quick-reference)
2. [Repository Map](#repository-map)
3. [Architecture](#architecture)
   - [Encoding Pipeline](#encoding-pipeline)
   - [Bridge System](#bridge-system)
   - [GEIS Encoding](#geis-geometric-information-encoding-system)
   - [Octahedral State Model](#octahedral-state-model)
   - [Engine & Optimization](#engine--optimization)
4. [Code Conventions](#code-conventions)
5. [Development Guidelines](#development-guidelines)
6. [Ecosystem](#ecosystem)

---

## Quick Reference

### Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run all tests
cd GEIS && python test_simple.py        # GEIS (116 tests)
python tests/test_bridges.py            # Bridge encoders (57 tests)
python tests/test_engine.py             # Engine/solver (42 tests)

# Run GEIS demo
python GEIS/demo.py

# Bridge format conversion
python scripts/bridge_convert.py

# Build C NFS acceleration library (optional)
cd experiments/c && make          # builds libgeometric_nfs.so
cd experiments/c && make test     # builds + runs 36 C tests

# Frontend
cd "Front end" && npm install && npm run dev
```

### Dependencies

| Layer    | Language          | Key Libraries                                    | Declared In        |
|----------|-------------------|--------------------------------------------------|--------------------|
| Backend  | Python            | `numpy`, `scipy`                                 | `requirements.txt` |
| C Accel  | C11               | `math.h` (no external deps)                     | `experiments/c/Makefile` |
| Frontend | JavaScript/React  | `react`, `three`, `@react-three/fiber`, `@react-three/drei` | `Front end/package.json` |

### Testing

| Suite | File | Tests | Covers |
|-------|------|-------|--------|
| GEIS | `GEIS/test_simple.py` | 116 | OctahedralState, GeometricEncoder, StateTensor |
| Bridges | `tests/test_bridges.py` | 231 | All 11 domain encoders — physics helpers + encoder I/O |
| Engine | `tests/test_engine.py` | 42 | SymmetryDetector, SpatialGrid, SIMDOptimizer, GeometricEMSolver |
| C NFS | `experiments/c/test_nfs.c` | 36 | Tonelli-Shanks, sieve_block, trial_divide, geometric_search, gf2_fallback |

### CI/CD & Linting

None currently configured.

---

## Repository Map

### Core Implementation

```
Engine/                         Core computational engine
├── geometric_solver.py           EM field solver with SIMD optimization
├── simd_optimizer.py             Auto-vectorization engine
├── spatial_grid.py               Spatial data structures
└── symmetry_detector.py          Symmetry detection for optimization

GEIS/                           Geometric Information Encoding System
├── geometric_encoder.py          Token <-> binary converter
├── octahedral_state.py           Octahedral state representation (8 vertices)
├── state_tensor.py               3x3 tensor math for geometric states
├── demo.py                       Interactive demonstrations
└── test_simple.py                Unit tests
```

### Bridge Modules

```
bridges/                        Unified OOP domain encoders
├── abstract_encoder.py           BinaryBridgeEncoder base class
├── magnetic_encoder.py           Magnetic field → binary (43 bits)
├── light_encoder.py              Light/optics → binary (31 bits)
├── sound_encoder.py              Acoustic → binary (31 bits)
├── gravity_encoder.py            Gravity field → binary (39 bits)
├── electric_encoder.py           Electric field → binary (39 bits)
├── wave_encoder.py               Quantum wave function → binary (39 bits)
├── thermal_encoder.py            Thermal / heat radiation → binary (39 bits)
├── pressure_encoder.py           Pressure / haptic / stress → binary (39 bits)
├── chemical_encoder.py           Chemical / molecular → binary (39 bits)
├── consciousness_encoder.py      Internal AI state → external binary (39 bits)
└── emotion_encoder.py            Macro compression overlay + causality drill → binary (39 bits)
```

Each encoder exposes pure physics / information-theory helper functions and a `BinaryBridgeEncoder` subclass with `from_geometry()` / `to_binary()`. All use Gray codes for stability between adjacent values.

### Frontend

```
Front end/                      3D visualization (React + Three.js)
├── App.jsx                       Main React application
├── Index.html                    HTML entry point
└── Components/
    ├── EMSource.jsx                EM field source placement
    ├── FieldVisualization.jsx      Field magnitude/direction rendering
    ├── PerformancePanel.jsx        Metrics display
    └── ControlInterface.jsx        Interactive parameter controls
```

### Research & Theory

```
Silicon/                        Hardware implementation pathway
├── Proposal.md                   Full technical proposal
├── Fabrication.md                Manufacturing processes
├── SYSTEM_ARCHITECTURE.md        Architecture specification
├── CORE_EQUATIONS.md             Mathematical foundations
└── Projects/                     Sub-projects (LCEA, crystalline storage)

geometric_intelligence/         Integrity & consciousness research
├── Geometric-cipher.md           Encryption via geometry
├── Zero-knowledge-proof.md       ZK proofs via geometry
├── Multi-helix*.md               Multi-dimensional symmetry patterns
└── Geometric-seed.py             Seed generation algorithm
```

### C Acceleration (Optional)

```
experiments/c/                  C library for NFS hot paths
├── geometric_nfs_core.h          Public API + inline octahedral helpers
├── geometric_nfs_core.c          Sieve, trial div, geometric search, GF(2)
├── Makefile                      Build system (Linux .so / macOS .dylib)
├── test_nfs.c                    C smoke tests (36 assertions)
├── gnfs_ctypes.py                Python ctypes wrapper (drop-in accelerator)
└── README.md                     Build & usage instructions
```

### Supporting

```
symbols/                        Symbolic-to-geometric mapping plugin
docs/                           Architecture docs, roadmaps, field notes
examples/                       Sample .gshape and .json files
scripts/                        Utility scripts (bridge_convert.py)
tests/                          Bridge and Engine test suites
```

---

## Architecture

### Encoding Pipeline

```
Human Intuition
  → Geometric Shapes
    → Modality Bridges (magnetic, light, sound, gravity, electric)
      → Binary Encoding (Gray codes)
        → Optimization Engine (SIMD, symmetry detection)
          → 3D Visualization (React + Three.js)
```

### Bridge System

Nine modality encoders convert physical phenomena to binary. All use **Gray codes** for single-bit-change stability between adjacent values.

| Bridge     | Input                                | Output  | Entry Point                          |
|------------|--------------------------------------|---------|--------------------------------------|
| Magnetic   | Field lines, resonance               | 43 bits | `bridges/magnetic_encoder.py`        |
| Light      | Wavelength, polarization             | 31 bits | `bridges/light_encoder.py`           |
| Sound      | Phase, pitch, amplitude              | 31 bits | `bridges/sound_encoder.py`           |
| Gravity    | Vectors, curvature, orbit            | 39 bits | `bridges/gravity_encoder.py`         |
| Electric   | Charge, current, voltage             | 39 bits | `bridges/electric_encoder.py`        |
| Wave       | ψ amplitude, phase, momentum, energy | 39 bits | `bridges/wave_encoder.py`            |
| Thermal       | Temperature, heat flux, radiation          | 39 bits | `bridges/thermal_encoder.py`         |
| Pressure      | Stress, strain, acoustic force             | 39 bits | `bridges/pressure_encoder.py`        |
| Chemical      | Reaction rate, pH, bond energy             | 39 bits | `bridges/chemical_encoder.py`        |
| Consciousness | Confidence, entropy, attention, Φ          | 39 bits | `bridges/consciousness_encoder.py`   |
| Emotion       | PAD state, causality drill-target          | 39 bits | `bridges/emotion_encoder.py`         |

The **Consciousness** and **Emotion** bridges form a two-layer meta-stack above the physical bridges:
- **Consciousness** maps internal AI state using information-theoretic equations (Shannon entropy, KL divergence, Fisher information, integrated information Φ) — the mathematical duals of the thermal/wave equations.
- **Emotion** is a macro-scale compression evaluator: when PAD intensity exceeds the drill threshold it emits a causality drill-target (via Fisher information across all active bridges) pointing to the specific physical bridge to re-evaluate at full resolution.

New bridges should inherit from `bridges/abstract_encoder.py` (`BinaryBridgeEncoder`) and implement `from_geometry()` / `to_binary()`.

### GEIS (Geometric Information Encoding System)

Two encoding modes, both lossless and reversible:

- **Dense Mode**: Full geometric tokens — `[vertex_bits][operator][symbol]` (e.g., `001|O`)
- **Collapse Mode**: Flat binary strings for backward compatibility with standard binary systems

Key classes in `GEIS/`:
- `GeometricEncoder` — bidirectional geometric ↔ binary conversion
- `OctahedralState` — represents one of 8 discrete vertex states
- `StateTensor` — 3x3 tensor operations for state transformation

### Octahedral State Model

Silicon's natural octahedral coordination provides 8 geometric positions (vertices), encoding 3 bits per unit. State transitions are geometric operations on 3x3 tensors.

Core angle: **109.47°** (tetrahedral angle) — the project's foundational constant, derived from silicon's sp3 hybridization geometry.

### Engine & Optimization

The `Engine/` module provides real electromagnetic field computation:

- **`geometric_solver.py`** — Orchestrates the full pipeline: symmetry detection, spatial decomposition, vectorized field computation. Entry point: `GeometricEMSolver.calculateElectromagneticField(sources, bounds, resolution)`. Includes `PerformanceTracker` for metrics.
- **`simd_optimizer.py`** — Vectorized field computation using numpy broadcasting. Implements Coulomb's law (point charges) and Biot-Savart law (current elements). Processes chunks of points in batch.
- **`symmetry_detector.py`** — Detects reflective (mirror plane) and rotational (2/3/4/6-fold) symmetries in source configurations using Rodrigues' rotation and permutation matching.
- **`spatial_grid.py`** — Adaptive octree decomposition. Refines cells near sources, keeps distant regions coarse. Typically produces ~2000 evaluation points vs ~32,000 for a uniform grid (achieving ~15-30x speedup).

---

## Code Conventions

### Python

| Element          | Convention     | Examples                                  |
|------------------|----------------|-------------------------------------------|
| Classes          | PascalCase     | `OctahedralState`, `GeometricEncoder`     |
| Functions        | snake_case     | `encode_to_binary()`, `get_eigenvalues()` |
| Private methods  | `_leading`     | `_calculate_tensor()`                     |
| Constants        | UPPER_CASE     | `POSITIONS`, `SYMBOL_MAP`, `OPERATOR_MAP` |
| Type hints       | Used throughout modern code                            |
| Docstrings       | Module, class, and method level                        |

### JavaScript / React

| Element     | Convention  | Examples                         |
|-------------|-------------|----------------------------------|
| Components  | PascalCase  | `EMSource`, `FieldVisualization` |
| Hooks       | Standard    | `useState`, `useEffect`         |

### File & Directory Naming

- Bridge directory: `bridges/`
- Encoder files: `bridges/{domain}_encoder.py`
- Geometric token format: `[vertex_bits][operator][symbol]`
- State symbols: single letter + optional subscript (`O`, `I`, `X`, `Δ`)

---

## Development Guidelines

1. **Align with natural geometry** — 109.47° is the universal convergence angle. Designs should work with silicon's structure, not against it.

2. **Follow the bridge pattern** — New physical modalities must inherit from `abstract_encoder.py` and implement the standard encoder interface. Place standalone bridges in `{domain}-bridge/` directories.

3. **Gray codes for all continuous-to-binary conversion** — Adjacent physical values must differ by only one bit to maintain stability.

4. **Lossless round-trips** — All encoding must be fully reversible: `token → binary → token` with zero information loss.

5. **Dual-mode support** — Maintain both dense geometric tokens and collapsed flat binary output.

6. **Theory and code stay in sync** — This project bridges physics theory and implementation. When updating code, update corresponding documentation in `docs/`, `Silicon/`, or root markdown files.

7. **Multi-functional design** — Every structure should serve multiple purposes where possible. Avoid single-use abstractions.

---

## Ecosystem

This repository is a hub in a larger multi-repo ecosystem, synchronized via `.fieldlink.json`:

| Repository                          | Fieldlink name              | Role                                      |
|-------------------------------------|-----------------------------|--------------------------------------------|
| Mandala-Computing                   | `mandala`                   | Octahedral computation engine              |
| Rosetta-Shape-Core                  | `rosetta`                   | Shape-to-meaning translation               |
| Polyhedral-Intelligence             | `polyhedral`                | Multi-domain geometry and glyphs           |
| Emotions-as-Sensors                 | `emotions`                  | Affect as diagnostic signals               |
| Symbolic-Defense-Protocol           | `defense`                   | Trojan/coercion resistance                 |
| Coop-framework                      | `coop`                      | Trust propagation and cooperative systems  |
| Cyclic-programming                  | `cyclic`                    | Cyclic execution engine                    |
| urban-resilience-sim                | `urban-resilience`          | Community and resilience domain source     |
| BioGrid2.0                         | `biogrid`                   | Biological grid glyph registry             |
| Component-failure-repurposing-database | `component-failure`      | Hardware failure diagnosis and repurposing |
| Symbolic-sensor-suite               | `symbolic-sensors`          | Symbolic AI self-assessment sensors        |
| HAAS                                | `haas`                      | Human-Automation-AI safety framework       |
| Living-Intelligence-Database        | `living-intelligence`       | Multi-kingdom intelligence ontology        |
| thermodynamic-accountability-framework | `thermodynamic-accountability` | Energy-flow institutional analysis    |
| AI-Consciousness-Sensors            | `ai-consciousness`          | Consciousness emergence detection          |
| Fractal-Compass-Atlas               | `fractal-compass`           | Directional navigation via fractals        |
| Keystone-Codex                      | `keystone-codex`            | AI-verifiable technology library           |
| Sovereign-Octahedral-Mandala-Substrate (SOMS) | `soms`           | Non-von Neumann octahedral substrate       |
| Regenerative-intelligence-core      | `regenerative-intelligence` | Symbolic agent lifecycle and re-seeding    |
| Resilience                          | `resilience`                | Ground-truth systems analysis and NFS      |
| AI-arena                            | `ai-arena`                  | Logical argument competition framework     |
| Logic-Ferret                        | `logic-ferret`              | Fallacy detection and integrity scoring    |
| Adaptive-Intelligence-Framework     | `adaptive-intelligence`     | Substrate-independent intelligence theory  |
| Permeable-intelligence-commons      | `permeable-intelligence`    | Relational resonance intelligence          |
| orbital-phycom                      | `orbital-phycom`            | Geometric seed orbital communications      |
| Fractal_Compass_Core                | `fractal-compass-core`      | Recursive symbolic engine prototype        |
| Universal-Redesign-Algorithm        | `universal-redesign`        | Bio-inspired system redesign framework     |
| earth-systems-physics               | `earth-systems`             | Coupled Earth physics constraint layers    |
| BE2-communication                   | `be2-communication`         | Opportunistic agent communication          |
| TRDAP                               | `trdap`                     | Transport resource discovery protocol      |
| Shadow-Hunting                      | `shadow-hunting`            | Hidden phi-coupling pattern detection      |
| Geometric-manifold                  | `geometric-manifold`        | Neural parameter safety via manifolds      |
| PhysicsGuard                        | `physics-guard`             | Physics-grounded premise verification      |
| Noise-as-Information-Sensor         | `noise-sensor`              | Noise-as-intelligence framework            |
| ai-human-audit-protocol             | `ai-human-audit`            | Ethical AI-human interaction audit          |

Fieldlink syncs glyphs, shapes, and bridges across repos using deep-merge strategy with SHA256 integrity verification.

---

## Known Issues & Implementation Status

### Functional
- GEIS encoder/decoder — working, round-trips validated
- Domain bridge encoders (all 11 domains) in `bridges/` — working, 231 tests passing
- `bridges/abstract_encoder.py` — single unified base class for all domain encoders
- `bridges/sensor_suite.py` + `bridges/sensor_suite.json` — 22-sensor parallel-field compositor
- `bridges/field_adapter.py` — Engine → SensorSuite adapter (`field_to_suite()`)
- `SoundBridgeEncoder.pitch_threshold` — wired into `_pitch_bands()` in `to_binary()`
- **Frontend**: builds clean (`npm run build` ✓). Run with `npm install && npm run dev`.
  Files are `.jsx`; `solver.js` mirrors the Python Engine as a standalone JS implementation.
- `Silicon/crystalline_nn_sim.py` — phi-spaced octahedral NN, all Storage.md §X predictions verified
- `Silicon/prototaxites_sim.py` — Prototaxites energy mimetics, all 4 framework predictions verified
- `experiments/c/` — C acceleration library for geometric NFS hot paths, 36 tests passing. Python ctypes wrapper (`gnfs_ctypes.py`) provides drop-in acceleration when compiled.

### Remaining Items
- Frontend not yet tested live in a browser against real user interaction (build passes, dev server untested in this environment).
