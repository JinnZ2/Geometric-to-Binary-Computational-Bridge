# Claim Table Versioning

How a claim evolves over time without losing the trail of how
it got there.

## Core rule

**Same claim, new data -> new version. Both versions stay in the
table.**

This is the opposite of "edit in place." An entry never disappears;
only newer entries supersede older ones. The history shows how the
model's understanding changed and why.

## Versioning fields

Add to any claim that gets updated:

```json
{
  "claim_id":           "fab::thermal::THERM_SMOKE::dyn",
  "version":            2,
  "supersedes":         "<previous claim id>",
  "superseded_by":      null,
  "updated_at":         "ISO-8601 timestamp",
  "update_reason":      "string -- WHY the claim was updated",
  "source_citation":    "string -- paper / measurement / issue link",
  "value":              60.0,
  "previous_value":     58.5,
  "delta_pct":          2.5,
  "tol_frac":           0.10,
  "measurement":        "...",
  "failure":            "..."
}
```

When v3 is added, v2 gets its `superseded_by` field set to point
at v3. v1 still points at v2. The full chain is walkable in both
directions.

## Test-suite naming convention

Tests follow the version they validate:

```
tests/test_<claim_id>_v1.py
tests/test_<claim_id>_v2.py
```

Running the full suite **runs all versions**. The current best
claim should be in `v_latest`; older versions stay in the suite
to demonstrate how the model's behavior changed -- and to catch
regressions where a v2 update accidentally broke what v1 got right.

## Workflow

```
new evidence arrives
  |
  v
read existing claim(s) at this claim_id
  |
  v
+-------------------------------------+
| does the new evidence:              |
|   (a) confirm v_latest    -> stop   |
|   (b) refine v_latest     -> v+1    |
|   (c) contradict v_latest -> v+1    |
|                              with   |
|                              update |
|                              reason |
|                              = "contradiction" |
+-------------------------------------+
  |
  v
create new claim entry v+1
  |
  v
write test_<claim_id>_v<+1>.py
  |
  v
run FULL suite (all versions)
  |
  v
+-----------------------------------+
| does v+1 pass?                    |
|   yes -> commit with citation link|
|   no  -> document why, keep v at  |
|          current latest           |
+-----------------------------------+
```

## What this enables

* The **probability landscape becomes visible over time**: readers
  can see how confidence in a claim shifted as evidence accumulated.
* **Contradicting evidence does not erase prior commitments**: a
  paper that overturns v2 produces v3, but v2 stays visible. The
  conditions under which v2 was correct (different operating
  regime, different material lot, different temperature range) are
  preserved, and v3 documents the boundary.
* **Calibration tracking gets richer**: a model whose v1 predictions
  systematically had to be revised toward higher values is showing
  a calibrated bias. That bias is itself a useful signal.
* **Replication is easier**: each version's `measurement` field
  tells a reader exactly how to reproduce the experiment that
  generated the value. Re-running an old version on new equipment
  is a falsification test on its own.

## What it is NOT

* Not a way to silently fix mistakes. Update reasons must be
  explicit, and the prior value is preserved in `previous_value`.
* Not version-as-author-name. Versions track *evidence
  generations*, not who wrote them. If two authors both update
  the same claim with different evidence, that produces two
  branches -- both stay in the table, and a reviewer reconciles
  by adding a v+1 that picks (or merges).
* Not a substitute for the falsification field. Each version of a
  claim still has to carry its own `failure` list mapping
  disagreement to physical causes.

## Example: how an existing claim would version

`fab::acoustic::HELM_SMOKE::mode0` was created in commit `a05112f`
with `tol_frac = 0.08` and a Rayleigh end-correction model. If a
later measurement found systematic 4% deviation at low Reynolds,
the update would look like:

```json
{
  "claim_id":     "fab::acoustic::HELM_SMOKE::mode0",
  "version":      2,
  "supersedes":   "<v1 id>",
  "updated_at":   "2026-06-15T12:00:00Z",
  "update_reason": "low-Re measurements show systematic 4% downward
                    shift; switching to Ingard end-correction model",
  "source_citation": "internal/2026-06-15-helmholtz-recalibration.csv",
  "value":          168.4,
  "previous_value": 175.2,
  "delta_pct":     -3.9,
  "tol_frac":      0.05,
  "measurement":   "swept-sine + baseline correction; phone mic at
                    cavity mouth; coh_min=0.7",
  "failure":       "deviation > 5% suggests neck geometry off-spec
                    OR cavity volume mismeasured"
}
```

v1 stays. v2 supersedes. Both tests stay in the suite. A future
reader can answer "when did this prediction change and why?" by
reading two consecutive claim entries.
