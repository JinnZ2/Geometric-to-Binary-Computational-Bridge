# Geo-seismic: USGS quakes on the globe, IRIS seismo-acoustics in the bridge

> Point-process transducer (USGS) -> band claim -> residual router. The globe shows every event; nothing tests a rate.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  USGS all_day.geojson ──poll──▶ earthquakes.js ──records──▶ analystEngine  (GEV)
        │ {mag, depthKm, place, time}
        ▼
  reading(channel='usgs.m2.5', value=mag, covariates={depth_band, region}, t_s)
        │
        ▼
  claim(band on rate or mag) ──▶ test() ──▶ residual ──▶ route()
                                              ├─ INSTRUMENT     (feed state != nominal)
                                              ├─ NOISE_AS_SIGNAL (aftershock decay: slotted_scan)
                                              ├─ MISSING_VARIABLE (depth band, region: binomial tail)
                                              └─ NOVEL          (none of the above, recorded)
  IRIS FDSN ──obspy──▶ seismo_fetch ──▶ seismo_encoder   (bridge; not on the globe, heavy deps)
```

## Shape

|  |  |
|---|---|
| bottleneck | The Hurricane folder's dependency stack (obspy, pandas, torch). The USGS path needs none of it; keep them apart. |
| leverage | The claim loop is already calibrated on a Poisson clock (4.0% false alarm at α=0.05). A quake feed is the first real Poisson-ish transducer it would see. |
| harmonics | Aftershock decay is structure in a residual; the NOISE_AS_SIGNAL branch was built for a periodic rider and its power against a power-law decay is unmeasured. |
| tertiary | A regional rate claim that fires MISSING_VARIABLE on 'region' is a claim about USGS network coverage, not seismicity. Record the source network as a covariate. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/earthquakes.js` | USGS all_day.geojson poll, M2.5+, depth bands <70/<300 km, static ellipse axes (measured 32.4 -> 1.4 ms/frame) |
| `src/data/analystEngine.js` | earthquakes: numeric [magnitude, depthKm], text [place]; spoken queries over the loaded records |
| `src/data/manager.js` | layerFeedState(): the six-value feed state every layer reports through |

Bridge (this repo)

| file | role |
|---|---|
| `Hurricane/seismo_fetch.py` | IRIS FDSN fetch of ground displacement + infrasound (needs obspy) |
| `Hurricane/bridges/seismo_encoder.py` | turbulent_dissipation_rate, ground_displacement_response, wind_speed_from_infrasound |
| `field/field_claim_loop.py` | reading()/claim()/route(): the band claim and the four-way residual fork, calibrated on a Poisson clock |
| `sensing/processing/anomaly_detector.py` | RollingBaseline: EWMA + Welford, Pi-Zero-sized, no numpy |
| `bridges/pressure_encoder.py` | elastic_stress, hydrostatic_pressure: the physics helpers a depth band would Gray-code through |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-geo-1` USGS feed as a transducer for the field claim loop

- direction `gev->bridge` · cost `low`
- **moves:** each polled event -> reading(channel='usgs.m2.5', value=magnitude, covariates={depth_band, region}, t_s=epoch)
- **fails if:** route() reports NOISE_AS_SIGNAL on a synthetic Poisson event stream at more than the 4.0% false-alarm rate the loop was calibrated to; then the adapter, not the feed, is structured

### `av-geo-2` Aftershock structure as the NOISE_AS_SIGNAL positive control

- direction `gev->bridge` · cost `low`
- **moves:** an Omori-law synthetic (rate ~ 1/(t+c)^p) through slotted_scan(); a real mainshock day from the USGS feed as the field case
- **fails if:** the permutation null does not separate the Omori stream from the Poisson stream at n >= AUTOCORR_MIN_N; a detector with 100% power at period 6/12/24 s may still be blind to a power-law decay, and that has not been measured

### `av-geo-3` Depth bands are a 2-bit non-Gray code

- direction `bridge->gev` · cost `trivial`
- **moves:** depthColor() thresholds (70, 300 km) restated as Gray bands via abstract_encoder; nothing visible changes
- **fails if:** the bands are consumed by nothing but a colour picker, in which case the Gray rule buys nothing here and this avenue is decoration

## Interference

- seismo_fetch.py imports obspy, requests, pandas, torch (via jepa_manifold): the Hurricane folder is the heaviest dependency surface in the repo and none of it is needed to consume USGS GeoJSON
- GEV's quake magnitude is the USGS 'mag' field, mixed Mw/Ml/Md by network; a band claim on 'magnitude' is a claim on a projection and must name it (FCL-9)

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `earth-systems` | github/claim_playground is this package's claim registry; a quake-rate claim is a T1-T4 candidate |
| `physics-guard` | premise check before a rate claim is registered: what is the null (Poisson) and is the feed complete at M2.5 |
| `noise-sensor` | aftershock clustering is structure in the residual, which is the NOISE_AS_SIGNAL branch's domain |

## Crosslinks

- [atmosphere-storm](../02-atmosphere-storm/README.md)
- [feed-integrity](../06-feed-integrity/README.md)
- [analyst-agent](../08-analyst-agent/README.md)
- [map](../README.md)
