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
