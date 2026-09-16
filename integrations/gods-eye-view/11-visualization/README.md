# Visualization: Cesium globe, GLSL styles and world overlays; React + Three.js field view, the JS solver mirror and Gaussian splats in the bridge

> The bridge has a field solver with a JavaScript mirror that has never been drawn on a globe. GEV has a globe that has never drawn a field.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  records ──setOverlayEntries──▶ worldOverlay (priority, lane, edge fade, horizon cull)   (GEV)
  track ──trailRenderer──▶ one polyline per entity
  RGB ──GLSL post──▶ NVG / FLIR / noir / CRT / snow   (looks)

  sources ──Front end/solver.js (vanilla)──▶ field samples ──▶ FieldVisualization.jsx (Three.js)   (bridge)
  Gaussian4DSource: space+time kernels; bhattacharyya_distance between two of them

  av-vis-1: geo sources ──solver.js──▶ samples ──▶ overlay entries   (batch: ENG-5)
  av-vis-2: trail (positions + times) ──▶ splat chain; covariance from motionModel noise floor
  av-vis-3: octahedral glyph ──▶ overlay token   (only once a node carries a state: 07)
```

## Shape

|  |  |
|---|---|
| bottleneck | ENG-5: one solver call per sample point. A globe layer must batch or it will not hold frame rate. |
| leverage | solver.js is already vanilla JavaScript; it can be imported by a GEV layer without React. |
| harmonics | A trail is a chain of 4D splats; the covariance is the one number the fix history can supply (turn-rate noise floor). |
| tertiary | Glyphs on a map with no state behind them are decoration; gate av-vis-3 on 07-sensing-edge. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/overlays/worldOverlay.js` | setOverlayEntries(): source-owned entries with priority, collision group, paint lane, edge fade, horizon cull |
| `src/overlays/worldOverlayTokens.js` | overlay token vocabulary |
| `src/data/trailRenderer.js` | one entity polyline per track; whole history at one alpha, dimmed behind geometry |
| `src/styles/surveillance.js` | post-process shader pattern (NVG); thermal.js, noir.js, retro.js, snow.js share it |
| `src/data/firmsHeatmap.js` | the one scalar-field render in GEV today |

Bridge (this repo)

| file | role |
|---|---|
| `Front end/solver.js` | GeometricEMSolver in plain JS: electricFieldCharge, magneticFieldCurrent, adaptiveGrid; no React dependency inside |
| `Front end/Components/FieldVisualization.jsx` | field magnitude/direction rendering in Three.js |
| `Engine/gaussian_splats/gaussian_4d.py` | space+time Gaussians; a trail is a chain of them |
| `docs/gaussian_splats/01_4d_splats.md` | the design note for the above |
| `Engine/engine_benchmark.py` | measured: adaptive path 0.26-0.48x of uniform; batch before drawing |
| `mappings/octahedral_state_encoding.json` | the eight glyphs an overlay token could carry |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-vis-1` solver.js as a GEV layer

- direction `bridge->gev` · cost `medium`
- **moves:** sources at geographic positions (a dam as a current element, a substation as a charge) -> Front end/solver.js -> field samples -> worldOverlay entries with magnitude as accent; solver.js is vanilla and imports nothing from React
- **fails if:** the field is drawn in ECEF metres while the solver's constants assume a local frame; a dipole field computed in the wrong frame looks plausible and is wrong, and the check is a known-source unit test at two latitudes

### `av-vis-2` Trails as 4D splat chains

- direction `gev->bridge` · cost `low`
- **moves:** a track history (positions + times) -> Gaussian4DSource chain; bhattacharyya_distance between two aircraft trails is a separation metric that has time in it
- **fails if:** the splat covariance is set by hand; it must come from the fix-history noise (motionModel's turn-rate noise floor is the one measured number available)

### `av-vis-3` Octahedral glyphs as overlay tokens

- direction `bridge->gev` · cost `low`
- **moves:** mappings/octahedral_state_encoding.json glyph_unicode -> worldOverlayTokens; a node's 3-bit state drawn as its glyph
- **fails if:** no GEV entity has an octahedral state to draw; a glyph with no state behind it is decoration, and the layer should not ship until 07-sensing-edge lands a node that carries one

## Interference

- React vs vanilla ES modules: the seam is data (overlay entries, sample arrays), never a component
- ENG-1/5: the adaptive octree is slower than a uniform grid at the current one-point-per-leaf; a globe layer must batch samples into one solver call or it will not hold 60 fps

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `mandala` | octahedral glyphs as overlay tokens |
| `polyhedral` | glyph atlas for the same |
| `rosetta` | shape ontology behind a glyph on a map |

## Crosslinks

- [infrastructure](../05-infrastructure/README.md)
- [detection-attention](../09-detection-attention/README.md)
- [encoding-wire](../10-encoding-wire/README.md)
- [map](../README.md)
