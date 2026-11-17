# Planted-semantics simulation

**Status: PROPOSED. Synthetic only.** A generator plants a truth, the v1.1
kernel encodes it, and a majority rule assigns code paths to predicates on a
train split. What is established: on this declared generator, at one seed,
the assignment beats its permuted-label null at low noise and stops beating
it as noise rises, and a planted fault reads as confused. What is **not**
established: anything about a neural model, an NCM checkpoint, or Lojban.
The gap this targets, "Semantic assignment" in
[RESEARCH_GAPS.md](../RESEARCH_GAPS.md), asks for an identified checkpoint and
stays NOT_STUDIED.

Co-authored, CC0. Stdlib only, Python 3.10. Separate from `v1/`, `v1_1/`,
`raw/` and `evidence/`: it reads the reference and imports the v1.1 kernel,
and writes only into the output directory it is given.

```sh
python -m experiments.experiment_bridge.sim.planted --selftest
python tests/test_experiment_bridge_sim.py
```

A fresh run needs a new or empty directory (about one minute; `--small` about
ten seconds): `python -m experiments.experiment_bridge.sim.planted --seed 0
--output-dir NEW_DIR`. The declared generator, rule, baselines and limits are
in the docstring of [planted.py](planted.py).

## Shape

```text
reference rows (read only, sha256 checked)
   8 predicates with OBSERVED structure + "efficient" (VOID in the reference)
        |
generator  embedding = predicate signature (amp 4) + slot x1 (1.5) + slot x2 (0.75) + noise(sigma)
        |          planted fault: mleca is generated with zmadu's signature
        v
v1.1 kernel   4 levels x 16 codes; codebooks by k-means on train; thresholds by
              v1.1 gated calibration at 2%, train only
        |
assign (train only)   key = first code of the path (declared); majority label
        |
held-out, one state each:  REJECTED | UNMAPPED | LEXICAL_VOID | ACCEPTED
        |
against:  permuted labels x100 | majority label | random codebook
```

## Committed run: seed 0, 600 train / 300 held-out

Files in `runs/seed0/`: `truth_table.json` (sha256 in `results.json`),
`results.json`, `states.json` (one state per held-out sample per sigma),
`summary.txt`. All numbers below are OBSERVED in that run and are from one
seed.

```text
with the planted fault
sigma   strict  covered coverage  null_max  majority  random_cb  beats  ACC  REJ  UNM  VOID
0.1     0.890   0.899   0.990    0.353     0.097     0.643     yes   268    3    0   29
0.25    0.870   0.897   0.970    0.403     0.097     0.530     yes   262    9    0   29
0.5     0.887   0.899   0.987    0.410     0.097     0.517     yes   268    4    0   28
1.0     0.777   0.812   0.957    0.353     0.097     0.443     yes   244   13    0   43
2.0     0.460   0.483   0.953    0.243     0.097     0.233     yes   248   14    0   38
4.0     0.183   0.193   0.950    0.193     0.097     0.140     NO    215   15    0   70
8.0     0.143   0.152   0.940    0.170     0.097     0.097     NO    254   18    0   28

control, no fault:  strict 0.990  0.987  0.980  0.847  0.463  0.213  0.107
                    beats  yes    yes    yes    yes    yes    yes    NO
```

`strict` counts REJECTED and UNMAPPED as wrong; `covered` leaves them out.
`null_max` is the largest of 100 permuted-label accuracies (their mean is
about 0.11).

- **Falsifier.** At the lowest noise the assignment is above every permuted
  run (0.890 against 0.353), so the verdict is
  `NOT_FALSIFIED_ON_THIS_GENERATOR`. The verdict `METHOD_FAILS` can fire: an
  assigner fed shuffled train labels gets it (selftest, and a test).
- **Where it stops.** With the fault, sigma 4.0 is the first level not above
  the null (0.183 against 0.193); the control still clears it there (0.213)
  and fails at 8.0. The boundary sits between 2 and 8 and one seed does not
  place it more finely.
- **Planted fault.** At sigma 0.1 every held-out `mleca` is read as `zmadu`:
  recall 1.0 for one and 0.0 for the other. Recall alone would show one
  clean mapping and one missing predicate. The key purity is what shows the
  fault: the pair `[mleca, zmadu]` is the only confused pair, and the control
  has none. The pair stops being flagged at sigma 2.0 and above, although it
  is still planted: under that much noise the keys are mixed among many
  labels and the pair no longer stands out.
- **Levels.** At sigma 0.1, mutual information in bits (largest shuffled
  value in brackets):

```text
level   predicate      slot x1        slot x2
1       2.94 (0.44)    0.84 (0.12)    0.15 (0.13)
2       1.10 (0.35)    0.81 (0.12)    1.18 (0.12)
3       0.67 (0.41)    0.30 (0.14)    0.43 (0.12)
4       0.50 (0.45)    0.10 (0.13)    0.10 (0.12)
```

  Level 1 holds the predicate (the ceiling is 3 bits: nine classes, two of
  them identical). The slots appear from level 2, but not cleanly: level 1
  also carries slot x1, and level 2 still carries over a bit of predicate.
  The levels do not separate predicate from slots one to one. At sigma 4 and
  above no slot is above its shuffles at any level.
- **Deeper keys.** Using more of the path does not help here: at sigma 0.1
  strict accuracy is 0.890 / 0.883 / 0.693 / 0.220 for depth 1 to 4, as
  UNMAPPED grows 0 / 1 / 64 / 218 of 300.
- **Random codebook.** Untrained codes reach 0.643 at sigma 0.1. A partition
  of any kind carries much of this planted signal, so it is a comparison,
  not a null, and the trained codebook's margin over it is the smaller part
  of the result.

## Limits

- The generator and the test were written by the same hands. Success shows
  the method can recover a structure of this declared kind when it is there.
- The level reading follows from the chosen amplitudes (predicate > x1 > x2);
  other amplitudes would give another picture.
- One seed. The permuted null is wide because depth 1 has only 16 keys.
- `CONFUSED_SHARE` 0.25, the 2% rejection fraction and depth 1 were declared
  before the run and were not tuned afterwards; they are choices, not
  results.
- v1.1 has no codebook trainer, so k-means here is this folder's own; the
  kernel's `walk`, `calibrate_thresholds` and `make_level` are used
  unchanged, and `validate_trace` re-checks the first 10 traces of each
  encode, not all of them.

Observer slots: human_interest null, ai_interest null.
