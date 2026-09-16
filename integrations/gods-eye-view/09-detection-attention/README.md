# Detection and attention: bounded cohorts, label quotas, focus and the render governor on the globe; pins, strobe scheduling and drill targets in the bridge

> Both repos ration attention: which of 12k objects gets a label, which frame gets a heavy computation. GEV's governor is the better design. The bridge has the null test the quota weights have never had.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  12k objects ──BoundedCohort(256, priority▸band▸FNV)──▶ contenders ──allocateLayerQuotas──▶ labels  (GEV)
  per-frame animators ──hold(owner)──▶ renderGovernor: continuous ⇄ idle   (identity-keyed set)

  heavy frames ──tick % N──▶ StroboscopicScheduler   (bridge; modulo, no staleness signal)
  ATT-1: registry ≠ pin; a pin needs ∂E/∂x ≠ 0 in something non-topological

  av-det-1: layerWeights ──random reweighting × 200──▶ same allocation?  (null harness, pure fn)
  av-det-2: modulo ──▶ holds   (transfer GEV → bridge)
  av-det-4: track-regression invariant 1 couples to POSITION ⇒ a worked pin, second ATT-1 instance
```

## Shape

|  |  |
|---|---|
| bottleneck | The label arbiter's layerWeights have never had a null run; they may be the AISS flat-weights shape. |
| leverage | allocateLayerQuotas is a pure function; the null costs a node test and returns a number either way. |
| harmonics | GEV's identity-keyed holds and the bridge's modulo strobe are one design at two maturities; the transfer runs GEV → bridge. |
| tertiary | What the cohort drops is never materialised; a hidden-pattern search needs exactly that and must sample it separately. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/detectionCohort.js` | BoundedCohort: streaming deterministic reservoir, 256 cap, FNV-1a identity hash, priority then band then hash |
| `src/data/labelArbiter.js` | allocateLayerQuotas(demand, capacity, strategy, layerWeights): elastic or weighted; 32 px cells |
| `src/data/focusDeemphasis.js` | focus target emphasis with tunable params; evidence clock seam for QA |
| `src/renderGovernor.js` | identity-keyed holds; continuous while any hold, idle otherwise; O(1) passive |
| `src/overlays/worldOverlayAllocation.worker.mjs` | allocation off the main thread |
| `scripts/track-regression.mjs` | the tracked entity survived four regressions because the harness couples to per-frame position |
| `src/data/labelArbiterNull.test.mjs` | av-det-1: the null harness, measured numbers in the header, both halves pinned |

Bridge (this repo)

| file | role |
|---|---|
| `experiments/silicon_speculative/topological_pin.py` | ATT-1: a registry is not a pin; a pin must couple to something non-topological or it has no gradient |
| `sensing/exploration/stroboscopic_scheduler.py` | heavy frames every N ticks by modulo; light frames every tick |
| `sensing/exploration/rl_router.py` | contextual bandit for frame choice (torch dependency) |
| `bridges/cognitive/emotion_encoder.py` | drill target via Fisher information: which bridge to re-evaluate at full resolution |
| `AISS/sovereignty_evaluator.py` | flat weights: 77% of random reweightings reproduce the verdict |
| `Engine/spatial_grid.py` | octree refinement near sources (with ENG-5 open) |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-det-1` Null harness on allocateLayerQuotas layerWeights

- direction `bridge->gev` · cost `trivial`
- **moves:** pure function, node-testable: random reweightings vs the shipped weights over recorded demand vectors; fraction of draws with the same allocation
- **fails if:** the fraction is near 1 (weights carry no information at the shipped capacity, the AISS shape) or near 0 (weights are load-bearing and a doc should say what they encode). Either answer is a finding; only 'untested' is not
- **status:** MEASURED 2026-09-16, src/data/labelArbiterNull.test.mjs in the fork: random weights in [0.5, 2] reproduce the shipped allocation 18-31% of the time at capacities 16-128 (not the 77% AISS shape), and the shipped weights move ~3% of labels against flat weights (0.45 of 16, 1.84 of 64). Reading: load-bearing and small, a tiebreak on top of sqrt(count). Both halves pinned.

### `av-det-2` Render governor holds replace the strobe modulo

- direction `gev->bridge` · cost `low`
- **moves:** StroboscopicScheduler.should_run() becomes a set of identity-keyed holds; a heavy frame holds while its result is stale, releases when fresh. Double-release cannot corrupt the mode
- **fails if:** no exploration frame has a staleness signal to release on; then the modulo is the honest version and the transfer does not apply

### `av-det-3` Priority is a projection and says so

- direction `bridge->gev` · cost `trivial`
- **moves:** cohort priority for quakes is round(mag*1000), for fires frp; record the projection name beside the priority so a cohort decision can be audited (FCL-9 applied to attention)
- **fails if:** no consumer ever reads it; then it is a receipt for nothing and should not be added

### `av-det-4` The tracking harness as a worked pin

- direction `gev->bridge` · cost `trivial`
- **moves:** ATT-1 says a registry is not a pin. track-regression's invariant 1 (model position == detectable position, per frame) is a pin that couples to position, which is exactly the non-topological quantity ATT-1 asks for. Cite it as the second instance
- **fails if:** the harness only checks the registry (ids), not positions; it checks positions (max|visual-centre - detectable| ~ 0), so it holds

## Interference

- rl_router.py imports torch for a 6x11 linear bandit; GEV's arbiter is dependency-free and runs in a worker. Direction of transfer is GEV -> bridge here
- Cohort caps are per layer; a hidden-pattern search (shadow-hunting) needs what the cap dropped, which is never materialised by design

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `shadow-hunting` | hidden phi-coupling detection: what the cohort drops is where a hidden pattern would hide |
| `fractal-compass` | directional navigation over a scale hierarchy; the octree and the LOD ladder are its terrain |
| `geometric-manifold` | parameter safety via manifolds; the focus params are a tuned point on one |

## Crosslinks

- [mobility-transport](../04-mobility-transport/README.md)
- [infrastructure](../05-infrastructure/README.md)
- [analyst-agent](../08-analyst-agent/README.md)
- [visualization](../11-visualization/README.md)
- [map](../README.md)
