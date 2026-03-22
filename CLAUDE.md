# CLAUDE.md — AI Assistant Guide

## Project Overview

**Geometric-to-Binary Computational Bridge** — A framework that bridges human geometric intuition with machine binary code generation. It uses silicon's natural octahedral coordination (109.47° tetrahedral angles, 8 geometric positions) to encode 3 bits per unit via geometric tensor states, enabling multi-state logic while maintaining binary compatibility.

**License**: CC-BY-4.0

## Repository Structure

```
Engine/                    # Core computational engine (Python)
  geometric_solver.py      #   EM field solver with SIMD optimization
  simd_optimizer.py        #   Auto-vectorization engine
  spacial_grid.py          #   Spatial data structures
  symmetry_detector.py     #   Symmetry detection for optimization

GEIS/                      # Geometric Information Encoding System (Python)
  geometric_encoder.py     #   Token <-> binary converter
  octahedral_state.py      #   Octahedral state representation (8 vertices)
  state_tensor.py          #   3x3 tensor math for geometric states
  demo.py                  #   Interactive demonstrations
  test_simple.py           #   Unit tests

Front end/                 # 3D visualization (React + Three.js)
  App.js                   #   Main React application
  Components/              #   EMSource, FieldVisualization, PerformancePanel, ControlInterface

src/bridge/                # Modular field encoders
  encode_binary.py         #   Unified binary encoding entry point
  common.py                #   Shared utilities (Gray codes)
  gravity.py, light.py, sound.py  # Domain-specific encoders

bridge/                    # Bridge orchestration
  bridge_orchestrator.py   #   Main bridge coordinator
  abstract_encoder.py      #   Abstract encoder base class

{magnetic,light,sound,gravity,electric}-bridge/
                           # Standalone domain-specific bridge modules

Silicon/                   # Hardware implementation specs & research
Geometric-Intelligence/    # Consciousness detection & integrity monitoring
symbols/                   # Symbolic-to-geometric mapping
docs/                      # Architecture docs, roadmaps, notes
examples/                  # Sample .gshape and .json files
scripts/                   # Utility scripts (bridge_convert.py)
```

## Languages & Dependencies

**Python** (primary backend):
- `numpy` — vector/tensor operations
- `scipy` — scientific computing
- No `requirements.txt` or `pyproject.toml` currently exists

**JavaScript/React** (frontend):
- `react`, `three`, `@react-three/fiber`, `@react-three/drei`
- No `package.json` currently committed

## Key Architecture

### Encoding Pipeline
```
Human Intuition → Geometric Shapes → Modality Bridges → Binary Encoding → Optimization → 3D Visualization
```

### Bridge System
Five modality encoders convert physical phenomena to binary:
- **Magnetic**: Polarity (N/S) → binary
- **Light**: Wavelength bands + chromaticity → binary via Gray codes
- **Sound**: Phase, pitch, amplitude → binary
- **Gravity**: Curvature, orbit stability → binary
- **Electric**: Charge polarity, current flow → binary

All bridges use Gray codes for stability. Unified interface: `encode(modality, features, target_bits)`.

### GEIS Dual-Mode Encoding
- **Dense Mode**: Full geometric tokens with operators and symbols
- **Collapse Mode**: Flat binary strings for backward compatibility
- Round-trip conversion is lossless

### Octahedral State Model
8 discrete states map to octahedral vertices. State transitions are geometric operations on 3x3 tensors. Key class hierarchy:
- `OctahedralState` — state representation
- `GeometricEncoder` — bidirectional geometric ↔ binary conversion
- `StateTensor` — tensor mathematics

## Coding Conventions

### Python
- **Classes**: PascalCase (`OctahedralState`, `GeometricEncoder`)
- **Functions/methods**: snake_case (`encode_to_binary()`, `get_eigenvalues()`)
- **Private methods**: leading underscore (`_calculate_tensor()`)
- **Constants**: UPPER_CASE (`POSITIONS`, `SYMBOL_MAP`)
- **Type hints**: used throughout modern code
- **Docstrings**: module, class, and method-level

### JavaScript/React
- **Components**: PascalCase (`EMSource`, `FieldVisualization`)
- **Hooks**: standard `useState`, `useEffect` patterns

### Naming Patterns
- Bridge modules: `{domain}-bridge/` directories
- Encoder files: `{domain}_encoder.py`
- Geometric tokens: `[vertex_bits][operator][symbol]` (e.g., `001|O`)

## Running Tests

```bash
cd GEIS && python test_simple.py
```

Tests validate:
- Encoder/decoder round-trip (token → binary → token)
- State vector calculations
- Geometric operation correctness

## Build & Run

No formal build system. Run Python modules directly:

```bash
# GEIS demo
python GEIS/demo.py

# Bridge conversion
python scripts/bridge_convert.py
```

Frontend (if dependencies installed):
```bash
cd "Front end" && npm start
```

## CI/CD & Linting

No CI/CD pipelines or linting configurations are currently set up.

## Related Repositories

This project is part of a larger ecosystem (see `.fieldlink.json`):
- Rosetta-Shape-Core, Polyhedral-Intelligence, Symbolic-Defense-Protocol
- Emotions-as-Sensors, AI-Consciousness-Sensors, Fractal-Compass-Atlas

## Development Guidelines

1. **Work with nature's geometry** — 109.47° is the universal convergence angle; designs should align with silicon's natural structure
2. **Modular bridges** — new physical modalities should follow the existing encoder pattern (inherit from `abstract_encoder.py`)
3. **Gray codes for stability** — always use Gray codes when encoding continuous physical values to binary
4. **Lossless round-trips** — any encoding must be reversible without information loss
5. **Dual-mode support** — maintain both dense geometric tokens and flat binary compatibility
6. **Document theory alongside code** — this project bridges physics theory and implementation; keep both in sync
