# Semantic routing adversarial replay

**Note 2026-11-17:** These findings add a correction specimen alongside immutable `v1`; they do not rewrite raw sources, as-received evidence, earlier findings, linguistic wording, or recorded status markers. Candidate fixes live only in `v1_1/semantics.py`. Read this with `READ_ME_THIS_WAY.md` and the existing v1 contract.

The tested objects are deterministic **ILLUSTRATIVE software fixtures**, not empirical linguistic data, actual neural-code observations, or evidence of physical/semantic validity. The recorded baseline is the exact legacy module loaded from disk, not a rewritten imitation. Its SHA-256 is `f3d892b2aa2dcaee77282e55b1358def46154c446999d125a6d35eb5e3b23c98`. The replay records candidate source hashes separately.

## Actual pre/post findings

`semantics_results.json` preserves the first legacy execution alongside candidate replay results. Each phase has 16 named probes. Times are single-run observations, not benchmarks or worst-case guarantees.

| Finding | Actual legacy outcome | Candidate outcome | Classification and falsifier |
|---|---|---|---|
| Cyclic unknown source extension | `RecursionError` | `ValueError` before hashing/deep copying | Actual validation defect. Falsified if the candidate cycle escapes as recursion failure or is accepted. |
| 1,200-level unknown source extension | `RecursionError` | Depth-policy `ValueError` | Actual validation defect. Falsified by acceptance or recursion failure. |
| 65,537-character extension / 100,001-element extension | Accepted both | String/node-policy `ValueError` | Newly declared bounded-resource policy, not a claim that large text is linguistically invalid. Falsified if either exceeds its declared input bound without rejection. |
| 4,000-digit occurrence suffix | `find_rows` accepted | `ValueError` before integer conversion | Actual missing occurrence constraint; avoid attributing an unmeasured denial-of-service magnitude to this small replay. Falsified by acceptance or unbounded integer parsing. |
| Repeated identical normalized `row_id` | `find_rows` accepted | `find_rows` and `annotate_trace` reject | Actual inconsistent shared validation. Legacy `annotate_trace` already rejected duplicate IDs; no claim that this was missing there. |
| Two rows claiming one collection/index position | Accepted | `ValueError` | Actual contradiction: no normalized source array can have both rows at the same slot. Falsified by accepting the fixture. |
| Occurrence 2 at source index 0 | Accepted | `ValueError` | Actual impossible occurrence metadata. Falsified by accepting the fixture. |
| Reversed occurrence metadata for identical source rows | Accepted | `ValueError` | Actual original-order contradiction, not a prohibition on reordering the returned list. Additional tests exercise order and occurrence-gap checks separately. |
| Transported `semantic_row` replaced while provenance reference hash stays unchanged | Hash stayed unchanged; no legacy consumer checker | `validate_annotation` returns a row-mismatch error | Demonstrated consumer-validation gap, not a broken promise of upstream authentication. Falsified if the checker returns no errors against the unchanged external rows/assignments. |

The forged-row probe's candidate `outcome: accepted` means that the probe successfully returned its result object. Its nested `detail.errors` contains the rejection finding; it does **not** mean the forged annotation passed validation.

## Narrow candidate changes

JSON validation walks an explicit stack with an active-container set, so cycles are rejected without recursive validation. Shared acyclic objects remain valid; repeated aliases count by their expanded JSON representation. Object keys must be strings; unsupported objects, non-finite numbers, oversize integers and excessive depth/text/nodes are rejected. Source extensions remain lossless within these software limits.

The declared constants are:

| Public constant | Value / behavior |
|---|---|
| `SEMANTIC_VERSION` | `experiment-bridge/v1.1` |
| `MAX_JSON_DEPTH` | 32; root depth 0 |
| `MAX_JSON_NODES` | 100,000 expanded values and object keys |
| `MAX_JSON_STRING_CHARS` | 65,536 Unicode characters per key/string |
| `MAX_JSON_TEXT_CHARS` | 1,000,000 aggregate key/string characters |
| `MAX_JSON_INTEGER_BITS` | 1,024 bits; bool remains distinct from integer |
| `MAX_REFERENCE_ROWS` | 4,096 total reference/normalized rows; source indexes in `[0, 4096)` |
| `MAX_ROW_OCCURRENCE` | 4,096; positive canonical ASCII decimal, at most four digits |
| `SEMANTIC_STEP_FIELDS` | `semantic_status`, `semantic_row_id`, `semantic_row` |
| `SEMANTIC_TOP_FIELDS` | `semantic_provenance`, `evidential` |

Limits are conjunctive: meeting the row cap does not waive the expanded-node or text cap. The occurrence parser checks suffix length before `int`. All normalized-row consumers enforce unique IDs and unique `(source_collection, source_index)` positions. An occurrence cannot exceed `source_index + 1`; for equal role/source identities, increasing source positions require increasing occurrences, and occurrence differences cannot exceed position differences.

Crucially, checks do **not** demand contiguous positions, contiguous occurrences, collection ordering, or normalized-list ordering. A filtered/reordered subset with existing source indexes remains valid, including a lone second duplicate occurrence originally at index 30. Stable IDs remain independent of unrelated row/key reordering.

## Consumer API and integration boundary

```python
validate_annotation(annotated_trace, rows, assignments=None,
                    evidential_row_id=None) -> list[str]
```

An empty list means consistency with the caller's **externally supplied trusted routing inputs**. Malformed inputs or disagreements return named error strings, without mutating any input. The checker never derives trusted rows, assignments or evidential selection from payload provenance. Omitted assignments mean an empty trusted mapping, not “trust the record's assignments.” Omitted evidential selection means no selected evidential.

The checker removes only the reserved semantic output fields from a new temporary trace view, reconstructs expected annotations using checked external rows/assignments, and compares all semantic output fields using canonical JSON digests. This also distinguishes JSON booleans from integer values (`False` is not interchangeable with source index 0). The full copied row, provenance version/reference hash/assignment list/evidential ID, per-step ID/status and selected evidential are checked. Missing output fields fail even when the expected value is null.

This is a separately callable **consumer consistency check**, not an independently implemented proof of the producer's routing rules: it intentionally reuses `annotate_trace`. Numerical checking must happen in the numerical module or the parent's checked-decode path before calling this checker. No original numerical trace or checkpoint is authenticated by this function.

## Compatibility and executed tests

The supplied raw reference still normalizes to exactly 41 rows, identical to legacy rows including every entire `source` dictionary, source index and `row_id`: 25 mapping, 5 recall-check and 11 evidential rows. For the explicit mixed-status trace fixture, the complete annotation is identical to legacy except the semantic provenance version string. Numerical trace fields are copied unchanged. Unknown source fields remain retained and identity-sensitive.

Executed from the repository root:

```sh
python experiments/experiment_bridge/adversarial/semantics_probe.py --phase legacy
python experiments/experiment_bridge/adversarial/semantics_probe.py --phase candidate
python tests/test_experiment_bridge_adversarial_semantics.py
python tests/test_experiment_bridge_semantics.py
ruff check experiments/experiment_bridge/v1_1/semantics.py \
  experiments/experiment_bridge/adversarial/semantics_probe.py \
  tests/test_experiment_bridge_adversarial_semantics.py
```

**Results:** 25 candidate adversarial tests passed; 19 unchanged legacy semantic tests passed; scoped Ruff passed. Additionally, all 19 existing semantic contract tests passed against the candidate by substituting only the semantic import and expected provenance version in memory; the existing test file was not edited.

The candidate replay and regression suite each executed 128 deterministic structured annotation mutations, seed `20261117`. All 128 were detected, all 128 supplied mutated inputs remained unchanged, and the honest fixture had no validation errors. Recorded field coverage is 27 status, 38 row-ID, 43 copied-row, 13 provenance and 7 evidential mutations. These are deliberately invalid deletion/replacement fixtures, not exhaustive fuzzing and not estimates of attack success rates.

The candidate replay checks the saved legacy module hash before retaining and extending the pre-fix record. Replaying `--phase candidate` updates only the candidate section; intentionally rerunning `--phase legacy` creates a fresh baseline file, so archive the existing result first if timing history matters. No raw/evidence/v1 differences were introduced by this work.

## Intentional trust limits and remaining gaps

**Found but not a defect:** changing or adding a source field changes its content identity while preserving that supplied field. Both versions accept this. A digest is not a signature, proof of source retrieval, linguistic correctness or checkpoint origin. A forged but internally coherent external reference can still be normalized and routed. A lone row claiming source index 99 remains accepted if nothing supplied contradicts it; only comparison with an independently trusted source/reference can establish the original position.

**Out of this module's scope:** minimal numerical traces remain accepted. Even an accepted step carrying an over-threshold distance is accepted by semantic annotation and semantic validation, because numerical transitions are owned by core. This is the deliberate contract boundary, not an additional semantic vulnerability or an excuse to omit core checking in an integrated path. `PRESENT`, `LEXICAL_VOID`, `UNMAPPED` and `NOT_APPLICABLE` remain separate routing states, not judgments of truth or worth.

**Unresolved:** no natural-language semantic truth evaluation, actual model/codebook checkpoint binding, authentic upstream reference acquisition, empirical dataset calibration, or physical bridge evidence is established. The bounded inputs are not a universal adversarial guarantee. Annotation expands copied rows; no global output-byte, wall-clock or process-memory guarantee is added here. The checker rejects inspected JSON graphs exceeding its policy, and common producer/checker implementation errors are still possible. An attacker who also controls the caller's purportedly trusted inputs can regenerate a consistent forged record and pass this consistency check.
