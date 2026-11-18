# equation_search: round 2 and the exact tier

**Status: PROPOSED. Generated data only.** Two additions beside the received
`equation_search.py`, which is kept unchanged under
[`../evidence/equation_search_as_received/`](../evidence/equation_search_as_received/MANIFEST.json)
and is imported, never edited. What is established: on the planted systems,
the results below, at seeds 0 to 9 where anything is random. What is **not**
established: anything about measured data, noisy chaotic data, or systems
outside the ten-term library.

Co-authored, CC0. Stdlib only, Python 3.10.

```sh
python -m experiments.experiment_bridge.eqsearch.exact --selftest
python tests/test_experiment_bridge_eqsearch.py
```

Full runs need a new output file: `python -m experiments.experiment_bridge.eqsearch.round2 --output NEW.json` (about 25 s) and `python -m experiments.experiment_bridge.eqsearch.exact --output NEW.json` (under a second). Snapshots: `runs/round2.json`, `runs/exact.json`.

## Declared before any run

Every threshold and band is in [`DECLARED.json`](DECLARED.json), committed
(`a419997`) before the specimen or the new code was run in this build. That
commit is what `DECLARED_PRE_RUN` refers to. One amendment was logged after
the first run and changes no declared value.

The specimen arrived as pasted text, not a file. It was cut from the session
transcript by program and was not retyped; there is no original file to
byte-compare with and no seed-0 record came with it.

## Round 2

```text
received specimen (unchanged) ---> greedy_bic      1/3   x: OVER_SELECTION (+yz)   z: OTHER (y2, 1, xy)
        |                          noise_floor     1/3   the same sets as greedy_bic
        +--- new branches -------> stlsq (thr 0.1) 3/3   {x,y} {x,y,xz} {z,xy}
```

- **F3, Lorenz.** STLSQ recovers all three planted term sets, so the
  any-branch claim passes. The specimen's greedy BIC fails 1 of 3 and that
  failure stays logged with its causes.
- **The noise floor did not help.** On noise-free RK4 data the Richardson
  error is truncation error, around 1e-3 to 6e-3 in variance. A spurious
  term that absorbs structured truncation residual still pays for itself
  against that floor, so the branch selects exactly what raw BIC selects.
  The z component is a forward-selection path problem (it starts with `y2`
  and cannot drop it), which no score fixes.
- **Nulls: 0 false discoveries in 40, for every family and branch, at all
  ten seeds, and all of that comes from the R² gate.** Without the gate the
  selections on pure noise, over 400 datasets, are:

```text
family / branch      selects something   false discoveries (with the R^2 >= 0.5 gate)
f2                   400 / 400           0      f2_fit always returns parameters
f3 greedy_bic         68 / 400           0
f3 noise_floor       400 / 400           0
f3 stlsq             400 / 400           0      an absolute threshold keeps noise-sized coefficients
f4                   398 / 400           0      the quadratic beats the linear guard on uniform noise
```

  The largest null R² is 0.06; the planted F2 fit at noise 1e-2 has R² 0.80,
  so the gate at 0.5 separates them here. The gate is a declared choice.
- **F4 sweep.** Noiseless row: SOLVER_CHECK, relative error 7e-12. Noisy
  rows recover r within 2% at both levels, all ten seeds (3.695 to 3.706 at
  noise 1e-2).
- **F1 identifiability.** The constant sequence has 8 exact recurrences
  (a + b = 1): NON_UNIQUE, verdict void, hit list kept.
- **Tolerance sources.** Round-2 claims: 5 DEFINITION, 6 DECLARED_PRE_RUN,
  3 UNSOURCED, 0 PHYSICS_BOUND. The three UNSOURCED are the specimen's 0.05
  (F2) and 2% (F4, two rows); a pass on them reads `pass (tol unsourced)`.
  The specimen's own six claims are re-read the same way in the snapshot.
- **Seeds 0 to 9.** Every stochastic claim has the same verdict at all ten
  seeds. The F3 recovery is deterministic and has no seed.

## Exact tier

```text
rational system + rational step ---> ENGAGED (a float anywhere: NOT_ENGAGED, logged, never converted)
        |
Fraction states, Euler dt 1/200 ---> denominator bits per step: 1, 7, 18, 39, 68, 114, 194, ... 3622 at step 12
        |
exact linear solve, rank 10 of 10 -> unique
        |
every step checked by exact equality -> PASS, or FAIL located (step, component); no BIC
```

Recovered step map, equal to the planted one coefficient for coefficient:

```text
x' = 19/20 x + 1/20 y
y' = 7/50 x + 199/200 y - 1/200 xz
z' = 74/75 z + 1/200 xy
read back as ODE coefficients: -10, 10 | 28, -1, -1 | -8/3, 1
```

| Run | Branch | Result |
|---|---|---|
| 12 steps | EXACT | 3 of 3, unique, 12 steps verified exactly |
| 40 steps, cap 65536 bits | EXACT | cap stops generation at step 19; the 18 exact steps give full rank |
| 40 steps, cap 256 bits | MODULAR | 4 primes, rank 10 each; same map; checked exactly on 6 steps and modulo each prime on 40 |
| 40 steps, cap 256 bits, no modular branch | VOID | rank 6 of 10 at the cap; no float fallback |
| float coefficients, or a float step under `--exact` | NOT_ENGAGED | refused with the reason |

Null: each of the 30 coefficients (zero ones included) moved by 1/1000 in
turn. The exact check fails all 30, each located at step 0 (the start
(1, 1, 1) makes every library term nonzero).

## Round 3

Declared in `DECLARED.json` under `round3` and committed (`ece54da`) before any round-3 code ran. Snapshot: `runs/round3.json`. Run: `python -m experiments.experiment_bridge.eqsearch.round3 --output NEW.json` (about 35 s).

**a. Time-shuffle guard.** A second guard that does not use R²: shuffle the time order, recompute the derivatives, refit the same structure, and pass only if the true order beats all 19 shuffles. False discoveries on 120 pure-noise datasets per family (seeds 0 to 2):

```text
family / branch      selects   R^2 gate only   shuffle guard only   both
f2                   120       0               8                    0
f3 greedy_bic         18       0               4                    0
f3 noise_floor       120       0               11                   0
f3 stlsq             120       0               10                   0
f4                   119       0               5                    0
```

The planted F2 (noise 1e-2), F3 (STLSQ) and F4 data all pass the shuffle guard at rank 1 of 20. Alone, the guard lets noise through at 4 to 9%, against the 5% its rule implies. The two selecting F3 branches sit highest, and that is consistent with a bias in how it is applied here: the structure is selected on the true order and only refitted on the shuffles, so the true order starts ahead. Re-running the selection on every shuffle would remove that; it was not done. With both guards, 0 of 600.

**b. `linear_comparison`.** The specimen's `f4_null_guard` is used here under that name. On round 2's 400 pure-noise series the quadratic beats the linear fit **398 times**, so winning that comparison is not evidence of structure. The specimen keeps its own names.

**c. STLSQ threshold sweep.**

```text
threshold            0.01  0.02  0.05  0.1   0.2   0.5   1.0
Lorenz               3/3   3/3   3/3   3/3   3/3   3/3   1/3  UNDER_SELECTION (y, z): the unit coefficients go
Lorenz + 0.05 x      3/3   3/3   2/3   2/3   2/3   2/3   1/3  UNDER_SELECTION (z): the planted term goes
```

The planted 0.05 term is estimated at 0.0499 and is dropped as soon as the threshold reaches 0.05. Recovery holds for thresholds below the smallest true coefficient and breaks at it; a threshold has to be chosen knowing that scale, which a search does not know in advance.

**d. Noisy Lorenz, noise 1e-3.** STLSQ at 0.1 still recovers 3 of 3. The exact tier: float states read NOT_ENGAGED; an exact Euler trajectory with rational noise added reads **FAIL**, located at step 10, the first transition after the ten it was solved on; the same trajectory with no noise reads PASS. The tier never passes the noisy data.

## Limits

- The exact tier recovers the step map of a known scheme from exact,
  noise-free states. Reading ODE coefficients back assumes explicit Euler.
- A check modulo a prime is necessary, not sufficient; the record says which
  steps were checked exactly and which only modulo primes.
- Denominators grew about 1.6 times per step, not the doubling the
  declaration expected, so the declared cap is never the binding limit in
  the declared runs; the 256-bit run was added to exercise the other
  branches (amendment in `DECLARED.json`).
- The F3 result is one trajectory with no observation noise. STLSQ's
  threshold of 0.1 sits below every planted coefficient (smallest 1); a
  system with smaller true coefficients would lose them.
- The R² gate, not the selection rules, is what abstains on noise.

Observer slots: human_interest null, ai_interest null.
