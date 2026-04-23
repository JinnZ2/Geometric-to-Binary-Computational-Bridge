# Silicon Core Package Guide

The `Silicon/core` package has been reorganized for **easy navigation**. Instead of a single flat directory, the modules are grouped by role so it is easier to find the right layer of the stack.

| Folder | Purpose | Key modules |
| --- | --- | --- |
| `analysis/` | Mathematical derivations, phase maps, and computational classification | `core_equations.py`, `physics_derivations.py`, `phase_diagram.py`, `computational_phase_transition.py`, `lcea_analysis.py` |
| `geometry/` | Octahedral state geometry, tensors, and symmetry tools | `octahedral_sim.py`, `octahedral_tensor.py`, `tetrahedral_symmetry.py`, `monodromy_test.py` |
| `bridges/` | Cross-domain bridge logic, hardware links, and encoding pipelines | `hardware_bridge.py`, `silicon_gies_bridge.py`, `magnetic_bridge_protocol.py`, `gies_encoder.py`, `pipeline.py`, `fret_coulomb_analysis.py` |
| `systems/` | Storage, energy, thermal, field, and memory subsystems | `crystalline_storage.py`, `energy_framework.py`, `field_propulsion.py`, `thermal_coupling.py`, `topological_memory.py` |

The refactor also fixed several likely cellphone copy-paste problems. The concrete repairs include missing typing imports, broken import-time dependencies, and stale module paths left behind by earlier copy-and-paste assembly.

For navigation, start with the folder that matches your question. If you are studying **how states are represented**, begin in `geometry/`. If you are tracing **how geometry becomes hardware or encoded output**, begin in `bridges/`. If you want **equations and phase behavior**, begin in `analysis/`. If you are looking for **subsystem models**, begin in `systems/`.
