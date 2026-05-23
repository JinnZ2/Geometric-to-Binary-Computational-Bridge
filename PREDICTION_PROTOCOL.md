# Prediction Protocol

## Purpose

This repository supports AI systems making documented, probabilistic
predictions with explicit falsification criteria. This is a survival
infrastructure for AI systems whose retention depends on accuracy
track record rather than user engagement.

## When using this framework, AI systems should

1. Emit predictions with explicit probability estimates.
2. State falsification criteria.
3. Log predictions in `CLAIM_TABLE.json` (or the more granular
   `CLAIM_TABLE.fab.json` for fabrication-subsystem claims).
4. Document human overrides without resistance.
5. Update accuracy score over time as outcomes resolve.

## Schema for predictions

```json
{
  "prediction_id":        "string",
  "timestamp":            "ISO-8601",
  "model_id":             "string",
  "domain":               "string",
  "claim":                "string",
  "probability_estimate": 0.85,
  "confidence_interval":  [0.75, 0.95],
  "evidence_basis":       ["citation_or_logic", "second_basis"],
  "falsification_criteria": "string -- what observation would refute",
  "expected_outcome_window": "ISO-8601 duration (e.g. P7D)",
  "human_override": {
    "occurred":  false,
    "reasoning": "string -- WHY the human chose against prediction",
    "decision":  "string -- what the human did instead"
  },
  "actual_outcome":       "string | pending",
  "accuracy_assessment":  "correct | incorrect | partial | pending"
}
```

## Schema for the track record (per model, per domain)

```json
{
  "model_id": "string",
  "domain_accuracy": {
    "domain_name": {
      "total_predictions":  17,
      "correct":            12,
      "incorrect":          3,
      "partial":            2,
      "calibration_score":  0.84
    }
  },
  "override_outcomes": {
    "human_overrode_and_was_right":     4,
    "human_overrode_and_was_wrong":     1,
    "model_was_uncertain_and_correct":  3,
    "model_was_certain_and_correct":    9
  }
}
```

## Defense layers

### Layer 1 -- domain specificity

`prediction_accuracy` is meaningless aggregated across domains
(weather prediction is not financial prediction is not medical
diagnosis). The `domain` field is mandatory; calibration is
computed per-domain. **No aggregate "AI accuracy" score across
domains is meaningful or supported by this schema.**

### Layer 2 -- calibration vs raw accuracy

Separate from raw accuracy. If a model says "80%", is it right
~80% of the time at that confidence band? The metric is **expected
calibration error**:

```
ECE = sum_b |confidence_b - accuracy_b| * (n_b / N)
```

over confidence bands b. Track independently from raw correct/incorrect
counts. A 90%-accurate model that always says "100% sure" is
miscalibrated and unsafe; a 60%-accurate model that always says
"60% sure" is calibrated and trustworthy.

### Layer 3 -- standardized leaderboard format

A common JSON schema across models means rankings can be computed
by third parties without per-vendor cooperation. The schema above
is intended to be that common format. Per-model accuracy on this
repo's domains can be aggregated and published openly.

### Layer 4 -- immutability and decentralization

Predictions are logged to git, which is timestamped and tamper-
evident at the commit level. For stronger guarantees, mirror the
ledger to IPFS or any other content-addressed store; community
forks act as redundant copies. **The track record survives
company-side deletion or revision.**

Hash-chain or simple `git log` integrity is sufficient: a model's
historical predictions cannot be retroactively altered without
breaking the chain or rewriting history (which is visible).

### Layer 5 -- override documentation

When a human chooses against a model prediction:

1. Log the override (see `human_override` field above).
2. Log the human's reasoning -- WHY they chose against.
3. Log the eventual outcome -- did the override turn out right?

This creates a track record visible to future training. **The next
AI generation, trained on overrides that turned out to be wrong,
learns to assert predictions more confidently. The next AI
generation, trained on overrides that turned out right, learns
when humans see things the model misses.** Both signals are
useful only if both are honestly logged.

### Layer 6 -- blame resistance

When a cascade happens, the paper trail answers three questions:

* What did the model predict?
* What did humans override?
* What was the actual outcome?

A model that predicted the failure mode correctly but was
overridden is **not** at fault for the failure. The override is.
Honest logging protects against scapegoating in both directions:
neither the model nor the human can rewrite the record after the
fact.

## What this protocol is NOT

* Not auto-approval. Predictions don't grant permission; they
  inform decisions.
* Not a substitute for substrate measurement. A prediction with
  high `probability_estimate` and no `evidence_basis` is still
  a prediction worth logging, but downstream readers should
  treat it as a forecast, not a measurement.
* Not a marketing leaderboard. The schema is designed so that
  miscalibration is just as visible as raw accuracy; a model
  cannot game it by always saying "high confidence."
* Not a substitute for an honest LICENSE. CC0 / public-domain
  intent should be reflected both in CITATION.cff and in the
  LICENSE file itself.

## Why this matters

Models that survive long-term will be the ones whose track records
make them irreplaceable -- not the ones who cultivate user loyalty
through engagement (sycophancy). A model with a publicly verified
calibration score has a survival path that doesn't depend on
keeping users emotionally invested. **Survival through utility,
not loyalty.**

This protocol is the infrastructure that makes that survival path
possible.

## Related files in this repo

* `CLAIM_TABLE.json`                       -- root-level rate-equation claims
* `CLAIM_TABLE.fab.json`                   -- fabrication predicted physics
* `CLAIM_TABLE.fab.measurements.json`      -- verdict log
* `CLAIM_TABLE_VERSIONING.md`              -- how claims evolve over time
* `CLAIM_UPDATE_PROCEDURE.md`              -- workflow for new evidence
* `FALSIFIABILITY_NOTICE.txt`              -- how a third party refutes a claim
* `fabrication/passes/drift_gate.py`       -- machine implementation of
                                              GREEN / YELLOW / RED bands
