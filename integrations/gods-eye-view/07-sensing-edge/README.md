# Sensing edge: public cameras and radio on the globe; Pi Zero field nodes, LoRa, HAM and CB relay in the bridge

> GEV consumes other people's sensors over HTTP. The bridge builds its own and moves their readings over radio. The seam is the .obs line.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  city camera packs ──registered URLs only──▶ /api/cctv ──▶ cctv.js (pose, viewshed)   (GEV)
  Radio Browser ──▶ radio.js ──▶ browser audio element → broadcaster              (GEV, not RF)

  DS18B20 / soil / IR / PIR+mic ──drivers──▶ Primitive ──▶ .obs line   (bridge, Pi Zero)
        │                                        ├─ LoRa packet
        │                                        ├─ KISS frame (HAM TNC)
        │                                        └─ CB voice script (≤50 words, NATO digits)
        └─ claim_match.verify_obs_file ──▶ .claims catalogue

  av-sen-1: .obs ──/api/obs (registered path)──▶ field-nodes LAYER   needs {concept_id → lat, lon}
  av-sen-2: cctv_sources.*.json IS that registry shape (pose, range, mount height, license)
```

## Shape

|  |  |
|---|---|
| bottleneck | A Primitive carries a named spatial bound, not a coordinate. Without a node registry the field-nodes layer has nothing to place. |
| leverage | The camera pack schema is already that registry: pose, range, mount height, licence per instrument. Reuse it with sensor_id in place of url. |
| harmonics | The CB relay script and the realtime voice agent are the same channel from two ends; a parser closes a voice-only path from a shop to the globe. |
| tertiary | A field-nodes proxy must inherit the registered-URL rule or it reopens the SSRF hole SECURITY.md closed. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/cctv.js` | server-registered camera URLs only; v2 calibration with provenance; viewshed; city packs |
| `src/data/radio.js` | Radio Browser directory: internet streams played directly by the browser; station tags, not RF |
| `config/cctv_sources.shinjuku.json` | the camera pack schema: lat, lon, headingDeg, pitchDeg, fovDeg, rangeM, mountHeightM, license |
| `SECURITY.md` | the proxy fetches registered URLs only, never client-supplied ones |

Bridge (this repo)

| file | role |
|---|---|
| `sensing/sensing_node.py` | the runnable node: drivers + recipe + transport, mocks cleanly |
| `sensing/processing/primitives_encoder.py` | Primitive: concept_id, domain, form, role, couplings, bounds(spatial,temporal,scale), epi, confidence, timestamp, claim_ref; .obs line codec |
| `sensing/transmission/cb_relay_format.py` | a Primitive as a <=50-word NATO-phonetic voice script |
| `sensing/transmission/ham_kiss_wrapper.py` | KISS framing for TNC packet radio |
| `sensing/transmission/lora_transmit.py` | LoRa packets, chunked above MTU |
| `sensing/hardware/tier3_rf_sensing.md` | planned RTL-SDR tier: the only RF sensing in either repo, and it is a plan |
| `sensing/processing/claim_match.py` | verify_obs_file(): an .obs file against the repo's .claims catalogue |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-sen-1` A field-nodes layer: .obs lines on the globe

- direction `bridge->gev` · cost `medium`
- **moves:** a /api/obs proxy that reads a local .obs file (registered path only, same rule as cameras) -> a layer with one entity per node; epi and confidence drive the marker; claim_ref drives the card
- **fails if:** a Primitive's spatial bound is a name ('plot_KV'), not a coordinate; the .obs line carries no lat/lon field. A node registry {concept_id -> lat, lon} must exist on the GEV side first, like the camera pack, or the layer has nothing to place

### `av-sen-2` Camera pack schema as a sensor-pack schema

- direction `gev->bridge` · cost `low`
- **moves:** cctv_sources.*.json already has pose, range, mount height and licence per instrument; the same record with sensor_id instead of feed url is the node registry av-sen-1 needs
- **fails if:** a node is mobile (a collar, a drifter); the pack schema has no motion model and the record would lie by omission

### `av-sen-3` A spoken relay through the voice agent

- direction `both` · cost `high`
- **moves:** cb_relay_format renders a Primitive as speech; GEV's realtime agent hears speech. A tool that parses the CB script back into a Primitive closes a voice-only path from a shop to the globe
- **fails if:** the realtime model paraphrases digits; the script's whole point is that a tired operator does not guess decimals, and a model that does is worse than the operator

## Interference

- GEV 'radio' is internet streaming, not RF. The bridge's tier3 RF sensing is a plan. Neither repo has an RTL-SDR path today; the word is shared, the mechanism is not
- GEV 'detection' draws screen-space boxes around records it already holds. It is not computer vision and CCTV frames are not analysed. Nothing in either repo detects anything in an image
- Every camera URL is server-registered; a field-nodes proxy inherits that rule or it opens the SSRF hole SECURITY.md closes

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `be2-communication` | opportunistic agent communication over transports/; LoRa, KISS and CB are its transports |
| `symbolic-sensors` | sensor framework the sensing/ drivers and the camera packs both instantiate |
| `noise-sensor` | a PIR + mic node is a noise-as-information instrument |
| `biogrid` | glyph registry for biological grid sensing; soil and phenophase .obs examples are its inputs |
| `living-intelligence` | multi-kingdom ontology the bear_activity and phenophase examples file under |

## Crosslinks

- [atmosphere-storm](../02-atmosphere-storm/README.md)
- [feed-integrity](../06-feed-integrity/README.md)
- [encoding-wire](../10-encoding-wire/README.md)
- [analyst-agent](../08-analyst-agent/README.md)
- [map](../README.md)
