# Infrastructure: datacenters, dams, submarine cables, installations on the globe; energy coupling and consent in the bridge

> Dams are G->EM nodes, datacenters are EM->T sinks, cables are EM information channels. The coupling matrix has the efficiencies; the globe has the positions; neither has the flows.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  bundled packs (ODbL / CC BY-NC-SA) ──localGeojson──▶ local-* layers   (GEV, tile cut for fps)
  Overpass military=* ──/api/military-installations──▶ cached, may serve stale

  dam ────────▶ G node  ──η(G→EM)──▶ EM grid ──η(EM→T)──▶ datacenter (T sink)
  cable ──────▶ EM information edge (info_matrix)
        physical_coupling_matrix supplies η; the packs supply position; NOTHING supplies capacity
        ⇒ av-inf-1 ships with weights_are_flat until a capacity source is mounted

  DATA_SOURCES.md carve-outs ◀──same shape──▶ .fieldlink.json consent {license, share_ok}
  TeleGeography (NC) ──✗──▶ this repo (CC-BY-4.0)
```

## Shape

|  |  |
|---|---|
| bottleneck | Capacity. The packs carry position and operator, not MW. Every coupling-matrix edge is a placeholder until a capacity source is mounted. |
| leverage | The consent field already exists in .fieldlink.json; applying it to GEV packs is a record per pack, and it makes the NC boundary mechanical. |
| harmonics | The Overpass refusal bug is a ready-made positive control for a stale-aware claim: the count went to zero under it. |
| tertiary | A flow graph over public infrastructure positions is an OSINT artifact; the tile was cut for frame rate, and there is a second reason to draw it carefully. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/local_data/datacenters/README.md` | ~4.3K OSM polygons (ODbL): name, operator, telecom=data_center. No power rating field |
| `src/data/local_data/dams/README.md` | 704 OSM/OpenInfraMap polygons (ODbL) |
| `src/data/local_data/telegeography_submarine_cables/README.md` | 712 cables + 1,917 landing points, CC BY-NC-SA 3.0: bundled with a carve-out, removed for commercial use |
| `src/data/militaryInstallations.js` | Overpass allow-listed military=* within a 10 deg viewport; cached, may serve stale |
| `src/data/localGeojson.js` | bundled GeoJSON loader shared by the local-* layers |
| `docs/CURRENT-STATE.md` | the INFRASTRUCTURE tile was cut: 5,700 entities on a full-earth view took the frame rate with them |

Bridge (this repo)

| file | role |
|---|---|
| `physical_coupling_matrix.py` | EM, M, C, T, R, F, G, K nodes; max conversion efficiency matrix; information matrix |
| `mappings/field_system.py` | regen_capacity() and invariant constraints (no_overextraction, energy_ratio) |
| `Negentropic/persistence.py` | Phi = -S_exchange - sigma, W/K: the persistence margin with no threshold to tune |
| `.fieldlink.json` | consent: {license, share_ok} per mounted source; the gate any GEV dataset must pass to be mounted here |
| `fabrication/ledger.py` | measurement ledger pattern (with the GB-5 relative-path finding to avoid repeating) |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-inf-1` Coupling-matrix nodes at geographic positions

- direction `gev->bridge` · cost `medium`
- **moves:** dam -> G node, datacenter -> T sink, cable -> EM info edge; positions from the bundled packs, efficiencies from PhysicalCouplingMatrix; a flow graph, not a flow field
- **fails if:** no capacity field exists in the OSM extracts (verified: datacenters carry name/operator only), so every edge weight is a placeholder; a graph whose weights are all equal is the AISS flat-weights shape and must report weights_are_flat until a capacity source is mounted

### `av-inf-2` Consent gate on any GEV dataset mounted into the atlas

- direction `gev->bridge` · cost `trivial`
- **moves:** each local_data pack gets a .fieldlink.json-shaped consent record {license, share_ok}; TeleGeography gets share_ok:false under this repo's CC0-1.0
- **fails if:** a mount is written for the cables pack; the validator in this folder rejects share_ok:false mounts by construction

### `av-inf-3` Installation feed as a stale-aware claim

- direction `gev->bridge` · cost `low`
- **moves:** the Overpass installation count per viewport cell -> reading() with covariates {mirror, cached, stale}; the CHANGELOG's refusal-cached-as-data bug is the positive control
- **fails if:** MISSING_VARIABLE does not fire on 'cached' when a refusal is replayed as data; that would mean the count did not change under the bug, and it did (the layer went empty)

## Interference

- Licence asymmetry: this repo is CC0-1.0 and the hub of a CC0/CC-BY/MIT ecosystem; CC BY-NC-SA data cannot cross that boundary. <!-- licence-ref: external, ecosystem repos and gods-eye-view data --> The consent field exists for this
- Infrastructure entities are polygons; every bridge helper wants a point. Centroid is a projection and must be named (FCL-9)
- The INFRASTRUCTURE tile was cut for frame rate. The bridge's octree (Engine/spatial_grid.py) is the right shape for a globe LOD and the wrong implementation (ENG-5); do not transplant it as-is

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `thermodynamic-accountability` | energy-flow institutional analysis; a datacenter is an accountable energy sink |
| `component-failure` | hardware failure diagnosis and repurposing; a dam or cable outage is a component failure at planet scale |
| `urban-resilience` | salvage.py and food_system.py consume infrastructure state |
| `resilience` | ground-truth systems analysis over the same nodes |
| `coop` | trust propagation and resource flow over a network of operators |

## Crosslinks

- [atmosphere-storm](../02-atmosphere-storm/README.md)
- [feed-integrity](../06-feed-integrity/README.md)
- [visualization](../11-visualization/README.md)
- [detection-attention](../09-detection-attention/README.md)
- [map](../README.md)
