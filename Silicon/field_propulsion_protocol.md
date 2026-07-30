# Field Propulsion — Falsifiable Test Plan

> **Supersedes** the conceptual description in `FIELD_PROPULSION_SHAPE.md` and
> `Field_Propulsion_Analog.json`. Working code: [`propulsion_bounds.py`](propulsion_bounds.py).
>
> **Read §2 before building anything.** The proposed experiment, as designed,
> cannot return "no". That is fixable, and fixing it makes the apparatus
> *simpler*, not more elaborate.

---

## 1. The claim

> A 3-D helical array of phase-coupled oscillators, driven by a traveling-wave
> phase gradient (Δφ ≈ 3π/2) with logarithmically spaced frequencies, generates
> a net momentum flux (thrust) through the surrounding medium, analogous to an
> octopus jet **but without expelling reaction mass**.

The last clause is where it comes apart, and not for the usual reason. It is
not that reaction mass is hard to avoid — it is that **"momentum flux through
a medium" and "no reaction mass" are the same quantity with opposite signs**.
A momentum flux through air *is* expelled air momentum. An octopus jet is the
correct analogy and it works precisely *by* expelling reaction mass.

So the question was never "is there reaction mass". It is: **how much thrust
per watt does the carrier allow?** That has a hard answer.

---

## 2. FP-1 — the momentum bound, and why it inverts the experiment

A wave of speed `v` carrying power `P` carries momentum flux `P/v`. A radiator
cannot recoil harder than the momentum it emits:

```
F <= P / v
```

| Carrier | Thrust per watt | Power for the registered 0.1 mN |
|---|---|---|
| EM radiation | 3.34e-9 N/W | **30 kW** |
| Acoustic, air | 2.92e-3 N/W | **34 mW** |
| Acoustic, water | 6.75e-4 N/W | 148 mW |

**This inverts the meaning of a positive result.** A tabletop array delivers
of order 1 W. At that power:

- an electromagnetic effect is capped near **3 nN** — six orders below the
  registered threshold;
- an acoustic effect reaches 0.1 mN on **34 milliwatts**.

So measuring F > 0.1 mN does not support the exotic hypothesis. **It
identifies the mechanism as acoustic** — which is to say, it identifies a fan.
The registered threshold was chosen high enough to be measurable and thereby
landed squarely in the regime that only the mundane explanation can reach.

---

## 3. FP-2 — Δφ = 3π/2 is arithmetic, not a mystery

A closed array of `N` nodes supports traveling waves only at `Δφ = 2πm/N`.

For **N = 8**: `3π/2 = 2π·6/8`, so it is the `m = 6` mode. By aliasing,
`m = 6 ≡ m = -2` — a **backward** wave of two turns. Therefore:

```
Δφ = 3π/2   and   Δφ = -π/2   are the SAME excitation.
```

Two consequences:

1. The "empirically optimal 3π/2" needs no explanation involving
   non-linearities or finite-array effects. It is a traveling-wave condition,
   and for N = 8 it is the one two steps below the Nyquist limit.
2. **Any claim that 3π/2 is special while -π/2 is not is refuted by
   arithmetic, with zero experiments.** `aliased_modes()` prints the
   equivalence class.

For N = 6, `3π/2` is *not* an allowed mode at all — so the claim is also
node-count dependent in a way the original document does not state.

---

## 4. FP-3 — all four registered predictions are H₀ predictions

This is the methodological finding, and it survives any amount of Bayesian
machinery wrapped around the experiment.

| Registered prediction | Predicted by ordinary radiation? |
|---|---|
| F > 0.1 mN at Δφ = 3π/2 | **YES** — needs only 34 mW of acoustic power |
| Sign reverses when Δφ → −Δφ | **YES** — reversing the gradient reverses the wave direction, so streaming thrust reverses |
| F scales as N² | **YES** — N coherent sources give amplitude ~N, radiated power ~N², and F = P/v, so F ~ N² *exactly* |
| Helix beats ring | **YES** — a ring has no axial phase gradient, hence no axial streaming |

**A pre-registered prediction that both hypotheses make is not a test.** The
N² result is the clearest case: it is often quoted as the signature of a
coherent collective effect, and it is exactly what a coherent *radiator*
does. Pre-registration protects against moving the goalposts. It does nothing
about goalposts that were never in the field of play.

---

## 5. FP-4 — the one measurement that can return "no"

One ratio, two instruments, no phase sweep:

```
Measure F (calibrated force balance) and P (total radiated acoustic power,
integrated over a closed surface) SIMULTANEOUSLY.

    H0:  F <= P/v
    H1:  F  > P/v      thrust exceeding the momentum carried by the
                       radiation that produced it
```

`exceeds_momentum_bound(F, P, carrier, margin)` is that test.

Three things make it better than the original plan:

- **It can fail.** A ratio at or below 1 is consistent with ordinary
  radiation at *any* absolute thrust. Absolute thrust is not evidence;
  thrust per watt radiated is.
- **It needs no pre-registered phase angle.** The exotic claim, if true,
  holds at whatever Δφ maximises it. Registering 3π/2 added specificity
  without adding discriminating power.
- **It is cheaper.** A force balance and a calibrated microphone survey,
  against a phase sweep across three frequency spacings and two geometries.

`P` must be **radiated** power over a closed surface, not electrical input
power. Ohmic loss in the drivers produces heat and no momentum, and counting
it inflates the denominator, which biases the test *toward* the null. Getting
this wrong in the conservative direction is still getting it wrong.

### 5.1 What the measurement actually has to be — a correction

The version above says "one ratio, two instruments". That is right about the
physics and wrong about the statistics, and building the apparatus is what
exposed it. Recorded here rather than quietly fixed, because the error is
instructive.

**Do not average the ratio.** `mean(F/(P/v))` is a biased estimator and it
diverges as `P → 0`. Fit a slope instead:

```
F  =  k · (P_rad / v)  +  c · P_elec  +  b
```

`k` is the entire claim — the thrust as a multiple of the momentum bound, so
H₀ is `k ≤ 1`. `c` carries the confounders that scale with *electrical* rather
than radiated power (thermal plume, ohmic heating, convection), and `b` carries
amplitude-independent offsets (balance drift, electrostatic pull, mount
preload).

**Sweeping drive amplitude alone cannot work.** At fixed radiation efficiency
`P_rad = η·P_elec`, so the `k` and `c` regressors are collinear to within
power-meter noise — measured `corr = 0.996`, `VIF = 96`. In that design a
simulated anomaly of `k = 4` was absorbed almost entirely by `c` (fitted
2.56e-4 N/W = the 2.33e-4 anomaly plus the 2.0e-5 real thermal term) and `k`
came back as **−0.06 ± 0.06 with r² = 0.9998** — a numerically excellent fit
reporting a confident NULL on a world where H₁ was true, 40 times out of 40.
The noise is on the regressor `P_rad`, so errors-in-variables pulls `k` toward
zero as well; both failures point the same way, which is why the wrong answer
looked precise.

So the campaign must contain operating points where radiated power is
decoupled from electrical power:

| state | how | `P_elec` | `P_rad` |
|---|---|---|---|
| `open` | normal operation | full | full |
| `detuned` | driven off resonance (40 → 32 kHz) | ~full | a fraction |
| `muted` | absorber cap or clamped cones | full | ~0 |

`muted` is the classical thrust-balance control and it is what makes `c` and
`b` identifiable from data rather than from assumption. It carries a condition:
a muted state must be **verified** to draw the same electrical power as the
open state at the same amplitude. Blocking a driver's output changes its
acoustic load and hence its electrical impedance; if `P_elec` shifts, it is a
different operating point and the `c` it constrains is not the `c` acting in
the open state. `check_muted_control()` tests both halves of that.

**The decision is asymmetric**, and for a reason that is easy to get wrong:

```
ANOMALY      k − z·se >  margin      (margin ≥ 1; the calibration allowance)
NULL         k + z·se ≤  1
UNRESOLVED   anything between
```

Claiming the bound is violated requires clearing it with slack. Being
*consistent* with the bound requires only sitting under it. A single threshold
for both makes the null unreachable: with a null simulated at exactly `k = 1`,
`k + z·se < 1` is false for any nonzero `se`, and a correct analysis scored
7/30 on a world where H₀ held. Note also that `k = 1` is not what an ordinary
radiator does — `F = P/v` is the perfectly collimated limit, and a real source
of finite directivity sits well below it. **H₀ is `k ≤ 1`, not `k = 1`.**

A fourth verdict, `NON-IDENTIFIABLE`, is returned when VIF(k) exceeds 20 and
is checked *before* the others. A narrow interval on an unidentified parameter
is not evidence.

`Silicon/fp4_autopilot.py` implements this and runs the null-world self-test
from §11 before it will report anything. `Silicon/field_propulsion_fp4.ino` is
the instrument: an N = 8 phase-gradient driver that refuses to emit data until
the balance is tared, the radiated-power survey factor has been entered, and
the physical radiation state has been declared.

### 5.2 One apparatus note that can manufacture a false positive

λ at 40 kHz in air is 8.58 mm, so grating-lobe-free spacing is ≤ 4.29 mm.
Eight 10 mm transducers on a ring give a 13.1 mm radius and 10.0 mm spacing
= **1.17 λ**; 16 mm units give 1.87 λ. Any buildable 40 kHz ring of commodity
transducers is spatially aliased and has real grating lobes.

This does not affect FP-2 — traveling-wave mode indexing depends on the node
count, not the spacing — and it does not affect FP-4's validity, since the
momentum bound holds for any radiation pattern whatsoever. It does mean the
power survey must be a genuine closed-surface integral. The lobes put a
substantial fraction of the power off-axis, so an on-axis measurement scaled
by solid angle **undercounts `P_rad`, which biases `k` upward** — toward a
false anomaly. This is the single most likely way to get a spurious positive
out of this apparatus, and it is a *specific*, checkable error rather than a
general call for care.

---

## 6. Hypotheses, restated so they differ

**H₀** — All axial force is accounted for by momentum carried away in
radiated acoustic (or EM) waves, plus mechanical, thermal, and electrostatic
coupling through the mount. Formally: `F <= P/v` within calibration
uncertainty.

**H₁** — There exists an axial force exceeding `P/v` by a factor of at least
`margin` (set from the calibration budget, not chosen afterward).

Note that H₁ no longer mentions Δφ, N, geometry, or frequency spacing. Those
are *optimisation* parameters — worth sweeping once an anomaly exists, and
worth nothing before.

---

## 7. Hidden-variable candidates, ranked by prior probability

The pasted analysis lists these; the ordering matters and is not alphabetical.

1. **Acoustic streaming** — highest prior by a wide margin, and *not* an
   artifact to be eliminated. It is H₀'s mechanism. Rule it in, quantitatively,
   before looking for anything else.
2. **Mechanical coupling through the mount** — vibration rectified by the
   balance. Test: suspend on long filaments, look for a resonance signature.
3. **Thermal/convective plume** — drivers heat, air rises. Test: correlate
   with driver temperature; it has a characteristic minute-scale time constant
   that phase changes do not.
4. **Electrostatic attraction to nearby surfaces** — scales with V², not with
   phase gradient. Test: vary drive voltage at fixed phase pattern.
5. **EM force on the balance itself** — test with drivers electrically
   driven but acoustically muted (cones clamped).

A vacuum test does not appear here, and its absence is deliberate: in vacuum
the acoustic channel is gone, so the *only* remaining carrier is EM, capped
at 3 nN/W. **A vacuum test is therefore the cleanest version of the whole
experiment** — if thrust survives at more than a few nN per watt in vacuum,
that is the result. It is also the most expensive step, which is why it
belongs after FP-4 has been run in air.

---

## 8. Stopping rule

Terminate and publish the null when either:

- the measured `F/(P/v)` ratio stays below `margin` across the full
  achievable power range, with the 95% interval excluding `margin`; or
- 100 instrument-hours accumulate with no ratio above 1.

Record the null. A measured bound on an exotic thrust claim is a publishable
result and is what most of these experiments actually produce.

---

## 9. If the answer is no — the apparatus is still good for three things

Stated up front so that a null result is not a loss:

1. **Phase-coherent communication.** Modulate a data stream onto the same
   phase pattern and log bit error rate against Δφ. This is a real test of
   the Geometric-to-Binary Bridge premise, and it does not depend on the
   thrust claim at all.
2. **A phased acoustic array.** Beam steering, standing-wave levitation,
   material NDT. The hardware is a working ultrasonic phased array; that is
   not a consolation prize.
3. **A calibrated demonstrator of the momentum bound.** Measuring `F = P/v`
   accurately, and showing that it *is* the ceiling, is a genuinely good
   teaching apparatus.

---

## 10. Falsifiers

| ID | Claim | Falsifier | Status |
|---|---|---|---|
| **FP-1** | Thrust is bounded by `P/v`; 0.1 mN needs 30 kW via EM or 34 mW via air | A measured `F/(P/v)` ratio above 1 outside calibration error | LIVE, **arithmetic verified** |
| **FP-2** | Δφ = 3π/2 is the `m = -2` traveling-wave mode for N = 8 and is identical to Δφ = −π/2 | Δφ = 3π/2 and −π/2 producing measurably different thrust on the same N = 8 array | LIVE, **arithmetic verified** |
| **FP-3** | All four originally registered predictions are also H₀ predictions | Any of the four shown to be excluded by ordinary radiation | LIVE, **verified in code** |
| **FP-4** | `F > P/v` is the only registered test that can return "no" | A different single measurement with equal or better discriminating power | LIVE |
| **FP-5** | Coherent N² power scaling accounts for the N² thrust prediction with no anomalous term | N² thrust scaling with sub-N² radiated power | LIVE |
| **FP-6** | An amplitude-only sweep cannot separate `k` from `c`; the design needs a state where `P_rad` is decoupled from `P_elec` | An amplitude-only design recovering a hidden `k` with VIF > 20 | **REFUTED for amplitude-only** — VIF 96, `k = −0.06 ± 0.06` on a `k = 4` world, r² = 0.9998 |
| **FP-7** | The N = 8 drive table realises `φᵢ = +2πm·i/N`, and mode `m` and `m + 8` are the same drive table byte-for-byte | Two distinct tables for `m = 6` and `m = −2`, or a recovered gradient of the opposite sign | LIVE, **verified in code** |

FP-1, FP-2, FP-3 and FP-5 are settled by `python Silicon/propulsion_bounds.py`.
They needed no apparatus.

FP-6 and FP-7 are settled by `python tests/test_fp4_autopilot.py`. Neither
needed apparatus either, and both were found by code rather than by argument:
FP-6 by the null-world self-test refusing to pass, and FP-7 by recovering each
node's phase from the emitted drive table's fundamental Fourier bin and
comparing it against `propulsion_bounds.aliased_modes()`. The first version of
`buildPhaseTable` delayed node *i* by `(i·m) mod N` steps, which makes it
*lag*, so the wave ran the opposite way around the ring while every DATA line
reported the positive `Δφ`. FP-4 is sign-blind and would have survived that;
FP-2 and the sign-reversal prediction are precisely about which way the wave
goes, and they would have been read against a mislabelled drive.

---

## 11. On the FRET protocol in the same submission

The FRET mesocosm plan is a better-posed piece of work than this one — four
quantitative predictions, a defined null, a skeptical prior — but its
simulator has the defect this repository has now hit three times.

`MesocosmSimulator` generates data with `true_coupling = 0.3`, and
`BayesianFRETModel.estimate_coupling()` returns `0.3` for `'natural'` and
`0.15` for `'linear'`. Checked numerically, those agree **to machine
precision**:

| arrangement | simulator truth | model belief | match |
|---|---|---|---|
| natural, B=0 | 0.30000 | 0.30000 | exact |
| natural, B=50 | 0.27123 | 0.27123 | exact |
| linear, B=0 | 0.15000 | 0.15000 | exact |
| scrambled, B=0 | 0.01500 | 0.02000 | close |

H₁'s coupling estimator **is** the simulator's generative process, hand-copied
including the `(1 + 0.1·sin(B/10))` magnetic term. The Bayes factor cannot do
anything but diverge toward H₁. A simulation whose null cannot win is not a
test of the loop; it is a test of whether the multiplication works.

This is the same defect as `ASIS/asc_core.py`'s single-candidate hidden-variable
search — third occurrence, and the pattern is now clear enough to state as a
rule:

> **Before trusting an autopilot, run it against a world where the null is
> true.** If H₀ does not win there, the loop is not measuring the world.

The fix is one line: draw `true_coupling` from `{0, 0.3}` at random per run,
hide it from the model, and confirm the Bayes factor goes the right way in
both cases. Until that passes, no output from the FRET autopilot means
anything — and it is worth noting that the FRET *protocol* is sound; it is
only the simulator that is rigged.

### 11.1 The rule earns a corollary, and immediately catches its own author

The first thing `fp4_autopilot.py` did on being run was fail its own
null-world test — false-negative rate **40/40** — which is how §5.1 came to be
written. Two things came out of that, and both generalise past this apparatus:

> **The loop must also lose on a world where the null is false.** A one-sided
> check passes any analysis that can only ever say "null", which is the mirror
> image of the rigged simulator and just as empty.

> **A null world must be drawn from the null hypothesis, not from its
> boundary.** H₀ here is `k ≤ 1`; simulating it at `k = 1` tests the decision
> threshold rather than the world, and it scored a correct analysis as broken.
> The first version of `null_world_test` made exactly that mistake.

The generalisable form: a self-test needs a **power** check alongside its
false-positive check, and its synthetic worlds have to be drawn from the
interior of each hypothesis rather than from the line between them.

The FRET one-liner above inherits both. Drawing `true_coupling` from
`{0, 0.3}` is the two-sided version already, but only if the run confirms the
Bayes factor moves toward H₀ on the `0` draws — not merely that it moves
toward H₁ on the `0.3` draws.

*License: CC-BY-4.0*
