# Feed integrity: GEV's six feed states and serve-stale caches; the bridge's epistemology grades, drift detector and instrument route

> Both repos already refuse to render a dead channel as healthy. They do it in two vocabularies. One table joins them.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  layer.getStats() ──▶ layerFeedState() ──▶ nominal | loading | degraded | stale | fallback | unavailable  (GEV)
  proxy caches ──serve-stale──▶ stale (never nominal)
  Overpass 406 ──cached as data for a month──▶ FIXED: rotate mirrors, never cache a refusal

  driver.confidence_grade ──epi_classifier──▶ measured | inferred | derived | asserted  (bridge)
        mock −0.40   saturation −0.20   uncalibrated −0.10   no baseline −0.05

  av-fdi-1: one table   feed state ──▶ epistemology × confidence   (data, both sides read it)
  av-fdi-4: stale:bool ──▶ trend.py 'walking toward the edge at N/day'  (gate TRD-3 first)
  av-fdi-3: track-regression + random-walk feed = null() on a QA harness
```

## Shape

|  |  |
|---|---|
| bottleneck | Two vocabularies for one question. The table (av-fdi-1) is the whole cost. |
| leverage | Both sides already refuse to read a dead channel as healthy; the join makes that refusal survive a hand-off between them. |
| harmonics | trend.py's TRD-3 and the loop's FCL-3 are the same shape (no minimum-sample gate). Fix once, cite twice. |
| tertiary | An adapter that drops the stale flag turns a measured value into an asserted one silently. That is the failure this folder exists to prevent. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/manager.js` | layerFeedState(): nominal \| loading \| degraded \| stale \| fallback \| unavailable; guidance states never read DEGRADED |
| `src/data/retryableLoad.js` | createRetryableLoader(): memoize success, rate-limit failure, 5 s doubling to 300 s |
| `src/data/adsbLolFallback.js` | regional fallback with provenance surfaced in stats |
| `CHANGELOG.md` | Overpass: a 406 refusal was cached to memory and disk and served as data for a month; fixed by rotating mirrors and never caching a refusal |
| `scripts/track-regression.mjs` | deterministic harness: synthetic feeds, invariants that must hold |
| `src/data/aisWatchdog.js` | liveness of a websocket stream |

Bridge (this repo)

| file | role |
|---|---|
| `sensing/processing/epi_classifier.py` | measured \| inferred \| derived \| asserted; mock_penalty 0.40, saturation 0.20, uncalibrated 0.10 |
| `geometric_intelligence/network/trend.py` | is this parameter walking toward its band edge (TRD-1..7 recorded, not all fixed) |
| `field/field_claim_loop.py` | INSTRUMENT route needs anchor_dev against ANCHOR_TOL; open problem 5a: what the physical standard is |
| `repo_guard.py` | reach(): is the signal above the instrument floor; null_harness(): does the result survive noise |
| `adaptive_sim/adaptive_sim_framework.py` | --verify: a record must reproduce under the code shipped beside it (ASF-1) |
| `playground/PRINCIPLES.json` | P-UNFALSIFIABLE and the 'dead channel reads as healthy' shape (GLY-1 empty reading -> FELT_COHERENT) |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-fdi-1` One feed-state to epistemology table

- direction `both` · cost `trivial`
- **moves:** nominal->measured(1.0), stale->measured(age-penalised), fallback->inferred, mode:'sim'->asserted(<=0.5), degraded->measured(0.5), unavailable->no reading. Shipped as data in this folder, consumed by either side
- **fails if:** a GEV stat set maps to two rows; layerFeedState() is a total function with a fixed precedence, so the table must reproduce that precedence and a test checks it against the shipped cases

### `av-fdi-2` Refusal-cached-as-data as a registered principle instance

- direction `gev->bridge` · cost `trivial`
- **moves:** the Overpass bug is a second independent instance of 'a dead channel reads as the healthy state' (first: GLY-1). Two instances is what PRINCIPLES.json needs to move an entry from PROVISIONAL to ESTABLISHED
- **fails if:** the register requires a `where` path inside this repo (it does, CI-3); a cross-repo instance needs a path convention the register does not have yet. Recorded here as a candidate, not added

### `av-fdi-3` A null run for the tracking harness

- direction `bridge->gev` · cost `low`
- **moves:** track-regression's synthetic feed replaced by random-walk positions; the invariants that still pass were never reading the geometry (playground null() gate, applied to a QA harness)
- **fails if:** all four invariants still pass on noise; then the harness locks the render path, not the tracking, and that is worth knowing before the next regression

### `av-fdi-4` Age distributions instead of a stale boolean

- direction `bridge->gev` · cost `low`
- **moves:** per-layer last-fix age, TLE epoch age, cache age as trend.py scopes; 'stale' becomes 'walking toward the edge at N/day'
- **fails if:** trend.py's TRD-3 (two points give R^2 = 1.0) is still open when this is wired; wire the minimum-sample gate first or the report will predict a failure from two polls

## Interference

- GEV feed state is per layer; bridge epistemology is per reading. The join key is (layer, poll) and a reading inherits the layer's state at poll time, not at render time
- Serve-stale is correct behaviour and reads as 'stale', never as 'nominal'. Any adapter that drops the stale flag converts a measured value into an asserted one silently

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `noise-sensor` | noise as information: a feed's failure pattern is a signal about the feed |
| `physics-guard` | premise verification before a feed value is believed |
| `logic-ferret` | truth_integrity_score: the same question asked of an argument |
| `component-failure` | a feed outage is a component failure with a repurposing path (fallback source) |
| `symbolic-sensors` | self-assessment sensors: the app assessing its own feeds |

## Crosslinks

- [geo-seismic](../01-geo-seismic/README.md)
- [atmosphere-storm](../02-atmosphere-storm/README.md)
- [orbital](../03-orbital/README.md)
- [mobility-transport](../04-mobility-transport/README.md)
- [infrastructure](../05-infrastructure/README.md)
- [sensing-edge](../07-sensing-edge/README.md)
- [analyst-agent](../08-analyst-agent/README.md)
- [map](../README.md)
