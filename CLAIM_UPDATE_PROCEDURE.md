# Claim Update Procedure

How to fold new evidence (a paper, a measurement, an issue report)
into the claim table without losing the audit trail.

This procedure is the operational counterpart to
`CLAIM_TABLE_VERSIONING.md`. The versioning doc specifies the
**shape** of the change; this doc specifies the **workflow**.

## When to update

A claim should be updated when **any** of the following are true:

* New peer-reviewed physics changes the predicted value.
* A reproducible measurement on hardware shows the existing
  `value` to be outside its own `tol_frac`.
* The protocol in the `measurement` field is found to systematically
  bias the result (e.g. baseline-correction band too narrow for the
  device class).
* The `failure` field is found to be missing a real failure mode
  that an operator hit in the field.
* The claim's scope was implicitly broader than it should have been
  (this triggers a SPLIT into two narrower claims, not an update).

A claim should **NOT** be updated for cosmetic reasons. Rewording
without evidence is noise.

## Step-by-step

```
1. read the new evidence
     (physics paper, arXiv preprint, peer-reviewed result, OR
      reproducible measurement with logged conditions)
        |
        v
2. identify which claim(s) in the table this evidence touches
     (use ledger.summary + ledger.list_claims to find scope prefixes)
        |
        v
3. read the latest version of each affected claim
     (the `value`, `tol_frac`, `measurement`, `failure` fields are
      the ones most likely to need revision)
        |
        v
4. decide the change category:
     (a) CONFIRM       evidence agrees within tol_frac
                       -> no claim update; optionally add a
                          measurement entry to the verdicts log
     (b) REFINE        evidence shifts value within ~2*tol_frac
                       -> new version with updated value and
                          a tightened tol_frac if warranted
     (c) CONTRADICT    evidence shifts value beyond 2*tol_frac
                       -> new version with updated value AND
                          an explicit `update_reason = "contradiction"`
                          AND an updated `failure` field explaining
                          the regime where the old value applied
     (d) SPLIT         evidence shows the claim was implicitly
                       conflating two regimes
                       -> two new claims with narrower scopes;
                          old claim gets `superseded_by` pointing
                          at BOTH new claim ids
     (e) NEW           evidence introduces a measurable that the
                       table doesn't yet cover
                       -> brand-new claim entry; the existing
                          tables are untouched
        |
        v
5. create the new claim entry (or entries) per
   CLAIM_TABLE_VERSIONING.md schema
        |
        v
6. write or revise the test file:
     tests/test_<claim_id>_v<N>.py    (per-claim file)
     OR
     fabrication/<subsystem>/tests/<smoke>.py    (existing pattern)
   The test must:
     - import the new claim
     - run the measurement protocol described in the claim
     - assert the measured value lies within tol_frac of value
     - on fail, print which `failure` mode best matches
        |
        v
7. run the FULL test suite (all versions of all claims)
        |
        v
+--------------------------------------------------------+
| outcome of test run:                                   |
|                                                        |
|   green across the board                               |
|     -> commit with a message that references the       |
|        evidence source: "fab::<scope> v<N+1>: <one-    |
|        line summary>. Source: <citation>."             |
|                                                        |
|   v<N+1> passes but v<N> now fails                     |
|     -> EXPECTED for CONTRADICT updates; the old test   |
|        documents the regime where the old claim was    |
|        right. Annotate the failing test with the       |
|        `regime_limit` comment explaining what changed. |
|                                                        |
|   v<N+1> fails                                         |
|     -> DO NOT commit. Either the new evidence has a    |
|        measurement error, OR the claim revision was    |
|        wrong. Investigate, then resubmit.              |
|                                                        |
|   regression elsewhere                                 |
|     -> a coupler / cross-substrate test broke. The     |
|        revised claim has knock-on effects. Trace via   |
|        the coupler claim's `linked_scopes` field and   |
|        update or annotate the affected couplers.       |
+--------------------------------------------------------+
        |
        v
8. commit. Message format:

       <scope>: v<N+1> - <one-line summary>
       
       Source: <citation_or_DOI_or_measurement_session_id>
       Update reason: <CONFIRM | REFINE | CONTRADICT | SPLIT | NEW>
       Prior value: <previous_value>
       New value:   <value>
       Delta:       <delta_pct>%
       Affected couplers: <list, or "none">
        |
        v
9. push. CI runs the full suite. If green, the new version is
   live. If red, the commit reverts (or the failing test is
   annotated with `regime_limit`, and a follow-up commit clarifies).
```

## Citation format

Every claim version that is updated from external evidence MUST
include a `source_citation` field. Accepted forms:

* DOI:                    `doi:10.1038/...`
* arXiv preprint:         `arxiv:2024.12345`
* GitHub issue / PR:      `gh-issue:JinnZ2/<repo>#<n>`
* Internal measurement:   `internal:<session_id>` with a sibling
                          file `measurements/<session_id>.csv`
                          committed alongside
* Direct measurement file `file:<relative_path>` (e.g. for raw
  data already in the repo)

Vague citations (`"per Karnopp & Margolis"`) are not sufficient;
either give the chapter+page (`"Karnopp 2nd ed., ch. 5, p. 142"`)
or upgrade to a real reference.

## Why this exists

Without a documented update procedure, two failure modes appear:

1. **Silent edits.** Someone changes `value: 175.2` to `value: 168.4`
   without anyone noticing. The old prediction disappears; the audit
   trail breaks; calibration history is lost.
2. **Stale claims.** A measurement found something new but the
   ledger doesn't know -- so the same wrong value gets cited again
   in a downstream prediction, propagating the error.

The procedure above prevents both. Every change is traceable to
external evidence; every version stays visible; every test runs
under the conditions documented at the time it was written.

## Related files

* `CLAIM_TABLE_VERSIONING.md`              -- schema for the version chain
* `PREDICTION_PROTOCOL.md`                 -- meta-protocol for prediction tracking
* `FALSIFIABILITY_NOTICE.txt`              -- public-facing refutation procedure
* `fabrication/passes/drift_gate.py`       -- GREEN / YELLOW / RED enforcement
