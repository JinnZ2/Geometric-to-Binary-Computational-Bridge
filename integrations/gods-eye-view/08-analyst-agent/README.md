# Analyst and agent: spoken queries and voice tools on the globe; residual router, T1-T4 claim tester and null gates in the bridge

> GEV answers questions over records and confirms only what happened. The bridge proposes routes with evidence and refuses to conclude. Same posture, opposite directions.

Rendered from `links.json` by `../crosslinks.py render`. Edit the JSON, not this file.

## Flow

```
  voice ──realtime──▶ GEV_REALTIME_TOOLS (28) ──▶ gevActions: confirm only what happened   (GEV)
  'how many flights over Texas' ──▶ analystEngine.query ──▶ {items, coverage.layersQueried}

  residual ──▶ route() ──▶ ranked candidates + evidence   (bridge: proposes, never concludes)
  text ──▶ claim_playground T1 T2 T3 T4 ──▶ four readings   (bridge: stdlib, keyless)

  av-agt-1: coverage ⨝ layerFeedState ──▶ every narrated answer carries its feed state
  av-agt-2: transcript ──sidecar──▶ T1..T4 ──▶ readback of four readings, not a verdict
  av-agt-3: shuffle values vs ids ──▶ re-summarise ──▶ same text? then it never read them
```

## Shape

|  |  |
|---|---|
| bottleneck | Language boundary: GEV proxies are Node, the bridge's judges are Python. A keyless sidecar behind a Vite proxy is the seam. |
| leverage | analystEngine already returns coverage; joining it with feed state is a one-line change with a large honesty gain. |
| harmonics | Both agents refuse to conclude. Keep it that way: T1..T4 return four readings, never a pass/fail. |
| tertiary | A voice tool that tests claims will be asked to test claims about the app; the null harness on the HUD summary is where that starts. |

## Entry points

GEV (https://github.com/JinnZ2/gods-eye-view-fork)

| file | role |
|---|---|
| `src/data/analystEngine.js` | pure query over record arrays: applyFilter, applyScope, follow-up memory; returns {items, coverage}; never fetches |
| `src/voice/gevActions.js` | client-side tool execution: confirm only what actually happened |
| `vite.config.js` | GEV_REALTIME_TOOLS (28 tools, ~line 5664) declared server-side; /api/openai/hud-summary; /api/realtime/token |
| `src/hudSummaryResponse.js` | LLM summary over the HUD state |

Bridge (this repo)

| file | role |
|---|---|
| `field/field_claim_loop.py` | route() proposes ranked candidates with evidence; next_query() spends against a ledger; yield_rate() reports what the spend bought |
| `github/claim_playground/claim_tester.py` | T1 thermodynamic closure, T2 cascade exposure, T3 scale invariance, T4 ontology translation; CLI takes raw text |
| `AISS/sovereignty_evaluator.py` | weights_are_flat reported beside every score; verdict_is_weight_sensitive() |
| `playground/playground.py` | null(): structure replaced by noise; broken(): a deliberately wrong version the checks must reject |
| `Kimchi/constraint_playground.py` | metacognition narrates its reasoning geometry before each act; unknowns are first-class |
| `META-PROTOCOL.md` | readings have outgoing edges; verdicts do not |

## Avenues

Each one names what would make it FAIL. An avenue that cannot fail is not listed.

### `av-agt-1` Coverage and feed state on every narrated answer

- direction `bridge->gev` · cost `trivial`
- **moves:** analystEngine already returns coverage.layersQueried; join it with layerFeedState() per layer so 'how many flights over Texas' is answered with 'from a stale OpenSky snapshot' when that is the case
- **fails if:** narration drops the epistemic tag to sound fluent; the test is a stale fixture whose narration must contain the word

### `av-agt-2` A spoken claim through T1-T4

- direction `gev->bridge` · cost `medium`
- **moves:** a test_claim tool: the transcript of an assertion -> claim_playground.cli -c '<text>' -> the four verdicts read back; a Python sidecar behind a Vite proxy, keyless
- **fails if:** T1-T4 on raw text with no waste-entropy or subsidy inputs returns the same verdict for every sentence; then the tool is a null artifact and playground's null() gate is the check to run before shipping it

### `av-agt-3` A null harness for the HUD summary

- direction `bridge->gev` · cost `low`
- **moves:** shuffle the record values against their ids and re-summarise; if the summary reads the same, it was never reading the records (repo_guard.null_harness applied to prose)
- **fails if:** the summary is templated from counts alone and passes trivially; then the finding is that it is a count, and it should say so in the UI

### `av-agt-4` The analyst result set as a Reading

- direction `gev->bridge` · cost `low`
- **moves:** query -> {count, min, max} is a projection of the record set; reading(channel=query_spec, value=count, projection='analystEngine.summarize', shape=items)
- **fails if:** the claim loop is fed the count without the projection name; FCL-9 forbids it and the reading() constructor raises

## Interference

- Both agents must not conclude. GEV's tools 'confirm only what actually happened'; the bridge's router 'proposes, it does not conclude'. A tool that returns a verdict from T1-T4 is a verdict, and META-PROTOCOL says verdicts have no outgoing edge. Return the four readings, not a pass/fail
- The realtime agent runs on a paid API; the bridge's tools are stdlib. A sidecar that requires a key breaks GEV's keyless-first rule; claim_playground needs none

## Ecosystem taps

| fieldlink mount | why it plugs in here |
|---|---|
| `haas` | human-automation-AI safety: handshake.py and risk.py are the contract a voice tool surface should honour |
| `defense` | Symbolic-Defense-Protocol: voice is an untrusted input channel; coercion resistance applies to tool calls |
| `logic-ferret` | fallacy detection over a spoken claim before it is tested |
| `ai-arena` | argument competition: two analysts over the same records |
| `ai-human-audit` | the audit protocol for an AI that narrates a live picture to a human |
| `adaptive-intelligence` | substrate-independent intelligence theory the agent layer is an instance of |

## Crosslinks

- [feed-integrity](../06-feed-integrity/README.md)
- [geo-seismic](../01-geo-seismic/README.md)
- [mobility-transport](../04-mobility-transport/README.md)
- [sensing-edge](../07-sensing-edge/README.md)
- [detection-attention](../09-detection-attention/README.md)
- [map](../README.md)
