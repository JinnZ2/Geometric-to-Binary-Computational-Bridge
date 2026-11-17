# Validation snapshot — 2026-11-17

This snapshot records checks on the additive experiment branch. It does not certify the incoming scripts or claim that every repository test ran.

## Passed checks

`python tests/test_experiment_bridge.py`: **7 tests passed**. Received file hashes, archive-member bytes, exact Python fence extraction, duplicated semantic instances, repeated record roles and declared null gaps are preserved. A deliberately corrupted payload fails its original hash comparison.

`python tests/test_claims_index.py`: **52 tests passed** both before the addition and after staging the experiment documentation and evidence.

`python tests/test_bridges.py`: **768 tests passed**. This existing suite was run before the final documentation additions; no production bridge implementation changed.

`ruff check .`: **passed** for the repository including the new tests, audit harnesses and received Python specimens.

The original-specimen replay snapshot has **16 passing audit assertions**; Kimi's replay snapshot has **7 passing audit assertions**. Those assertions confirm recorded findings, including defects. The independent synthetic checks are software measurements, not real NCM inference or physical validation. The CLI comparisons exclude only the runtime field and claim timestamps.

The seven fast preservation tests and full replay harnesses remain available for explicit execution; the optional compiler branch requires GnuCOBOL. Existing CI is unchanged. Note 2026-11-17: the first branch push was rejected because the GitHub App cannot modify `.github/workflows/tests.yml` without `workflows` permission. The proposed CI step was removed, not silently claimed as delivered. Wiring that suite into CI is held for a workflow-authorized actor. No claim of remote CI success is made by this local snapshot.

## Expected nonzero results

GnuCOBOL 3.1.2.0 returns **97** for compilation of the unchanged original generated copybook. This is the audited defect, not a compilation failure of a promoted runtime. Exact source, wrapper, options and diagnostics remain under `evidence/original_compiler/`.

`python repo_guard.py prose` returns **1** with **47 existing hits** on both the baseline and staged addition. The two captured reports were identical. No unrelated prose correction or blanket suppression was made.

`git diff --cached --check` reports trailing whitespace in the untouched incoming working notes and extracted Python specimens, plus a final blank line in two retained generated copybook specimens. These bytes are preserved deliberately. Authored documentation, tests and harnesses are checked separately from raw/specimen bytes rather than cleaning the originals.

## Boundaries

The audit used Python 3.12.3 on Linux. Incoming sources and generated replay records retain their environment details and hashes. Fixed-seed replication elsewhere may depend on Python's random and floating-point behavior; no universal cross-platform byte-identical claim is made.

No model training/inference, complete linguistic audit, exact-inflation replay, database integration, corrected production adapter, full repository test sweep, or physical sensor measurement was performed. Main and the production claim registries are not altered by this experiment branch.

## Subsequent v1 expansion — 2026-11-17

The separately implemented [v1](v1/README.md) has **95 passing experiment tests, with none skipped**, covering preservation, numerical guards/trace checks, semantic reference roles, wire validation and integration. Its actual GnuCOBOL four-record demonstration compiled and ran successfully and preserved **65,840 bytes exactly**. Compiler warning and runtime diagnostics are retained. Repository Ruff passed; the existing claim-index suite passed 52 tests after staging. Prose guard remains byte-for-byte identical to the 47-hit baseline. Raw files, prior evidence, specialist audit files and CI workflows remain unchanged.

The v1 test log includes explicitly labelled simulated compiler-failure output; it is a negative-control fixture, not the real integration result. The real integration snapshot reports PASS. Serialized `.dat` streams include intentional padding and no added line terminator, so v1 marks them binary in Git to preserve byte semantics. Authored code/documentation diff checks are separate from retained protocol bytes. No exact-decimal ledger, real NCM inference, semantic calibration or physical model is claimed.

## Subsequent adversarial candidate — 2026-11-17

[Adversarial findings](adversarial/README.md) and the separate [v1.1 candidate](v1_1/README.md) retain reproduced breakages, narrow corrections, policies and trust limits. The full experiment command passes **213 unittest cases with none skipped**; this includes the unchanged legacy suites and inherited compatibility executions, not 213 distinct attacks. Repository Ruff and staged authored-file diff checks pass. The existing claim-index suite passes **52 tests** after staging the candidate, and prose guard remains exactly identical to the **47-hit** baseline.

A fresh actual GnuCOBOL candidate run compiles/executes successfully and preserves **65,840 input/output bytes exactly**. Its four actual output records pass the external illustrative context checks. Rehashed copied-row and wrong-code traces fail context checking, while coherent replacement targets and unrelated outer labels deliberately remain accepted as documented trust limits. The semantic consumer checker reuses producer rules; it is not an independent semantic proof.

Legacy `v1/` code, contract and runs; raw inputs; prior evidence/audit files; production code; and CI workflows remain unchanged. New byte streams are marked binary for exact transport semantics. No exhaustive fuzzing, full repository sweep, remote CI-success claim, hostile-process/filesystem security certification, authenticated origin, exact arithmetic, neural semantic calibration or physical measurement is made. Aggregate CPU/memory quotas and stronger target/source binding remain explicit unimplemented protections.
