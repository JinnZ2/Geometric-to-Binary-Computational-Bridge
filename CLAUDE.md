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
# Run tests
cd GEIS && python test_simple.py

# Run GEIS demo
python GEIS/demo.py

# Bridge format conversion
python scripts/bridge_convert.py

# Frontend (requires npm dependencies)
cd "Front end" && npm start
```

### Dependencies

| Layer    | Language          | Key Libraries                                    |
|----------|-------------------|--------------------------------------------------|
| Backend  | Python            | `numpy`, `scipy`                                 |
| Frontend | JavaScript/React  | `react`, `three`, `@react-three/fiber`, `@react-three/drei` |

No `requirements.txt`, `pyproject.toml`, or `package.json` is currently committed.

### Testing

Tests live in `GEIS/test_simple.py`. No formal test runner (pytest/unittest) is configured. Tests validate encoder/decoder round-trips, state vector calculations, and geometric operation correctness.

### CI/CD & Linting

None currently configured.

---

## Repository Map

### Core Implementation

```
Engine/                         Core computational engine
├── geometric_solver.py           EM field solver with SIMD optimization
├── simd_optimizer.py             Auto-vectorization engine
├── spacial_grid.py               Spatial data structures
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
bridge/                         Orchestration layer
├── bridge_orchestrator.py        Main coordinator
├── abstract_encoder.py           Base class for all encoders
└── addendum_entropy_analyzer.py  Entropy calculations

src/bridge/                     Modular field encoders (unified)
├── encode_binary.py              Unified entry point
├── common.py                     Shared utilities (Gray codes)
├── gravity.py                    Gravity field encoding
├── light.py                      Light spectrum encoding
└── sound.py                      Sound/vibration encoding

magnetic-bridge/                Standalone domain bridges
light-bridge/                     Each contains a {domain}_encoder.py
sound-bridge/                     with domain-specific encoding logic
gravity-bridge/
electric-bridge/
```

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

Five modality encoders convert physical phenomena to binary. All use **Gray codes** for single-bit-change stability between adjacent values.

| Bridge     | Input                     | Encoding Strategy          | Entry Point                      |
|------------|---------------------------|----------------------------|----------------------------------|
| Magnetic   | Polarity (N/S)            | Direct binary mapping      | `magnetic-bridge/magnetic_encoder.py` |
| Light      | Wavelength + chromaticity | SPD → Gray-coded bands     | `light-bridge/light_encoder.py`  |
| Sound      | Phase, pitch, amplitude   | Temporal pattern analysis  | `sound-bridge/sound_encoder.py`  |
| Gravity    | Curvature, orbit params   | Stability curve mapping    | `gravity-bridge/gravity_encoder.py` |
| Electric   | Charge, current flow      | Polarity + magnitude       | `electric-bridge/electric_encoder.py` |

**Unified interface** (in `src/bridge/encode_binary.py`): `encode(modality, features, target_bits)`

New bridges should inherit from `bridge/abstract_encoder.py`.

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

The `Engine/` module provides computational acceleration:

- **`geometric_solver.py`** — Solves EM field equations with geometry-aware optimizations
- **`simd_optimizer.py`** — Automatically vectorizes operations using SIMD instructions
- **`symmetry_detector.py`** — Detects exploitable symmetries to reduce computation (100–1000x speedups)
- **`spacial_grid.py`** — Spatial indexing structures for field calculations

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

- Bridge directories: `{domain}-bridge/`
- Encoder files: `{domain}_encoder.py`
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
