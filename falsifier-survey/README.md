# falsifier-survey

Filed 2026-09-05; instructions pending. Nothing here has been audited,
re-run or edited. This README is the only file in the folder not from the
drop or derived from it by the filter stated below.

## Where this came from

A two-run falsifier survey arrived as one zip and was first filed whole in
`JinnZ2/Simulators` (commit `5e81b9d`, `falsifier-survey/`). Run 1 covered
Simulators. **Run 2 covered this repository and `Geometric-manifold-` in one report
and one cell file.** This folder is the Geometric-to-Binary-Computational-Bridge share of Run 2, split out by
the `repo` field every Run 2 record carries (`g2b`). The combined
delivered files are recoverable at that Simulators commit; their hashes are
below so the split can be checked.

## Contents

```
falsifier_survey_report_run2.md   VERBATIM. Covers both repos; the same
                                  bytes sit in Geometric-manifold-/falsifier-survey/.
                                  sha256 981631c6487405d54337e52568e2f5e3c2a7fbeeaaf3c87ac3c1d7aa825ea0aa
cell_records.jsonl                DERIVED: rows of the delivered
                                  cell_records_run2.jsonl with repo == "g2b"
                                  (514 of 623). Row content untouched.
cell_records.csv                  DERIVED: same filter on the delivered CSV
                                  (514 of 623), header kept.
survey2/folders_g2b.json        VERBATIM. Survey units (30).
survey2/raw_hits_g2b.jsonl      VERBATIM. Extraction mention list.
survey2/scope_different_cells.json  DERIVED: entries with repo == "g2b"
                                  (18 of 19) from the delivered
                                  scope_different_cells_run2.json.
survey2/batches2/                 VERBATIM. This repo's coder batch(es)
                                  (g2b_a, g2b_b) and the hit slice each
                                  coder received; assign.json (all three
                                  batches, both repos) and validate2.py
                                  (both repos, absolute /mnt/agents paths)
                                  are the delivered combined files, unedited.
```

Delivered combined sources (sha256):

```
cell_records_run2.jsonl              75c0cf47af38cee7ee236026ece9c3893448564cbd77b2c8c86434a92043abbb
cell_records_run2.csv                af7bf34142c6b9afe9f739aeae3646bb77230fa80a37915b6d155a5179f38575
scope_different_cells_run2.json      52092b02ac17863ffd7ce42f63578b18a6a750d0e2da402702fc323429eb296f
batches2/assign.json                 dd6980064d88df0530e6a900721bf4d115954a13017b712af66c7590cf7ca5f3
validate2.py                         821c425d95eecb42aec4562655644beb3a101657ce84b09ba17fb9d88772b937
plan.md (kept in Simulators)         b4d652437a793660af3bef0d4279029830fd931b3b10e4c722752defdfe67768
```

## Counts for this repo, as delivered

514 cells: MEASURED 440, MISSING 7, SCOPE-DIFFERENT 18, UNKNOWN 49.
The report's own per-repo line is the authority; this line is the filter's
count and should match it.

## Provenance notes, not findings

- Seven unit names occur in both repos (`docs`, `atlas`, `experiments`,
  `tests`, `scripts`, `bridges`, `(repo root)`), so the split keys on the
  `repo` field and never on the unit name.
- The report dates its run 2026-09-05 against a fresh clone of HEAD and
  records no commit.
- Run 2 includes `docs/` as a survey unit; Run 1 excluded it.
- Coding was from reading, not execution, per the Run 1 report's own
  limitations section; Run 2 states an identical protocol.
