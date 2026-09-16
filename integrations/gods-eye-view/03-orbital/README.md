# Orbital: CelesTrak TLEs and SGP4 on the globe, gravity encoder and precession in the bridge

> TLE -> SGP4 -> position is a forecast whose error grows with epoch age. GEV draws it; the bridge has the potential-energy encoder and a drift detector but no orbit.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  CelesTrak TLE ──/api/celestrak──▶ satellites.js ──SGP4──▶ {r, v, epoch}  (GEV)
        │                                   │
        │                                   └─▶ issPass.findNextIssPass ──▶ link windows ──▶ orbital-phycom
        ▼
  epoch age ──▶ trend.py scope  'error < X km' with X ~ 1 km/day   (bridge)
  {r, v}    ──▶ gravity_encoder.from_geometry ──▶ 39-bit Gray token (bridge)

  geoid.js: h = H + N    every altitude in GEV passes through here; record the datum
  celestialRing.js ◀──cross-check──▶ Negentropic/precession.py   (pole position at J2000)
```

## Shape

|  |  |
|---|---|
| bottleneck | No second position source in GEV, so a TLE-age residual has no anchor. The INSTRUMENT route needs one (FCL open problem 5a). |
| leverage | getNextIssPass already computes link windows; orbital-phycom consumes exactly that and nothing else in the ecosystem does. |
| harmonics | precession.py and celestialRing.js both place the pole; a cross-check costs one function call and can fail. |
| tertiary | Altitude datums: ellipsoidal in GEV, orthometric in most sources, pressure altitude in ADS-B. A reading that omits its datum is off by up to ~100 m and looks fine. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/satellites.js` | twoline2satrec/propagate from satellite.js; ISS overlay; dense catalog modes; tracked refresh |
| `src/data/issPass.js` | findNextIssPass(): look angles, next pass above min elevation |
| `src/data/rocketLaunches.js` | Launch Library 2 rolling 30-day; failed launches get no fallback orbit |
| `src/data/geoid.js` | EGM96 undulation N: h = H + N, the datum every altitude in the app passes through |
| `src/celestialRing.js` | celestial directions projected into the camera plane |

Bridge (this repo)

| file | role |
|---|---|
| `bridges/gravity_encoder.py` | orbital_velocity, escape_velocity, tidal_acceleration, schwarzschild_radius -> 39-bit Gray payload |
| `Negentropic/precession.py` | alignment_window(): dating a sky datum; circumpolarity vs epoch |
| `geometric_intelligence/network/trend.py` | drift toward a band edge over a measurement log (with TRD-1..7 recorded) |
| `Engine/spatial_grid.py` | adaptive octree; ENG-5: one point per leaf, batch before trusting it |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-orb-1` SGP4 state -> gravity encoder payload

- direction `gev->bridge` · cost `low`
- **moves:** per-satellite r, v from propagate() -> specific potential -> GravityBridgeEncoder.from_geometry(); one 39-bit token per satellite per epoch
- **fails if:** the encoder's band edges are set for planetary-scale potentials and every LEO satellite lands in one band; then the payload carries no information and the null harness (repo_guard.null_harness) says so

### `av-orb-2` TLE epoch age as a drift claim

- direction `gev->bridge` · cost `low`
- **moves:** epoch age per NORAD id -> trend.py scope; claim 'position error < X km' with X growing ~1 km/day; GEV's stale flag becomes a band edge instead of a boolean
- **fails if:** there is no second position source, so the residual is unmeasurable in GEV alone; INSTRUMENT needs an anchor (FCL open problem 5a). A ground-station pass time is the cheapest anchor and orbital-phycom is where it lives

### `av-orb-3` precession.py vs celestialRing.js cross-check

- direction `both` · cost `trivial`
- **moves:** both place celestial directions; compute the pole position at J2000 from each and compare
- **fails if:** they disagree by more than precession.py's stated model error (a few arcmin over reference epochs); one of them then has a datum bug and the comparison says which

### `av-orb-4` ISS pass windows as orbital-phycom link opportunities

- direction `gev->ecosystem` · cost `low`
- **moves:** getNextIssPass({lat, lon, minElevDeg}) -> a link-window record the orbital-phycom simulations can consume
- **fails if:** orbital-phycom's core/ expects a different orbit representation than look angles; then the seam is a schema and not a function

## Interference

- GEV altitudes are ellipsoidal (h); barometric/ADS-B altitudes are orthometric or pressure altitudes. geoid.js is the one place that reconciles them. Any bridge reading of a GEV altitude must record which datum it took
- satellite.js SGP4 is a mean-element propagator; feeding its output to a Keplerian helper (orbital_velocity from potential) mixes models. Fine for a Gray band, wrong for a residual below ~1 km

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `orbital-phycom` | geometric-seed orbital communications: link windows are exactly what findNextIssPass computes |
| `fractal-compass` | directional navigation; celestialRing is a compass rendered on a globe |
| `keystone-codex` | AI-verifiable technology library; SGP4 and EGM96 are verifiable references to register |

## Crosslinks

- [feed-integrity](../06-feed-integrity/README.md)
- [encoding-wire](../10-encoding-wire/README.md)
- [mobility-transport](../04-mobility-transport/README.md)
- [map](../README.md)
