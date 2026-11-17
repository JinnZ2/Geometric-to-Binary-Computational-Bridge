# Experiment bridge v1

**A checked nonphysical reference implementation, not a real NCM model, verified semantic ontology, or physical substrate.** Note 2026-11-17: this is the expansion requested after the original [audit](../AUDIT.md). Received code, raw files and earlier negative findings are untouched. [CONTRACT.md](CONTRACT.md) defines the three module boundaries.

## What now runs

The numerical kernel validates finite, compatible vectors and codebooks before selection. It records squared distances and thresholds, accepted contributions, before/after vectors, residual errors, and ordered codebook hashes. Rejection uses a null accepted index and a zero contribution; a legitimate zero vector remains a real code, not an accidentally competing VOID symbol. Ties follow fixed codebook order. Error reduction is signed and may be negative.

The semantic reference view preserves all 41 supplied rows: 25 mapping rows, five recall checks and eleven evidentials. Content/role/occurrence-based row ids distinguish safe from its snura recall specimen and retain both xagrai senses. An assignment names one explicit mapping row; no codebook index is automatically equated with a Lojban predicate. Source wording and OBSERVED/PROPOSED/DIFFERS/VOID statuses stay attached. Numerical rejection, absent assignment and lexical absence are separate states.

The transport layer validates a finite JSON object, writes canonical ASCII-escaped JSON into a fixed-width EB01 envelope, and verifies length, hash, padding and canonical spelling when reading it back. Apostrophes and Unicode are data escapes, not unescaped COBOL source literals. Overwidth payloads, non-finite floats, duplicate keys, cyclic objects and corrupt records are rejected rather than truncated. It supports optional real COBOL fixed-record read/write through a generated user-data-free copybook.

## Four states through one pipeline

The [executed demo](runs/2026-11-17/summary.json) keeps these outcomes distinct:

- **ACCEPTED + PRESENT:** a code is accepted and explicitly linked to the supplied “better” mapping row. PRESENT means a lexical record exists; its source mapping remains PROPOSED.
- **REJECTED + NOT_APPLICABLE:** distance exceeds threshold; accepted index is null and the residual passes unchanged. No semantic claim is emitted.
- **ACCEPTED + UNMAPPED:** the numerical code is accepted, but no semantic assignment exists. Its numerical contribution is retained, not silently discarded as VOID.
- **ACCEPTED + LEXICAL_VOID:** an explicitly selected scoped gap row is retained as a gap. Numerical acceptance is unaffected; no word or definition is invented.

The vectors and assignments in these demonstrations are **ILLUSTRATIVE fixtures**. Tests of routing and serialization do not empirically validate those mappings. The evidential row is explicitly chosen demonstration metadata, not an automatic truth tag.

## Reproduce

From the repository root:

```sh
python -m unittest discover -s tests -p 'test_experiment_bridge*.py' -v
python -m experiments.experiment_bridge.v1.demo --output-dir /tmp/experiment-bridge-v1-new-run
```

The demo requires a new or empty output directory and refuses raw, evidence and prior-audit directories. The Python modules are stdlib-only. If `cobc` is absent, the COBOL result is NOT_RUNNABLE, never a fabricated pass. A real compiler/runtime/byte mismatch reports FAIL and the demo exits nonzero. Received specimens are not imported.

## Evidence from this expansion

**95 experiment tests passed**, including the existing seven preservation tests and the numerical, semantic, transport and integration suites. No test was skipped in the recorded Linux/Python 3.12.3 run. Repository Ruff passed. [Test log](runs/2026-11-17/all_tests.log) and [run manifest](runs/2026-11-17/manifest.json) retain the evidence.

The combined demo compiled and ran with GnuCOBOL 3.1.2.0: four records, **65,840 input bytes and 65,840 output bytes**, exactly equal. Compiler and runtime return codes are zero. A compiler `_FORTIFY_SOURCE` redefinition warning is retained, not treated as a failure; runtime stderr is empty. The saved run includes copybook, program source, input/output bytes, source hashes and diagnostics. The platform-specific binary is omitted; original paths in diagnostic JSON identify where execution occurred.

Negative controls matter more than a happy path alone. The independent numerical validator catches an over-threshold transition relabelled ACCEPTED, stale residuals, malformed dimensions and absent/wrong codebook identities. With supplied codebooks it also rejects a self-consistent trace that used the wrong code. Without codebooks, it can check bookkeeping but cannot certify actual codebook identity or nearest choice. The transport rejects altered payload bytes. Unit tests also exercise compiler failure, byte mismatch and missing-compiler reporting as explicitly labelled fixtures, separate from real execution evidence.

## Calibration follows actual rejection

`calibrate_thresholds(..., gated=True)` calibrates each later stage on the residuals actually left by earlier accepted/rejected stages. Ungated comparison remains available explicitly. A finite illustrative fixture with samples `[0], [2], [10]` and codebooks `[[2]], [[4]]` gives thresholds `(4, 36)` for gated calibration and `(4, 16)` for ungated calibration, as tested. This exposes the trajectory mismatch found in the received toy without claiming a statistical improvement on real data.

The quantile rule and inclusive threshold are declared in `core.py`: finite samples and ties make achievable rejection rates discrete. This is not an exact target-rate guarantee or an NCM nested-dropout bound. No held-out neural/data calibration or statistical sweep was performed.

## Explicit transport aperture

Each record is **16,460 bytes**: EB01 magic 4, decimal JSON length 8, SHA-256 hex 64, and an ASCII JSON area of 16,384 bytes padded with spaces. Entire objects that do not fit raise an error. The full 41-row reference is not promised to fit in one record; the demo transports selected per-step records.

The COBOL program copies opaque fixed-width records; it does not parse semantic JSON or perform exact-decimal arithmetic. Python validates payloads before and after transport. Float spelling is preserved as Python JSON, not converted into a universally exact numeric measurement. SHA-256 detects changes relative to a recorded hash but can be recomputed by a tamperer. It is not sender authentication, immutable storage or truth certification. The large fixed aperture is a correctness demonstration, not a bitrate-optimized codec.

## What remains open

This expansion closes a bounded **software representation and routing** gap. It does not close checkpoint-specific semantic calibration, real NCM inference, genuine nested-dropout experiments, measured rate–distortion/performance, append-only storage or a physical energetic model. Source assertions remain source assertions. Physical and production registries, root claim tables and CI workflows are unchanged. CI wiring still requires workflow-write permission; the tests are runnable directly.

Any future model adapter should first record the real checkpoint, level schedule and codebook identity, then measure semantic assignment and calibrated abstention independently. No automatic promotion follows from these passing tests.
