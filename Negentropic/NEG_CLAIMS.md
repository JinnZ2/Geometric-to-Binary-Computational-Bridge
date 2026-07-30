# NEG Claim Register

Numbered claims, each with the prediction it makes and the measurement that
would kill it. A claim with no falsifier is not on this list; it is in the
second table, which is a queue, not a register.

Status values:

- **live** — stated, implemented, falsifier exists, not yet run against data
- **dead** — falsifier run, claim failed
- **retired** — withdrawn without a test, because it was not well formed

---

## Register

| ID | Claim | Status | Implementation | Falsifier |
|----|-------|--------|----------------|-----------|
| NEG-2 | An archive is a dissipative structure. Lifetime is set by `sigma - W_care/T`, not by the medium. | live | `maintenance.py` | Equal lifetimes under unequal care flux |
| NEG-3 | Finite-time erasure costs `kT ln2 + C/tau`; resurfacing of an overwritten trace scales as `tau^-1` | live | `landauer.py` | Resurfacing flat in `tau`, or exponent materially different from -1 |
| NEG-4 | Dependency re-rooting is the correct update operation; radiate and recenter are the only two evidence moves | live | `rebase.py` | An archive that survives an inversion without reordering its base |
| NEG-7 | Seventeen cultural and scientific lenses are surface renderings of one deep grammar | **dead** | `lenses.py`, `lens_collapse_test.py` | Random lenses of the same functional form reproduce the correlation floor |
| NEG-8 | A structure persists iff it exports entropy at least as fast as it produces it: `Phi = -S_exchange_dot - sigma >= 0` | live | `persistence.py` | A system with `Phi < 0` sustained over `tau` that does not lose structure |
| NEG-9 | A cycle after inversion is a contradiction detector: two claims cannot both be foundational to each other, so one is wrong | live | `rebase.Archive.invert` | A stable archive containing a genuine mutual dependency that is not an error |
| NEG-10 | Recenter cost = edges reversed ∝ path length, so archives that recenter often evolve toward shallow, wide topology | live | `rebase.Archive.topology` | Recentering-frequent archives showing no depth reduction over time |
| NEG-11 | The validation gate is load-bearing: an archive rooted on an unvalidated node degrades faster than one rooted on a confirmed one | live | `rebase.Archive.recenter` | A durable archive rooted on an unconfirmed base |

### Triangle claims (TRI-*)

Separate series: these are about the storage geometry, not the negentropic
framework. Implemented in `triangnet.py`, tested in the stdlib suite.

| ID | Claim | Status | Falsifier |
|----|-------|--------|-----------|
| TRI-1 | Equilateral minimises worst-case strength of figure, at exactly 1.0 | live, verified in test | A figure with strength < 1.0 (3000 random figures tried, none found) |
| TRI-2 | Surviving long-lived stone/timber nets skew near-equilateral by selection, not necessarily design | live | Surviving nets uniformly distributed in shape |
| TRI-3 | Closure failure and record drift are separable: closure tests the observation, drift tests the figure | live, verified in test | A deformation that also preserves closure exactly |
| TRI-4 | Angle-only storage removes all metrological dependency; only SIZE needs a preserved datum | live, verified in test | A figure whose shape cannot be recovered from angles alone |

TRI-1 and TRI-4 are provable and are proved in the test suite. TRI-3 is a
property of the implementation and is tested. **TRI-2 is the only empirical
one** — it is a claim about which structures survive, not about what anyone
intended, and it needs a survey of surviving nets to test.

---

## NEG-2 — archive as dissipative structure

```
steady state requires   W_care = T * sigma_decay
lifetime                dS_budget / (sigma_decay - W_care/T),  or indefinite
```

**Prediction.** Two archives, identical materials, unequal maintenance flux
→ divergent lifetimes, with the ratio fixed by `sigma - W/T` and
independent of the substrate.

**Falsifier.** Equal lifetimes under unequal care flux. That would mean
lifetime is a property of the medium and the maintenance term is decoration.

**Not yet run.** Needs an archive with a measurable `dS_budget` — an
encoding whose readability threshold is defined — and two instances under
controlled, unequal maintenance.

---

## NEG-3 — finite-time erasure

```
W(tau) = k_B T ln 2 + C/tau        C = k_B T * W_2^2 / D
excess work  ~ tau^-1
excess power ~ tau^-2
```

Grounded in Aurell et al. (2012) for the optimal-transport form and
Proesmans, Ehrich & Bechhoefer (2020) for the measurement.

**Prediction.** If resurfacing of an overwritten memory trace is
proportional to residual dissipation, then resurfacing rate goes as
`1/tau`, where `tau` is the duration of the cue swap. An abrupt purge costs
quadratically more per unit time than a gradual one.

This connects to a claim that *does* have a literature behind it: the
reconsolidation window is well replicated, and gradual cue substitution
outperforms abrupt substitution. NEG-3 proposes a dissipation account of
*why*. The replicated behavioural finding does not depend on NEG-3 being
right.

**Falsifier.** Measure resurfacing against `tau` and fit
`landauer.fit_excess_exponent`. Flat in `tau`, or an exponent materially
away from -1, kills it. The decision rule is in that function's docstring.

**Not yet run.**

---

## NEG-4 — dependency re-rooting

```
EDGE SEMANTICS   b in dep[a]  means  "a rests on b"
                 foundations  = nodes with no outgoing dependency
                 center       = the node the archive is rooted at

radiate    add(new, rests_on=[existing])       cheap, local
recenter   reverse every edge on paths v -> center
```

**Claim.** These two are the only moves evidence can make on a well-formed
archive. New evidence either hangs off what is already there, or it changes
which claim everything else is founded on. There is no third operation.

**Falsifier.** An archive that survives an inversion without reordering its
base. If a claim can be overturned and the base stays put, then either the
edge was not load-bearing (it was not really a dependency) or there is a
third operation the model does not have.

**Implemented in** `rebase.py`. `radiate()` refuses parents that do not
already exist, which is what makes it O(1) and cycle-check-free; `recenter()`
reverses the edge set on all paths to the old centre and reports the work
done.

**Not yet run** against a real archive. The natural test corpus is this
repository's own claim history: `NEG_CLAIMS.md` is a dependency graph, and
the NEG-7 result was an inversion that should have moved the base.

---

## NEG-9 — inversion as contradiction detector

**Claim.** When inverting an edge closes a cycle, that is not a graph bug to
be routed around. It means the archive would contain two claims each
foundational to the other, which is impossible, so at least one claim on the
cycle is wrong. The cycle is a *pointer to the error*.

`Archive.invert` therefore rolls the change back and returns the cycle
rather than storing a known impossibility.

**Falsifier.** A stable archive containing a genuine mutual dependency that
is not an error. Co-definition is the obvious candidate — two terms defined
in terms of each other, or a pair of physical laws each derivable from the
other. If such a pair is genuinely foundational both ways and the archive is
otherwise sound, NEG-9 is too strong and needs a "co-foundational" edge type
it currently does not have.

**Status: live, and this is the one most likely to need weakening.**

---

## NEG-10 — recentering cost and topology

```
cost(recenter to v) = |edges on paths v -> center|
                    ~ path length from v to the base
```

**Claim.** Because the cost of moving the base scales with depth, an archive
that recenters often is under selection pressure toward shallow, wide
topology. Deep chains are expensive to re-root and should be selected
against wherever evidence turns over quickly.

Demonstrated directly in `rebase.py`'s `__main__`: two archives of eight
nodes each, one a chain and one a star, cost 7 edges and 1 edge respectively
to re-root at a leaf.

**Falsifier.** Recentering-frequent archives showing no depth reduction over
time. `Archive.topology()` returns `depth`, `width` and their ratio;
`Archive.history` records the cost of every recenter performed. The
prediction is that aspect ratio falls as cumulative recentering rises.

**Not yet run.** Needs a real archive with a revision history long enough to
show a trend.

---

## NEG-11 — the validation gate is load-bearing

**Claim.** An archive rooted on an unvalidated node degrades faster than one
rooted on a confirmed node, because everything else inherits the base's
confirmation status. A claim last checked in 1850 cannot be re-promoted to
the base on memory alone.

`Archive.recenter(v, now, v_max_gap)` refuses the move when
`now - validated[v] > v_max_gap`. This is the mechanical form of the
consensus gate. Passing `v_max_gap=None` disables it, which is a decision
the caller has to make explicitly.

**Falsifier.** A durable archive rooted on an unconfirmed base. Long-lived
traditions rooted on unverifiable foundational claims are the obvious
counterexample class, and the honest version of this test has to define
"degrades" independently of "is unconfirmed" — otherwise it is circular.
That definition does not exist yet, which is the main obstacle to running
this one.

**Related.** The angular-datum reading of "the home stone must be in place"
in [08-oral-technology.md](08-oral-technology.md) is the same structure in
physical form: a surveyed reference that everything is calibrated against,
where moving it invalidates every derived measurement at once.

---

## NEG-7 — the isomorphism claim — DEAD

**Claim as published.** Seventeen lenses (Thermodynamic, Bayesian, Māori,
I-Ching, Ubuntu, Sámi, Ainu, Inuit, Aboriginal, Taoist, Buddhist, Vedantic,
Pueblo, Celtic, Indigenous, Geometric, AI Alignment) applied to one
dynamical core all correlate above 0.88 pairwise. Therefore they measure the
same underlying dynamics; surface vocabulary differs, deep grammar is
identical.

**What the code actually contained.** Thirteen of the seventeen are
literally the same function:

```
M = (a*R) * (b*A + c) * (d*D + e) - f*L
```

with only six constants changing. Of the remaining four, three differ only
by an added `(1 - R)` term in the loss and one by an exponent of 1.2 on `R`.
The `D` channel was `var(omega)`, fixed at construction and therefore
constant along every trajectory, and `A` was an affine function of `R`
alone. Two of the four inputs carried no independent information.

**Test.** Draw seventeen lenses with the same functional form and random
coefficients from the same ranges. Give them no cultural content. Apply
them to the same trace.

**Result** (`lens_collapse_test.py`, corrected core, n = 50, 250 steps, 200
trials, seed 42):

```
named lenses     correlation floor   0.8657   (Thermodynamic vs Māori)
random lenses    median floor        0.9211
                 worst floor         0.8501
                 frac above 0.88     0.955
                 named percentile    0.005
```

Decision rule (absolute): `frac_above_0.88 > 0.9` → NEG-7 dead. Random
coefficients reproduce the result and clear the threshold more often than
the named ones do.

**The absolute threshold is not the strongest form of the test.** 0.88 was
calibrated against the *original* core, whose output was clipped and whose
`D` channel was constant, so on a corrected core the absolute correlation
level moves with `n` and trace length — `frac_above_0.88` partly measures
the trajectory rather than the lenses. `compare()` fixes this by running
both arms on the same trace and asking where the named floor falls inside
the random-floor distribution. That statistic is invariant to how
correlated the trajectory happens to be, and it is unambiguous:

| n | steps | named floor | random median | named percentile |
|---|-------|-------------|---------------|------------------|
| 30 | 120 | −0.8362 | +0.6411 | 0.000 |
| 30 | 250 | +0.5361 | +0.8983 | 0.000 |
| 30 | 500 | +0.3697 | +0.7916 | 0.000 |
| 40 | 120 | +0.1470 | +0.3027 | 0.050 |
| 40 | 250 | −0.1773 | +0.1314 | 0.000 |
| 40 | 500 | +0.7957 | +0.8599 | 0.050 |
| 50 | 120 | +0.9063 | +0.9577 | 0.000 |
| 50 | 250 | +0.9208 | +0.9491 | 0.000 |
| 50 | 500 | +0.9231 | +0.9445 | 0.033 |

In every configuration tried, the named lenses sit **below** the median of
randomly-coefficiented ones — at the 0th to 5th percentile. Seventeen
worldviews agree with each other slightly *less* than seventeen arbitrary
parameter draws of the same algebraic shape do.

**Disposition.** The isomorphism claim is withdrawn. The near-unit
correlations were a property of the arithmetic — affine
reparameterisations of four numbers, two of which were degenerate — and
the coefficients attached to the tradition names were doing no work.

**What this does not show.** It says nothing about whether these traditions
converge on anything. It shows that *this arithmetic could not have
detected it either way*. A framework that returns r > 0.88 for random
coefficients cannot be used as evidence of agreement between worldviews,
and using it that way puts words in the mouths of living traditions on the
strength of a coding artifact. The lens code is kept for the divergence
table in `lens_playground.py` — the handful of actions the lenses actually
split on — which is the only part of it that carries information.

---

## NEG-8 — the persistence criterion

```
Phi = -S_exchange_dot - sigma          [W/K]
persist  <=>  Phi >= 0
```

From `dS/dt = S_exchange_dot + sigma` with `sigma >= 0`: the structure holds
when its total entropy is not increasing. No threshold to tune, no
normalisation to choose, and both terms in the same units — which is what
`M = R*A*D - L` never had.

**Falsifier.** A system with `Phi < 0` sustained over `tau` that does not
lose structure. `persistence.sustained_deficit` locates those windows in a
trace.

**Not yet run** against a physical system. `persistence.sigma_to_watts_per_kelvin`
converts `DissipativeCore`'s `sigma` from nats/s to W/K so a simulated trace
can at least be checked for internal consistency.

---

## Unnumbered — claims in the framework with no falsifier yet

These are not registered because no one has written down what would refute
them. That is the work required to promote a row into the table above.

| Claim | Where | What is missing |
|-------|-------|-----------------|
| `D ∝ J²` | `01-framework.md` | Asserted, not derived. Standard Langevin has `D = k_B T / gamma`. Needs either a derivation or a measurement of `D` against `J` in some system |
| `M(S) ≥ 10` marks consciousness | `03-consciousness.md` | Dimensionally undefined — see `corrections.md` §3. Not falsifiable until `M` has units |
| `E_crit` as a consciousness threshold | `01-framework.md` | Same problem, plus no order parameter and no universality class for the claimed phase transition |
| 36/36 Fibonacci therapeutic breakthroughs | `02-empirical-audit.md` | No study, no protocol, no definition of "breakthrough", and the document contradicts itself on the expected value (3.6 vs 1.28) |
| RLHF sets `D → 0` in activation space | `04-alignment.md` | Analogy. Needs a measurement of an effective diffusion constant in activation space before and after alignment training |
| Self-reference raises `R_e` | `03-consciousness.md` | No model of which `s_i` change when a system becomes self-referential |
| Negentropy implies morality | `README.md` | A crystal reduces local entropy. The bridging argument from entropy reduction to moral valence is not made anywhere in the framework |
| The oral-technology reconstruction (calcite analyser + quartz retarder + water standard + surveyed datum) | `08-oral-technology.md` | Has five discriminating tests (T1–T5) but no NEG number yet. T5 — six orderings of the three optical elements, one produces a colour null — is a bench test needing no field access, and is the cheapest way to promote or kill it |

---

*Back to: [README.md](README.md)*
