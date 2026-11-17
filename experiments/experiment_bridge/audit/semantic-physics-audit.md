The supplied reference is useful as an evidence-bearing JSON instance. It is not yet a validation schema, a verified semantic ontology, or a physical bond-graph model. The reusable mathematical core is an additive reconstruction/residual identity; the notes overstate what that identity establishes.

## Preserve the schema distinctions and repeated records

The [supplied JSON](../raw/lojban_wordslot_reference.json) contains data arrays, quoted source text, statuses, and reasons. It does not declare standard JSON Schema constraints for types, required fields, status combinations, or record variants. This is not simply a missing `$schema` issue: JSON Schema permits objects containing unknown properties, which can behave as an effectively unconstraining schema. Passing this data object to a permissive schema processor would therefore not establish meaningful validation. [1]

The key `gismu` functions as a **valsi identifier**, not a gismu-only field. CLL identifies the evidentials as cmavo in selma'o UI, while the spot-checked `xagrai` entry identifies itself as a lujvo. [2] [3] Preserve the original key as experimental data, but consumers must not infer word type from its name. Similarly, `place_structure_verbatim` holds predicate definitions in one array and evidential explanations in another. Those explanations are not numbered predicate-place structures. Quoted text alone does not supply machine-checkable argument types or prove that the English classifications form a formal ontology.

Repeated identifiers are not redundant records. `zmadu` appears as superior, more, greater, and a recall check; `snura` and `jibni` each occur in mapping and recall-check roles. The two `xagrai` rows cite different definitions: “best” is Definition #18579, while “optimal” is Definition #18042, with different place wording and authors. Both supplied texts match their respective source definitions. [3] A word-level URL does not identify which definition was used.

The dictionary comprehensions in [working notes](../raw/working_notes.txt), lines 391 and 538, key records only by `gismu`. By inspection, later rows overwrite earlier rows: a recall check can replace a semantic mapping, and optimal replaces best. This is a structural loss independent of model performance. Reusable bookkeeping needs record identity separate from word identity, plus the record role and source-definition identity; it must preserve the original rows rather than merge them.

`structure_status=OBSERVED` and `mapping_status=PROPOSED` are valuable independent assertions: source wording was reportedly observed, but its assignment to an English concept remains proposed. Neither means that a model output has been semantically verified. `DIFFERS` in recall-check rows describes another task entirely, so consumers need an explicit record-role distinction rather than treating all mapping statuses as one confidence scale. The snura spot-check confirms the source's `(event)` qualifier on the threat argument. Its omission in recall is more than punctuation; unchanged place count does not establish semantic equivalence. [4]

The three null/`VOID` records describe different scoped lookup gaps: efficient, cold in the emotive class, and imminent. Null identifier, absent quotable structure, unresolved mapping, threshold rejection, and missing code-to-word assignment must not silently become the same condition. These records do **not** demonstrate that Lojban globally lacks the concepts. Their lookup scope and rejection reasons should remain attached to the gap. No exhaustive absence claim was verified here. Likewise, `source_url` and `retrieved` provide useful provenance metadata, not the “cryptographic provenance” claimed at notes line 115; the supplied fields contain no integrity hash or signature.

## CLL evidentials do not certify truth or encode missingness

The supplied JSON correctly distinguishes the critical meanings, but the later notes collapse them. CLL §13.11 says `ju'a` avoids stating a specific basis, or covers a basis not represented by another evidential. **`ca'e`, not `ju'a`, covers definition and performative utterances.** Thus notes line 197's “ju'a … performative” is incorrect. Replacing it with ca'e would still not make a ledger's arithmetic empirically true: the linguistic category and the verification operation are different. [2]

CLL defines `ru'a` as an assumption by the speaker. It does not mean “I postulate a gap,” absent evidence, or threshold failure. Notes line 198's equation of VOID with ru'a is therefore unsupported. A threshold failure may be directly observed during an execution; an assumed threshold may instead deserve an assumption annotation. The decision status and the basis for a particular claim belong in separate fields. [2]

`za'a` concerns perception/direct observation; `ti'e` concerns relayed information, including written material; `ja'o` concerns a conclusion from other information or ideas, not necessarily rigorous deduction. These are speaker-relative evidence descriptions, not automatic tags for Optical, COBOL, and NCM, and not a “unified truth table.” Independent measurement protocols and comparable quantities would still be needed for triangulation. [2] This audit checked the CLL evidential semantics and three targeted dictionary definition texts across two words; it does not claim complete linguistic verification of all supplied rows.

## The proposed pair is not power-conjugate

A physical bond pairs effort and flow whose product is power; for vector ports the corresponding pairing is a power-producing inner product. Voltage/current and force/velocity are standard scalar examples. The requirement is dimensional and constitutive, not merely the labels “across” and “through.” [5]

Notes lines 13 and 29 propose different pairs—codebook index/error, then cumulative reconstruction/residual—without establishing either one's power meaning. Reconstruction and residual are coordinates in the same latent vector space. Their sum can equal the target, but no energy function, physical units, time evolution, or port-power interpretation is supplied. A level index is not physical time, and a sequential loop is not by itself a bond-graph topology. In particular, the proposed level walk's `error_reduction` is a difference of L1 residual errors, not its advertised vector reconstruction derivative; its nearest-code distance uses a different, Euclidean metric. These findings are from inspection, not execution.

An ideal transformer has reciprocal port relations, for example `e1 = n e2` and `f2 = n f1`, giving equal input/output power with consistent orientation. [6] Nearest-neighbor argmin instead selects a discrete code under a metric. For a fixed codebook it is deterministic only when ties are resolved, but determinism does not establish a transformer ratio or power preservation. The [glossary](../../../BRIDGE_GLOSSARY.md)'s local “zero free physical parameters” taxonomy cannot supply the missing physical relation. Adding softmax temperature changes a selection rule; it does not establish a physical soft-ratio coupler.

A passive R-element dissipates free energy, with a constitutive relation such as `e = R f` and absorbed power `R f²` for positive R. [7] Code collisions or discarded distinctions quantify information loss, not that power transfer. They may be reported as nonphysical loss metrics, but neither “pseudo-resistance” nor “entropic decay” establishes a physical resistor.

VOID is likewise not an insulator. Notes lines 186–187 say flow stops, while lines 524 and 604–614 say the residual passes unchanged. These are different operational claims. In a physical open-circuit idealization, flow is zero at the relevant port; retaining a nonzero residual for another processing stage is instead a no-update/pass-through decision. Without a power port, neither rejection nor retention establishes insulation or quarantined energy. [5] [7]

## The precise reusable bookkeeping identity

For a fixed target vector `z` in a declared coordinate space, set `r₀ = z − ẑ₀`. At step `k`, let `aₖ` be the accepted additive contribution, with `aₖ = 0` only for a specifically defined no-update decision:

```text
ẑₖ = ẑₖ₋₁ + aₖ
rₖ  = rₖ₋₁ − aₖ
z   = ẑₖ + rₖ
Δẑₖ = −Δrₖ
```

This identity is exact algebraically, subject to the stated numerical representation. It works without physical terminology and does not imply monotone error reduction. For squared Euclidean error,

```text

Whether error decreases therefore needs a separate condition or measurement. The invariant also assumes a fixed target and compatible coordinates; a decoder operating elsewhere needs its own declared relation.

Preserve vectors, accepted contributions, metric, codebook identity, threshold, numerical decision, and semantic assignment separately. In the supplied walk, an accepted numeric code can update reconstruction yet emit VOID because its semantic mapping is absent. That is not the same event as threshold rejection, and VOID alone cannot determine whether `aₖ` was zero. The name “nested-dropout bound” does not itself establish a justified rejection threshold; model-specific threshold claims are outside this audit.

Treat **contextual/semantic bookkeeping as an explicitly experimental, nonphysical namespace**. The [inspected protocol](../../../bridge_protocol.yaml) supplies no contextual registration, and the [substrate IR](../../../fabrication/substrate_ir.py)'s Domain/geometry catalogue supplies no contextual physics. Its open string fields can accommodate new names but do not validate conjugacy. Keep lexical VOID, numerical rejection, and missing semantic assignment distinct there. Physical power, resistance, insulation, and transformer claims remain unestablished until an actual energetic model and measurement chain are supplied.

## Incremental verdict on the Kimi archive

The archived [contextual substrate entry](../evidence/kimi_as_received/contextual_substrate_entry.md) **already corrects substantial Grok/DeepSeek overreach**. It explicitly calls its variables bookkeeping rather than power-conjugate, rejects the exact-ratio classification, declares a synthetic toy RVQ rather than a measured neural codec, and withholds transfer to real codecs, bit-rate claims, and cross-substrate coupling. Its rejection thresholds are explicitly a toy design calibrated to a target training VOID rate, not evidence of an inherited model guarantee. These improvements should not be presented as corrections still owed by Kimi. Its code replay and numerical verdicts were not verified in this audit.

The remaining physical inference is nevertheless wrong. Lines 28–33 and claim 2 say physical power requires the orthogonal split `||z||² = ||ẑ||² + ||r||²`. The unconditional identity is instead

```text

Omitting the cross term tests orthogonality, not the defining effort–flow power relation. Physical coupled systems can have cross terms; conversely, orthogonalizing latent vectors would not create physical units or a power port. Kimi's reported defect therefore rebuts an orthogonal-energy interpretation of that toy split, but does not prove that no possible energetic model can exist. Nor does it prove physical dissipation. The verdict should remain: **no power-conjugate model has been established**, rather than physical impossibility proven by this statistic. [5] [6]

The assertion that every existing repository domain already multiplies to power also needs qualification. The inspected table's temperature-difference × heat-flow pair is not power-conjugate; the 20-sim manual explicitly distinguishes pseudothermal temperature × heat flow from temperature × entropy flow. [5] The contextual row still places argmin under “Resistance” despite its nonphysical qualifier. Calling its codebook a locally “composite coupler” is permissible experimental naming, not recognition as a physical TF/GY element. “Power reading VOID” here means an unestablished interpretation, distinct from the lexical gaps and reserved rejection symbol.

Kimi's claim 3 usefully labels over-threshold routing as structural. A successful routing census would check an implemented policy, not establish semantic adequacy or a new physical boundary. Claim 4's `1 − distinct_paths/n` counts excess samples beyond one per distinct path; it is not generally the fraction of samples that belong to shared-path groups, as its prose states. Its `rate_var` names also do not turn the reported fractions and worst-case defect into measured derivatives. These are interpretation findings; this audit does not replace the code agent's replay.

The archived [expansion curiosités](../evidence/kimi_as_received/expansion_curiosites.md) already separates finite-range OBSERVED results, PROPOSED extrapolation, and scoped “no match.” That discipline is compatible with preserving scoped VOID rather than claiming universal absence. Its exact-arithmetic and finite geometric identities, even if reproduced, would not independently establish semantic correctness, power conjugacy, or neural-model transfer. No claim in that separate mathematics study was independently researched or replayed here. The archive's semantically identical JSON was not subjected to a duplicate dictionary audit.

*Manus AI · 2026-11-17. Originals preserved under the repository reading protocols. No git operations, repository changes, implementation corrections, experiment executions, or NCM-paper research were performed.*

## References

[1]: https://json-schema.org/draft/2020-12/json-schema-core.html "JSON Schema Core 2020-12, especially section 4.3"
[2]: https://lojban.org/publications/cll/cll_v1.1_xhtml-section-chunks/section-evidentials.html "The Complete Lojban Language, section 13.11 Evidentials"
[3]: https://jbovlaste.lojban.org/dict/xagrai "jbovlaste xagrai, English definitions 18579 and 18042"
[4]: https://jbovlaste.lojban.org/dict/snura "jbovlaste snura, English definition 1"
[5]: https://www.20sim.com/webhelp/modeling_tutorial_bond_graphs_effortandflow.php "20-sim manual, Effort and Flow"
[6]: https://www.20sim.com/webhelp/modeling_tutorial_bond_graphs_transformersandgyrators.php "20-sim manual, Transformers and Gyrators"
[7]: https://www.20sim.com/webhelp/modeling_tutorial_bond_graphs_resistance.php "20-sim manual, Resistance"
