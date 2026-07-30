# Polarization-Resolved Optical Interface to Strain-Tensor States in Diamond-Cubic Silicon

> **Supersedes** `3D_LIGHT_ENHANCED_OCTAHEDRAL_PROCESSING.md`, moved to
> `legacy/`. That document had three FATAL defects; the audit is at the
> bottom of this page.
>
> **Companion to** `silicon_error_correction.json` v2.0 — this supplies the
> eigenvector read channel that spec left flagged OPEN.

---

## The symmetry error, and why it matters more than a label

"Octahedral geometry of silicon" is wrong twice, and the two wrongs point in
**opposite directions**:

| | Correct | What the docs said |
|---|---|---|
| **Site** symmetry | **Td** — tetrahedral, sp³, 109.47° | "octahedral" |
| **Crystal** point group | **Oh** (m-3m), Fd-3m — **centrosymmetric** | conflated with the site |

The site is *not* Oh. The crystal *is* Oh, and Oh has an **inversion centre
at the bond midpoint**. That inversion centre is the whole ballgame for
optics:

```
centrosymmetric  =>  chi(2) = 0 BY SYMMETRY
                 =>  no Pockels effect
                 =>  no second-harmonic generation
                 =>  no linear electro-optic state switching
```

Bulk Si has **no second-order optical nonlinearity**. This is the single most
consequential fact in silicon photonics, and it is exactly what the old
document's core mechanism — "polarization induces transitions between
configurations" — needs and does not have.

Calling it "octahedral" accidentally lands on the *right crystal class for
the wrong reason*, and the right class is the one that **forbids the proposed
mechanism**.

### Where 8 states actually come from

The 8-state / 3-bit premise **survives**, but not for the stated reason. It
was justified as "octahedral coordination provides 8 vertices". An
octahedron has **6 vertices** — log₂6 = 2.585 bits, which does not give a
clean 3-bit code. Octahedral *coordination* is 6-fold.

An octahedron has **8 faces**, and its face normals point along
⟨111⟩ — the same 8 directions as the vertices of the dual cube. In diamond
cubic those are exactly the sp³ bond directions:

```
sublattice A bonds : (1,1,1) (-1,-1,1) (-1,1,-1) (1,-1,-1)      4
sublattice B bonds : the inverted set                            4
union              : the complete <111> body-diagonal set        8   -> 3 bits
```

Verified: the two sets are related by inversion (180° apart, pairwise), and
the angle between two bonds of one sublattice is 109.4712° — the tetrahedral
angle.

So: **8 = the 8 ⟨111⟩ directions = 4 sp³ bonds × 2 sublattices**, which is
Td-site symmetry plus the inversion that makes the crystal Oh. The count is
right, the bit width is right, and the derivation should say "faces" or
"⟨111⟩ directions", never "octahedral vertices".

---

## Substrate

| Property | Value |
|---|---|
| Crystal point group | Oh (m-3m), Fd-3m. **CENTROSYMMETRIC** |
| Site symmetry | Td |
| Bandgap | 1.12 eV, **INDIRECT** |
| Transparency window | 1.1 µm to ~8 µm |
| n @ 1.55 µm | 3.48 |
| χ⁽²⁾ | **0 by symmetry** |
| Magneto-optic response | **NEGLIGIBLE.** No isolator, no MO switching |

---

## READ channel — viable

**Polarization-resolved Raman at 520.7 cm⁻¹.**

Si has three optical phonon modes at Γ, triply degenerate in the unstrained
crystal. Strain **lifts the degeneracy**:

- the **splitting pattern** gives the strain **eigenvalues**;
- the **polarization dependence** of each split peak gives the strain
  **eigenvector orientation**, through the Raman tensor selection rules of
  the Oh crystal.

```
scattering geometry  z(xy)z-bar  ->  couples one mode
scattering geometry  z(xx)z-bar  ->  couples the others
```

Rotate the input and output polarizers, watch which peak lights up, read the
frame.

**Which directions to sample is not free.** `tensor_readout.py` settles it:
the four sp³ bond directions are rank-deficient and blind to the E doublet,
so a readout built on them cannot see two dimensions of the state space. The
six ⟨110⟩ directions are complete and invertible. See
[`ttm_audit.md`](ttm_audit.md), TTM-2 and TTM-3.

**This is the missing channel.** `silicon_error_correction.json` v2.0
established that strain invariants (I₁, J₂, J₃) are blind to pure
reorientation and that the eigenvectors are required — then flagged the
readout as OPEN because unpolarized Raman gives only the spectrum.
Polarization resolution supplies the eigenvectors. It is standard technique,
not new physics, and it is the only thing in the superseded document that
does real work.

| | |
|---|---|
| Strain resolution | ~1e-4 |
| Latency | ~1 ms |
| Role | **MONITOR.** Detects after the fact; cannot gate a ps event |

---

## WRITE channel — viable

**Optomechanical: photoelastic coupling + radiation pressure in a Si
nanobeam photonic crystal.**

Photon → phonon → strain. This is a genuine light-to-geometry coupling, and
it is the honest route.

| | |
|---|---|
| Coupling | g₀/2π ~ 1e5 – 1e6 Hz |
| Speed | GHz |
| Addresses | **MODE-scale strain, ~1e8 unit cells. NOT individual lattice sites** |

---

## THROUGHPUT — viable

**Mode-division multiplexing with OAM / vector modes.** Real and deployed.
It multiplies throughput on a waveguide, which is the correct domain for
structured light.

Keep the throughput application. Delete the state-manipulation application.
Same technology, correct scale.

---

## Real light→lattice channels in Si

Replacements for the deleted mechanisms:

| Mechanism | Magnitude | Speed | Status |
|---|---|---|---|
| **Plasma dispersion** (free carrier) | Δn = −[8.8e-22·ΔNe + 8.5e-18·ΔNh^0.8], cm⁻³ | ps–ns | **THE workhorse.** Every Si modulator ever built uses this |
| **Optomechanical** (radiation pressure + photoelastic) | g₀/2π ~ 100 kHz – 1 MHz | GHz | **The honest route from light to geometry** |
| Kerr χ⁽³⁾ | n₂ ~ 4.5e-18 m²/W @1.55 µm | fs | Real, weak. **Allowed** — odd order survives centrosymmetry |
| Thermo-optic | dn/dT = 1.86e-4 /K. Large | µs | Slow |
| Two-photon absorption | β ~ 0.8 cm/GW @1.55 µm | — | **LOSS.** A limit, not a tool. Budget it |
| Pockels χ⁽²⁾ | **ZERO** unstrained | — | **DEAD** unless strained; strain-induced reports are small and contested |

---

## Deleted

| Mechanism | Why |
|---|---|
| Magneto-optic control | Si is diamagnetic |
| Photon-driven site-level state switching | Mode-size mismatch, ~1e8 sites per mode |
| "Topologically protected" as an unqualified claim | Downgrade to "reduced backscattering under symmetry-preserving disorder" |

---

## Falsifiers

| ID | Test | Status |
|---|---|---|
| **LO-1** | Polarized Raman fails to resolve strain eigenvector orientation at 1e-4 → the read channel is dead and `silicon_error_correction.json` v2.0 has no eigenvector input | LIVE |
| **LO-2** | Any optical addressing of a lattice state below the diffraction limit λ/2n, without a near-field or tip-enhanced probe → the mode-size objection is wrong | LIVE |
| **LO-3** | Measurable Faraday rotation in undoped Si at sub-tesla fields → the magneto-optic deletion is wrong | LIVE |
| **LO-4** | Second-harmonic generation from unstrained bulk Si → the centrosymmetry claim is wrong | LIVE |
| **LO-5** | Optomechanical strain modulation exceeding the photoelastic bound → a channel not accounted for here | LIVE |

LO-1 is the one that matters most to the rest of the repository: the whole
v2.0 error-correction spec depends on an eigenvector channel existing.

---

## Audit of the superseded document

| Claim | Status | Why |
|---|---|---|
| "Octahedral geometry of silicon" (throughout) | **WRONG** | Site is Td, crystal is Oh. The document conflates them and takes its selection rules from neither |
| "Magneto-Optic Synergy" | **FATAL** | Si is diamagnetic; the Verdet constant is 2–3 orders below garnet MO materials, needing tesla-scale fields for degree-scale rotation over cm paths. This is not a gap in the document — it is **the** unsolved problem of the field. Silicon photonics has had no monolithic optical isolator after 20 years for exactly this reason. **Repeat of the fault in `Silicon_Error_Correction` v1** |
| "Photon-Driven State Manipulation" | **FATAL** | Si is indirect-gap, Eg = 1.12 eV. Radiative recombination needs a phonon for momentum; radiative lifetime ~ms against ~ns for direct-gap, IQE ~1e-6. Si is a poor emitter and a poorly-coupled absorber for state work. Also opaque below 1.1 µm — any "light" here is IR, not visible |
| "3D light controls octahedral states" | **FATAL** | **Mode-size mismatch.** Diffraction limit in Si is λ/2n = 1550/(2×3.48) = 223 nm against a 0.543 nm lattice constant: ~400× linear, ~1e8 unit cells per cavity mode volume. Structured light (OAM, skyrmions, knotted vortices) carries its structure in the *transverse* profile at wavelength scale, so it averages over ~1e8 sites. You cannot address a lattice state with a beam |
| "Topological Light Channels — topologically protected" | **PARTIAL** | Real physics, oversold. Protection is against backscattering from disorder that *preserves the protecting symmetry*. Not protected against out-of-plane radiation loss, material absorption, or symmetry-breaking disorder. Genuine time-reversal-broken protection **requires magneto-optics**, looping back into the fatal item above. Valley-Hall and spin-Hall analogues in Si are not truly protected |
| "Enhanced Data Throughput" | **SOUND** | The one application that survives intact |
| Philosophical Implications | n/a | Prose layer, no claim to audit |
| Whole document | — | No numbers, no units, no falsifiers. Same failure mode as the 17 lens functions in `Negentropic/`: asserted architecture with nothing to check |

---

## The magneto-optic fault is systematic

The same wrong premise — that silicon responds magnetically — appeared in
**three** files:

1. `Silicon_Error_Correction` v1: "magnetic coupling loss > 10%",
   "magneto-thermal relaxation event". Fixed.
2. This document: "Magneto-Optic Synergy". Superseded.
3. `Octahedral_State_Encoder` v1: read/write method
   `"magnetic field coupling (Zeeman basis)"`, `E_mag = -M : B_ext`, and a
   state literally named "magnetic bias". Fixed in v2.0.

A grep of `Silicon/` for magneto-optic language found no further *asserted*
instances; `Fabrication.md` mentions Faraday rotation only as an optional
imaging technique on other materials, which is legitimate, and the
`Magnetic-bridge` documents concern encoding *external* magnetic fields,
which silicon's diamagnetism does not refute.

*License: CC-BY-4.0*
