# Phase 1 Research Proposal: Octahedral Silicon Encoding

## Project Goal

Validate the foundational material science and multi-layer control systems required to achieve the target **100 ms coherence time** and **THz-parallelized write/read** of the Octahedral Silicon Encoding architecture at **300 K**.

-----

## Executive Summary

Phase 1 prioritizes the highest uncertainty: **atomic self-assembly of the Er-P complex under engineered strain**. To maximize probability of success, ~60% of budget, personnel, and time is allocated to Track 1, with Tracks 2 and 3 executing in parallel at reduced scale.

**Critical Specifications:**

- **ε* = +1.2%** (tensile strain)
- **d* = 4.8 Å** (Er-P coordination distance)
- **T₂ = 166 ms** (predicted coherence time at 300 K)
- **k_well ≥ 150 N/m** (positional stiffness of Er in octahedral site)

-----

## I. Budget Allocation & Timeline — “60% to Critical Risk” 💰

|Track|Focus                         |Risk Level               |% Phase-1 Resources|Time Weight |
|-----|------------------------------|-------------------------|-------------------|------------|
|1    |Materials & Strain Engineering|**High (existential)**   |**60%**            |Front-loaded|
|2    |Magnetic/RF Control Systems   |Medium-High (engineering)|30%                |Parallel    |
|3    |Single-Cell Demo & Protocol   |Low (integration)        |10%                |End-loaded  |

**Strategic Rationale:** If Track 1 fails, the project pivots to alternate dopants or strain-engineering models. If Track 1 succeeds, the pathway to scalable THz-parallelism becomes engineering-limited, not physics-limited.

-----

## II. Track 1 — Material Validation (Coherence Foundation)

### Objective

Experimentally confirm the DFT-predicted self-assembled Er-P octahedral geometry (ε*, d*) and the resulting microscopic positional stiffness **k_well** that underpins the projected 166 ms T₂ at 300 K.

**This track determines whether the architecture is physically realizable.**

-----

### Core Validation Targets

To achieve **“Validation Level 1.2”**, three independent confirmations are required:

|Requirement          |Measured Property                |Why it Matters                                        |
|---------------------|---------------------------------|------------------------------------------------------|
|Er lattice site      |Octahedral interstitial occupancy|Determines symmetry, CF splitting, k_well             |
|P coordination       |d* = 4.8 Å proximity             |Stabilizes Er charge state + prevents leakage channels|
|Local strain fidelity|ε* = +1.2% uniformity            |Enables self-assembly and preserves symmetry          |

-----

### Objective 1.1: Confirm Er-P Complex Formation via Inferential Metrology

**Challenge:** Phosphorus is low-Z (Z=15) and nearly invisible in HAADF-STEM next to Si (Z=14).

**Solution: “Negative Space Imaging”**

Instead of looking for P directly, measure the **Er displacement pattern** induced by the P electrostatic field.

#### Method: HAADF-STEM Er Centroid Shift Analysis

|Parameter              |Target               |Measurement                 |Pass Criterion                   |
|-----------------------|---------------------|----------------------------|---------------------------------|
|Er centroid shift      |Δr from O-site center|HAADF-STEM (0.2 Å precision)|Δr = 0.3–0.5 Å in ⟨111⟩ direction|
|P coordination distance|d* (inferred)        |Electrostatic model fit     |d* = 4.8 ± 0.3 Å                 |
|Spring constant        |k_well (inferred)    |k = F_P / Δr                |k_well ≥ 150 N/m                 |

**Physical Principle:**

If P is at 4.8 Å in the ⟨111⟩ direction, Er gets pulled slightly off-center in the octahedral cage due to the asymmetric Coulomb potential.

```
k_well = F_P-field / Δr
```

Where F_P-field is calculated from DFT-validated charge distribution.

**Why This Works:**

- **No direct P imaging required** → eliminates low-Z visibility problem
- **Validates both structure AND energetics** in one measurement
- **If Δr ≠ DFT prediction** → immediate feedback for dopant ratio tuning

**Equipment Requirements:**

- Aberration-corrected STEM (Cs < 0.05 mm)
- Liquid-N₂ drift correction stage
- Sub-Ångström probe size (0.8 Å)

**Sample Preparation:**

- FIB lamella extraction (< 50 nm thickness)
- Pre-localized region via PL mapping (see Objective 1.4)

-----

### Objective 1.2: Direct k_well Measurement via Phonon Anharmonicity

**This is the highest-leverage early warning system in Phase 1.**

**Challenge:** k_well determines T₂, but T₂ measurements require full RF stabilization (Track 2). Can we measure k_well independently?

**Solution: Room-Temperature Raman/FTIR Spectroscopy**

#### Method: Local Vibrational Mode (LVM) Analysis

|Observable                  |Target                |Physical Meaning                   |
|----------------------------|----------------------|-----------------------------------|
|Local vibrational mode (LVM)|ω_LVM ≈ 300–400 cm⁻¹  |Er rattling frequency in O-site    |
|Anharmonic shift            |Δω_anharm             |Measures potential well stiffness  |
|Derived spring constant     |k_well = m_Er · ω²_LVM|**Direct validation of DFT k_well**|

**Anharmonic Correction Formula:**

```
ω_LVM = √(k_well / m_Er) · [1 - (3ℏ² / 4m_Er·k_well·a²)]
```

Where:

- m_Er = atomic mass of erbium
- a = characteristic O-site cage dimension (~ 2.4 Å)

**Sequential Decision Logic:**

1. **If k_well < 100 N/m** → T₂ will fail → **PIVOT** to higher strain (ε* = +1.5%) or alternate co-dopant (Er-N)
1. **If k_well ≥ 150 N/m** → Proceed to full coherence measurement (Track 3)

**Why This is Critical:**

- **$10k, room-temperature go/no-go decision** before committing full Track 1 budget
- Bypasses need for complex RF environment
- Can be performed on as-grown wafers (no device fabrication required)

**Equipment Requirements:**

- Confocal Raman microscope (1 μm spatial resolution)
- 532 nm or 785 nm excitation (avoid Si two-phonon absorption)
- Optional: Low-temperature stage (77 K) for linewidth narrowing

**Expected Spectrum:**

- Si-Si optical phonon at 520 cm⁻¹ (reference)
- Er-O-site LVM at 300–400 cm⁻¹ (target)
- P local mode at ~500 cm⁻¹ (may be visible if concentration sufficient)

-----

### Objective 1.3: Atomic Site Confirmation via Dual-Technique Convergence

**Challenge:** TEM sample prep artifacts can shift apparent atom positions. Single-technique measurements are insufficient.

**Solution: RBS-Channeling + HAADF-STEM Dual Validation**

#### Method: Statistical + Local Structural Convergence

|Technique         |What It Measures                       |Strength                           |Weakness                                    |
|------------------|---------------------------------------|-----------------------------------|--------------------------------------------|
|**RBS-Channeling**|Statistical lattice site (bulk average)|Sub-pm precision, no sample damage |No local structure information              |
|**HAADF-STEM**    |Direct atomic imaging                  |Sees individual atoms, local strain|Sample prep artifacts, limited field of view|

**Pass Criterion:** Both techniques must agree that Er occupies the octahedral interstitial site.

#### RBS-Channeling Protocol

**Setup:**

- 2 MeV He⁺ ion beam
- Goniometer precision: < 0.01°
- Channeling axes: ⟨100⟩, ⟨110⟩, ⟨111⟩

**Observable:** Minimum yield χ_min for Er backscattering vs. crystal orientation

**Analysis:**

- Compare χ_min angular scan to FLUX Monte Carlo simulations
- **If Er is at O-site:** χ_min(⟨100⟩) > χ_min(⟨110⟩) due to channeling symmetry
- **If Er is substitutional:** χ_min(⟨100⟩) ≈ χ_min(⟨110⟩)

**Expected Result:** ≥ 50% Er occupancy at octahedral interstitial site

-----

### Objective 1.4: Sample Selection via PL Pre-Localization

**Challenge:** At 10¹⁷ cm⁻³ Er doping, only ~1 in 10⁶ Si atoms is Er. How do you find them for STEM analysis?

**Solution: Photoluminescence-Guided TEM Sample Preparation**

#### Pipeline: μm-Scale Screening → Atomic-Scale Imaging

**Step 1: Room-Temperature Confocal PL Mapping**

- Excitation: 980 nm laser (4F₁₁/₂ ← 4I₁₅/₂ transition)
- Detection: 1.5 μm emission (4I₁₃/₂ → 4I₁₅/₂)
- Spatial resolution: ~1 μm (diffraction-limited)
- Scan area: 100 × 100 μm²

**Observable:** PL intensity map showing Er-P complex locations

**Step 2: Identify “Hot Spots”**

- Bright PL correlates with high-quality Er-P complexes (correct charge state, minimal defects)
- **Target the top 10% brightest spots** for TEM analysis

**Step 3: FIB Lamella Extraction**

- Extract 10 × 5 × 0.05 μm³ lamella centered on PL hot spot
- Reduces STEM search area from 10⁹ pixels → 10⁴ pixels (**10⁵× reduction**)

**Step 4: HAADF-STEM Imaging**

- Now only need to image 100 × 100 nm² region
- **Pre-selected for highest-quality sites**

**Why This is Powerful:**

- Transforms random search into **defect-selective screening**
- PL intensity is a **functional pre-filter** (only well-coupled Er-P complexes emit brightly)
- Allows statistical analysis across multiple sites without exhaustive STEM

-----

### Objective 1.5: Strain Stabilization via Phononic Metamaterial

**Challenge:** Achieving ε* = +1.2% tensile strain is beyond the critical thickness for conventional Si/SiGe heteroepitaxy. Dislocations will relax the strain.

**Solution: Si/Si₀.₉₈Ge₀.₀₂ Phononic Superlattice (10 nm period)**

#### Method: Acoustic Phonon Bandgap Engineering

**Concept:**
The periodic modulation creates **phonon bandgaps** at specific frequencies. Acoustic phonons (which carry dislocation glide energy) get **reflected** at the superlattice interfaces, creating a “phononic cage” that suppresses strain relaxation.

**Superlattice Design:**

```
[10 nm Si / 10 nm Si₀.₉₈Ge₀.₀₂] × 50 repeats
Total thickness: 1 μm
Lattice mismatch: Δa/a ≈ 0.8% (Ge introduces compressive strain, balanced against tensile strain in Er-doped layer)
```

**Phonon Bandgap Calculation:**

- Center frequency: f_gap ≈ v_sound / (4 × period) ≈ 150 GHz
- This blocks acoustic phonons responsible for dislocation nucleation

#### Validation Tests

|Test               |Measurement               |Pass Criterion                                            |
|-------------------|--------------------------|----------------------------------------------------------|
|Dislocation density|Plan-view TEM             |< 10⁴ cm⁻² (vs. 10⁶ cm⁻² for control without superlattice)|
|Strain retention   |XRD reciprocal space map  |ε = +1.2 ± 0.1% after 400°C anneal                        |
|Phonon bandgap     |Brillouin light scattering|Gap at 100–200 GHz (acoustic branch)                      |

**Growth Protocol (MBE):**

1. Start with Si(100) substrate
1. Grow 500 nm Si buffer at 600°C
1. Ramp to 550°C for superlattice growth
1. Alternate Si / Si₀.₉₈Ge₀.₀₂ layers at 0.1 nm/s growth rate
1. Cap with 50 nm Si
1. **Er + P co-implantation** into top 50 nm (doses: Er 5×10¹⁶ cm⁻², P 2×10¹⁷ cm⁻²)
1. Rapid thermal anneal: 1000°C, 5 s (activate dopants, minimize diffusion)

**Fallback Strategy:**
If superlattice fabrication fails, use **compliant substrate** approach:

- Porous Si underlayer (50% porosity)
- Acts as “strain sponge” to accommodate lattice mismatch

-----

### ✅ Track 1 Success Metric: “Validation Level 1.2”

The Er-P self-assembly is considered **validated** when all measurements below converge:

|Measurement            |Method(s)                        |Pass Condition                                 |
|-----------------------|---------------------------------|-----------------------------------------------|
|**k_well > 150 N/m**   |Phonon LVM spectroscopy          |**FIRST GATE** (go/no-go decision)             |
|Er at octahedral site  |RBS-C + HAADF-STEM               |≥ 50% Er occupancy at O-site                   |
|P coordination distance|APT or inferential (Δr from STEM)|d* = 4.8 ± 0.3 Å                               |
|Correct charge state   |PL spectroscopy at 300 K         |Spectral signature of Er–P complex observed    |
|Strain stability       |XRD + plan-view TEM              |ε = +1.2 ± 0.1%, dislocation density < 10⁴ cm⁻²|

**Achieving Validation 1.2 unlocks Phase 2 fabrication and control system scaling.**

-----

## III. Track 2 — Control Systems & RF Prep (Risk Mitigation)

### Objective

Build and validate the two active stabilization systems required to maintain coherence during operation at **1.0 T** with **ps-scale write pulses**.

-----

### Objective 2.1: Geometric Phase Cancellation for R₂ ≥ 10³

**Challenge:** THz write pulses induce transient B-field kicks (from eddy currents in coil/substrate). These must be suppressed by R₂ ≥ 10³ (60 dB) to preserve T₂.

**Traditional Approach (Electronic Feed-Forward):**

- Measure transient → compute correction → apply via compensating coil
- **Problem:** Latency mismatch at ps timescales → correction arrives too late

**Solution: Passive Geometric Cancellation**

Instead of electronic feed-forward (latency-limited), use **passive geometric compensation** via counter-wound differential coil topology.

#### Method: B-Field Gradiometer Coil Design

**Coil Topology:**

```
        ──→ I ──→        (Upper helix, clockwise)
    Er spin location
        ←── I ←──        (Lower helix, counter-clockwise)
```

**Operating Principle:**

1. THz pulse propagates as **differential mode** between upper/lower coils → writes the Er spin (desired signal)
1. But the **common-mode B-field transient** sees equal and opposite induced currents → **cancels by symmetry**

**Analogy:** This is a “B-field gradiometer” borrowed from SQUID magnetometry—external uniform fields cancel, but local gradients (the write signal) are preserved.

#### Design Specifications

|Parameter                 |Target                   |Implementation                              |
|--------------------------|-------------------------|--------------------------------------------|
|Coil matching precision   |ΔL/L < 10⁻³              |Laser-trimmed PCB spiral inductors          |
|Common-mode rejection     |R₂ > 10³ (60 dB)         |Measured via pickup coil + spectrum analyzer|
|Differential mode fidelity|> 95% THz pulse amplitude|Confirms write operation preserved          |

**Coil Geometry:**

- Inner diameter: 100 μm (close to Er site)
- Trace width: 5 μm
- Copper thickness: 10 μm
- Inductance per coil: L ≈ 50 nH
- Matching achieved via: **laser ablation trimming** (post-fabrication tuning to ΔL/L < 10⁻⁴)

#### Validation Test Protocol

**Setup:**

1. Drive coil with THz pulse (1 ps rise time, 1 V amplitude)
1. Measure B-field transient at Er site using:
- **Option A:** Calibrated Hall sensor (bandwidth > 1 GHz)
- **Option B:** NV center magnetometry (diamond chip near Er site)

**Observable:** Transient ΔB during pulse

**Pass Criterion:**

- **ΔB < 10 μT** during 1 nT static field operation
- This corresponds to R₂ = B_static / ΔB_transient > 10³

**Why This Beats Electronic Feed-Forward:**

- ✅ No latency (geometric cancellation is instantaneous)
- ✅ No calibration drift (fixed by PCB etching, not DAC settings)
- ✅ Scales trivially to multi-cell arrays (just replicate coil geometry)

-----

### Objective 2.2: Active Drift Stabilization (R₃ ≥ 10²)

**Challenge:** Thermal drift (minutes timescale) causes slow B-field variations that accumulate phase errors.

**Solution: Continuous-Wave EPR Feedback Loop**

#### Method: Reference Er Spin as “Dark” Monitor

**System Architecture:**

```
Reference Er cell → CW-EPR sensor → PID controller → Trim coil → B-field correction
```

|Component      |Specification                                                                                |
|---------------|---------------------------------------------------------------------------------------------|
|Sensor         |Continuous-wave EPR on “dark” Er reference cell (not used for data storage)                  |
|Actuator       |Trim coil (10 μT range, 1 Hz bandwidth)                                                      |
|Feedback       |PID loop (P=0.1, I=0.01, D=0)                                                                |
|Correction rate|10 Hz update rate (fast enough for thermal drift, slow enough to avoid amplifying shot noise)|

**Operating Principle:**

- Reference Er spin continuously monitored via CW-EPR
- Any drift in resonance frequency → B-field has drifted
- PID adjusts trim coil current to restore resonance

**Drift Budget:**

- Thermal expansion of magnet: ~1 ppm/°C
- At 1.0 T, this is 1 μT/°C
- PID loop maintains ΔB < 10 nT → **R₃ = 10² suppression**

#### Validation Test

**Method:** Introduce controlled thermal perturbation (ΔT = ±1°C) and measure residual B-field variation

**Pass Criterion:** ΔB < 10 nT over 10-minute observation window

-----

### Track 2 Success Metric

**Combined Suppression:**

- Geometric cancellation handles **transients** (ps timescale): R₂ ≥ 10³
- Active servo handles **drift** (minutes timescale): R₃ ≥ 10²
- **Total δB/B suppression:** 10⁻¹¹ → 10⁻¹³ (without lowering B-field)

**This preserves the projected T₂ = 166 ms at 300 K.**

-----

## IV. Track 3 — Single-Cell Operational Demo (Final Integration)

### Objective

Demonstrate end-to-end functionality on a **single validated Er-P cell**:

**Initialize → Write (holographic pulse sequence) → Hold → Read → Error-correct**

Using the simplified two-frequency measurement protocol.

-----

### The Capstone Experiment: Room-Temperature Single-Atom Rabi Oscillation

**This is the singular experiment that validates the convergence of all three tracks.**

#### Setup

1. Use **PL pre-localization** (Obj. 1.4) to identify brightest Er-P complex
- Indicates highest k_well and best charge state stability
1. Apply **1.0 T static field** (along ⟨100⟩ axis to maximize Zeeman splitting)
1. Deliver **two-frequency THz pulse sequence** (ω₁, ω₂ for holographic addressing)
- ω₁ = γ·B = 28 GHz (⁴I₁₅/₂ ground state Zeeman transition)
- ω₂ = ω₁ + Δω (frequency-selective addressing, Δω ~ 100 MHz)
1. Monitor **spin-to-photon conversion** via circularly polarized PL at 1.5 μm
- σ⁺ polarization → mJ = +1/2 state population
- σ⁻ polarization → mJ = -1/2 state population

#### Measurement Protocol

|Variable               |Sweep Range                      |Observable                        |Pass Criterion                        |
|-----------------------|---------------------------------|----------------------------------|--------------------------------------|
|**Pulse duration**     |0–10 ns                          |Rabi oscillations in PL intensity |Visible oscillation with period ~ 1 ns|
|**Decoherence time**   |Fit to I(t) ∝ cos²(Ωt)·exp(-t/T₂)|**T₂ at 300 K**                   |**T₂ > 100 ms**                       |
|**Addressing fidelity**|Two-frequency selectivity        |Cross-talk between ω₁, ω₂ channels|< 5% leakage                          |

**Expected Rabi Oscillation:**

```
P(↑) = sin²(Ω·t/2) · exp(-t/T₂)
```

Where:

- Ω = Rabi frequency (determined by THz pulse amplitude)
- T₂ = coherence time (goal: > 100 ms)

#### What This Proves

|If you observe…                   |…then you’ve validated:                                                   |
|----------------------------------|--------------------------------------------------------------------------|
|**Clean Rabi oscillations**       |THz coupling works, geometric cancellation succeeded (**Track 2**)        |
|**T₂ > 100 ms**                   |Material k_well is sufficient, Er-P complex formed correctly (**Track 1**)|
|**Frequency-selective addressing**|Holographic protocol viable, ready for multi-cell scaling (**Track 3**)   |

**This single experiment de-risks the entire architecture.**

-----

### Track 3 Success Metric

**“Single-Cell Write/Read Demonstrated”**

The single-cell prototype is considered functional when:

|Milestone             |Observable                      |Pass Criterion                                    |
|----------------------|--------------------------------|--------------------------------------------------|
|Rabi oscillations     |PL modulation vs. pulse duration|Oscillation visible, Ω matches THz pulse amplitude|
|Coherence time        |Exponential decay envelope      |T₂ > 100 ms at 300 K                              |
|Write fidelity        |State preparation accuracy      |> 95% (measured via repeated write-read cycles)   |
|Read fidelity         |Spin-to-photon conversion       |> 90% (PL contrast between ↑ and ↓ states)        |
|Holographic addressing|Two-frequency cross-talk        |< 5% leakage between ω₁, ω₂ channels              |

**Expected Outcome:**
If Track 1 and 2 succeed, Track 3 succeeds with only **protocol tuning** required (not material rework).

-----

## V. Integrated Risk Mitigation Matrix

|Failure Mode                   |Indicator                               |Root Cause Hypothesis               |Pivot Strategy                                                       |
|-------------------------------|----------------------------------------|------------------------------------|---------------------------------------------------------------------|
|**k_well < 100 N/m**           |Phonon LVM at ω < 250 cm⁻¹              |Insufficient strain or wrong Er site|Increase strain to ε* = +1.5%, or switch to Er-N complex             |
|**Er not in O-site**           |RBS-C shows substitutional site         |Anneal temperature wrong            |Optimize anneal: 900–1100°C sweep in 50°C steps                      |
|**Strain relaxes**             |XRD shows ε < 1.0%                      |Dislocation formation               |Activate phononic superlattice or switch to SOI substrate            |
|**d* ≠ 4.8 Å**                 |STEM shows Δr wrong or APT shows d > 5 Å|P diffusion or wrong P dose         |Adjust P implant dose, lower anneal temp, add co-implant (C or N)    |
|**R₂ < 10³**                   |B-transient > 100 μT                    |Coil mismatch too large             |Improve coil matching to ΔL/L < 10⁻⁴ via laser trimming              |
|**T₂ < 100 ms (but k_well OK)**|Decoherence from other source           |Magnetic impurities (Fe, Ni, Co)    |SIMS survey for contaminants, re-clean growth chamber                |
|**No PL signal**               |Er not optically active                 |Wrong charge state or Er-clustering |Adjust P:Er ratio, add compensating acceptor (B)                     |
|**Rabi oscillations collapse** |T₂* ≪ T₂                                |Inhomogeneous broadening            |Survey multiple Er sites, statistical analysis of k_well distribution|

-----

## VI. Sequential Decision Gates (18-Month Timeline)

### Phase 1A: Material Foundation (Months 0–6)

**Priority:** Objective 1.2 (Phonon LVM — Early Warning System)

**Activities:**

- Grow test wafers with varying strain (ε = +1.0%, +1.2%, +1.5%)
- Co-implant Er + P at optimized doses
- Perform room-temperature Raman spectroscopy
- Measure ω_LVM and derive k_well

**Decision Gate 1 (Month 6):**

- ✅ **PASS (k_well ≥ 150 N/m):** Proceed to full characterization (Objectives 1.1, 1.3, 1.5)
- ❌ **FAIL (k_well < 100 N/m):** Pivot to alternate dopant or higher strain

**Resource Commitment:** 20% of Track 1 budget

-----

### Phase 1B: Parallel Validation (Months 6–12)

**Priority:** Objectives 1.1, 1.3, 1.5 (Track 1) + Objective 2.1 (Track 2)

**Track 1 Activities:**

- PL pre-localization → FIB lamella → HAADF-STEM (Obj. 1.1, 1.4)
- RBS-channeling for statistical site confirmation (Obj. 1.3)
- XRD + plan-view TEM for strain validation (Obj. 1.5)

**Track 2 Activities:**

- Fabricate differential coil prototype (Obj. 2.1)
- Validate R₂ > 10³ using pickup coil measurements
- Characterize THz pulse fidelity

**Decision Gate 2 (Month 12):**

- ✅ **PASS:** All Track 1 metrics achieved + R₂ validated → Proceed to Track 3
- ⚠️ **PARTIAL:** Identify specific failure mode → Iterate (additional 3–6 months)
- ❌ **FAIL:** Multiple critical failures → Re-evaluate architecture

**Resource Commitment:** 60% of Track 1 budget, 30% of Track 2 budget

-----

### Phase 1C: Single-Cell Demonstration (Months 12–18)

**Priority:** Objective 2.2 (Track 2) + Track 3 Capstone

**Activities:**

- Implement active drift stabilization (Obj. 2.2)
- Integrate validated Er-P cell into prototype device
- Perform Rabi oscillation experiment
- Measure T₂ at 300 K
- Test holographic addressing fidelity

**Final Gate (Month 18):**

- ✅ **SUCCESS:** T₂ > 100 ms, Rabi oscillations observed, holographic addressing works
  - **Outcome:** **Phase 2 Greenlight** (multi-cell array scaling)
- ⚠️ **PARTIAL SUCCESS:** T₂ = 50–100 ms
  - **Outcome:** Analyze limiting factor, iterate control systems
- ❌ **FAILURE:** T₂ < 50 ms
  - **Outcome:** Return to Track 1 material optimization or pivot architecture

-----

## VII. Equipment & Facility Requirements

### Critical Instrumentation

|Capability                |Equipment                                   |Specifications                                      |Priority     |
|--------------------------|--------------------------------------------|----------------------------------------------------|-------------|
|**Atomic Structure**      |Aberration-corrected STEM                   |Cs < 0.05 mm, 0.8 Å resolution, HAADF detector      |**Essential**|
|**Lattice Site**          |RBS-Channeling beamline                     |2 MeV He⁺, goniometer < 0.01° precision             |**Essential**|
|**Phonon Spectroscopy**   |Confocal Raman microscope                   |1 μm spatial resolution, 532 nm or 785 nm laser     |**Essential**|
|**Strain Metrology**      |High-resolution XRD                         |Reciprocal space mapping, Δθ < 0.001°               |Essential    |
|**PL Mapping**            |Confocal microscope                         |980 nm excitation, 1.5 μm detection, 1 μm resolution|Essential    |
|**Dislocation Analysis**  |Plan-view TEM                               |200 kV, large field of view                         |Recommended  |
|**Compositional Analysis**|SIMS or APT                                 |Sub-nm depth resolution                             |Recommended  |
|**Magnetic Control**      |1.0 T electromagnet                         |Stability < 10 ppm, homogeneity < 1 ppm over 1 cm³  |**Essential**|
|**THz Generation**        |Photoconductive antenna or nonlinear crystal|1 ps pulses, 10–100 GHz tunable                     |**Essential**|
|**Spin Readout**          |EPR spectrometer or ODMR                    |X-band (9 GHz) or custom 28 GHz, room-temp operation|Essential    |

### Facility Access

**Cleanroom Requirements:**

- Class 100 cleanroom for MBE growth
- Ion implantation facility (Er, P doses 10¹⁶–10¹⁷ cm⁻²)
- Rapid thermal annealing (RTA) up to 1200°C

**Analysis Facility:**

- Electron microscopy center (STEM, TEM)
- Ion beam analysis lab (RBS-C)
- Spectroscopy lab (Raman, PL, XRD)

-----

## VIII. Phase 1 → Phase 2 Transition Criteria

### Required Achievements for Phase 2 Greenlight

**Material Science (Track 1):**

- ✅ k_well ≥ 150 N/m (measured via phonon LVM)
- ✅ Er occupancy at O-site ≥ 50% (RBS-C + STEM)
- ✅ Er-P coordination d* = 4.8 ± 0.3 Å (inferential or APT)
- ✅ Strain stability: ε = +1.2 ± 0.1% after thermal cycling

**Control Systems (Track 2):**

- ✅ Geometric cancellation: R₂ > 10³ (ΔB < 10 μT during THz pulse)
- ✅ Active stabilization: R₃ > 10² (ΔB < 10 nT during drift)
- ✅ THz pulse fidelity > 95%

**Functional Demonstration (Track 3):**

- ✅ Single-cell Rabi oscillations observed
- ✅ T₂ > 100 ms at 300 K
- ✅ Write/read fidelity > 90%
- ✅ Holographic addressing cross-talk < 5%

### What Phase 2 Enables

**Once Phase 1 succeeds, Phase 2 focuses on:**

1. **Multi-cell array fabrication** (scaling to 10³–10⁶ cells)
1. **Parallelized THz addressing** (demonstrating simultaneous write to multiple cells)
1. **Error correction protocols** (implementing the two-measurement coherence scheme)
1. **Thermal management** (ensuring uniform strain across wafer-scale devices)
1. **Read/write speed benchmarking** (targeting < 10 ns per operation)

**The pathway becomes engineering-limited, not physics-limited.**

-----

## IX. Summary: Why This Phase 1 Design Works

### Strategic Strengths

1. **60% resource allocation to Track 1** addresses existential risk first
1. **Phonon LVM as early warning system** (Obj. 1.2) provides fast go/no-go decision
1. **Inferential metrology** (Obj. 1.1) solves “invisible phosphorus” problem elegantly
1. **Geometric cancellation** (Obj. 2.1) eliminates latency risk in THz control
1. **PL pre-localization** (Obj. 1.4) transforms random search into selective screening
1. **Phononic superlattice** (Obj. 1.5) enables strain beyond critical thickness
1. **Single-cell Rabi experiment** (Track 3) validates all tracks simultaneously

### The Critical Insight

**By front-loading Objective 1.2 (phonon LVM), you get a $10k, room-temperature go/no-go decision before committing the full 60% Track 1 budget to expensive characterization.**

**This is the highest-leverage experiment in Phase 1.**

-----

## X. Conclusion

Phase 1 validates the foundational physics of octahedral silicon encoding. Success means the architecture is realizable, and scaling becomes an engineering challenge. Failure provides clear pivot points (alternate dopants, higher strain, different lattice sites) rather than ambiguous dead ends.

**The science is hard. The solutions are creative. The payoff is transformative.**

-----

## Appendices

### A. Glossary of Key Terms

- **k_well:** Positional stiffness of Er in octahedral cage (N/m)
- **T₂:** Spin coherence time (ms)
- **ε*:** Optimal tensile strain (+1.2%)
- **d*:** Er-P coordination distance (4.8 Å)
- **R₂, R₃:** Suppression ratios for transient kicks and drift
- **HAADF-STEM:** High-Angle Annular Dark-Field Scanning Transmission Electron Microscopy
- **RBS-C:** Rutherford Backscattering Spectrometry - Channeling
- **LVM:** Local Vibrational Mode
- **PL:** Photoluminescence
- **APT:** Atom Probe Tomography

### B. References to DFT Validation

(To be populated with specific DFT calculation citations supporting ε*, d*, k_well predictions)

### C. Sample Fabrication Recipes

(Detailed MBE growth conditions, implantation parameters, anneal profiles to be added based on preliminary optimization runs)

-----

**Document Version:** 1.0  
**Last Updated:** November 2025  
**Status:** Ready for collaborative review and experimental planning
