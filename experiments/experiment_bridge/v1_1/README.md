# Experiment bridge v1.1 candidate

**Additive candidate fixes from the [adversarial audit](../adversarial/README.md), not a production or security certification.** Note 2026-11-17: the original `v1/` implementation, contract and run evidence remain unchanged. This directory is selected explicitly by importing `experiments.experiment_bridge.v1_1`; existing v1 imports are not redirected.

## Changed behavior

The numerical module now rejects lossy integer conversion and nonzero component squares that underflow to zero. Walk refuses transitions outside its existing additive-identity tolerance. Input iteration is bounded; the diagnostic validator does not consume an invalid steps generator and normalizes the demonstrated ordinary iteration errors.

Semantic references have bounded JSON structure and consistent uniqueness/occurrence/position checks. Stable ids and all 41 received source rows are preserved. `validate_annotation` checks annotations against externally supplied reference and assignment context; it does not trust transported provenance as its authority.

Wire encoding preflights escaped byte size, nesting, nodes and integer/string limits before canonical assembly. Decoding rejects over-depth JSON before parser recursion. COBOL record collection is incremental and capped. Output guards cover held source/evidence/archive directories, and complete text files publish exclusively rather than replacing an existing file or symlink. The demonstrated filesystem race probes are mitigated, not universally eliminated.

`verify.checked_decode(record, levels, rows, assignments=None, evidential_row_id=None)` composes byte decoding, numerical validation and semantic consumer validation. It returns a payload only if those checks pass. The supplied levels/reference/policy are external trust inputs; neither sender identity nor the original target measurement is authenticated. Arbitrary outer labels and an internally consistent replacement target remain outside its claim.

## Intentional compatibility limits

Trace and semantic provenance version is now `experiment-bridge/v1.1`. EB01 framing is unchanged at 16,460 bytes with a 16,384-byte JSON aperture. Ordinary accepted/rejected decisions, source rows and row ids are compatible within the declared supported range; a legacy trace version is not silently presented as a v1.1 trace.

Numerical caps: dimension 4,096; codes per book 4,096; levels 64; calibration samples 4,096; collection consumes at most one extra item to detect excess. The existing arithmetic relative/absolute tolerance remains `1e-12`. Caps do not impose an aggregate scalar or CPU budget.

Semantic caps: root-depth 0 through 32; 100,000 expanded JSON nodes/keys; 65,536 characters per string/key; 1,000,000 aggregate text characters; 1,024-bit integers; 4,096 reference rows and bounded occurrence/index metadata. Filtered or reordered legitimate subsets remain supported.

Wire caps: at most 64 container levels (root depth 1), 16,384 nodes/keys, 16,384 string code points and integer magnitude digits, plus the stricter exact 16,384-byte escaped-JSON aperture. Up to 64 records may enter a compiler stream. Compiler/runtime subprocess timeout remains 30 seconds per call. These are conjunctive policies; satisfying one cap does not waive another.

Candidate runtime refuses outputs in raw, evidence, audit, the entire legacy v1 tree, candidate archived runs, and adversarial evidence. Saved runs here were curated from outside runtime output after execution. Exclusive text publication requires local hard-link support. The filesystem is still a trust assumption.

## Run and inspect

From repository root:

```sh
python -m unittest discover -s tests -p 'test_experiment_bridge*.py' -v
python -m experiments.experiment_bridge.v1_1.demo --output-dir /tmp/bridge-v1-1-new-run
```

Optional GnuCOBOL absence is NOT_RUNNABLE, not PASS. A real compiler/runtime/report failure returns FAIL; a completed demo with that failure exits nonzero. The recorded run passed actual COBOL transport and subsequent consumer checks: [summary](runs/2026-11-17/summary.json), [consumer results](runs/2026-11-17/final_consumer.json), [213-case test log](runs/2026-11-17/final_tests.log), and [artifact manifest](runs/2026-11-17/manifest.json). The test total includes legacy and inherited compatibility executions, not that many unique attacks.

The [adversarial report](../adversarial/README.md) distinguishes reproduced defects, new bounded policies, expected rejection and deliberate trust/representation limits, with probes and refuters. Unresolved: higher-precision arithmetic, aggregate resource quotas, target/source authentication, OS-level race/process isolation, real neural/linguistic validation and physical measurement. Do not promote this candidate by inference from passing tests.
