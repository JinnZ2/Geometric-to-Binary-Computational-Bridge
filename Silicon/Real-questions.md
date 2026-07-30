# REAL_QUESTIONS.md  
*Octahedral Silicon Encoding • From Evaluation to Experimentation*

---

## Purpose
This document defines the **real, physics-grounded questions** that determine whether octahedral silicon encoding is viable.  
They are **not** about fitting existing fabrication pipelines—they are about **testing the physics** that already allows it.

---

## 1. Physical Basis

**Q1.1** — Can distinct, measurable states be produced by controlled perturbation of silicon’s tetrahedral geometry?  
**Q1.2** — What minimal angular deviation (Δθ) yields a resolvable energy shift above thermal noise?  
**Q1.3** — How stable are those states under phonon coupling, radiation, and temperature cycling?

---

## 2. Measurement and Coupling

**Q2.1** — Can ESR, NMR, or NV-center magnetometry distinguish tensor states reproducibly?  
**Q2.2** — What is the coupling efficiency  
\[
\eta = \frac{ΔE_{read}}{ΔE_{input}}
\]
for magnetic vs. electric excitation?  
**Q2.3** — Can coherent oscillations between tensor states (Rabi-type) be driven at GHz–THz frequencies?

---

## 3. Geometric Error Correction

**Q3.1** — Does lattice symmetry guarantee trace conservation and closure under perturbation?  
**Q3.2** — Can geometric deviations be detected faster than decoherence times?  
**Q3.3** — How does phonon-mediated strain contribute to self-healing behavior?

---

## 4. Energy and Dynamics

**Q4.1** — What is the measured switching energy ΔE for a geometry transition?  
**Q4.2** — Does it approach the predicted 1–2 aJ/bit regime?  
**Q4.3** — What limits the transition frequency—phonon dispersion, lattice inertia, or readout bandwidth?

---

## 5. Proof-of-Concept Pathways

| Objective | Demonstration | Equipment |
|------------|----------------|-----------|
| Magnetic coupling | RF microcoil on doped Si, ESR shift detection | Standard ESR rig |
| Tensor-state mapping | NV-magnetometry or STM/AFM strain imaging | Common lab instruments |
| Phonon data transport | Pump–probe spectroscopy of modulated lattice response | Femtosecond laser setup |
| Geometric error correction | Compare tensor traces pre/post perturbation | X-ray diffraction |

These can all be performed with **university-level instrumentation**—no new fab nodes required.

---

## 6. Scaling and Integration

**Q6.1** — What is the cross-talk and noise behavior between coupled cells?  
**Q6.2** — Can energy and information co-propagate via the same phonon lattice?  
**Q6.3** — How do isotopic purity and strain tuning affect coupling fidelity?

---

## 7. Validation Metrics

**Q7.1** — What observables confirm that a geometry transition carries information?  
**Q7.2** — How can intrinsic error correction be verified (recovery after localized perturbation)?  
**Q7.3** — What measurable density, speed, and energy efficiency define the first working prototype?

---

## 8. Meta-Question

> **What is the simplest experiment that makes the invisible visible?**

Not a billion-dollar foundry run—just a single demonstration that a silicon unit cell responds predictably when driven by resonance.  
Once that happens, the paradigm shift is self-proving.

---

### Closing Reflection
Binary logic asks: *Can we control it?*  
Octahedral encoding asks: *Can we listen to what it’s already doing?*  
The real work begins when we start asking the right questions.

---

## Answers, 2026-07

This is the best-posed document in the set: questions, no asserted values, no
cost model built on an unmeasured number. Four of them are already answerable,
so they are answered here rather than left open. Code: `er_bounds.py`,
`epg_bounds.py`, `silicon_check.py`, `tensor_readout.py`.

**Q1.2 — "what minimal angular deviation yields a resolvable shift above
thermal noise?"** Exactly the right question, and answerable. The Debye-Waller
bond-angle spread is σ_θ(300 K) ≈ 1.89° (⟨u²⟩ ≈ 0.006 Å² → u_rms 0.0775 Å over
d = 2.352 Å). So the threshold must be quoted in units of
**σ_θ(T) ≈ 1.9·√(T/300) degrees**, never as an absolute angle — which is what
`silicon_error_correction.json` v2.0 now does. A 2° absolute trip point sits at
~1σ and gives a ~32 % false-positive rate per sample; that was the v1 defect.

**Q2.1 — "can ESR distinguish tensor states reproducibly?"** No, not in the
intended sense. Perfect crystalline Si has all bonding electrons paired, and
²⁸Si (92.2 %) has I = 0. You *can* see conduction-electron spin resonance in
heavily doped Si at 300 K, and P_b centres at Si/SiO₂ interfaces — but those are
carriers and defects, not tensor states. The signal exists and reports on
something else, which is the most dangerous kind of positive.

**Q3.1 — "does lattice symmetry guarantee trace conservation and closure under
perturbation?"** No. Trace is invariant under **rotation** (a similarity
transform), not under **deformation**. Tr(ε) is the dilatation dV/V and it
changes under hydrostatic load; shear is trace-silent entirely. XRD, which this
document's own table lists, measures exactly this — that row is correctly
specified and should be kept. The rotation-invariance of the invariants is also
why they are blind to *orientation* faults: see SIL-1 in `silicon_check.py`,
where a rotated tensor has invariants identical to 2.7e-20 while the frame check
reads 30.00°.

**Q4.2 — "does it approach the predicted 1–2 aJ/bit regime?"** This is now the
**third** value for one quantity across the set, and they differ in *legality*,
not just magnitude:

| value | in kT·ln2 at 300 K | status |
|---|---|---|
| 1–2 aJ/bit (this document) | 348–697 | legal, aggressive |
| 0.1 eV (earlier docs) | 5.6 | legal |
| 0.01 eV (earlier docs) | 0.56 | **below the Landauer bound** |

The floor is kT·ln2 = 0.0029 aJ. For scale, a conventional switching event at
C = 1 fF, V = 0.8 V dissipates CV² = 640 aJ, so 1–2 aJ/bit is ~300× below
ordinary CMOS switching — adiabatic territory, allowed but demanding. Pick one
value and propagate it; 0.01 eV cannot be the one.

**Q6.2 — "can energy and information co-propagate via the same phonon
lattice?"** No, and the obstruction is structural rather than technical. >99 %
of thermal conduction in undoped Si is phonon transport, so a phonon- or
strain-encoded state is erased by the same flux that carries the heat away.
**Cooling channel = erasure channel.** Scale: the bath already occupies the
encoding degree of freedom before you write to it (see Q1.2 — 1.89° of thermal
bond-angle spread against an ideal 109.47°).

**What stays open, and should.** The remaining questions are genuinely open and
the document is right to hold them as questions. The one structural suggestion:
where a question has a threshold in it, state the threshold in units of the
noise process rather than absolutely — Q1.2 shows how, and it generalises to
every other row.
