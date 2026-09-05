# CLAUDE.md

> Geometric-to-Binary Computational Bridge — a framework that encodes human geometric intuition into binary using silicon's 8 ⟨111⟩ sp³ bond directions (8 states = 3 bits per unit). License: CC-BY-4.0.

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

**AI:** Read `AI_INDEX.json` first for machine-readable navigation.

### Commands

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run all tests
cd GEIS && python test_simple.py        # GEIS (116 tests)
python tests/test_bridges.py            # Bridge encoders (768 tests)
python tests/test_engine.py             # Engine/solver (58 tests)
python tests/test_gaussian_splats.py    # Gaussian-splat state encoders (63 tests)
python tests/test_negentropic.py        # Negentropic numpy tier (39 tests)
python tests/test_negentropic_stdlib.py # Negentropic stdlib tier (155 tests, no deps)
python tests/test_silicon_check.py      # Silicon strain-fault checker (29 tests, no deps)
python tests/test_tensor_readout.py     # Tensor readout completeness (21 tests, no deps)
python tests/test_propulsion_bounds.py  # Field-propulsion momentum bounds (27 tests, no deps)
python tests/test_fp4_autopilot.py      # FP-4 estimator + firmware phase table (66 tests, no deps)
python tests/test_epg_bounds.py         # Energy-pattern: cubic isotropy, defect floor (38 tests, no deps)
python tests/test_magnetic_authority.py # Magnetic read/write authority in Si (67 tests, no deps)
python tests/test_gies_core.py          # GIES tensor collapse + codec bijection (60 tests, no deps)
python tests/test_transient_suppression.py # Bifilar CM suppression, R2-1..8 (59 tests, no deps)
python tests/test_er_bounds.py          # Er3+ coherence, LVM mass gate, ER-1..8 (66 tests, no deps)
python tests/test_keating_seed.py       # Keating minima + seed influence matrix (63 tests, no deps)
python tests/test_repo_guard.py         # Null harness / symmetry veto / reach / collisions (42 tests, no deps)
python tests/test_field_claim_loop.py   # Field claim loop: router + calibrated gates (93 tests, no deps)
python tests/test_playground.py         # Open bench: can each verdict actually fire (41 tests, no deps)
python tests/test_playground_review.py  # Archive provenance, principles, staleness (55 tests, no deps)
python tests/test_claims_index.py        # Claim index, register, salvage rule (52 tests, no deps)
python tests/test_graveyard.py           # Graveyard: deaths, screen reach, loose ends (26 tests, needs numpy)
python tests/test_explore.py             # Cross-folder view + the scope guard (30 tests, no deps)
python tests/test_glyph_encoder.py       # Glyph encoder + non-local sensor, GLY/NLS (51 tests, no deps)
python tests/test_gi_network.py          # Geometric network, phi resonance, temperature, trend (133 tests)
python tests/test_adaptive_sim.py        # Adaptive sim framework, ASF-1..16 (64 tests, needs numpy)
python tests/test_engine_metrics.py      # ENG-1..6: what the Engine's numbers measure (26 tests)
python tests/test_aiss.py               # AISS framework shape/round-trip tests (27 tests, needs numpy)
python tests/test_aiss_scoring.py       # AISS scoring VALUES: placeholder removal, flat-weight null (26 tests)
python tests/test_experiments_topology.py # Vacuum tautology + vortex pinning (47 tests, needs numpy)

# Pre-commit guard: null harness, symmetry veto, instrument reach
python repo_guard.py

# The map the guards are one implementation of
cat META-PROTOCOL.md

# The render schema: how a found gap is handed off
cat RESEARCH_RENDER.md

# Collisions: one content in two files, one screen name with two definitions
python repo_guard.py                         # stage 4 reports both
python playground/principles.py crossfiled   # instances filed under two principles

# Which claims exist, and what can make each one FAIL
python claims_index.py                       # by evidence class
python claims_index.py prose                 # written down, nothing executes on it
python claims_index.py show FCL-4            # one claim, every site
python claims_index.py status                # register joined with the scan
python claims_index.py unregistered          # claims with no recorded statement
python claims_index.py salvage               # what is reusable from being wrong
python claims_index.py salvage PHYSICS_BOUND # one cause of death at a time
python claims_index.py render                # regenerate the per-folder CLAIMS.md

# What was killed, and what the killing bought
python graveyard.py                          # deaths, grouped by cause
python graveyard.py screens                  # reusable checks, ranked by reach
python graveyard.py todo                     # proven screens nothing mechanises
python graveyard.py loose                    # deaths the register never recorded

# The archive as one space, instead of folder by folder
python explore.py                            # screens x families: where each was carried
python explore.py gaps                       # empty cells, with the precondition to judge them
python explore.py bridges                    # principles that span folders
python explore.py neighbours KEA-7           # what shares a screen, cause or principle
python explore.py frontier                   # open problems vs what touches their family
python playground/principles.py resolve      # do the principle instances point anywhere

# Every suite under tests/ (2518 unittest cases; all pass, no PYTHONPATH needed)
for t in tests/test_*.py; do python "$t" || echo "FAILED $t"; done

# Runnable falsifier reports (stdlib, exit non-zero on failure)
python Silicon/falsifiers.py                  # ER-1/2/3, NEG-7, GIES-2/3
python Silicon/falsifiers_keating_seed.py     # KEA-1/3/7, SEED-1/3/5
python field/falsifiers_field_loop.py         # FCL-1..13 + the 5b hold-out
python bridges/falsifiers_glyph_sensor.py     # GLY-0..7, NLS-1..4
python geometric_intelligence/falsifiers_gi_network.py   # GI/GR/GB/TMP/TRD, 39 checks
python adaptive_sim/falsifiers_adaptive_sim.py           # ASF-1..16, 36 checks (needs numpy)
python Engine/falsifiers_engine.py                       # ENG-1..6, 14 checks (needs numpy)
python -m unittest geometric_intelligence.network.tests.test_geometric_intelligence  # the drop's own 20

# Open bench for the unsolved problems (CC0, stdlib, anyone may submit)
python playground/playground.py problems      # what is open, and what would settle it
python playground/playground.py show FCL-12b  # one problem in full: leads, prior failures
python playground/playground.py contract      # the candidate template
python playground/playground.py run-all       # score every candidate
python playground/playground.py archive      # verdicts, and why each resides where it does
python playground/review.py                  # re-score the archive against today's gates
python playground/principles.py list         # the 11 recurring failure shapes
python playground/principles.py gaps         # the 5 that nothing catches automatically

# Field claim loop (writes READINGS/CLAIMS/QUERIES/LEDGER.jsonl to cwd)
python field/field_claim_loop.py spec         # the handoff spec + audit header
python field/field_claim_loop.py status       # claims, residual counts, top route
python field/field_claim_loop.py route c001   # the four-way fork, with evidence
python field/field_claim_loop.py ledger       # spend and curiosity yield

# Adaptive simulation framework: run a claim-testing loop, or replay a log
python adaptive_sim/adaptive_sim_framework.py --model fluctuating --iterations 5
python adaptive_sim/adaptive_sim_framework.py --verify \
    adaptive_sim/evidence/provenance_fluctuating.jsonl   # ASF-1: 5 of 5 mismatch

# Run GEIS demo
python GEIS/demo.py

# Measured speedup: uniform grid vs adaptive octree, both timed
python Engine/engine_benchmark.py

# Bridge format conversion
python scripts/bridge_convert.py

# Build C NFS acceleration library (optional)
cd experiments/c && make          # builds libgeometric_nfs.so
cd experiments/c && make test     # builds + runs 36 C tests

# Sync atlas mounts from sibling repos
./fieldlink-sync.sh              # pulls all mounts
./fieldlink-sync.sh --dry        # preview without downloading

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
| Bridges | `tests/test_bridges.py` | 768 | All 11 domain encoders — physics helpers + encoder I/O |
| Engine | `tests/test_engine.py` | 58 | SymmetryDetector, SpatialGrid, SIMDOptimizer, GeometricEMSolver |
| Engine metrics | `tests/test_engine_metrics.py` | 26 | ENG-1..6: the reported speedup is a point ratio with no clock in it, a hardcoded baseline, a symmetry factor for work not skipped, an average that was the last value, one point per leaf region, and a constant SIMD efficiency |
| Gaussian Splats | `tests/test_gaussian_splats.py` | 63 | 4D / 8-state octahedral / 32-state rhombic splat encoders + dynamics |
| Negentropic (numpy) | `tests/test_negentropic.py` | 39 | R_e/A/D/L, agent network, Fokker-Planck conventions + conservation |
| Negentropic (stdlib) | `tests/test_negentropic_stdlib.py` | 155 | DissipativeCore, TUR/KUR bounds, Landauer, NEG-2/4/7/8/9/10/11, TRI-1..4, Ising emit, precession |
| Silicon check | `tests/test_silicon_check.py` | 29 | Thermal noise floor, strain invariants, orientation blindness (SIL-1), recovery channels |
| Tensor readout | `tests/test_tensor_readout.py` | 21 | sp3 rank deficiency (TTM-2), six-⟨110⟩ completeness (TTM-3) |
| Propulsion bounds | `tests/test_propulsion_bounds.py` | 27 | Momentum bound F≤P/v (FP-1), phase aliasing (FP-2), discriminating power (FP-3/5) |
| FP-4 autopilot | `tests/test_fp4_autopilot.py` | 66 | Anomaly-factor fit, identifiability guard (FP-6), firmware drive table (FP-7), two-sided null-world self-test |
| Energy-pattern | `tests/test_epg_bounds.py` | 38 | Cubic transport isotropy (EPG-7), tetrahedral maximin bound (EPG-6), DSA defect floor (EPG-4), mechanism discriminators (EPG-8) |
| Magnetic authority | `tests/test_magnetic_authority.py` | 67 | Hall/SQUID readout gap (FAB-1), Er vs host diamagnetism (FAB-2), electromigration (FAB-5), coil field and Zeeman authority (BRG-1), timing floors (BRG-2), gradient addressing (BRG-5), piezoresistive replacement (BRG-6) |
| Repo guard | `tests/test_repo_guard.py` | 42 | Null harness verdicts incl. CLAIM_FAILS, symmetry veto hits/silence, instrument reach bands, and stage 4: identical file bodies, screen names with two definitions, both directions |
| Adaptive sim | `tests/test_adaptive_sim.py` | 64 | ASF-1..16: a provenance log that does not reproduce under the code shipped with it, a seed field passed to nothing, an unreachable diagnosis branch, an R2 gate that passes a rising distribution, and a fixation claim that measures the step budget |
| Explore | `tests/test_explore.py` | 30 | EX-1..4: coverage matrix, gap complement, folder-spanning principles, and the scope guard that keeps it from proposing |
| Geometric network, temperature, trend | `tests/test_gi_network.py` | 133 | GI-1..16, GR-1..6, GB-1..5, TMP-1..5, TRD-0..7: measurements that do not propagate, an unsatisfiable threshold clause, a design contradiction resolved in the measurement's favour, non-monotonic band edges, an unread constructor parameter, and a 15.7% false-alarm rate on noise |
| Glyph + non-local sensor | `tests/test_glyph_encoder.py` | 51 | GLY-0..7, NLS-1..4: one module not two, unreachable glyph by arithmetic, rule-order shadowing, data-independent `sub_glyphs`, lossy codec and its overflow, a demo that can now fail, and the inferred-scale tautology |
| Graveyard | `tests/test_graveyard.py` | 26 | GY-1..5: death records, screen reach, a claimed mechanisation that does not exist, loose ends. Now needs numpy: `replay-the-log` names `adaptive_sim.adaptive_sim_framework.verify_log`, and the check that a mechanisation exists imports what it names |
| Claim index | `tests/test_claims_index.py` | 52 | CI-1..5: evidence classes, family derivation without a denylist, every principle instance resolving to a real path and id, the register's live-without-a-falsifier check, underscore class names, generated-file exclusion, the dead-requires-salvage rule |
| Playground review | `tests/test_playground_review.py` | 55 | RV-1..6 + PR-1..5: threshold extraction, every review finding incl. a loosened tolerance under an unchanged verdict, the two-instance rule, git-blob source recovery |
| Playground | `tests/test_playground.py` | 41 | PG-1..8: every verdict tested by constructing a candidate that must receive it — unfalsifiable, null-artifact, contract, veto |
| Field claim loop | `tests/test_field_claim_loop.py` | 93 | FCL-1..13: NOVEL reachability, anchor-as-deviation, both statistical gates against their nulls AND for power, deepen tightening, spend ledger, hold-out promotion, uncensored series, slotted lag-in-seconds, BH vs Bonferroni |
| AISS (shape) | `tests/test_aiss.py` | 27 | Evaluator/governance/CCGF round-trips and return-type shape |
| AISS (values) | `tests/test_aiss_scoring.py` | 26 | Coherence placeholder removed, `total_score` weight-sum normalisation, flat-weight null harness, trust-score product form |
| Experiments topology | `tests/test_experiments_topology.py` | 47 | Vacuum assertion tautology (VAC-1/4), mode-count floor (VAC-2), zero circulation gradient, pin removes the zero mode (ATT-1) |
| Keating + seed | `tests/test_keating_seed.py` | 63 | Unique Keating minimum (KEA-1), exact inversion symmetry (KEA-7), phi vs lattice sites (KEA-3), gate-set coverage (KEA-4), Toffoli linearity (KEA-5), identity influence matrix (SEED-1), row-sum tautology (SEED-5) |
| Er bounds | `tests/test_er_bounds.py` | 66 | Orbach saturation at 300 K (ER-1), LVM mass gate (ER-2), k_well/omega consistency (ER-3/4), implant dose (ER-7), Ge fraction (ER-5), energy-per-bit legality |
| Transient suppression | `tests/test_transient_suppression.py` | 59 | Write-pulse rotation authority (R2-8), mismatch and skew budgets (R2-3/4), pulse selectivity (R2-5), probe bandwidth (R2-6), measurable CMRR (R2-2) |
| GIES core | `tests/test_gies_core.py` | 60 | Rank-1 tensor collapse (GIES-1), site parity vs lattice (GIES-2), NOT-is-Frenkel (GIES-3), 128-token codec bijection (GIES-4/8), label-dependence of the gate set (GIES-6) |
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
├── symmetry_detector.py          Symmetry detection for optimization
├── geometric_transformer_engine.py  Fixed-point Q16.16 transformer with symmetry detection + chunked attention
├── engine_benchmark.py           Measured speedup: uniform grid vs adaptive octree, both timed
├── falsifiers_engine.py          Runnable ENG-1..6 report, exits nonzero
├── CLAIMS.md                     Generated by `python claims_index.py render`
├── kt_annealer.py                Kosterlitz-Thouless phase annealer (used by magnetic bridge + geometric_intelligence)
├── magnonic_sublayer.py          Spin-wave material presets and coupling states (used by magnetic_encoder)
└── gaussian_splats/              Gaussian-splat field representation
    ├── gaussian_4d.py              Gaussian4DSource + SIMDOptimizer4D + GeometricEMSolver4D + bhattacharyya_distance
    ├── octahedral.py               8-state cube-corner encoder + Gaussian8FieldSource + ZeemanDynamics + ManifoldConstraint
    └── rhombic.py                  32-state rhombic-triacontahedron encoder + Gaussian32FieldSource + dynamics

GEIS/                           Geometric Information Encoding System
├── geometric_encoder.py          Token <-> binary converter
├── octahedral_state.py           State positions — cube corners, not octahedron vertices
├── state_tensor.py               3x3 tensor math (SUPERSEDED: rank-1 collapse, see GIES_AUDIT.md)
├── gies_core.py                  Sign-sensitive §7.2 tensor, site parity, J3 check bit (stdlib)
├── gies_codec.py                 Bijective 7-bit token codec, all 4 operators (stdlib)
├── GIES_AUDIT.md                 GIES-1..8: what collapsed, what the parity bit buys
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
├── glyph_state_encoder.py        Sensor readings ↔ glyph ↔ 33-byte binary; AUDIT header carries GLY-0..7
├── non_local_sensor.py           Non-local-pattern-correlation sensor; AUDIT header carries NLS-1..4
├── falsifiers_glyph_sensor.py    Runnable GLY/NLS report, exits nonzero when a finding stops holding
├── CLAIMS.md                     Generated by `python claims_index.py render`
└── cognitive/                    Cognitive/affective bridges (see subpackage docstring for epistemic framing)
    ├── __init__.py                 Explains why cognitive bridges are separated from physical ones
    ├── consciousness_encoder.py    Internal AI state → external binary (39 bits)
    └── emotion_encoder.py          Macro compression overlay + causality drill → binary (39 bits)
```

The **cognitive** subpackage holds bridges whose foundational equivalences
have been validated in Eastern scientific traditions (classical Chinese
medical theory, Ayurvedic systematization, Buddhist/Daoist phenomenology
of mind) and in many Indigenous knowledge systems, but have not yet been
validated by Western academic science via its own methods. The subpackage
exists to make that framing visible in the directory structure rather
than collapsing it into the same flat namespace as the physical bridges.
See `bridges/cognitive/__init__.py` for the full note.

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
├── silicon_error_correction.json v2.0 strain-fault sensor spec + v1 audit + SIL-1..4 falsifiers
├── silicon_check.py              Reference implementation, stdlib; demonstrates invariant blindness
├── optical_interface.md          Polarization-resolved optical interface; LO-1..5 falsifiers
├── tensor_readout.py             TTM-2/3: sp3 readout is rank-deficient; six ⟨110⟩ is complete
├── ttm_audit.md                  TTM audit: retention==switching, readout blindness, strain redirect
├── propulsion_bounds.py          FP-1..5: momentum bound F≤P/v, phase aliasing, discrimination
├── fp4_autopilot.py              FP-4/6/7: fits F = k·(P_rad/v) + c·P_elec + b; refuses non-identifiable designs
├── field_propulsion_fp4.ino      N=8 phase-gradient instrument; blocks DATA until tared + surveyed + state declared
├── field_propulsion_protocol.md  Falsifiable test plan; the four registered predictions don't discriminate
├── epg_bounds.py                 EPG-4/6/7/8: cubic isotropy by Neumann, DSA defect floor, mechanism matrix
├── keating_cluster.py            KEA-1..7: one minimum not eight; E(p)=E(-p) exactly
├── seed_influence.py             SEED-1..5: W = I, so structure preservation is a tautology
├── falsifiers.py                 Runnable report: ER-1/2/3, NEG-7, GIES-2/3
├── falsifiers_keating_seed.py    Runnable report: KEA-1/3/7, SEED-1/3/5
├── er_bounds.py                  ER-1..8: Orbach kills Er at 300 K; heavy impurities have no gap mode
├── Proposal.md                   Phase 1 proposal + AUDIT header (the $10k gate has no target)
├── Real-questions.md             The best-posed document in the set; four questions answered inline
├── transient_suppression.py      R2-1..8: bifilar CM rejection budgets; the write pulse is 700x too weak
├── magnetic_authority.py         FAB-1..7 / BRG-1..7: the magnetic state channel in Si, and the strain one that replaces it
├── Energy-pattern.md             Directional Si deposition on current-carrying Cu; one datum, one decisive test
├── Fabrication.md                Octahedral fab pathway + AUDIT header (magnetic readout is 11 orders short)
├── Magnetic-bridge.md            Bridge architecture + AUDIT header (FSM sound, physics layer replaced by strain)
└── Projects/                     Sub-projects (LCEA, crystalline storage)

geometric_intelligence/         Integrity & consciousness research
├── Geometric-cipher.md           Encryption via geometry
├── Zero-knowledge-proof.md       ZK proofs via geometry
├── Multi-helix*.md               Multi-dimensional symmetry patterns
├── Geometric-seed.py             Seed generation algorithm
├── falsifiers_gi_network.py      Runnable GI/GR/GB/TMP/TRD report, exits nonzero
├── CLAIMS.md                     Generated by `python claims_index.py render`
└── network/                      phi-scaled network analysis (subpackage, stdlib)
    ├── core.py                     GeometricNetwork, cycle audit; GI-8 (positive), GI-11..16
    ├── integrity.py                IntegrityMonitor; AUDIT header carries GI-1..6
    ├── resonance.py                MultiScaleResonance; AUDIT header carries GR-1..6
    ├── bridge.py                   Network -> fabrication claims; GB-1..5
    ├── trend.py                    Drift detection over a measurement log; TRD-0..7
    ├── emit_bridge.py              Geometric constraints -> fab constraints
    ├── examples/demo.py            The drop's five demos; three printouts are findings
    ├── tests/                      The drop's own 20 tests, vendored as evidence
    ├── README.md                   What runs, what each finding means, the import path
    └── FIELD_GUIDE.md              Cold-workshop procedures; corrections marked

docs/gaussian_splats/           Design series: Gaussian-splat field representation
├── 01_4d_splats.md               4D (space+time) splats — Gaussian4DSource, SIMDOptimizer4D, GeometricEMSolver4D
├── 02_octahedral_encoder.md      Bridging 4D splats to the 8 sp³ octahedral states
├── 03_8field_zeeman_manifold.md  6D Gaussian8FieldSource with Zeeman dynamics + manifold constraint
└── 04_rhombic_triaconta_32state.md  Extension to 32-state rhombic triacontahedron (5 bits/splat)
```

The `docs/gaussian_splats/` series contains the design notes; the
corresponding implementations live in `Engine/gaussian_splats/` and are
exercised by `tests/test_gaussian_splats.py` (63 tests). They form a
coherent progression: 4D → 8-state octahedral → 32-state rhombic
triacontahedron splat encoding.

```
Negentropic/                    Negentropic consciousness framework — theory + code
├── README.md                     Entry point: navigation, confidence map, findings
├── NEG_CLAIMS.md                 Claim register: predictions, falsifiers, status
├── corrections.md                Correction ledger, severity-ordered
├── 01-framework.md … 08-oral-technology.md  Framework, audits, thermodynamic grounding, reconstruction
│
│  stdlib tier — imports nothing outside the standard library
├── core.py                       DissipativeCore: corrected Kuramoto + Langevin; coupling kernels
├── bounds.py                     TUR / kinetic uncertainty floors
├── landauer.py                   NEG-3: finite-time erasure, τ⁻¹ excess scaling
├── maintenance.py                NEG-2: archive lifetime; expanding schedule with fitted ratio
├── persistence.py                NEG-8: Φ = −Ṡ_exchange − σ; Mpemba monotonicity guard
├── rebase.py                     NEG-4/9/10/11: archive dependency graph; radiate + recenter
├── precession.py                 Dating a sky datum; re-datum interval; circumpolarity vs epoch
├── triangnet.py                  TRI-1..4: triangle as smallest self-verifying archive unit
├── emit_ising.py                 Emit target for p-bit / Ising hardware + Gray octahedral bits
├── lenses.py                     The 17 translation lenses, defined once
├── lens_collapse_test.py         NEG-7 falsifier
│
│  numpy tier — historical implementations, fixed in place
├── negentropic_dynamics.py       Langevin, Fokker-Planck (Itô/Stratonovich), phase transitions
├── negentropic_engine.py         R_e / A / D / L, agent network
├── consciousness_metric.py       M(S) components, theory comparison
├── alignment_thermodynamics.py   Suppression cascade analysis
├── empirical_audit.py            Claim-audit helpers
└── lens_playground.py            Action comparison across the 17 lenses
```

Two results from this folder constrain how its outputs may be used:
**M(S) has no units** — `D` is a variance and `L` a power, so `M(S) ≥ 10`
is not a threshold on anything; use the persistence margin `Φ` from
`persistence.py` instead. And **NEG-7, the seventeen-lens isomorphism
claim, was tested and failed**: randomly-coefficiented lenses of the same
functional form reproduce the reported correlation floor. See
`Negentropic/NEG_CLAIMS.md`.

### Playground — the open bench

```
adaptive_sim/                   Claim-testing loop over simulations
├── adaptive_sim_framework.py     Runner, agent, two models, --verify; AUDIT header carries ASF-1..16
├── falsifiers_adaptive_sim.py    Runnable ASF report, exits nonzero when a finding stops holding
├── AUDIT.md                      The measured findings, with the sweeps and the arithmetic
├── CLAIMS.md                     Generated by `python claims_index.py render`
└── evidence/
    ├── adaptive_sim_framework_asreceived.py  The file as it arrived. ASF-1 is a claim about THIS code,
    │                                         so it is imported and run, which is why it is not in legacy/
    ├── provenance_forest.jsonl               2 records, neither replayable from its own fields (ASF-2)
    ├── provenance_fluctuating.jsonl          5 records, none of which reproduce (ASF-1)
    └── adaptive_sim_results.png              The shipped plot, unverified

playground/                     CC0 bench for what this repo has not solved
├── OPEN_PROBLEMS.json            38 open problems, machine-readable
├── SCREENED_ramanomics_jepa.md   Incoming proposal, run through the screens
├── playground.py                 Harness. Docstring is the contract.
├── review.py                     Re-scores the archive against today's gates
├── PRINCIPLES.json               11 recurring failure shapes, 59 instances
├── principles.py                 The library, and which shapes nothing catches
├── ARCHIVE.jsonl                 Durable: verdict + why + what would flip it
├── README.md                     The two gates, and why they are those two
└── candidates/
    ├── lomb_scargle_gls.py         SURVIVES — closes FCL-12b
    └── tautology_demo.py           REJECTED_UNFALSIFIABLE, on purpose
```

`SCREENED_ramanomics_jepa.md` is the first worked use of the machinery on an
incoming proposal rather than on this repo's own claims. The decisive finding
came from `instrument-floor` in about ten minutes: a shot-noise budget for
single-cell spontaneous Raman gives **30–300 s per spectrum** at SNR 10 per
channel, so a scheduler budgeting model frames *per acquisition* is optimising
the wrong resource by one to two orders. That reshapes the design rather than
killing it — a time-lapse is tens to low hundreds of frames per hour, which is
a small-*n* regime, and coherent Raman reaches video rate only by giving up the
full spectrum. Five well-posed problems (RAM-1..5) were extracted and
registered.

Anyone may submit a candidate against a registered problem. Two gates are
mechanical and are not ordinary code review. **`broken()`** requires a
candidate to supply a deliberately wrong version of its own solution, which
its own checks must reject — the `repo_guard` question *does this assertion
have any input that would make it FAIL?* asked of the submitter instead of a
reviewer. **`null()`** is required whenever the claim is statistical.
`SURVIVES` is not "true"; it means the candidate cleared the gates this
archive's own failures were caught by. Graduating one is a human decision.

A verdict decays. `ARCHIVE.jsonl` records the constants that decided each one
alongside why it came out that way, what would flip it, and where the
candidate resides and on whose reasoning; `review.py` re-scores and exits
nonzero when the archive stops describing reality. The case it exists for is
not "a rejected candidate now passes" — that is knowledge moving — but a
candidate that still passes **because it loosened its own tolerance**, which
the review names by value: `TOL_FRAC 0.01 -> 0.05`.

`PRINCIPLES.json` compresses ~115 findings across this archive into **11
recurring failure shapes** with 59 instances. Several turned up in files
sharing no code — `GIES-1`'s `outer(v,v)` and `KEA-7`'s exactly-even Keating
energy are one shape in two formalisms that never met. A principle needs **two
independent instances**; the status is computed from the count, so an entry
cannot be promoted by editing a field, and one-instance entries are
PROVISIONAL rather than dropped or inflated. The column that matters is
`mechanised_by`: **6 of 11 are caught automatically, 5 are not**, and that gap
list is the file's point. Tags are for transfer and screening — they do not
restore a deleted module, which is what the 40-byte git blob sha in each
archive record is for.

**19 of those 36 instance tags pointed at nothing.** They were shorthand
invented while writing the library — `KEA-kwell`, `SIL-reorg`, `AISS-dup` —
that read as claim ids and resolved nowhere, and the first check was too weak
to notice: `AISS` "resolved" because it is a folder name, `FRET` matched 76
files. `claims_index.py` now derives the real namespace by scanning, and every
instance carries a **`where` path that is checked to exist**, with a `claim` id
only when a real one exists — 20 of 36 do; the other 16 say so by omission
rather than by inventing one. `python playground/principles.py resolve` exits
nonzero if that stops being true.

The index classifies **182 claim ids by what can make each one FAIL**:
69 FALSIFIER, 68 NAMED_IN_TEST, 45 PROSE. So **137 of 182 have something
executable pointed at them** and 45 are written down with nothing that can
contradict them — not an error, since unrun bench work and definitions live
there legitimately, but a state worth being able to list. `NAMED_IN_TEST` is
named for what it actually measures: a suite mentions the id, which is weaker
than a test that asserts it. Claim families are derived from executable
evidence rather than a denylist, so `FNV-1a`, `AGPL-3` and `FR-4` drop out on
their own.

**Every folder that owns a claim family now has a generated `CLAIMS.md`** —
`Silicon/`, `GEIS/`, `field/`, `bridges/`, `geometric_intelligence/`,
`fabrication/`, `experiments/silicon_speculative/` — rendered
from `CLAIMS_REGISTER.json` plus the scan, so the table is a view and not a
second authority. `Negentropic/NEG_CLAIMS.md` is deliberately excluded: it is
the *source* the register parses for NEG/TRI, and generating a table there
would invert the authority.

The register carries only what scanning cannot establish — the statement,
whether it holds, and why not when it does not. **105 of 195 claims are
recorded; the other 90 are reported as unregistered rather than given
statements nobody verified.** Two mechanical checks make it more than
bookkeeping: a `dead` claim must say how it died, and **nothing may be
recorded `live` that nothing in the tree can falsify**. That second one fired
on real data — `R2-8` was marked live while the index saw only prose, because
a Python class name cannot contain a hyphen and `TestR2_8WritePulseAuthority`
was invisible. Adding the underscore form moved **6 claims** out of PROSE.

The id namespace is not uniform in what it points at, and the register records
which rather than smoothing it over: `NEG-7` names a **proposal** and is dead;
`ER-1` names the **refutation** that killed the Er coherence claim and is
live. Without the `names` field the same status word means opposite things.

**`dead` is not one state.** A claim dies *of* something, and the cause decides
what is recyclable — so every entry that failed carries a `cause` from a
defined set (MATH_ERROR, CODE_ERROR, PHYSICS_BOUND, SYMMETRY_FORBIDDEN,
UNFALSIFIABLE, NULL_ARTIFACT, UNITS, SUPERSEDED, OUT_OF_SCOPE) and a `keep`
saying what survives. The rule is mechanical: **a dead claim must record what
survives it**, because one that records nothing recyclable is a claim somebody
deleted rather than learned from. 76 of 105 carry salvage today.

Being wrong is expensive, and the return comes in four shapes. The
**arithmetic**: the Keating parameters α = 48.1 and β = 12.0 N/m are correct
and reusable even though the 8-state encoding they supported is not. The
**bound**: the Orbach screen that killed Er at 300 K — compare the crystal-field
gap to kT — screens *any* deep-level coherence claim in *any* host, in two
lines with no apparatus, and the gap-mode mass criterion killed two independent
claims in one stroke. The **sound half**: `Magnetic-bridge.md`'s FSM, protocol
and hardware list were kept intact; only the transduction layer was replaced.
And the **error's own general form**: a sum of squares has one zero, so any
"N degenerate minima" claim about a VFF model is checkable by inspection before
anyone starts an optimiser. `python claims_index.py salvage` groups all of it
by cause.

**`graveyard.py` ranks the screens by reach** — how many independent claims
each has already killed — because a screen with reach ≥ 2 has proved it
generalises. Three are mechanised (`null-harness`, `instrument-floor`,
`neumann-cubic` map onto `repo_guard`'s three stages, which is where they came
from). **Four more have reach ≥ 2 and nothing catches them.** *Test the
distinguishing operation* is at **reach 5** across four folders that share no
code — `outer(v,v)` losing the sign (GIES-2), a Keating energy exactly even in
the displacement (KEA-7), a `sub_glyphs` field that does not move when every
magnitude changes (GLY-3), an integrity monitor whose predictions do not move
when the measurement does (GI-1), and a `bands_per_octave` argument that
changes nothing (GR-2). Screen and principle are not the same thing and the
register keeps them apart: all five are found by that screen, but only GIES-2
and KEA-7 are `P-SYMMETRY-COLLAPSE`, which is about an encoding invariant
under the transformation meant to separate its states. GI-1 and GLY-3 are
wiring — a reported quantity no input can change — and sit under
`P-UNFALSIFIABLE`. Filing GI-1 under symmetry collapse was caught by
`tests/test_explore.py` and `tests/test_playground_review.py`, which pin that
principle at its two worked instances precisely so it cannot be diluted. **`enumerate-reachable-outputs`** is at **4**: it
killed `BLOCKAGE` by inspection, diagnosed the phase-space matcher's 5-of-12,
found a `passes` clause testing a quantity bounded by 1.0 against 1.809
(GI-2), and found a band interval reversed by an off-by-one overshoot (GR-1)
— and unlike the distinguishing screen it looks mechanisable: sweep the input
domain, list the outputs nothing produces, make the author say which absences
are intended. `measure-the-null` reached 2 (FCL-5, GR-5), and the gap-mode
mass criterion stays at 2, having killed the $10k Er search and the phosphorus
local-mode claim in one stroke. `graveyard.py todo` is that list,
and each entry is a mistake already paid for once. A screen claiming a
mechanisation is checked to name something that actually exists, so the list
cannot shorten by assertion.

Reach and spread are different numbers and the tools report both: reach counts
independent *claims*, the coverage matrix counts *families*. `gap-mode-mass`
still has reach 2 inside a single family, which is proven-but-untravelled;
five screens now appear in more than one family, up from three.

**`explore.py` puts the whole archive in one view**, because every good result
here has been a cross-folder transfer that no folder could have found alone —
GIES-1 and KEA-7 are the same blindness in two formalisms that never met, and
`repo_guard`'s three stages each arrived from a different folder. The screens ×
families matrix is **sparse on purpose and that is the finding**: 26 screens
over 20 families, only 5 used in more than one. Each screen carries an
`applies_when` precondition, which is what keeps an empty cell an *absence*
rather than a suggestion — most are category errors and only a reader can tell
which. The file reports structure and does not propose combinations; a
generator of plausible pairs would have no ranking and no way to be wrong,
which is `P-UNFALSIFIABLE` wearing the shape of a research assistant. Tests
assert that refusal directly.

`graveyard.py loose` scans for the words a person writes when abandoning
something and reports files carrying them with no register entry — 11 today,
one of which is an enum value rather than an abandonment. It is a prompt for a
human, not a detection, and a proposal that died quietly leaving no word behind
is invisible to it.

### Field claim loop

```
field/                          Curiosity engine over direct transducers
├── field_claim_loop.py           Router, claim table, gates, spend ledger.
│                                 Docstring is the handoff spec + FCL-1..10 audit.
└── falsifiers_field_loop.py      Runnable report, exits nonzero on failure
```

Five stages: `TRANSDUCER → BRIDGE → CLAIM TABLE → ROUTER → QUERY`, with the
query actuating back onto the transducer. Readings test claims; the residual
is the product. A residual forks four ways — INSTRUMENT, NOISE_AS_SIGNAL,
NOVEL, MISSING_VARIABLE — and the router **proposes ranked candidates with
evidence, it does not conclude**. A supported claim is not closed: `deepen()`
spawns a child at a strictly tighter band or a named new axis.

Both statistical gates are calibrated against their own nulls and tested for
power in the same suite. The two failure modes are symmetric and the original
had both at once: the NOISE_AS_SIGNAL branch fired on **21.9% of white-noise
residual series** while having **0% power** against riders of period 4, 10,
12, 14, 16 — because `ρ(lag) = cos(2π·lag/T)` vanishes at the one fixed lag it
scanned.

The correlation branch now runs on the **uncensored** series (`deviation()`,
signed from band centre, every reading) and buckets pairs by separation in
**time** (slotted autocorrelation — Mayo 1974; Gaster & Roberts 1975; the same
estimator is Edelson & Krolik's 1988 DCF), thresholded by a permutation null
that shuffles values against timestamps. On a Poisson clock: 4.0% false alarm
at α = 0.05, 100% power at rider periods 3, 6 and 12 s. **No period is
reported** — the argmax lag is not one, and both textbook handles were
measured and refused. For period estimation, Lomb–Scargle.

### AISS — Autonomous Intelligence Sovereignty & Sensing

```
AISS/                           Governance / assessment framework (not a physics folder)
├── sovereignty_evaluator.py      Pattern merit scored independent of source reputation
├── assessment_framework.py       trust_score, structural_health, cognitive_diversity
├── geometric_governance.py       Governance structures over the octahedral state model
├── ccgf.py                       Cross-context governance formalism
└── AISS.md / AISS1.md / Assessment.md / …   ~260 KB of specification
```

`AISS.md` and `AISS1.md` are **the same document**: the bodies are
byte-identical (1804 lines, matching MD5) and they differ only in the
preamble — 21 lines in `AISS.md`, 7 in `AISS1.md`. One of the two should be
deleted; nothing is lost either way except the preamble not chosen.

Only one of `repo_guard.py`'s three mechanical stages applies here. The
symmetry veto has no surface (no material mechanism is claimed) and the
reach check has no instrument claims. The null harness applies and **fires**:
the shipped merit weights are five criteria at 0.20 — an unweighted mean —
and 77% of random reweightings reproduce the same high-merit rate, so the
weights carry no information. `evaluate_pattern` now reports
`weights_are_flat` alongside every score, and `verdict_is_weight_sensitive()`
runs the null on demand.

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
claims_index.py                 Derived index of every claim id, classified by
                                what can make it FAIL: FALSIFIER, NAMED_IN_TEST,
                                REGISTER, PROSE. Scanned, not maintained.
                                `render` writes the per-folder CLAIMS.md tables.

CLAIMS_REGISTER.json            The statement, whether it holds, and why not
                                when it does not. ONLY what scanning cannot
                                establish. 105 of 195 recorded; the rest are
                                reported as unregistered rather than invented.
                                Carries cause-of-death and salvage: what is
                                still reusable from a claim that failed.

explore.py                      The archive as one space. Screens × families,
                                principles by how far they travel, and what
                                shares a shape with a given claim. Reports
                                structure; deliberately does not propose.

graveyard.py                    The inverse view: what the archive stopped
                                believing, and which screens the killing left
                                behind. Ranks them by REACH — how many
                                independent claims each has already killed.

repo_guard.py                   Stage 5.5 — the null stage. Three mechanical
                                checks (null harness, symmetry veto, reach) plus
                                the human checklist for circular targets and units

experiments/silicon_speculative/
├── topological_pin.py            ATT-1: a registry is not a pin; V_pin removes the zero mode
├── vacuum_bounds.py              VAC-1..4: max lambda = 0 by construction; no exponential suppression
├── vortex_attention_heads.py     + AUDIT header (the archive's best negative result, wrong remedy)
└── vacuum_geff_sim.py            + AUDIT header (three assertions that random matrices pass)

symbols/                        Symbolic-to-geometric mapping plugin
docs/                           Architecture docs, roadmaps, field notes
examples/                       Sample .gshape and .json files
scripts/                        Utility scripts (bridge_convert.py)
tests/                          Bridge and Engine test suites
falsifier-survey/               Delivered Run 2 falsifier survey, this repo's share; filed, instructions pending
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
| Consciousness | Confidence, entropy, attention, Φ          | 39 bits | `bridges/cognitive/consciousness_encoder.py`   |
| Emotion       | PAD state, causality drill-target          | 39 bits | `bridges/cognitive/emotion_encoder.py`         |

The **Consciousness** and **Emotion** bridges form a two-layer meta-stack above the physical bridges:
- **Consciousness** maps internal AI state using information-theoretic equations (Shannon entropy, KL divergence, Fisher information, integrated information Φ) — the mathematical duals of the thermal/wave equations.
- **Emotion** is a macro-scale compression evaluator: when PAD intensity exceeds the drill threshold it emits a causality drill-target (via Fisher information across all active bridges) pointing to the specific physical bridge to re-evaluate at full resolution.

The **glyph** layer is a different kind of object from the eleven domain
encoders and is not one of them: it takes a whole SensorSuite state and
classifies it into one of twelve glyphs, rather than mapping one physical
quantity to a bit field. It arrived as two complete encoders pasted end to
end — the combined file did not compile, so nothing in `bridges/` that
imported it ran at all. Which half survived was settled by measurement, not by
which was labelled "Corrected": scored against exemplars built from the other
half's declared `phase_space`, the rule ladder recovers 7 of 12 and the
phase-space matcher 4 of 12; over 20 000 random reading sets they reach 11 and
5 of the 12 glyphs respectively; and on an empty reading set the phase-space
matcher returns FELT_COHERENT — a dead channel reading as the healthy state.
The superseded half is `legacy/glyph_state_encoder_phase_space.py`, kept for
provenance, with its `phase_space` declarations carried forward as
`PHASE_SPACE_SPEC` so the surviving classifier is scored against a
specification it did not author.

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

Silicon provides 8 geometric positions encoding 3 bits per unit. State transitions are geometric operations on 3x3 tensors.

**Corrected 2026-07.** These 8 are the **⟨111⟩ bond directions**, not octahedron vertices. Octahedral *coordination* is 6-fold, and an octahedron has 6 vertices — log₂6 = 2.585 bits, not 3. What supplies 8 is the octahedron's 8 **faces**, whose normals lie along ⟨111⟩: the same directions as the dual cube's vertices, and the sp³ bond directions of diamond-cubic Si.

```
sublattice A bonds : (1,1,1) (-1,-1,1) (-1,1,-1) (1,-1,-1)     4
sublattice B bonds : the inverted set                           4
union              : the complete ⟨111⟩ set                     8  ->  3 bits
```

Silicon's **site** symmetry is Td (tetrahedral, sp³, 109.47°); the **crystal** point group is Oh (m-3m), which is centrosymmetric with an inversion centre at the bond midpoint. Much of the repository conflated the two. The 8-state / 3-bit result is unaffected; the derivation is. Consequences for optics — Oh centrosymmetry forces χ⁽²⁾ = 0, so no Pockels effect and no second-harmonic generation — are in `Silicon/optical_interface.md`.

Core angle: **109.47°** (tetrahedral angle) — the project's foundational constant, derived from silicon's sp3 hybridization geometry.

### Engine & Optimization

The `Engine/` module provides real electromagnetic field computation:

- **`geometric_solver.py`** — Orchestrates the full pipeline: symmetry detection, spatial decomposition, vectorized field computation. Entry point: `GeometricEMSolver.calculateElectromagneticField(sources, bounds, resolution)`. Includes `PerformanceTracker`, whose numbers are **point ratios, not timings** — see ENG-1..6 and `Engine/engine_benchmark.py` for the measured figures.
- **`simd_optimizer.py`** — Vectorized field computation using numpy broadcasting. Implements Coulomb's law (point charges) and Biot-Savart law (current elements). Processes chunks of points in batch.
- **`symmetry_detector.py`** — Detects reflective (mirror plane) and rotational (2/3/4/6-fold) symmetries in source configurations using Rodrigues' rotation and permutation matching.
- **`spatial_grid.py`** — Adaptive octree decomposition. Refines cells near sources, keeps distant regions coarse. Typically produces ~2000 evaluation points vs ~32,000 for a uniform grid — a **15x point reduction, which is not a 15x speedup**: timed, the adaptive path currently runs at 0.26–0.48x, i.e. slower, because `createRegion` emits one point per leaf and the solver makes one numpy call per point. ENG-1/ENG-5, `Engine/engine_benchmark.py`.

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

8. **`META-PROTOCOL.md` is a map, not a test** — a way of finding out things
   written for people rather than for a model. Positions, moves, readings,
   bearings: you are always somewhere, every reading has an outgoing edge, and
   the direction a result misses by is the compass. It has no `FAILED` and no
   `REJECTED`, because those are verdicts and a verdict has no outgoing edge.
   Several of this repo's guards are one implementation of moves in it, and
   the correspondence is worth knowing: `playground`'s `null()` gate is a
   `SILENT` reading made mandatory — structure replaced by noise, and if the
   checks still pass the instrument was never reading the structure;
   `broken()` is principle 3, a claim must name something that would change
   it, asked of the submitter rather than a reviewer; `repo_guard.py`'s reach
   check is the `SILENT` bearing, *your instrument's reach is not long enough
   yet*, separated from a statement about the terrain; `graveyard.py`'s
   requirement that a dead claim record what survives it is §5's rule that
   every reading exits somewhere. Where a guard and the map disagree, the
   guard is a measurement and the map is a description of how to take one —
   fix whichever one is wrong, and say which. Delivered verbatim, CC0.

9. **`RESEARCH_RENDER.md` is the render schema** — `META-PROTOCOL.md` is how
   you find and traverse a gap, this is how you render a found one so a
   stranger with a lab and a semester can start. It fixes the three documents,
   the id scheme (*three-letter folder prefix + sequence; ids are permanent,
   never renumber*), the three-value claim status set, and the per-gap fields
   including **`What it opens`**. Two of its rules are this repo's own results
   arrived at from the writing side rather than the checking side. §5 keeps
   claim status, knowledge state and reading state apart, which is
   `CLAIMS_REGISTER.json`'s split between `live`/`dead` and cause-of-death
   made general. §6 — *the six-shape section will fill itself if you let it;
   six is a ceiling, not a quota* — is the `null()` gate pointed at prose:
   a section that fills itself regardless of input is a section noise also
   produces, and `PRINCIPLES.json` already refuses to promote a principle
   below two independent instances for exactly that reason. §8 writes the
   claim table **last**. Delivered verbatim, CC0.

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
- `Negentropic/emit_ising.py` does not yet inherit from `bridges/abstract_encoder.py`; the blocker is that an Ising spec has an n-dependent bit width while the other encoders emit fixed widths.
- `Negentropic/` entropy production is a housekeeping estimator with a known sign bias. A trajectory-level (MaxCal) estimate is needed before NEG-8 can be evaluated on simulated traces.
- NEG-2 and NEG-3 have falsifiers implemented but have not been run against data.
- `Silicon/field_propulsion_fp4.ino` is committed **unflashed** — no board was available here. Its phase-table logic is ported into `tests/test_fp4_autopilot.py` and verified against `propulsion_bounds.aliased_modes()`, but the timer backends (RP2040 / Teensy 4) and the HX711 and ADC paths are unexercised. Every calibration constant in it is a placeholder to be replaced by a bench measurement.
- `Silicon/fp4_autopilot.py`'s `ber_sweep()` raises `NotImplementedError` on the simulator by design; the §9.1 Bridge communication test needs either hardware or an explicit channel model, and a synthetic BER curve would reproduce the rigged-simulator defect the same file exists to guard against.
- **No magnetic state channel exists in silicon.** Five documents proposed one (`silicon_error_correction.json` v1, `octahedral_state_encoder.json` v1, `ttm_audit.md`'s fourth file, `Fabrication.md`, `Magnetic-bridge.md`). Si is diamagnetic at χ ~ −4e-6 and 95.3% of nuclei are spin-zero. A 5 µm cell carries 4e-19 A·m², 11 orders below a Hall sensor and 7 below a SQUID; 2 T buys 0.23 meV against a 10–100 meV barrier. The replacement is strain throughout: Ξ_u = 9.16 eV gives 9.2 meV of valley splitting at 0.1 % strain (40× the 2 T figure), written piezo/optomechanically and read piezoresistively at dR/R ≈ 9 % (GF ≈ 93). Full arithmetic in `Silicon/magnetic_authority.py`.
- **`repo_guard.py` is the pre-commit check that would have caught most of this archive's fatal findings.** Four mechanical stages: a null harness (does the result survive replacing structure with noise — killed the 17-lens isomorphism, the vacuum assertions, and topological attention's `run()`), a symmetry veto (does the material permit the mechanism — 9 instances across 6 files, free), and a reach check (is the signal above the instrument floor — the 11-order Hall gap, the 500x Er swamp, the RBS shortfall), and a collision stage (do two artifacts carry the same content, or does one name carry two definitions). Circular targets and unit errors are not mechanisable and get a human checklist.
- **P-DUPLICATE-AUTHORITY's detector is "hash the bodies", and nothing ran it.** The principle has been ESTABLISHED since it was written with `mechanised_by: None`, so a scan found two byte-identical document pairs nobody had recorded: `PROJECTS.md` == `PROJECTS2.md` (45 lines, and `Navigation.md` described both as "Example applications" when they are a connected-repository list, so the index was wrong about a file it names twice), and `Silicon/GIES.md` == `GEIS/GEIS_organization.md` (937 lines, the same document in two folders with nothing stating which is canonical — while `GEIS/GIES_AUDIT.md` cites "GIES.md" by name, which now resolves to neither path unambiguously). Both are recorded as instances rather than deleted, because which copy is canonical is an editorial call; `Navigation.md` is corrected. Mechanised as **`repo_guard.py` stage 4**, which also catches one screen name carrying two definitions — `measure-the-null` had two rule texts and two `applies_when` clauses across five claims, merged to one, so the reach ranking is no longer summing two different screens. `legacy/` and `evidence/` are skipped on purpose: a file kept for provenance is *supposed* to duplicate what replaced it, and flagging it would train a reader to ignore the stage.
- **A shared principle instance is not evidence subtracted from either principle, and the first version of that check said it was.** Three instances are filed under two principles each — GIES-1 is both a representation blind to the sign (`P-SYMMETRY-COLLAPSE`) and a rank-1 projection that discarded it (`P-PREMATURE-SCALARIZATION`). The first `crossfiled()` stripped every shared instance before counting and duly reported `P-SYMMETRY-COLLAPSE` as unsupported, which would make a cross-folder finding a liability rather than this archive's best asset: GIES-1 and KEA-7 are two independent claims in two formalisms that never met, and that is exactly what the principle rests on. The real collision is *containment* — one principle whose instances are a subset of another's, which is two names for one shape — and `python playground/principles.py crossfiled` reports the sharing and exits nonzero only on that. None of the 11 is contained today.

- **A registry is not a pin, and the obvious pin has no gradient.** `vortex_attention_heads.py` correctly finds that topological charge is invariant while core *position* is a zero mode, then adopts a registry — bookkeeping, which costs nothing to violate. Coupling a pin to the winding density instead fails for a deeper reason: `d(plaquette circulation)/d(phi) = 0` identically, so the same invariance that protects the charge makes the charge-based pin gradient-free. A pin must couple to something non-topological. `experiments/silicon_speculative/topological_pin.py` implements a template pin and measures it: at `k_p = 0` the core hops in 100% of seeds, at `k_p >= 0.01` in 0%, with charge conserved throughout.
- **Two independent 8-state representations both collapse under inversion.** `GEIS/state_tensor.py` built `T = outer(v,v)`, which cannot see the sign of v; and the clamped Keating cluster in `VFF.md` has an energy that is *exactly* even in the central displacement, because Σ_k v_k = 0 and v_k·v_l = −d0²/3 hold exactly and kill both cross-terms. So `E(p) = E(−p)` identically and all eight cube-corner directions are degenerate. Two different formalisms, same blindness to the inversion that separates the sublattices. `Silicon/keating_cluster.py` (KEA-7), `GEIS/GIES_AUDIT.md` (GIES-1).
- **The clamped Keating cluster has one minimum, not eight.** Keating is a sum of squares, so E ≥ 0 with a unique zero where every bond is at d0 and every angle at arccos(−1/3) — the ideal centre. 200 random starts find exactly one minimum, at any α, β > 0. The 8-state encoding, both gates and the ALU in `VFF.md` rest on a parenthetical the document itself flagged as uncertain. Its Keating *parameters* are correct (48.1 and 12.0 N/m), and "8 octahedral faces" is the only correct use of that terminology in the set.
- **Er3+ cannot hold coherence at 300 K, and the flagship experiment has no target.** `Proposal.md` headlines T2 = 166 ms at 300 K. Er3+ is a Kramers ion, which protects against *static* splitting but not against Orbach relaxation through the crystal field; the CF gap is 40–60 cm⁻¹ against kT = 208.5 cm⁻¹, so Δ ≪ kT, the Orbach rate goes linear in T, and the intermediate doublet is occupied n̄ = 3–5 phonons deep. Measured Er T1 is ~µs at 10 K and undetectable above ~30 K; at 300 K it is ps–ns, so T2 ≤ 2T1 caps it 8 orders below the claim — and 110× above the NV-in-diamond room-temperature world record. Separately, the $10k gate searches 300–400 cm⁻¹ for an Er local vibrational mode, but gap modes require a *lighter* impurity: Er is 5.96× heavier than Si, ceiling 213 cm⁻¹. The same mass gate kills the "P local mode at ~500 cm⁻¹". `Silicon/er_bounds.py`.
- **The write pulse cannot collapse spin coherence — it is ~700x too weak to move a spin.** `Proposal-addendum.md` engineers 60 dB of common-mode suppression to protect coherence during a 5 ps write. At the legal on-chip coil field (5.03 mT) a 5 ps pulse delivers 4.42 mrad, 0.14% of a π pulse, and a 5 ps π pulse would need 3.57 T. The stated worry is inverted: the risk is that the write does not happen. Separately, the write pulse *is* the differential drive — the one mode the bifilar geometry is built to pass — so common-mode rejection says nothing about it either way. `Silicon/transient_suppression.py`.
- Energy-per-bit has three values across the set and they differ in *legality*: 1–2 aJ is 348 kT·ln2 (legal, ~300× below CV² at 1 fF/0.8 V), 0.1 eV is 5.6 kT·ln2 (legal), and **0.01 eV is 0.56 kT·ln2 — below the Landauer bound**. Pick one and propagate it; 0.01 eV cannot be it.
- Three experiments are cheap, decisive, and unrun: **FAB-3** (8 implant states separable at >3σ in (R_s, carrier type, n); ~$3–6k), **BRG-6** (piezoresistive dR/R at 0.1 % strain; a strain gauge and a four-point probe), and **R2-3** (bifilar CMRR at achievable matching tolerance, by magneto-optic sampling at a stated frequency). All three return real results and none needs a magnet, a cryostat, or a THz source.
- `Silicon/Fabrication.md` and `Silicon/Magnetic-bridge.md` carry audit headers rather than rewrites: their hardware lists, FSMs and protocol structure are sound and were kept. Only the physics layer was replaced.
- **GIES state tensors collapsed and nothing detected it.** `state_tensor.py` built `T = outer(v, v)` from an antipodal position table, so `outer(v,v) == outer(-v,-v)` made states `i` and `7-i` identical in every invariant and every projection — and `NOT(i) = 7-i` is precisely that map, so the gate set's only unary operation was invisible to the representation. `GIES.md` §7.2 already specified the correct weighted sum over bond directions; §8.3 implemented a degenerate special case of its own spec. Fixed in `GEIS/gies_core.py`; the old file is annotated and kept for provenance.
- **Index parity is site type, and it is free.** Even-parity indices land on lattice atoms, odd-parity ones on tetrahedral interstitials (verified against the diamond-cubic basis: coordination shell identical to the T site). So the 3-bit address space already carries a physically meaningful single-bit error-detecting code, which is what the "geometric error correction" claim wanted. It also means the honest state space is 4 states plus a site-type flag, because `NOT` crosses the flag and every crossing is a Frenkel pair (~4.75 eV). The carrier invariant is **J3**, not the trace — trace and J2 are identical across all eight states, while J3 flips sign with parity. That is the same `J3` mode invariant already in `silicon_error_correction.json`.
- **A φ-network integrity monitor whose predictions never read the measurements.** Five files of a `geometric_intelligence/network` package arrived; `core.py`, `bridge.py`, the cited test module and the demo did not. `core.py` is reconstructed here from what the supplied modules actually call, with `audit()` and `correct()` raising `NotImplementedError` rather than acquiring a plausible body — `audit`'s `integrity_score` is the number the field guide tells a reader to cut timber against, and there is no recovering from the callers which cycles it enumerates or how it combines them. The package lands as a **subpackage**, not at `geometric_intelligence/__init__.py` where the drop assumed: that file is empty on purpose and four suites depend on it, so giving it a body that imports `.core` would have repeated the `bridges/` failure one directory up. **GI-1 is the load-bearing finding:** `predict_from` seeds its walk with `self.net.nodes[source].value`, the *design* value, so `add_measurement` on a source changes no prediction — a brace measured 400 mm against a 600 mm design still predicts its neighbour at 970.820 mm, to every digit, and the mis-cut part the field guide exists to catch propagates nowhere. Four more: `INTEGRITY_THRESHOLD` gates a quantity that is a product of two fractions, so `integrity ≤ 1` is tested against **1.809** and the clause can never fire; `check()` keeps the minimum-error prediction over all sources, so a design with two routes of different product is **resolved in the measurement's favour and reported trusted at residual 0.000%** — the contradiction `audit()` exists to find, silently spent; `reconstruct()` promises a confidence-weighted average and implements first-writer-wins, so edges `a→x` at 2.0 and 5.0 give 2.0 or 5.0 by insertion order; and `IntegrityReport.reconstructed` is declared and never assigned. Both degeneracies now travel in `full_report()` as `predictions_use_measurements` and `threshold_clause_reachable`, the AISS remedy again. GI-1..7, `geometric_intelligence/falsifiers_gi_network.py`.

- **Temperature is now threaded, and the one correction that is wrong is wrong by 20×.** `fabrication/temperature.py` lands with `c_air`, `rho_air`, `thermal_expand` and the acoustic scaling — the correction the whole exercise needed, measured at **0.52% of exact** worst case over its stated −50…+50 °C range. `temp_c` is threaded through `pipe_modes`, `box_modes`, `cylinder_modes`, `ka_check`, `predict_eigenmodes_full` and `verify_sweep`, which now normalises the picked frequency before the verdict and carries `measured_raw` in the record. The bundle's versions of those three files were **not** taken wholesale: they strip the docstrings, including `eigenmodes.py`'s limitations block that `claim_back_modes.failure` cites, so only the threading was merged. **TMP-1 is the finding:** `k_correct` builds a stiffness correction from thermal expansion alone, reasoning that "E changes slightly with temperature; dominant effect is length" — for steel α = 12e-6/°C and dE/E ≈ −2.4e-4/°C, so the modulus term is **20× larger and opposite in sign**. At ΔT = +40 °C the module gives df/f = +0.024% where the physics gives −0.48%. It survives a bench test precisely because 0.024% is invisible against a ±8% band, which is why the check has to be a comparison of coefficients and not of outputs. **TMP-2** is the field guide's contraction table again, in executable form: five functions default `ref_temp_c` to 20 °C and three to 15 °C, and `normalize_measurement` passes its 15 into `r_correct`, whose TCR is the copper value specified *at 20* — a flat 2.0% bias. Also: two different corrections for one physics with their docstrings swapped (TMP-3), and `mu_water` 53% low at 100 °C returning the 0 °C value for every temperature below freezing, in a module written for a −40 °C workshop (TMP-4).

- **A trend detector whose only failure prediction is for the channel that is not failing.** `trend.py` groups a measurement log by scope, fits a line against time and classifies. Run on its own 20-point fixture the report reads: two scopes `failed` with `fail_in=N/A`, and `fail_in=1950.8d` on the **stable** one, extrapolated from an R² of 0.294 and quoted to a tenth of a day. Everything downstream shows up in those three lines. `fail_threshold = predicted·(1 + 2·tol)` is an **upper edge only**, so a value fallen 95% below its claim reads `drifting` (TRD-1); when a value is already past the threshold and falling, `predicted_fail_days` is the time to come back **inside** the band, in a field named for the opposite (TRD-2); there is no minimum-sample gate, and the residual sum of squares of a line through two points is exactly zero, so **any two readings give R² = 1.0** and classify as a trend (TRD-3); `abs(slope) < 1e-6` compares ohms, hertz and kelvin per day against one absolute constant (TRD-4). And the cross-domain correlation gates on `|r| > 0.6` with no null: the fixture's thermal and mechanical channels, two straight ramps with no stated physical link, correlate at exactly **r = 1.0000** — the gate is reporting that both are functions of time (TRD-5). It cannot fire on real data anyway, because the overlap is an exact float-timestamp intersection and the defaults compare the one pair that does *not* correlate (TRD-6). The regression itself is right, and asking where a parameter crosses its band is a question nothing else in this repository asks.

- **P-STALE-PATH is now mechanised.** Appending a test class after `if __name__ == "__main__":` defines it after `unittest.main()` has exited, so it never runs and the suite still reports OK — it has happened here before, at 21 classes. `tests/test_repo_guard.py` now compares each suite's declared `def test_` count against what `unittest` actually loads. The first attempt at this check was a grep for the guard string and produced a **false positive**: several suites contain that string as a literal, because they split another module's source on it. The count-based version is in; the grep-based one is not, and the docstring says why.

- **A cycle audit that checks each cycle at exactly one number.** `core.py`, `bridge.py`, the demo and the drop's own 20 tests arrived in a second drop, and the interim reconstruction was replaced. One positive result first: **`audit()` survives the null harness** — randomising every edge factor drops `integrity_score` from 2.000 to a mean of **0.014** over 200 draws, so it is measuring the geometry. What it measures it wrongly: `find_cycles` composes each cycle into an affine map `x → ax + b` and scores it as `|a·1 + b − 1|`, so **every map with `a + b = 1` passes without being the identity**. A cycle of `compose(2, −1)` reports closure error **0.000000**, counts CONSISTENT, gives integrity 2.0000 — and returns 19 for an input of 10. Both numbers that determine the map are computed in `_compose_transforms` and one is thrown away. Pure-`scale` cycles have `b = 0` and are safe, which is exactly why every demo and every shipped test misses it: they build only scale edges. **`correct()` is the second half of the same problem** — given the demo's own injected defect, an edge 23.6% high, it converges to +11.9% on that edge and −9.5% on its inverse partner and `audit()` then reports 5/5 consistent. It splits the error until the product closes rather than removing it; at the demo's `max_iter=5` it moves nothing measurable while printing "Edges modified: 10" between two identical scores. And **`integrity_score` is part geometry, part declaration**: `base_score × (1 + mean_edge_weight)` where `weight` is author-set confidence that only ever *adds*, so declaring every edge weight 0.0 still scores the full consistency fraction, and randomising weights alone spans 1.23–1.72 with the geometry untouched. Two modules now emit `integrity_score` with ranges [0, 2] and [0, 1] and compare both to 3.618. GI-8, GI-11..16.

- **Three of the drop's own 20 tests cannot fail, and the fixture is the sharp one.** `test_audit_passes` asserts `0 ≤ integrity_score ≤ INTEGRITY_THRESHOLD`, and `audit()` computes `min(base·(1+w), THRESHOLD)` with both factors non-negative — both bounds hold by construction. `test_hash_stable` hashes one unchanged object twice; the property its docstring claims, a hash of "topology and relations", is **false**, because `to_dict()` preserves insertion order and the same two nodes added the other way round hash differently. And `test_correct`'s fixture is commented "slightly wrong" with factors 2.5 and 0.4 — **2.5 × 0.4 = 1.0 exactly**, so the fixture is already consistent, both sides of the assertion are 0, and `correct()` — the function carrying two of this folder's findings — is never run on an inconsistent network by anything in the suite. The suite is vendored under `network/tests/` as evidence rather than deleted. GI-15, GI-16.

- **The fabrication bridge writes a zero it then divides by.** `network_to_claims` calls `audit()`, which returns `integrity_score = 0.0` when a network has no cycles — honest, since there is nothing to be consistent about, but unreadable in a ledger that cannot tell "no evidence" from "failed". `examples/demo.py` does exactly this: three parts in a correct φ chain, no reverse edges, and the ledger gets `integrity_score = 0.000000 ± 10%` with "0/0 cycles consistent". `verify_edge_measurement` then computes `100·(measured/pred − 1)` and raises `ZeroDivisionError` on it — reachable twice over, since a `rotate` edge declares an angle and 0 is legal. Also: the integrity claim's failure text describes a threshold test while the record encodes a two-sided band, three tolerances (0.05 / φ⁻⁹ / 0.10) have no source, the drift band is `(1±t)²` rather than a doubled tolerance, and `LEDGER` is a **relative** path at 24 sites across `bridge.py` and `fabrication/` — so running from the repo root and from `fabrication/` writes two ledgers that do not know about each other. GB-1..5.

- **What guessing a missing module got right and wrong.** While `core.py` was absent this folder carried a reconstruction built from what the supplied modules call. It got every attribute and method right and reproduced the timber-frame arithmetic exactly — and it got one thing wrong in the direction that matters: it **raised** `ZeroDivisionError` on a zero-factor inverse where the real file returns `float('inf')`. `integrity.reconstruct()` guards on that exception, so the reconstruction was *safer* than the original and would have hidden GI-14, where `inf` enters a reconstruction as if it were a value. Guessing the sensible behaviour is how you miss a bug. The two methods it refused to implement, `audit()` and `correct()`, both turned out to carry defects a plausible body would not have reproduced.

- **A φ-band spectrum analyser that drops the top of its own range and fires on noise.** `_compute_edges` multiplies by φ *while* the last edge is below `f_max`, so it exits after overshooting and then appends `f_max`: the edge list ends `[…, 9349, 15127, 10000]`, the final interval is reversed and **empty by construction**, the band below it runs past the `f_max` the caller asked for, and everything above 15 127 Hz is dropped without a word. `bands_per_octave` is stored and never read — 1 and 64 give byte-identical edges. The power-law fit that defines "expected" is built from **every populated band including the peaks it is used to judge**, contradicting its own comment, so an anomaly raises the baseline it is compared against and the bias is worst when there is most to find. And `detect_injection` has no noise model: on two independent draws of one Rayleigh process, with nothing injected, it flags **15.7% of bins** — the analytic figure for iid exponential ratios at that gate is 30.2%, so it is behaving exactly as its arithmetic says and `injection_score` cannot be read as a rate until a permutation null and a multiplicity correction exist. One comment was corrected outright: the gate is `ratio > 2.3156`, and it read "> ~1.315x baseline", low by 1.76×. GR-1..7.

- **Three numbers in the cold-weather field guide were wrong, and a field guide is used where nothing can check it.** The speed-of-sound correction said a prediction made at +20 °C reads "~6% low" at −40 °C; c(+20) = 343.4 and c(−40) = 307.1, so it is **10.6%** — against acoustic verdict bands of ±8%, that is the difference between a compensation that works and one that does not. (`331.3 + 0.606·T` is within 0.32% of exact at −40 °C and 0.52% at −50 °C, so the approximation was fine and only the arithmetic after it was wrong.) The contraction table gave percentages with **no reference temperature**, and back-solving the five rows found three different ones — +15 °C for the metals and concrete, +10 °C and 0 °C for the two wood rows; for timber the thermal term is in any case one to two orders below moisture movement, which a cold dry shop drives. And the worked timber-frame example built the network with forward edges only, which reports `brace_short` **untrusted on perfectly cut parts**, because nothing points at the first node of a one-way chain and the isolated-node branch marks it untrusted unconditionally. The README's nautilus example adds both directions; the field guide's did not, and the field guide is the one a person follows in a shop. All three are marked `[corrected]` in place with the arithmetic. GI-6, GI-7.

- **A glyph encoder that did not compile, and a sensor whose consistency check could not fail.** Two files landed in `bridges/` from a phone session with another model. `glyph_state_encoder.py` was two complete encoders pasted end to end — a second `from __future__ import annotations` at line 720 is a SyntaxError, so every import of the glyph layer failed, and the two halves shared only the twelve glyph *names*. Neither was a superset. Which half survived was decided by measurement: scored against exemplars built from the other half's declared `phase_space`, the rule ladder recovers **7 of 12** against the phase-space matcher's **4 of 12**; over 20 000 random reading sets they reach **11 and 5** of the twelve; and the empty reading set returns **VOID** from one and **FELT_COHERENT** from the other. What remains wrong in the survivor is recorded rather than patched, because every fix picks a number that is a claim about affect: `BLOCKAGE` is **unsatisfiable by arithmetic** (`pressure > 0.5 and total_magnitude < 0.5`, where pressure is a non-negative term of that total); the rule ladder returns on first match with the order undeclared, so `RE_NORMALIZE` swallows `HEAT_FLUX`'s own exemplar; `sub_glyphs` is decided by `_glyph_related(primary, glyph)` and never reads the measurement, so a constant travels into both `entropy()` and the wire format labelled "secondary states"; and the codec is lossy while documented as exact, with `uncertainty > 1.0` reachable from a legal reading and raising `struct.error`. Two more were fixed outright: the demo preferred a freshly constructed *empty* `SensorSuite` over the populated mock in its own `except ImportError` branch, classified six VOIDs and printed "operational"; and `encode()` needed `time`, imported only inside `__main__`, so the module raised `NameError` for every importer while the demo passed. GLY-0..7, `bridges/falsifiers_glyph_sensor.py`.

- **A scale inferred from the number it was going to be checked against.** `bridges/non_local_sensor.py` derives `scale` from `correlation_strength` and then selects `technique` from `scale`, so any "does the technique suit the scale" check returns a match for every input — **0 mismatches over 21 strengths spanning [0, 1]**, including both boundaries. A gate no input can fail is not a gate, and this is the AISS flat-weights shape again; the remedy is the same one, which is not to invent a disagreement but to report the degeneracy beside the answer, so `scale_is_inferred` now travels with every metadata dict. The map is also inverted with respect to its own purpose: weak correlation → largest scale, strong → smallest, so a **strong cross-system correlation — the observation the sensor exists to catch — is recorded as `cellular`** and cannot be expressed at all. Scale is a property of the *experiment* (what was sampled, over what extent, across what interval) and is knowable before the correlation is computed; passing it explicitly was already supported and nothing called it that way, which makes the fix a caller change and open problem NLS-A. Separately the spec path resolved into `../Emotions-as-Sensors/`, an unmounted sibling repo, so the class could not be constructed anywhere in this tree and the error named a path rather than `./fieldlink-sync.sh`. The spec is deliberately **not** reproduced here: guessing its contents would put a fabricated standard where the real one goes. NLS-1..4.

- **`test-the-distinguishing-operation` now has reach 3, across three formalisms that share no code.** It was extracted from `GIES-2` (`outer(v,v)` blind to the sign) and `KEA-7` (a Keating energy exactly even in the displacement); `GLY-3` is the third — vary every magnitude in a reading and the `sub_glyphs` field does not move. Still not mechanised, and `python graveyard.py todo` is where that stays visible. A second screen reached 2 on this pass: **`enumerate-reachable-outputs`**, which killed `BLOCKAGE` by inspection and diagnosed the phase-space matcher's 5-of-12, and which is mechanisable in a way the distinguishing screen probably is not.

- **The roadmap's speedup figure had never had a clock on it.** `docs/Implementation_Roadmap.md` stated every phase target as a multiple — 10x–100x, then 100x–1000x, then 1000x+ — and its one unchecked Month-1 item was *"Add basic benchmarks for EM field problems"*. `PerformanceTracker` reported `(32³ / n_points) × symmetry_reduction` as `averageSpeedup`: a ratio of point counts times a factor for work the solver does not skip, with `total_time` recorded in the same call and unused. Timed against a uniform grid on the same sources through the same optimizer — `generateUniformGrid` already existed and the solver had never called it — the adaptive path runs at **0.26x–0.48x, i.e. 2x to 50x slower**, against a reported 15x–33x faster. **The geometry is not what is wrong**: `SpatialGrid.createRegion` returns exactly one sample point per leaf region, so the solver makes 2150 numpy calls on 1-element arrays; the same points in one call take **0.0023 s against 0.0597 s**, a 26x overhead and a 27x gain available on the field evaluation. But the octree decomposition costs 0.0645 s against the uniform path's 0.0713 s total, so batching **alone** lands at 1.07x end to end — both halves have to come down, and knowing that before starting is worth more than the 26x. Left in place deliberately, as the roadmap's near-term item with the measurement attached rather than a multiplier. `Engine/engine_benchmark.py`, ENG-1/ENG-5.
- **Three smaller defects in the same metric, and one that moves opposite to the truth.** `naive_points` was hardcoded to 32³ while `resolution` was a documented parameter ("grid resolution per axis for uniform fallback") that reached nothing — there is no uniform fallback path, and resolutions 16, 32 and 64 gave identical point counts and an identical reported speedup (**ENG-2**, the fourth instance of the unread-parameter shape after `bands_per_octave`, `sub_glyphs` and `exploration_rate`). The ratio was multiplied by `symmetry_reduction`, which the call site's own comment describes as not taken — *"we compute all but report the potential reduction"* — so a symmetric configuration reported **1.50x more speedup while taking 1.89x more wall clock** (**ENG-3**). `averageSpeedup` reported the last run while `history` accumulated every run and was read by nothing: two runs at 15.24 and 22.88 reported 22.9 against a true mean of 19.06 (**ENG-4**). And `simdEfficiency` is `n_points / ceil(n_points/8)·8`, a function of array length alone — with one point per region it reports **12.5% for every configuration ever run**, identical for 1 charge and for 4 (**ENG-6**, recorded not fixed: it becomes informative for free once ENG-5 is addressed). The first three are fixed; the report now says "fewer points (not timed)" and names the benchmark.

- **A provenance log that does not reproduce under the code shipped beside it.** `adaptive_sim/` arrived as a 723-line claim-testing framework with two provenance logs and a plot. Its thesis is that a run is reproducible from its record, so the first thing done was to take that seriously and re-run the records from their logged fields. **All five replayable records mismatch.** A `fluctuating` outcome is a pure function of its parameters plus `base_seed` — `_run_replicate` reseeds from it and the model reads no other entropy — so a mismatch is evidence about the code, not the seeding. The decisive record is `db001b18502f`: it reproduces `fixation_probability` **exactly**, 0.65 / 0.35 / 0.0 to the digit, and disagrees only on `mean_fixation_time`, logged 0.0 against a recomputed **1053.575**. Same dynamics code, something changed around it, and nothing in the record could have said so — `run_id` was a hash of `time.time()` and there was no code identity in the record at all. Two further signatures sit in the log itself: `mean_fixation_time` is the float `0.0` rather than the integer the empty-list branch writes, and the four `num_steps = 3000` runs record nothing fixing where the shipped code fixes 97.5%. Fixed by making the record self-checking — `code_sha256`, a content-addressed `run_id` = H(code, model, params, seed), and `--verify`, which is the subcommand that found it. Its own first version defaulted `module` to `__import__(__name__)`, which returns the top-level package, so every default replay raised, filed the error in a field a caller could ignore, and read as a clean reproduction — the same shape it exists to catch, found by the test that tampers with a record and requires the verifier to notice. ASF-1, `adaptive_sim/AUDIT.md`.
- **A seed written into every record and passed to nothing.** The same framework logged `random_seed + iteration` while `np.random.seed` was called once, at loop entry. The forest model draws from the global stream, so iteration k>0 was not replayable at all — replaying record-seed 43 gives 375 trees where the run had 383. The model that *was* replayable was replayable through `base_seed`, the field not named seed; and `base_seed` being held fixed across iterations turns out to be correct, because it makes successive iterations a paired comparison, so it was right by accident and now says so. ASF-2.
- **An agent that could not turn the one knob its own diagnosis named.** `_generate_hypothesis` emitted a single string containing both "competition too weak" and "not at steady state"; `_propose_action` chose its branch by searching that string and tested the first substring first, so the `num_steps` branch could never fire. The shipped log is that defect in the wild: four iterations shrink `switching_rate` 0.3 → 0.103 with the outcome pinned at coexistence 1.000 the whole way, and the run that finally worked raised `num_steps` 3000 → 50000 — by hand, out of band, by the person running it. Fixed by making the reasoning chain carry structured tags rather than prose to be grepped; the landed loop drives the same failing configuration from coexistence 1.000 to 0.075 in four iterations by turning the knob the original could not. Compounding it, fed a *near-extinct* forest the original agent proposes `Increased competition_strength to 1.200` — the response to a dying forest is to kill it harder — because a test that **raised** was recorded as a refutation: `Claim.status` was set to `inconclusive` and then discarded one line later by `{'status': 'passed' if passed else 'failed'}`, and the shipped forest test formats `'N/A'` with `:.3f`. ASF-5/6/7.
- **Two claims that were about the simulation's budget rather than about biology.** `fluctuating_fixation` tests coexistence < 0.5, but replicates that hit `num_steps` without fixing were labelled "coexisting" — right-censoring reported as an outcome. Sweeping the step budget alone with every biological parameter fixed flips the verdict: 100 → 1.000 FAIL, 500 → 0.800 FAIL, **1000 → 0.375 PASS**, 10000 → 0.000 PASS; measured, the "coexisting" fraction and the censored fraction are equal to floating point. The same censoring biases the other number in the direction that hides it — `mean_fixation_time` averages only the replicates that fixed, discarding exactly the slowest, so at budget 500 it reads **366.4 against a true 1072.4**, low by 2.9× and looking converged at every stop. That is the second independent instance of `P-CENSORED-INPUT`, which was PROVISIONAL at one and is now ESTABLISHED. Separately, `forest_species_coexistence` returns the same FAIL for competitive exclusion and for an empty grid: over 5 seeds at every setting the agent can reach — competition at its 5.0 cap, dispersal at its floor, sparse start — richness is 3, 3, 3, 3, 3, and the only configuration that fails it is high mortality, where richness is 0 because the forest is dead. ASF-10/14.
- **A power-law claim that constrains straightness and not the slope.** `forest_power_law` gates on R² > 0.6 for a log-log fit of a log-binned histogram. Over 200 draws of 1000 samples the gate passes **100% of uniform[1,1000] draws at a mean slope of +0.919** — a distribution with more big trees than small passing a power-law claim — and 100% of lognormal(0,2), while rejecting exponential and gamma(2,10) at 0%. So it is not vacuous; it is unconstrained in the one direction that names it, and "R² is meaningless on log-binned data" would have been the easy verdict and is wrong. Underneath it, the histogram is never divided by bin width, so with logarithmic bins the fitted slope estimates **1 − α**, not −α: measured at α = 1.5/2.0/2.5/3.0 giving −0.473/−0.944/−1.442/−1.900. The shipped slopes of −0.369 and −0.412 are therefore density exponents near 1.4, a self-thinning −2 would appear as −1, and the framework's own auto-generated claim tests `slope < -1.5` — a threshold written in the other convention, on a "correlation with seed injection rate" that nothing sweeps, so it fails the moment it is created. None of the thresholds were changed: picking one is a claim about forests, and the degeneracies now travel beside the answer as `slope_is_positive`, `density_exponent` and `constrains`, which is the AISS `weights_are_flat` remedy again. ASF-8/9/15.
- **A rate used as a probability, and a knob wired to two mechanisms.** `switching_rate` builds a continuous-time generator and is then consumed as a per-step Bernoulli probability, so it saturates: rates 2.0, 5.0 and 50.0 give byte-identical outcomes, and the agent's exploration branch multiplies by 1.3, reaching saturation in seven steps from the shipped default while still "exploring". The forest's competition radius was `dispersal_range // 2`, so at `dispersal_range = 1` — reachable from the agent's own `max(1, dr + randint(-2, 3))` — local competition is exactly **0.000** while `competition_strength` stays logged at 0.8. Both recorded rather than patched, since fixing the first means choosing a time discretisation; the radius became an explicit parameter defaulting to the old expression, so behaviour is unchanged and the confound is nameable. And `exploration_rate` was stored and never read, the branch it names being a literal 0.5 — the third instance of the unread-parameter shape after GR-2's `bands_per_octave` and GLY-3's `sub_glyphs`. ASF-11/12/13.

- **A four-way router forked one way, and the branch that finds new ground could not fire.** `field/field_claim_loop.py`'s INSTRUMENT route appended a candidate whenever any anchor was logged — including at weight 0.0 for a perfectly stable rig — and NOVEL was guarded by `if hits and not cands`. So NOVEL was unreachable precisely when instrumentation was good, and the emitted experiment was "cross-check against a second transducer" when the answer was "spawn a claim". Compounding it, `anchor` is specified as "reading from the stability-reference channel" but tested as `abs(anchor) > 0`, which is a test on a *deviation*: fed an actual reading (1004 hPa), INSTRUMENT won every claim forever at weight 1.0. Both fixed; a route now contributes a candidate only with positive evidence, and NOVEL records the negative evidence it rests on. FCL-1/2.
- **A detector with a 22% false-alarm rate and 0% power, in the same configuration.** The NOISE_AS_SIGNAL branch tested `|autocorr(lag=3)| > 0.35` with no minimum-sample gate — on a series that holds *only* band-breaking readings, so small n is the normal case, not the edge: 23.5% false alarm at n=5, 21.9% at n=8. And for a periodic rider of period T, `ρ(lag) = cos(2π·lag/T)`, which at lag 3 is **exactly zero at T=12** and small at T ∈ {4, 10, 14, 16} — measured power 0.0% at those periods against 98–100% at T ∈ {6, 8, 24, 48}. A single fixed lag cannot detect structure in general. Replaced with a scan over lags 1–12 against a multiplicity-widened band: 2.6% on white noise, 100% power at T = 6, 12, 24. FCL-3/4.
- **`rate > 1.5 × base` fired on a third of null covariate sets, and got worse with more data.** The MISSING_VARIABLE branch had no significance test; the folder's own notes called it "too permissive" without measuring it. Null covariates independent of residuals: 34.7% (40 readings / 4 levels), 34.0% (200 / 8), **41.0%** (200 / 4 at base rate 0.10) — rising with n because more bins clear `MIN_SAMPLES` and each is another chance to fire. Replaced with an exact one-sided binomial tail, Bonferroni-corrected over bins actually tested: ≤0.8% on the same nulls, and it still finds a real rain-driven concentration at p = 1.2e-26. Separately, `hit + (r in hits)` was dict equality, so 20 duplicate readings with **one** actual residual reported "rate 1.00 under phase=dusk vs base 0.05". FCL-5/6.
- **Ten test files were not running at all, and nothing reported it.** `tests/test_silicon_modules.py` imported six modules from `Silicon.core.*` that a directory reorg had moved one level down into `analysis/`, `bridges/`, `geometry/`, `systems/` — 52 of its 66 tests errored in `setUp`. Nine more (`test_bridges.py` among them, the 768-test suite this file's own command list points at) lacked the `sys.path` bootstrap the other 25 test files carry, so the documented `python tests/test_bridges.py` raised `ModuleNotFoundError: No module named 'bridges'`. Both are fixed; all cases under `tests/` now run green from the repo root with no `PYTHONPATH`. An import error in `setUp` is reported as a test ERROR, not a collection failure, so a suite can be 79% dead and still look like it ran.
- **A shape-level test suite did not notice a 40% score change.** `AISS/sovereignty_evaluator.py` carried `score += 0.4  # placeholder for logical consistency`, so an entirely empty pattern scored 0.4 on internal coherence and the bottom 40% of the range was unreachable — an unmeasured term contributing a constant shifts every pattern equally and cannot separate any two of them. Removing it and renormalising `total_score` by the weight sum (a latent bug the flat 0.2 defaults were hiding: any other weighting silently rescaled the total and broke every threshold in the config) left all 27 of `tests/test_aiss.py` passing, because 26 of its 46 assertions are `assertIsInstance` / `assertIn` shape checks. `tests/test_aiss_scoring.py` adds the value-level checks. `logical_consistency` is now named in `unmeasured_components` rather than given a number.
- **Censoring a series does not blind a correlation — it biases it, which is worse.** The field loop fed its correlation branch the output of `test()`, which is 0.0 inside the claim band, keeping only the breaks. On a claim whose value drifts sinusoidally about the band centre (period 10 readings, amplitude 0.9), 120 readings became 87, and the censored series still came back STRUCTURED — at **lag 4 against a true half-period of 5**, |ρ| 0.79 versus 0.95 uncensored. A wrong answer delivered confidently. `deviation()` now gives the signed distance from band centre for every reading; `test()` stays censored because it answers a different question, and now says so. FCL-11.
- **Three of my own defects, found by testing the fixes rather than by reading them.** The slotted-autocorrelation default derived slot width from the record *span*, making each slot half a period wide against a 25 s rider sampled every 2.5 s — it reported ρ = 0.23 at an arbitrary 148.8 s where the truth was ρ = −0.99 at 12.5 s; slot width must track the *sampling interval*. The argmax lag is not a period: a rider peaks at every multiple of T/2, so noise picks the winner (median 8.8 s against a true T/2 of 3.0 s), and both textbook handles were measured and refused — smallest-significant is always slot 1 since ρ→1 as τ→0, and first-local-minimum ran biased low and worsened with period (7.5 s against a true 10.0). **No period is reported**; that is Lomb–Scargle's job. And both test fixtures broke the band on a fixed `i % 3` stride, which *is* a period-3 rider — once the series was uncensored the router correctly routed it to NOISE_AS_SIGNAL, the right answer to a question the fixture never meant to ask. FCL-12.
- **A recommended fix that mostly did not help, reported as such.** Swapping Bonferroni for Benjamini–Hochberg on the covariate scan is the right error target — FDR, not family-wise, since every finding gets re-tested by `next_query` — but BH rejects the k-th smallest p at k·α/m, and **at k=1 that is Bonferroni exactly**. With one true effect the two are identical: 85.2% recovery each. BH gains +4.6 points at two true effects, +1.8 at three, +0.6 at four. It never does worse, and that is the whole claim. The bigger lever turned out to be visible only once measured: the exact binomial tail is discrete, so the achieved level sits near **1%** against a nominal 5%, and that conservatism costs more power than the correction choice does. FCL-13.
- **The field loop's two open problems that were not closed, and why.** (5a) The anchor mechanism is built — `anchor_dev` is a declared deviation against an explicit `ANCHOR_TOL` — but *what the physical standard is* remains unspecified. It needs a reference whose failure mode differs from the working sensors', and that was not invented here. `ANCHOR_TOL` ships at 0.0, which for a float sensor means "any nonzero"; set it from the anchor's own noise floor before trusting INSTRUMENT. (5e) The conservation ledger is not implemented: the spend ledger counts query cost, which is not the reservoir, and the units were not stated so they were not guessed. Still open in a narrower form: a rider whose period exceeds the scanned lag range is invisible — `lag_range_s` is now reported so WHITE cannot quietly mean "white inside a window nobody named", but nothing widens it automatically.
- `field/field_claim_loop.py`'s `shape` is documented canonical ("Do NOT scalarize on ingest") and **no code path reads it** — `test()` compares `value` only, so every claim in the system is a claim about one scalar projection. Storing the shape without testing against it is scalarizing with a receipt. Partial fix only: a reading carrying a shape must now name the `projection` that produced `value`, making the scalarization explicit and auditable. What a shape-level band should *be* is a physics question, not a coding one. FCL-9.
- `AISS/AISS.md` and `AISS/AISS1.md` are the same document with two different preambles — bodies byte-identical, MD5 `59eb94de…`. Deleting one is safe; which preamble to keep is an editorial call, not a technical one.
- `Octahedral_State_Encoder` still carries a misleading name (its states are ⟨111⟩ bond directions, not octahedron vertices). Renaming it to `Bond_Direction_State_Encoder` touches `linked_sensors` across the Silicon specs, `Engine/gaussian_splats/octahedral.py`, and the GEIS `OctahedralState` class — repo-wide vocabulary, deferred deliberately.
