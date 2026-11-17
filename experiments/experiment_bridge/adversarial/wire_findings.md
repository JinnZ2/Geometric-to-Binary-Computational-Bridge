# Wire and output-policy adversarial findings

Note 2026-11-17: additive audit against the supplied baseline `19c9a80`; the original v1 remains a correction specimen. Candidate: `experiment-bridge/v1.1` (`v1_1`). Read `READ_ME_THIS_WAY.md` with this record. Only candidate `wire.py`/`demo.py`, the new adversarial wire test, and this wire evidence set were authored here. No legacy implementation, raw specimen, existing audit, other module, Git state, or CI file was edited.

## Scope and reproducibility

This is bounded software validation, not authentication, production hardening, arbitrary-process isolation, calibrated semantics, or a physical-system finding. Every path adversary uses a disposable mock bench with a copied reference; **no actual specimen was attacked**. Each independent probe child is limited to five seconds. The original unbounded collector is stopped by a sentinel exception after 66 generated records rather than allowed to exhaust resources.

From repository root:

```bash
python experiments/experiment_bridge/adversarial/wire_probe.py
python tests/test_experiment_bridge_adversarial_wire.py
```

`wire_probe.py` produces `wire_results.json`: **25 paired cases, 50 executions, 0 child errors, 0 bounded timeouts**. Temporary compiler artifacts are removed by the probe; the JSON records real outcomes, not invented compiler passes. Individual cases can be replayed using `--version v1 --case deep_decode` (or `v1_1`).

## Confirmed implementation/preservation issues: four

| ID | Original v1 observation | Candidate treatment |
|---|---|---|
| W-01: unnormalized recursion failure | Correctly framed/hashed, valid JSON with 1,200 nested arrays uses only **2,407 JSON bytes**, below 16,384, but decode raises `RecursionError`. Deep Python objects also reach `RecursionError` during recursive validation. This is a real under-capacity robustness failure, not malformed framing. | Explicit container-depth preflight rejects depth over **64** before `json.loads`; encode checks depth before assembling JSON. Unexpected parser/validator/serializer `RecursionError` becomes `ValueError` with the stated depth. Depth 64 round-trips; depth 65 deliberately does not. The candidate contract is intentionally narrower than unrestricted under-capacity nesting. |
| W-02: limit enforced after allocation | A 50,000-character string, 3,000 `雪` characters, a 17,001-digit integer (`10**17000`), a wide list, and a shared binary DAG are rejected, but only after canonical JSON assembly starts. Instrumented `_json_text` calls: wide list **16,388**, huge string **3**, Unicode oversize **3**, huge integer **3**, shared-DAG expansion **16,383**. These small reproductions demonstrate allocation order; they are not exhaustion measurements. | Bounded preflight rejects all five before `_json_text` (**0 calls** each). It checks exact ASCII-escaped size, string code points, node visits (including keys/repeated shared values), depth, cycles, and finite/legal types. Integer magnitude is compared against a bounded constant before `abs`/decimal chunk construction; legal large integers remain supported without changing Python's global digit-conversion setting. |
| W-03: unbounded stream collection | `records = list(records)` has no count bound. The sentinel stream consumes **66** items, then propagates the probe's `RuntimeError`. An actually endless iterable would not reach validation or compiler execution. | Validate incrementally; accept at most **64** records. Reject after consuming the **65th**, do not create output artifacts. Invalid items also reject before any writes. This bounds storage, not the execution time of a user-written iterator's `next()` method. |
| W-04: incomplete preservation policy | New directories inside old `v1/runs` pass the wire path guard; a demo using temporary `v1/runs/new-run` writes four fixtures and a summary. Original guards also accept new `v1_1/runs` and `adversarial` paths; these are newly requested candidate preservation exclusions, not claims that v1 anticipated later archives. | Refuse any output within `raw`, `evidence`, `audit`, the entire immutable `v1` tree (including `v1/runs`), candidate `v1_1/runs`, or `adversarial`. Check lexical and resolved paths, including symlink parents, before writes and even when `cobc` is absent. Ordinary outside directories, including trusted allowed symlink parents and an existing empty demo directory, remain supported. |

Preflight still incurs bounded work on an already-created input object. It does not undo the caller's allocation, isolate arbitrary Python behavior, or promise a fixed wall-clock runtime for arbitrary processes.

## Trusted-filesystem observations: two, not OS-isolation claims

**T-01 — injected leaf symlink.** In a temporary existing empty demo output, the probe inserts a symlink at the first fixture filename between the emptiness check and the write. V1 follows it and overwrites a temporary victim. Candidate final-file publication is exclusive: it raises `FileExistsError`, leaves the victim unchanged, and creates no summary. This mitigates accidental/injected leaf replacement. It is not a claim that all filesystem races are closed.

**T-02 — injected directory swap.** The probe replaces the temporary output directory with a symlink into a temporary mock `raw` directory after the initial guard. V1 writes a fixture and summary into that mock held directory. Candidate's pre-write recheck catches this specific interleaving and rejects before a held fixture is created. A directory/symlink can still change *after* a recheck. **The local filesystem must remain trusted during the run**, including when an existing empty directory is supplied. There is no dirfd-based OS-level TOCTOU guarantee, malicious-compiler sandbox, or protection from an arbitrary concurrent local process.

Compiler runs use newly created exclusive `eb01-*` directories. Candidate text reports/fixtures are written to an exclusive temporary file, successfully closed, then published via a same-directory exclusive hard link; an existing file/symlink is not replaced. This requires ordinary local-filesystem hard-link support. It is not power-loss durability or atomic directory isolation. A failed cleanup can leave a clearly temporary dot-prefixed file, not a claimed final success report.

## Diagnostic hardening: one

**D-01 — report/artifact failure normalization.** Mock report denial makes v1 raise `OSError`; it does **not** prove that v1 returned a false PASS. Candidate returns overall `FAIL` with `report_error`, removes the uncreated `report` artifact from its returned mapping, and retains actual compiler/runtime diagnostics. Artifact preparation failure remains `FAIL` with `compile_status=NOT_RUNNABLE`. Tests additionally simulate byte-exact compiler/runtime PASS followed by report failure: overall status is still `FAIL`, the final report is absent, and successful transport sub-statuses remain truthful. Atomic publication avoids a partial write/close failure creating a final `summary.json`/`result.json`.

## Expected behavior / genuine rejection controls: four categories

1. **Strict fixed-record rejection is already working.** Both versions reject all **9/9** correctly hashed noncanonical/invalid controls (whitespace, ordering, numeric spelling, escaped ordinary text, trailing JSON whitespace, duplicate keys, NaN, overflow-to-infinity). Existing framing/hash/padding/type tests also pass. Cycles already raise `ValueError`; they are not the recursion bug.
2. **SHA-256 is integrity relative to the envelope, not authentication.** Both versions accept an altered canonical payload `{"x":2}` whose sender recomputes the hash. This is expected and is explicitly not reported as an authentication defect. No HMAC/signatures or provenance promises were added.
3. **Process timeout was already bounded.** Both versions pass **30 seconds** to the compiler/runtime subprocess call and return timeout diagnostics. Candidate additionally normalizes both bytes and text in `TimeoutExpired` output. The pathological probe itself never waits 30 seconds: it injects the exception or uses a five-second child deadline. Captured process diagnostics, descendant processes, and hostile executables are not fully isolated/resource-limited.
4. **Partial demo failure already avoids a success summary.** A failure on the second annotation leaves the first fixture, raises `OSError`, and produces **no summary** in both versions. Thus no pre-existing false-success summary was demonstrated. Candidate preserves partial diagnostics, uses final-only complete summary publication, and truthfully records COBOL `FAIL` in a completed integration summary; its CLI exits nonzero for that failure.

## Exact candidate bounds

| Constant / policy | Value |
|---|---:|
| `VERSION` | `experiment-bridge/v1.1` |
| `MAGIC` | `EB01` (unchanged transport framing) |
| `JSON_CAPACITY` | 16,384 ASCII bytes |
| `HEADER_SIZE` | 76 bytes |
| `RECORD_SIZE` | 16,460 bytes |
| `MAX_JSON_DEPTH` | 64 containers, root object at depth 1 |
| `MAX_JSON_NODES` | 16,384 visited values and object keys |
| `MAX_JSON_STRING_LENGTH` | 16,384 code points; total escaped byte cap still applies |
| `MAX_INTEGER_DIGITS` | 16,384 magnitude digits before chunk construction; total record cap still applies |
| `MAX_RECORDS` | 64; at most one additional item consumed to reject excess |
| Maximum encoded compiler input | 1,053,440 bytes |
| `PROCESS_TIMEOUT_SECONDS` | 30 per compiler/runtime call |
| Path exclusions | `raw`, `evidence`, `audit`, `v1`, `v1_1/runs`, `adversarial` |

`{"x":10**16377}` uses all **16,384** bytes and round-trips in the regression test. The paired integer probe also preserves a **16,383-byte** legal integer record. Strings at exact record capacity, Unicode escapes, apostrophes, nulls, booleans, finite floats (including signed zero), keys, and large integers retain their existing wire representation. Public core/semantic API names were not changed.

## Validation results

All commands ran from repository root on this environment with `/usr/bin/cobc` available.

| Command / suite | Tests | Result |
|---|---:|---|
| `python tests/test_experiment_bridge_adversarial_wire.py` | **53** (31 inherited compatibility gates + 22 additional gates) | PASS |
| `python tests/test_experiment_bridge.py` | 7 | PASS |
| `python tests/test_experiment_bridge_core.py` | 31 | PASS |
| `python tests/test_experiment_bridge_semantics.py` | 19 | PASS |
| `python tests/test_experiment_bridge_wire.py` | 31 | PASS |
| `python tests/test_experiment_bridge_v1.py` | 7 | PASS |
| **Total assertions grouped as unittest test cases across these invocations** | **148** (95 old + 53 candidate; includes intentional compatibility repeats) | PASS |

Real GnuCOBOL verification passes for both versions in the paired probe. Candidate compatibility also runs real empty-stream, full-width, and two-record transports. A candidate demo using an existing empty `/tmp` output completes four fixtures and real byte-exact COBOL transport (**65,840 bytes**, 4 × 16,460). Optional compiler absence remains `NOT_RUNNABLE`, never a manufactured pass; tests skip real compiler gates when unavailable. Targeted Ruff checking of the four authored Python files passes.

Saved evidence: `wire_probe.py` (reproducer), `wire_results.json` (paired machine outcomes), and this dated finding record. Generated reports are not added to preserved legacy runs or adversarial evidence by the demo/runtime.
