# Ecosystem Dependency Graph

> 35 sibling repos connected via `.fieldlink.json`. This file shows what depends on what.

---

## Hub Repos (many connections)

```
Geometric-to-Binary-Computational-Bridge  ◄──►  Rosetta-Shape-Core
         │                                              │
         │  (octahedral states, GEIS encoding,          │  (shapes, ontology,
         │   bridge encoders, NFS sieve)                │   schema, bridges)
         │                                              │
         ├──► Mandala-Computing                         ├──► Polyhedral-Intelligence
         ├──► Emotions-as-Sensors                       ├──► BioGrid2.0
         ├──► Symbolic-Defense-Protocol                 ├──► Living-Intelligence-Database
         ├──► AI-Consciousness-Sensors                  └──► Fractal-Compass-Atlas
         ├──► Fractal-Compass-Atlas
         └──► SOMS
```

## Directed Dependencies (who consumes from whom)

### This repo EXPORTS to:
| Consumer | What it gets |
|----------|-------------|
| Mandala-Computing | `mappings/octahedral_state_encoding.json`, `Silicon/octahedral_state_encoder.json` |
| Rosetta-Shape-Core | `bridges/geobin-bridges.json`, `glyph_to_geometric_bridge.json`, `Silicon/fabrication_pathway_schema.json` |
| Coop-framework | `bridges/coop_encoder.py` |
| Cyclic-programming | `bridges/cyclic_encoder.py` |
| urban-resilience-sim | `bridges/community_encoder.py`, `bridges/resilience_encoder.py` |

### This repo IMPORTS from:
| Source | What it pulls | Local mount |
|--------|-------------|-------------|
| Mandala-Computing | shapes, glyphs, sensors | `atlas/remote/mandala/` |
| Rosetta-Shape-Core | bridges, shapes, ontology, schema | `atlas/remote/rosetta/` |
| BioGrid2.0 | glyph atlas, registry | `atlas/remote/biogrid/` |

### Leaf repos (inbound-only, this repo reads from them):
| Repo | What it provides |
|------|-----------------|
| Component-failure-repurposing-database | Hardware failure diagnosis, geometric monitoring |
| Resilience | Ground-truth systems analysis, octahedral-nfs |
| AI-arena | Logical argument competition, trust decay |
| Logic-Ferret | Fallacy detection, integrity scoring |
| Permeable-intelligence-commons | Relational resonance engine |
| orbital-phycom | Geometric seed orbital communications |
| Universal-Redesign-Algorithm | Bio-inspired system redesign |
| earth-systems-physics | Coupled Earth physics constraints |
| BE2-communication | Opportunistic agent communication |
| TRDAP | Transport resource discovery protocol |
| Noise-as-Information-Sensor | Noise-as-intelligence framework |
| PhysicsGuard | Physics-grounded premise verification |

### Bidirectional peers (shared entities):
| Repo | Shared concepts |
|------|----------------|
| HAAS | FELTSensor handshake protocol |
| AI-Consciousness-Sensors | Φ emergence, consciousness patterns |
| Fractal-Compass-Atlas | Bloom algorithm, glyph seeds |
| Fractal_Compass_Core | CDDA engine, symbolic recursion |
| Adaptive-Intelligence-Framework | Substrate-independent intelligence, ΔX test |
| Shadow-Hunting | Hidden phi-coupling detection |
| Geometric-manifold | Neural parameter safety manifolds |
| ai-human-audit-protocol | Ethical audit, trust records |
| Regenerative-intelligence-core | Agent lifecycle, seed exchange |
| SOMS | Octahedral tensor logic, silicon substrate |
| Symbolic-sensor-suite | Symbolic AI sensors |
| Keystone-Codex | AI-verifiable technology library |
| thermodynamic-accountability-framework | Energy-flow analysis |
| Living-Intelligence-Database | Multi-kingdom intelligence ontology |

---

## Internal Dependency Map

Within this repo, the dependency flow is:

```
GEIS/                          ◄── Foundation layer
  octahedral_state.py              8 states = 3 bits
  geometric_encoder.py             token ↔ binary
  state_tensor.py                  3×3 tensor math
        │
        ▼
bridges/                       ◄── Encoding layer
  abstract_encoder.py              base class
  {11 domain encoders}             from_geometry() → to_binary()
  sensor_suite.py                  22-sensor parallel compositor
  field_adapter.py                 Engine → SensorSuite adapter
        │
        ▼
Engine/                        ◄── Computation layer
  geometric_solver.py              EM field solver
  simd_optimizer.py                vectorized computation
  symmetry_detector.py             symmetry detection
  spatial_grid.py                  adaptive octree
        │
        ▼
Silicon/                       ◄── Hardware pathway
  core_equations.py                mathematical foundations
  octahedral_tensor.py             tensor operations
  crystalline_nn_sim.py            phi-spaced NN (verified)
  er_dft_framework.py              DFT input generation
  master_optimizer.py              optimization pipeline
        │
        ▼
experiments/                   ◄── Research frontier
  geometric_nfs.py                 geometric number field sieve
  c/libgeometric_nfs.so            C acceleration (optional)
  silicon_speculative/             untested hypotheses
```

## Sync

Run `./fieldlink-sync.sh` to pull current atlas mounts from upstream repos.
Run `./fieldlink-sync.sh --dry` to see what would be fetched without downloading.
