# loop_topology: six toys on what a cut can see of a loop, and a planted pipeline

CC0-1.0. Co-authored. Standard library only. Status: PROPOSED.

A loop that returns through a cut leaves no net trace on the cut. These
toys put numbers on that, for information, cost, entropy production and
heat, and a pipeline then tries to find a planted loop from a trajectory.

## Provenance of the numbers

The recorded numbers are REPORTED: they come from a prior session whose
code is lost. They were copied into `DECLARED.json` and committed before
any code here was run (commit a47b392). The toys were then rebuilt from
the work order's descriptions. Where the order did not fix a definition
or a parameter, the choice is in `DECLARED.json` under `readings`, made
before the run. Tolerance: 2e-3 absolute per number. A mismatch is
reported and nothing is tuned to remove it.

## Files

    DECLARED.json   recorded numbers, tolerance, readings, pipeline gates
    ctmc.py         shared arithmetic: stationary state, sigma, matrix
                    exponential, window KL, semi-Markov estimator
    cuts.py         T1  4-spin chain through cuts; merged 3-ring
    weld.py         T2  cut reads net, cost reads total
    collision.py    T3  two bits round a cycle, each unbiased alone
    te.py           T4  transfer entropy, information flow, Schnakenberg
    dwell.py        T5  dwell-time + entry/exit estimator (--selftest)
    nested.py       T6  figure-eight, state cuts and time cuts
    ledger.py       T6  bath heat against Markov heat through a cut
    run_all.py      every number against DECLARED.json
    pipeline.py     planted trajectory -> rates -> cycles -> sigma -> cuts
    samples/        pinned output of run_all.py and pipeline.py

    python experiments/loop_topology/run_all.py
    python experiments/loop_topology/pipeline.py
    python experiments/loop_topology/dwell.py --selftest

## Result of the rebuild

64 recorded numbers: 56 MATCH, 8 not. Full table in
`samples/run_all.sample.txt`.

    T3.obs_both_over_sigma   recorded 0.8      rebuilt 0.8092   recorded as approximate
    T4.TE.c0.9               recorded 0.3436   rebuilt 0.3409
    T5 uneven ring           recorded 0.1138   rebuilt 0.2885   rates not in the order; the declared guess is wrong
    T6.cut.hub               recorded 0.2646   rebuilt 0.0745   see below
    T6.time tau 0.01         recorded 0.74     rebuilt 0.7326
    T6.time tau 0.05/0.2/1   recorded 0.24/0.06/0.03   rebuilt 0.2357/0.0576/0.0259   inside the recorded rounding

T6.cut.hub: the declared reading is a fraction of total sigma. The same
estimator in sigma units gives 0.2645. The recorded 0.2646 is probably a
sigma value. Logged as a post-run note in `DECLARED.json`; the verdict
under the declared reading stays MISMATCH.

The T5 ring rates are not in the order. Declared before the run as
3.0 forward, 0.5 backward. With them the recorded 1.75x error of the
unconditional estimator is reproduced exactly.

## Result of the pipeline

One seeded trajectory (seed 20261124, time 50000, 435685 jumps).
All 12 rates recovered within 3.4 percent; both cycle sigmas inside the
10 percent gate; the detailed-balance null reads 0.0004 against a gate of
0.01. Under the cuts, a Markov reading of the merged trajectory flags a
loop only when the cut leaves that loop's cycle in the merged graph:

    collapse fast, hub   fast loop hidden, slow loop flagged
    collapse slow        slow loop hidden, fast loop flagged
    across               both flagged
    both                 neither flagged
    time cut tau = 5     not flagged (sigma 0.0018)

## Not established

- The pipeline reads a merged trajectory as Markov. The dwell estimator of
  T5 is exact arithmetic here and was not run on the simulated trajectory.
- One seed, one trajectory length. Seed-to-seed spread: NOT RECORDED.
- The mismatches above are not explained beyond what is written.
