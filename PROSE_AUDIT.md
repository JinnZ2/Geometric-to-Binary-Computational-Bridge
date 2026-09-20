# PROSE_AUDIT — snapshot of `python repo_guard.py prose`, 2026-09-16 (fourth pass: the fixing pass)

> A VIEW. The authority is stage 5 of `repo_guard.py`; rerun it before trusting this file.
> Nothing here was auto-changed by the guard; the fixing pass below was applied by hand, line
> by line, in the order the fourth work order set, and each marked line is listed with its marker.
>
> Licence: the four surfaces agree on CC0-1.0 and every per-file header says CC0-1.0. Every
> remaining line that names another licence carries a `licence-ref` marker (convention below);
> the licence stage reports 0 unmarked.
>
> Nx claims: the classification of the third pass (MEASURED / DERIVED / DERIVED_WEAK / CARRIED /
> NOT-A-CLAIM) was the fixing order. A fixed line is not deleted and its number is not changed:
> it carries a claim-status marker saying what the number is (convention below), and the guard
> counts marked lines separately from unsupported claims. After the pass the guard's speedup
> stage reports 25 lines with no marker and no benchmark nearby, and all 25 are
> MEASURED, DERIVED (every operand sound) or NOT-A-CLAIM; no CARRIED line and no line with a
> dead or carried operand is left unmarked.

## Corrections ledger

Every correction this sequence made to a previously reported number, with its direction.

| pass | what was corrected | from | to | direction | how the number arrived |
|---|---|---|---|---|---|
| 1 | licence surfaces disagreeing | 4 values across 4 files | 1 (CC0-1.0) | shrank | inherited: the values were read off the files |
| 2 | licence ids != LICENSE, any tracked file | 46 headers + 15 prose lines | 15 prose lines | shrank | inherited: headers were rewritten, prose counted |
| 3 | licence ids unmarked | 15 | 0 | shrank | inherited: the 15 were marked, none was re-derived |
| 3 | Nx claims classed DERIVED | 51 | 13 DERIVED + 38 DERIVED_WEAK | **grew** | **recomputed**: each line's operands were classified first and the line inherited the weakest |
| 4 | Nx claims unmarked and unsupported | 129 | 25 | shrank | applied: 103 lines marked in four ordered groups (counts below) |

The DERIVED recount (51 -> 13) is the first correction in this sequence that made a reported
problem LARGER. The three shrinking corrections before it were all inherited numbers: values
read off files, headers rewritten, hits marked. The one that grew came from an ordered
recomputation, operands before lines. n = 1; recorded, not concluded from.
A prior pattern of the same shape ("110/7/1") was referenced from a different Claude Code
instance on a different tree; it is out-of-tree and unverified from here, and this ledger
stands alone.

## Fixing pass, counts after each group

| group | lines marked | guard speedup hits after | marker |
|---|---|---|---|
| (start) | | 129 | |
| DEAD operand, asserted (T₂ = 166 ms / ER-1; ENG-3 symmetry; ENG-1; 0.01 eV/bit below Landauer, marked refuted; 10 THz wrong band; the magnetic channel, FAB-1) | 33 | 96 | `[refuted: ...]` |
| DEAD operand, the line is itself the refutation | 3 | 92 | `[refutation of ...]` |
| CARRIED, no operands | 48 | 44 | `[unmeasured: ...]` |
| DERIVED_WEAK whose only defect is a CARRIED operand | 19 | 25 | `[unmeasured operand: ...]` |

The order's group sizes were 65 CARRIED and 35 DERIVED_WEAK. The pass found 17 of the 65
CARRIED lines rest on a dead operand (symmetry speedups on ENG-3, "15-30x" adaptive-vs-uniform
on ENG-1, "10x better than room-temp quantum memories" on ER-1, addendum figures on FAB-1) and
moved them into the DEAD group; of the 38 DERIVED_WEAK, 16 have a dead operand, 3 are
refutations, 19 have only a carried one. So: DEAD 33, refutation 3, CARRIED 48, carried-operand
19; 103 marked; 25 left, none of them carried.

## claim-status markers

A line that carries its own status is not an unsupported claim, and the guard says so
separately instead of counting it as a hit or letting it pass silently:

```
15-30x speedup [refuted: timed at 0.26-0.48x -- ENG-1, README Performance]
4-8x faster [unmeasured: never timed against a scalar path -- ENG-6]
32x total [unmeasured operand: the 8x SIMD factor, ENG-6]
166x better [refutation of ER-1]          (the line derives the number in order to kill it)
```

- `[refuted: <why, claim id, file>]` — something in the tree kills the figure. A bare
  `[refuted]` is a MARKER DEFECT and stays a hit: a refutation names what did the killing.
- `[unmeasured]` / `[unmeasured: <what is missing>]` — nothing in the tree produced the figure.
- `[unmeasured operand: <which>]` — arithmetic on such a figure.
- `[refutation of <id>]` — the line derives the number to refute its operand, not to assert it.
- The number is left in place. Deleting it would delete the record of what was claimed.

## benchmark markers, and the proximity split of the residual

The speedup stage accepts an Nx line when the word "benchmark" appears within 3 lines. That
is a proximity heuristic, and after the fixing pass 25 unmarked lines remained. Splitting
them: of the 9 MEASURED rows, only 2 were hitting because the benchmark reference sat
outside the 3-line window (CLAUDE.md's step-budget line, 5 lines from its mention;
docs/Implementation_Roadmap.md:41, 23 lines from its). The other 7 named no benchmark
anywhere near: Navigation.md's three ENG-1 lines are 237 lines from the file's nearest
mention, and Engine/CLAIMS.md and the falsifier survey never use the word. So proximity was
NOT the whole of the 9, and widening the window would not have reached 7 of them; it would
also let one mention vouch for every unrelated line within reach. The choice is the explicit
marker:

```
2x to 50x slower <!-- benchmark: Engine/engine_benchmark.py -->
```

- `<!-- benchmark: <path> -->` names the executable in the tree that produced or checks the
  figure on that line. The path must exist; a marker naming nothing in the tree is a MARKER
  DEFECT and stays a hit. Counted apart as `benchmark-marked`.
- `python claims_index.py render` emits the marker on every CLAIMS.md row whose claim has a
  FALSIFIER, naming that falsifier, so the generated tables carry their own evidence pointer.
- Applied to the 9 MEASURED rows (6 by hand, 3 generated). The residual is 14: 12 DERIVED
  rows (audit arithmetic on sourced constants: CLAUDE.md TMP-1 and GR-7, Fabrication.md's
  electromigration row and ADC multiplexing, Magnetic-bridge.md's two corrections,
  Proposal-addendum.md's bandwidth row, Proposal.md's RBS and piezo rows, Tensor-encode.md's
  3x triplet, optical_interface.md's mode-size row, ttm_audit.md's strain-vs-magnetic
  ratio) and 2 NOT-A-CLAIM rows (an INA128 amplifier gain, a FRET aperture ratio). These are
  REPORTED, not marked: a derived audit figure could carry the same marker naming the script
  that computes it (Silicon/magnetic_authority.py, Silicon/er_bounds.py, tests/test_gi_network.py),
  and the two gains want the detector to learn that "gain" is not a speedup; neither was done
  in this pass because the order asked for the split, not the fix.

## licence-ref markers

A line that names a licence other than this repo's is either a mismatch or a reference to
someone else's licence, and the guard cannot tell which from the identifier alone. The
convention is an inline marker that says which, and whose:

```
<!-- licence-ref: external, gods-eye-view data pack -->     in Markdown
"licence_ref": "external, gods-eye-view data pack"          in JSON
<!-- licence-ref: historical, REVIEW.md audit record of the pre-CC0 state -->
```

- `external` — the line describes another project's licence. The attribution after the
  comma is REQUIRED; a marker that names nobody is reported as a MARKER DEFECT.
- `historical` — the line is a record of a past state of THIS repo (REVIEW.md 32/33/37/253).
  The record is not edited; the marker says it is a record.
- A marked line is counted under `licence-ref external/historical (not a mismatch)` and is
  not a hit. The stage goes green only when every remaining non-canonical identifier is marked.
- Marking a line about this repo's own licence `external` is a defect the guard still
  catches: if the clause naming "this repo" carries a non-canonical identifier and no
  canonical one, the line is reported as `MARKER DEFECT: marked external but the line
  attributes MIT to this repo`. "MIT (their code) / CC0-1.0 (this repo)" passes;
  "this repo is MIT" under an external marker does not. tests/test_repo_guard.py has both.

```
  licence strings                   0 surface(s) disagree
  licence ids != LICENSE, unmarked 0
  licence-ref external   (not a mismatch) 10
      CLAUDE.md:771  [CC-BY-NC-SA]  gods-eye-view data pack
      CROSSLINKS.md:90  [MIT]  gods-eye-view code and data
      integrations/gods-eye-view/05-infrastructure/README.md:78  [CC-BY]  ecosystem repos and gods-eye-view data
      integrations/gods-eye-view/05-infrastructure/consent.json:5  [ODbL-1.0]  gods-eye-view data pack
      integrations/gods-eye-view/05-infrastructure/consent.json:8  [ODbL-1.0]  gods-eye-view data pack
      integrations/gods-eye-view/05-infrastructure/consent.json:11  [CC-BY-NC-SA-3.0]  gods-eye-view data pack
      integrations/gods-eye-view/05-infrastructure/consent.json:17  [PDDL-1.0]  gods-eye-view data pack
      integrations/gods-eye-view/05-infrastructure/consent.json:21  [CC-BY-4.0]  gods-eye-view live sources
      integrations/gods-eye-view/05-infrastructure/links.json:127  [CC-BY]  ecosystem repos and gods-eye-view data
      integrations/gods-eye-view/README.md:118  [MIT]  gods-eye-view code and data
  licence-ref historical (not a mismatch) 5
      CLAUDE.md:1025  [MIT]  the state the README audit found and this guard was built to catch
      REVIEW.md:32  [MIT]  REVIEW.md audit record of the pre-CC0 state
      REVIEW.md:33  [CC-BY-4.0]  REVIEW.md audit record of the pre-CC0 state
      REVIEW.md:37  [CC-BY-4.0]  REVIEW.md audit record of the pre-CC0 state
      REVIEW.md:253  [MIT]  REVIEW.md audit record of the pre-CC0 state
  speedup claims, no benchmark near 14
      CLAUDE.md:1041  - **Temperature is now threaded, and the one correction that is wrong is wrong b
      CLAUDE.md:1055  - **A φ-band spectrum analyser that drops the top of its own range and fires on 
      Universal-geometric-intelligence-P3.md:405  'instrumentation_amp': 'INA128, gain 100-1000×',
      Silicon/Fabrication.md:17  > | micro-coil at 10 mA | **100× OVER EM LIMIT** | 50 nm × 200 nm → J = 1e8 A/cm
      Silicon/Fabrication.md:2038  - Aggregate rate: 8× slower per sensor
      Silicon/Magnetic-bridge.md:35  > shortfall against 1 GHz channels is **714×**, not 700,000×, and the gradient
      Silicon/Magnetic-bridge.md:48  > magnitude only because a 12×-low coefficient was paired with a 10×-high
      Silicon/Proposal-addendum.md:37  > | 5 ps pulse can address a transition | **NO** | bandwidth ≈ 200 GHz (1/Δt) or
      Silicon/Proposal.md:67  > | RBS-C "sub-pm precision" | **WILL NOT SEE IT** | 5e11 cm⁻² areal against a 1
      Silicon/Proposal.md:84  > longitudinal coefficient is (π₁₁+π₁₂+π₄₄)/2 = **7.18e-10**, 12× larger, and it
      Silicon/Tensor-encode.md:153  Overhead: 3× storageBenefit: Tolerates any single-cell failure per triplet
      Silicon/optical_interface.md:200  | "3D light controls octahedral states" | **FATAL** | **Mode-size mismatch.** Di
      Silicon/ttm_audit.md:158  against **0.0845 meV** for 0.73 T. **Strain beats magnetic by ~1080× at
      Silicon/FRET/Fractalization.md:378  •	G (geometric gain): aperture/edge-cell area ratio, design 5–20×
  claim-status refuted             (not a claim) 33
  claim-status refutation of       (not a claim) 3
  claim-status unmeasured          (not a claim) 48
  claim-status unmeasured operand  (not a claim) 19
  benchmark-marked                  (names its executable) 11
      CLAUDE.md:1072  -> adaptive_sim/falsifiers_adaptive_sim.py
      Navigation.md:787  -> Engine/engine_benchmark.py
      Navigation.md:789  -> Engine/engine_benchmark.py
      Navigation.md:800  -> Engine/engine_benchmark.py
      Engine/CLAIMS.md:12  -> Engine/falsifiers_engine.py
      Engine/CLAIMS.md:14  -> Engine/falsifiers_engine.py
      Engine/CLAIMS.md:16  -> Engine/falsifiers_engine.py
      docs/Implementation_Roadmap.md:41  -> Engine/engine_benchmark.py
      fabrication/CLAIMS.md:12  -> geometric_intelligence/falsifiers_gi_network.py
      falsifier-survey/falsifier_survey_report_run2.md:125  -> Engine/engine_benchmark.py
      geometric_intelligence/CLAIMS.md:15  -> geometric_intelligence/falsifiers_gi_network.py
  shell commands that cannot run    28
      Navigation.md:675  shapebridge --demo --visualize  <- command not found: shapebridge
      Navigation.md:694  python em_coil_example.py  <- file missing: em_coil_example.py
      Navigation.md:697  python acoustic_cavity.py  <- file missing: acoustic_cavity.py
      Navigation.md:700  python fluid_obstacle.py  <- file missing: fluid_obstacle.py
      TRANSLATION_GUIDE.md:304  python Silicon/crystalline_nn_sim.py  <- file missing: Silicon/crystalline_nn_sim.py
      TRANSLATION_GUIDE.md:307  python Silicon/prototaxites_sim.py  <- file missing: Silicon/prototaxites_sim.py
      Universal-geometric-intelligence-P1.md:1673  python3 examples/sound_demo.py  <- file missing: examples/sound_demo.py
      GEIS/GEIS_organization.md:709  pip install -r geometric_encoding_system/requirements.txt --break-system-package  <- path missing: geometric_encoding_system/requirements.txt
      GEIS/build_summary.md:232  cd geometric_encoding_system  <- cd target missing: geometric_encoding_system
      GEIS/build_summary.md:233  python tests/test_core.py  <- file missing: tests/test_core.py
      GEIS/build_summary.md:239  python examples/demo.py  <- file missing: examples/demo.py
      GEIS/quick_start.md:29  cd geometric_encoding_system  <- cd target missing: geometric_encoding_system
      GEIS/quick_start.md:30  python tests/test_core.py  <- file missing: tests/test_core.py
      GEIS/quick_start.md:44  python examples/demo.py  <- file missing: examples/demo.py
      Silicon/COMPLETE_INDEX.v2.md:474  python master_optimizer.py  <- file missing: master_optimizer.py
      Silicon/COMPLETE_INDEX.v2.md:477  ls optimization_workspace/  <- path missing: optimization_workspace/
      Silicon/GIES.md:709  pip install -r geometric_encoding_system/requirements.txt --break-system-package  <- path missing: geometric_encoding_system/requirements.txt
      Silicon/INDEX.md:158  python master_optimizer.py  <- file missing: master_optimizer.py
      Silicon/QUICKSTART.md:34  python master_optimizer.py  <- file missing: master_optimizer.py
      Silicon/README-Architecture.md:96  cd dft_inputs/strain_0.0_site_O  <- cd target missing: dft_inputs/strain_0.0_site_O
      Silicon/README-Architecture.md:159  cd codoping_inputs/distance_3.0A  <- cd target missing: codoping_inputs/distance_3.0A
      Silicon/seed_physics.md:330  python seed_expansion.py  <- file missing: seed_expansion.py
      Silicon/seed_physics.md:333  python expansion_8d.py  <- file missing: expansion_8d.py
      Silicon/seed_physics.md:336  python reverse_engineering.py  <- file missing: reverse_engineering.py
      Silicon/seed_physics.md:339  python uniqueness_test.py  <- file missing: uniqueness_test.py
      geometric_intelligence/Multi-helix.md:44  python multi_helix_focus.py  <- file missing: multi_helix_focus.py
      geometric_intelligence/README.md:63  cd geometric-intelligence  <- cd target missing: geometric-intelligence
      geometric_intelligence/README.md:64  python geometric_intelligence.py  <- file missing: geometric_intelligence.py
  second-person address             1
      Mandala/ToDo.md:29  Auto-detects old octahedral table imports across your repos and
  filenames with a space            2
      Front end
      AISS/. well-known
  45 hit(s) -- each is a fix in a separate pass; nothing was changed
```

## Nx claims after the fixing pass and the benchmark markers

```
UNMARKED 14: DERIVED 12, NOT-A-CLAIM 2  (reported, not marked; see "benchmark markers" above)
MARKED  114: refuted 33, refutation-of 3, unmeasured 48, unmeasured-operand 19, benchmark-marked 11

### unmarked (14)
CLAUDE.md:1041  - **Temperature is now threaded, and the one correction that is wrong is wrong b
CLAUDE.md:1055  - **A φ-band spectrum analyser that drops the top of its own range and fires on 
Universal-geometric-intelligence-P3.md:405  'instrumentation_amp': 'INA128, gain 100-1000×',
Silicon/Fabrication.md:17  > | micro-coil at 10 mA | **100× OVER EM LIMIT** | 50 nm × 200 nm → J = 1e8 A/cm
Silicon/Fabrication.md:2038  - Aggregate rate: 8× slower per sensor
Silicon/Magnetic-bridge.md:35  > shortfall against 1 GHz channels is **714×**, not 700,000×, and the gradient
Silicon/Magnetic-bridge.md:48  > magnitude only because a 12×-low coefficient was paired with a 10×-high
Silicon/Proposal-addendum.md:37  > | 5 ps pulse can address a transition | **NO** | bandwidth ≈ 200 GHz (1/Δt) or
Silicon/Proposal.md:67  > | RBS-C "sub-pm precision" | **WILL NOT SEE IT** | 5e11 cm⁻² areal against a 1
Silicon/Proposal.md:84  > longitudinal coefficient is (π₁₁+π₁₂+π₄₄)/2 = **7.18e-10**, 12× larger, and it
Silicon/Tensor-encode.md:153  Overhead: 3× storageBenefit: Tolerates any single-cell failure per triplet
Silicon/optical_interface.md:200  | "3D light controls octahedral states" | **FATAL** | **Mode-size mismatch.** Di
Silicon/ttm_audit.md:158  against **0.0845 meV** for 0.73 T. **Strain beats magnetic by ~1080× at
Silicon/FRET/Fractalization.md:378  •	G (geometric gain): aperture/edge-cell area ratio, design 5–20×

### benchmark-marked (11) — the 9 MEASURED rows (6 by hand, 3 generated) plus the generator's other falsifier rows
CLAUDE.md:1072  -> adaptive_sim/falsifiers_adaptive_sim.py
Engine/CLAIMS.md:12  -> Engine/falsifiers_engine.py
Engine/CLAIMS.md:14  -> Engine/falsifiers_engine.py
Engine/CLAIMS.md:16  -> Engine/falsifiers_engine.py
Navigation.md:787  -> Engine/engine_benchmark.py
Navigation.md:789  -> Engine/engine_benchmark.py
Navigation.md:800  -> Engine/engine_benchmark.py
docs/Implementation_Roadmap.md:41  -> Engine/engine_benchmark.py
fabrication/CLAIMS.md:12  -> geometric_intelligence/falsifiers_gi_network.py
falsifier-survey/falsifier_survey_report_run2.md:125  -> Engine/engine_benchmark.py
geometric_intelligence/CLAIMS.md:15  -> geometric_intelligence/falsifiers_gi_network.py

### MEASURED (9), as classified in the third pass; now benchmark-marked
CLAUDE.md:1040  - **Two claims that were about the simulation's budget rather than about biology.** `fluctuating_fix
Navigation.md:787  > acceleration (10-100x additional speedup)"** was written on top of a reported
Navigation.md:789  > adaptive path runs at 0.26x-0.48x, i.e. slower, and the bottleneck is
Navigation.md:800  - ~~GPU acceleration (10-100x additional speedup)~~ — see the note above
Engine/CLAIMS.md:12  | ENG-1 | the reported geometric_speedup was a point-count ratio times a symmetry factor, with no cl
Engine/CLAIMS.md:14  | ENG-3 | the reported figure multiplied in a symmetry reduction the solver explicitly does not take
Engine/CLAIMS.md:16  | ENG-5 | SpatialGrid.createRegion emits one sample point per leaf region, so the solver makes one n
docs/Implementation_Roadmap.md:41  The adaptive path is **2× to 50× slower**, not 15–33× faster. ENG-1.
falsifier-survey/falsifier_survey_report_run2.md:125  "speedup" 11–16× where wall-clock measured 0.26–0.48×; in ENG-3 the proxy

### DERIVED (13), as classified in the third pass; 12 still unmarked, TMP-1's generated row now benchmark-marked
CLAUDE.md:1010  - **Temperature is now threaded, and the one correction that is wrong is wrong by 20×.** `fabricatio
    operands: α = 12e-6/°C and dE/E = −2.4e-4/°C, literature; asserted by tests/test_gi_network.py TMP-1
CLAUDE.md:1024  - **A φ-band spectrum analyser that drops the top of its own range and fires on noise.** `_compute_e
    operands: 2.3156 / 1.315, both constants read from geometric_intelligence/network/resonance.py
Silicon/Fabrication.md:17  > | micro-coil at 10 mA | **100× OVER EM LIMIT** | 50 nm × 200 nm → J = 1e8 A/cm² against a 1e6 desi
    operands: 10 mA over 50 nm × 200 nm (the document's own design input) against the 1e6 A/cm² electromigration limit; tests/test_magnetic_authority.py FAB-5
Silicon/Fabrication.md:2038  - Aggregate rate: 8× slower per sensor
    operands: 8 sensors on one ADC, the document's own design input; definitional
Silicon/Magnetic-bridge.md:35  > shortfall against 1 GHz channels is **714×**, not 700,000×, and the gradient
    operands: g·μ_B/h = 28.0 GHz/T, 1000 T/m × 50 nm; Silicon/magnetic_authority.py BRG-5
Silicon/Magnetic-bridge.md:48  > magnitude only because a 12×-low coefficient was paired with a 10×-high
    operands: π₁₁ vs (π₁₁+π₁₂+π₄₄)/2, literature; strain 1% vs 0.1%; magnetic_authority.PIEZO_NOTE, BRG-6
Silicon/Proposal-addendum.md:37  > | 5 ps pulse can address a transition | **NO** | bandwidth ≈ 200 GHz (1/Δt) or 88 GHz (Gaussian) a
    operands: 1/Δt at 5 ps against g·μ_B·B at 1–2 T; tests/test_transient_suppression.py R2-8
Silicon/Proposal.md:67  > | RBS-C "sub-pm precision" | **WILL NOT SEE IT** | 5e11 cm⁻² areal against a 1e13–1e14 RBS limit:
    operands: 5e11 cm⁻² areal from the stated dose against the 1e13–1e14 cm⁻² RBS limit, literature; ER-7
Silicon/Proposal.md:84  > longitudinal coefficient is (π₁₁+π₁₂+π₄₄)/2 = **7.18e-10**, 12× larger, and it
    operands: π coefficients, literature; magnetic_authority.PIEZO_NOTE
Silicon/Tensor-encode.md:153  Overhead: 3× storageBenefit: Tolerates any single-cell failure per triplet
    operands: three cells per bit, definitional
Silicon/optical_interface.md:200  | "3D light controls octahedral states" | **FATAL** | **Mode-size mismatch.** Diffraction limit in S
    operands: λ/2n = 1550/(2×3.48) nm against a = 0.543 nm, constants
Silicon/ttm_audit.md:158  against **0.0845 meV** for 0.73 T. **Strain beats magnetic by ~1080× at
    operands: Ξ_u = 9.16 eV × 1% against g·μ_B × 0.73 T; Silicon/magnetic_authority.py BRG-1
fabrication/CLAIMS.md:12  | TMP-1 | the mechanical resonance correction uses thermal expansion where the modulus term dominate
    operands: generated from CLAIMS_REGISTER.json; the TMP-1 operands above, tests/test_gi_network.py

### NOT-A-CLAIM (3), as classified in the third pass; 2 still unmarked, GB-4's generated row now benchmark-marked
Universal-geometric-intelligence-P3.md:405  'instrumentation_amp': 'INA128, gain 100-1000×',
Silicon/FRET/Fractalization.md:378  •	G (geometric gain): aperture/edge-cell area ratio, design 5–20×
geometric_intelligence/CLAIMS.md:15  | GB-4 | three unsourced tolerances (0.05 edge, phi^-9 cycle, 0.10 integrity) and a drift band of (1

### refuted (33)
GUIDE.md:143  **For efficiency:** The geometric EM solver achieves 15-30x speedup [refuted: ti
    [refuted: timed, the adaptive path runs at 0.26–0.48x of the uniform g]
GUIDE.md:178  | 15-30x | spatial speedup | Adaptive grid vs. uniform grid in EM solver [refute
    [refuted: timed, the adaptive path runs at 0.26–0.48x of the uniform g]
Mandala/01-octahedral-mapping.md:137  # With symmetry detection (Engine/symmetry_detector.py): 2–4× reduction [refuted
    [refuted: the solver computes every point and reports a symmetry reduc]
Mandala/01-octahedral-mapping.md:138  # Combined typical speedup vs uniform grid: ~15–30× [refuted: timed, the adaptiv
    [refuted: timed, the adaptive path runs at 0.26–0.48x of the uniform g]
Mandala/04-roadmap.md:29  ├── geometric_solver.py        EM field solver, symmetry-aware, ~15–30× speedup 
    [refuted: timed, the adaptive path runs at 0.26–0.48x of the uniform g]
Mandala/05-physics-connections.md:69  - SIMD-vectorised, ~15–30× speedup via octree + symmetry detection [refuted: tim
    [refuted: timed, the adaptive path runs at 0.26–0.48x of the uniform g]
Navigation.md:122  - Symmetry-reduced computation (2-10x speedup) [refuted: the solver computes eve
    [refuted: the solver computes every point and reports a symmetry reduc]
Navigation.md:395  **Why it matters:** A 6-fold symmetric pattern? Compute 1/6 of it, rotate copies
    [refuted: the solver computes every point and reports a symmetry reduc]
Navigation.md:405  = 6x speedup + perfect accuracy [refuted: the solver computes every point and re
    [refuted: the solver computes every point and reports a symmetry reduc]
Navigation.md:458  - 2-fold symmetry: 2x additional speedup [refuted: the solver computes every poi
    [refuted: the solver computes every point and reports a symmetry reduc]
Navigation.md:459  - 4-fold symmetry: 4x additional speedup [refuted: the solver computes every poi
    [refuted: the solver computes every point and reports a symmetry reduc]
Navigation.md:460  - 6-fold symmetry: 6x additional speedup [refuted: the solver computes every poi
    [refuted: the solver computes every point and reports a symmetry reduc]
Navigation.md:461  - Spherical symmetry: 10-100x additional speedup [refuted: the solver computes e
    [refuted: the solver computes every point and reports a symmetry reduc]
Silicon/COMPLETE_INDEX.v2.md:278  |**Write speed**  |1 THz        |**10 THz**  |✅ **10× better** [refuted: 1–10 TH
    [refuted: 1–10 THz sits 1.2–2.6 orders above ESR at 1–2 T (28–56 GHz),]
Silicon/COMPLETE_INDEX.v2.md:301  - T₂: 166 ms vs. 1 ms → **166× better** [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K 
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/COMPLETE_INDEX.v2.md:308  - T₂: 166 ms vs. 100 μs → **1660× better** [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/EXECUTIVE_SUMMARY.md:333  - 10× better than existing room-temp quantum memories [refuted: T₂ ≤ 2T₁ and Er³
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/FINAL_VALIDATION_REPORT.md:147  |NV centers in diamond          |~1 ms     |300 K      |**166× better** [refuted
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/FINAL_VALIDATION_REPORT.md:149  |Superconducting qubits         |~100 μs   |20 mK      |**1660× better** + room 
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/FINAL_VALIDATION_REPORT.md:292  |**Write Speed**         |~1 THz        |**10 THz** (parallel)|✓ **10× better** 
    [refuted: 1–10 THz sits 1.2–2.6 orders above ESR at 1–2 T (28–56 GHz),]
Silicon/FINAL_VALIDATION_REPORT.md:333  - ✓ **T₂ = 166 ms** (166× better than NV) [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/INDEX.md:342  **Impact**: 10× better than state-of-the-art room-temp quantum memory [refuted: 
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:90  •	2-20× faster than adiabatic [refuted: no magnetic state channel exists in Si; 
    [refuted: no magnetic state channel exists in Si; a 5 µm cell carries ]
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:102  •	3× pulse overhead acceptable for critical operations [refuted: no magnetic sta
    [refuted: no magnetic state channel exists in Si; a 5 µm cell carries ]
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:343  •	Read speed: 50ns → 25ns (2× faster) [refuted: no magnetic state channel exists
    [refuted: no magnetic state channel exists in Si; a 5 µm cell carries ]
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:347  •	Crosstalk: 1% → 0.1% (10× better) [refuted: no magnetic state channel exists i
    [refuted: no magnetic state channel exists in Si; a 5 µm cell carries ]
Silicon/Octahedral-computation.md:356  •	Compare to CMOS: ~100 fJ/bit → 100× more efficient [refuted: 0.01 eV is 0.56 k
    [refuted: 0.01 eV is 0.56 kT·ln2 at 300 K, below the Landauer bound, a]
Silicon/SYSTEM_ARCHITECTURE.md:11  - **166 ms coherence** at 300 K (166× better than NV centers) [refuted: T₂ ≤ 2T₁
    [refuted: T₂ ≤ 2T₁ and Er³⁺ T₁ at 300 K is ps–ns by Orbach relaxation ]
TRANSLATION_GUIDE.md:129  # -> 2080 adaptive grid points (vs 32768 for uniform grid: 15x speedup) [refuted
    [refuted: timed, the adaptive path runs at 0.26–0.48x of the uniform g]
Universal-geometric-intelligence-P2.md:1157  - Single reflection plane: Compute 1/2, mirror → **2× faster** [refuted: the sol
    [refuted: the solver computes every point and reports a symmetry reduc]
Universal-geometric-intelligence-P2.md:1158  - Two orthogonal planes: Compute 1/4 → **4× faster** [refuted: the solver comput
    [refuted: the solver computes every point and reports a symmetry reduc]
Universal-geometric-intelligence-P2.md:1161  **Combined with SIMD:** 8× (SIMD) × 4× (symmetry) = **32× total speedup** [refut
    [refuted: the solver computes every point and reports a symmetry reduc]
docs/GeneralOverview.md:14  - Symmetry Exploitation (2x-8x reduction) [refuted: the solver computes every po
    [refuted: the solver computes every point and reports a symmetry reduc]

### refutation of (3)
CLAUDE.md:1009  - **Er3+ cannot hold coherence at 300 K, and the flagship experiment has no targ
    [refutation of: ER-1]
Silicon/Energy-pattern.md:208  "$10M vs $300M, 10-30x capital reduction" [refutation of the quoted capital figu
    [refutation of: the quoted capital figure; no source]
Silicon/Proposal.md:24  > class, so 166 ms is **~8 orders high**. Grant a 1000× improvement on T₁ and it
    [refutation of: ER-1]

### unmeasured (48)
Mandala/01-octahedral-mapping.md:136  # With SIMD (Engine/simd_optimizer.py): 8× vectorised throughput [unmeasured: ne
    [unmeasured: never timed against a scalar path; the Engine reports SIMD e]
Mandala/04-roadmap.md:82  **Expected gain**: ~3× fewer residual vortices vs linear schedule; asymptoticall
    [unmeasured: no benchmark or device in the tree produced this figure]
Navigation.md:120  - SIMD-vectorized operations (4-8x speedup) [unmeasured: never timed against a s
    [unmeasured: never timed against a scalar path; the Engine reports SIMD e]
Navigation.md:121  - Cache-aware data layout (3-5x speedup) [unmeasured: no cache-layout experiment
    [unmeasured: no cache-layout experiment exists in the tree]
Navigation.md:123  - Combined: 50-200x faster than naive implementation [unmeasured: no benchmark o
    [unmeasured: no benchmark or device in the tree produced this figure]
Navigation.md:412  **What it means:** CPU cache is 100x faster than RAM. Organize data so CPU can u
    [unmeasured: no cache-layout experiment exists in the tree]
Navigation.md:423  = 3-5x speedup from same code, better arrangement [unmeasured: no cache-layout e
    [unmeasured: no cache-layout experiment exists in the tree]
Navigation.md:452  - SIMD auto-vectorization: 4-8x faster [unmeasured: never timed against a scalar
    [unmeasured: never timed against a scalar path; the Engine reports SIMD e]
Navigation.md:453  - Cache-aware layout: 2-3x faster [unmeasured: no cache-layout experiment exists
    [unmeasured: no cache-layout experiment exists in the tree]
Navigation.md:454  - Combined: 8-24x faster than naive code [unmeasured: no benchmark or device in 
    [unmeasured: no benchmark or device in the tree produced this figure]
Navigation.md:465  - Simple problems: 10-50x faster [unmeasured: no benchmark or device in the tree
    [unmeasured: no benchmark or device in the tree produced this figure]
Navigation.md:466  - Symmetric problems: 50-500x faster [unmeasured: no benchmark or device in the 
    [unmeasured: no benchmark or device in the tree produced this figure]
Navigation.md:467  - Best case (high symmetry + SIMD): 1000x faster [unmeasured: no benchmark or de
    [unmeasured: no benchmark or device in the tree produced this figure]
Navigation.md:483  - Impact: Iterate 100x more, discover faster [unmeasured: no benchmark or device
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/EXECUTIVE_SUMMARY.md:156  - 32 cores per job (2× speedup) [unmeasured: no benchmark or device in the tree 
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/FINAL_VALIDATION_REPORT.md:200  - **20× faster than individual sequential writes** [unmeasured: no benchmark or 
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/Fabrication.md:781  - Speedup: 2-3× vs. sequential [unmeasured: no benchmark or device in the tree p
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/Fabrication.md:940  •	Energy: 0.1-1 aJ/bit (10-100× better than CMOS) [unmeasured: no device exists;
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/Fabrication.md:1063  - Our approach: 100× energy improvement possible [unmeasured: no device exists; 
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/Fabrication.md:1209  Why? Works WITH physics, 100× energy advantage [unmeasured: no device exists; th
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/Fabrication.md:1933  Throughput: 8× single-cell performance [unmeasured: no benchmark or device in th
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/Fabrication.md:2380  ✅ 1000× faster writes (enables real-time processing) [unmeasured: no benchmark o
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/Fabrication.md:2563  ✅ Demonstrate clear advantages (100× power savings) [unmeasured: no device exist
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/Fabrication.md:2575  •	✅ Speed: 100-1000× faster writes [unmeasured: no benchmark or device in the tr
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/Fabrication.md:2700  - 100× energy advantage over incumbents [unmeasured: no device exists; the energ
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/README.md:30  •	1.6 aJ/bit energy efficiency (100× better than CMOS) [unmeasured: no device ex
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/SYSTEM_ARCHITECTURE.md:13  - **0.22 aJ/bit** energy efficiency (7× better than target) [unmeasured: no devi
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/SYSTEM_ARCHITECTURE.md:327  |**Write energy**    |0.22 aJ/bit|7× better than target [unmeasured: no device e
    [unmeasured: no device exists; the energy per bit is a design target, and]
Silicon/Tensor-encode.md:363  Advantage: 7-10× energy savings for compressible dataDisadvantage: Random access
    [unmeasured: no benchmark or device in the tree produced this figure]
Silicon/Tensor-encode.md:372  Compression: 10-100× for natural signals [unmeasured: no benchmark or device in 
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P1.md:61  - Result: 100-1000× lower computational cost for equivalent information [unmeasu
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P1.md:1601  **Speedup: 3-15× faster, 10-100× lower power** [unmeasured: no benchmark or devi
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P1.md:2015  ✓ **Efficient** - 10-100× less compute than ML [unmeasured: no benchmark or devi
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P2.md:1223  **Scaling:** With 8 cores, total speedup approaches **700×** [unmeasured: no ben
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P2.md:1400  **Combined speedup: 100-1000× vs. naive implementation** [unmeasured: no benchma
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P3.md:21  - **100× energy efficiency** vs. conventional memory [unmeasured: no device exis
    [unmeasured: no device exists; the energy per bit is a design target, and]
Universal-geometric-intelligence-P3.md:706  | Parallel speedup | 2-4× | Time-division or frequency multiplexing [unmeasured:
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P3.md:782  'radiation_hardness': '10× better (higher barriers)', [unmeasured: no benchmark 
    [unmeasured: no benchmark or device in the tree produced this figure]
Universal-geometric-intelligence-P3.md:995  - **Energy:** 100-10000× better than conventional [unmeasured: no device exists;
    [unmeasured: no device exists; the energy per bit is a design target, and]
Universal-geometric-intelligence-P3.md:1190  'octahedral_fit': 'Excellent (100× energy advantage)', [unmeasured: no device ex
    [unmeasured: no device exists; the energy per bit is a design target, and]
Universal-geometric-intelligence-P3.md:1358  'result': '100-1000× energy advantage' [unmeasured: no device exists; the energy
    [unmeasured: no device exists; the energy per bit is a design target, and]
Universal-geometric-intelligence-P3.md:1468  'Demonstrate clear advantages (100× energy)', [unmeasured: no device exists; the
    [unmeasured: no device exists; the energy per bit is a design target, and]
Universal-geometric-intelligence-P3.md:1559  ✅ **Performance projections** - 100-10000× energy advantage [unmeasured: no devi
    [unmeasured: no device exists; the energy per bit is a design target, and]
Universal-geometric-intelligence-P4.md:2193  1. **Energy-efficient computation** (100-1000× better than conventional) [unmeas
    [unmeasured: no device exists; the energy per bit is a design target, and]
docs/GeneralOverview.md:12  - SIMD Parallelism (8x practical speedup) [unmeasured: never timed against a sca
    [unmeasured: never timed against a scalar path; the Engine reports SIMD e]
docs/Transition_Strategy.md:12  - Gains: 10x–100x performance on real problems [unmeasured: no benchmark or devi
    [unmeasured: no benchmark or device in the tree produced this figure]
docs/Transition_Strategy.md:24  - Gains: 100x–1000x [unmeasured: no benchmark or device in the tree produced thi
    [unmeasured: no benchmark or device in the tree produced this figure]
docs/Transition_Strategy.md:36  - Gains: 1000x+ efficiency and emergent behavior [unmeasured: no benchmark or de
    [unmeasured: no benchmark or device in the tree produced this figure]

### unmeasured operand (19)
Navigation.md:377  **Why it matters:** If you’re computing a field at 1 million points, SIMD makes 
    [unmeasured operand: SIMD efficiency, never timed; a constant 12.5% in Performanc]
Navigation.md:386  = 4x speedup [unmeasured operand: SIMD efficiency — ENG-6]
    [unmeasured operand: SIMD efficiency — ENG-6]
Silicon/COMPLETE_INDEX.v2.md:275  |**Precision**    |< 0.5 nm     |**0.025 nm**|✅ **20× better** [unmeasured opera
    [unmeasured operand: 0.025 nm "achieved" was never measured, and RBS-C cannot res]
Silicon/COMPLETE_INDEX.v2.md:277  |**Energy/bit**   |< 1.6 aJ     |**0.22 aJ** |✅ **7× better** [unmeasured operan
    [unmeasured operand: 0.22 aJ/bit "achieved" was never measured]
Silicon/FINAL_VALIDATION_REPORT.md:289  |**Positional Precision**|< 0.5 nm      |**0.025 nm**         |✓ **20× better** 
    [unmeasured operand: 0.025 nm "achieved" was never measured, and RBS-C cannot res]
Silicon/FINAL_VALIDATION_REPORT.md:291  |**Energy per Bit**      |< 1.6 aJ/bit  |**0.22 aJ/bit**      |✓ **7× better** [
    [unmeasured operand: 0.22 aJ/bit "achieved" was never measured]
Silicon/Projects/LCEA.md:73  The embodied energy to **manufacture** AI hardware is 2.6× greater than the ener
    [unmeasured operand: E_Mfg per day; no source in the tree]
Six-sigma.md:298  - **Improvement factor: 4000x-280,000x better quality** [unmeasured operand: the
    [unmeasured operand: the 0.5σ baseline; nothing in the tree measured it]
Six-sigma.md:462  # Cost ratio: 10,100 / 155 = 65x more expensive to use defective equations [unme
    [unmeasured operand: 10,100 and 155 are stated, not measured]
Six-sigma.md:465  **“Efficient” equations are actually 65x MORE expensive when quality costs inclu
    [unmeasured operand: the 10,100 / 155 cost figures]
Six-sigma.md:488  But your Cost of Poor Quality is 65x higher. [unmeasured operand: the 10,100 / 1
    [unmeasured operand: the 10,100 / 155 cost figures]
Six-sigma.md:698  **4. “Efficient” equations are actually 65x more expensive** [unmeasured operand
    [unmeasured operand: the 10,100 / 155 cost figures]
Universal-geometric-intelligence-P2.md:332  Average compression: 250× [unmeasured operand: bearing sample counts; no code or
    [unmeasured operand: bearing sample counts; no code or data in the tree]
Universal-geometric-intelligence-P2.md:336  Healthy bearing: 6.1% loss, 280× compression → PASS [unmeasured operand: bearing
    [unmeasured operand: bearing sample counts; no code or data in the tree]
Universal-geometric-intelligence-P2.md:337  Worn bearing:    7.8% loss, 245× compression → PASS [unmeasured operand: bearing
    [unmeasured operand: bearing sample counts; no code or data in the tree]
Universal-geometric-intelligence-P2.md:338  Misaligned:      9.5% loss, 225× compression → PASS [unmeasured operand: bearing
    [unmeasured operand: bearing sample counts; no code or data in the tree]
Universal-geometric-intelligence-P2.md:344  - 200-300× compression: Removes measurement noise, keeps signal [unmeasured oper
    [unmeasured operand: bearing sample counts; no code or data in the tree]
Universal-geometric-intelligence-P2.md:955  - **Speedup: 8× with zero algorithm change** [unmeasured operand: SIMD efficienc
    [unmeasured operand: SIMD efficiency; 8 is the AVX-256 lane count, a ceiling — EN]
Universal-geometric-intelligence-P2.md:1396  ✅ **SIMD optimizer** - Parallel acceleration (8× typical) [unmeasured operand: S
    [unmeasured operand: SIMD efficiency — ENG-6]
```
