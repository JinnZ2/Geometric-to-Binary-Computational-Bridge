# Local experiment claim record

**This is an audit of delivered specimens and a synthetic numerical witness, not a physical claim registry.** Note 2026-11-17: ids below are local `EBR_` identifiers and are not registered in the root lookup tables. SUPPORTED means the bounded statement holds; UNVERIFIED means the missing check is named. A changed reading updates this record, not the received design.

## EBR_001 — Original copybook fails compilation — SUPPORTED

The unchanged generator, applied to the supplied JSON, produces source that fails GnuCOBOL 3.1.2.0 free-source compilation at an unescaped apostrophe. Evidence: [compiler record](evidence/original_compiler/original_generated/command.json), [diagnostics](evidence/original_compiler/original_generated/stderr.txt), and [code audit](audit/code-audit.md). Refuter: successful compilation of those exact source bytes with the recorded compiler/options, not a repaired or different input fixture.

## EBR_002 — Original level-walk narration does not execute — SUPPORTED

The received target/hierarchy emits three VOIDs and zero accepted reconstruction, not the narrated two successes. Evidence: [original replay](evidence/original_reproduction.json). Refuter: the exact unchanged script and supplied JSON executing the advertised successful sequence under its original main configuration.

## EBR_003 — Word-only semantic keys lose distinct records — SUPPORTED

The original adapters overwrite different senses and recall specimens sharing an identifier. Evidence: [code audit](audit/code-audit.md), [schema audit](audit/semantic-physics-audit.md), and raw JSON. Refuter: an unchanged adapter retaining both records under independent identities rather than last-row-wins dictionary values.

## EBR_004 — Kimi seed-0 stable results reproduce — SUPPORTED

Two replays match every saved numerical value and verdict after removing only runtime_s and claims[].ts. This states nothing about byte-identical output or another Python version/seed. Evidence: [Kimi replay](evidence/kimi_reproduction.json). Refuter: stable-field differences when replaying the same specimen and configuration in the recorded environment.

## EBR_005 — Finite synthetic routing and additive bookkeeping hold — SUPPORTED

Independent traversal finds zero over-threshold accepted snaps on the 1,000 held-out vectors, with additive reconstruction/residual error no larger than 1.2e-16. Evidence: [Kimi replay](evidence/kimi_reproduction.json). Refuter: one over-threshold accepted code on that dataset or additive error beyond that stated bound. This is not a guarantee for malformed input, altered dimensions, or changed codebooks.

## EBR_006 — Neural semantic and physical integration remains unverified — UNVERIFIED

No NCM inference, checkpoint-specific Lojban calibration, compatible COBOL round trip, or power-conjugate physical measurement chain was delivered. Evidence: [AUDIT.md](AUDIT.md) and its scoped specialist reports. What changes the state: a separately specified and tested integration with actual model artifacts, linguistic evaluation, validated numeric/byte contracts, and a physical model if physical terminology is retained. A toy replay or labels alone do not settle it.

## EBR_007 — Raw files and archive members are preserved — SUPPORTED

Received hashes and extracted bytes match the manifest; three original Python fence bodies match their raw source. Evidence: [manifest](raw/manifest.json), `tests/test_experiment_bridge.py`. Refuter: any byte/hash mismatch or transformed original. This proves preservation relative to received files, not authentication of upstream authors or quotations.

## Subsequent v1 findings — 2026-11-17

These findings concern the separately implemented version, not the unchanged received scripts.

## EBR_008 — Four decision states survive annotation and transport — SUPPORTED

The four illustrative integration fixtures retain ACCEPTED/PRESENT, REJECTED/NOT_APPLICABLE, ACCEPTED/UNMAPPED and ACCEPTED/LEXICAL_VOID without changing numerical contributions or promoting the reference's PROPOSED mapping. Evidence: [v1 run](v1/runs/2026-11-17/summary.json) and `tests/test_experiment_bridge_v1.py`. Refuter: any fixture collapses those statuses, mutates numerical input or replaces the source status during the recorded round trip. This is software routing, not semantic validation.

## EBR_009 — Actual COBOL stream round trip preserves bytes — SUPPORTED

The v1 generated program compiled and ran with return codes zero, copying four fixed-size records: 65,840 input and output bytes, exactly equal. Evidence: [v1 summary](v1/runs/2026-11-17/summary.json), retained program/copybook and byte files under its run directory. Refuter: unequal input/output bytes or nonzero compiler/runtime result when repeating that exact configuration. The program transports opaque JSON envelopes; it does not validate semantics or perform exact-decimal arithmetic.

## EBR_010 — Negative numerical and transport controls are detected — SUPPORTED

The v1 validator rejects an over-threshold transition marked accepted, and the wire parser rejects changed payload bytes. With actual levels supplied, the numerical validator also rejects a self-consistent wrong-code trace; without them, it cannot establish actual codebook identity. Evidence: [v1 test log](v1/runs/2026-11-17/all_tests.log) and integration summary. Refuter: the deliberately broken fixtures pass the same checks. This states nothing about every possible adversarial payload.

## EBR_011 — Source rows stay distinct in the normalized reference — SUPPORTED

The supplied 41 rows normalize to independent mapping, recall and evidential records with source content/role/occurrence identity. Safe versus recall snura and both xagrai senses remain separately queryable. Evidence: `tests/test_experiment_bridge_semantics.py`. Refuter: identifier-only overwriting, omitted input source fields, or an assignment silently selecting a recall/evidential row as a mapping.

## Subsequent adversarial findings — 2026-11-17

The retained v1 is unchanged. These candidate claims refer only to documented fixtures and limits, not universal defenses.

## EBR_012 — Demonstrated fail-open underflow and lossy Integral inputs are rejected — SUPPORTED

Legacy v1 accepts a nonzero code distance squaring to zero at threshold zero and loses identity for `2**53+1`. Candidate v1.1 raises ValueError for those cases. Evidence: [numerical replay](adversarial/core_results.json) and [findings](adversarial/core_findings.md). Refuter: candidate returns the same accepted trace for either exact fixture. Noninteger Real rounding, nonzero subnormal rounding and already preconverted floats remain representation limits.

## EBR_013 — Demonstrated recursion/identity failures have bounded rejection — SUPPORTED

Candidate reference validation rejects the recorded cyclic/deep source extensions, duplicate row ids, conflicting source slots and impossible occurrence metadata. Candidate wire decoding rejects over-depth valid JSON before the demonstrated parser recursion failure. Evidence: [semantic replay](adversarial/semantics_results.json), [wire replay](adversarial/wire_results.json), and their scoped reports. Refuter: one listed candidate case is accepted or leaks the recorded recursion failure. The newly declared size/depth policies narrow the API; they do not invalidate large linguistic content.

## EBR_014 — Rehashed trace forgeries fail external-context consistency checks — SUPPORTED

The actual-output consumer probe accepts four honest illustrative COBOL records, but rejects a rehashed copied-row forgery and a self-consistent wrong-code trace against independently supplied reference/assignment/codebook context. Evidence: [consumer results](v1_1/runs/2026-11-17/final_consumer.json). Refuter: either forged trace passes those same supplied context checks. Outer labels, sender origin, replacement targets, semantic truth and malicious externally supplied policies remain unbound.

## EBR_015 — Recorded output-preservation interleavings are mitigated — SUPPORTED

Candidate held-path guards and exclusive publication reject the disposable leaf-symlink and held-directory-swap fixtures while preserving the temporary victim. Evidence: [wire/filesystem findings](adversarial/wire_findings.md) and paired replay. Refuter: either exact candidate fixture overwrites the victim or creates the claimed held output. This is not an OS-level TOCTOU, hostile-process isolation or crash-durability guarantee.

## Kimi round 2 snapshot findings — 2026-11-17

These rows record what the received `snapshot_delta.py` measures on its own two toy systems (an exact Fibonacci-word inflation and two float ODEs under RK4), replayed twice with every claim equal. Evidence for all four: [the specimen and its seed-0 record](evidence/kimi_round2_as_received/snapshot_delta_seed0.json) and [the round-2 replay](evidence/kimi_round2_reproduction.json). They are statements about that script's systems and step sizes, not about checkpointing in general, a neural codec or a physical process. The tolerances behind the verdicts are the script's own; the replay records which of them state a reason.

## EBR_016 — Resume from an exact snapshot reproduces the uninterrupted run — SUPPORTED

Resuming the Fibonacci word from snapshots every 5 levels gives 0 mismatched levels of 26; the letter-count chain gives 0 of 26; and RK4 resumed from an exactly stored float state matches the uninterrupted integration bitwise on both ODE systems (0 mismatched states). Refuter: one mismatched level or state when the same specimen is replayed. This holds for a stepper whose next state depends only on the stored state, in one process on one machine; it says nothing about a snapshot that crosses platforms or loses precision.

## EBR_017 — A lossy snapshot stays bounded on the decaying system — SUPPORTED

With the mid-trajectory state rounded to 3 decimals on the stable spiral (lambda = -0.1), the error 30 s later is 0.0498 times the injected error, inside the script's band of [0, 3]. Refuter: a ratio above 3 on that replay. The band is stated in the claim text without a reason, so the replay lists its tolerance as UNSOURCED; the number is one horizon on one system.

## EBR_018 — On the Lorenz system a lossy snapshot needs refresh — SUPPORTED

The same rounding on the Lorenz system gives an error ratio of 16980 at the 30 s horizon against the script's band of 100: the claim is a designed fail and it fails. With refresh (resync when the receiver is more than tau away), the largest deviation at tau 0.5 is 0.577, inside the stated bound of 1.5 tau, at 261 refreshes in 10,000 steps. Refuter: a ratio inside 100 without refresh, or a deviation above 0.75 with it, on that replay. The band of 100 states no reason (UNSOURCED); the refresh bound's reason, one-step overshoot, is the script's. How often refresh is needed is specific to this step size and receiver.

## EBR_019 — A word cannot be resumed from its letter counts — SUPPORTED

The letter counts resume exactly as counts, but they are a many-to-one summary of the word: at level 8 the counts (34, 21) fit 841,728,816,603,675 distinct words, and the script records the claim's value and measured fields as null with verdict `void`. Refuter: a decoder that returns the level-8 word from its two counts alone. The count of words is arithmetic (55 choose 21), not a measurement; the finding is that the specimen keeps this as a VOID and does not fill it.

