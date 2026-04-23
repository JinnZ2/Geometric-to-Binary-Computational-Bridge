# Bridge Registry Gap Report

## Summary

The main registry, canonical manifest, silicon adapter layer, and silicon bridge catalog now agree on an expanded bridge surface. In addition to the original physical, contextual, cognitive, and geometric-fiber entries, the repository now exposes **biomachine**, **coop**, **cyclic**, and **vortex** through stable `encode_*` registry names and matching catalog entries.

The practical effect is that the earlier high-priority wiring gap has been closed. The remaining open work is no longer the absence of these bridge families from the contract surface, but rather continued clarification of documentation, downstream consumer adoption, and any later decision about whether further experimental bridge families should be promoted.

## Currently wired bridge domains

| Domain | Registry entry | Contract note |
| --- | --- | --- |
| magnetic | `encode_magnetic` | Fixed-width physical bridge |
| light | `encode_light` | Fixed-width physical bridge |
| sound | `encode_sound` | Fixed-width physical bridge |
| gravity | `encode_gravity` | Fixed-width physical bridge |
| electric | `encode_electric` | Fixed-width physical bridge |
| wave | `encode_wave` | Fixed-width physical bridge |
| thermal | `encode_thermal` | Fixed-width physical bridge |
| pressure | `encode_pressure` | Fixed-width physical bridge |
| chemical | `encode_chemical` | Fixed-width physical bridge |
| community | `encode_community` | Concrete human-organism resilience instantiation |
| resilience | `encode_resilience` | Substrate-independent resilience bridge |
| biomachine | `encode_biomachine` | Physical maintenance and regeneration bridge |
| coop | `encode_coop` | Contextual trust / redistribution bridge |
| cyclic | `encode_cyclic` | Topological / cyclic field bridge |
| vortex | `encode_vortex` | **Dynamic payload**: 4 bits per registered slot |
| geometric_fiber | `encode_geometric_fiber` | Fiber / holonomy bridge |
| consciousness | `encode_consciousness` | Cognitive meta-layer |
| emotion | `encode_emotion` | Cognitive meta-layer |

## Status of the previously unwired priority set

| Bridge | Current status | Notes |
| --- | --- | --- |
| biomachine | Wired | Added to registry, manifest, adapters, and silicon catalog as a physical bridge tied to seal stress and regeneration dynamics. |
| coop | Wired | Added as a contextual bridge that maps trust propagation and resource flow into a thermal-style coupling model. |
| cyclic | Wired | Added as a topological bridge for cyclic field evolution, resonance, phase transition, and regeneration structure. |
| vortex | Wired | Added across contract surfaces with an explicit note that its binary payload is dynamic rather than fixed-width. |

## Remaining bridge-surface questions

These are now mostly **policy and downstream-integration questions** rather than missing-wire problems.

| Topic | Why it still matters |
| --- | --- |
| Dynamic payload handling for `vortex` | Downstream consumers should read manifest metadata rather than assume every bridge emits a fixed-width payload. |
| Cross-repo adoption | Related repositories should consume the manifest / helper layer instead of hardcoding domain lists. |
| Experimental bridge promotion | Modules such as alternative-compute or other experimental bridge files should remain outside the canonical contract until their interfaces stabilize. |
| Hardware overlap boundaries | Hardware-adjacent modules should stay distinguished from bridge domains unless they expose a stable encoder contract. |

## Practical conclusion

The earlier navigation and registry gap for **biomachine**, **coop**, **cyclic**, and **vortex** has been resolved. The canonical source repository now exposes those families through the registry, manifest, silicon adapter layer, and domain catalog in one aligned surface.

The main caution is simply that **vortex is canonical but variable-width**. That distinction is now made explicit in the manifest and registry metadata so related repositories can adapt to it cleanly instead of assuming a universal fixed payload length.
