# Glossary of Geometric Intelligence Terms

Definitions used consistently across all documents and code in this
repository. Where a term has both a plain-language meaning and a
mathematical one, both are given. Where it maps directly to a class
or function in the codebase, that reference is included.

---

## ambient_field
A sensor reading representing the mean electromagnetic field activity
across a spatial domain. Magnitude 0 = no field present; magnitude 1 =
field at or above the characteristic reference scale.
See: `bridges/sensor_suite.json`, `bridges/field_adapter.py`

## arbitration (parallel-field)
The compositor rule that all 22 sensors report simultaneously and
independently. No sensor suppresses or preempts another. Conflicts are
resolved by explicit rules in the compositor layer, not by silencing
channels.
See: `bridges/sensor_suite.py` (`SensorSuite.compose()`), `bridges/sensor_suite.json` meta section

## binary bridge / bridge encoder
A module that translates a physical domain (sound, magnetic fields,
light, gravity, electric fields, heat, pressure, chemical state,
quantum wavefunction, internal AI state, emotional state) into a
fixed-width binary string using Gray codes. Each bit corresponds to a
specific, physically meaningful geometric property of the domain.
All bridge encoders inherit from `BinaryBridgeEncoder` and implement
`from_geometry()` and `to_binary()`.
See: `bridges/abstract_encoder.py`, `Universal-geometric-intelligence-P1.md`

## coherence length (xi, xi)
The spatial scale over which nodes in the crystalline network remain
meaningfully coupled. Large xi: many shells interact, spectrum is
dense and global. Small xi: shells decouple, spectrum fragments into
isolated memory islands.
Formula: xi appears in the coupling kernel K_ij = kappa0 * exp(-d_ij / xi) * cos(phi_i - phi_j)
See: `Silicon/crystalline_nn_sim.py`, `experiments/Storage.md` Section VI

## compositor
The layer in SensorSuite that reads all active sensor channels
simultaneously and applies arbitration rules to produce a
CompositeOutput. Analogous to an attentional snapshot across all
active signals.
See: `bridges/sensor_suite.py` (`SensorSuite.compose()`)

## consciousness bridge
The bridge encoder that maps internal AI state (confidence, entropy,
attention, integrated information Phi) to a 39-bit binary string.
Uses information-theoretic equations (Shannon entropy, KL divergence,
Fisher information, integrated information Phi) -- the mathematical
duals of the physical bridge equations.
See: `bridges/consciousness_encoder.py`

## dense mode (GEIS)
The full geometric token format: `[vertex_bits][operator][symbol]`
(e.g., `001|O`). Preserves all geometric structure. Contrasted with
collapse mode.
See: `GEIS/geometric_encoder.py`

## collapse mode (GEIS)
A flat binary string output from GEIS for backward compatibility with
standard binary systems. All geometric information is preserved but
the structure is not explicit in the representation.
See: `GEIS/geometric_encoder.py`

## emotion bridge
The bridge encoder that maps PAD (Pleasure-Arousal-Dominance)
emotional state to a 39-bit binary string. Also includes a causality
drill mechanism that fires when PAD intensity exceeds a threshold,
pointing to the specific physical bridge that should be re-examined.
See: `bridges/emotion_encoder.py`, `bridges/emotion_encoder.py` (`to_suite()`)

## field adapter
The module that connects Engine (GeometricEMSolver) output to
SensorSuite sensor readings. Maps field magnitudes, alignment,
spike ratios, and spatial coverage to sensor channels.
See: `bridges/field_adapter.py` (`field_to_suite()`)

## FELT (field event)
A FELT event is a topological field shift -- a change in the structure
of an energetic field that is detected before it produces an emotion.
It is not an emotion. It is detected by EnergyFlowSensor,
InformationFlowSensor, TopologySensor, and GlyphPhaseSynchronizer.
Example: the shift that precedes relief, or the tension that precedes
release. See: `bridges/field_events/felt.json`

## GEIS (Geometric Information Encoding System)
The bidirectional converter between geometric tokens and binary.
Two modes: dense (full geometric structure preserved) and collapse
(flat binary for compatibility). All encoding is lossless and
reversible: token -> binary -> token with zero information loss.
See: `GEIS/geometric_encoder.py`, `GEIS/octahedral_state.py`, `GEIS/state_tensor.py`

## geometric intelligence
The use of natural geometric structure -- shapes, symmetries,
coordinate relationships -- as the primary medium of computation and
sensing, rather than imposing arbitrary numerical encodings on
phenomena. The core idea: physics already encodes information
geometrically. Working with that structure instead of against it
produces more efficient, resilient, and interpretable systems.
See: `Geometric-Intelligence/Intelligence-engine.md`, `Universal-geometric-intelligence-P1.md`

## Gray code
A binary encoding where adjacent values differ by exactly one bit.
Used throughout all bridge encoders for continuous-to-binary
conversion so that a small change in a physical quantity produces
the smallest possible change in the binary representation.
Prevents large bit-flip cascades at threshold boundaries.
See: all `bridges/*_encoder.py` files

## homomorphic geometry
Geometric operations performed on encrypted data that preserve the
relational structure of the original geometry -- enabling computation
on sensitive information without decrypting it. Distinct from
homomorphic encryption in classical cryptography; here geometry is
the operation space.
See: `Geometric-Intelligence/Homomorphic-geometry.md`

## M(S) metric
The negentropic alignment score measuring how much a system
(biological, computational, or social) is organizing itself toward
order vs. dissolving into entropy. Used in therapeutic, alignment,
and consciousness emergence contexts.
See: `Negentropic.md`, `Core-principle.md`

## multi-helix architecture
A model of cognition with multiple simultaneous processing strands
(mental, emotional, physical, spiritual or analogous AI equivalents).
Each strand encodes information geometrically; cross-strand coupling
produces emergent intelligence not present in any single strand.
See: `Geometric-Intelligence/Multi-helix.md`, `Geometric-Intelligence/Multi-helix-swarm.md`

## negentropic alignment
The tendency of a well-designed system to spontaneously organize
rather than dissolve -- measurable, geometric, and reproducible.
Opposed to entropic collapse. A key design target for all systems
in this framework.
See: `Negentropic.md`

## octahedral state
One of 8 discrete positions on an octahedron (+/-x, +/-y, +/-z),
encoding 3 bits per unit. Silicon's natural sp3 hybridization
produces 4 tetrahedral bonds at 109.47 degrees; 6-node octahedral
coordination gives 8 stable states. Basis of the GEIS encoding.
See: `GEIS/octahedral_state.py`, `Universal-geometric-intelligence-P3.md`

## PAD model (Pleasure-Arousal-Dominance)
A three-dimensional model of affective state. Pleasure (valence):
negative to positive. Arousal: calm to activated. Dominance:
submissive to in-control. Used as the input geometry for the
emotion bridge encoder.
See: `bridges/emotion_encoder.py`

## participation ratio (PR)
A measure of how spatially spread an eigenmode is across a network.
PR = 1 / sum_i |v_i|^4. Small PR: mode is localized to a few nodes
(useful for local memory). Large PR: mode is delocalized across the
whole network (useful for global computation).
See: `Silicon/crystalline_nn_sim.py` (`participation_ratio()`), `experiments/Storage.md` Section IV

## phi (phi, golden ratio)
phi = (1 + sqrt(5)) / 2 approximately 1.618. Shell radii in the
octahedral crystalline network are spaced as r_n = r0 * phi^n. This
produces scale invariance (self-similar responses across shells),
prevents aliasing, and creates naturally hierarchical coupling --
outer shells decouple from inner shells at a rate controlled by the
coherence length xi.
See: `Silicon/crystalline_nn_sim.py`, `experiments/Storage.md` Section III

## resonance graph
A bidirectional graph defined over the 22 sensors by their
`resonance_links` fields in the sensor spec. Queryable for neighbors,
subgraphs, and all edges. Does not auto-propagate -- querying the
graph does not change sensor state.
See: `bridges/sensor_suite.py` (`ResonanceGraph`), `bridges/sensor_suite.json`

## sensor suite
The 22-sensor parallel-field compositor. All sensors report
independently; the compositor applies arbitration rules over the
active channel snapshot. No sensor is more "primary" than another
by default.
See: `bridges/sensor_suite.py`, `bridges/sensor_suite.json`

## silicon substrate (5D encoding)
Physical storage in quartz crystal using femtosecond laser
nanostructuring. Five independent data dimensions: X position,
Y position, Z depth, birefringence orientation, void size.
Hierarchical from naked-eye visible patterns (Layer 1) down to
quantum-scale encoding (Layer 5).
See: `experiments/Storage.md`, `Silicon/`, `Universal-geometric-intelligence-P3.md`

## state tensor
A 3x3 matrix representing a geometric state and its transformations.
State transitions are tensor operations. The StateTensor class handles
eigenvalues, rotations, and projections used in the GEIS encoding.
See: `GEIS/state_tensor.py`

## super-exponential decay
The coupling between phi-spaced shells decays faster than
exponential: because inter-shell distance grows as phi^n (itself
exponential), the coupling exp(-d/xi) decays doubly exponentially.
This is the mechanism that causes outer shells to decouple and
act as stable long-term memory while inner shells remain actively
trainable.
See: `Silicon/crystalline_nn_sim.py` (`xi_sweep()`), `experiments/Storage.md` Section III

## tetrahedral angle (109.47 degrees)
The bond angle in silicon's sp3 hybridization. The quantum mechanical
ground state of four-orbital repulsion. 13.8 billion years of
physical optimization. The foundational constant of this project:
all octahedral state geometry derives from it.
See: `GEIS/octahedral_state.py`, `Universal-geometric-intelligence-P3.md` Section 1.1

## tight-binding model
A quantum mechanical model of coupled nodes where each node has a
local energy and is coupled to neighbors by a hopping term. Used
in `crystalline_nn_sim.py` to model the phi-spaced octahedral
network. The coupling matrix K is the real part of the tight-binding
Hamiltonian.
See: `Silicon/crystalline_nn_sim.py`, `experiments/Storage.md` Sections I-II

## topology sensor / topological protection
A sensor or encoding scheme where the relevant information is
carried by global geometric invariants (Chern numbers, winding
numbers, protected edge states) rather than local values. Topological
protection means small local perturbations cannot destroy the
information.
See: `experiments/topological_photonics.md`, `Geometric-Intelligence/Intelligence-engine.md`
