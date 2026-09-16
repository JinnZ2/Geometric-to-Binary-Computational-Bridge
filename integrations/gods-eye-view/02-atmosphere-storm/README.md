# Atmosphere and storm: Open-Meteo + FIRMS on the globe, NDBC buoys + HURDAT2 in the bridge

> Two live thermal/fluid feeds on the globe (weather, fires) and one live thermal/fluid feed in the bridge (buoys) that has never been drawn.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  Open-Meteo ──/api/weather-effects──▶ deriveWeatherEffectProfile ──▶ cockpit visuals   (GEV)
  NASA FIRMS ──/api/firms──▶ adaptFirmsRecords ──▶ firmsHeatmap, analyst 'local-firms'  (GEV)

  NDBC realtime2 ──urllib──▶ noaa_fetch.fetch_buoy ──▶ {wind, gust, wave, pres, sst}  (bridge)
  HURDAT2 / NHC RSS ────────▶ noaa_fetch ──▶ track fixes                               (bridge)
        │
        ├─ av-atm-1 ▶ a buoy LAYER on the globe (init/enable/update/getStats)
        ├─ av-atm-2 ▶ storm track as annotation polygons
        └─ av-atm-4 ▶ buoy residuals through route() with storm_distance as covariate

  physical_coupling_matrix: R(radiative) ─▶ T(thermal) ─▶ F(fluid)   the storm as an engine
  styles/thermal.js ✗──▶ thermal_encoder    (a look, not a measurement; must not connect)
```

## Shape

|  |  |
|---|---|
| bottleneck | The bridge's one live transducer (NDBC) has no render path; GEV's render path has no bridge-side physics. Neither side is missing code, only a layer module. |
| leverage | noaa_fetch is stdlib, keyless, public domain. It clears DATA_SOURCES.md on arrival, which no other bridge feed does. |
| harmonics | Storm-distance from HURDAT2 is the covariate MISSING_VARIABLE should find; that makes a live storm a power test for FCL-5 with a known answer. |
| tertiary | GEV weather is a per-camera-cell observation cached 5 min; a gradient built from two cells is a claim about the cache, not the atmosphere. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/weatherEffectsMath.js` | deriveWeatherEffectProfile(): WMO code selects the family, observations bound strength; missing weather fails clear |
| `src/data/firmsAdapt.js` | adaptFirmsRecords(): FIRMS VIIRS l/n/h and MODIS 0..100 confidence -> 0..1; frp, brightness, day/night |
| `src/data/firmsHeatmap.js` | the fire layer's render path; 'local-firms' in analystEngine |
| `src/styles/thermal.js` | the FLIR look: a GLSL post-process over RGB imagery. Not thermal data. See interference |
| `DATA_SOURCES.md` | licence carve-outs per feed; the shape the bridge's .fieldlink.json consent field mirrors |

Bridge (this repo)

| file | role |
|---|---|
| `Hurricane/noaa_fetch.py` | fetch_buoy(): NDBC realtime2 (wind, gust, wave, pressure, SST, air temp); HURDAT2 best track; NHC RSS. stdlib urllib only, keyless, public domain |
| `Hurricane/hurricane_coupling.py` | multi-domain coupling analysis via the bridge encoders' physics helpers |
| `GI/hurricane_validator.py` | compute_phase_coupling(): Fibonacci-pair phase coherence, the intensification hypothesis's own test |
| `bridges/thermal_encoder.py` | stefan_boltzmann_radiance, newton_cooling_rate, blackbody_peak_wavelength |
| `fabrication/temperature.py` | c_air, rho_air, thermal_expand: the acoustic and density corrections, 0.52% of exact over -50..+50 C |
| `physical_coupling_matrix.py` | F (fluid), T (thermal), R (radiative) nodes with entropy ranks and max conversion efficiencies |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-atm-1` NDBC buoys as a GEV data layer

- direction `bridge->gev` · cost `medium`
- **moves:** noaa_fetch.BUOYS positions + fetch_buoy() fields -> a layer module implementing init/enable/disable/update/destroy/getStats; keyless, public-domain, so it passes DATA_SOURCES.md on arrival
- **fails if:** the layer cannot report an honest getStats(): NDBC's 45-day window means a buoy with no row in the last hour must read 'stale', and a buoy that is adrift or offline must read 'unavailable', not 0 m/s

### `av-atm-2` NHC active storms as annotation polygons

- direction `bridge->gev` · cost `low`
- **moves:** NHC index-at.xml (already parsed by noaa_fetch) -> annotationGeoJson track lines + cone; the voice whiteboard already draws real boundary polygons
- **fails if:** the RSS carries no cone geometry, only advisories; then the cone is invented and the avenue stops at the track line

### `av-atm-3` FIRMS confidence <-> epistemology grade

- direction `both` · cost `trivial`
- **moves:** normalizeConfidence() output and epi_classifier's measured/inferred/derived/asserted are both provenance grades; one table maps them, see 06-feed-integrity
- **fails if:** VIIRS 'nominal' and MODIS 50 map to the same grade while meaning different things; the table must carry the sensor as a covariate or it is lossy

### `av-atm-4` Buoy pressure/wind residuals through the claim loop during a named storm

- direction `bridge->bridge` · cost `low`
- **moves:** fetch_buoy() rows -> reading() with covariates {storm_distance_km from HURDAT2}; MISSING_VARIABLE is expected to fire on storm_distance
- **fails if:** the binomial-tail branch does not fire on storm distance at p < COVAR_ALPHA for a buoy the storm passed within 100 km; that would mean either the band was set too wide or the branch has lost the power measured in FCL-5

## Interference

- GEV 'thermal' is a look, not a measurement: styles/thermal.js maps RGB luminance to an ironbow ramp. It must never feed thermal_encoder. The share-link token is 'flir', which names a sensor the app does not have
- Hurricane/hurricane_coupling.py begins with an 'add:' paste block before its module docstring, the same shape as the two-encoders-in-one-file glyph paste (GLY-0). Check it compiles before importing
- GEV weather is per-camera-cell (0.1 deg, 5 min cache): one observation, not a field. Do not read it as a gradient

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `earth-systems` | assumption_validator/ is the premise gate for any storm-intensity claim before it is drawn |
| `physics-guard` | domains/ carries the thermal and fluid premise checks |
| `urban-resilience` | a fire or storm layer is the disturbance input its community.py models |
| `noise-sensor` | FIRMS confidence l/n/h is a noise grade; the epistemology mapping in 06-feed-integrity applies |

## Crosslinks

- [geo-seismic](../01-geo-seismic/README.md)
- [feed-integrity](../06-feed-integrity/README.md)
- [infrastructure](../05-infrastructure/README.md)
- [sensing-edge](../07-sensing-edge/README.md)
- [map](../README.md)
