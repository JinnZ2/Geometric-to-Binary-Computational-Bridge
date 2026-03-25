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

# Frontend
cd "Front end" && npm install && npm run dev
```

### Dependencies

| Layer    | Language          | Key Libraries                                    | Declared In        |
|----------|-------------------|--------------------------------------------------|--------------------|
| Backend  | Python            | `numpy`, `scipy`                                 | `requirements.txt` |
| Frontend | JavaScript/React  | `react`, `three`, `@react-three/fiber`, `@react-three/drei` | `Front end/package.json` |

### Testing

| Suite | File | Tests | Covers |
|-------|------|-------|--------|
| GEIS | `GEIS/test_simple.py` | 116 | OctahedralState, GeometricEncoder, StateTensor |
| Bridges | `tests/test_bridges.py` | 121 | All 6 domain encoders — physics helpers + encoder I/O |
| Engine | `tests/test_engine.py` | 42 | SymmetryDetector, SpatialGrid, SIMDOptimizer, GeometricEMSolver |

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
└── wave_encoder.py               Quantum wave function → binary (39 bits)
```

Each encoder exposes pure physics helper functions and a `BinaryBridgeEncoder` subclass with `from_geometry()` / `to_binary()`. All use Gray codes for stability between adjacent values.

### Frontend

```
Front end/                      3D visualization (React + Three.js)
├── App.js                        Main React application
├── Index.html                    HTML entry point
└── Components/
    ├── EMSource.js                 EM field source placement
    ├── FieldVisualization.js       Field magnitude/direction rendering
    ├── PerformancePanel.js         Metrics display
    └── ControlInterface.js         Interactive parameter controls
```

### Research & Theory

```
Silicon/                        Hardware implementation pathway
├── Proposal.md                   Full technical proposal
├── Fabrication.md                Manufacturing processes
├── SYSTEM_ARCHITECTURE.md        Architecture specification
├── CORE_EQUATIONS.md             Mathematical foundations
└── Projects/                     Sub-projects (LCEA, crystalline storage)

Geometric-Intelligence/         Integrity & consciousness research
├── Geometric-cipher.md           Encryption via geometry
├── Zero-knowledge-proof.md       ZK proofs via geometry
├── Multi-helix*.md               Multi-dimensional symmetry patterns
└── Geometric-seed.py             Seed generation algorithm
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

Six modality encoders convert physical phenomena to binary. All use **Gray codes** for single-bit-change stability between adjacent values.

| Bridge     | Input                                | Output  | Entry Point                          |
|------------|--------------------------------------|---------|--------------------------------------|
| Magnetic   | Field lines, resonance               | 43 bits | `bridges/magnetic_encoder.py`        |
| Light      | Wavelength, polarization             | 31 bits | `bridges/light_encoder.py`           |
| Sound      | Phase, pitch, amplitude              | 31 bits | `bridges/sound_encoder.py`           |
| Gravity    | Vectors, curvature, orbit            | 39 bits | `bridges/gravity_encoder.py`         |
| Electric   | Charge, current, voltage             | 39 bits | `bridges/electric_encoder.py`        |
| Wave       | ψ amplitude, phase, momentum, energy | 39 bits | `bridges/wave_encoder.py`            |

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

| Repository                   | Role                                    |
|------------------------------|-----------------------------------------|
| Rosetta-Shape-Core           | Shape-to-meaning translation            |
| Polyhedral-Intelligence      | Multi-domain geometry and glyphs        |
| Symbolic-Defense-Protocol    | Trojan/coercion resistance              |
| Emotions-as-Sensors          | Affect as diagnostic signals            |
| AI-Consciousness-Sensors     | Consciousness emergence detection       |
| Fractal-Compass-Atlas        | Directional navigation via fractals     |

Fieldlink syncs glyphs, shapes, and bridges across repos using deep-merge strategy with SHA256 integrity verification.

---

## Known Issues & Implementation Status

### Functional
- GEIS encoder/decoder — working, round-trips validated
- Domain bridge encoders (magnetic, light, sound, gravity, electric) in `bridges/` — working, 98 tests passing
- `bridges/abstract_encoder.py` — single unified base class for all domain encoders

### Remaining Items
- **`SoundBridgeEncoder.pitch_threshold`** is stored but not yet wired into the frequency-band encoding logic.
- **Frontend**: Has `package.json` and Vite config but hasn't been tested end-to-end with `npm install && npm run dev`. The JS solver (`Front end/solver.js`) mirrors the Python Engine but is a separate implementation.
