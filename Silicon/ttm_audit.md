# TTM Audit — Tetrahedral Tensor Memory

Audit of the TTM architecture as stated across `Octahedral-computation.md`,
`Advanced-solutions.md` and `A.Addendum.md`.

Working code: [`tensor_readout.py`](tensor_readout.py) (TTM-2, TTM-3).
Every number below was recomputed; the arithmetic is in the falsifier table
at the bottom and reproducible from the module.

---

## HEADLINE — retention and switching are the same barrier. TTM forgets in picoseconds.

The documents treat `0.01–0.1 eV/bit` as the efficiency win. It is the
**fatal parameter**, because one number sets both:

```
tau = tau0 * exp(Ea / kT),   tau0 ~ 1e-13 s

Ea = 0.01 eV  ->  tau(300K) = 0.15 ps
Ea = 0.10 eV  ->  tau(300K) = 4.8  ps
```

That *is* the quoted switching time. It is also the **retention time**. The
state decays as fast as you can write it.

For 10-year retention at 300 K:

```
Ea = kT * ln(3.16e8 / 1e-13) = 1.280 eV      ~12.8x the top of the range
```

And `kT·ln2` at 300 K is **0.0179 eV**, so a 0.01 eV barrier sits **below
the Landauer floor** — the state is not thermodynamically distinguishable
from noise.

This is not a tuning problem. Thermal activation gives one knob and the
architecture spent it on write energy. Every real NVM solves this by making
the barrier **high** and knocking it down transiently during write
(field-assisted, heat-assisted). **The architecture is inverted.**

---

## SECOND — the sp3 readout is blind to half the state space

Contradiction between the sections: one derives the `ℓ=2 → E + T2`
decomposition under Td correctly, and the next proposes a readout that
cannot see `E`.

For the four sp3 directions, every projection has `rx² = ry² = rz² = 1/3`,
so the diagonal enters all four identically and cancels for traceless `T`:

```
s1 = (2/3)( Txy + Txz + Tyz)      s1 + s2 + s3 + s4 = 0
s2 = (2/3)(-Txy - Txz + Tyz)
s3 = (2/3)(-Txy + Txz - Tyz)
s4 = (2/3)( Txy - Txz - Tyz)
```

**Counterexample, verified in code:**

```
T = diag(1, -1, 0)  ->  s = (0, 0, 0, 0)
T = 0               ->  s = (0, 0, 0, 0)
```

Two distinct states, one fingerprint. "Resolves positions 0, 2, 3" is false:
it resolves T2-type states and collapses every E-type state onto zero.

Stated exactly — both ranks are true in their own domain and it matters
which is quoted:

| Domain | Rank | Sees |
|---|---|---|
| Full symmetric space (6-dim) | 4 | trace + T2. **Blind to E** |
| Traceless subspace (5-dim) | 3 | T2 only. **Blind to E** |

The four projections are independent as functionals on the full space — they
can read the trace — and become dependent the moment the trace is fixed,
which is the regime a deviatoric state variable lives in. Either way, two
dimensions of the state space have no readout.

### FIX

Six components need six independent projections. The six ⟨110⟩ directions
span `E + T2 + trace`, are invertible, and each is a physically realisable
measurement axis:

```
(1,1,0) (1,-1,0) (1,0,1) (1,0,-1) (0,1,1) (0,1,-1)  / sqrt2
```

`recover_tensor()` inverts them and returns the tensor exactly, including
the E-type state the sp3 basis could not see. **This also tells the
polarized-Raman channel from `optical_interface.md` which scattering
geometries to sample.**

---

## THIRD — magnetic control, fourth file, same root fault

| File | Magnetic claim |
|---|---|
| `Silicon_Error_Correction` v1 | "magnetic coupling loss > 10%" |
| 3D-Light doc | "Magneto-Optic Synergy" |
| this architecture | "B_crit ≈ 0.73 T lowers the barrier" |
| this architecture | "AR-ESR readout" |
| this architecture | "M ∝ T via residual orbital + L·S" |

**Numbers:**

```
Zeeman at 0.73 T:  g*mu_B*B = 2 * 5.788e-5 * 0.73 = 0.0845 meV
claimed barrier:                                    10-100 meV
fractional barrier change:                          0.08% - 0.85%

to reach 0.01 eV of Zeeman splitting:  B = 86.4 T
```

Destructive pulsed-magnet regime, off by ~2–3 orders.

**"M ∝ T via residual orbital term":** orbital angular momentum is
**quenched** in sp³ covalent bonding — ⟨L⟩ = 0 for real hybrid orbitals.
Spin-orbit in Si is 44 meV (split-off band), weak, which is exactly why Si
is the good spin-qubit host. There is no orbital moment tensor tracking the
geometric tensor. Asserted, no mechanism.

**AR-ESR:** perfect crystalline Si has **no unpaired spins** — all bonding
electrons are paired. ESR in Si reads *defects* (Pb, E′, dangling bonds) or
*dopants* (P donors). It cannot read lattice geometry. "ns-to-ps
single-shot, ~10 GHz readout" confuses the X-band **carrier** (9.4 GHz) with
measurement bandwidth; real single-spin readout is µs–ms via spin-to-charge.
Off by 3–6 orders.

### ROOT CAUSE — worth naming once, because it explains all four files

Every document needs a channel that **breaks the Td symmetry** to select a
transition, and each keeps reaching for magnetic, because that is the reflex
from spintronics.

**In silicon the symmetry-breaking channels are STRAIN and ELECTRIC FIELD.
Not magnetic.**

---

## THE REDIRECT — strain, and the numbers land exactly where the architecture wants

Uniaxial strain splits the Si conduction valleys via the deformation
potential:

```
dE = Xi_u * (e_zz - e_xx),    Xi_u = 9.16 eV

e = 0.1%  ->   9.2 meV
e = 1.0%  ->  91.6 meV        <- the 0.01-0.1 eV window, exactly
```

against **0.0845 meV** for 0.73 T. **Strain beats magnetic by ~1080× at
achievable magnitudes**, and 1%-strained Si has been in production CMOS
since the 90 nm node.

### One consistent stack across four documents, zero magnetic terms

| Role | Channel | Established in |
|---|---|---|
| State variable | strain tensor | `silicon_error_correction.json` v2.0 |
| Write | optomechanical, g₀/2π ~1e5–1e6 Hz | `optical_interface.md` |
| Select | strain valley splitting | this document, retargeted |
| Read | polarized Raman → eigenvectors, sampled on the six ⟨110⟩ | `optical_interface.md` + `tensor_readout.py` |

---

## Photon recycling and thermal claims (`A.Addendum.md`)

| Claim | Status | Why |
|---|---|---|
| "passive gain mechanism — increases local excitation density without raising incident flux" | **FATAL** | Brightness (étendue) theorem: passive optics cannot exceed source radiance. Recycling **reduces loss**; it does not create **gain**. Each Stokes-shifted pass is strictly lossy, and a closed recycling cavity thermalizes toward the source rather than amplifying |
| `f_rad <= 0.03` with TIR | **WRONG** | Escape-cone fraction is `1 − cos(θc)`, `θc = asin(1/n)`. n=1.5 (polymer LSC) → **25.5%**; n=3.48 (Si) → **4.2%**. `f = 0.03` requires **n > 4.11**. A typical LSC loses 25%, not 3% — off by ~8.5× |
| "sapphire, or Al₂O₃" | **TELL** | Sapphire *is* single-crystal Al₂O₃, listed as two materials |
| Heat-sink material choice | **WRONG** | k (W/m·K): DLC ~1–10, sapphire ~35, **silicon ~150**, diamond ~2000. Every listed "conductive base" is *worse* than the Si it sits on — that is a thermal **resistor**, not a sink. Only true diamond helps |
| "fractal microfins" | **WEAK** | Fin efficiency `tanh(mL)/(mL)` collapses on fine branches while viscous pressure drop rises. Surface area is not the binding constraint; "fractal" per se buys nothing |
| Servo priority: "if dJ/dT ≠ 0, prioritize thermal before field" | **BUG** | Inverts cascade control. Thermal τ ~ ms–s; electronic ~ns–ps. You close the **fast inner loop** and let the slow outer loop trim. As written, the fast disturbance stays uncorrected for the whole thermal settle |
| "long-term κ² coherence" | **CATEGORY ERROR** | κ² is a dipole **orientation** factor (0–4, isotropic average 2/3). Not a coherence quantity |
| "photons recycle as nutrients; heat becomes respiration" | n/a | Narrative layer, no claim to audit |

---

## What survives — keep these

| Section | Status |
|---|---|
| Deviatoric decomposition, J₂, J₃, Lode angle | **CORRECT.** Keep |
| `ℓ=2 → E + T2` under Td | **CORRECT.** Keep — and it is the tool that diagnoses the readout defect |
| `argmax \|rᵀ dT r\|` = principal eigenvector | **CORRECT MATH.** Retarget `r` from B-field to strain axis |
| Stokes-shift engineering to cut self-absorption | **REAL.** Keep as loss reduction, not gain |
| Moth-eye / graded-index input coupling | **REAL**, standard |

---

## Falsifiers

| ID | Claim | Falsifier | Status |
|---|---|---|---|
| **TTM-1** | Retention = switching time for any single-barrier thermally-activated cell. Ea ≥ 1.28 eV for 10 yr @ 300 K | A thermally-activated cell with retention ≫ switching at one barrier | LIVE |
| **TTM-2** | The sp3 4-projection readout is rank-deficient and blind to the E doublet | Any E-type state distinguished by `{s_i}` | LIVE, **verified in code** |
| **TTM-3** | Six ⟨110⟩ projections fully determine a symmetric rank-2 tensor | A symmetric tensor not recovered from the six | LIVE, **verified in code** |
| **TTM-4** | Strain beats magnetic by ~1e3 for Td symmetry breaking in Si | A sub-tesla field producing >10 meV splitting in undoped Si | LIVE |
| **TTM-5** | Passive photon recycling cannot raise local excitation density above the source brightness limit | Measured local excitation exceeding the étendue bound | LIVE |

TTM-2 and TTM-3 are settled by `python Silicon/tensor_readout.py` — they are
the two that needed no experiment.

---

## Related claim series in `Silicon/`

| Series | Subject | Register |
|---|---|---|
| SIL-1..4 | Strain-fault detection, invariant blindness | `silicon_error_correction.json` |
| OSE-1..4 | ⟨111⟩ bond-direction state encoding | `octahedral_state_encoder.json` |
| LO-1..5 | Optical interface, centrosymmetry, mode-size | `optical_interface.md` |
| TTM-1..5 | This document |
| FP-1..5 | Field propulsion momentum bounds | `field_propulsion_protocol.md` |

*License: CC-BY-4.0*
