# God's Eye View × Geometric-to-Binary Bridge — integration map

> Where the two repositories could exchange energy, one folder per domain,
> crosslinked, with the ecosystem repos as the third axis. Each avenue names
> what would make it FAIL. Nothing here is wired yet; this is the map.

```
  GEV      = SINK + RENDER    public feeds ──▶ proxies (cache, serve-stale) ──▶ layer records ──▶ globe / voice / analyst
  Bridge   = MEASURE + JUDGE  transducer ──▶ Gray bits ──▶ claim table ──▶ router ──▶ residual ──▶ query
  Ecosystem = 35 fieldlink mounts, each a shard that carries one field

  SEAM     = the layer record  {lat, lon, value…, feed state}   ⇄   reading() / Primitive {value, projection, covariates, epi}
             plain data crossing a language boundary (JS ⇄ Python). Never a component, never a class.
```

## The shape, whole

```
                     ┌────────────────────────── GEV ──────────────────────────┐
   USGS  FIRMS  Open-Meteo  CelesTrak  OpenSky/AIS  OSM packs  CCTV  Radio  voice
     │     │       │           │            │           │        │     │      │
     ▼     ▼       ▼           ▼            ▼           ▼        ▼     ▼      ▼
   [01]  [02]    [02]        [03]         [04]        [05]     [07]  [07]   [08]
     └─────┴───────┴───────────┴────────────┴───────────┴────────┘            │
                              │  feed state  [06]                            │
                              ▼                                              ▼
                   ┌── reading() / Primitive ──┐                    analystEngine / tools
                   │                           │                             │
                   ▼                           ▼                             ▼
             claim table ──▶ route()      epi_classifier              T1..T4 / null()
                   │        [01][02][04]        [06]                        [08]
                   ▼
             attention / render  [09]      wire  [10]       draw  [11]
                     └────────────── Bridge ──────────────┘
```

Bottleneck for the whole system: **language boundary**. GEV is vanilla ES
modules behind Vite proxies; the bridge's judges are Python stdlib. Every
avenue that crosses it does so as data (a JSONL line, an `.obs` line, a
`/api/*` response), which is why the seam above is a record and not an API.

Leverage for the whole system: **both sides already refuse to read a dead
channel as healthy**. GEV has six feed states and a serve-stale discipline;
the bridge has four epistemology grades and a null harness. Joining those two
refusals (folder 06) is the cheapest change with the largest reach, and most
other folders crosslink to it.

## Folders

| folder | shape in one line | avenues |
|---|---|---|
| [01-geo-seismic](01-geo-seismic/README.md) | USGS as a Poisson transducer for the claim loop | 3 |
| [02-atmosphere-storm](02-atmosphere-storm/README.md) | NDBC buoys have never been drawn; the FLIR look must never be read | 4 |
| [03-orbital](03-orbital/README.md) | SGP4 is a forecast whose error grows with epoch age; no anchor in GEV | 4 |
| [04-mobility-transport](04-mobility-transport/README.md) | a coast is a point forecast; Kimchi widens an interval instead | 4 |
| [05-infrastructure](05-infrastructure/README.md) | dams, datacenters, cables as coupling-matrix nodes with no capacity; the consent gate | 3 |
| [06-feed-integrity](06-feed-integrity/README.md) | six feed states ⇄ four epistemology grades, one table | 4 |
| [07-sensing-edge](07-sensing-edge/README.md) | `.obs` lines from Pi Zero nodes onto the globe; the camera pack is the node registry | 3 |
| [08-analyst-agent](08-analyst-agent/README.md) | both agents refuse to conclude; keep it that way across the seam | 4 |
| [09-detection-attention](09-detection-attention/README.md) | quota weights have never had a null run; holds beat modulo | 4 |
| [10-encoding-wire](10-encoding-wire/README.md) | share links vs Gray bands; a token is a claim | 4 |
| [11-visualization](11-visualization/README.md) | `solver.js` is vanilla and has never been drawn on a globe | 3 |

Each folder holds:

```
NN-<id>/
├── links.json     AUTHORITY: entry points both sides, ecosystem mounts, siblings, avenues, interference
└── README.md      VIEW: rendered from links.json by crosslinks.py; do not edit
```

Two folders carry a data artifact their avenue promised:

- `05-infrastructure/consent.json` — one `.fieldlink.json`-shaped consent record per GEV bundled pack. The cables pack is `share_ok:false` and has no mount; `crosslinks.py` refuses one.
- `06-feed-integrity/feed_state_epistemology.py` — the table, plus a port of `layerFeedState()` tested against the cases GEV ships, so the precedence cannot drift silently.

## Ecosystem axis

`python integrations/gods-eye-view/crosslinks.py matrix` prints domains × fieldlink mounts. Filled cells are where a mount plugs into an avenue; empty cells are absences, not suggestions (the scope rule `tests/test_explore.py` enforces on `explore.py` applies here too). Mounts touched by more than one domain today: `noise-sensor`, `physics-guard`, `earth-systems`, `urban-resilience`, `symbolic-sensors`, `fractal-compass`, `rosetta`, `mandala`, `component-failure`, `logic-ferret`, `be2-communication`, `keystone-codex`.

## Ranked by cost × reach

```
trivial, high reach   av-fdi-1  feed state → epistemology table          (shipped, tested)
                      av-det-1  null harness on label-arbiter weights     (pure fn, node test)
                      av-agt-1  feed state on every narrated answer
low, measurable       av-mob-1  coast error vs coast time from GEV's own fix history   (horizon_sweep)
                      av-geo-1  USGS through route(); Poisson null already calibrated
                      av-orb-3  precession.py vs celestialRing.js pole cross-check
medium, visible       av-atm-1  NDBC buoy layer                          (stdlib, keyless, public domain)
                      av-sen-1  field-nodes layer from .obs               (needs a node registry: av-sen-2)
                      av-vis-1  solver.js field as a GEV layer            (batch first: ENG-5)
```

## Guard

```bash
python integrations/gods-eye-view/crosslinks.py           # 10 checks, exit nonzero
python integrations/gods-eye-view/crosslinks.py render    # regenerate the views
python integrations/gods-eye-view/crosslinks.py gev-view  # the GEV-side pointer doc (docs/INTEGRATION_AVENUES.md there)
python tests/test_integration_crosslinks.py               # the checks, and the checks' own failure cases
```

The GEV checkout is found at `GEV_ROOT`, `../gods-eye-view-fork` or
`../gods-eye-view`; without one, GEV paths are reported UNVERIFIED rather
than failed, the same way `fieldlink-sync.sh --dry` treats an unmounted
sibling.

## How to add a domain

1. `mkdir NN-<id>`, write `links.json` with every field the others have. Every avenue needs a `fails_if`.
2. Add the id to the `siblings` of every folder it crosslinks, and theirs to it. The check is reciprocal.
3. `crosslinks.py render`, then `crosslinks.py`. Add the folder to the table above.
4. Do not invent a claim id. Avenue ids are lowercase (`av-xxx-n`) so `claims_index.py` cannot scan them into a family.

## Licences at the seam

GEV code is MIT; its bundled data carries its own terms (ODbL, PDDL, public domain, and one CC BY-NC-SA pack). This repo is CC0-1.0. Code may cross either way. Data crosses only with a consent record, and the NC pack does not cross. <!-- licence-ref: external, gods-eye-view code and data -->
