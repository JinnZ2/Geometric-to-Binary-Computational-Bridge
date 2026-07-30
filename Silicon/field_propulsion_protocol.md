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

FP-1, FP-2, FP-3 and FP-5 are settled by `python Silicon/propulsion_bounds.py`.
They needed no apparatus.

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

*License: CC-BY-4.0*
