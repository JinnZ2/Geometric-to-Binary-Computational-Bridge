# playground

An open bench for what this repo has not solved. CC0, stdlib only, no deps.
Anyone may submit — human or model, named or not. The verdict is mechanical.

```bash
python playground/playground.py problems       # what is open
python playground/playground.py show FCL-12b   # one problem, in full
python playground/playground.py contract       # the candidate template
python playground/playground.py run-all        # score every candidate
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

## Adding a problem

Edit `OPEN_PROBLEMS.json`. Record it the moment it is found open — do not let
it live only in prose. `kind` says what class of evidence would settle it, not
how hard it is. `leads` are starting points, not endorsements; several of the
ones listed will not work, and finding out which is the job.
