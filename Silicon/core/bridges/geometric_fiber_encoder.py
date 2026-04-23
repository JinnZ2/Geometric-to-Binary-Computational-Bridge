# bridges/geometric_fiber_encoder.py
"""
Geometric Fiber Bundle Encoder
===============================
Encodes the octahedral fiber bundle structure into binary using
the Z₂³ torsor holonomy, connection 1-form, and parallel transport.

This is the META-ENCODER: it encodes not just physical measurements,
but the topological relationship BETWEEN measurements—specifically,
whether two identical silicon states arrived at by different paths
have the same or different octahedral encodings.

The binary output captures:
- Whether the bundle is trivial or nontrivial in a given region
- Which Z₂³ holonomy elements appear around phase boundaries
- The holonomy group structure (subgroup of Z₂³)

Equations implemented
---------------------
  Holonomy:          H(γ) ∈ Z₂³ for closed loop γ
  Curvature:         Ω = dA + A ∧ A  (discretized as transition functions)
  Chern class:       c₁ (mod 2 reduction of the curvature)
  Section obstruction: Whether a global section exists (bundle triviality)

Bit layout
----------
Per loop test (39 bits, compatible with Geometric Binary Bridge):
  Section A (18 bits): Holonomy group structure
    [trivial       1b]   bundle is trivial (1) or nontrivial (0)
    [holonomy_bits 3b]   which Z₂³ elements appear (X, Y, Z flips)
    [group_order   3b]   order of holonomy group (1, 2, 4, or 8)
    [affected_bits 3b]   which qubits are holonomy-sensitive
    [curvature_mag 2b]   curvature concentration (0-3)
    [regime_bound  3b]   enclosed regime types (metallic, quantum, defect)
    [loop_scale    3b]   log scale of loop in phase space

  Section B (9 bits): Parallel transport along path
    [path_length   3b]   number of regime transitions
    [transport_cost 3b]  mean transport cost (Gray-coded)
    [stability     3b]   path stability under perturbation

  Section C (6 bits): Topological invariants
    [chern_mod2   1b]    first Chern class (mod 2)
    [obstruction  2b]    section obstruction class
    [winding      3b]    winding number around phase boundary

  Section D (6 bits): Geometric phase
    [berry_phase  3b]    Berry phase (discretized)
    [anomaly      3b]    anomaly detection bits

Usage:
    from bridges.geometric_fiber_encoder import GeometricFiberEncoder
    
    encoder = GeometricFiberEncoder()
    encoder.from_fiber_bundle(holonomy_results)
    binary = encoder.to_binary()
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set, Any
from enum import IntEnum

from bridges.abstract_encoder import BinaryBridgeEncoder
from bridges.common import gray_bits as _gray_bits

# Import the fiber bundle structure
from octahedral_fiber_bundle import (
    BitFlip, OctahedralTorsor, Connection, HolonomyResult,
    compute_monodromy, compute_holonomy_group,
    generate_loop_around_metallic_breakdown,
    generate_loop_around_quantum_boundary,
    generate_loop_around_defect_singularity,
)


# ======================================================================
# Band thresholds for geometric quantities
# ======================================================================

_HOLONOMY_ORDER_BANDS = [0.0, 1.0, 2.0, 4.0, 8.0]  # Group orders
_CURVATURE_BANDS = [0.0, 0.125, 0.25, 0.5, 0.75, 1.0]  # Normalized curvature
_PATH_LENGTH_BANDS = [0.0, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 200.0]
_TRANSPORT_COST_BANDS = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 100.0]
_LOOP_SCALE_BANDS = [0.0, 0.1, 0.3, 0.5, 0.7, 1.0, 1.5, 3.0]  # log10 scale
_WINDING_BANDS = [0.0, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 100.0]
_BERRY_PHASE_BANDS = [0.0, 0.39, 0.78, 1.57, 2.36, 3.14, 4.71, 6.28]  # radians


# ======================================================================
# Geometric encoder class
# ======================================================================

class GeometricFiberEncoder(BinaryBridgeEncoder):
    """
    Encodes the octahedral fiber bundle topology into binary.
    
    This is the meta-encoder: it encodes the RELATIONSHIPS between
    measurements that the regular encoders process independently.
    
    Input: Holonomy results from octahedral_fiber_bundle.py
    Output: 39-bit binary string compatible with Geometric Binary Bridge
    """
    
    def __init__(self):
        super().__init__("geometric_fiber")
        self.holonomy_results: Dict[str, HolonomyResult] = {}
        self.holonomy_group: Set[BitFlip] = set()
        self.bundle_topology: str = "unknown"
    
    def from_fiber_bundle(self, 
                          holonomy_results: Dict[str, HolonomyResult],
                          holonomy_group: Set[BitFlip] = None):
        """
        Load holonomy computation results.
        
        Args:
            holonomy_results: Dict mapping regime boundary names to HolonomyResult
            holonomy_group: Set of BitFlip elements forming the holonomy group
        """
        self.holonomy_results = holonomy_results
        self.holonomy_group = holonomy_group or set()
        
        # Classify bundle topology
        group_order = len(self.holonomy_group)
        if group_order == 1:
            self.bundle_topology = "trivial"
        elif group_order == 2:
            self.bundle_topology = "Z2_twisted"
        elif group_order == 4:
            self.bundle_topology = "Z2xZ2_twisted"
        elif group_order == 8:
            self.bundle_topology = "full_Z2cubed"
        else:
            self.bundle_topology = f"subgroup_order_{group_order}"
        
        return self
    
    def to_binary(self) -> str:
        """
        Encode fiber bundle topology into 39-bit binary string.
        
        Returns:
            39-bit binary string in Geometric Binary Bridge format
        """
        bits = []
        
        # Aggregate across all holonomy results
        n_results = len(self.holonomy_results)
        
        if n_results == 0:
            # Empty: all zeros
            return "0" * 39
        
        # ── Section A: Holonomy Group Structure (18 bits) ──
        
        # Is any result nontrivial?
        any_nontrivial = any(
            not result.is_trivial for result in self.holonomy_results.values()
        )
        bits.append("1" if not any_nontrivial else "0")  # trivial = 1
        
        # Which bit flips appear as holonomies? (3 bits: X, Y, Z)
        all_holonomies = set()
        for result in self.holonomy_results.values():
            all_holonomies.add(result.holonomy)
        
        has_x = any(h.value[0] == 1 for h in all_holonomies)
        has_y = any(h.value[1] == 1 for h in all_holonomies)
        has_z = any(h.value[2] == 1 for h in all_holonomies)
        bits.append("1" if has_x else "0")
        bits.append("1" if has_y else "0")
        bits.append("1" if has_z else "0")
        
        # Holonomy group order (3 bits Gray)
        group_order = len(self.holonomy_group) if self.holonomy_group else len(all_holonomies) + 1
        bits.append(_gray_bits(float(group_order), _HOLONOMY_ORDER_BANDS))
        
        # Affected qubits count (3 bits Gray)
        affected_count = sum(1 for result in self.holonomy_results.values()
                           if not result.is_trivial)
        bits.append(_gray_bits(float(affected_count), [0, 0.5, 1, 2, 3, 5, 8, 100]))
        
        # Curvature magnitude (2 bits: 0-3)
        # Curvature ∝ fraction of loops with nontrivial holonomy
        if n_results > 0:
            curvature = sum(1 for r in self.holonomy_results.values() 
                          if not r.is_trivial) / n_results
        else:
            curvature = 0.0
        curvature_level = min(3, int(curvature * 4))
        bits.append(format(curvature_level, '02b'))
        
        # Enclosed regime types (3 bits)
        all_regimes = set()
        for result in self.holonomy_results.values():
            all_regimes.update(result.enclosed_regimes)
        
        regime_bits = 0
        if "metallic" in all_regimes or "semiconductor" in all_regimes:
            regime_bits |= 0b001
        if "quantum" in all_regimes or "coherent" in all_regimes:
            regime_bits |= 0b010
        if "defect" in all_regimes or "disordered" in all_regimes:
            regime_bits |= 0b100
        bits.append(format(regime_bits, '03b'))
        
        # Loop scale (3 bits Gray)
        # Use the largest loop's parameter range
        max_scale = 1.0
        for key, result in self.holonomy_results.items():
            if hasattr(result, 'loop_scale'):
                max_scale = max(max_scale, result.loop_scale)
        bits.append(_gray_bits(max_scale, _LOOP_SCALE_BANDS))
        
        # ── Section B: Parallel Transport (9 bits) ──
        
        # Path length: total regime transitions across all loops
        total_transitions = sum(
            len(result.path_transitions) for result in self.holonomy_results.values()
        )
        bits.append(_gray_bits(float(total_transitions), _PATH_LENGTH_BANDS))
        
        # Transport cost: mean cost across all transitions
        # (Transport cost is implicit in number of transitions;
        #  more transitions = higher transport cost)
        mean_cost = total_transitions / max(n_results, 1)
        bits.append(_gray_bits(mean_cost, _TRANSPORT_COST_BANDS))
        
        # Path stability: are holonomy results consistent across start states?
        # Check if different start states give consistent holonomies
        all_start_states_consistent = True
        for key, result in self.holonomy_results.items():
            if result.is_trivial and any(
                not r.is_trivial for k, r in self.holonomy_results.items() if k != key
            ):
                all_start_states_consistent = False
                break
        
        stability = 1.0 if all_start_states_consistent else 0.5
        bits.append(_gray_bits(stability, [0.0, 0.25, 0.5, 0.75, 1.0]))
        
        # ── Section C: Topological Invariants (6 bits) ──
        
        # Chern class mod 2 (1 bit)
        # Nontrivial iff odd number of nontrivial holonomy elements
        chern_mod2 = sum(1 for r in self.holonomy_results.values() 
                        if not r.is_trivial) % 2
        bits.append("1" if chern_mod2 == 1 else "0")
        
        # Section obstruction class (2 bits)
        # 0: no obstruction (global section exists)
        # 1: Z₂ obstruction
        # 2: Z₂×Z₂ obstruction
        # 3: Full Z₂³ obstruction (no global section)
        obstruction_level = min(3, len(all_holonomies) - 1) if all_holonomies else 0
        bits.append(format(obstruction_level, '02b'))
        
        # Winding number (3 bits Gray)
        # Total winding around all phase boundaries
        total_winding = sum(
            len(result.affected_qubits) for result in self.holonomy_results.values()
        )
        bits.append(_gray_bits(float(total_winding), _WINDING_BANDS))
        
        # ── Section D: Geometric Phase (6 bits) ──
        
        # Berry phase (3 bits Gray)
        # Holonomy IS the Berry phase (discretized for Z₂³)
        berry_phase = 0.0
        for result in self.holonomy_results.values():
            if result.holonomy == BitFlip.X_FLIP:
                berry_phase += math.pi
            elif result.holonomy == BitFlip.Y_FLIP:
                berry_phase += math.pi
            elif result.holonomy == BitFlip.Z_FLIP:
                berry_phase += math.pi
            elif result.holonomy != BitFlip.IDENTITY:
                berry_phase += math.pi / 2  # Combined flips
        
        bits.append(_gray_bits(berry_phase % (2*math.pi), _BERRY_PHASE_BANDS))
        
        # Anomaly detection (3 bits)
        # Detects if holonomy violates expected conservation
        anomaly_flags = 0
        for key, result in self.holonomy_results.items():
            # Check for unexpected holonomy combinations
            if (result.holonomy == BitFlip.X_FLIP and 
                "quantum" not in str(result.enclosed_regimes).lower()):
                anomaly_flags |= 0b001
            if (result.holonomy_order > 2):
                anomaly_flags |= 0b010
            if len(result.affected_qubits) > 2:
                anomaly_flags |= 0b100
        
        bits.append(format(anomaly_flags, '03b'))
        
        self.binary_output = "".join(bits)
        return self.binary_output
    
    def decode_holonomy_from_binary(self, binary: str) -> Dict[str, Any]:
        """
        Decode a binary string back into holonomy information.
        
        This is the inverse operation: reconstruct the fiber bundle
        topology from the 39-bit encoding.
        
        Args:
            binary: 39-bit binary string
            
        Returns:
            Dict with decoded holonomy structure
        """
        if len(binary) < 39:
            raise ValueError(f"Need 39 bits, got {len(binary)}")
        
        pos = 0
        
        # Section A
        is_trivial = binary[pos] == '1'; pos += 1
        has_x_flip = binary[pos] == '1'; pos += 1
        has_y_flip = binary[pos] == '1'; pos += 1
        has_z_flip = binary[pos] == '1'; pos += 1
        
        # Reconstruct holonomy elements
        holonomy_elements = set()
        if is_trivial:
            holonomy_elements.add(BitFlip.IDENTITY)
        if has_x_flip:
            holonomy_elements.add(BitFlip.X_FLIP)
        if has_y_flip:
            holonomy_elements.add(BitFlip.Y_FLIP)
        if has_z_flip:
            holonomy_elements.add(BitFlip.Z_FLIP)
        
        # Add combined flips if multiple single flips exist
        if has_x_flip and has_y_flip:
            holonomy_elements.add(BitFlip.X_FLIP @ BitFlip.Y_FLIP)
        if has_x_flip and has_z_flip:
            holonomy_elements.add(BitFlip.X_FLIP @ BitFlip.Z_FLIP)
        if has_y_flip and has_z_flip:
            holonomy_elements.add(BitFlip.Y_FLIP @ BitFlip.Z_FLIP)
        if has_x_flip and has_y_flip and has_z_flip:
            holonomy_elements.add(BitFlip.X_FLIP @ BitFlip.Y_FLIP @ BitFlip.Z_FLIP)
        
        # Skip remaining bits (full decode would parse all fields)
        pos += 14  # Skip to end of Section A (3+12=15 bits from pos)
        
        return {
            "bundle_trivial": is_trivial,
            "holonomy_group": holonomy_elements,
            "group_order": len(holonomy_elements),
            "has_x_holonomy": has_x_flip,
            "has_y_holonomy": has_y_flip,
            "has_z_holonomy": has_z_flip,
            "topology_class": (
                "trivial" if is_trivial else
                f"Z2_{'x' if has_x_flip else ''}{'y' if has_y_flip else ''}{'z' if has_z_flip else ''}_twisted"
            ),
        }


# ======================================================================
# Ternary & Quantum extensions for the fiber bundle
# ======================================================================

class TernaryHolonomyState(IntEnum):
    """
    Three-valued holonomy interpretation.
    
    The binary encoder says "trivial = 1 if holonomy is IDENTITY else 0".
    But holonomy comes in three qualitative types:
    
      TRIVIAL     (−1/0): Bundle is flat. Encoding is path-independent.
                         All fabrication paths give the same result.
                         
      QUANTIZED    (0):   Holonomy is nontrivial but quantized—the same
                         bit flip appears for all loops in a region.
                         This is a stable topological phase.
                         
      ANOMALOUS   (+1):   Holonomy varies with loop geometry—the bundle
                         has curvature singularities. This is the
                         computationally interesting regime where
                         encoding depends on fabrication history.
    """
    TRIVIAL   = -1
    QUANTIZED =  0
    ANOMALOUS = +1
    
    @property
    def physical_meaning(self) -> str:
        return {
            self.TRIVIAL:   "Flat bundle: fabrication history irrelevant",
            self.QUANTIZED: "Quantized holonomy: stable topological memory",
            self.ANOMALOUS: "Anomalous holonomy: history-dependent encoding"
        }[self]


def classify_holonomy_ternary(holonomy_results: Dict[str, HolonomyResult]) -> TernaryHolonomyState:
    """
    Classify the holonomy structure into ternary state.
    
    The key question: is the holonomy the same for all loops?
    
    - Same holonomy (including trivial) for all loops → QUANTIZED or TRIVIAL
    - Different holonomies for different loops → ANOMALOUS
    """
    if not holonomy_results:
        return TernaryHolonomyState.TRIVIAL
    
    holonomies = set(result.holonomy for result in holonomy_results.values())
    
    if len(holonomies) == 1:
        holo = list(holonomies)[0]
        if holo == BitFlip.IDENTITY:
            return TernaryHolonomyState.TRIVIAL
        else:
            return TernaryHolonomyState.QUANTIZED
    else:
        return TernaryHolonomyState.ANOMALOUS


@dataclass
class QuantumFiberBundleState:
    """
    The fiber bundle as a quantum superposition.
    
    Before measurement (holonomy computation), the octahedral state
    at a point exists in superposition over all 8 states:
    
      |S⟩ = Σ c_i |octahedral_state_i⟩
    
    The connection tells us how these amplitudes evolve under
    parallel transport. The holonomy is the geometric phase
    acquired after a closed loop—exactly like a Berry phase.
    
    This is not an analogy. The Z₂³ holonomy IS a Berry phase
    for a discrete quantum system. The octahedral states are
    the computational basis, and the silicon phase space is
    the parameter manifold.
    """
    
    base_point_state: int  # Initial octahedral state
    holonomy_results: Dict[str, HolonomyResult] = field(default_factory=dict)
    
    # Quantum state after parallel transport around all loops
    superposition_amplitudes: Dict[int, complex] = field(default_factory=dict)
    berry_phase_total: float = 0.0
    geometric_entropy: float = 0.0
    
    def __post_init__(self):
        self._compute_superposition()
    
    def _compute_superposition(self):
        """
        Compute the quantum state after all holonomy loops.
        
        Each loop contributes a phase factor to the amplitude
        of the final state. The superposition represents the
        uncertainty in which octahedral state we end up in
        after traversing all fabrication paths.
        """
        if not self.holonomy_results:
            # No loops: state is pure |base_point_state⟩
            self.superposition_amplitudes = {
                i: complex(1.0 if i == self.base_point_state else 0.0, 0)
                for i in range(8)
            }
            return
        
        # Start with equal amplitude for all 8 states
        # (maximal uncertainty before holonomy measurement)
        amplitudes = {i: complex(1.0 / math.sqrt(8), 0) for i in range(8)}
        
        # Each holonomy result shifts the amplitude toward the
        # state we end up in after that loop
        for key, result in self.holonomy_results.items():
            # The holonomy tells us which state we reach from base_point_state
            final_state = result.final_state
            
            # Amplify the amplitude of the final state
            # (measurement collapses toward this state)
            weight = 0.1  # Per-loop contribution
            for i in range(8):
                if i == final_state:
                    # Constructive interference
                    amplitudes[i] += complex(weight, 0)
                else:
                    # Destructive interference (slight)
                    amplitudes[i] -= complex(weight / 7, 0)
        
        # Normalize
        total_prob = sum(abs(a)**2 for a in amplitudes.values())
        if total_prob > 0:
            self.superposition_amplitudes = {
                i: a / math.sqrt(total_prob) for i, a in amplitudes.items()
            }
        else:
            self.superposition_amplitudes = amplitudes
        
        # Total Berry phase
        for result in self.holonomy_results.values():
            if not result.is_trivial:
                # Each nontrivial holonomy contributes π (for single flips)
                # or π/2 (for combined flips)
                weight = sum(result.holonomy.value)
                self.berry_phase_total += weight * math.pi
        
        # Geometric entropy (uncertainty in final state)
        probs = [abs(a)**2 for a in self.superposition_amplitudes.values()]
        self.geometric_entropy = -sum(p * math.log2(p) for p in probs if p > 0)
    
    def measure_final_state(self) -> Tuple[int, float]:
        """
        Collapse the superposition to a definite octahedral state.
        
        Returns:
            (state_index, probability) via Born's rule
        """
        import random
        
        probs = [abs(a)**2 for a in self.superposition_amplitudes.values()]
        total = sum(probs)
        normalized = [p / total for p in probs]
        
        r = random.random()
        cumulative = 0
        for i, prob in enumerate(normalized):
            cumulative += prob
            if r <= cumulative:
                return i, prob
        
        return 7, normalized[-1]
    
    def diagnose(self) -> str:
        """Human-readable quantum fiber bundle diagnosis."""
        if not self.holonomy_results:
            return "No holonomy computed. Bundle state is a pure |base_point⟩ state."
        
        n_loops = len(self.holonomy_results)
        n_nontrivial = sum(1 for r in self.holonomy_results.values() if not r.is_trivial)
        
        diagnosis = (
            f"Base state: |{self.base_point_state}⟩. "
            f"{n_loops} loops computed, {n_nontrivial} nontrivial holonomies. "
        )
        
        if self.geometric_entropy < 0.5:
            diagnosis += (
                f"Low geometric entropy ({self.geometric_entropy:.2f} bits): "
                f"final state is nearly pure. Holonomies are consistent—"
                f"the bundle has a well-defined topological phase."
            )
        elif self.geometric_entropy < 2.0:
            diagnosis += (
                f"Moderate geometric entropy ({self.geometric_entropy:.2f} bits): "
                f"multiple final states are probable. The bundle has some "
                f"topological uncertainty—different loops give different holonomies."
            )
        else:
            diagnosis += (
                f"High geometric entropy ({self.geometric_entropy:.2f} bits): "
                f"final state is highly uncertain. The bundle has strong "
                f"curvature singularities—fabrication history matters greatly. "
                f"This is the regime for topological quantum memory."
            )
        
        if self.berry_phase_total > 0:
            diagnosis += (
                f" Total Berry phase: {self.berry_phase_total:.2f} rad "
                f"({self.berry_phase_total / math.pi:.1f}π)."
            )
        
        return diagnosis


# ======================================================================
# Unified geometric encoding pipeline
# ======================================================================

def encode_fiber_bundle_topology(
    holonomy_results: Dict[str, HolonomyResult],
    holonomy_group: Set[BitFlip] = None,
) -> Dict[str, Any]:
    """
    Complete pipeline: compute holonomy → encode as binary → add
    ternary + quantum interpretations.
    
    This is the unified entry point for geometric fiber encoding.
    
    Args:
        holonomy_results: Dict from regime names to HolonomyResult
        holonomy_group: Set of BitFlip elements (or None to derive)
    
    Returns:
        Dict with binary encoding, ternary classification,
        quantum state, and full diagnostic
    """
    # Binary encoding
    encoder = GeometricFiberEncoder()
    encoder.from_fiber_bundle(holonomy_results, holonomy_group)
    binary = encoder.to_binary()
    
    # Ternary classification
    ternary_state = classify_holonomy_ternary(holonomy_results)
    
    # Quantum fiber state
    all_states = set()
    for result in holonomy_results.values():
        all_states.add(result.initial_state)
    
    base_state = list(all_states)[0] if all_states else 0
    quantum_state = QuantumFiberBundleState(
        base_point_state=base_state,
        holonomy_results=holonomy_results
    )
    
    # Decode binary for verification
    decoded = encoder.decode_holonomy_from_binary(binary)
    
    return {
        "binary_encoding": binary,
        "bit_length": len(binary),
        "ternary_classification": ternary_state.name,
        "ternary_meaning": ternary_state.physical_meaning,
        "quantum_state": {
            "base_state": base_state,
            "berry_phase": quantum_state.berry_phase_total,
            "geometric_entropy": quantum_state.geometric_entropy,
            "diagnosis": quantum_state.diagnose()
        },
        "decoded_holonomy": decoded,
        "bundle_topology": encoder.bundle_topology,
        "nontrivial_loops": sum(1 for r in holonomy_results.values() if not r.is_trivial),
        "total_loops": len(holonomy_results),
    }


# ======================================================================
# Demo
# ======================================================================

if __name__ == "__main__":
    print("=" * 70)
    print("GEOMETRIC FIBER BUNDLE ENCODER")
    print("Octahedral Z₂³ Torsor → 39-bit Binary + Ternary + Quantum")
    print("=" * 70)
    
    # Generate test holonomy data
    print("\n1. Generating test loops around phase boundaries...")
    
    loop_metallic = generate_loop_around_metallic_breakdown(n_points=40)
    loop_quantum = generate_loop_around_quantum_boundary(n_points=40)
    loop_defect = generate_loop_around_defect_singularity(n_points=40)
    
    # Compute holonomies
    print("\n2. Computing holonomies for start state 0...")
    
    results = {}
    results["metallic_breakdown"] = compute_monodromy(0, loop_metallic)
    results["quantum_boundary"] = compute_monodromy(0, loop_quantum)
    results["defect_boundary"] = compute_monodromy(0, loop_defect)
    
    # Print raw results
    for name, result in results.items():
        flag = "◈ NONTRIVIAL" if not result.is_trivial else "  trivial"
        print(f"  {name:20s}: {result.holonomy.name:12s} [{flag}]")
    
    # Encode
    print("\n3. Encoding fiber bundle topology...")
    encoded = encode_fiber_bundle_topology(results)
    
    print(f"\n  Binary encoding ({encoded['bit_length']} bits):")
    # Print in Section groups
    binary = encoded['binary_encoding']
    print(f"    Section A (holonomy group):  {binary[0:18]}")
    print(f"    Section B (transport):       {binary[18:27]}")
    print(f"    Section C (invariants):      {binary[27:33]}")
    print(f"    Section D (geometric phase): {binary[33:39]}")
    
    print(f"\n  Ternary classification: {encoded['ternary_classification']}")
    print(f"    {encoded['ternary_meaning']}")
    
    print(f"\n  Quantum fiber state:")
    qs = encoded['quantum_state']
    print(f"    Berry phase: {qs['berry_phase']:.2f} rad")
    print(f"    Geometric entropy: {qs['geometric_entropy']:.2f} bits")
    print(f"    {qs['diagnosis']}")
    
    print(f"\n  Bundle topology: {encoded['bundle_topology']}")
    print(f"  Nontrivial loops: {encoded['nontrivial_loops']}/{encoded['total_loops']}")
    
    # Verify decode
    print(f"\n4. Verifying binary decode...")
    decoded = encoded['decoded_holonomy']
    print(f"  Bundle trivial: {decoded['bundle_trivial']}")
    print(f"  Group order: {decoded['group_order']}")
    print(f"  Topology class: {decoded['topology_class']}")
    
    # Show all start states
    print(f"\n5. Holonomy for all start states (0-7) around quantum boundary:")
    for start in range(8):
        result = compute_monodromy(start, loop_quantum)
        flag = "◈" if not result.is_trivial else " "
        print(f"    [{flag}] State {start} → State {result.final_state}: {result.holonomy.name}")
    
    print("\n" + "=" * 70)
    print("""
    The geometric fiber encoder captures what no single-domain encoder can:
    
    - The RELATIONSHIP between measurements made along different paths
    - Whether fabrication history matters (nontrivial holonomy = YES)
    - The holonomy group structure (subgroup of Z₂³)
    - The Berry phase acquired by parallel transport
    
    This is the meta-encoder: it encodes the topology of encoding itself.
    """)
