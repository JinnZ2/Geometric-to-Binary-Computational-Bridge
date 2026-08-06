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
python tests/test_repo_guard.py         # Null harness / symmetry veto / reach check (32 tests, no deps)
python tests/test_field_claim_loop.py   # Field claim loop: router + calibrated gates (93 tests, no deps)
python tests/test_playground.py         # Open bench: can each verdict actually fire (41 tests, no deps)
python tests/test_playground_review.py  # Archive provenance, principles, staleness (52 tests, no deps)
python tests/test_claims_index.py        # Claim index, register, salvage rule (52 tests, no deps)
python tests/test_graveyard.py           # Graveyard: deaths, screen reach, loose ends (26 tests, no deps)
python tests/test_explore.py             # Cross-folder view + the scope guard (30 tests, no deps)
python tests/test_aiss.py               # AISS framework shape/round-trip tests (27 tests, needs numpy)
python tests/test_aiss_scoring.py       # AISS scoring VALUES: placeholder removal, flat-weight null (26 tests)
python tests/test_experiments_topology.py # Vacuum tautology + vortex pinning (47 tests, needs numpy)

# Pre-commit guard: null harness, symmetry veto, instrument reach
python repo_guard.py

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

# Every suite under tests/ (2332 unittest cases; all pass, no PYTHONPATH needed)
for t in tests/test_*.py; do python "$t" || echo "FAILED $t"; done

# Runnable falsifier reports (stdlib, exit non-zero on failure)
python Silicon/falsifiers.py                  # ER-1/2/3, NEG-7, GIES-2/3
python Silicon/falsifiers_keating_seed.py     # KEA-1/3/7, SEED-1/3/5
python field/falsifiers_field_loop.py         # FCL-1..13 + the 5b hold-out

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

# Run GEIS demo
python GEIS/demo.py

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
| Gaussian Splats | `tests/test_gaussian_splats.py` | 63 | 4D / 8-state octahedral / 32-state rhombic splat encoders + dynamics |
| Negentropic (numpy) | `tests/test_negentropic.py` | 39 | R_e/A/D/L, agent network, Fokker-Planck conventions + conservation |
| Negentropic (stdlib) | `tests/test_negentropic_stdlib.py` | 155 | DissipativeCore, TUR/KUR bounds, Landauer, NEG-2/4/7/8/9/10/11, TRI-1..4, Ising emit, precession |
| Silicon check | `tests/test_silicon_check.py` | 29 | Thermal noise floor, strain invariants, orientation blindness (SIL-1), recovery channels |
| Tensor readout | `tests/test_tensor_readout.py` | 21 | sp3 rank deficiency (TTM-2), six-⟨110⟩ completeness (TTM-3) |
| Propulsion bounds | `tests/test_propulsion_bounds.py` | 27 | Momentum bound F≤P/v (FP-1), phase aliasing (FP-2), discriminating power (FP-3/5) |
| FP-4 autopilot | `tests/test_fp4_autopilot.py` | 66 | Anomaly-factor fit, identifiability guard (FP-6), firmware drive table (FP-7), two-sided null-world self-test |
| Energy-pattern | `tests/test_epg_bounds.py` | 38 | Cubic transport isotropy (EPG-7), tetrahedral maximin bound (EPG-6), DSA defect floor (EPG-4), mechanism discriminators (EPG-8) |
| Magnetic authority | `tests/test_magnetic_authority.py` | 67 | Hall/SQUID readout gap (FAB-1), Er vs host diamagnetism (FAB-2), electromigration (FAB-5), coil field and Zeeman authority (BRG-1), timing floors (BRG-2), gradient addressing (BRG-5), piezoresistive replacement (BRG-6) |
| Repo guard | `tests/test_repo_guard.py` | 32 | Null harness verdicts incl. CLAIM_FAILS, symmetry veto hits/silence, instrument reach bands |
| Explore | `tests/test_explore.py` | 30 | EX-1..4: coverage matrix, gap complement, folder-spanning principles, and the scope guard that keeps it from proposing |
| Graveyard | `tests/test_graveyard.py` | 26 | GY-1..5: death records, screen reach, a claimed mechanisation that does not exist, loose ends |
| Claim index | `tests/test_claims_index.py` | 52 | CI-1..5: evidence classes, family derivation without a denylist, every principle instance resolving to a real path and id, the register's live-without-a-falsifier check, underscore class names, generated-file exclusion, the dead-requires-salvage rule |
| Playground review | `tests/test_playground_review.py` | 52 | RV-1..6 + PR-1..5: threshold extraction, every review finding incl. a loosened tolerance under an unchanged verdict, the two-instance rule, git-blob source recovery |
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
└── Geometric-seed.py             Seed generation algorithm

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
playground/                     CC0 bench for what this repo has not solved
├── OPEN_PROBLEMS.json            15 open problems, machine-readable
├── playground.py                 Harness. Docstring is the contract.
├── review.py                     Re-scores the archive against today's gates
├── PRINCIPLES.json               11 recurring failure shapes, 36 instances
├── principles.py                 The library, and which shapes nothing catches
├── ARCHIVE.jsonl                 Durable: verdict + why + what would flip it
├── README.md                     The two gates, and why they are those two
└── candidates/
    ├── lomb_scargle_gls.py         SURVIVES — closes FCL-12b
    └── tautology_demo.py           REJECTED_UNFALSIFIABLE, on purpose
```

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

`PRINCIPLES.json` compresses ~60 findings across this archive into **11
recurring failure shapes** with 36 instances. Several turned up in files
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

The index classifies **130 claim ids by what can make each one FAIL**:
31 FALSIFIER, 55 NAMED_IN_TEST, 44 PROSE. So **86 of 130 have something
executable pointed at them** and 44 are written down with nothing that can
contradict them — not an error, since unrun bench work and definitions live
there legitimately, but a state worth being able to list. `NAMED_IN_TEST` is
named for what it actually measures: a suite mentions the id, which is weaker
than a test that asserts it. Claim families are derived from executable
evidence rather than a denylist, so `FNV-1a`, `AGPL-3` and `FR-4` drop out on
their own.

**Every folder that owns a claim family now has a generated `CLAIMS.md`** —
`Silicon/`, `GEIS/`, `field/`, `experiments/silicon_speculative/` — rendered
from `CLAIMS_REGISTER.json` plus the scan, so the table is a view and not a
second authority. `Negentropic/NEG_CLAIMS.md` is deliberately excluded: it is
the *source* the register parses for NEG/TRI, and generating a table there
would invert the authority.

The register carries only what scanning cannot establish — the statement,
whether it holds, and why not when it does not. **56 of 130 claims are
recorded; the other 74 are reported as unregistered rather than given
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
deleted rather than learned from. 27 of 56 carry salvage today.

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
from). **Two more have reach 2 and nothing catches them**: the gap-mode mass
criterion, which killed the $10k Er search and the phosphorus local-mode claim
in one stroke, and *test the distinguishing operation*, which is GIES-2 and
KEA-7 — the same blindness in two formalisms that never met. `graveyard.py
todo` is that list, and each entry is a mistake already paid for once. A screen
claiming a mechanisation is checked to name something that actually exists, so
the list cannot shorten by assertion.

**`explore.py` puts the whole archive in one view**, because every good result
here has been a cross-folder transfer that no folder could have found alone —
GIES-1 and KEA-7 are the same blindness in two formalisms that never met, and
`repo_guard`'s three stages each arrived from a different folder. The screens ×
families matrix is **sparse on purpose and that is the finding**: 13 screens
over 15 families, only 4 used in more than one. Each screen carries an
`applies_when` precondition, which is what keeps an empty cell an *absence*
rather than a suggestion — most are category errors and only a reader can tell
which. The file reports structure and does not propose combinations; a
generator of plausible pairs would have no ranking and no way to be wrong,
which is `P-UNFALSIFIABLE` wearing the shape of a research assistant. Tests
assert that refusal directly.

`graveyard.py loose` scans for the words a person writes when abandoning
something and reports files carrying them with no register entry — 7 today,
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
                                establish. 56 of 130 recorded; the rest are
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
- `Negentropic/emit_ising.py` does not yet inherit from `bridges/abstract_encoder.py`; the blocker is that an Ising spec has an n-dependent bit width while the other encoders emit fixed widths.
- `Negentropic/` entropy production is a housekeeping estimator with a known sign bias. A trajectory-level (MaxCal) estimate is needed before NEG-8 can be evaluated on simulated traces.
- NEG-2 and NEG-3 have falsifiers implemented but have not been run against data.
- `Silicon/field_propulsion_fp4.ino` is committed **unflashed** — no board was available here. Its phase-table logic is ported into `tests/test_fp4_autopilot.py` and verified against `propulsion_bounds.aliased_modes()`, but the timer backends (RP2040 / Teensy 4) and the HX711 and ADC paths are unexercised. Every calibration constant in it is a placeholder to be replaced by a bench measurement.
- `Silicon/fp4_autopilot.py`'s `ber_sweep()` raises `NotImplementedError` on the simulator by design; the §9.1 Bridge communication test needs either hardware or an explicit channel model, and a synthetic BER curve would reproduce the rigged-simulator defect the same file exists to guard against.
- **No magnetic state channel exists in silicon.** Five documents proposed one (`silicon_error_correction.json` v1, `octahedral_state_encoder.json` v1, `ttm_audit.md`'s fourth file, `Fabrication.md`, `Magnetic-bridge.md`). Si is diamagnetic at χ ~ −4e-6 and 95.3% of nuclei are spin-zero. A 5 µm cell carries 4e-19 A·m², 11 orders below a Hall sensor and 7 below a SQUID; 2 T buys 0.23 meV against a 10–100 meV barrier. The replacement is strain throughout: Ξ_u = 9.16 eV gives 9.2 meV of valley splitting at 0.1 % strain (40× the 2 T figure), written piezo/optomechanically and read piezoresistively at dR/R ≈ 9 % (GF ≈ 93). Full arithmetic in `Silicon/magnetic_authority.py`.
- **`repo_guard.py` is the pre-commit check that would have caught most of this archive's fatal findings.** Three mechanical stages: a null harness (does the result survive replacing structure with noise — killed the 17-lens isomorphism, the vacuum assertions, and topological attention's `run()`), a symmetry veto (does the material permit the mechanism — 9 instances across 6 files, free), and a reach check (is the signal above the instrument floor — the 11-order Hall gap, the 500x Er swamp, the RBS shortfall). Circular targets and unit errors are not mechanisable and get a human checklist.
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
- **A four-way router forked one way, and the branch that finds new ground could not fire.** `field/field_claim_loop.py`'s INSTRUMENT route appended a candidate whenever any anchor was logged — including at weight 0.0 for a perfectly stable rig — and NOVEL was guarded by `if hits and not cands`. So NOVEL was unreachable precisely when instrumentation was good, and the emitted experiment was "cross-check against a second transducer" when the answer was "spawn a claim". Compounding it, `anchor` is specified as "reading from the stability-reference channel" but tested as `abs(anchor) > 0`, which is a test on a *deviation*: fed an actual reading (1004 hPa), INSTRUMENT won every claim forever at weight 1.0. Both fixed; a route now contributes a candidate only with positive evidence, and NOVEL records the negative evidence it rests on. FCL-1/2.
- **A detector with a 22% false-alarm rate and 0% power, in the same configuration.** The NOISE_AS_SIGNAL branch tested `|autocorr(lag=3)| > 0.35` with no minimum-sample gate — on a series that holds *only* band-breaking readings, so small n is the normal case, not the edge: 23.5% false alarm at n=5, 21.9% at n=8. And for a periodic rider of period T, `ρ(lag) = cos(2π·lag/T)`, which at lag 3 is **exactly zero at T=12** and small at T ∈ {4, 10, 14, 16} — measured power 0.0% at those periods against 98–100% at T ∈ {6, 8, 24, 48}. A single fixed lag cannot detect structure in general. Replaced with a scan over lags 1–12 against a multiplicity-widened band: 2.6% on white noise, 100% power at T = 6, 12, 24. FCL-3/4.
- **`rate > 1.5 × base` fired on a third of null covariate sets, and got worse with more data.** The MISSING_VARIABLE branch had no significance test; the folder's own notes called it "too permissive" without measuring it. Null covariates independent of residuals: 34.7% (40 readings / 4 levels), 34.0% (200 / 8), **41.0%** (200 / 4 at base rate 0.10) — rising with n because more bins clear `MIN_SAMPLES` and each is another chance to fire. Replaced with an exact one-sided binomial tail, Bonferroni-corrected over bins actually tested: ≤0.8% on the same nulls, and it still finds a real rain-driven concentration at p = 1.2e-26. Separately, `hit + (r in hits)` was dict equality, so 20 duplicate readings with **one** actual residual reported "rate 1.00 under phase=dusk vs base 0.05". FCL-5/6.
- **Ten test files were not running at all, and nothing reported it.** `tests/test_silicon_modules.py` imported six modules from `Silicon.core.*` that a directory reorg had moved one level down into `analysis/`, `bridges/`, `geometry/`, `systems/` — 52 of its 66 tests errored in `setUp`. Nine more (`test_bridges.py` among them, the 768-test suite this file's own command list points at) lacked the `sys.path` bootstrap the other 25 test files carry, so the documented `python tests/test_bridges.py` raised `ModuleNotFoundError: No module named 'bridges'`. Both are fixed; all 2332 cases under `tests/` now run green from the repo root with no `PYTHONPATH`. An import error in `setUp` is reported as a test ERROR, not a collection failure, so a suite can be 79% dead and still look like it ran.
- **A shape-level test suite did not notice a 40% score change.** `AISS/sovereignty_evaluator.py` carried `score += 0.4  # placeholder for logical consistency`, so an entirely empty pattern scored 0.4 on internal coherence and the bottom 40% of the range was unreachable — an unmeasured term contributing a constant shifts every pattern equally and cannot separate any two of them. Removing it and renormalising `total_score` by the weight sum (a latent bug the flat 0.2 defaults were hiding: any other weighting silently rescaled the total and broke every threshold in the config) left all 27 of `tests/test_aiss.py` passing, because 26 of its 46 assertions are `assertIsInstance` / `assertIn` shape checks. `tests/test_aiss_scoring.py` adds the value-level checks. `logical_consistency` is now named in `unmeasured_components` rather than given a number.
- **Censoring a series does not blind a correlation — it biases it, which is worse.** The field loop fed its correlation branch the output of `test()`, which is 0.0 inside the claim band, keeping only the breaks. On a claim whose value drifts sinusoidally about the band centre (period 10 readings, amplitude 0.9), 120 readings became 87, and the censored series still came back STRUCTURED — at **lag 4 against a true half-period of 5**, |ρ| 0.79 versus 0.95 uncensored. A wrong answer delivered confidently. `deviation()` now gives the signed distance from band centre for every reading; `test()` stays censored because it answers a different question, and now says so. FCL-11.
- **Three of my own defects, found by testing the fixes rather than by reading them.** The slotted-autocorrelation default derived slot width from the record *span*, making each slot half a period wide against a 25 s rider sampled every 2.5 s — it reported ρ = 0.23 at an arbitrary 148.8 s where the truth was ρ = −0.99 at 12.5 s; slot width must track the *sampling interval*. The argmax lag is not a period: a rider peaks at every multiple of T/2, so noise picks the winner (median 8.8 s against a true T/2 of 3.0 s), and both textbook handles were measured and refused — smallest-significant is always slot 1 since ρ→1 as τ→0, and first-local-minimum ran biased low and worsened with period (7.5 s against a true 10.0). **No period is reported**; that is Lomb–Scargle's job. And both test fixtures broke the band on a fixed `i % 3` stride, which *is* a period-3 rider — once the series was uncensored the router correctly routed it to NOISE_AS_SIGNAL, the right answer to a question the fixture never meant to ask. FCL-12.
- **A recommended fix that mostly did not help, reported as such.** Swapping Bonferroni for Benjamini–Hochberg on the covariate scan is the right error target — FDR, not family-wise, since every finding gets re-tested by `next_query` — but BH rejects the k-th smallest p at k·α/m, and **at k=1 that is Bonferroni exactly**. With one true effect the two are identical: 85.2% recovery each. BH gains +4.6 points at two true effects, +1.8 at three, +0.6 at four. It never does worse, and that is the whole claim. The bigger lever turned out to be visible only once measured: the exact binomial tail is discrete, so the achieved level sits near **1%** against a nominal 5%, and that conservatism costs more power than the correction choice does. FCL-13.
- **The field loop's two open problems that were not closed, and why.** (5a) The anchor mechanism is built — `anchor_dev` is a declared deviation against an explicit `ANCHOR_TOL` — but *what the physical standard is* remains unspecified. It needs a reference whose failure mode differs from the working sensors', and that was not invented here. `ANCHOR_TOL` ships at 0.0, which for a float sensor means "any nonzero"; set it from the anchor's own noise floor before trusting INSTRUMENT. (5e) The conservation ledger is not implemented: the spend ledger counts query cost, which is not the reservoir, and the units were not stated so they were not guessed. Still open in a narrower form: a rider whose period exceeds the scanned lag range is invisible — `lag_range_s` is now reported so WHITE cannot quietly mean "white inside a window nobody named", but nothing widens it automatically.
- `field/field_claim_loop.py`'s `shape` is documented canonical ("Do NOT scalarize on ingest") and **no code path reads it** — `test()` compares `value` only, so every claim in the system is a claim about one scalar projection. Storing the shape without testing against it is scalarizing with a receipt. Partial fix only: a reading carrying a shape must now name the `projection` that produced `value`, making the scalarization explicit and auditable. What a shape-level band should *be* is a physics question, not a coding one. FCL-9.
- `AISS/AISS.md` and `AISS/AISS1.md` are the same document with two different preambles — bodies byte-identical, MD5 `59eb94de…`. Deleting one is safe; which preamble to keep is an editorial call, not a technical one.
- `Octahedral_State_Encoder` still carries a misleading name (its states are ⟨111⟩ bond directions, not octahedron vertices). Renaming it to `Bond_Direction_State_Encoder` touches `linked_sensors` across the Silicon specs, `Engine/gaussian_splats/octahedral.py`, and the GEIS `OctahedralState` class — repo-wide vocabulary, deferred deliberately.
