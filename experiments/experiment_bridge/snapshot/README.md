# Snapshot classes (T4)

**Status: PROPOSED.** A classifier for snapshot claims and a resume rule per
class, built from EBR_016 to EBR_019 in [../CLAIM_TABLE.md](../CLAIM_TABLE.md).
Those findings rest on the received `snapshot_delta.py` and its seed-0 record:
two toy systems, one seed. What is established: the ten received claims sort
into the four classes and the rule returns the decisions below. What is **not**
established: that these four classes cover snapshots in general, or anything
about a real checkpoint.

Co-authored, CC0. Stdlib only, Python 3.10. Reads the specimen record; edits
nothing under `evidence/`.

```sh
python -m experiments.experiment_bridge.snapshot.snapshot_class --selftest
python tests/test_experiment_bridge_snapshot.py
```

```text
snapshot = content (FULL_STATE | SUMMARY) + fidelity (EXACT | LOSSY) + growth (measured, LOSSY only)
        |
class                 when                               resume
CONTEXT_FREE_EXACT    full state, exact                   always
STABLE_LOSSY          full state, lossy, growth <= 1      only with a stated bound (a refresh threshold counts)
CHAOTIC_REFRESH       full state, lossy, growth > 1       only with refresh; a bound alone is REFUSED
SUMMARY_ONLY          a many-to-one summary               VOID
        |
decision: ALLOWED | REFUSED | VOID, with the reason and the condition it rests on
```

The ten received claims, in [`classes_seed0.json`](classes_seed0.json):

```text
claim                            class                bare      + bound   + refresh
fib::word_resume_exact           CONTEXT_FREE_EXACT   ALLOWED   ALLOWED   ALLOWED     EBR_016
fib::count_resume_exact          CONTEXT_FREE_EXACT   ALLOWED   ALLOWED   ALLOWED     EBR_016
float::bitwise_resume            CONTEXT_FREE_EXACT   ALLOWED   ALLOWED   ALLOWED     EBR_016
sink::lossy_snapshot_drift       STABLE_LOSSY         REFUSED   ALLOWED   ALLOWED     EBR_017
lorenz::lossy_snapshot_drift     CHAOTIC_REFRESH      REFUSED   REFUSED   ALLOWED     EBR_018
sink::adaptive_refresh_bound     STABLE_LOSSY         REFUSED   ALLOWED   ALLOWED
lorenz::adaptive_refresh_bound   CHAOTIC_REFRESH      REFUSED   REFUSED   ALLOWED     EBR_018
fib::word_from_counts            SUMMARY_ONLY         VOID      VOID      VOID        EBR_019
lorenz::random_access_speedup    CONTEXT_FREE_EXACT   ALLOWED   ALLOWED   ALLOWED
fib::random_access_work_ratio    CONTEXT_FREE_EXACT   ALLOWED   ALLOWED   ALLOWED
```

## Limits

- **Content and fidelity per claim are a reading**, made by hand from each
  claim's own measurement text and listed in `READ`. Growth is never typed in:
  it is looked up in the record (0.0498 for the sink, 16980 for Lorenz).
- **`growth > 1` means the error grew** over the one horizon measured. The class
  is named CHAOTIC_REFRESH as ordered, but the rule tests growth, not chaos: a
  system that is unstable without being chaotic lands in the same class.
- **The same counts are two snapshots.** Resuming the count chain from the
  counts is CONTEXT_FREE_EXACT, because the counts are that chain's full state;
  resuming the word from them is SUMMARY_ONLY. The class belongs to the pair
  (snapshot, what is resumed), which the `content` field carries.
- **The rule decides and runs nothing.** It does not check that a stated bound
  is true or that a refresh is ever performed.
- A lossy snapshot with no measured growth has no class and reads VOID; growth
  is never assumed.

Observer slots: human_interest null, ai_interest null.
