# Adversarial audit — 2026-11-17

**The pass found real breakages and produced separately tested candidate fixes. It did not establish a secure, authenticated, exact-arithmetic or semantically validated bridge.** The original v1 remains unchanged at baseline commit `19c9a805e6acd99144451e1aa4b78a5973a39ce7`; candidate code lives in [v1_1](../v1_1/README.md). Read with the [plan and trust model](PLAN.md) and [repository preservation rules](../../../READ_ME_THIS_WAY.md).

## What broke

**A nonzero numerical distance became zero.** With target `[1,0]`, code `[1,1e-200]` and a zero squared-distance threshold, v1 accepts: the nonzero difference squares to zero in binary64. Its validator accepts the resulting trace. Candidate v1.1 fails closed when a nonzero component square underflows to zero. It retains the same metric rather than silently rescaling it or changing the threshold. The guard is conservative and may reject a whole vector computation even when other components are representable.

**Integer identity was silently lost.** The old numerical API turns `2**53+1` into `2**53` and can accept a different target at threshold zero. The candidate rejects lossy Integral-to-binary64 conversion. Exactly representable large integers are still allowed; later arithmetic can still overflow. Preconverted floats and noninteger Real rounding remain representation limits.

**A producer returned a trace that failed its own validator.** A target of one with accepted contributions `1e16` and `-1e16` loses the target through cancellation. Candidate transition checks reject results outside the existing additive tolerance. They do not recover exact arithmetic. A target discrepancy within the `1e-12` absolute tolerance can still pass; tiny mutations are not integrity-certified by numerical tolerances.

**Malformed or deep content escaped clean validation.** Ordinary failed numerical iterators can leak RuntimeError from the old diagnostic API. Cyclic/deep semantic extensions and an otherwise valid, hashed **2,407-byte** deeply nested JSON payload can leak RecursionError. Candidate input handling normalizes the demonstrated errors and declares finite depth, item, text and node bounds before deep-copying, hashing or assembling the affected JSON.

**Reference identities were not consistently validated.** Old `find_rows` accepts duplicate row ids, conflicting source positions and impossible duplicate occurrences, while old annotation already rejects duplicate ids. Candidate shared validation rejects the demonstrated contradictions without requiring contiguous or sorted subsets. A plausible lone forged source position still needs an independently trusted reference to disprove it; hashes cannot establish origin.

**Output protection was incomplete.** Old runtime guards allow new output within the retained v1 run tree. Disposable path probes also show an injected leaf symlink overwriting a temporary victim and a mocked directory swap redirecting writes into a mock held directory. Candidate held-path exclusions, pre-write rechecks and exclusive complete-file publication reject these specific interleavings. No actual received file or saved v1 artifact was attacked. This is not OS-level protection from every concurrent filesystem race.

The detailed [numerical findings](core_findings.md), [semantic findings](semantics_findings.md), and [wire/filesystem findings](wire_findings.md) retain exact cases, outcomes, scope and refuters. Resource caps that merely narrow the API are distinguished from actual old-contract defects.

## The most important trust test

A changed payload with a recomputed SHA-256 is still a valid envelope. Both versions accept that byte-integrity check, as they should. **This is an expected trust limit, not a failed cryptographic authentication promise.**

The new `checked_decode` helper requires externally supplied codebooks, reference rows, assignments and evidential selection. It checks the numerical trace and annotation against that context before returning a payload. In the [executed consumer probe](../v1_1/runs/2026-11-17/final_consumer.json), all four actual COBOL output records pass their declared context. A rehashed semantic-row forgery and a self-consistent wrong-code trace pass wire decoding but fail the appropriate context checks.

The same probe deliberately retains two successful attacks outside that claim: an unrelated outer label can be changed, and a different internally consistent target can be substituted. No independently trusted target measurement, sensor/encoder attestation or sender identity is supplied to this helper. An attacker controlling the caller's “trusted” reference and policy can also manufacture a consistent false account. The semantic checker reuses producer routing rules; it is a consumer consistency gate, not an independent proof of those rules or of linguistic truth.

## Executed evidence

The final repository experiment command passes **213 unittest cases with none skipped**, including the original 95-test v1/preservation suites, candidate adversarial suites, inherited compatibility checks and cross-boundary gates. This is a test-execution count, **not 213 unique attack types**. Repository Ruff passes.

The numerical replay records **39 paired fixtures** with isolated two-second worker deadlines; deliberate cooperative iterator probes hit TIMEOUT in the legacy version and terminate under candidate item policies. The semantic replay records **16 named probes per version**. The wire replay records **25 paired cases**, each child bounded to five seconds, with no child errors/timeouts. The suites also include 512 finite dyadic regression inputs and 128 deliberately invalid structured annotation mutations. Those are software fixtures, not statistical attack-success estimates, empirical semantic data or exhaustive fuzzing.

A fresh GnuCOBOL run compiles and executes the candidate successfully: four records, **65,840 input bytes and 65,840 output bytes**, exactly equal. The actual output is then consumer-checked against the external illustrative context. [Execution summary](../v1_1/runs/2026-11-17/summary.json), [test log](../v1_1/runs/2026-11-17/final_tests.log), [consumer results](../v1_1/runs/2026-11-17/final_consumer.json), and [run manifest](../v1_1/runs/2026-11-17/manifest.json) preserve source hashes, source/copybook, input/output bytes and diagnostics. The compiled platform-specific binary is omitted. Absolute paths in the original reports identify the execution machine; copied artifacts keep their relative run layout.

The baseline v1 code/contract/runs, raw inputs, prior evidence, specialist audit files, production code and CI workflows remain unchanged. Existing claim-index/prose regression details are recorded in the parent validation note. No full repository sweep or remote CI success is claimed.

## Reproduce without overwriting history

From repository root:

```sh
python -m unittest discover -s tests -p 'test_experiment_bridge*.py' -v
python experiments/experiment_bridge/adversarial/core_probe.py --output /tmp/bridge-core-new.json
python experiments/experiment_bridge/adversarial/wire_probe.py --output /tmp/bridge-wire-new.json
python -m experiments.experiment_bridge.v1_1.demo --output-dir /tmp/bridge-v1-1-new-run
```

The demo needs a new or empty allowed directory. To verify its actual output, read `cobol.artifacts.output` from the generated summary, then pass that path to `consumer_probe.py --input-file PATH --output /tmp/bridge-consumer-new.json`. The consumer output file must be new.

`semantics_probe.py --phase legacy` intentionally creates a fresh baseline snapshot, and `--phase candidate` extends that result after checking the legacy source hash. These commands write the named result inside the evidence folder; archive/copy that folder first if replaying so the dated snapshot is not erased. The saved results themselves remain available without rerunning. Existing v1 imports are not silently redirected to the candidate.

## Fixes still worth exploring

**Aggregate workload quotas.** Per-axis item caps do not bound dimension × code count × level count × sample count tightly enough for a hostile service. An explicit total-scalar/work budget and process-level memory/time budget should precede any public endpoint. Maximal Cartesian combinations were not allocated or benchmarked here.

**Measurement and source binding.** Checkpoint/codebook manifests, an independently pinned target and acquired reference, authenticated origin, and replay identifiers could distinguish a faithful computation from a consistently fabricated one. None has been added or inferred from hashes.

**A separately specified higher-precision metric.** Scaled or higher-precision arithmetic could explore underflow, near-ties and cancellation, but must name a new metric/representation contract and measure its acceptance differences. This candidate intentionally rejects demonstrated unsafe cases rather than inventing exactness.

**Stronger filesystem/process isolation.** A dirfd/no-follow design, exclusive run ownership and crash-durable publication would be needed if the filesystem becomes adversarial. Hard-link support is now a publication requirement; pre-write rechecks still leave races. Arbitrary Python methods, malicious compilers, subprocess descendants and unbounded diagnostic output are not sandboxed.

Real NCM inference, semantic assignment quality, physical power conjugacy and production certification remain separate open questions. The candidate's stronger refusal behavior is useful, but refusal is not evidence of correctness beyond the declared tests.
