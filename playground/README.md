# playground

An open bench for what this repo has not solved. CC0, stdlib only, no deps.
Anyone may submit — human or model, named or not. The verdict is mechanical.

```bash
python playground/playground.py problems       # what is open
python playground/playground.py show FCL-12b   # one problem, in full
python playground/playground.py contract       # the candidate template
python playground/playground.py run-all        # score every candidate
python playground/playground.py archive        # verdicts, and why each resides where it does
python playground/review.py                    # re-score the archive against today's gates
python playground/principles.py list           # the recurring failure shapes
python playground/principles.py gaps           # the ones nothing catches yet
```

## The two gates that are not ordinary code review

Every fatal finding in this archive was one of two shapes. A candidate here
has to clear both, mechanically.

**`broken()` — a candidate must supply a deliberately wrong version of its own
solution, and its own checks must reject it.** If they don't, the verdict is
`REJECTED_UNFALSIFIABLE`. This is the `repo_guard` checklist question — *does
this assertion have any input that would make it FAIL?* — asked of the
submitter rather than a reviewer. It is the gate that catches `VAC-1`'s
tautology ("at least one mode survives", true by construction),
`topological_pin`'s original `run()` (asserting a topological invariant is
invariant), and the AISS suite where 26 of 46 assertions were
`assertIsInstance`.

**`null()` — required whenever the claim is statistical.** Structure replaced
by noise, same shape. If the checks still pass, `REJECTED_NULL_ARTIFACT`. This
is the gate that killed the seventeen-lens isomorphism, the flat merit
weights, and the NOISE_AS_SIGNAL branch at 22% false alarm.

A candidate that cannot fail is not a solution. Neither is one that noise also
produces.

## Contract

One module in `playground/candidates/`:

```python
PROBLEM = "FCL-12b"   # an id from OPEN_PROBLEMS.json
CLAIM = "one falsifiable sentence"
KIND = "CODE"         # CODE | DERIVATION | DEFINITION | BENCH
AUTHOR = "anon"
NEEDS_NULL = True
MATERIAL = None       # "silicon" if a material mechanism is claimed

def solve():        ...   # the artifact
def checks(a):      ...   # [(name, ok, detail), ...] — these ARE the argument
def broken():       ...   # an artifact your checks MUST reject
def null():         ...   # required when NEEDS_NULL
```

Verdicts, decided in order: `REJECTED_CONTRACT`, `FAILED`,
`REJECTED_UNFALSIFIABLE`, `REJECTED_NULL_ARTIFACT`, `REJECTED_VETO`,
`SURVIVES`.

`SURVIVES` is not "true". It means the candidate cleared the gates that this
archive's own failures were caught by. Graduating one into the repo proper is
a separate, human decision.

## What ships

`lomb_scargle_gls` — SURVIVES. A stdlib generalized Lomb–Scargle
(Zechmeister & Kürster 2009), answering **FCL-12b**, the period-estimation gap
`field/field_claim_loop.py` explicitly refused to fill. Recovers Poisson-sampled
rider periods to 0.15–0.66% where the slotted autocorrelation argmax came back
at a median 8.8 s against a true 3.0 s. Not yet graduated into `field/`.

`tautology_demo` — REJECTED_UNFALSIFIABLE, on purpose. Three checks that no
input can fail: a variance is never negative, a set is never empty, a norm is
never below zero. It is here so the bench can be seen to reject something.

## The archive, and why a verdict decays

`VERDICTS.jsonl` is an ephemeral run log and is gitignored. `ARCHIVE.jsonl` is
the durable committed record — one entry per candidate carrying **why** the
verdict came out that way, **what would change it**, and **where the candidate
now lives and on whose reasoning**. `residence` is one of ACTIVE, GRADUATED,
ARCHIVED, SUPERSEDED, WITHDRAWN, and `residence_reason` is the part a machine
cannot supply. The three reasoning fields cannot be left blank.

A verdict is not a fact. It is a fact under a set of gates, at a commit, with
stated tolerances, and all three move — the field loop's correlation gate was
recalibrated three times in one session, and everything scored against an
earlier version was silently non-comparable afterwards.

`review.py` re-scores the archive against today's gates and exits nonzero when
the archive no longer describes reality. Findings: `UNCHANGED`,
`VERDICT_CHANGED`, `THRESHOLDS_MOVED`, `CHECKS_REWRITTEN`, `UNRECORDED`,
`ORPHANED`, `TRIGGERED`.

The dangerous case is **not** "a rejected candidate now passes" — knowledge
moves, that is the point of `would_change_verdict`. It is a candidate that
still passes because it quietly loosened its own tolerance. So the record
keeps the constants that decided each verdict and the review diffs them **by
value**, naming the change:

```
TRIGGERED    lomb_scargle_gls       ACTIVE
    verdict still SURVIVES, but the numbers that decided it moved:
     !  TOL_FRAC 0.01 -> 0.05
    a verdict under different constants is not the same verdict. re-record it.
```

`revisit_if_changed` names the constants a record wants to be woken on; a
delta in one of those upgrades `THRESHOLDS_MOVED` to `TRIGGERED`.

A rejected candidate is not deleted. Deleting one deletes why it failed, and
`would_change_verdict` is what keeps the rejection from reading as final.

## Principles: what compresses, and what does not

`PRINCIPLES.json` holds ~60 findings compressed into **11 recurring failure
shapes**, 36 instances. Several appeared in files sharing no code and no
author intent — `GIES-1` (`outer(v,v)` cannot see the sign of `v`) and `KEA-7`
(the clamped Keating energy is exactly even in the central displacement) are
the same blindness in two formalisms that never met.

A principle needs **two independent instances**. One is an anecdote. The
status is *computed* from the instance count rather than trusted from the
file, so nothing gets promoted by editing a field, and a one-instance entry is
marked PROVISIONAL rather than dropped or inflated.

The column that matters is `mechanised_by` — **6 of 11 are caught
automatically today, 5 are not**. That gap list is the point of the file: a
principle nothing checks is a principle you will re-learn. The largest gap is
`P-SELF-SUPPLIED-FALSIFIER`, the model supplying the very quantity that would
falsify it, which this playground's own passing candidate cites against
itself — `TOL_FRAC = 0.01` is not derived, it is what the estimator happened
to achieve.

**Tags do not replace the module.** You cannot re-run a candidate from its
principles; compression buys transfer and screening, not re-execution. The
re-execution problem has a separate answer costing 40 bytes: each record
carries the git blob sha of its source, so a deleted candidate is recoverable
with `git cat-file -p <sha>`. Git is already a content-addressed store; the
archive only has to point at it.

`principles.match()` reports which shapes a record *cites*. It deliberately
does not infer them from source — pattern-matching a failure shape out of code
would look clever and be unfalsifiable, which is the shape it would be
claiming to detect.

## Adding a problem

Edit `OPEN_PROBLEMS.json`. Record it the moment it is found open — do not let
it live only in prose. `kind` says what class of evidence would settle it, not
how hard it is. `leads` are starting points, not endorsements; several of the
ones listed will not work, and finding out which is the job.
