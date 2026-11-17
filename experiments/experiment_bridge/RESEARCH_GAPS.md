# Experiment bridge research gaps

These are requirements that would change the audit disposition, not a request to implement them automatically. Note 2026-11-17: no revised runtime was built.

## Representation contract — INSTRUMENTAL

**Gap / knowledge state:** UNDER_STUDY. The semantic data exists, but no validated record-role schema and compatible COBOL writer/reader contract exists. The original generator and adapters disagree on field order, widths, encoding, and null handling.

**Research question:** Can a declared encoding and versioned record contract preserve all reference rows and distinguish numerical rejection from lexical gaps without silent truncation?

**Data sources:** the supplied reference, compiler diagnostics, apostrophe/Unicode/duplicate-key/overflow fixtures in the replay evidence.

**Method:** assign stable row identities while preserving original identifiers; declare roles, encoding and byte widths; reject overflows and non-finite numerics explicitly; generate escaped valid source and exercise a COBOL round trip. If fixed-point values are introduced, specify scale, rounding policy, overflow behavior and loss bounds rather than claiming representation is universally exact.

**Expected deliverable:** a separately versioned adapter and validation schema with loss-aware serialization tests.

**Falsifier:** any undeclared truncation, merged role, wrong status, byte-offset mismatch or numeric loss in those round-trip fixtures.

**What it opens:** a tested representation boundary; not semantic or neural-model validity by itself.

## Rejection calibration — METHODOLOGICAL

**Gap / knowledge state:** UNDER_STUDY. Kimi's thresholds use ungated training residuals, while inference follows gated residuals. Original thresholds are illustrative, not inherited dropout bounds.

**Research question:** How do rejection and distortion change when later thresholds are calibrated on the actual gated trajectory, across independent seeds and shifted input distributions?

**Data sources:** synthetic train/held-out vectors regenerated from the pinned toy, then an explicitly identified real model/dataset if transfer is attempted.

**Method:** specify squared versus unsquared metric and normalization; calibrate without consuming held-out data; record per-level rejection and residual distortion; compare gated calibration with the received ungated procedure. Include a deliberately broken rejector so the routing check must fail.

**Expected deliverable:** held-out per-level calibration records with source/codebook hashes and declared acceptance criteria.

**Falsifier:** the broken rejector passes, accepted cases violate the threshold, or a predeclared held-out rejection/distortion bound is exceeded.

**What it opens:** a measured abstention policy for that source and configuration; not a universal VOID guarantee.

## Semantic assignment — EMPIRICAL

**Gap / knowledge state:** NOT_STUDIED. No checkpoint/level-specific code-to-predicate mapping has been measured. Handwritten vectors and labels do not establish semantic fit.

**Research question:** Does a proposed assignment predict independently judged meanings with a declared error rate, compared with permuted-label and unmapped-code baselines?

**Data sources:** an identified NCM checkpoint, held-out contexts, preserved source definitions and their definition ids, and annotated evaluation examples.

**Method:** separate code identity from semantic-row identity; retain provenance and argument-place context; preregister evaluation/error criteria; compare calibrated assignments with label permutations and record absent mappings explicitly.

**Expected deliverable:** a checkpoint-bound mapping and held-out error/coverage record, including abstentions and unresolved rows.

**Falsifier:** the assignment cannot outperform its declared null or exceeds its error bound. A mapping labelled PROPOSED remains proposed until that criterion is tested.

**What it opens:** a bounded semantic adapter, not automatic truth certification by evidentials.

## Physical reading — METHODOLOGICAL

**Gap / knowledge state:** UNDEFINED. Reconstruction/residual coordinates have no specified units, energy model, or physical port pairing.

**Research question:** Is there a declared energetic system and independently measurable port relation that justifies any physical effort–flow language here?

**Data sources:** an actual proposed transducer/model and its measurements; none were supplied.

**Method:** state energy and units, time variable, effort/flow pairing, constitutive relations and measurable failure conditions before applying the physical taxonomy. Otherwise retain nonphysical bookkeeping terminology.

**Expected deliverable:** a power-consistent model and external measurement protocol, or an explicit decision to keep the channel nonphysical.

**Falsifier:** dimensional inconsistency or input/output power discrepancy outside a stated uncertainty bound. Squared-norm orthogonality alone is neither the criterion nor a remedy.

**What it opens:** consideration for a physical registry only if the energetic and measurement contracts are established.
