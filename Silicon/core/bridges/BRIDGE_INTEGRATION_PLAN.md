# Bridge Integration Plan

The repository currently has **two bridge layers** with different roles.

| Layer | Role | Keep as source of truth? | Reason |
| --- | --- | --- | --- |
| `bridges/` | Domain-facing physical and conceptual bridge encoders | **Yes** | This is where the sound, electric, gravity, community, pressure, magnetic, thermal, light, wave, and chemical bridge implementations already live. |
| `Silicon/core/bridges/` | Silicon-facing physics, reduction, and bridge-to-bridge adapters | **Yes, but narrower** | This folder should expose silicon-specific bridge helpers, plus adapter entry points into the domain-facing bridge layer. |

The navigation-first strategy is therefore **not** to duplicate both directories. Instead, the top-level `bridges/` directory should remain the home of the primary bridge encoders, while `Silicon/core/bridges/` should gain a small set of adapter modules that make those encoders available from the silicon layer.

## Recommended structure

| Location | Purpose |
| --- | --- |
| `bridges/*.py` | Primary domain encoders and bridge orchestration code |
| `Silicon/core/bridges/adapters.py` | Shared import-safe adapter layer from silicon code into top-level bridge encoders |
| `Silicon/core/bridges/domain_bridge_catalog.py` | Navigation index describing the available bridge families and their mappings |
| `Silicon/core/bridges/__init__.py` | Re-export only silicon-native bridge utilities plus adapter access points |

## Repair priorities

| Priority | Action |
| --- | --- |
| 1 | Add explicit adapters for the bridges the user called out: sound, electric, gravity, community, and geometric fiber / holonomy-related mapping |
| 2 | Update docstrings in those encoders so they describe **field coupling** rather than simplistic sensor-data ingestion |
| 3 | Run repository-wide compile/import validation on both `bridges/` and `Silicon/core/bridges/` |
| 4 | Fix any remaining copied import issues in adapter, orchestrator, or registry code |

## Guiding principle

The code should be easy to navigate by question.

If a reader asks, "How is sound encoded?" they should go to `bridges/sound_encoder.py`.
If they ask, "How does the silicon layer use that bridge?" they should go to `Silicon/core/bridges/adapters.py`.
If they ask, "What bridge families exist and where are they wired?" they should go to `Silicon/core/bridges/domain_bridge_catalog.py`.
