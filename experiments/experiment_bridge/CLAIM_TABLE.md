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
