# Magnetic Bridge Architecture

> **AUDIT 2026-07 — the control layer is sound, the physics layer beneath it
> is not.** Numbers computed in `magnetic_authority.py`, settled by
> `tests/test_magnetic_authority.py`.
>
> **This file states the correct electromigration limit** — `J_max ~ 1e10 A/m^2`
> = 1e6 A/cm². `Fabrication.md` runs the same coil at 1e8 A/cm². The two
> documents disagree and **this one is right**; propagate it back.
>
> Worked through this file's own coil geometry: 100 nm × 200 nm → A = 2e-14 m²,
> so I_max = 0.20 mA, and with N = 10 at r = 250 nm, **B = 5.03 mT**. The write
> protocol calls for 1.0 T static — **199× short**. Zeeman authority at 5 mT is
> 0.58 µeV against a stated 10–100 meV barrier: **0.0006 % barrier modulation.**
>
> | claim | status | correct value |
> |---|---|---|
> | 1 T write field from the on-chip coil | **DEAD** | 5.03 mT at this file's own J limit |
> | read time 50 ns | **8× OVER** | the hardware spec at the top of this file says 100 ns per field ramp; four rotations is a 400 ns floor before eddy currents |
> | "wait 5 ns" for eddy decay | **3 ORDERS OFF** | τ ≈ μσL²/π², Cu: 7.6 µs at 1 mm, 76 ns at 100 µm, 0.76 ns at 10 µm. Anything at coil-former or package scale is **microseconds** |
> | write = 70 ns | **DEAD** | write = read + transition + verify read, so the floor is >800 ns. Every downstream throughput and cost figure inherits this |
> | 2 T + 3-axis + 100 ns slew + dB/B < 1e-5 | **MUTUALLY EXCLUSIVE** | 2 T over 1 cm³ stores 1.59 J; switching in 100 ns is **15.9 MW** and 1e5–1e6 V class drive. That is destructive-pulsed-magnet engineering. And dB/B < 1e-5 at 2 T is 20 µT stability, which needs superconducting persistent mode (cannot slew) or 1e-5 regulation *during* the slew. Real 1–3 T 3-axis vector magnets slew in seconds to minutes |
> | gradient addressing, 10–1000 T/m at 5–50 nm | **714× SHORT** | see the correction note below |
> | T_Rabi = 0.54 ps | **330× OFF** | the file substituted π·ħ = 3.14e-15 **s** where 3.31e-34 **J·s** belongs — wrong by 19 orders and dimensionally wrong. Correct: g·μ_B·B_RF = 1.855e-24 J, T_Rabi = **179 ps**, composite X(π/2)-Y(π)-X(π/2) = **536 ps** |
> | B_RF = 0.1 T at "0.1–10 W" | **5 ORDERS SHORT** | u = B²/2μ₀ = 3979 J/m³, (λ/2)³ = 3.4e-6 m³ → U = 13.4 mJ, P = ωU/Q = **842 kW** at Q = 1000. Cross-checked against real hardware: a 1 kW pulsed X-band ESR spectrometer gives B1 ≈ 1 mT, and B1 ∝ √P, so 0.1 T needs **10 MW** |
> | the [111] cross-check | **DEAD** | `T_111 = (T_xx+T_yy+T_zz)/3` drops the off-diagonals. The true projection is v·T·v = (1/3)(T_xx+T_yy+T_zz+2T_xy+2T_xz+2T_yz). The check reduces to an identity that holds whenever T is diagonal — the very assumption used to extract the diagonals. **It is exactly blind to the only error it claims to catch.** It is also underdetermined: a symmetric 3×3 has 6 independent components and four axes give four equations |
> | frequency multiplexing as a static address | **DEAD** | ω_nm = ΔE_nm/ħ is a property of *which states the cell is between*. `transition_table[0][5]` → 15.2 GHz; a different starting state gives a different frequency for the same cell. **The address changes when the data changes.** The only static-offset candidate offered is the gradient, which fails above |
> | `confidence = 1 - d_best/d_second` | **NaN FOR HALF THE STATES** | against the canonical table, states 1/4 and 2/5 are identical triples, so d_best == d_second → confidence 0 always, and 0/0 → NaN. **Four of eight states are permanently unreadable by this decoder** |
> | calibration bootstrap | **NO ENTRY POINT** | writing requires a read, reading requires calibration, calibration requires writing. Fix, using something already available: `Fabrication.md`'s implanted array is permanent, read-only and of independently known dose. Calibrate the read against implanted cells and the loop opens. The read-only array has a job |
>
> **Two corrections to the audit's own arithmetic:**
>
> *Gradient addressing.* The offset across 50 nm at 1000 T/m is **1.40 MHz**,
> not 1.4 kHz — g·μ_B/h = 28.0 GHz/T and 1000 T/m × 50 nm = 50 µT. So the
> shortfall against 1 GHz channels is **714×**, not 700,000×, and the gradient
> required for 1 GHz spacing is **7.1e5 T/m**, not 7e8. That is at the MFM tip
> state of the art (~1e6 T/m), not three orders beyond it. BRG-5 stands — the
> specified 10–1000 T/m is still 714× short, and a tip-scale gradient exists
> only within tens of nm of the tip, which is not a 4×4 array at 5 µm pitch —
> but it stands by hundreds, not by six orders.
>
> *Piezoresistance.* 6e-11 Pa⁻¹ is π₁₁, the **⟨100⟩** coefficient. The ⟨110⟩
> longitudinal value is (π₁₁+π₁₂+π₄₄)/2 = **7.18e-10 Pa⁻¹**, 12× larger, and it
> is the one consistent with the same audit's "gauge factor ~100" (π_l·E = 93;
> 6e-11 gives 7.8). So dR/R = GF × ε: **93 % at 1 % strain**, which is
> unphysical since Si fractures at 1–2 % and piezoresistance saturates well
> below that, or **9.3 % at a realistic 0.1 %**. The quoted 7.8 % was right in
> magnitude only because a 12×-low coefficient was paired with a 10×-high
> strain.
>
> **KEEP AS-IS:** the `STATE_*` finite state machine, `BridgeCommand` /
> `BridgeResponse`, the error code table, read → verify → retry(3) → mark
> defective, the insight that the write path depends on starting state, the
> coordinate system and v1..v4 definitions, the adiabaticity condition
> T >> ħ/ΔE, and J_max = 1e10 A/m². The architecture is fine.
>
> **REPLACEMENT PHYSICS LAYER.** Zero magnetic terms, zero ESR, zero cryogenics:
>
> | layer | mechanism | number |
> |---|---|---|
> | state variable | strain tensor | — |
> | write | piezo / optomechanical | 0.1–1 ns |
> | select | valley splitting, Ξ_u = 9.16 eV | 92 meV at 1 % strain, 9.2 meV at 0.1 % — vs 0.58 µeV from the legal coil, **authority ratio 1.6e4** |
> | read (fast) | **piezoresistive** — the piece that was missing | GF ≈ 93, dR/R ≈ **9 % at 0.1 % strain**, electrical, ns, 300 K |
> | read (full frame) | polarized Raman, six ⟨110⟩ geometries | complete; ~ms |
> | control layer | the FSM in this document, unchanged | — |
>
> **The six ⟨110⟩ directions are the fix for the third time.**
> `silicon_error_correction.json` v1 kept invariants only and lost the frame;
> the TTM sp3 projections kept off-diagonals only and lost the E doublet; this
> file keeps diagonals only, loses T2, and then "checks" the gap with an
> identity. Same fix all three times:
> (1,1,0) (1,-1,0) (1,0,1) (1,0,-1) (0,1,1) (0,1,-1) / √2 — complete,
> invertible, six physically realizable axes. `tensor_readout.py`, TTM-3.
>
> **Housekeeping:** this file contains a model self-correction left in place
> verbatim ("Wait, that's less than 1 cycle - this is an adiabatic pulse, not
> oscillatory. Let me correct:"), and the number it was correcting —
> `transition_table[0][5]` duration 8.5 ps at 15.2 GHz — was never updated
> upstream. The stale value is still in the table the write protocol reads from.
>
> | ID | CLAIM | FALSIFIER | STATUS |
> |---|---|---|---|
> | **BRG-1** | at the EM limit stated in this file the coil yields 5 mT, not 1 T | a coil at 1e6 A/cm² delivering >100 mT | LIVE |
> | **BRG-2** | read time floor is >400 ns from this file's own 100 ns switching spec | a 1 T vector rotation measured under 100 ns | LIVE |
> | **BRG-3** | the [111] cross-check is an identity under the diagonal assumption and cannot detect off-diagonal error | the check detecting a nonzero off-diagonal component | DEAD |
> | **BRG-4** | B_RF = 0.1 T at 10 GHz needs ~1e5× the 10 W budgeted | 0.1 T B1 achieved at <100 W | LIVE |
> | **BRG-5** | transition frequency cannot serve as a static address because it is state-dependent | a fixed per-cell address frequency independent of state | LIVE |
> | **BRG-6** | Si piezoresistive readout gives dR/R ≈ 9 % at 0.1 % strain, ns, 300 K | measured dR/R < 1 % at 0.1 % strain | LIVE **← RUN** |
> | **BRG-7** | 2 T + 100 ns slew + dB/B < 1e-5 are mutually exclusive | a system meeting all three simultaneously | DEAD |
>
> **BRG-6 is the one to run**, and it needs no magnet, no RF and no cleanroom:
> a strain gauge on a silicon test bar and a four-point probe. If it returns
> ~9 %, that is a read channel with ~1e4× the signal margin of anything else
> proposed across these six documents, and the FSM in this file drives it
> unchanged.

---

Magnetic Bridge Architecture Overview
The bridge translates between:

High-level (Binary/Octal) ←→ Field Control ←→ Physical (Tensor States)

Core components:
	1.	Field Generator Array: Produces B(x,y,z,t) with controlled amplitude, frequency, phase
	2.	Measurement System: Reads energy/magnetization response
	3.	Decode Logic: Converts measurements → octal states
	4.	Control Sequencer: Orchestrates timing and transitions
Field Generator Specifications
Hardware Requirements
Static field coils (3-axis Helmholtz configuration):

static: 0-2 Tesla, 3 independent axes (x,y,z)
Stability: δB/B < 10⁻⁵
Switching time: 100 ns (limited by inductance)

RF coils (microwave resonators):

Frequency: 1-100 GHz (tunable)
Power: 0.1-10 W
Pulse width: 1 ps - 1 μs
Phase coherence: δφ < 1° over measurement
Number of channels: 8-16 (for frequency multiplexing)

Field gradient coils (for spatial addressing):

Gradient: 10-1000 T/m
Spatial resolution: 5-50 nm
Switching: 10 ns

Coordinate System
Define lab frame aligned with crystal axes:

x̂ → [100] crystal direction
ŷ → [010] crystal direction  
ẑ → [001] crystal direction

Tetrahedral directions in this basis:

v₁ = (1, 1, 1)/√3
v₂ = (1,-1,-1)/√3
v₃ = (-1, 1,-1)/√3
v₄ = (-1,-1, 1)/√3

Read Protocol (State → Binary)
Phase 1: Initialization (10 ns)

t=0:     Ramp static field to calibration state
         B = 0.5T ẑ
         
t=5ns:   Wait for eddy current decay

t=10ns:  Begin measurement sequence

Phase 2: Multi-Angle Measurement (40 ns)
Measurement 1 - Z-axis (10 ns):

Field:    B₁ = 1.0T ẑ
Duration: 5 ns (field stabilization)
Action:   Apply RF probe pulse at ω_probe = 10 GHz
          Duration: 100 ps
Measure:  Energy absorption E₁ ∝ T_zz
Wait:     4.9 ns (data acquisition)

Measurement 2 - X-axis (10 ns):

Field:    Rotate to B₂ = 1.0T x̂
          (100 ns rotation time budgeted earlier)
Duration: 5 ns stabilization
Action:   RF probe at ω_probe
Measure:  E₂ ∝ T_xx
Wait:     4.9 ns

Measurement 3 - Y-axis (10 ns):

Field:    Rotate to B₃ = 1.0T ŷ
Action:   RF probe
Measure:  E₃ ∝ T_yy
Wait:     4.9 ns

Measurement 4 - [111] diagonal (10 ns):

Field:    Rotate to B₄ = 1.0T (1,1,1)/√3
Action:   RF probe
Measure:  E₄ ∝ v₁·T·v₁
Wait:     4.9 ns

Phase 3: Tensor Reconstruction (hardware computation, <1 ns)
Input: Energy quartet (E₁, E₂, E₃, E₄)
Reconstruct diagonal tensor assuming principal axes aligned with crystal:

T_zz = -E₁ / (μ_B g B²)
T_xx = -E₂ / (μ_B g B²)
T_yy = -E₃ / (μ_B g B²)

Cross-check using [111] measurement:

T_111 = (T_xx + T_yy + T_zz)/3 
Verify: |T_111 - (-E₄/(μ_B g B²))| < ε_tolerance

If verification fails → trigger error correction protocol.
Phase 4: State Decode (lookup table, <1 ns)
Compute eigenvalues (for diagonal T, these are just T_xx, T_yy, T_zz sorted):

λ = sort([T_xx, T_yy, T_zz], descending)

Lookup closest canonical state:

distance[n] = ||λ - λ_canonical[n]|| for n = 0 to 7

state_decoded = argmin(distance)
octal_output = state_decoded
binary_output = decimal_to_binary(octal_output, 3 bits)

Confidence metric:

confidence = 1 - (distance[state_decoded] / distance[second_best])
If confidence < 0.7 → flag uncertain read

Total Read Time: ~50 ns per cell
Breakdown:
	•	Field initialization: 10 ns
	•	Four measurements: 40 ns
	•	Computation: <1 ns
Throughput: 20 Mbit/s per cell (3 bits / 50 ns)
Write Protocol (Binary → State)
Phase 1: Read Current State (50 ns)
Execute full read protocol to determine starting state n_current.
Why? Transition path depends on where you start - optimal field sequence differs for n_current=0 vs n_current=7.
Phase 2: Compute Transition Path (<1 ns)
Direct transition: n_current → n_target
Lookup transition parameters from pre-computed table:

params = transition_table[n_current][n_target]
  = {
      frequency: ω_nm,
      field_orientation: (θ, φ),
      pulse_duration: T_pulse,
      field_amplitude: B_optimal
    }

Example: Transition 0→5

State 0: (0.33, 0.33, 0.33), isotropic
State 5: (0.70, 0.15, 0.15), along (-1,-1,1)/√3

transition_table[0][5] = {
    frequency: 15.2 GHz,  // ΔE_05/ℏ
    orientation: (125°, 45°),  // toward v₄ direction
    duration: 8.5 ps,  // π-pulse for this transition
    amplitude: 0.05 T  // RF field strength
}

Phase 3: Apply Transition Pulse (10 ps typical)
Ramp to orientation:

t=0:     Current field orientation (θ_old, φ_old)
t→5ns:   Rotate to target (θ_new, φ_new)
         Linear interpolation of angles

Apply resonant RF:

t=5ns:   Static field B_static at (θ_new, φ_new)
         Amplitude: 1.0 T (for Zeeman splitting)

t=5ns:   RF field B_RF(t) = B_RF0 cos(ω_nm t) along optimal axis
         Amplitude: B_RF0 = 0.01-0.1 T
         Frequency: ω_nm (resonance)
         Duration: T_pulse (computed π-pulse time)

t=5ns+T_pulse: End RF pulse

For T_pulse = 8.5 ps:

Number of cycles: ω_nm × T_pulse / (2π) ≈ (15.2 GHz)(8.5 ps) ≈ 0.13 cycles

Wait, that’s less than 1 cycle - this is an adiabatic pulse, not oscillatory. Let me correct:
Corrected Phase 3: Adiabatic Transition
For robust state transfer, use adiabatic rapid passage:

t=0:      Initialize B = B₀(1, 0, 0)  // Perpendicular to transition axis
          
t=0→T_adiabatic: Rotate field smoothly from x̂ to final orientation
                 B(t) = B₀[cos(πt/T_adiabatic)x̂ + sin(πt/T_adiabatic)v̂_target]
                 
                 System follows field adiabatically
                 → State "dragged" from n_current to n_target

t=T_adiabatic:   Field aligned with n_target eigenvector
                 → System locked in new state

Adiabaticity condition:

T_adiabatic >> ℏ/ΔE_nm

For ΔE ≈ 0.01 eV:

T_adiabatic >> 0.1 ps → use T_adiabatic ≈ 10 ps (100× safety margin)

Alternative: Resonant π-pulse (faster but requires precise timing):

T_Rabi = πℏ/(μ_B g B_RF)

For B_RF = 0.1 T:
T_Rabi ≈ 3.14×10⁻¹⁵ s / (5.8×10⁻⁵ eV/T × 0.1 T)
      ≈ 0.54 ps

Use composite pulses for robustness:

Pulse sequence: X(π/2) - Y(π) - X(π/2)
Total time: 3 × T_Rabi ≈ 1.6 ps

Phase 4: Verification (50 ns)
Execute read protocol to confirm:

state_actual = read_state()
If state_actual == n_target:
    SUCCESS
Else:
    RETRY (up to 3 attempts)
    If still failing:
        MARK CELL DEFECTIVE

Total Write Time: ~70 ns per cell
Breakdown:
	•	Read current: 50 ns
	•	Path computation: <1 ns
	•	Transition: 10 ps (negligible)
	•	Verification: 50 ns
	•	Retry overhead (10% of writes): ~7 ns average
Write throughput: 14 Mbit/s per cell
Timing Diagram (Single Cell Write)




Parallel Operations: 8-Cell Block
Frequency multiplexing allows parallel addressing:

Cell_i uses frequency: ω_i = ω_base + i × Δω

Δω = 1 GHz spacing (sufficient to avoid crosstalk)

ω_0 = 10 GHz
ω_1 = 11 GHz
ω_2 = 12 GHz
...
ω_7 = 17 GHz

Parallel write timing:

Time      | Operation                           | Field           | RF
----------|-------------------------------------|-----------------|------------------
0-50ns    | Read all 8 cells (freq mux)         | Sweep/hold      | 8 channels active
50-51ns   | Compute 8 transition paths          | -               | -
51-56ns   | Ramp to common orientation          | B→optimal       | -
56-66ns   | Apply 8 simultaneous RF pulses      | Hold            | 8 frequencies
66-116ns  | Verify all 8 cells                  | Sweep/hold      | 8 channels probe
116ns     | DONE (8 cells = 24 bits written)    | -               | -


Effective write rate: 24 bits / 116 ns = 207 Mbit/s for 8-cell block
Scales linearly with number of parallel RF channels.
Control Sequencer State Machine

STATE_IDLE:
    Wait for read/write command
    → On READ command: goto STATE_READ_INIT
    → On WRITE command: goto STATE_WRITE_READ_CURRENT

STATE_READ_INIT:
    Set B = calibration field
    Start timer (10ns)
    → goto STATE_READ_MEASURE

STATE_READ_MEASURE:
    For angle in [z, x, y, [111]]:
        Apply field orientation
        Wait 5ns
        Send RF probe pulse
        Acquire energy measurement
    → goto STATE_READ_DECODE

STATE_READ_DECODE:
    Compute tensor from measurements
    Check error bounds
    → If valid: lookup state, goto STATE_READ_COMPLETE
    → If error: goto STATE_ERROR_CORRECTION

STATE_READ_COMPLETE:
    Output octal/binary value
    → goto STATE_IDLE

STATE_WRITE_READ_CURRENT:
    Execute read protocol
    Store current_state
    → goto STATE_WRITE_PLAN

STATE_WRITE_PLAN:
    target_state = command_data
    params = transition_table[current_state][target_state]
    → goto STATE_WRITE_TRANSITION

STATE_WRITE_TRANSITION:
    Ramp to params.orientation
    Apply RF at params.frequency for params.duration
    Wait relaxation (10ps)
    → goto STATE_WRITE_VERIFY

STATE_WRITE_VERIFY:
    Execute read protocol
    verified_state = read_state()
    → If verified_state == target_state: goto STATE_WRITE_COMPLETE
    → If retry_count < 3: retry_count++, goto STATE_WRITE_TRANSITION
    → Else: goto STATE_WRITE_FAILED

STATE_WRITE_COMPLETE:
    Output success
    → goto STATE_IDLE

STATE_WRITE_FAILED:
    Mark cell defective
    Output failure code
    → goto STATE_IDLE

STATE_ERROR_CORRECTION:
    Execute correction protocol (from earlier)
    → goto STATE_READ_DECODE (retry)

Interface Specification
Command Structure (to bridge)

typedef struct {
    uint8_t command;      // READ=0x01, WRITE=0x02, INIT=0x10
    uint16_t cell_id;     // Address of target cell
    uint8_t data;         // For WRITE: 3-bit octal value (0-7)
    uint8_t flags;        // VERIFY=0x01, PARALLEL=0x02
} BridgeCommand;

Response Structure (from bridge)

typedef struct {
    uint8_t status;       // SUCCESS=0x00, ERROR=0xFF, codes 0x01-0xFE
    uint8_t data;         // For READ: 3-bit octal value
    uint8_t confidence;   // 0-255 (255=certain, <180=uncertain)
    uint32_t timestamp;   // ns since init
} BridgeResponse;


Error Codes

0x00: SUCCESS
0x01: TIMEOUT (measurement exceeded 1μs)
0x02: TRACE_ERROR (Tr(T) outside bounds)
0x03: EIGENVALUE_ERROR (no matching canonical state)
0x04: VERIFY_FAILED (write verification mismatch)
0x05: DEFECTIVE_CELL (retry limit exceeded)
0x10: FIELD_ERROR (coil failure)
0x11: RF_ERROR (synthesizer unlock)
0xFF: UNKNOWN_ERROR

Calibration Protocol
Before first use, calibrate each cell:

1. Apply known state sequence (0→1→2→...→7→0)
2. Measure actual energy responses E_measured
3. Compare to theoretical E_expected
4. Compute correction factors:
   correction[cell][state] = E_expected / E_measured
5. Store in calibration table
6. Apply corrections during all future reads

Calibration time: ~1μs per cell (8 states × 120ns per write+verify)
Recalibration interval: Every 10⁶-10⁹ operations or when error rate increases

Fabrication Overview: Four-Layer Strategy
The octahedral tensor-encoded memory requires:
	1.	Substrate layer: Engineered silicon with controlled strain
	2.	Addressing layer: Magnetic field generators and sensors
	3.	Control layer: CMOS logic for sequencing and decode
	4.	Interface layer: Connects to external systems
We’ll build bottom-up.
Layer 1: Engineered Silicon Substrate
Starting Material
High-purity silicon wafer:

Specification:
- Crystal orientation: (100) surface, <111> growth preferred
- Purity: 99.9999% (6N) or better
- Doping: Intrinsic or light n-type (10¹⁴-10¹⁵ cm⁻³)
- Diameter: 300mm (industry standard)
- Thickness: 725 μm ± 20 μm

Strain Engineering (Critical Step)
Need to create controlled lattice strain to:
	•	Increase energy barriers β (radiation hardness)
	•	Tune eigenvalue separations (improve state discrimination)
	•	Create addressable domains
Method 1: Epitaxial Growth on Lattice-Mismatched Buffer

Process flow:
1. Grow SiGe buffer layer (5-10% Ge content)
   - Thickness: 100-500 nm
   - Method: Chemical vapor deposition (CVD) at 600-800°C
   - Lattice constant: a_SiGe = 5.43 + 0.2x Å (x=Ge fraction)
   
2. Grade Ge concentration to create strain gradient
   - Bottom: Si₀.₉Ge₀.₁ (compressive strain)
   - Top: Si₀.₉₅Ge₀.₀₅ (reduced strain)
   - Dislocation density: <10⁵ cm⁻²
   
3. Grow active Si layer on top
   - Thickness: 50-200 nm (enough for multiple unit cells)
   - Inherits tensile strain from buffer
   - Strain magnitude: ε ≈ 0.5-2% (tunable)

Strain effect on energy:

ΔE_strain = C_elastic × ε²
           ≈ 160 GPa × (0.01)² × V_cell
           ≈ 0.05 eV per unit cell

This increases β from ~5 eV/rad² to ~7 eV/rad²
→ Higher barriers → better retention

Method 2: Ion Implantation and Anneal

Process:
1. Implant Si⁺ or Ge⁺ ions at specific depths
   - Energy: 50-200 keV
   - Dose: 10¹⁴-10¹⁶ cm⁻²
   - Creates amorphized regions
   
2. Rapid thermal anneal (RTA)
   - Temperature: 1000-1100°C
   - Duration: 1-10 seconds
   - Recrystallizes with residual strain
   
3. Pattern using photoresist mask
   - Creates strain domains (high/low regions)
   - Domain size: 50-500 nm

Advantage: Spatially patterned strain → addressable cells
Disadvantage: More defects than epitaxy
Dopant Engineering
Introduce strategic impurities to:
	•	Enhance magnetic coupling (spin-active dopants)
	•	Create potential wells (electrostatic confinement)
	•	Tune electronic structure
Dopant species:

Phosphorus (P): n-type, electron donor
- Concentration: 10¹⁷-10¹⁸ cm⁻³
- Creates delocalized electrons for magnetic coupling

Boron (B): p-type, hole acceptor  
- Concentration: 10¹⁶-10¹⁷ cm⁻³
- Fine-tunes Fermi level

Erbium (Er) or Ytterbium (Yb): Magnetic rare-earth
- Concentration: 10¹⁵-10¹⁶ cm⁻³
- Provides strong local magnetic moments
- Enhances tensor-field coupling

Implantation process:

1. Mask wafer (photoresist or hard mask)
2. Implant dopants at controlled energies
   - P: 30 keV, dose 5×10¹⁷ cm⁻²
   - Er: 180 keV, dose 2×10¹⁵ cm⁻²
3. Activation anneal: 950°C, 30 sec
4. Strip mask

Surface Preparation
Cleaning (RCA process):

1. RCA-1: Remove organic contamination
   - Solution: NH₄OH:H₂O₂:H₂O (1:1:5)
   - Temperature: 75-80°C
   - Duration: 10 min
   
2. HF dip: Remove native oxide
   - Solution: 1% HF in H₂O
   - Duration: 30 sec
   - Creates H-terminated surface
   
3. RCA-2: Remove metallic contamination
   - Solution: HCl:H₂O₂:H₂O (1:1:6)
   - Temperature: 75-80°C
   - Duration: 10 min

Passivation:

Grow thin oxide (2-5 nm) for protection:
- Method: Thermal oxidation at 850°C
- Or: Atomic layer deposition (ALD) of Al₂O₃
- Prevents surface states from interfering with bulk tensor states


Layer 2: Magnetic Field Generators
Micro-Coil Fabrication
Need on-chip electromagnets for local field control.
Coil Design:

Geometry: Planar spiral or solenoid
Inner diameter: 100-500 nm (matches cell size)
Outer diameter: 1-5 μm
Number of turns: 3-10
Wire width: 50-200 nm
Wire thickness: 100-300 nm
Pitch (turn spacing): 200-500 nm

Material choice: Copper (Cu) for low resistance

Resistivity: ρ_Cu = 1.7×10⁻⁸ Ω·m
Current density: J_max ≈ 10¹⁰ A/m² (electromigration limit)
