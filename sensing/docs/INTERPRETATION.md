# Interpretation

> What the readings *mean*. The pipeline never guesses — it emits
> Primitives with explicit confidence and the right `claim_ref`. This
> page is the human-side companion: how to read a row of `.obs`,
> what the regimes look like, when to escalate.

## Reading one .obs line

```
soil_regime    measured_kinesthetic    {"DS18B20.surface":{"celsius":11.5}, ...}    direct_observation    temperature,moisture    Superior_MN,2026_April,0-30cm    measured    0.850    2026-04-20T18:00:00+00:00    fourier_heat
```

| Field             | Value in example                                  | Meaning                                                |
|-------------------|---------------------------------------------------|--------------------------------------------------------|
| concept_id        | `soil_regime`                                     | What is being observed                                 |
| domain            | `measured_kinesthetic`                            | Direct sensor data, not derived                        |
| form              | JSON of all reading values                        | Compact dump for rendering / search                    |
| role              | `direct_observation`                              | Routine reading, not an anomaly flag                   |
| couplings         | `temperature,moisture`                            | Other concepts this co-varies with                     |
| bounds            | `Superior_MN,2026_April,0-30cm`                   | (spatial, temporal, scale) — same shape as CLAIM_TABLE |
| epi               | `measured`                                        | Real-hardware reading (not mock)                       |
| epi_confidence    | `0.850`                                           | Combined sensor + calibration confidence               |
| timestamp         | `2026-04-20T18:00:00+00:00`                       | UTC ISO-8601                                           |
| claim_ref         | `fourier_heat`                                    | CLAIM_SCHEMA law this Primitive supports / falsifies   |

## Regime archetypes

These are the patterns the anomaly detector will flag in `.obs`. Each
shows the *shape* you are looking for in a moving window.

### Soil regime shift

`vwc` jumps > 30 % in < 24 h, surface `celsius` drops by 2 °C+,
30 cm `celsius` lags surface by 6+ h. This is a rain-pulse signature.
Confidence stays high; the role flips from `direct_observation` to
`anomaly_signal` for the duration. See
[`examples/soil_regime_shift.obs`](../examples/soil_regime_shift.obs).

### Bear / large-mammal pass

PIR `motion=1.0` for 2+ ticks within 10 minutes, MLX `delta_c` jumps
above ambient by 15+ °C on at least one of those ticks. The IR delta
is what distinguishes a deer from a hot rock. See
[`examples/bear_activity_log.obs`](../examples/bear_activity_log.obs).

### Phenophase anomaly

Day-mean soil `celsius` at 10 cm rises > 5 °C above the 14-day
trailing mean. Indicates a late-frost rebound, a heat-dome event, or
an early budbreak setup. See
[`examples/phenophase_anomaly.obs`](../examples/phenophase_anomaly.obs).

## When to escalate

| Confidence | Role                | Action                                         |
|------------|---------------------|------------------------------------------------|
| ≥ 0.90     | direct_observation  | Append. No signal — baseline still building.  |
| ≥ 0.90     | anomaly_signal      | Transmit immediately. High-trust real event.  |
| 0.70–0.90  | anomaly_signal      | Transmit with `qualifier=corroboration_needed`.|
| < 0.70     | anomaly_signal      | Queue. Wait for at least one other Primitive  |
|            |                     | from a different sensor before transmitting.   |
| any        | direct_observation  | Append. Routine.                              |

The thresholds above are conservative. Tune per site once you have a
month of baseline. The point is: **never amplify low-confidence data
into the consortium**. The framework will not stop you, but the epi
classifier puts the truth on every line so you have no excuse.

## Mock data discipline

Mock readings (`epi=inferred`, confidence capped near 0.5) exist so
the pipeline runs end-to-end during development. **Never publish
mock-mode .obs files** to the consortium. They look like measurements
because they are timestamped and well-formed, but the substrate is
synthetic. The 0.5 confidence cap is the framework's way of telling
you so.
