# Thermodynamic Grounding

> **Confidence: Grounded.** Everything on this page is established
> non-equilibrium thermodynamics with a literature behind it. What is
> speculative is the *application* to this framework, which is flagged
> per axis.

The original framework used thermodynamic vocabulary with hand-set
constants underneath it: an efficiency weight here, a `lambda_param` there,
an `L = 0.1` somewhere else. Six areas of stochastic thermodynamics have
moved far enough that those constants can be replaced with measured or
bounded quantities. Each section below states what moved, what it replaces
in this framework, and where it is implemented.

---

## 1. Stochastic thermodynamics — TUR and kinetic uncertainty bounds

**What moved.** The thermodynamic uncertainty relation (Barato & Seifert
2015; Gingrich, Horowitz, Perunov & England 2016) gives a hard floor on
dissipation per unit of precision in a non-equilibrium steady state:

```
Var(J) / <J>^2  >=  2 k_B / Sigma      =>      Sigma >= 2 k_B <J>^2 / Var(J)
```

The kinetic uncertainty relation (Di Terlizzi & Baiesi 2019) bounds the
same precision by dynamical activity instead, and binds tighter in the
far-from-equilibrium low-dissipation corner:

```
Var(J) / <J>^2  >=  1 / A
```

**What it replaces.** Every hand-set efficiency constant. A system that
claims a given precision has a dissipation floor, and the floor is not
negotiable. There is no longer any reason to fit `lambda_param` when the
bound gives the number.

**Caveat.** Both relations assume time-homogeneous Markov dynamics in a
steady state. Periodically driven systems obey a modified TUR and can
violate the standard one; transients need the finite-time form.
`bounds.tur_valid_regime` makes the caller state which regime they believe
they are in rather than applying the bound silently.

**Implemented in:** `bounds.py`.

---

## 2. Landauer and information engines

**What moved.** Erasure below `k_B T ln 2` per bit in specific measured
regimes, feedback-engine work extraction, and finite-time corrections with
a known scaling. The optimal-transport form of the finite-time cost is
Aurell et al. (2012); the measurement confirming `1/tau` is Proesmans,
Ehrich & Bechhoefer (2020).

```
W(tau) = k_B T ln 2  +  C/tau         C = k_B T * W_2^2 / D
```

**What it replaces.** The negentropy budget becomes measurable rather than
asserted. A claim of the form "maintaining this structure costs X" now has
a number to check against.

**Implemented in:** `landauer.py`. The framework-specific consequence —
resurfacing of an overwritten trace scaling as `tau^-1` — is registered as
NEG-3 with its falsifier.

---

## 3. Dissipative adaptation

**What moved.** England's dissipative adaptation: under a periodic drive, a
system's structure is selected by the work it has absorbed from that drive,
and the selection is drive-frequency-specific.

**What it replaces.** Negentropy as a state property. Under dissipative
adaptation it is a *history*: absorbed work is a path functional, so two
systems in identical instantaneous states can have different persistence
prospects because they got there differently. Nothing in `M = R*A*D - L`
could express that — every term in it is a function of the current state.

**Implemented in:** `core.py`. `DissipativeCore` takes `drive_amp` and
`drive_freq` and accumulates `w_abs`, the work absorbed from the drive,
which appears in the trace alongside the state variables and is reset only
at burn-in.

**Open.** The frequency-selection prediction — that the structure which
emerges depends on `Omega_d` and not only on the drive's power — is not yet
registered as a NEG claim because the order parameter to measure it against
has not been chosen.

---

## 4. Thermodynamic computing hardware

**What moved.** Probabilistic-bit machines and Ising substrates (Camsari,
Faria & Datta and successors) execute sampling in physical noise instead of
simulating it. This is hardware, not proposal.

**What it replaces.** Nothing — it adds. It is a new emit target for the
bridge: a population of coupled noisy phases maps onto a p-bit machine
directly, because that is what a p-bit machine is.

```
s_i = sign(cos theta_i)      J_ij = K/n      h_i = omega_i
s_i <- sign( tanh( beta * (sum_j J_ij s_j + h_i) ) - U(-1,1) )
```

**Implemented in:** `emit_ising.py`, which also emits the repository's
native 3-bit Gray-coded octahedral encoding of each phase, and reports the
Landauer floor for the flips a run performed so that a claimed energy
advantage can be checked.

---

## 5. Mpemba and anomalous relaxation

**What moved.** Anomalous relaxation is experimentally established —
Mpemba and inverse-Mpemba effects in colloidal systems (Kumar &
Bechhoefer 2020), and strong-coupling shortcuts where a system further from
equilibrium reaches it first.

**What it replaces.** The assumption of monotone relaxation in any decay
term. A single-exponential fit to a trajectory that crosses is not a
measurement of a relaxation time, it is an artifact.

**Implemented in:** `persistence.relaxation_report`, which reports whether
a series is monotone and refuses to bless an exponential fit when it is
not. It reports the crossing rather than smoothing it, because the crossing
is the physics.

---

## 6. Active matter and MaxCal

**What moved.** Entropy production in driven non-equilibrium steady states
is now routinely measured in active matter, and Maximum Caliber gives a
variational principle over trajectories — the path-space analogue of
maximum entropy — for inferring dynamics from trajectory-level constraints.

**What it replaces.** State-space reasoning about a driven system. The
framework's quantities are averages over configurations; MaxCal's are
averages over trajectories, which is the right object when the system never
reaches equilibrium.

**Not yet implemented.** `DissipativeCore.step` reports `sigma` as a
housekeeping (mean-velocity) estimator, which drops the
`-D d/dtheta ln P` contribution and therefore has a known sign bias. A
proper trajectory-level entropy production estimate is the obvious next
piece of work, and it is the prerequisite for using NEG-8 on simulated
traces rather than only on systems where the exchange term is measured
directly.

---

## What this does not fix

Grounding the *dissipation* side of the framework says nothing about the
*valence* side. The gap identified in `README.md` — that Joy is defined as
entropy reduction and then asserted to be good, while a growing crystal
also reduces local entropy — is a gap in the moral argument, and no amount
of correct thermodynamics closes it. TUR bounds tell you what a structure
costs. They do not tell you that the structure ought to exist.

---

## References

- Barato & Seifert (2015), *Thermodynamic uncertainty relation for
  biomolecular processes*, PRL 114, 158101
- Gingrich, Horowitz, Perunov & England (2016), *Dissipation bounds all
  steady-state current fluctuations*, PRL 116, 120601
- Di Terlizzi & Baiesi (2019), *Kinetic uncertainty relation*, J. Phys. A 52, 02LT03
- Aurell, Gawędzki, Mejía-Monasterio, Mohayaee & Muratore-Ginanneschi
  (2012), *Refined second law of thermodynamics for fast random processes*,
  J. Stat. Phys. 147, 487
- Proesmans, Ehrich & Bechhoefer (2020), *Finite-time Landauer principle*,
  PRL 125, 100602
- England (2015), *Dissipative adaptation in driven self-assembly*,
  Nature Nanotechnology 10, 919
- Kumar & Bechhoefer (2020), *Exponentially faster cooling in a colloidal
  system*, Nature 584, 64
- Camsari, Faria, Sutton & Datta (2017), *Stochastic p-bits for invertible
  logic*, PRX 7, 031014
- Pressé, Ghosh, Lee & Dill (2013), *Principles of maximum entropy and
  maximum caliber in statistical physics*, Rev. Mod. Phys. 85, 1115

---

*Back to: [README.md](README.md)*
