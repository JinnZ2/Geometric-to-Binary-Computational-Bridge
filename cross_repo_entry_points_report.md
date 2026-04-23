# Cross-Repository Entry Points and Discrepancies

This note maps the clearest integration surfaces between the updated **Geometric-to-Binary-Computational-Bridge** repository and three related repositories: **Rosetta-Shape-Core**, **Sovereign-Octahedral-Mandala-Substrate-SOMS-**, and **Mandala-Computing**. The focus is practical navigation: where a developer would actually enter each codebase, which modules align most naturally with the updated bridge stack, and where the present discrepancies are conceptual, structural, or import-level rather than merely stylistic.[1] [2] [3] [4]

The strongest immediate conclusion is that the four repositories already share a recognizable architecture, but they do not yet expose that architecture through one stable cross-repo contract. In the updated bridge repository, the most explicit entry surfaces are now the main bridge registry, the silicon bridge adapter layer, the silicon bridge catalog, and the hardware-module chooser. In the external repositories, however, the integration surfaces are uneven: **Rosetta** is strongest as a semantic and ontology hub, **SOMS** is strongest as a protocol and encoder bridge, and **Mandala-Computing** is strongest as a downstream substrate / solver consumer. That means the missing piece is not raw conceptual alignment; it is a thin, shared adapter contract.[1] [5] [6] [7] [8]

| Repository | Best current role relative to updated bridge repo | Clearest entry point(s) | Integration maturity |
| --- | --- | --- | --- |
| Geometric-to-Binary-Computational-Bridge | Canonical encoder / registry / silicon bridge layer | `solver_registry.py`, `bridges/*`, `Silicon/core/bridges/__init__.py`, `Silicon/core/bridges/hardware_modules.py` | Highest |
| Rosetta-Shape-Core | Semantic hub and bridge-index / ontology resolver | `src/rosetta_shape_core/_bridges.py`, integration docs under `docs/` | Conceptually clear, code wiring incomplete |
| SOMS | Protocol bridge and octahedral / geometric encoding layer | `src/geometric_bridge.py`, `src/geometric_encoder.py`, `src/resilience_core.py` | Strong representation overlap |
| Mandala-Computing | Substrate consumer and solver-side integration target | `sovereign_integration.py`, `Integration.md`, examples | Mixed: examples strong, core integration partial |

## 1. Updated bridge repository: canonical entry points

The updated bridge repository is now the cleanest place to anchor cross-repo integration. Its registry already exposes bridge domains as named encode targets, while the silicon-side bridge package presents a navigation-first adapter surface. In practical terms, any other repository that wants access to the bridge ecosystem should target this repository as the canonical source of **bridge names**, **encoder classes**, and **silicon-side adapter exports**.[1]

The first entry point is the main registry in `solver_registry.py`, because that is where domain encoders become callable through stable names. The second entry point is `Silicon/core/bridges/__init__.py`, which now acts as a curated package surface rather than a random directory. The third is `Silicon/core/bridges/domain_bridge_catalog.py`, which is useful because it is documentation-oriented and already expresses domain-to-implementation mappings in a form other repositories can consume. The fourth is `Silicon/core/bridges/hardware_modules.py`, which now provides the navigation-friendly “choose your modules to import” layer you requested and is therefore the most natural import surface for hardware-adjacent repos.[1]

| Updated bridge repo surface | Why it matters cross-repo | Best external consumers |
| --- | --- | --- |
| `solver_registry.py` | Stable domain names and encoder registration | SOMS, Mandala-Computing |
| `bridges/*.py` | Canonical domain encoders | SOMS protocol layer |
| `Silicon/core/bridges/__init__.py` | Curated silicon-side import surface | Mandala-Computing, SOMS |
| `Silicon/core/bridges/domain_bridge_catalog.py` | Machine-readable / human-readable bridge map | Rosetta-Shape-Core |
| `Silicon/core/bridges/hardware_modules.py` | Navigation-first hardware import selection | Mandala-Computing, SOMS |

## 2. Rosetta-Shape-Core: semantic and ontology entry points

Rosetta’s clearest real entry point is `src/rosetta_shape_core/_bridges.py`. That file does not implement physical bridge encoders, but it **does** implement a bridge indexing and resolution mechanism that can traverse bridge mappings by shape, family, or entity. In other words, Rosetta is already organized to function as a semantic router above the bridge layer, not as a duplicate of the bridge layer itself.[2]

The important discrepancy is that Rosetta’s strongest integration language currently lives in design documentation rather than importable code. The `docs/unified-bridge-integration-guide.md` document describes a `rosetta_shape_core.bridges.unified_bridge` integration layer and a `unified_patterns/` directory as if they were the central operational bridge hub, but the repository’s actual import surface is the `_bridges.py` resolver and the surrounding package exports. That means Rosetta is closest to being a **metadata / ontology orchestrator**, but its documented cross-repo bridge path is ahead of its implemented package layout.[2] [5]

> Rosetta is best treated as the place to translate between **shape / family / entity semantics** and the updated bridge repository’s **domain encoders**, not as the place where the encoders themselves should be duplicated.[2] [5]

The most sensible integration path here is to let Rosetta consume the updated bridge repository’s `domain_bridge_catalog.py` and expose those bridge families as indexed bridge records inside `_bridges.py`. That would make Rosetta the navigation layer for “what bridge concept maps to what computational substrate,” without forcing it to re-implement the physical encoders.[1] [2]

| Rosetta file | Best integration use | Main discrepancy |
| --- | --- | --- |
| `src/rosetta_shape_core/_bridges.py` | Semantic resolution of bridge-backed paths | No direct import of the updated bridge catalog yet |
| `docs/unified-bridge-integration-guide.md` | Architectural intent | Describes integration surfaces not clearly present as code |
| `src/rosetta_shape_core/__init__.py` | Public package surface | Does not expose a stable bridge adapter tied to the updated repo |

## 3. SOMS: protocol and representation entry points

SOMS has the most obvious code-level overlap with the updated bridge repository. The file `src/geometric_encoder.py` explicitly states that it was ported from the Geometric-to-Binary bridge ecosystem, and it defines a compact token-to-binary interface that is already a cross-repo compatibility surface.[3] That makes it one of the strongest concrete entry points in the entire comparison.

Its second major entry point is `src/geometric_bridge.py`, which defines a self-describing protocol with modalities, bridge targets, Gray-coded bands, and decoder structures. Conceptually, this is close to the updated repository’s encoder family and hardware / field bridge logic, but the packaging is different: SOMS currently bundles protocol concerns, decoding, physics helper functions, and bridge targeting into one large module, while the updated repository has moved toward a registry + domain-encoder + silicon-adapter split.[3]

The third SOMS surface is `src/resilience_core.py`. This is not a direct bridge encoder, but it is highly relevant because it cleanly represents **substrate-independent resilience primitives**, which matches the conceptual distinction you just clarified between `resilience` and `community`. As a result, SOMS is the best external place to anchor a future **resilience adapter contract** if you want resilience to remain cross-substrate rather than population-specific.[3]

| SOMS file | Best integration use | Main discrepancy |
| --- | --- | --- |
| `src/geometric_encoder.py` | Direct shared representation layer | Needs explicit alignment with current registry names and token conventions |
| `src/geometric_bridge.py` | Protocol / telemetry bridge layer | Too monolithic relative to updated repo’s split architecture |
| `src/resilience_core.py` | Substrate-independent resilience backbone | Not yet connected to bridge domain naming or registry wiring |

## 4. Mandala-Computing: substrate consumer entry points

Mandala-Computing is the clearest downstream consumer of the bridge ecosystem. The file `sovereign_integration.py` already shows how octahedral glyph states, physical-field semantics, constraint validation, and resonance energy are meant to feed into a computational substrate.[4] This means Mandala-Computing is the repository most ready to **consume** outputs from the updated bridge registry rather than define those outputs itself.

The discrepancy is openly documented in `Integration.md`. That document explicitly says that the **bridge-to-substrate adapter** exists only in examples and is “not integrated into the main engines.” That is extremely useful because it separates aspiration from implementation. In practice, it means Mandala-Computing has a strong conceptual slot for the updated bridge repository, but it still lacks one thin production import layer that turns a registered bridge output into a main-engine substrate state.[4] [6]

> Mandala-Computing already knows what to do **after** a bridge output becomes a substrate state. The missing piece is a stable adapter that turns the updated bridge repo’s canonical encoder outputs into that substrate representation.[4] [6]

The example and documentation structure suggests the right future direction: instead of keeping `bridge_to_substrate_adapter` as example-only code, Mandala-Computing should import from the updated bridge repository’s registry or silicon bridge chooser and expose a small production module such as `mandala_bridge_adapter.py`.[1] [4] [6]

| Mandala file | Best integration use | Main discrepancy |
| --- | --- | --- |
| `sovereign_integration.py` | Substrate-side receiver for bridge outputs | Not wired directly to the updated registry |
| `Integration.md` | Honest status / implementation boundary | Admits bridge adapter is example-only |
| `examples/example-bridge-substrate.py` | Demonstration of desired flow | Not promoted into the main engine path |

## 5. Cross-repository entry map

The cleanest near-term entry map is to treat the updated bridge repository as the source of truth, Rosetta as the semantic index, SOMS as the protocol / representation companion, and Mandala-Computing as the substrate execution layer.[1] [2] [3] [4]

| From | To | Recommended entry point | Why this is the cleanest path |
| --- | --- | --- | --- |
| Rosetta-Shape-Core | Updated bridge repo | `Silicon/core/bridges/domain_bridge_catalog.py` | Rosetta can index bridge domains without duplicating encoders |
| SOMS | Updated bridge repo | `solver_registry.py` and selected `bridges/*.py` encoders | SOMS already shares encoder language and token logic |
| SOMS | Updated bridge repo silicon layer | `Silicon/core/bridges/hardware_modules.py` | Gives SOMS a selective import surface instead of monolithic copying |
| Mandala-Computing | Updated bridge repo | `solver_registry.py` | Registry gives a stable named bridge output contract |
| Mandala-Computing | Silicon bridge layer | `Silicon/core/bridges/__init__.py` and `hardware_modules.py` | Cleanest hardware / silicon-facing import path |
| Rosetta-Shape-Core | SOMS | `src/geometric_encoder.py` metadata only | Useful as shared representation reference, but should not become a second source of truth |

## 6. Main discrepancies to note now

The first discrepancy is **planned-vs-implemented integration drift**. Rosetta’s bridge guide and Mandala’s integration document both describe stronger cross-repo bridge flows than their present package layouts actually expose.[5] [6]

The second discrepancy is **monolithic versus layered packaging**. SOMS’s `geometric_bridge.py` gathers protocol, modality, decoding, and bridge-target logic into one file, while the updated bridge repository has moved toward a layered model: registry, domain encoders, silicon adapters, and navigation catalogs. This is not merely stylistic; it affects where imports should terminate.[1] [3]

The third discrepancy is **representation mismatch risk**. SOMS’s `GeometricEncoder` is explicitly ported from the bridge ecosystem, but it still encodes a narrower token surface than the updated bridge repository’s broader domain registry and silicon-layer bridge catalog. That means SOMS is a good compatibility layer, but not yet a full mirror of the new repo structure.[1] [3]

The fourth discrepancy is **semantic-role confusion around resilience**. SOMS has a clean substrate-independent resilience core, while the updated bridge repo now distinguishes `community` as a concrete bridge and `resilience` as a broader cross-substrate notion. That is conceptually compatible, but the naming and adapter boundaries are not yet unified across repos.[1] [3]

The fifth discrepancy is **example-only substrate adaptation** in Mandala-Computing. The docs explicitly say the bridge-to-substrate adapter exists in examples but is not wired into the main engines. This is the single clearest engineering gap if the goal is a real end-to-end flow from bridge encoding into substrate computation.[6]

## 7. Recommended next fixes

The most efficient next step would be to create one tiny **shared bridge contract** and then wire each repository to that contract instead of trying to make all four repositories import each other directly. That contract should minimally define the bridge domain name, encoder class path, payload width, optional silicon entry point, and substrate-adapter hints. Most of that information already exists in the updated bridge repository’s registry and domain catalog.[1]

A practical four-step sequence would be as follows.

| Priority | Fix | Best home | Expected effect |
| --- | --- | --- | --- |
| 1 | Create a machine-readable bridge manifest derived from the updated registry | Updated bridge repo | Gives all other repos one source of truth |
| 2 | Add a Rosetta adapter that ingests the manifest into `_bridges.py` | Rosetta-Shape-Core | Makes Rosetta the semantic navigator for real bridge domains |
| 3 | Split SOMS integration into `geometric_encoder` compatibility plus optional registry-backed imports | SOMS | Preserves local protocol strengths while reducing drift |
| 4 | Promote Mandala’s bridge-to-substrate example into a main-engine adapter | Mandala-Computing | Creates the first true end-to-end cross-repo execution path |

If you want the shortest path to actual cross-repo functionality, I would start with **Mandala-Computing first**, because its own documentation already names the missing production adapter. If you want the shortest path to cleaner navigation across the whole ecosystem, I would start with **Rosetta first**, because it is the natural place to publish a cross-repo bridge map.[5] [6]

## References

[1]: https://github.com/JinnZ2/Geometric-to-Binary-Computational-Bridge "JinnZ2/Geometric-to-Binary-Computational-Bridge"
[2]: https://github.com/JinnZ2/Rosetta-Shape-Core "JinnZ2/Rosetta-Shape-Core"
[3]: https://github.com/JinnZ2/Sovereign-Octahedral-Mandala-Substrate-SOMS- "JinnZ2/Sovereign-Octahedral-Mandala-Substrate-SOMS-"
[4]: https://github.com/JinnZ2/Mandala-Computing "JinnZ2/Mandala-Computing"
[5]: https://github.com/JinnZ2/Rosetta-Shape-Core/blob/main/docs/unified-bridge-integration-guide.md "Rosetta-Shape-Core: unified-bridge-integration-guide.md"
[6]: https://github.com/JinnZ2/Mandala-Computing/blob/main/Integration.md "Mandala-Computing: Integration.md"
[7]: https://github.com/JinnZ2/Sovereign-Octahedral-Mandala-Substrate-SOMS-/blob/main/src/geometric_encoder.py "SOMS: geometric_encoder.py"
[8]: https://github.com/JinnZ2/Rosetta-Shape-Core/blob/main/src/rosetta_shape_core/_bridges.py "Rosetta-Shape-Core: _bridges.py"

## Addendum: contract expansion after registry-gap closure

Since the initial version of this report, the canonical bridge contract surface in the updated bridge repository has been expanded to include **biomachine**, **coop**, **cyclic**, and **vortex** across `solver_registry.py`, `bridge_contract_manifest.json`, `Silicon/core/bridges/adapters.py`, and `Silicon/core/bridges/domain_bridge_catalog.py`.

This changes the practical cross-repository recommendation in one important way. Related repositories should now treat those four domains as part of the canonical source surface rather than as local or inferred extensions. At the same time, downstream consumers should not assume that every bridge emits a fixed-width binary payload: the `vortex` bridge is intentionally documented as **dynamic: 4 bits per registered slot**, which means manifest-aware consumers should read per-domain contract metadata instead of hardcoding width assumptions.

| Newly canonical domain | Best downstream interpretation |
| --- | --- |
| biomachine | Physical maintenance / regeneration bridge for machine-state stress and recovery |
| coop | Contextual trust / redistribution bridge for cooperative-network dynamics |
| cyclic | Topological cyclic-field bridge for resonance and phase-evolution structure |
| vortex | Topological-memory bridge with dynamic per-slot payload width |

In other words, the updated bridge repository is now an even stronger source of truth for related repositories, because it no longer exposes these four families only as latent modules on disk; it exposes them as named contract domains. The remaining cross-repository task is therefore adapter uptake, not domain discovery.
