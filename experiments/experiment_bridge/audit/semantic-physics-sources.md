# Semantic and physical analogy audit — source working file

Author: Manus AI. Audit date: 2026-11-17.

## Local corpus evidence

Root: `/home/ubuntu/Geometric-to-Binary-Computational-Bridge`.

- Required guides read: `READ_ME_THIS_WAY.md` and `READING_PROTOCOL.md`. Mismatches are specimens; preserve originals and separate found, out of scope, unresolved.
- `experiments/experiment_bridge/raw/lojban_wordslot_reference.json`: data instance with `place_structures` and `evidentials` arrays, not an explicit validation contract. The field `gismu` includes cmavo such as `za'a` and lujvo such as `xagrai`; preserve original spelling but interpret as valsi identifier.
- Repeated values are purposeful records: `zmadu` in superior/more/greater/recall-check rows; `snura` in safe and recall-check rows; `jibni` in near and recall-check rows; `xagrai` in best and optimal with distinct quoted structures; `le'onmo` in hostile/aggressive.
- `structure_status=OBSERVED` and `mapping_status=PROPOSED` on lexical mapping rows distinguish source capture from English-concept assignment. Recall-check rows use `mapping_status=DIFFERS` and include `recalled_form`.
- Null identifiers and null structures occur with `VOID` on efficient, cold in the emotive class, imminent. Their reasons record asserted lookup gaps, not demonstrated global absence in the language.
- `working_notes.txt` lines 29–31: reconstruction/residual as conjugate pair, conserved by construction; deterministic argmin called exact-ratio coupler. Lines 180–198: VOID as insulator; ju'a called performative; ru'a called postulated gap. Lines 391 and 538: dictionary keyed solely by `gismu`, causing last-row overwrite of repeated identifiers. Lines 604–614: threshold rejection makes no update; accepted code with absent semantic mapping can still update reconstruction and emit VOID. Lines 616–619: rate is difference of L1 errors, not vector reconstruction derivative. No code was executed.
- `BRIDGE_GLOSSARY.md` lines 35–45: physical R/TF/GY terminology; TF power preservation. Lines 69–71: internal exact/soft/composite ratio taxonomy by physical parameter count.
- `fabrication/substrate_ir.py`: names arbitrary strings at `BondPort`; open element kind registry and domain strings do not enforce power conjugacy. Original Domain literal lists seven physical substrate labels; geometry catalogue has no contextual entry.
- `bridge_protocol.yaml` is prose-like protocol text, not a contextual-substrate schema; existing labels do not register a new contextual modality or OBSERVED/PROPOSED/VOID semantics.

## Sources read

### CLL §13.11 — primary linguistic source

URL: https://lojban.org/publications/cll/cll_v1.1_xhtml-section-chunks/section-evidentials.html
Retrieved by fetch 2026-11-17; full section returned.

CLL identifies these as cmavo in selma'o UI. Evidentials report the speaker's information/idea source and affect the bridi. ju'a avoids stating a specific basis or covers a basis not otherwise represented; ca'e covers definition and performative utterances. ru'a means an assumption by the speaker, not missingness, rejection, or a gap. za'a is perception/direct observation; ja'o is a conclusion from other information/ideas, not necessarily rigorous; ti'e is relayed information including writing. All eleven supplied evidential descriptions are broadly consistent with the section; this is not a complete dictionary-entry audit. The scalar English headings for ba'a and su'a need the associated cu'i/nai forms, which the mapping reasons already mention.

### JSON Schema core 2020-12 — official specification

URL: https://json-schema.org/draft/2020-12/json-schema-core.html
Retrieved by fetch 2026-11-17; relevant sections returned; full extracted Markdown saved by tool at `/home/ubuntu/upload/json-schema.org_draft_2020-12_json-schema-core.html_2a01b993-0439-4ff7-bd59-a8e18f3bbebd.md`.

§4.3: a schema describes an instance; schemas are objects or booleans. Unknown keywords should be treated as annotations. An object with only unknown properties is an empty schema for assertion purposes. Thus absence of `$schema` alone is NOT the finding: this file has data rows and no standard assertion/applicator contract. A permissive processor might accept the object as an effectively unconstraining schema rather than reject it.

### 20-sim effort and flow — primary software manual

URL: https://www.20sim.com/webhelp/modeling_tutorial_bond_graphs_effortandflow.php
Retrieved by fetch 2026-11-17; complete manual page returned.

Effort and flow are power-conjugated: their product is power. Examples: force times velocity, voltage times current. The manual explicitly distinguishes temperature × entropy flow from the non-power-conjugate pseudothermal temperature × heat flow pair. Names and across/through labels alone cannot establish the required property.

### Oregon State University bond-graph fundamentals — unresolved extraction

URL: https://web.engr.oregonstate.edu/~webbky/ESE330_files/Section%202%20Bond%20Graph%20Fundamentals.pdf
Fetch returned binary-like text, not usable evidence. Do not cite this extraction as supporting equations until a readable source is acquired.

### Two targeted dictionary spot-checks — extraction limitation

URLs:
- https://jbovlaste.lojban.org/dict/xagrai
- https://jbovlaste.lojban.org/dict/snura

Fetch returned the site shell, not definitions. Shell says the application is read-only and points to lensisku.lojban.org. Definitions are not yet verified from these retrievals. This does not prove entries absent. The repeated-record finding is already established from the supplied JSON; external definition verification remains pending.

## Reusable identity derivation

For fixed target z in a declared vector space, initial reconstruction zhat_0 and residual r_0=z-zhat_0, accepted additive contribution a_k (zero on a specifically defined no-update decision): zhat_k=zhat_{k-1}+a_k; r_k=r_{k-1}-a_k. Consequently z=zhat_k+r_k and delta zhat_k=-delta r_k. This is algebraic bookkeeping, not a power law. For squared Euclidean residual error, ||r_k||²=||r_{k-1}||²-2<r_{k-1},a_k>+||a_k||², so monotone reduction requires a separate condition. Store error norm, coordinate space, distance metric, codebook identity, threshold, decision, semantic assignment and reason separately. No model-specific paper claims are verified here.

## Resolved targeted retrievals

Browser navigation and read-only DOM extraction recovered the two selected dictionary pages. No records were edited. Three target definition texts were checked in total: two xagrai definitions and one snura definition; no other dictionary definitions were substantively audited.

### xagrai

URL: https://jbovlaste.lojban.org/dict/xagrai
Browser/DOM retrieval 2026-11-17. Type is `lujvo`. English Definition #18579 is `t1=x1 is the best among set/range t4 for x2 by standard x3.` English Definition #18042 is `t1=x1 is optimal in property t2 of extremity t3 among range t4.` Both match the supplied JSON texts exactly. Different authors and definition IDs show why word URL alone does not identify the source sense. No claim that these exhaust the page's definitions or establish a unique canonical sense. Read-only browser output: `/home/ubuntu/console_outputs/exec_result_2026-11-17_15-33-05_357.txt`.

### snura

URL: https://jbovlaste.lojban.org/dict/snura
Browser/DOM retrieval 2026-11-17. Type is `gismu`; English Definition #1 attributed to officialdata: `x1 is secure/safe from threat x2 (event).` Matches both supplied source-text rows. The recalled form omits the `(event)` qualifier. Same place count does not demonstrate semantic equivalence; DIFFERS captures a textual discrepancy but supplies no semantic severity score. Read-only browser output: `/home/ubuntu/console_outputs/exec_result_2026-11-17_15-33-31_352.txt`.

### 20-sim transformers and gyrators

URL: https://www.20sim.com/webhelp/modeling_tutorial_bond_graphs_transformersandgyrators.php
Fetch retrieved full page 2026-11-17. Describes ideal energy conversion; readable effort-in TF equations are `f1=(1/n)f2` and `e2=(1/n)e1`, hence `e1=n e2`, `f2=n f1` and `e1 f1=e2 f2` with consistent orientation. The other causality block has an apparent displayed transcription/typographical defect `f2=n f2`; do not use that block as evidence. The valid effort-in block is sufficient. An ideal TF has a ratio/modulus; number of fitted parameters is not its physical defining property.

### 20-sim resistance

URL: https://www.20sim.com/webhelp/modeling_tutorial_bond_graphs_resistance.php
Fetch retrieved full page 2026-11-17. R dissipates free energy irreversibly toward the thermal domain. Constitutive equations `f=e/R`, `e=Rf`; for passive positive R, `P=ef=Rf²` is nonnegative. Collision counts, lost semantic distinctions, null fields, and rejection flags do not specify a power port or thermal transfer.

## Final audit boundaries

No git commands, repository edits, corrected implementation, Python/shell code execution, or NCM-paper research were performed. Browser JavaScript was limited to read-only extraction of the two selected dictionary pages. Only the final audit and this working file were intentionally written under `/home/ubuntu/audit_work`; source tools also generated normal browser/extraction artifacts. Scoped VOID was not tested against every dictionary or against Lojban's productive word/phrase formation. The findings concern the supplied instance and analogy claims, not complete linguistic correctness or empirical model performance.

## Incremental Kimi archive reading

Parent supplied an additional untouched archive during the task. Read only:
- `/home/ubuntu/Geometric-to-Binary-Computational-Bridge/experiments/experiment_bridge/evidence/kimi_as_received/contextual_substrate_entry.md`
- `/home/ubuntu/Geometric-to-Binary-Computational-Bridge/experiments/experiment_bridge/evidence/kimi_as_received/expansion_curiosites.md`

The archived JSON is reported semantically identical to the supplied raw instance and was not independently re-audited. No code or numerical outputs were replayed. Parent handoff says the NCM research agent confirmed actual Next-Concept Modeling arXiv 2610.14162, nested dropout uses cumulative prefixes and supplies no distance threshold; no independent NCM research was performed here. The final Kimi verdict instead rests directly on its entry's explicit toy-RVQ threshold calibration and does not present parent findings as independently verified sources.

Corrections already in Kimi: explicit bookkeeping/not-power qualifier, VQ not exact-ratio, reserved index rather than physical insulator language, structural routing-zero label, toy synthetic scope, real-codec transfer withheld, bit-rate unmeasured, intra-substrate versus cross-substrate separation.

Remaining interpretations:
- Lines 28–33/claim 2 incorrectly characterize the orthogonal squared-norm split as required for physical power. Missing cross term checks orthogonality, not P=e f. Exact identity includes 2<zhat,r>. Orthogonality neither necessary for general coupled physical energy expressions nor sufficient for latent coordinates to be power ports.
- Claim that every existing repository pair multiplies to power is false for its pseudothermal-like temperature-difference × heat-flow pair; 20-sim primary manual explicitly documents the distinction.
- Argmin in resistance column and composite-coupler local taxonomy must remain nonphysical labels. Power-reading VOID is a model-interpretation status, not the same VOID as lexical gap or reserved numerical rejection.
- 1-distinct_paths/n is excess duplicate count fraction, not generally fraction of all samples that share a path. Do not verify or recalculate the supplied toy numbers; code agent owns numerical replay.
- `rate_var` derivative labels do not describe measurements that are ratios or worst-case defects.
- expansion_curiosites.md uses finite-range OBSERVED / beyond-range PROPOSED / scoped no-match responsibly; its claimed exact computations are not new evidence for a power bond or neural-model transfer. Mathematical results and external theorem matches were not researched or replayed in this audit.
