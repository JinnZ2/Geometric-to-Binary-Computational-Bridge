# Experiment bridge

**This is an audited experimental notebook and synthetic test bench, not a new physical substrate or a working NCM–Lojban–COBOL integration.** Note 2026-11-17: raw notes are preserved beside their corrections under [READ_ME_THIS_WAY.md](../../READ_ME_THIS_WAY.md) and [READING_PROTOCOL.md](../../READING_PROTOCOL.md). Errors remain data. No received specimen has been repaired in place.

## Start here

[AUDIT.md](AUDIT.md) separates what is usable from what remains unsupported. [CLAIM_TABLE.md](CLAIM_TABLE.md) records bounded findings and their refuters. [RESEARCH_GAPS.md](RESEARCH_GAPS.md) names the missing measurements and contracts; [SCOPE_BOUNDARY.md](SCOPE_BOUNDARY.md) limits interpretation.

The useful core is explicit rejection, reconstruction/residual bookkeeping, and a reproducible synthetic residual vector quantization experiment. The original COBOL generator and purported NCM adapters are retained as correction specimens, not promoted to production.

## Original material

`raw/working_notes.txt` and `raw/lojban_wordslot_reference.json` are byte-for-byte copies of the two supplied text attachments. `raw/kimi_notes.zip` preserves the additional archive. [raw/manifest.json](raw/manifest.json) records original filenames, sizes, SHA-256 hashes, the repository base commit, and archive-member hashes. Hashes identify received bytes; they do not authenticate the source quotations or model authorship.

`evidence/*_as_received.py` contains the three Python fence bodies extracted from the original notes without code changes. `evidence/kimi_as_received/` preserves all five Kimi archive members, including the misspelled `expansion_curiosites.md`. The two semantic JSON instances are equal as data; both remain available. That separate exact-inflation mathematics note is retained but not audited here.

The supplied semantic reference contains 30 place-structure rows and 11 evidential rows. It is a data instance, not a meaningful JSON Schema validation contract. Preserve its repeated word identifiers, scoped gaps, recall checks, and proposed mappings.

## Reproduce without overwriting incoming evidence

Run these commands from the repository root:

```sh
python tests/test_experiment_bridge.py
python experiments/experiment_bridge/evidence/reproduce_originals.py --skip-compiler --output /tmp/experiment-bridge-originals.json --artifacts-dir /tmp/experiment-bridge-compiler
python experiments/experiment_bridge/evidence/reproduce_kimi.py --output /tmp/experiment-bridge-kimi.json
```

The two audit harnesses use only Python's standard library and execute unchanged specimens in temporary directories. The originals harness can additionally use GnuCOBOL (`cobc`) if `--skip-compiler` is omitted. Compiler evidence from the audit session is retained under `evidence/original_compiler/`; it includes the failed generated copybook and isolated language probes, not executable binaries.

Passing an audit assertion means the finding reproduced, including defects. It does not mean the incoming implementation passed validation. Do not run the received generator or toy directly inside their evidence directories: they overwrite copybook or seed-named output files. Reproduction harness defaults also replace audit-generated JSON; the commands above keep fresh results separate from the committed snapshot.

## Detailed evidence

Read the [code audit](audit/code-audit.md), [NCM primary-source audit](audit/ncm-audit.md), and [semantic/physics audit](audit/semantic-physics-audit.md) for exact references and findings. `evidence/original_reproduction.json` holds the original-snippet cases; `evidence/kimi_reproduction.json` holds two replay comparisons, an independently recomputed census, and edge cases.

This folder is deliberately not registered in `fabrication/substrate_ir.py`, `bridge_protocol.yaml`, or the root claim tables. Its local results must not be silently inherited by real neural models or physical bridges.

## Subsequent expansion — checked v1

Note 2026-11-17, after the original audit: [v1/](v1/README.md) adds a separate checked numerical kernel, lossless role-aware semantic reference view, strict JSON byte envelope, and actual COBOL transport demonstration. It has 95 passing experiment tests, including deliberate broken/corrupt controls. This is a bounded software implementation; the original specimens and findings remain unchanged. Neural semantic validity, exact-decimal metrology and physical power conjugacy are not claimed.

## Subsequent adversarial pass

Note 2026-11-17, after v1: [adversarial/README.md](adversarial/README.md) records reproduced numerical, semantic-validation, resource-ingestion and output-preservation breakages. [v1_1](v1_1/README.md) contains separate candidate fixes and externally context-checked decoding. The retained v1 modules, contract and runs remain unchanged. The final 213-case experiment execution passes, including legacy/inherited compatibility cases; it is not an exhaustive attack count or a security/semantic certification. Trust limits and unimplemented protections stay explicit.

## Subsequent simulation — planted semantics

Note 2026-11-17, after v1.1: [sim/](sim/README.md) plants a synthetic truth, encodes it with the unchanged v1.1 kernel and tests majority assignment of code paths against permuted-label, majority-label and random-codebook comparisons, with a planted fault that must read as confused. It is synthetic only: no neural model was run and the "Semantic assignment" gap stays NOT_STUDIED. The retained specimens, v1 and v1.1 are unchanged.

## Subsequent reusable checks

Note 2026-11-17, after the audit: two harnesses under `evidence/` turn findings the audit already holds into checks that can be run again. Both run unchanged specimens on copies in a temporary directory and refuse to overwrite an existing output file.

```sh
python experiments/experiment_bridge/evidence/printed_vs_executed.py --check experiments/experiment_bridge/evidence/printed_vs_executed.json
python tests/test_experiment_bridge_tools.py
```

`printed_vs_executed.py` (T1) reads the two blocks of output printed in `raw/working_notes.txt`, runs the two as-received scripts and diffs them. Snapshot: `evidence/printed_vs_executed.json`. Both differ: the bridge prints distances 0.0608 and 0.6782 where execution gives 0.0574 and 0.7348, and the level walk prints two accepted levels where execution gives three VOIDs. These are the numbers in the [code audit](audit/code-audit.md); the speaker label in the notes is as supplied and is not authenticated.

`claim_tools.py` takes a received claim-emitting script and records three things: a two-run replay with claims compared by scope, every claim whose `measured` value is a literal in the source (flagged STRUCTURAL, with the probe that backs it when one is named), and the stated reason for each tolerance (UNSOURCED when the source gives none). Run on the round-1 Kimi toy, snapshot `evidence/kimi_round1_claim_tools.json`: 4 of 4 claims equal on both comparisons; `void_escape_integrity` is STRUCTURAL (measured is the literal `0.0`), backed by the independent census in `evidence/kimi_reproduction.json`; all four tolerances are UNSOURCED in the source.

## Subsequent specimens — Kimi round 2

Note 2026-11-17, after the reusable checks: `evidence/kimi_round2_as_received/` holds seven files as received (three scripts, their seed-0 records, the revised entry with its errata and addendum), with sha256 in `MANIFEST.json`. The manifest also accounts for the four archive members that are byte-identical to round 1 and for the files attached separately; the archive itself is not committed.

```sh
python experiments/experiment_bridge/evidence/reproduce_kimi_round2.py --output /tmp/experiment-bridge-kimi-round2.json
```

Snapshot: `evidence/kimi_round2_reproduction.json`.

- **Replay.** 21 claims across the three scripts; 21 of 21 equal between the saved records and a replay, and 21 of 21 between two replays, with only `claims[].ts` left out. Verdicts as recorded: 17 pass, 3 fail, 1 void.
- **STRUCTURAL.** `void_escape_integrity` reports `measured = 0.0` as a literal in both RVQ scripts (`toy_rvq_void_v2.py` line 458, `toy_rvq_orthogonal.py` line 351). The probe the v2 claim names, `seventeenth_real_code_roundtrips`, covers the index-collision failure only. What backs the count is the replay harness's own recount: 4,000 held-out levels per script, 0 accepted over threshold, 0 rejected within it, at seed 0 in the declared configuration.
- **Tolerance provenance.** All 21 rows are in the snapshot. No tolerance has a reason in a source comment. Three have a reason in the claim's own text, read by hand and checked to be present (`projection_dominance`, both `adaptive_refresh_bound`). The other 18 are UNSOURCED; three of those state a band without saying why.
- **Claim table.** The snapshot findings are EBR_016 to EBR_019 in [CLAIM_TABLE.md](CLAIM_TABLE.md).

These are synthetic toys. The entry's addendum reads the orthogonal variant as pricing a power-conjugate reading; that interpretation is the entry's and is not adopted here (see [SCOPE_BOUNDARY.md](SCOPE_BOUNDARY.md)). The addendum is dated 2026-11-18 inside a file received on 2026-11-17; the date is kept as received.

## Subsequent specimen and additions — equation_search

Note 2026-11-17, after Kimi round 2: `evidence/equation_search_as_received/` holds `equation_search.py` as received (pasted as text; cut from the session transcript by program, not retyped; no record came with it). [eqsearch/](eqsearch/README.md) adds, beside it and without editing it, a round 2 (two more F3 branches, nulls for F2, F3 and F4, an F4 noise sweep, a tolerance source per claim, seeds 0 to 9) and an exact tier that recovers the Lorenz Euler step map in rationals. Thresholds were committed in `eqsearch/DECLARED.json` before any run. Generated data only; nothing is promoted.

