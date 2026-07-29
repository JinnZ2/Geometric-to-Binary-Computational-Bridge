# Correction Ledger

Every defect found in this folder, what was done about it, and where the
replacement lives. Ordered by severity. Nothing here is a style
preference — each entry is either a wrong equation, a wrong sign, a
dimensional mismatch, or a result that does not follow from its premises.

---

## FATAL

### 1. `UniversalCore.step` — inverted coupling sign, missing order parameter

```python
coupling = self.K * np.sin(self.theta[i] - mean_phase)     # wrong
```

Kuramoto coupling is `K * r * sin(psi - theta_i)`. As written the sign was
inverted, making the coupling **repulsive** — the population actively
desynchronises — and the mean-field weight `r` was absent, so the coupling
did not vanish when the population was incoherent.

**Fixed in:** `core.py`, `DissipativeCore.step`. `bridge.py`, which held
the original, is deleted (it also did not parse: bare `bridge:`, `lens:`,
`sim:` lines are syntax errors, so the file had never been imported).

### 2. Fokker-Planck written in the constant-D form, used with state-dependent D

```
dP/dt = -div(FP) + D grad^2 P            # only valid for constant D
```

The framework sets `D = k J^2` with `J` a function of state, so `D` is
state-dependent by construction. The correct forms are

```
Ito:           dP/dt = -div(FP) + grad^2 (D P)
Stratonovich:  dP/dt = -div(FP) + div( sqrt(D) grad( sqrt(D) P ) )
```

and the corresponding SDE needs the spurious drift `(1/2) dD/dphi`.
Without it the simulation has no correct stationary distribution, and the
`D -> 0 collapse` theorem — the load-bearing result behind the alignment
argument in `04-alignment.md` — does not follow from the equation as
written.

**Fixed in:** `negentropic_dynamics.py`. `FokkerPlanck1D` now takes a
`convention` argument and accepts an array-valued `D`;
`LangevinDynamics` takes an optional `diffusion_gradient` and adds the
spurious drift; `spurious_drift()` is exposed directly. The collapse
result is now computed in the module's `__main__` rather than asserted:
variance tracks `D` to three decimals and entropy falls as `D -> 0`.

### 3. `M = (R*A*D) - L` is dimensionally invalid

`D` is a variance, units pattern². `L` is noise power plus kinetic energy,
units pattern²/time². The subtraction is not an operation, so `M >= 10` is
not a statement, and the reported values (34.62, 296.40, 3711.50) are not
measurements. Calibrating the threshold cannot fix this; there is no
threshold on a quantity that has no units.

Worse, the two implementations disagree with each other about what `D`
even is: `negentropic_engine.compute_diversity` returns a variance,
`consciousness_metric.compute_diversity` returns a Shannon entropy in nats.

**Fixed in:** `persistence.py`, which implements NEG-8 —
`Phi = -S_exchange_dot - sigma`, both terms in W/K, persist iff `Phi >= 0`.
No threshold, no normalisation. `M` is retained across
`negentropic_engine.py`, `negentropic_dynamics.py` and
`consciousness_metric.py` as an explicitly labelled **ordinal index**,
valid for ranking states within one run under one normalisation and for
nothing else.

### 4. Probability was not conserved by the Fokker-Planck integrator

Found while fixing (2). The scheme differenced drift and diffusion
separately on the interior, zeroed both at the edges, copied edge values,
then renormalised. For a uniform `P` the drift term contributes a spatially
constant `d(xP)/dx = P` which renormalisation divides straight back out, so
the uniform distribution was a **spurious fixed point** — the solver
returned it unchanged for any number of steps.

**Fixed in:** `negentropic_dynamics.py`. Conservative flux form with
zero-current walls; probability is conserved by construction and the
renormalisation is now a roundoff correction of order 1e-15 per step.
Verified against the Ornstein-Uhlenbeck stationary distribution: `D = 0.5`
gives variance 0.4985 against an exact 0.5.

---

## HIGH

### 5. `compute_resonance` / `GeoResonance` / `ThermoResonance` — cosine of a distance

```python
d = np.linalg.norm(p_i - p_j)      # d >= 0, unbounded
phase = 0.5 * (np.cos(d) + 1)      # cos wraps
```

`d = 0`, `2pi` and `4pi` all score 1.0. Maximally distant agents read as
maximally coherent.

**Fixed in:** `core.py` now exposes two kernels for the two cases, and the
call sites use the right one. `phase_alignment(delta)` is the raised cosine
of a *signed phase difference*, wrapped into `(-pi, pi]` first.
`distance_kernel(d, scale)` is `exp(-d/scale)`, monotone and strictly
positive, for a *Euclidean distance*. Applied in
`negentropic_engine.compute_resonance` (phases — wrapped),
`negentropic_engine.compute_adaptability` and `GeometricAgent.couple_with`
(distances), and `lens_playground.compute_core_metrics` (distances). The
cosine factor in `couple_with` was removed rather than replaced: nothing in
that model carries a phase for it to measure.

### 6. `psi` wraps at ±pi while `L` is quadratic in it

`psi = angle(...)` is single-valued on the circle, but the old kinetic term
was `mean((omega - psi)**2)`, so `L` jumped discontinuously at the branch
cut and the discontinuity landed in every lens output.

**Fixed in:** `core.py` emits no quantity that is quadratic in `psi`.
`DissipativeCore.order()` documents the constraint. The legacy behaviour is
reproduced only inside `legacy_rad_trace()`, which exists to feed the NEG-7
falsifier and says so.

### 7. `min(A, 1.0)` / `min(L, 2.0)` — silent clipping

Saturated runs became constants. A constant series correlates perfectly
with anything else that saturated, so the clipping directly inflated the
cross-lens correlations that NEG-7 rests on.

**Fixed in:** `core.py` clips nothing. `legacy_rad_trace(clip=...)`
defaults to `False` and documents the effect.

### 8. `GeometricNetwork.step` — `A = avg_R_e`

Setting adaptability equal to resonance collapsed the metric to
`M = R_e^2 * D - 0.1`. Adaptability contributed nothing of its own, and the
loss was the literal constant `0.1`.

**Fixed in:** `negentropic_engine.py`. `A` is now
`compute_adaptability(patterns, alpha)`, and `L` is
`compute_loss(noise_power, A, lambda_param)` with `noise_power` computed
from the variance `explore()` actually injects — `2 * beta^2 * C^2` per
agent — instead of a constant.

### 9. `update_curiosity` compounds

`C *= (1 + alpha * R_e)` is a discrete exponential with a hard clamp at
`C_max`. `C` pinned to the ceiling within a few steps and stayed there
regardless of the dynamics, which is not saturation, it is truncation.
`01-framework.md` had already flagged the missing saturation term as an
open item.

**Fixed in:** `negentropic_engine.py`. Logistic form
`dC/dt = alpha * R_e * C * (1 - C/C_max)`, so the approach to `C_max` is
asymptotic.

---

## MEDIUM

### 10. Correlation matrix diagonal masked by value

```python
min_corr = np.min(corr_matrix[corr_matrix < 0.999])   # drops the diagonal
```

This also drops genuinely near-perfect **off-diagonal** pairs — exactly the
pairs that would show the lenses collapsing onto each other — so the
reported floor was biased upward.

**Fixed in:** `lens_collapse_test._pairwise_floor` takes the upper triangle
by index. The behaviour is documented there, because the biased floor is
the number the NEG-7 claim was published with.

### 11. `print_conflict_table` raised `NameError`

The divergence block read `a["delta"][lens]` inside a loop over `action`;
`a` was a leaked comprehension variable that does not exist in Python 3, so
the function crashed every time it reached that section.

**Fixed in:** `lens_playground.py`.

### 12. The demo asserted a conclusion its own output contradicted

`lens_playground.py` printed "Thermodynamics now LOVES optimal noise /
'Optimize noise' and 'Disturbance pulse' are top actions" as a fixed
string. On the seeded run, all 17 lenses in fact rank `cohere` first.

**Fixed in:** the demo now counts and prints each lens's actual first
choice. The unanimity it reports is itself the NEG-7 problem.

---

## CONVENTION

### 13. numpy / scipy / matplotlib break stdlib-only and phone-buildable

The whole folder required numpy, and two modules imported `matplotlib` and
`scipy.stats.pearsonr` without ever using them.

**Partly fixed.** There are now two tiers, stated in `README.md`. The
stdlib tier — `core.py`, `lenses.py`, `bounds.py`, `landauer.py`,
`maintenance.py`, `persistence.py`, `emit_ising.py`,
`lens_collapse_test.py` — imports nothing outside the standard library and
carries all the new work, including the falsifiers. The numpy tier —
`negentropic_dynamics.py`, `negentropic_engine.py`, `consciousness_metric.py`,
`alignment_thermodynamics.py`, `empirical_audit.py`, `lens_playground.py` —
holds the historical implementations and is fixed in place, not rewritten.
The dead `matplotlib` and `scipy` imports are gone.

### 14. The 17 lens functions were defined twice

Once in `bridge.py` and once in `lens_playground.py`, with the copies
already drifting apart.

**Fixed in:** `lenses.py` is the single definition. `LENS_COEFFICIENTS`
there makes the shared functional form explicit — 13 of 17 lenses are the
same expression with six constants changed — which is what
`lens_collapse_test.py` was written to test.

---

## Results this ledger produced

Running the falsifier on a corrected-core trace (`lens_collapse_test.py`,
250 steps, 200 trials, seed 42):

| Quantity | Value |
|---|---|
| Named-lens correlation floor | 0.8657 (Thermodynamic vs Māori) |
| Random-lens median floor | 0.9211 |
| Fraction of random lens sets above 0.88 | **0.955** |
| Percentile of the named floor within the random distribution | **0.005** |

The decision rule in that module says `frac_above_0.88 > 0.9` kills NEG-7.
Random coefficients not only reproduce the floor, they beat the named ones.

The last row is the more robust statistic and was added while testing.
The 0.88 threshold had been calibrated against the *original* core — the
one with clipped outputs and a constant `D` channel — so on a corrected
core the absolute correlation level moves with `n` and trace length, and
`frac_above_0.88` measures the trajectory as much as the lenses.
`compare()` puts both arms on the same trace instead. Across nine
combinations of `n` and trace length the named floor lands between the 0th
and 5th percentile of the random distribution every time. See
`NEG_CLAIMS.md` for the table and the disposition.

---

*Back to: [README.md](README.md)*
