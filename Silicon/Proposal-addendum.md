# R_2 Test Protocol — Geometric Phase Cancellation

> **AUDIT 2026-07 — the geometry is right, the two-mode protocol is right, and
> the conclusion does not follow.** Numbers in `transient_suppression.py`,
> settled by `tests/test_transient_suppression.py` (59 tests, no apparatus).
>
> **R2-1, the mode mismatch.** Counter-wound bifilar + differential drive adds;
> + common-mode drive cancels. Self-consistent. But **the write pulse *is* the
> differential drive** — its field is the one mode the geometry is built to
> PASS, at full amplitude, by design. R_2 measures rejection of the mode the
> write pulse does not use, then concludes something about the mode it does.
> `R_2 = 10^3` or `10^6` says nothing about the write field's own kick.
>
> What R_2 *does* de-risk, and it is worth having: ground bounce, shield
> currents, capacitive pickup from the generator, EMI. All genuinely
> common-mode. State that as the purpose and this document becomes true.
>
> **R2-8 — the premise is inverted, and this was not in the audit.** At the
> field an on-chip coil can legally deliver (5.03 mT at the electromigration
> limit, `magnetic_authority.py`), a 5 ps pulse rotates a spin by
> `θ = 2πγBt = 4.42 mrad`, which is **0.14 % of a π pulse**. A 5 ps π pulse
> needs `B1 = 3.57 T`, **710× the coil**. So the write pulse cannot collapse
> spin coherence — it is ~700× too weak to move the spin at all. The risk is
> not that the write pulse is too violent; it is that **the write does not
> happen.** Engineering 60 dB of suppression against a transient that could at
> most produce 4 mrad of unwanted rotation optimises the wrong quantity by
> three orders.
>
> | claim | status | correct value |
> |---|---|---|
> | `R_2 ≥ 10³ (60 dB)` from "sub-µm matching" | **40 dB, or 20 dB** | residual scales as 1/Δ. On a 10 µm coil, 100 nm matching → Δ = 1e-2 → 40 dB; 1 µm → Δ = 1e-1 → **20 dB**. The audit took the generous reading of "sub-µm"; the shortfall against 60 dB is **20–40 dB**, not 20. |
> | 60 dB is reachable by growing the coil | **TRAP** | 60 dB at 100 nm matching needs a **100 µm** coil, which drops field-per-amp straight back into the shortfall in `Magnetic-bridge.md`. |
> | one mismatch number suffices | **NO** | amplitude mismatch and arrival-time skew are independent and add in quadrature. Two channels at 1e-2 give **37 dB**, not 40. Both must independently reach 1e-3. |
> | 60 dB at 5 ps needs 5 fs skew = 0.43 µm | **CRITERION-DEPENDENT** | time-domain peak residual (`τ ≤ T/1.4R`) gives **3.57 fs = 0.31 µm**; spectral rejection at the top of the band (`τ ≤ 1/2πf_max R`) gives **0.80 fs = 0.068 µm**, ~6× tighter. The audit used the looser one without saying so. Either way "sub-µm" sits on or past the boundary with no margin. |
> | R_2 is a single number | **UNDERSPECIFIED** | skew-limited rejection is `1/(2\|sin πfτ\|)`. At 5 fs skew: **90 dB at 1 GHz, 44 dB at 200 GHz.** A CMRR measured at 1 GHz flatters by 46 dB. The criterion must name a frequency. |
> | `R_2 = B_CM,input / B_CM,residual` | **NOT MEASURABLE** | the cancellation *is* the geometry; you cannot remove it without building a different device, so the numerator is necessarily theoretical. R_2 is a model-vs-measurement ratio, and modelling error inflates it in the flattering direction. |
> | 5 ps pulse can address a transition | **NO** | bandwidth ≈ 200 GHz (1/Δt) or 88 GHz (Gaussian) against a Zeeman splitting of 28 GHz at 1 T, 56 GHz at 2 T. Ratio ≥ 1 in *every* convention, so a "π-pulse" of this bandwidth is not a π-pulse. The audit's "4–7×" is the 1/Δt convention; Gaussian gives 1.6–3.2×. Conclusion unchanged. |
> | "THz" pulse | **WRONG BAND** | 1–10 THz sits 1.2–2.6 orders above ESR at 1–2 T (28–56 GHz). Consistent with the `Magnetic-bridge.md` finding from the other side: correct `T_Rabi` at 0.1 T is 178 ps, **36× longer** than the 5 ps budgeted. |
> | "ultrafast OPM" | **8 ORDERS SHORT** | optically pumped magnetometers are atomic-vapour spin-precession devices, DC-to-kHz by construction: ~1 kHz typical, ~10 kHz best, against 200 GHz needed. |
> | "pickup loop >200 GHz" | **NOT THE LOOP** | λ/10 at 200 GHz is 150 µm, buildable. The **digitizer** is not: fastest real-time scopes ~110–160 GHz, sampling ~70–110 GHz. And loop area, hence sensitivity, collapses. |
> | probe, missing | **THE RIGHT TOOL** | time-resolved **magneto-optic** (Faraday/Kerr) pump-probe sampling. Resolution set by the ~100 fs optical pulse, no digitizer in the path, measures B directly. Note electro-optic sampling (ZnTe/GaP, to ~7 THz) reads **E**, not B. |
>
> **R2-2, the well-posed replacement**, using only the two drives already
> specified, both terms measured, no model, no unwinding, same afternoon:
>
>     CMRR = (response to DM drive) / (response to CM drive)
>
> at matched input current, same sensor, same position — and **stated at a
> frequency**. Note the order: DM/CM, so that bigger is better. CMRR is also
> the standard figure the rest of the world reports, so the result is comparable
> to prior art.
>
> **R2-7, the spin system is unspecified and Si does not supply one.** Perfect
> crystalline Si has all bonding electrons paired — no unpaired spins — and
> Si-28 (92.2 % natural) has I = 0. **Seventh file in this set to require a
> magnetic degree of freedom the material does not have.** The one real
> candidate is P donors in isotopically enriched ²⁸Si, which is genuinely
> superb (T₂ reaching seconds) but needs enrichment, typically < 10 K, and is a
> *different device* from the strain/tensor encoding in the other six documents.
>
> Fork to name before this test is worth running — the two branches share no
> physics:
>
> - **strain** → there is no spin coherence to protect and this document is
>   moot. The piezoresistive read path has no coherence requirement at all.
> - **donor spin** → it is a spin qubit, and the tensor encoding, the octahedral
>   state space and the Frenkel-pair gate set do not apply to it.
>
> **The right criterion for the write pulse.** The write field must be present
> at the target — that is its job. The risk is not its amplitude but whether its
> **time integral** is a controlled rotation: `θ = γ ∫B₁ dt`, π-pulse at
> `γ∫B₁dt = π`. So the figure of merit is **shot-to-shot area
> reproducibility**, and infidelity ≈ `(δθ)²/4`. Corrected arithmetic: 1e-4
> infidelity gives `δθ = 0.02 rad`, which is an *absolute* rotation error; the
> *fractional* area stability is `0.02/π = 0.64 %`, **not 2 %**. The 2 % figure
> is the right answer to a different question — it corresponds to 1e-3
> infidelity. Measured by the same MO sampling setup.
>
> **And residual rotation error is already a solved problem** — with open-loop
> methods, which preserve exactly the latency property this document wants:
> composite / dynamically-corrected pulses (BB1, CORPSE, SCROFULOUS) and
> refocusing sequences (Hahn echo, CPMG) suppress error to second order or
> better. The document rejects "algorithmic" solutions as latency-bound, which
> conflates a **control loop** with a **pulse sequence**. They are not the same
> thing.
>
> **KEEP:** the two-mode drive protocol (differential then common, matched
> amplitude, same sensor position) — correct and standard, keep verbatim.
> "Latency-free: works at the speed of physics, no control loop" — correct, and
> for the right reason: passive symmetry beats feedback at ps timescales.
> "Fabrication-bound, not algorithm-bound" — correct framing, and it is what
> makes the tolerance number the whole story. The bifilar structure itself is
> genuinely useful, for the common-mode sources listed above.
>
> **UNDEFINED:** "Holographic Write" appears once with no definition and no
> antecedent in the other six documents. "Layer-2 Transient Engineering
> requirement for Phase 1" references a structure not present here.
>
> | ID | CLAIM | FALSIFIER | STATUS |
> |---|---|---|---|
> | **R2-1** | the write pulse is differential-mode, so common-mode suppression cannot reduce its own kick on the spins | a write scheme whose field is common-mode at the target | LIVE **← FORK** |
> | **R2-2** | R_2 as defined needs a theoretical numerator; CMRR from the two stated drives is fully measurable | a measurement of `B_CM,input` on the cancelling structure | DEAD |
> | **R2-3** | sub-µm matching yields 20–40 dB, not 60, by both geometric and timing routes | 60 dB measured at sub-µm matching | LIVE **← RUN** |
> | **R2-4** | 60 dB at 5 ps needs 0.8–3.6 fs arrival-time match = 0.07–0.31 µm on-chip path | 60 dB with >5 fs skew | LIVE |
> | **R2-5** | a 5 ps pulse's bandwidth exceeds the full Zeeman splitting at 1–2 T in every transform convention; it cannot be selective | selective transition driving demonstrated with a 5 ps pulse | LIVE |
> | **R2-6** | OPMs are kHz-class and cannot serve as a >200 GHz probe | a >1 GHz OPM | DEAD |
> | **R2-7** | undoped crystalline Si supplies no unpaired spins; a donor-spin device is a different architecture from the strain/tensor line | measured unpaired-spin resonance in undoped float-zone Si | LIVE |
> | **R2-8** | at the legal coil field a 5 ps pulse delivers 4.4 mrad, 0.14 % of π, so there is no coherence collapse to suppress | a 5 ps pulse producing >0.1 π rotation at ≤10 mT | LIVE |
>
> **R2-3 is the cheap decisive one** — no spins, no cryostat, no THz source.
> Fabricate the bifilar pair at your achievable matching tolerance, drive it
> with a fast electrical pulse, measure CMRR by magneto-optic sampling *at a
> stated frequency*. If it lands at 40 dB, the criterion moves or the coil
> grows, and you know that before committing to a spin system.
>
> **R2-1 and R2-8 decide whether the file has a subject at all**, and they are
> free: name the state variable. If it is strain, there is nothing here to
> protect.

---

⚡ \mathbf{R_2} Test Protocol: Geometric Phase Cancellation

This experiment validates the Geometric Phase Cancellation mechanism as the primary method for suppressing THz-pulse-induced magnetic transients. It replaces the latency-limited electronic feed-forward approach with a passive, symmetry-protected cancellation geometry capable of operating at the picosecond timescale.

The goal is to demonstrate that a 5\,\text{ps} THz write pulse can be delivered without collapsing spin coherence by achieving a transient suppression factor of:

\mathbf{R_2 \ge 10^3} \quad (\ge 60\,\text{dB})

⸻

1. Testbed Configuration: Cancellation Geometry Setup

The testbed isolates the geometric cancellation physics independent of the spin system. It uses a prototype coil structure that enforces differential write coupling while passively cancelling common-mode magnetic excursions.

Components:
	•	Bifilar THz Write Antenna (Counter-Wound Helices)
Fabricated to sub-µm matching tolerance; supports differential and common-mode excitation.
	•	Picosecond Pulse Generator
Capable of producing 1–10\,\text{ps} pulses with controlled amplitude for both drive modes.
	•	High-Bandwidth Magnetic Field Sensor
e.g., on-chip THz B-dot probe, ultrafast OPM, or pickup loop with >200 GHz bandwidth.

Purpose:
Validate that geometric symmetry cancels magnetic transients before they couple into the active region.

⸻

2. Test Protocol: Deterministic Cancellation Measurement

This protocol quantifies cancellation for both intended (differential) and undesired (common-mode) excitations.

Step
Mode
Purpose
A. Differential-Mode Drive
Current flows in opposite directions in the paired helices
Confirms the write pulse field couples efficiently into the target region (intended spin rotation axis)
B. Common-Mode Drive
Current flows in the same direction in both helices
Measures how well geometry suppresses transient magnetic fields


Procedure:
	1.	Deliver calibrated picosecond pulses in differential mode; measure field at sensor → baseline “write-useful” B-field.
	2.	Deliver pulses in common-mode with identical amplitude; measure residual transient B-field at same sensor location.
	3.	Compute cancellation factor R_2 (below).

⸻

3. Success Metric: Geometric Suppression Factor

The suppression factor quantifies how effectively the coil geometry rejects common-mode transients:

\mathbf{R_2 = \frac{B_{\text{CM, input}}}{B_{\text{CM, residual}}}}

Where:
	•	B_{\text{CM, input}} is the theoretical or measured common-mode field without cancellation
	•	B_{\text{CM, residual}} is the measured field at the active zone during the write pulse

Success Criterion:

\boxed{\mathbf{R_2 \ge 10^3 \; (60\,\text{dB})} \text{ at the ps timescale}}

Achieving this verifies that the geometry alone suppresses the destructive transient by at least three orders of magnitude—without relying on active electronics, feedback, or timing-critical control.

⸻

✅ Why This Test De-Risks the Architecture
	•	Latency-Free: Works at the speed of physics—no control loop needed.
	•	Fabrication-Bound, Not Algorithm-Bound: Performance scales with coil matching accuracy, not DSP bandwidth.
	•	Spin-Safe: Once validated, THz pulses will not introduce coherence-killing B-field kicks during operation.

Outcome:
This test provides high-confidence validation that the 5\,\text{ps} Holographic Write pulse can be executed without collapsing spin coherence, satisfying the Layer-2 Transient Engineering requirement for Phase 1.
