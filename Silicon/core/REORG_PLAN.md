# Silicon Core Reorganization Plan

This note captures the navigation-first layout for `Silicon/core` before the file moves are applied. The goal is to make the directory easier to browse by topic while keeping imports workable through explicit package structure and compatibility updates.

| New subfolder | Purpose | Planned modules |
| --- | --- | --- |
| `analysis/` | Mathematical models, phase maps, and derived computational analysis | `core_equations.py`, `physics_derivations.py`, `phase_diagram.py`, `computational_phase_transition.py`, `lcea_analysis.py` |
| `geometry/` | Octahedral and tensor geometry primitives | `octahedral_sim.py`, `octahedral_tensor.py`, `tetrahedral_symmetry.py`, `monodromy_test.py` |
| `bridges/` | Cross-domain integration, encoding, and bridge protocols | `hardware_bridge.py`, `gies_encoder.py`, `silicon_gies_bridge.py`, `magnetic_bridge_protocol.py`, `pipeline.py`, `fret_coulomb_analysis.py` |
| `systems/` | Storage, memory, thermal, field, and energy subsystems | `crystalline_storage.py`, `energy_framework.py`, `field_propulsion.py`, `thermal_coupling.py`, `topological_memory.py` |

The refactor should also repair the three concrete import-time issues already found: missing typing imports in `monodromy_test.py`, missing imports and dependencies in `phase_diagram.py`, and the broken external `silicon_state` dependency in `silicon_gies_bridge.py`.

The preferred compatibility strategy is to update repository-internal imports to the new package paths and leave lightweight root-level shims only where that meaningfully reduces breakage risk.
