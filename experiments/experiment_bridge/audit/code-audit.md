# Experiment bridge — executable specimen audit

**Note 2026-11-17.** This is an additive audit, not a replacement implementation. `READ_ME_THIS_WAY.md` and `READING_PROTOCOL.md` were read before execution. Raw notes, semantic JSON, all three extracted scripts, and the later Kimi archive files remain unchanged; SHA-256 before/after checks are in the evidence. No git operations were performed. The raw snippets are **correction specimens**, not usable production bridge implementations.

## Evidence and reproduction

Evidence paths below are relative to the parent experiment folder. Specialist reports record only their assigned audit scope; the combined disposition is in ../AUDIT.md.

- `evidence/reproduce_originals.py`: reusable stdlib harness; 29 bridge cases, 20 level-walk cases, 10 generator fixtures, plus formatter and compiler probes.
- `evidence/original_reproduction.json`: complete machine results, original main stdout/stderr, schema outcomes, and 16 passing audit assertions.
- `evidence/original_compiler/`: exact generated copybook, free-source wrappers, compiler commands, diagnostics, version, and independent language probes. GnuCOBOL `3.1.2.0` was installed in the audit sandbox; the compiler version and exact diagnostics are retained with the evidence.
- `evidence/reproduce_kimi.py` and `evidence/kimi_reproduction.json`: two exact CLI replays, a third training pass for independent census checks, 22 input edge cases, and seven passing assertions.

```sh
# From repository root
python3 experiments/experiment_bridge/evidence/reproduce_originals.py
python3 experiments/experiment_bridge/evidence/reproduce_kimi.py
# Stdlib-only Python reproduction, omitting optional compiler checks:
python3 experiments/experiment_bridge/evidence/reproduce_originals.py --skip-compiler
```

**Do not run the received scripts directly in the evidence folder:** the generator executes on import, and Kimi's CLI overwrites its seed-named output. Both harnesses copy specimens unchanged to a `TemporaryDirectory`, execute there, and remove it. Fixtures and independent language probes are tests, not edits to the originals. Passing harness assertions mean the recorded audit findings reproduced; they do not certify the specimens as correct.

Line references below use **G** = `generate_copybook_as_received.py`, **B** = `ncm_bridge_as_received.py`, **W** = `ncm_level_walk_as_received.py`, **K** = `kimi_as_received/toy_rvq_void.py`, **N** = `raw/working_notes.txt`, **J** = `raw/lojban_wordslot_reference.json`, and **E** = Kimi's `contextual_substrate_entry.md`.

## 1. Numerical examples: what actually runs

**B residual `[0.15, 0.22, 0.28]`, threshold `0.3`**. Executable result: nearest `xagmau`, distance `0.05744562646538026`, printed `0.0574`. Conflict with notes: N492 prints `0.0608`.

**B residual `[0.8, 0.1, 0.5]`, threshold `0.3`**. Executable result: VOID, distance `0.7348469228349535`, printed `0.7348`. Conflict with notes: N496–501 prints `0.6782`.

**W target `[0.8, 0.9, 0.1]`, original hierarchy**. Executable result: all three levels VOID; distances `0.5099019513592785`, `0.7071067811865476`, `1.101135777277262`; reconstruction stays zero, residual stays target, L1 reductions all zero. Conflict with notes: N691–704 describes two successful levels followed by VOID; this does not execute.


B's second example has mathematically tied distances to its first two codes, but floating arithmetic yields `0.7348469228349536` versus `0.7348469228349535`. At a permissive threshold the second would win; exact equal distances retain the first because B53 uses `<`.

An **input-fixture-only** increase of W's first threshold from `0.5` to `0.51` accepts its first code: reconstruction `[0.5,0.5,0]`, residual `[0.30000000000000004,0.4,0.1]`, L1 reduction `1.0`. Level two then reconstructs the target with distance `5.551115123125783e-17`, reduction `0.8`, and exits before level three. This also contradicts the stated rates `1.2`, `0.5`, and leftover residual. Originals were not changed.

## 2. Schema and record contracts do not join

G16–27 actually computes widths **12 / 36 / 15 / 10 / 10 / 10 / 402 / 290**, totaling **785 declared bytes**. The notes' sample widths `26 / 147 / 345` are not the output from this supplied JSON. B74–78 hardcodes those stale widths and B92 omits the declared **RECORD-TYPE** entirely: its output is **563 characters**, not a compatible ledger record. Even adding twelve characters alone would not reconcile the remaining widths. Machine evidence includes parses against both layouts showing the misalignment.

W21–42 emits a human-readable, delimiter-containing line, ordinarily **439 characters** here, rather than either fixed record schema. It omits class, structure/mapping statuses, and record type. W30 computes a verbatim structure but W42 never emits it. Numeric apertures use `rjust`, a minimum width, so large values and long level numbers expand the line. Signed values print `0-1.00`; non-finite values print `000nan` / `000inf`. Distinct vectors `[1,-1]` and `[0,0]` yield identical formatter records when other inputs match: summed coordinates lose vector information.

Both semantic dictionaries use `gismu` as their sole key (B28, W8), not a row identity. Thirty place rows contain three null identifiers and only twenty unique non-null keys. Last-row-wins overwrites are:

**`xagrai`**. Rows in input order: best → optimal. Surviving row: optimal.

**`zmadu`**. Rows in input order: superior → more → greater → recall check. Surviving row: zmadu (recall check), DIFFERS.

**`le'onmo`**. Rows in input order: hostile → aggressive. Surviving row: aggressive.

**`snura`**. Rows in input order: safe → recall check. Surviving row: snura (recall check), DIFFERS.

**`jibni`**. Rows in input order: near → recall check. Surviving row: jibni (recall check), DIFFERS.


See J35–49/172–186, J80–124/140–154/425–435, J263–292, J309–323/399–409, and J370–384/411–423. The generator preserves separate rows, but the bridges collapse them. `xamgu` resolves only to its recall-check row (J438–449); `xlali` is absent. Both bridges exclude all eleven evidentials and the null-mapped efficient/cold/imminent rows. A fixture replacing `gismu` with `valsi` makes both constructors raise `KeyError`; G instead silently substitutes VOID because it uses `.get`. This is a demonstrated field contract, not a proposed schema migration.

## 3. COBOL compilation, character widths, and truncation

G54–60/G69–75 interpolate single-quoted literals without escaping embedded apostrophes. The received `xagme'a` breaks the generated source at **copybook line 31**. Exact compilation of the untouched generated copybook in a minimal wrapper used:

```sh
cobc -free -Wall -fsyntax-only -I . wrapper.cob
cobc -free -Wall -x -I . -o original-audit wrapper.cob
```

Both returned **97**, nonzero. The first diagnostic is `ledger.cpy:31: error: syntax error, unexpected Identifier`; subsequent diagnostics cascade until `too many errors [-fmax-errors=128]`. Preserve that distinction: the large cascade is not evidence of hundreds of independent defects. Exact commands and output are in `original_compiler/original_generated/command.json`, `stderr.txt`, and `full_compile.json`.

Isolated inputs to the unchanged generator establish additional defects without repairing the full source:

- An apostrophe-only fixture fails compilation; a parenthesized English name generates `ENTRY-GLARE-(RECALL-C` and fails. G52/G67 truncate names to fifteen characters and do not fully sanitize them. Two names sharing that prefix produce a compiler redefinition warning, not distinct identifiers.
- G5 counts Python characters (`len(str(...))`), not encoded bytes. A 100-character `é` reason produces PIC X(100) with a 200-byte UTF-8 literal. GnuCOBOL warns but compiles; the displayed initialized field contains **50**, not 100, `é` characters. The actual supplied snura bridge record is **563 characters / 567 UTF-8 bytes**; an oversized Unicode formatter fixture is **563 characters / 710 bytes**. Encoding is not declared by these snippets.
- G57–58 do not truncate overlong statuses. A `STATUS-TOO-LONG` fixture compiles with a warning and initializes `STATUS-TOO` in PIC X(10). G treats null gismu/structure as VOID/NO DEFINITION but null `mapping_reason` raises `TypeError` at G60. An empty-array fixture compiles and declares fallback widths; schema validation is absent.
- B80–89 and W28–39 explicitly slice and silently discard excess text. A 400-character evidential occupies the entire reason aperture and removes the distance/reason; newline evidentials pass through. None are validated against the JSON evidential list.

An **independent COBOL language probe**, not a corrected copybook, returned `INITIAL=PASS`, `APERTURE=abc`, `DECIMAL=1.23`: a VALUE-initialized `VOID` field was overwritten; a six-character variable moved into PIC X(3) truncated without runtime failure; `1.239` moved to PIC 9V99 truncated with a compiler warning. Thus N212/N344–346's universal “fails loudly,” “no silent truncation,” and “immutable” claims do not hold. The received generator contains **only PIC X** data, not exact-numeric arithmetic; B/W use binary floats and rounded textual formatting. No COBOL file writer, READ pipeline, DB2 integration, or immutable storage exists here.

## 4. VOID, mutation, validation, and parameter claims

**B's zero vector participates in nearest-neighbor competition** (B12–16, B51–66). Exact zero and its nearby neighborhood select VOID even with distances `0` and `0.017320508075688773` below the threshold. Its stock explanation falsely says the bound was exceeded. B60–62 mutate the shared `void_record`; a far residual followed by zero emits current distance `0.0000` alongside stale reason `Distance: 0.7348 > 0.3`. Dictionary values also alias the loaded JSON row objects. This is not an immutable ledger.

B40 and W67/W81/W84 use `zip` without dimension checks. B accepts `[]` and `[0.1]` as “better” at distance zero and ignores an extra billion-valued coordinate. A one-shot residual iterator is consumed by the first distance calculation; later empty distances make “worse” win at zero. W target `[1,99]` and code `[1]` become reconstruction `[1]`, residual `[0]`, claimed error reduction `100`, and early “perfect” exit; an empty code erases every coordinate. Algebraic conservation survives only for well-shaped finite vectors, not this accepted malformed input.

Both accept threshold equality and allow negative/non-finite thresholds. NaN input distances never update B/W's initial infinity, yielding VOID with `inf` rather than a NaN validation error; W also prints NaN rates. NaN thresholds bypass rejection, accepting arbitrarily far codes. Empty books, nonnumeric input, huge finite values, and missing hierarchy keys either fall through to misleading records or raise unhandled `TypeError`, `OverflowError`, or `KeyError`; machine evidence preserves each outcome.

W's missing map emits VOID **while still adding the code** (W80–81). A missing semantic row such as `xlali` uses the VOID explanation while retaining that identifier and a successful reconstruction. VOID therefore conflates threshold rejection, missing map, missing semantic payload, and reserved-zero selection. Its “rate” (W87–89) is a discrete **L1-error decrease**, not a reconstruction derivative; it may be negative. The initial zero-target case is not checked before a code is added, so error can increase from zero.

B's `codebook_path` is entirely unused; a nonexistent path loads the same three hardcoded vectors. Argmin is deterministic **conditional on** codebook, order, metric, floats, mapping, thresholds, and valid input. The full bridge is not parameter-free (N31/N481), and neither script trains a model or implements nested dropout. Calling a threshold a nested-dropout bound does not establish that relationship.

## 5. Additional Kimi toy: a stronger but bounded numerical witness

K imports only stdlib modules (K27–31); no numpy is required. Two seed-0 CLI replays reproduced **every saved numerical value and verdict exactly**, excluding only `runtime_s` and `claims[].ts`. The stable audit-added SHA-256 is `abd2944bb6019e6c7adeb524a6d9bb02d1240f1ce12cd7ba95a21b7aaa38f6c4`. Full JSON is **not** byte-identical because those five timing fields change. Saved runtime is `6.334677457809448` seconds; this sandbox measured approximately `11.41` and `11.56` seconds. Runtime is hardware-dependent.

The saved timestamp `1794928666.2079706` converts to **2026-11-17 15:17:46.207971 UTC**. It is a wall-clock start timestamp shared by all claims (K213/K231), not proof of authorship or integrity. Provenance labels are filename strings only; saved output contains no source/codebook hash or actual codebooks/source vectors. Audit-added hashes are explicitly distinguished from supplied labels.

What reproduces: held-out first-level residual-energy fraction `0.24838060886903807`, final residual fraction `0.07661369632660063`, worst relative energy-identity defect `1.5036325501281391`, and 985 distinct code paths out of 1000. Recalculated verdicts match all four recorded verdicts. Independent traversal counted **zero finite held-out over-threshold snaps**; rejection contributes zero and passes the residual to the next level. Reconstruction-plus-residual bookkeeping error was at most `1.1102230246251565e-16`; the energy-defect/cross-term identity differed by at most `1.1546319456101628e-14`.

Important corrections to the accompanying narrative, kept beside the untouched original:

1. **Wrong denominator:** E87–88/E173's held-out captured fractions `[0.378,0.050,0.022,0.013]` divide held-out energy by **training** signal energy. Correct same-split fractions are `[0.770096,0.101219,0.044466,0.026634]`; level one directly contributes about **77.01%**, not 37.8%.
2. **Collision wording:** K190's `1 - distinct_paths/n = 1.5%` is the redundant-sample fraction beyond one representative per path. It is not the proportion sharing a path (E159–163). Independently, nine pairs and one seven-member path contain **25/1000 = 2.5%** of samples. K's per-level census (K175/K182–188) compares unique original inputs, not code occupancy; its zero result is acknowledged as degenerate, not a valid per-level VQ collision measurement.
3. **Calibration is not exact target enforcement:** K109's rank plus strict `>` yields 0.95% on each unconditional calibration residual set. K110 advances even would-be rejected residuals; actual gated training rates are 0.95%, 1.1%, 1.2%, 1.3%, as saved. Later bounds are calibrated on different residual trajectories than gated encoding.
4. **Structural versus measured:** K257–268 hardcodes the integrity claim's `measured=0.0`; it does not count violations. The independent audit found zero for this finite dataset, but the saved structural pass alone is not an instrumented census.

Validation limits remain (K57–60/K84/K116–138): NaN inputs choose a real first code, NaN thresholds disable rejection, extra dimensions vanish, missing thresholds silently skip levels, empty input chooses a real code, and negative decode indices select Python's last code. The global reserved index `CODES=16` correctly avoids competing with the real sixteen codes **in the main configuration**; however a seventeen-code fixture legitimately encodes real index 16 and then decodes it as VOID. Empty/zero-energy measurement divides by zero; no-level measurement, ragged training, and target VOID rate zero fail with unhandled exceptions. Configuration globals constrain what the reusable functions can safely accept.

This is synthetic Gaussian RVQ with trained codebooks and threshold calibration, **not** NCM or a nested-dropout-trained network. Only first-level standalone reconstruction is assessed, not every level's standalone semantic meaning. K never loads the supplied semantic JSON, emits no Lojban or COBOL, and handles no missing semantic mappings. Energy norms and verdicts are measurements, but rate labels do not make these ratios derivatives. The expansion-math document concerns other instruments and was read only for context; its computations were not reproduced here.

## 6. What survives; what stays unresolved

**Survives:** the originals demonstrate finite, equal-dimension nearest-neighbor selection, deterministic tie handling, an explicit over-distance fallback, and sequential residual bookkeeping. The supplied semantic data retains distinctions the adapters lose. Kimi adds a reproducible stdlib trained RVQ toy, a correctly non-competing reserved escape in its fixed configuration, held-out numerical checks, and an explicit negative energy-identity result. These are useful experimental witnesses when accompanied by their apertures and failures.

**Not established:** schema-compatible COBOL ingestion, exact decimal or byte semantics, immutability, production validation, semantic validity of learned codes, actual nested dropout, real neural-model behavior, physical power conjugacy, cryptographic provenance, bitrate/speedup claims, or repository integration. The finite tests do not universally disprove every possible design; they falsify the stated behavior of these particular received snippets and numerical examples. No corrected runtime, real model, claim-table rewrite, database pipeline, or new physical bridge was built.
