# Adversarial core findings — additive v1.1 correction

**Note 2026-11-17:** This is an additive software audit under [READ_ME_THIS_WAY.md](../../../READ_ME_THIS_WAY.md). Legacy `v1/core.py` is preserved unchanged beside candidate `v1_1/core.py`; earlier records and incoming specimens are untouched. All constructors are **ILLUSTRATIVE software fixtures**, not measured neural, semantic, physical, security, or statistical evidence. The report does not claim universal exact arithmetic or production readiness.

## Replay and real checks

Run from the repository root, using a fresh output path so the recorded snapshot is not overwritten:

```sh
python tests/test_experiment_bridge_adversarial_core.py
python tests/test_experiment_bridge_core.py
python experiments/experiment_bridge/adversarial/core_probe.py --output /tmp/core-replay-new.json
ruff check experiments/experiment_bridge/v1_1/core.py experiments/experiment_bridge/adversarial/core_probe.py tests/test_experiment_bridge_adversarial_core.py
```

The recorded [core_results.json](core_results.json) has **39 fixtures, 78 isolated workers, and 39/39 expected old/new outcome pairs reproduced** on Python 3.12.3. Every replay worker has a **2-second subprocess hard timeout**; the parent kills and waits for timed-out children. Deliberately nonterminating probes are cooperative, slowly yielding iterators with low memory use before termination. They were not run directly in the audit process. TIMEOUT means this worker did not finish within that bound, not that arbitrary legacy inputs were proved nonterminating.

The added suite passed **31 tests in 11.219 seconds**, including **512 finite deterministic dyadic cases** using standard-library `random.Random(20261117)`. Each generated case compares legacy/candidate walk fields (apart from version), both validators, and a gated calibration result. This is a software regression corpus, not a scientific data sweep, distribution estimate, held-out study, or rate–distortion benchmark. The unchanged legacy numerical suite passed **31 tests in 0.015 seconds**. Root-configured Ruff passed on the three owned Python files. No repository-wide test/lint, Git/CI configuration, HTTP target, or network/security target is claimed by this subtask.

Replay source SHA-256 identifiers (identity only, not authentication):

- Legacy `v1/core.py`: `2381c6ea03ea6dc0b3fbad0255ff870dc1fa1b2a3bb6444e38b063bb68737b8c`.
- Candidate `v1_1/core.py`: `921a6aa8e1bad20e70a4d9cdd33b22d948c4bb149be788515b1e3b64f4c1f8c5`.

## What actually broke, and why the correction is narrow

### Nonzero distances became zero

`walk([1e-200], [make_level([[0]], 0)])` accepts in v1 with recorded squared distance zero and nonzero residual. More importantly, the separate fixture `target=[1,0], code=[1,1e-200], threshold=0` starts with a representable target squared norm of one, yet the nonzero code distance still squares to zero and is accepted. The v1 validator also accepts both generated traces. This is binary64 underflow **plus a fail-open gate defect**: a zero threshold can admit a genuinely unequal binary64 vector.

v1.1 retains the same squared-distance calculation and inclusive `<=` gate, but raises `ValueError` whenever any nonzero component product `x*x` is zero. It does **not** rescale the metric, switch to unsquared distance, add an epsilon to the threshold, or pretend to recover the missing squared value. The same check applies to target/residual norms and calibration. It is deliberately conservative: `[1,1e-200]` has a norm rounded to one in v1, but v1.1 rejects its underflowing component even though the total is nonzero. A nonzero representable subnormal square, e.g. `1e-160**2`, remains accepted for computation and correctly fails a zero threshold.

### Integer inputs silently lost identity

v1 converts `2**53+1` to `9007199254740992.0` and accepts a code of `2**53` at threshold zero. `2**1000+1` also converts to a finite float but loses its low bit. This is not a failure of Python's documented float conversion; it is a silent-loss hazard in an API described as checked input processing. Its underlying source is binary64 representability, not bad empirical data.

v1.1 rejects a `numbers.Integral` input unless the finite converted float satisfies `int(result) == value`. This covers vectors, codebooks, thresholds, calibration samples/codebooks, and checked scalar trace fields. Exactly representable large integers such as `2**53+2` and `2**1000` remain allowed for conversion; later squared arithmetic can still overflow. Existing overflow rejection for `10**400` remains unchanged. **This is not an exact-conversion promise for every `numbers.Real`:** `Fraction(1,10)` still rounds to `0.1`, and a lossy integer already converted by its caller to a float is indistinguishable from an intended float.

### Catastrophic cancellation escaped the producer contract

For target `[1]`, accepted codes `[1e16]` then `[-1e16]`, and thresholds `1e32`, v1 returns final reconstruction `[0]` and residual `[0]`. Its own validator reports `step 2: additive identity mismatch`. The lost unit arises from inherent binary64 cancellation; **returning a trace outside the implementation's own documented tolerance is the producer/validator contract bug**.

v1.1 checks the additive identity after each transition and raises `ValueError` if it is outside the same existing scaled tolerance. It does not recover exact arithmetic or change the residual recurrence. The analogous target `[1e-13]` still ends with zero reconstruction/residual and validates because its discrepancy is within the declared absolute floor. This explicitly limits the claim: candidate traces are tolerance-consistent, not exact decompositions of all real inputs.

### Malformed input diagnostics and bounded ingestion

For JSON-native malformed traces tested here, v1 already returns diagnostics. Two ordinary Python iterator fixtures, however, raise `RuntimeError` out of `validate_trace` rather than returning its advertised diagnostic list. Also, v1 consumes `steps` before checking that it is a list/tuple; a generator that should be rejected can be consumed first, including until timeout.

v1.1 checks the `steps` list/tuple shape before consuming it. Ordered inputs are collected through bounded `islice` with at most `limit+1` yielded items. Type/value/overflow/runtime errors during ordinary iteration are normalized to `ValueError`; the validator catches ordinary runtime/attribute errors at both step and trace boundaries and returns diagnostics. This is **not** a sandbox or arbitrary-code-execution defense for Python objects.

## Exact constants and unchanged APIs

Candidate version is `VERSION = "experiment-bridge/v1.1"`.

| Constant | Value | Application |
|---|---:|---|
| `MAX_ITERABLE_ITEMS` | 4096 | Default private ordered-ingestion bound |
| `MAX_DIMENSION` | 4096 | Target, code, sample, and recorded vectors |
| `MAX_CODES` | 4096 | Rows per codebook |
| `MAX_LEVELS` | 64 | Walk levels, calibration codebooks, trace steps |
| `MAX_SAMPLES` | 4096 | Calibration sample rows |
| `TRACE_REL_TOL` | `1e-12` | Arithmetic comparisons and scaled additive check |
| `TRACE_ABS_TOL` | `1e-12` | `math.isclose` arithmetic absolute tolerance |

Public signatures are unchanged: `Level(codebook, threshold_squared, label="")`, `make_level(codebook, threshold_squared, label="")`, `walk(target, levels)`, `validate_trace(trace, levels=None) -> list[str]`, and `calibrate_thresholds(samples, codebooks, rejection_fraction, gated=True)`. `Level` remains frozen and defensively copied. Ordered ties, hashes, inclusive acceptance, rejection with null index/zero contribution, signed error reduction, quantile calibration, and explicit gated/ungated behavior remain unchanged for supported cases.

New rejection messages include:

- `integer cannot be represented exactly as binary64`.
- `squared error underflow: nonzero component squared to zero`.
- `additive identity outside binary64 trace tolerance`.
- `{name} exceeds limit ({limit} items)` for `vector`, `codebook`, `levels`, `steps`, `samples`, or `codebooks`.
- `cannot read ordered {name}: {original error}` for the ordinary iteration errors caught during ingestion.

These are `ValueError` from constructors/walk/calibration. In `validate_trace`, such failures appear inside `malformed step: ...` or `malformed trace or levels: ...` diagnostics; a wrong step-container type produces `steps must be a list or tuple` in a diagnostic. No new exact-integrity API is introduced.

## Per-case expected/observed evidence and falsifiers

Each old and new column below gives **expected / actually observed**. All expected outcomes were specified in the replay constructor; the JSON preserves real returned values or exception messages, not invented outcomes. `D0` means returned diagnostic list `[]`; `D+` means returned nonempty diagnostics. `SELF_VALID`/`SELF_INVALID` are producer trace outcomes followed by actual codebook-backed validation. Each row's falsifier is a bounded check that would refute that row, not an unbounded universal test.

| Replay case | v1 expected / observed | v1.1 expected / observed | Classification and scope | Specific falsifier |
|---|---|---|---|---|
| `target_square_underflow` | ACCEPTED / ACCEPTED | ValueError / ValueError | Fail-open underflow bug, target `[1e-200]`, code zero, threshold zero | Old distance is nonzero or new returns a trace |
| `distance_square_underflow` | ACCEPTED / ACCEPTED | ValueError / ValueError | Fail-open underflow bug, target `[1,0]`, code `[1,1e-200]` | Old zero-threshold gate rejects or new fails to report underflow |
| `component_square_underflow` | ACCEPTED / ACCEPTED | ValueError / ValueError | Conservative new policy; an underflowing component of a nonzero total | Old norm differs from one or candidate permits the component |
| `representable_subnormal_square` | REJECTED / REJECTED | REJECTED / REJECTED | Expected gate rejection, representable nonzero subnormal distance | Either zero-threshold gate accepts or records distance zero |
| `decimal_gate_roundoff` | REJECTED / REJECTED | REJECTED / REJECTED | Inherent binary64 `0.1*0.1 > 0.01`, metric unchanged | Candidate accepts or changes recorded squared value |
| `lossy_integer_target` | ACCEPTED / ACCEPTED | ValueError / ValueError | Silent target conversion loss, `2**53+1` | Old preserves integer identity or candidate accepts that integer |
| `lossy_huge_finite_integer_code` | RETURNED / RETURNED | ValueError / ValueError | Silent finite code conversion loss, `2**1000+1` | Old converted integer equals input or new accepts it |
| `exact_huge_integer_code` | RETURNED / RETURNED | RETURNED / RETURNED | Expected exact conversion, `2**1000`; not square support | New rejects conversion or converted integer differs |
| `integer_conversion_overflow` | ValueError / ValueError | ValueError / ValueError | Expected input rejection, `10**400` | Either constructor accepts finite conversion |
| `lossy_integer_threshold` | RETURNED / RETURNED | ValueError / ValueError | Silent threshold input loss, `2**53+1` | Old threshold equals original integer or new accepts it |
| `lossy_integer_calibration` | RETURNED / RETURNED | ValueError / ValueError | Silent calibration sample loss; old threshold `(0.0,)` | Old threshold is nonzero or new accepts lossy sample |
| `rounded_fraction_input` | ACCEPTED / ACCEPTED | ACCEPTED / ACCEPTED | Noninteger Real rounding explicitly retained | Either identical converted code/target fails zero-threshold acceptance |
| `cancellation_outside_tolerance` | SELF_INVALID / SELF_INVALID | ValueError / ValueError | Producer contract bug triggered by inherent cancellation; target one | Old final states are not both zero, audit misses mismatch, or new returns |
| `cancellation_inside_tolerance` | SELF_VALID / SELF_VALID | SELF_VALID / SELF_VALID | Inexact identity intentionally allowed; target `1e-13` | Either validator rejects or candidate recovers claimed exact identity |
| `tiny_final_mutation` | D0 / D0 | D0 / D0 | Final reconstruction `+5e-13`, documented tolerance, not bug | Codebook-backed validator rejects this particular mutation |
| `large_final_mutation` | D+ / D+ | D+ / D+ | Final reconstruction `+5e-11`, expected rejection | Either validator returns empty diagnostics |
| `tiny_step_state_mutation` | D0 / D0 | D0 / D0 | Recorded reconstruction-after `+5e-13`, documented tolerance | Codebook-backed validator rejects this mutation |
| `tiny_distance_without_levels` | D0 / D0 | D0 / D0 | Recorded distance `+5e-13`, tolerance without codebooks | Either no-level validator rejects this mutation |
| `tiny_distance_with_levels` | D+ / D+ | D+ / D+ | Actual nearest distance checked exactly with codebooks | Either codebook-backed validator misses mutation |
| `missing_step_field` | D+ / D+ | D+ / D+ | Expected malformed trace rejection, missing contribution | Either validator returns empty diagnostics or raises |
| `nested_malformed_vector` | D+ / D+ | D+ / D+ | Expected structured-shape rejection | Either validator accepts nested recorded vector or raises |
| `nonfinite_trace_field` | D+ / D+ | D+ / D+ | Expected nonfinite field rejection | Either validator accepts NaN recorded error or raises |
| `malformed_target_iterator` | RuntimeError / RuntimeError | D+ / D+ | Ordinary failed Python iterator, diagnostics contract correction | Legacy does not raise or candidate leaks runtime error |
| `malformed_step_iterator` | RuntimeError / RuntimeError | D+ / D+ | Ordinary failed contribution iterator, per-step correction | Legacy does not raise or candidate leaks runtime error |
| `finite_generator_steps` | D+ / D+ | D+ / D+ | Expected wrong-container rejection; old consumes 1, new consumes 0 | Candidate consumes a yielded step before type rejection |
| `infinite_generator_steps` | TIMEOUT / TIMEOUT | D+ / D+ | Consumption-before-shape-check gap; isolated cooperative iterator | Old finishes within 2 seconds or new consumes/hangs |
| `infinite_target` | TIMEOUT / TIMEOUT | ValueError / ValueError | Missing old item bound; isolated cooperative iterator | Candidate does not reject after 4097 yields within timeout |
| `infinite_codes` | TIMEOUT / TIMEOUT | ValueError / ValueError | Missing old code-row bound; isolated cooperative iterator | Candidate does not reject after 4097 yields within timeout |
| `infinite_levels` | TIMEOUT / TIMEOUT | ValueError / ValueError | Missing old level bound; isolated cooperative iterator | Candidate does not reject after 65 yields within timeout |
| `vector_at_limit` | RETURNED / RETURNED | RETURNED / RETURNED | 4096-dimensional zero vector remains supported | Candidate rejects dimension 4096 |
| `vector_over_limit` | RETURNED / RETURNED | ValueError / ValueError | New policy, not an old numerical bug; dimension 4097 | Candidate permits dimension 4097 |
| `codes_at_limit` | RETURNED / RETURNED | RETURNED / RETURNED | 4096 zero codes supported, first tie selected | Candidate rejects 4096 rows or selects a later tied code |
| `codes_over_limit` | RETURNED / RETURNED | ValueError / ValueError | New policy, not an old numerical bug; 4097 codes | Candidate permits 4097 rows |
| `levels_at_limit` | RETURNED / RETURNED | RETURNED / RETURNED | 64 zero-code levels supported | Candidate rejects or returns other than 64 steps |
| `levels_over_limit` | RETURNED / RETURNED | ValueError / ValueError | New policy, not an old numerical bug; 65 levels | Candidate permits 65 levels |
| `samples_at_limit` | RETURNED / RETURNED | RETURNED / RETURNED | 4096 zero samples, calibration threshold zero | Candidate rejects or returns nonzero threshold |
| `samples_over_limit` | RETURNED / RETURNED | ValueError / ValueError | New sample-row policy; 4097 samples | Candidate permits 4097 samples |
| `calibration_books_over_limit` | RETURNED / RETURNED | ValueError / ValueError | New level policy; 65 calibration books | Candidate permits 65 books |
| `trace_steps_over_limit` | D0 / D0 | D+ / D+ | New trace-size policy; 65 otherwise consistent zero steps | Candidate returns empty diagnostics |

The added tests additionally delete every required top-level and step field, exercise ordinary iterator failure in supplied levels, check bounded finite consumption at exactly `limit+1`, and confirm that validation does not call `walk` or mutate its trace. These additional subchecks are not silently added to the replay's 39-fixture count.

## Tolerance, arithmetic, and resource risks deliberately held open

**Tolerance is not tamper evidence.** Arithmetic fields still use `math.isclose(rel_tol=1e-12, abs_tol=1e-12)`. Additive identity still uses `abs(t-(c+r)) <= 1e-12 * max(1,abs(t),abs(c),abs(r))`. A large intermediate reconstruction/residual therefore permits a larger absolute discrepancy than a small final state. The cancellation guard only rejects when that existing tolerance is exceeded. Tiny final/state mutations pass even with supplied codebooks. Actual codebook thresholds, nearest distance, selected contribution and hash are checked exactly when levels are supplied; a small distance mutation is thus rejected with levels while passing without them. Without levels, nearest choice and codebook identity remain uncertified. Hashes are not authentication.

**Binary64 remains binary64.** Subnormal nonzero squares may round substantially; ordinary multiplication, summation, subtraction, comparisons and inclusive threshold decisions still round. Individual products are rounded before `math.fsum`. Near-ties and near-threshold differences can still be indistinguishable. No scaled-norm or universal exact arithmetic claim is made. The underflow policy can reject a whole computation because of an unused code or a small component, consistent with existing eager validation of all candidate distances and overflow rejection. No alternative metric is introduced. Exact rational/decimal support, exact gate ordering and recovery of preconverted integers are out of scope.

**Item bounds are not a hard memory/CPU/service budget.** A codebook can still have 4096 rows of 4096 coordinates, and 64 levels can combine large books; calibration can multiply sample count, code count, dimension and levels. Revalidation and hashing copy/traverse data. Maximal combinations were not allocated or benchmarked. There is no aggregate scalar budget, streaming calibration, complexity quota, wall-time guarantee inside the public API, or protection against an already allocated oversized caller object. Labels and diagnostic text are not byte-limited. The extra `limit+1` item is intentionally consumed to detect overflow; a side-effecting iterator observes that consumption. One-shot ordered inputs are consumed once, not replayed. Iterable limits were tested at ordinary single-axis boundaries, not every Cartesian combination of maxima.

**Python object behavior is not contained.** User-defined `__iter__`, `__next__`, numeric conversions, equality, stringification, or dict/list subclasses can block, allocate, execute code, raise exceptions outside the ordinary caught set, or otherwise have side effects. The public core does not time-limit those methods and does not catch `BaseException`. A generator blocked before its next yield can still hang the caller regardless of item bounds. The subprocess timeout protects the finite audit harness, not the in-process API. This report makes no arbitrary-code-execution defense, hostile-object safety, denial-of-service prevention, or network-security claim.

**Promotion remains out of scope.** These software findings do not validate semantic assignments, NCM calibration, physical energetic identities, production reliability, scientific rejection rates, or upstream source assertions. Legacy behavior remains readable and reproducible beside these bounded candidate corrections.
