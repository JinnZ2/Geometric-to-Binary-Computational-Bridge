# PROSE_AUDIT — snapshot of `python repo_guard.py prose`, 2026-09-16 (third pass)

> A VIEW. The authority is stage 5 of `repo_guard.py`; rerun it before trusting this file.
> Every hit is a fix for a separate pass. Nothing here was auto-changed.
>
> Licence: the four surfaces agree on CC0-1.0 and every per-file header in this repo's own
> code and docs says CC0-1.0. Every remaining line that names another licence carries a
> `licence-ref` marker (convention below), so the licence stage reports 0 unmarked.
>
> Nx claims are classified at the bottom. MEASURED: a benchmark or sweep in the tree produced
> the number. DERIVED: arithmetic whose operands are all MEASURED, literature constants with a
> source in the tree, or the document's own design inputs. DERIVED_WEAK: arithmetic with at
> least one operand that is CARRIED (stated, no source in the tree) or DEAD (a claim the
> register killed); the weak operand and its file are named on each line, and `[refutation]`
> marks the three lines that derive the number in order to kill the operand rather than to
> assert it. CARRIED: no operands, no benchmark. NOT-A-CLAIM: the detector matched a gain or
> an exponent. DERIVED inherits its weakest operand, so the 51 of the second pass was an upper
> bound; the recount is 13 DERIVED and 38 DERIVED_WEAK. The CARRIED list is the fixing order
> and is held until this recount has been read.

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
      CLAUDE.md:740  [CC-BY-NC-SA]  gods-eye-view data pack
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
      CLAUDE.md:994  [MIT]  the state the README audit found and this guard was built to catch
      REVIEW.md:32  [MIT]  REVIEW.md audit record of the pre-CC0 state
      REVIEW.md:33  [CC-BY-4.0]  REVIEW.md audit record of the pre-CC0 state
      REVIEW.md:37  [CC-BY-4.0]  REVIEW.md audit record of the pre-CC0 state
      REVIEW.md:253  [MIT]  REVIEW.md audit record of the pre-CC0 state
  speedup claims, no benchmark near 128
      CLAUDE.md:1001  - **Er3+ cannot hold coherence at 300 K, and the flagship experiment has no targ
      CLAUDE.md:1010  - **Temperature is now threaded, and the one correction that is wrong is wrong b
      CLAUDE.md:1024  - **A φ-band spectrum analyser that drops the top of its own range and fires on 
      CLAUDE.md:1040  - **Two claims that were about the simulation's budget rather than about biology
      GUIDE.md:143  **For efficiency:** The geometric EM solver achieves 15-30x speedup
      GUIDE.md:178  | 15-30x | spatial speedup | Adaptive grid vs. uniform grid in EM solver |
      Navigation.md:120  - SIMD-vectorized operations (4-8x speedup)
      Navigation.md:121  - Cache-aware data layout (3-5x speedup)
      Navigation.md:122  - Symmetry-reduced computation (2-10x speedup)
      Navigation.md:123  - Combined: 50-200x faster than naive implementation
      Navigation.md:377  **Why it matters:** If you’re computing a field at 1 million points, SIMD makes 
      Navigation.md:386  = 4x speedup
      Navigation.md:395  **Why it matters:** A 6-fold symmetric pattern? Compute 1/6 of it, rotate copies
      Navigation.md:405  = 6x speedup + perfect accuracy
      Navigation.md:412  **What it means:** CPU cache is 100x faster than RAM. Organize data so CPU can u
      Navigation.md:423  = 3-5x speedup from same code, better arrangement
      Navigation.md:452  - SIMD auto-vectorization: 4-8x faster
      Navigation.md:453  - Cache-aware layout: 2-3x faster
      Navigation.md:454  - Combined: 8-24x faster than naive code
      Navigation.md:458  - 2-fold symmetry: 2x additional speedup
      Navigation.md:459  - 4-fold symmetry: 4x additional speedup
      Navigation.md:460  - 6-fold symmetry: 6x additional speedup
      Navigation.md:461  - Spherical symmetry: 10-100x additional speedup
      Navigation.md:465  - Simple problems: 10-50x faster
      Navigation.md:466  - Symmetric problems: 50-500x faster
      Navigation.md:467  - Best case (high symmetry + SIMD): 1000x faster
      Navigation.md:483  - Impact: Iterate 100x more, discover faster
      Navigation.md:787  > acceleration (10-100x additional speedup)"** was written on top of a reported
      Navigation.md:789  > adaptive path runs at 0.26x-0.48x, i.e. slower, and the bottleneck is
      Navigation.md:800  - ~~GPU acceleration (10-100x additional speedup)~~ — see the note above
      Six-sigma.md:298  - **Improvement factor: 4000x-280,000x better quality**
      Six-sigma.md:462  # Cost ratio: 10,100 / 155 = 65x more expensive to use defective equations
      Six-sigma.md:465  **“Efficient” equations are actually 65x MORE expensive when quality costs inclu
      Six-sigma.md:488  But your Cost of Poor Quality is 65x higher.
      Six-sigma.md:698  **4. “Efficient” equations are actually 65x more expensive**
      TRANSLATION_GUIDE.md:129  # -> 2080 adaptive grid points (vs 32768 for uniform grid: 15x speedup)
      Universal-geometric-intelligence-P1.md:61  - Result: 100-1000× lower computational cost for equivalent information
      Universal-geometric-intelligence-P1.md:1601  **Speedup: 3-15× faster, 10-100× lower power**
      Universal-geometric-intelligence-P1.md:2015  ✓ **Efficient** - 10-100× less compute than ML
      Universal-geometric-intelligence-P2.md:332  Average compression: 250×
      Universal-geometric-intelligence-P2.md:336  Healthy bearing: 6.1% loss, 280× compression → PASS
      Universal-geometric-intelligence-P2.md:337  Worn bearing:    7.8% loss, 245× compression → PASS
      Universal-geometric-intelligence-P2.md:338  Misaligned:      9.5% loss, 225× compression → PASS
      Universal-geometric-intelligence-P2.md:344  - 200-300× compression: Removes measurement noise, keeps signal
      Universal-geometric-intelligence-P2.md:955  - **Speedup: 8× with zero algorithm change**
      Universal-geometric-intelligence-P2.md:1157  - Single reflection plane: Compute 1/2, mirror → **2× faster**
      Universal-geometric-intelligence-P2.md:1158  - Two orthogonal planes: Compute 1/4 → **4× faster**
      Universal-geometric-intelligence-P2.md:1161  **Combined with SIMD:** 8× (SIMD) × 4× (symmetry) = **32× total speedup**
      Universal-geometric-intelligence-P2.md:1223  **Scaling:** With 8 cores, total speedup approaches **700×**
      Universal-geometric-intelligence-P2.md:1396  ✅ **SIMD optimizer** - Parallel acceleration (8× typical)
      Universal-geometric-intelligence-P2.md:1400  **Combined speedup: 100-1000× vs. naive implementation**
      Universal-geometric-intelligence-P3.md:21  - **100× energy efficiency** vs. conventional memory
      Universal-geometric-intelligence-P3.md:405  'instrumentation_amp': 'INA128, gain 100-1000×',
      Universal-geometric-intelligence-P3.md:706  | Parallel speedup | 2-4× | Time-division or frequency multiplexing |
      Universal-geometric-intelligence-P3.md:782  'radiation_hardness': '10× better (higher barriers)',
      Universal-geometric-intelligence-P3.md:995  - **Energy:** 100-10000× better than conventional
      Universal-geometric-intelligence-P3.md:1190  'octahedral_fit': 'Excellent (100× energy advantage)',
      Universal-geometric-intelligence-P3.md:1358  'result': '100-1000× energy advantage'
      Universal-geometric-intelligence-P3.md:1468  'Demonstrate clear advantages (100× energy)',
      Universal-geometric-intelligence-P3.md:1559  ✅ **Performance projections** - 100-10000× energy advantage
      Universal-geometric-intelligence-P4.md:2193  1. **Energy-efficient computation** (100-1000× better than conventional)
      Engine/CLAIMS.md:12  | ENG-1 | the reported geometric_speedup was a point-count ratio times a symmetr
      Engine/CLAIMS.md:14  | ENG-3 | the reported figure multiplied in a symmetry reduction the solver expl
      Engine/CLAIMS.md:16  | ENG-5 | SpatialGrid.createRegion emits one sample point per leaf region, so th
      Mandala/01-octahedral-mapping.md:136  # With SIMD (Engine/simd_optimizer.py): 8× vectorised throughput
      Mandala/01-octahedral-mapping.md:137  # With symmetry detection (Engine/symmetry_detector.py): 2–4× reduction
      Mandala/01-octahedral-mapping.md:138  # Combined typical speedup vs uniform grid: ~15–30×
      Mandala/04-roadmap.md:29  ├── geometric_solver.py        EM field solver, symmetry-aware, ~15–30× speedup
      Mandala/04-roadmap.md:82  **Expected gain**: ~3× fewer residual vortices vs linear schedule; asymptoticall
      Mandala/05-physics-connections.md:69  - SIMD-vectorised, ~15–30× speedup via octree + symmetry detection
      Silicon/COMPLETE_INDEX.v2.md:275  |**Precision**    |< 0.5 nm     |**0.025 nm**|✅ **20× better**|
      Silicon/COMPLETE_INDEX.v2.md:277  |**Energy/bit**   |< 1.6 aJ     |**0.22 aJ** |✅ **7× better** |
      Silicon/COMPLETE_INDEX.v2.md:278  |**Write speed**  |1 THz        |**10 THz**  |✅ **10× better**|
      Silicon/COMPLETE_INDEX.v2.md:301  - T₂: 166 ms vs. 1 ms → **166× better**
      Silicon/COMPLETE_INDEX.v2.md:308  - T₂: 166 ms vs. 100 μs → **1660× better**
      Silicon/EXECUTIVE_SUMMARY.md:156  - 32 cores per job (2× speedup)
      Silicon/EXECUTIVE_SUMMARY.md:333  - 10× better than existing room-temp quantum memories
      Silicon/Energy-pattern.md:208  "$10M vs $300M, 10-30x capital reduction"
      Silicon/FINAL_VALIDATION_REPORT.md:147  |NV centers in diamond          |~1 ms     |300 K      |**166× better**         
      Silicon/FINAL_VALIDATION_REPORT.md:149  |Superconducting qubits         |~100 μs   |20 mK      |**1660× better** + room 
      Silicon/FINAL_VALIDATION_REPORT.md:200  - **20× faster than individual sequential writes**
      Silicon/FINAL_VALIDATION_REPORT.md:289  |**Positional Precision**|< 0.5 nm      |**0.025 nm**         |✓ **20× better** 
      Silicon/FINAL_VALIDATION_REPORT.md:291  |**Energy per Bit**      |< 1.6 aJ/bit  |**0.22 aJ/bit**      |✓ **7× better**  
      Silicon/FINAL_VALIDATION_REPORT.md:292  |**Write Speed**         |~1 THz        |**10 THz** (parallel)|✓ **10× better** 
      Silicon/FINAL_VALIDATION_REPORT.md:333  - ✓ **T₂ = 166 ms** (166× better than NV)
      Silicon/Fabrication.md:17  > | micro-coil at 10 mA | **100× OVER EM LIMIT** | 50 nm × 200 nm → J = 1e8 A/cm
      Silicon/Fabrication.md:781  - Speedup: 2-3× vs. sequential
      Silicon/Fabrication.md:940  •	Energy: 0.1-1 aJ/bit (10-100× better than CMOS)
      Silicon/Fabrication.md:1063  - Our approach: 100× energy improvement possible
      Silicon/Fabrication.md:1209  Why? Works WITH physics, 100× energy advantage
      Silicon/Fabrication.md:1933  Throughput: 8× single-cell performance
      Silicon/Fabrication.md:2038  - Aggregate rate: 8× slower per sensor
      Silicon/Fabrication.md:2380  ✅ 1000× faster writes (enables real-time processing)
      Silicon/Fabrication.md:2563  ✅ Demonstrate clear advantages (100× power savings)
      Silicon/Fabrication.md:2575  •	✅ Speed: 100-1000× faster writes
      Silicon/Fabrication.md:2700  - 100× energy advantage over incumbents
      Silicon/INDEX.md:342  **Impact**: 10× better than state-of-the-art room-temp quantum memory
      Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:90  •	2-20× faster than adiabatic
      Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:102  •	3× pulse overhead acceptable for critical operations
      Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:343  •	Read speed: 50ns → 25ns (2× faster)
      Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:347  •	Crosstalk: 1% → 0.1% (10× better)
      Silicon/Magnetic-bridge.md:35  > shortfall against 1 GHz channels is **714×**, not 700,000×, and the gradient
      Silicon/Magnetic-bridge.md:48  > magnitude only because a 12×-low coefficient was paired with a 10×-high
      Silicon/Octahedral-computation.md:356  •	Compare to CMOS: ~100 fJ/bit → 100× more efficient
      Silicon/Proposal-addendum.md:37  > | 5 ps pulse can address a transition | **NO** | bandwidth ≈ 200 GHz (1/Δt) or
      Silicon/Proposal.md:24  > class, so 166 ms is **~8 orders high**. Grant a 1000× improvement on T₁ and it
      Silicon/Proposal.md:67  > | RBS-C "sub-pm precision" | **WILL NOT SEE IT** | 5e11 cm⁻² areal against a 1
      Silicon/Proposal.md:84  > longitudinal coefficient is (π₁₁+π₁₂+π₄₄)/2 = **7.18e-10**, 12× larger, and it
      Silicon/README.md:30  •	1.6 aJ/bit energy efficiency (100× better than CMOS)
      Silicon/SYSTEM_ARCHITECTURE.md:11  - **166 ms coherence** at 300 K (166× better than NV centers)
      Silicon/SYSTEM_ARCHITECTURE.md:13  - **0.22 aJ/bit** energy efficiency (7× better than target)
      Silicon/SYSTEM_ARCHITECTURE.md:327  |**Write energy**    |0.22 aJ/bit|7× better than target|
      Silicon/Tensor-encode.md:153  Overhead: 3× storageBenefit: Tolerates any single-cell failure per triplet
      Silicon/Tensor-encode.md:363  Advantage: 7-10× energy savings for compressible dataDisadvantage: Random access
      Silicon/Tensor-encode.md:372  Compression: 10-100× for natural signals
      Silicon/optical_interface.md:200  | "3D light controls octahedral states" | **FATAL** | **Mode-size mismatch.** Di
      Silicon/ttm_audit.md:158  against **0.0845 meV** for 0.73 T. **Strain beats magnetic by ~1080× at
      Silicon/FRET/Fractalization.md:378  •	G (geometric gain): aperture/edge-cell area ratio, design 5–20×
      Silicon/Projects/LCEA.md:73  The embodied energy to **manufacture** AI hardware is 2.6× greater than the ener
      docs/GeneralOverview.md:12  - SIMD Parallelism (8x practical speedup)
      docs/GeneralOverview.md:14  - Symmetry Exploitation (2x-8x reduction)
      docs/Implementation_Roadmap.md:41  The adaptive path is **2× to 50× slower**, not 15–33× faster. ENG-1.
      docs/Transition_Strategy.md:12  - Gains: 10x–100x performance on real problems
      docs/Transition_Strategy.md:24  - Gains: 100x–1000x
      docs/Transition_Strategy.md:36  - Gains: 1000x+ efficiency and emergent behavior
      fabrication/CLAIMS.md:12  | TMP-1 | the mechanical resonance correction uses thermal expansion where the m
      falsifier-survey/falsifier_survey_report_run2.md:125  "speedup" 11–16× where wall-clock measured 0.26–0.48×; in ENG-3 the proxy
      geometric_intelligence/CLAIMS.md:15  | GB-4 | three unsourced tolerances (0.05 edge, phi^-9 cycle, 0.10 integrity) an
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
  159 hit(s) -- each is a fix in a separate pass; nothing was changed
```

## Nx claims, classified

```
TOTAL 128 MEASURED 9 DERIVED 13 DERIVED_WEAK 38 (of which refutation 3) CARRIED 65 NOT-A-CLAIM 3

### MEASURED (9)
CLAUDE.md:1040  - **Two claims that were about the simulation's budget rather than about biology.** `fluctuating_fix
Navigation.md:787  > acceleration (10-100x additional speedup)"** was written on top of a reported
Navigation.md:789  > adaptive path runs at 0.26x-0.48x, i.e. slower, and the bottleneck is
Navigation.md:800  - ~~GPU acceleration (10-100x additional speedup)~~ — see the note above
Engine/CLAIMS.md:12  | ENG-1 | the reported geometric_speedup was a point-count ratio times a symmetry factor, with no cl
Engine/CLAIMS.md:14  | ENG-3 | the reported figure multiplied in a symmetry reduction the solver explicitly does not take
Engine/CLAIMS.md:16  | ENG-5 | SpatialGrid.createRegion emits one sample point per leaf region, so the solver makes one n
docs/Implementation_Roadmap.md:41  The adaptive path is **2× to 50× slower**, not 15–33× faster. ENG-1.
falsifier-survey/falsifier_survey_report_run2.md:125  "speedup" 11–16× where wall-clock measured 0.26–0.48×; in ENG-3 the proxy

### DERIVED (13) — every operand MEASURED, a sourced constant, or the document's own design input
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

### DERIVED_WEAK (38) — inherits a CARRIED or DEAD operand; weak operand and file named
CLAUDE.md:1001  - **Er3+ cannot hold coherence at 300 K, and the flagship experiment has no target.** `Proposal.md`
    weak operand [refutation]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Navigation.md:377  **Why it matters:** If you’re computing a field at 1 million points, SIMD makes it 4-16x faster auto
    weak operand [asserted]: SIMD efficiency = 1 — never timed; PerformanceTracker.simdEfficiency is a constant 12.5% (ENG-6, Engine/geometric_solver.py)
Navigation.md:386  = 4x speedup
    weak operand [asserted]: SIMD efficiency = 1 — never timed; PerformanceTracker.simdEfficiency is a constant 12.5% (ENG-6, Engine/geometric_solver.py)
Navigation.md:395  **Why it matters:** A 6-fold symmetric pattern? Compute 1/6 of it, rotate copies = 6x faster.
    weak operand [asserted]: symmetry reduction taken — the solver computes all and reports the potential reduction (ENG-3, Engine/geometric_solver.py)
Navigation.md:405  = 6x speedup + perfect accuracy
    weak operand [asserted]: symmetry reduction taken — the solver computes all and reports the potential reduction (ENG-3, Engine/geometric_solver.py)
Six-sigma.md:298  - **Improvement factor: 4000x-280,000x better quality**
    weak operand [asserted]: baseline 0.5σ and the cost figures 10,100 / 155 — stated in Six-sigma.md, nothing measured
Six-sigma.md:462  # Cost ratio: 10,100 / 155 = 65x more expensive to use defective equations
    weak operand [asserted]: baseline 0.5σ and the cost figures 10,100 / 155 — stated in Six-sigma.md, nothing measured
Six-sigma.md:465  **“Efficient” equations are actually 65x MORE expensive when quality costs included.**
    weak operand [asserted]: baseline 0.5σ and the cost figures 10,100 / 155 — stated in Six-sigma.md, nothing measured
Six-sigma.md:488  But your Cost of Poor Quality is 65x higher.
    weak operand [asserted]: baseline 0.5σ and the cost figures 10,100 / 155 — stated in Six-sigma.md, nothing measured
Six-sigma.md:698  **4. “Efficient” equations are actually 65x more expensive**
    weak operand [asserted]: baseline 0.5σ and the cost figures 10,100 / 155 — stated in Six-sigma.md, nothing measured
TRANSLATION_GUIDE.md:129  # -> 2080 adaptive grid points (vs 32768 for uniform grid: 15x speedup)
    weak operand [asserted]: point count ∝ time — DEAD (ENG-1, Engine/engine_benchmark.py: fewer points ran 2–50x slower)
Universal-geometric-intelligence-P2.md:332  Average compression: 250×
    weak operand [asserted]: bearing sample counts and loss figures — Universal-geometric-intelligence-P2.md §2.3, no code or data in the tree
Universal-geometric-intelligence-P2.md:336  Healthy bearing: 6.1% loss, 280× compression → PASS
    weak operand [asserted]: bearing sample counts and loss figures — Universal-geometric-intelligence-P2.md §2.3, no code or data in the tree
Universal-geometric-intelligence-P2.md:337  Worn bearing:    7.8% loss, 245× compression → PASS
    weak operand [asserted]: bearing sample counts and loss figures — Universal-geometric-intelligence-P2.md §2.3, no code or data in the tree
Universal-geometric-intelligence-P2.md:338  Misaligned:      9.5% loss, 225× compression → PASS
    weak operand [asserted]: bearing sample counts and loss figures — Universal-geometric-intelligence-P2.md §2.3, no code or data in the tree
Universal-geometric-intelligence-P2.md:344  - 200-300× compression: Removes measurement noise, keeps signal
    weak operand [asserted]: bearing sample counts and loss figures — Universal-geometric-intelligence-P2.md §2.3, no code or data in the tree
Universal-geometric-intelligence-P2.md:955  - **Speedup: 8× with zero algorithm change**
    weak operand [asserted]: SIMD efficiency = 1 — never timed; PerformanceTracker.simdEfficiency is a constant 12.5% (ENG-6, Engine/geometric_solver.py)
Universal-geometric-intelligence-P2.md:1157  - Single reflection plane: Compute 1/2, mirror → **2× faster**
    weak operand [asserted]: symmetry reduction taken — the solver computes all and reports the potential reduction (ENG-3, Engine/geometric_solver.py)
Universal-geometric-intelligence-P2.md:1158  - Two orthogonal planes: Compute 1/4 → **4× faster**
    weak operand [asserted]: symmetry reduction taken — the solver computes all and reports the potential reduction (ENG-3, Engine/geometric_solver.py)
Universal-geometric-intelligence-P2.md:1161  **Combined with SIMD:** 8× (SIMD) × 4× (symmetry) = **32× total speedup**
    weak operand [asserted]: SIMD efficiency = 1 — never timed; PerformanceTracker.simdEfficiency is a constant 12.5% (ENG-6, Engine/geometric_solver.py); symmetry reduction taken — the solver computes all and reports the potential reduction (ENG-3, Engine/geometric_solver.py)
Universal-geometric-intelligence-P2.md:1396  ✅ **SIMD optimizer** - Parallel acceleration (8× typical)
    weak operand [asserted]: SIMD efficiency = 1 — never timed; PerformanceTracker.simdEfficiency is a constant 12.5% (ENG-6, Engine/geometric_solver.py)
Silicon/COMPLETE_INDEX.v2.md:275  |**Precision**    |< 0.5 nm     |**0.025 nm**|✅ **20× better**|
    weak operand [asserted]: 0.025 nm "achieved" — never measured; RBS-C cannot resolve it (Silicon/Proposal.md:67 audit row)
Silicon/COMPLETE_INDEX.v2.md:277  |**Energy/bit**   |< 1.6 aJ     |**0.22 aJ** |✅ **7× better** |
    weak operand [asserted]: 0.22 aJ/bit "achieved" — never measured (Silicon/COMPLETE_INDEX.v2.md, Silicon/FINAL_VALIDATION_REPORT.md)
Silicon/COMPLETE_INDEX.v2.md:278  |**Write speed**  |1 THz        |**10 THz**  |✅ **10× better**|
    weak operand [asserted]: 10 THz write "achieved" — never measured; THz is the wrong band for ESR at 1–2 T (Silicon/Proposal-addendum.md:37 audit row)
Silicon/COMPLETE_INDEX.v2.md:301  - T₂: 166 ms vs. 1 ms → **166× better**
    weak operand [asserted]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Silicon/COMPLETE_INDEX.v2.md:308  - T₂: 166 ms vs. 100 μs → **1660× better**
    weak operand [asserted]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Silicon/Energy-pattern.md:208  "$10M vs $300M, 10-30x capital reduction"
    weak operand [refutation]: $10M / $300M — stated in Silicon/Energy-pattern.md, no source; the line quotes the claim to refute it
Silicon/FINAL_VALIDATION_REPORT.md:147  |NV centers in diamond          |~1 ms     |300 K      |**166× better**             |
    weak operand [asserted]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Silicon/FINAL_VALIDATION_REPORT.md:149  |Superconducting qubits         |~100 μs   |20 mK      |**1660× better** + room temp|
    weak operand [asserted]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Silicon/FINAL_VALIDATION_REPORT.md:289  |**Positional Precision**|< 0.5 nm      |**0.025 nm**         |✓ **20× better** |
    weak operand [asserted]: 0.025 nm "achieved" — never measured; RBS-C cannot resolve it (Silicon/Proposal.md:67 audit row)
Silicon/FINAL_VALIDATION_REPORT.md:291  |**Energy per Bit**      |< 1.6 aJ/bit  |**0.22 aJ/bit**      |✓ **7× better**  |
    weak operand [asserted]: 0.22 aJ/bit "achieved" — never measured (Silicon/COMPLETE_INDEX.v2.md, Silicon/FINAL_VALIDATION_REPORT.md)
Silicon/FINAL_VALIDATION_REPORT.md:292  |**Write Speed**         |~1 THz        |**10 THz** (parallel)|✓ **10× better** |
    weak operand [asserted]: 10 THz write "achieved" — never measured; THz is the wrong band for ESR at 1–2 T (Silicon/Proposal-addendum.md:37 audit row)
Silicon/FINAL_VALIDATION_REPORT.md:333  - ✓ **T₂ = 166 ms** (166× better than NV)
    weak operand [asserted]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:343  •	Read speed: 50ns → 25ns (2× faster)
    weak operand [asserted]: 50 ns → 25 ns read — stated in Silicon/MAGNETIC_BRIDGE_ADDENDUM.md; the magnetic channel is DEAD (FAB-1, Silicon/magnetic_authority.py)
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:347  •	Crosstalk: 1% → 0.1% (10× better)
    weak operand [asserted]: 1% → 0.1% crosstalk — stated in Silicon/MAGNETIC_BRIDGE_ADDENDUM.md; the magnetic channel is DEAD (FAB-1)
Silicon/Octahedral-computation.md:356  •	Compare to CMOS: ~100 fJ/bit → 100× more efficient
    weak operand [asserted]: 0.01 eV/bit — DEAD (below Landauer, Silicon/Fabrication.md audit header, Negentropic/landauer.py); "0.01 eV = 1.6 aJ" is wrong 1000x; 100 fJ/bit CMOS unsourced; 1.6 aJ vs 100 fJ is 62,500x, not 100x
Silicon/Proposal.md:24  > class, so 166 ms is **~8 orders high**. Grant a 1000× improvement on T₁ and it
    weak operand [refutation]: T₂ = 166 ms — DEAD (ER-1, Silicon/er_bounds.py; Silicon/Proposal.md audit header)
Silicon/Projects/LCEA.md:73  The embodied energy to **manufacture** AI hardware is 2.6× greater than the energy to **keep a human
    weak operand [asserted]: E_Mfg daily — Silicon/Projects/LCEA.md, no source in the tree

### CARRIED (65)
GUIDE.md:143  **For efficiency:** The geometric EM solver achieves 15-30x speedup
GUIDE.md:178  | 15-30x | spatial speedup | Adaptive grid vs. uniform grid in EM solver |
Navigation.md:120  - SIMD-vectorized operations (4-8x speedup)
Navigation.md:121  - Cache-aware data layout (3-5x speedup)
Navigation.md:122  - Symmetry-reduced computation (2-10x speedup)
Navigation.md:123  - Combined: 50-200x faster than naive implementation
Navigation.md:412  **What it means:** CPU cache is 100x faster than RAM. Organize data so CPU can use cache effectively
Navigation.md:423  = 3-5x speedup from same code, better arrangement
Navigation.md:452  - SIMD auto-vectorization: 4-8x faster
Navigation.md:453  - Cache-aware layout: 2-3x faster
Navigation.md:454  - Combined: 8-24x faster than naive code
Navigation.md:458  - 2-fold symmetry: 2x additional speedup
Navigation.md:459  - 4-fold symmetry: 4x additional speedup
Navigation.md:460  - 6-fold symmetry: 6x additional speedup
Navigation.md:461  - Spherical symmetry: 10-100x additional speedup
Navigation.md:465  - Simple problems: 10-50x faster
Navigation.md:466  - Symmetric problems: 50-500x faster
Navigation.md:467  - Best case (high symmetry + SIMD): 1000x faster
Navigation.md:483  - Impact: Iterate 100x more, discover faster
Universal-geometric-intelligence-P1.md:61  - Result: 100-1000× lower computational cost for equivalent information
Universal-geometric-intelligence-P1.md:1601  **Speedup: 3-15× faster, 10-100× lower power**
Universal-geometric-intelligence-P1.md:2015  ✓ **Efficient** - 10-100× less compute than ML
Universal-geometric-intelligence-P2.md:1223  **Scaling:** With 8 cores, total speedup approaches **700×**
Universal-geometric-intelligence-P2.md:1400  **Combined speedup: 100-1000× vs. naive implementation**
Universal-geometric-intelligence-P3.md:21  - **100× energy efficiency** vs. conventional memory
Universal-geometric-intelligence-P3.md:706  | Parallel speedup | 2-4× | Time-division or frequency multiplexing |
Universal-geometric-intelligence-P3.md:782  'radiation_hardness': '10× better (higher barriers)',
Universal-geometric-intelligence-P3.md:995  - **Energy:** 100-10000× better than conventional
Universal-geometric-intelligence-P3.md:1190  'octahedral_fit': 'Excellent (100× energy advantage)',
Universal-geometric-intelligence-P3.md:1358  'result': '100-1000× energy advantage'
Universal-geometric-intelligence-P3.md:1468  'Demonstrate clear advantages (100× energy)',
Universal-geometric-intelligence-P3.md:1559  ✅ **Performance projections** - 100-10000× energy advantage
Universal-geometric-intelligence-P4.md:2193  1. **Energy-efficient computation** (100-1000× better than conventional)
Mandala/01-octahedral-mapping.md:136  # With SIMD (Engine/simd_optimizer.py): 8× vectorised throughput
Mandala/01-octahedral-mapping.md:137  # With symmetry detection (Engine/symmetry_detector.py): 2–4× reduction
Mandala/01-octahedral-mapping.md:138  # Combined typical speedup vs uniform grid: ~15–30×
Mandala/04-roadmap.md:29  ├── geometric_solver.py        EM field solver, symmetry-aware, ~15–30× speedup
Mandala/04-roadmap.md:82  **Expected gain**: ~3× fewer residual vortices vs linear schedule; asymptotically better for large g
Mandala/05-physics-connections.md:69  - SIMD-vectorised, ~15–30× speedup via octree + symmetry detection
Silicon/EXECUTIVE_SUMMARY.md:156  - 32 cores per job (2× speedup)
Silicon/EXECUTIVE_SUMMARY.md:333  - 10× better than existing room-temp quantum memories
Silicon/FINAL_VALIDATION_REPORT.md:200  - **20× faster than individual sequential writes**
Silicon/Fabrication.md:781  - Speedup: 2-3× vs. sequential
Silicon/Fabrication.md:940  •	Energy: 0.1-1 aJ/bit (10-100× better than CMOS)
Silicon/Fabrication.md:1063  - Our approach: 100× energy improvement possible
Silicon/Fabrication.md:1209  Why? Works WITH physics, 100× energy advantage
Silicon/Fabrication.md:1933  Throughput: 8× single-cell performance
Silicon/Fabrication.md:2380  ✅ 1000× faster writes (enables real-time processing)
Silicon/Fabrication.md:2563  ✅ Demonstrate clear advantages (100× power savings)
Silicon/Fabrication.md:2575  •	✅ Speed: 100-1000× faster writes
Silicon/Fabrication.md:2700  - 100× energy advantage over incumbents
Silicon/INDEX.md:342  **Impact**: 10× better than state-of-the-art room-temp quantum memory
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:90  •	2-20× faster than adiabatic
Silicon/MAGNETIC_BRIDGE_ADDENDUM.md:102  •	3× pulse overhead acceptable for critical operations
Silicon/README.md:30  •	1.6 aJ/bit energy efficiency (100× better than CMOS)
Silicon/SYSTEM_ARCHITECTURE.md:11  - **166 ms coherence** at 300 K (166× better than NV centers)
Silicon/SYSTEM_ARCHITECTURE.md:13  - **0.22 aJ/bit** energy efficiency (7× better than target)
Silicon/SYSTEM_ARCHITECTURE.md:327  |**Write energy**    |0.22 aJ/bit|7× better than target|
Silicon/Tensor-encode.md:363  Advantage: 7-10× energy savings for compressible dataDisadvantage: Random access becomes more comple
Silicon/Tensor-encode.md:372  Compression: 10-100× for natural signals
docs/GeneralOverview.md:12  - SIMD Parallelism (8x practical speedup)
docs/GeneralOverview.md:14  - Symmetry Exploitation (2x-8x reduction)
docs/Transition_Strategy.md:12  - Gains: 10x–100x performance on real problems
docs/Transition_Strategy.md:24  - Gains: 100x–1000x
docs/Transition_Strategy.md:36  - Gains: 1000x+ efficiency and emergent behavior

### NOT-A-CLAIM (3)
Universal-geometric-intelligence-P3.md:405  'instrumentation_amp': 'INA128, gain 100-1000×',
Silicon/FRET/Fractalization.md:378  •	G (geometric gain): aperture/edge-cell area ratio, design 5–20×
geometric_intelligence/CLAIMS.md:15  | GB-4 | three unsourced tolerances (0.05 edge, phi^-9 cycle, 0.10 integrity) and a drift band of (1
```
