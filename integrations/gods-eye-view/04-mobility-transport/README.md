# Mobility: ADS-B flights, AIS vessels, road traffic on the globe; interval propagation and residual routing in the bridge

> A dead-reckoning coast between polls is a point forecast. The bridge's Kimchi engine widens an interval instead and flags when the fitted regime expired.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  OpenSky / adsb.lol ──poll──▶ flights.js ──▶ motionModel: coast between fixes  (GEV)
  AISStream ──ws──▶ aisLiveVessels ──▶ aisWatchdog
  OSM roads ──▶ traffic.js (sim) ──▶ mode:'sim' ──▶ feed state 'fallback'

  fix(t) ──coast──▶ x̂(t+dt)          GEV: a point, cut at staleCoastLimitSeconds
  fix(t) ──widen──▶ [lo,hi](t+dt)     Kimchi: an interval, noise per step, regime scope
        └─ av-mob-1: |x̂ − fix(t+dt)| vs dt from GEV's own history = horizon_sweep

  crossTrackKm ──▶ reading() ──▶ route()   MISSING_VARIABLE expected on phase-of-flight
```

## Shape

|  |  |
|---|---|
| bottleneck | The coast is a point forecast with a hard cut; the interval engine has no live feed. av-mob-1 needs only GEV's fix history and one Python script. |
| leverage | horizon_sweep's headline (false confidence compounds with distance) is testable on real aircraft today; that is the cheapest empirical result in this map. |
| harmonics | A per-phase band (climb / cruise / descent) removes the MISSING_VARIABLE hit that a single cross-track band will always produce. |
| tertiary | Fallback transitions (OpenSky → adsb.lol) change coverage; a rate claim spanning one measures the switch. Carry the source as a covariate. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/motionModel.js` | displayedKinematics, staleCoastLimitSeconds, synthesizeForwardKinematicsFix, corridorPathLatLon: coast between fixes |
| `src/data/routePlausible.js` | crossTrackKm against origin/destination great circle |
| `src/data/flights.js` | OpenSky primary; adsb.lol regional fallback with provenance in stats |
| `src/data/aisWatchdog.js` | AIS stream liveness |
| `src/data/traffic.js` | simulated dots on OSM roads; TomTom flow tiles when keyed; mode: 'sim' reads as 'fallback' |
| `scripts/track-regression.mjs` | four tracking invariants locked with synthetic feeds |

Bridge (this repo)

| file | role |
|---|---|
| `Kimchi/forward_predict.py` | Interval.widen(noise), Coupling.in_regime(): unknowns widen honestly; couplings carry a validity scope |
| `Kimchi/horizon_sweep.py` | divergence vs horizon: false confidence compounds with prediction distance |
| `field/field_claim_loop.py` | route(): INSTRUMENT / NOISE_AS_SIGNAL / NOVEL / MISSING_VARIABLE on a residual series |
| `sensing/processing/anomaly_detector.py` | RollingBaseline for a per-track speed or turn-rate channel |
| `integrations/gods-eye-view/04-mobility-transport/coast_divergence.py` | av-mob-1 harness: coast error vs coast time; p90 widening rate in m/s |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-mob-1` Coast error vs coast time, measured from GEV's own fix history

- direction `gev->bridge` · cost `low`
- **moves:** for each aircraft: coasted position at t+dt vs the real fix that arrived at t+dt, over dt in 1..staleCoastLimitSeconds; horizon_sweep.ascii_plot of the divergence curve
- **fails if:** divergence does not grow with dt (then the coast is better than a widening interval and Kimchi's premise fails here), or grows faster than the interval widens at the shipped noise (then staleCoastLimitSeconds is too long)
- **status:** harness shipped (coast_divergence.py: ports of arcOffsetEnu, estimateTurnRateDps, staleCoastLimitSeconds; fetch/measure/selftest), self-tested on great-circle synthetics with a ~120 m tangent-plane floor at 69 km. UNMEASURED on real fixes: OpenSky and adsb.lol were unreachable from the session. Run `fetch` where they are, then `measure`.

### `av-mob-2` Cross-track distance as a band claim

- direction `gev->bridge` · cost `low`
- **moves:** crossTrackKm per fix -> reading() with covariates {altitude band, phase of flight, weather code}; route() the breaks
- **fails if:** MISSING_VARIABLE fires on 'phase of flight' for every route because climb/descent legs are never on the great circle; then the claim band is wrong, not the covariate, and the fix is a per-phase band

### `av-mob-3` Traffic simulation must enter the bridge as 'asserted'

- direction `gev->bridge` · cost `trivial`
- **moves:** the epistemology table in 06-feed-integrity maps mode:'sim' -> asserted with confidence capped at the mock penalty
- **fails if:** any consumer downstream treats a simulated dot as a measured vehicle; the table exists to make that impossible without editing it

### `av-mob-4` Validity scope on the kinematic constants

- direction `bridge->gev` · cost `low`
- **moves:** COURSE_TRACK_ONLY_MPS, COURSE_CHORD_ONLY_MPS, TURN_MIN_SPEED_MPS become Coupling(valid_lo, valid_hi) records so the coast reports when it left the regime it was tuned for (helicopters, balloons, ships at anchor)
- **fails if:** no record in the fix history ever leaves the regime, in which case the scope is decoration and should not be added

## Interference

- Two flight sources with different coverage (OpenSky worldwide snapshot, adsb.lol 250 nm around the camera): a rate claim across a fallback transition is a claim about the source switch, not the sky
- Traffic dots are a model. GEV already labels it fallback; the bridge must not upgrade it

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `trdap` | transport resource discovery: flights, vessels and bikeshare are discovered transport resources |
| `urban-resilience` | traffic and bikeshare are its mobility inputs |
| `be2-communication` | ADS-B and AIS are opportunistic broadcasts; its transports/ layer is the same shape |
| `cyclic` | poll loops with coast and prune are a cyclic execution pattern |

## Crosslinks

- [feed-integrity](../06-feed-integrity/README.md)
- [orbital](../03-orbital/README.md)
- [detection-attention](../09-detection-attention/README.md)
- [analyst-agent](../08-analyst-agent/README.md)
- [map](../README.md)
