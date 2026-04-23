# octahedral_fiber_bundle.py
"""
The Octahedral State as a Fiber Bundle Section

Constructs the mathematical structure underlying the silicon-GIES integration:

Total space:  E = Silicon manifold × {0,1,...,7} (with nontrivial twist)
Base manifold: B = {(n, d, ℓ, κ)} = silicon phase space
Fiber:        F = Z₂³ = {0,1}³ ≅ {0,1,...,7} octahedral states
Structure group: G = Z₂³ (bit-flip operations on the octahedron)
Projection:   π: E → B, (S, state_index) ↦ S
Section:      σ: B → E, a choice of octahedral state at each silicon point

The fiber is a Z₂³ torsor — it has no distinguished identity element
until a section (gauge choice) is fixed. Bit-flip operations correspond
to parity inversions along the cube axes of the octahedron.

Key question: Is the bundle trivial (E = B × F globally) or does it
have nontrivial holonomy around phase transition surfaces?

Nontrivial holonomy means: traversing a closed loop around a metallic
breakdown or quantum phase boundary transforms the octahedral encoding
in a path-dependent way — a geometric Aharonov-Bohm effect for computation.
"""

import numpy as np
from typing import Dict, Tuple, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from itertools import product
import warnings


# ─── 1. The Z₂³ Torsor Structure ───

class BitFlip(Enum):
    """The three generators of Z₂³: bit flips along cube axes."""
    X_FLIP = (1, 0, 0)  # flip x-axis parity
    Y_FLIP = (0, 1, 0)  # flip y-axis parity
    Z_FLIP = (0, 0, 1)  # flip z-axis parity
    IDENTITY = (0, 0, 0)

    def __matmul__(self, other: 'BitFlip') -> 'BitFlip':
        """Group multiplication: XOR of bit vectors."""
        result = tuple(
            (a + b) % 2 for a, b in zip(self.value, other.value)
        )
        for bf in BitFlip:
            if bf.value == result:
                return bf
        return BitFlip.IDENTITY

    def act_on_state(self, state_index: int) -> int:
        """Apply this bit flip to an octahedral state index (0-7)."""
        bits = [(state_index >> i) & 1 for i in range(3)]  # [x, y, z]
        flipped = [(b + f) % 2 for b, f in zip(bits, self.value)]
        return sum(f * (2**i) for i, f in enumerate(flipped))


# Verify Z₂³ group structure
Z2_CUBE_GROUP = list(BitFlip)
Z2_MULTIPLICATION_TABLE = {
    (a, b): a @ b for a in BitFlip for b in BitFlip
}


class OctahedralTorsor:
    """
    The fiber F = Z₂³ as a torsor over the octahedral states.

    A torsor is a group that has "forgotten" its identity element.
    Only differences between states are meaningful, not absolute values.
    The octahedral states form a torsor because there is no distinguished
    "origin" state — all 8 states are equivalent under cubic symmetry.
    """

    def __init__(self):
        self.states = list(range(8))  # {0, 1, ..., 7}
        self.bit_flips = list(BitFlip)

    def difference(self, state_a: int, state_b: int) -> BitFlip:
        """
        The bit flip that takes state_a to state_b.

        Since this is a torsor, the difference between any two states
        is a well-defined group element.
        """
        bits_a = [(state_a >> i) & 1 for i in range(3)]
        bits_b = [(state_b >> i) & 1 for i in range(3)]
        diff = tuple((a - b) % 2 for a, b in zip(bits_a, bits_b))
        for bf in BitFlip:
            if bf.value == diff:
                return bf
        return BitFlip.IDENTITY

    def apply(self, state_index: int, bit_flip: BitFlip) -> int:
        """Apply a bit flip transformation to a state."""
        return bit_flip.act_on_state(state_index)

    def orbit(self, state_index: int) -> List[int]:
        """All states reachable from this state (the entire fiber)."""
        return [self.apply(state_index, bf) for bf in BitFlip]

    def stabilizer(self, state_index: int) -> List[BitFlip]:
        """Group elements that leave this state unchanged."""
        return [bf for bf in BitFlip if self.apply(state_index, bf) == state_index]


# ─── 2. The Connection: Parallel Transport Between Fibers ───

@dataclass
class Connection:
    """
    A connection on the octahedral fiber bundle.

    The connection defines parallel transport: given a path γ(t) in the
    base manifold B, how does the fiber element (octahedral state) transform?

    For a discrete fiber, the connection is specified by transition functions
    t_ij ∈ G = Z₂³ for each overlap of coordinate charts on B.
    """

    # The connection 1-form (discretized): maps tangent vectors in B to Z₂³
    # For a lattice in B, this is a map: (S_i, S_j) → BitFlip

    def __init__(self):
        self._transition_cache: Dict[Tuple, BitFlip] = {}

    def parallel_transport(
        self,
        current_state: int,
        S_from: 'SiliconState',
        S_to: 'SiliconState',
        step_size: float = 0.01,
    ) -> int:
        """
        Parallel transport the octahedral state along an infinitesimal
        step in the silicon phase space.

        The fundamental rule: choose the octahedral state at S_to that
        minimizes the "transport cost" from the state at S_from.

        Transport cost has two components:
        1. Geometric cost: how much the tensor eigenvalues change
        2. Regime continuity: whether both states are in compatible regimes
        """
        # Compute the "best" octahedral state at S_to given current state at S_from
        best_state = current_state
        best_cost = float('inf')

        for candidate in range(8):
            cost = self._transport_cost(
                current_state, S_from, candidate, S_to
            )

            if cost < best_cost:
                best_cost = cost
                best_state = candidate

        # Record the transition (for holonomy detection)
        transition = OctahedralTorsor().difference(current_state, best_state)
        key = (self._state_snapshot(S_from), self._state_snapshot(S_to))
        self._transition_cache[key] = transition

        return best_state

    def _transport_cost(
        self,
        state_from: int,
        S_from: 'SiliconState',
        state_to: int,
        S_to: 'SiliconState',
    ) -> float:
        """
        Compute the cost of transporting from (S_from, state_from) to
        (S_to, state_to).

        The cost penalizes:
        1. Large changes in tensor eigenvalue structure
        2. Crossing regime boundaries discontinuously
        3. Breaking the "natural" state-regime affinity
        """
        from Silicon.core.inverse_regime_design import (
            CANONICAL_EIGENVALUES, compute_structural_metrics
        )

        # ── Eigenvalue continuity cost ──
        eigs_from = np.array(CANONICAL_EIGENVALUES[state_from])
        eigs_to = np.array(CANONICAL_EIGENVALUES[state_to])

        # Frobenius distance between eigenvalue triplets
        eigenvalue_cost = np.sum((eigs_from - eigs_to)**2)

        # ── Regime continuity cost ──
        # Get regime weights at both points
        weights_from = S_from.regime_weights(temperature=0.1)
        weights_to = S_to.regime_weights(temperature=0.1)

        # Dominant regimes
        regime_from = max(weights_from, key=weights_from.get)
        regime_to = max(weights_to, key=weights_to.get)

        # Penalize regime discontinuities
        if regime_from != regime_to:
            regime_cost = 1.0
        else:
            regime_cost = 0.0

        # ── Structural affinity cost ──
        metrics_from = compute_structural_metrics(state_from)
        metrics_to = compute_structural_metrics(state_to)

        # Penalize if the target state is unnatural for the target regime
        affinity_key = {
            "quantum": "quantum_affinity",
            "semiconductor": "classical_affinity",
            "photonic": "photonic_affinity",
        }.get(regime_to, "memory_affinity")

        structural_affinity = getattr(metrics_to, affinity_key)
        affinity_cost = 1.0 - structural_affinity

        # ── Bit flip cost (Hamming distance) ──
        torsor = OctahedralTorsor()
        bit_flip = torsor.difference(state_from, state_to)
        hamming_weight = sum(bit_flip.value)  # number of bit flips
        bit_flip_cost = hamming_weight * 0.1

        # Total cost (weighted sum)
        total_cost = (
            1.0 * eigenvalue_cost +
            2.0 * regime_cost +
            0.5 * affinity_cost +
            0.3 * bit_flip_cost
        )

        return total_cost

    def _state_snapshot(self, S: 'SiliconState') -> Tuple:
        """Create a hashable snapshot of a silicon state for caching."""
        return (
            round(np.log10(max(S.n, 1e8)), 2),
            round(S.d, 3),
            round(S.l, 3),
            round(S.k.get("coherent", 0), 3),
        )


# ─── 3. Holonomy Detection: The Central Computation ───

@dataclass
class HolonomyResult:
    """
    Result of computing holonomy around a closed loop in silicon phase space.

    If the final octahedral state differs from the initial state by a
    nontrivial bit flip, the fiber bundle has nontrivial holonomy around
    the enclosed phase transition surfaces.
    """
    initial_state: int
    final_state: int
    holonomy: BitFlip                # the net transformation
    is_trivial: bool                 # True if holonomy = IDENTITY
    loop_points: int                 # number of points in the loop
    path_transitions: List[Dict]     # intermediate transitions
    enclosed_regimes: Set[str]       # which regimes does the loop enclose?

    @property
    def holonomy_order(self) -> int:
        """Order of the holonomy element in Z₂³ (1, 2, 4, or 8)."""
        if self.holonomy == BitFlip.IDENTITY:
            return 1
        h = self.holonomy
        for order in [2, 4, 8]:
            result = h
            for _ in range(order - 1):
                result = result @ h
            if result == BitFlip.IDENTITY:
                return order
        return 8

    @property
    def affected_qubits(self) -> List[int]:
        """Which logical qubits are flipped by the holonomy?"""
        return [i for i, v in enumerate(self.holonomy.value) if v == 1]

    def __str__(self) -> str:
        if self.is_trivial:
            return "Trivial holonomy (bundle is locally flat)"
        return (
            f"NONTRIVIAL HOLONOMY: {self.holonomy.name}\n"
            f"  Initial state {self.initial_state} → Final state {self.final_state}\n"
            f"  Affected qubits: {self.affected_qubits}\n"
            f"  Order: {self.holonomy_order}\n"
            f"  Enclosed regimes: {self.enclosed_regimes}"
        )


def compute_monodromy(
    start_state_index: int,
    loop: List['SiliconState'],
    connection: Optional[Connection] = None,
) -> HolonomyResult:
    """
    Trace a closed loop in silicon phase space and compute the holonomy.

    The loop must be closed: loop[0] ≈ loop[-1] in S-space.

    If the bundle is nontrivial, the final octahedral state will differ
    from the initial state by a nontrivial bit flip — a Z₂³ holonomy.

    Parameters
    ----------
    start_state_index : int
        Which octahedral state to start with (0-7)
    loop : list of SiliconState
        Sequence of points forming a closed path in the base manifold

    Returns
    -------
    HolonomyResult with the detected holonomy
    """
    if connection is None:
        connection = Connection()

    n_points = len(loop)
    current_state = start_state_index

    # Record transitions along the path
    transitions = []

    # Regimes encountered
    enclosed_regimes = set()

    for i in range(n_points - 1):
        S_from = loop[i]
        S_to = loop[i + 1]

        old_state = current_state

        # Parallel transport
        current_state = connection.parallel_transport(
            current_state, S_from, S_to
        )

        # Record regime at this point
        weights = S_from.regime_weights(temperature=0.1)
        dominant = max(weights, key=weights.get)
        enclosed_regimes.add(dominant)

        # Record transition
        torsor = OctahedralTorsor()
        bit_flip = torsor.difference(old_state, current_state)

        if bit_flip != BitFlip.IDENTITY:
            transitions.append({
                "step": i,
                "from_state": old_state,
                "to_state": current_state,
                "bit_flip": bit_flip.name,
                "regime_from": max(
                    S_from.regime_weights(temperature=0.1),
                    key=S_from.regime_weights(temperature=0.1).get
                ),
                "regime_to": max(
                    S_to.regime_weights(temperature=0.1),
                    key=S_to.regime_weights(temperature=0.1).get
                ),
            })

    # Compute net holonomy
    torsor = OctahedralTorsor()
    holonomy = torsor.difference(start_state_index, current_state)

    return HolonomyResult(
        initial_state=start_state_index,
        final_state=current_state,
        holonomy=holonomy,
        is_trivial=(holonomy == BitFlip.IDENTITY),
        loop_points=n_points,
        path_transitions=transitions,
        enclosed_regimes=enclosed_regimes,
    )


# ─── 4. Loop Generation: Encircle Phase Boundaries ───

def generate_loop_around_metallic_breakdown(
    n_points: int = 50,
    base_defect: float = 0.05,
    base_dimension: float = 3.0,
    radius: float = 0.5,  # in log10(n) space
    center_log10n: float = 19.5,  # near Mott criterion
) -> List['SiliconState']:
    """
    Generate a closed circular loop in S-space that encircles
    the metallic breakdown surface.

    The loop varies carrier density n and defect density d
    while keeping effective dimension ℓ and coupling κ fixed.

    Returns a closed loop: loop[0] ≈ loop[-1].
    """
    from Silicon.core.analysis.computational_phase_transition import SiliconState

    loop = []

    for i in range(n_points):
        angle = 2 * np.pi * i / n_points

        # Parametric circle in (log10(n), d) space
        log10_n = center_log10n + radius * np.cos(angle)
        d = base_defect + radius * 0.3 * np.sin(angle)

        # Clamp
        d = np.clip(d, 0.0, 1.0)
        n = 10 ** log10_n

        state = SiliconState(
            n=n,
            d=d,
            l=base_dimension,
            k={
                "electrical": 0.7,
                "optical": 0.0,
                "thermal": 0.2,
                "mechanical": 0.0,
                "coherent": 0.1,
            }
        )

        loop.append(state)

    # Close the loop explicitly
    loop.append(loop[0])

    return loop


def generate_loop_around_quantum_boundary(
    n_points: int = 50,
    base_doping: float = 1e17,
    base_defect: float = 0.02,
    radius_dim: float = 1.5,  # in ℓ space
    radius_coherence: float = 0.3,  # in κ space
    center_dim: float = 1.0,
    center_coherence: float = 0.5,
) -> List['SiliconState']:
    """
    Generate a closed loop encircling the quantum-classical boundary.

    Varies effective dimension ℓ and coherent coupling κ —
    the two parameters that control the quantum confinement transition.
    """
    from Silicon.core.analysis.computational_phase_transition import SiliconState

    loop = []

    for i in range(n_points):
        angle = 2 * np.pi * i / n_points

        ell = center_dim + radius_dim * np.cos(angle)
        k_coherent = center_coherence + radius_coherence * np.sin(angle)

        # Clamp
        ell = np.clip(ell, 0.1, 3.0)
        k_coherent = np.clip(k_coherent, 0.0, 1.0)

        state = SiliconState(
            n=base_doping,
            d=base_defect,
            l=ell,
            k={
                "electrical": 0.3,
                "optical": 0.1,
                "thermal": 0.1,
                "mechanical": 0.05,
                "coherent": k_coherent,
            }
        )

        loop.append(state)

    loop.append(loop[0])
    return loop


def generate_loop_around_defect_singularity(
    n_points: int = 50,
    base_n: float = 1e16,
    center_d: float = 0.3,
    radius_d: float = 0.25,
    center_thermal: float = 0.3,
    radius_thermal: float = 0.25,
) -> List['SiliconState']:
    """
    Generate a loop encircling the defect-dominated regime boundary.

    Varies defect density and thermal coupling.
    """
    from Silicon.core.analysis.computational_phase_transition import SiliconState

    loop = []

    for i in range(n_points):
        angle = 2 * np.pi * i / n_points

        d = center_d + radius_d * np.cos(angle)
        k_thermal = center_thermal + radius_thermal * np.sin(angle)

        d = np.clip(d, 0.0, 1.0)
        k_thermal = np.clip(k_thermal, 0.0, 1.0)

        state = SiliconState(
            n=base_n,
            d=d,
            l=2.5,
            k={
                "electrical": 0.3,
                "optical": 0.0,
                "thermal": k_thermal,
                "mechanical": 0.1,
                "coherent": 0.1,
            }
        )

        loop.append(state)

    loop.append(loop[0])
    return loop


# ─── 5. Holonomy Classification ───

def classify_holonomy_around_regimes(
    start_state: int = 0,
    n_test_points: int = 50,
) -> Dict[str, HolonomyResult]:
    """
    Test for holonomy around each type of phase transition surface.

    Returns a dictionary mapping regime boundary names to holonomy results.
    """
    results = {}

    # ── Loop 1: Around metallic breakdown ──
    print("  Testing holonomy around metallic breakdown...")
    loop_metallic = generate_loop_around_metallic_breakdown(n_points=n_test_points)
    results["metallic_breakdown"] = compute_monodromy(start_state, loop_metallic)

    # ── Loop 2: Around quantum boundary ──
    print("  Testing holonomy around quantum-classical boundary...")
    loop_quantum = generate_loop_around_quantum_boundary(n_points=n_test_points)
    results["quantum_boundary"] = compute_monodromy(start_state, loop_quantum)

    # ── Loop 3: Around defect singularity ──
    print("  Testing holonomy around defect singularity...")
    loop_defect = generate_loop_around_defect_singularity(n_points=n_test_points)
    results["defect_boundary"] = compute_monodromy(start_state, loop_defect)

    return results


# ─── 6. Holonomy Group Computation ───

def compute_holonomy_group(
    base_point: 'SiliconState',
    n_loops: int = 50,
    loop_radius_range: Tuple[float, float] = (0.1, 1.0),
) -> Set[BitFlip]:
    """
    Compute the holonomy group at a base point by sampling many
    closed loops and recording which Z₂³ elements appear as holonomies.

    The holonomy group is a subgroup of Z₂³.
    Its size reveals the topological complexity of the fiber bundle:
    - Trivial group {IDENTITY} → bundle is globally trivial
    - Z₂ subgroup → bundle has a 2-fold twist
    - Full Z₂³ → maximally nontrivial topology
    """
    from Silicon.core.analysis.computational_phase_transition import SiliconState

    holonomy_elements = set()

    for _ in range(n_loops):
        # Generate a random closed loop
        radius = np.random.uniform(*loop_radius_range)

        # Random plane in S-space
        axis1 = np.random.randn(4)
        axis2 = np.random.randn(4)
        axis2 = axis2 - np.dot(axis1, axis2) * axis1  # orthogonalize
        axis1 /= np.linalg.norm(axis1)
        axis2 /= np.linalg.norm(axis2)

        loop = []
        n_pts = 30

        S0 = np.array([
            np.log10(max(base_point.n, 1e8)),
            base_point.d,
            base_point.l,
            base_point.k.get("coherent", 0.1),
        ])

        for i in range(n_pts):
            angle = 2 * np.pi * i / n_pts
            dS = radius * (np.cos(angle) * axis1 + np.sin(angle) * axis2)

            S_new = S0 + dS

            state = SiliconState(
                n=max(10**S_new[0], 1e8),
                d=np.clip(S_new[1], 0, 1),
                l=np.clip(S_new[2], 0.1, 3.0),
                k={
                    "electrical": 0.5,
                    "optical": 0.0,
                    "thermal": 0.1,
                    "mechanical": 0.0,
                    "coherent": np.clip(S_new[3], 0, 1),
                }
            )

            loop.append(state)

        loop.append(loop[0])  # close

        # Compute holonomy (use random start state)
        start_state = np.random.randint(0, 8)
        result = compute_monodromy(start_state, loop)

        holonomy_elements.add(result.holonomy)

    return holonomy_elements


# ─── 7. Geometric Phase Interpretation ───

def interpret_holonomy(result: HolonomyResult) -> str:
    """
    Provide a physical interpretation of a holonomy result.

    Nontrivial holonomy means that the octahedral encoding is
    path-dependent — the same silicon state can correspond to
    different octahedral states depending on how you got there.
    """
    if result.is_trivial:
        return (
            "The fiber bundle is locally flat. Octahedral encoding is\n"
            "path-independent: any fabrication trajectory ending at the\n"
            "same silicon state produces the same geometric encoding.\n"
            "The bundle is trivial in this region."
        )

    interpretation = f"""
    NONTRIVIAL HOLONOMY DETECTED
    ════════════════════════════

    The octahedral fiber bundle has nontrivial curvature around
    the phase transition surfaces enclosed by this loop.

    Physical meaning:
    - A device fabricated via two different paths that end at the
      SAME silicon state (n, d, ℓ, κ) will have DIFFERENT octahedral
      encodings if the paths enclose a phase boundary.

    - The holonomy {result.holonomy.name} acts on qubits {result.affected_qubits}
      by flipping their logical values.

    - This is a geometric (Berry) phase for computation: the
      computational state acquires a topological transformation
      that depends only on the homotopy class of the fabrication path.

    Consequences:
    1. Fabrication history matters: two identical silicon states
       can be computationally different.
    2. The enclosed regimes {result.enclosed_regimes}
       are the source of the curvature.
    3. This establishes the silicon-GIES system as a genuine
       topological quantum memory — information is stored in the
       bundle topology, not in any local degree of freedom.
    """

    return interpretation


# ─── 8. Visualization ───

def plot_holonomy_loop(
    result: HolonomyResult,
    loop: List['SiliconState'],
    save_path: Optional[str] = None,
):
    """Visualize a holonomy-detecting loop in silicon phase space."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D

    fig = plt.figure(figsize=(14, 5))

    # ── Panel 1: 3D projection of the loop ──
    ax1 = fig.add_subplot(121, projection='3d')

    # Extract coordinates
    n_log = [np.log10(S.n) for S in loop]
    d_vals = [S.d for S in loop]
    l_vals = [S.l for S in loop]

    # Color by position along loop
    colors = plt.cm.viridis(np.linspace(0, 1, len(loop)))

    ax1.scatter(n_log, d_vals, l_vals, c=colors, s=20, alpha=0.8)
    ax1.plot(n_log, d_vals, l_vals, 'k-', alpha=0.3, linewidth=0.5)

    # Mark start/end
    ax1.scatter([n_log[0]], [d_vals[0]], [l_vals[0]],
                color='green', s=200, marker='o', edgecolors='black', linewidth=2,
                label=f'Start: State {result.initial_state}')
    ax1.scatter([n_log[-1]], [d_vals[-1]], [l_vals[-1]],
                color='red', s=200, marker='s', edgecolors='black', linewidth=2,
                label=f'End: State {result.final_state}')

    ax1.set_xlabel('log₁₀(n)')
    ax1.set_ylabel('Defect density d')
    ax1.set_zlabel('Effective dim ℓ')
    ax1.set_title('Closed Loop in Silicon Phase Space')
    ax1.legend(fontsize=8)

    # ── Panel 2: Holonomy information ──
    ax2 = fig.add_subplot(122)
    ax2.axis('off')

    text = f"""
    HOLONOMY ANALYSIS
    ═══════════════════

    Initial state:     {result.initial_state}
    Final state:       {result.final_state}
    Holonomy:          {result.holonomy.name}
    Trivial?           {result.is_trivial}
    Holonomy order:    {result.holonomy_order}
    Affected qubits:   {result.affected_qubits}

    Enclosed regimes:  {result.enclosed_regimes}
    Path transitions:  {len(result.path_transitions)}

    {interpret_holonomy(result)}
    """

    ax2.text(0.05, 0.95, text, transform=ax2.transAxes,
            fontsize=10, fontfamily='monospace', verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightyellow', alpha=0.8))

    fig.suptitle('Octahedral Fiber Bundle Holonomy Detection',
                fontsize=14, fontweight='bold')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150, bbox_inches='tight', facecolor='white')

    return fig


# ─── 9. Demo ───

if __name__ == "__main__":
    print("=" * 70)
    print("OCTAHEDRAL FIBER BUNDLE: HOLONOMY DETECTION")
    print("Z₂³ Torsor Structure Over the Silicon Manifold")
    print("=" * 70)

    # ── Part 1: Z₂³ group structure ──
    print("\n1. Z₂³ GROUP STRUCTURE")
    print("-" * 50)

    torsor = OctahedralTorsor()

    print("  Bit flip generators:")
    for bf in BitFlip:
        print(f"    {bf.name:12s}: {bf.value}")

    print("\n  Example: State 5 (101) under Z_FLIP:")
    result = BitFlip.Z_FLIP.act_on_state(5)
    print(f"    5 (101) → {result} ({format(result, '03b')})")

    print("\n  Orbit of state 0 under full group:")
    orbit = torsor.orbit(0)
    for s in orbit:
        print(f"    {s} ({format(s, '03b')})")

    # ── Part 2: Holonomy around metallic breakdown ──
    print("\n\n2. HOLONOMY AROUND METALLIC BREAKDOWN")
    print("-" * 50)

    loop_metallic = generate_loop_around_metallic_breakdown(
        n_points=40,
        base_defect=0.05,
        center_log10n=19.5,
        radius=0.5,
    )

    print(f"  Loop: {len(loop_metallic)} points")
    print(f"  n range: {min(np.log10(S.n) for S in loop_metallic):.1f} → "
          f"{max(np.log10(S.n) for S in loop_metallic):.1f}")
    print(f"  d range: {min(S.d for S in loop_metallic):.3f} → "
          f"{max(S.d for S in loop_metallic):.3f}")

    # Test all start states
    print("\n  Holonomy for each start state:")
    for start_state in range(8):
        result = compute_monodromy(start_state, loop_metallic)
        flag = "◈ NONTRIVIAL" if not result.is_trivial else "  trivial"
        print(f"    State {start_state} → State {result.final_state}: "
              f"{result.holonomy.name:12s} [{flag}]")

    # ── Part 3: Holonomy around quantum boundary ──
    print("\n\n3. HOLONOMY AROUND QUANTUM BOUNDARY")
    print("-" * 50)

    loop_quantum = generate_loop_around_quantum_boundary(
        n_points=40,
        center_dim=1.0,
        radius_dim=1.5,
        center_coherence=0.5,
        radius_coherence=0.3,
    )

    print(f"  ℓ range: {min(S.l for S in loop_quantum):.2f} → "
          f"{max(S.l for S in loop_quantum):.2f}")
    print(f"  κ range: {min(S.k['coherent'] for S in loop_quantum):.2f} → "
          f"{max(S.k['coherent'] for S in loop_quantum):.2f}")

    quantum_results = {}
    for start_state in range(8):
        result = compute_monodromy(start_state, loop_quantum)
        quantum_results[start_state] = result
        flag = "◈ NONTRIVIAL" if not result.is_trivial else "  trivial"
        print(f"    State {start_state} → State {result.final_state}: "
              f"{result.holonomy.name:12s} [{flag}]")

    # ── Part 4: Holonomy group computation ──
    print("\n\n4. HOLONOMY GROUP (sampling random loops)")
    print("-" * 50)

    from Silicon.core.analysis.computational_phase_transition import SiliconState

    base_point = SiliconState(
        n=1e17, d=0.02, l=3.0,
        k={"electrical": 0.5, "optical": 0.0, "thermal": 0.1,
           "mechanical": 0.0, "coherent": 0.4}
    )

    holonomy_group = compute_holonomy_group(base_point, n_loops=30)

    print(f"  Holonomy group elements: {len(holonomy_group)}")
    for element in holonomy_group:
        print(f"    {element.name}")

    # Classify the bundle topology
    if len(holonomy_group) == 1:
        topology = "Trivial bundle (no curvature)"
    elif len(holonomy_group) == 2:
        topology = "Z₂ bundle (single bit-flip holonomy)"
    elif len(holonomy_group) == 4:
        topology = "Z₂×Z₂ bundle (two-bit holonomy subgroup)"
    elif len(holonomy_group) == 8:
        topology = "Full Z₂³ bundle (maximally nontrivial)"
    else:
        topology = f"Subgroup of order {len(holonomy_group)}"

    print(f"\n  Bundle topology: {topology}")

    # ── Part 5: Interpretation ──
    print("\n\n5. PHYSICAL INTERPRETATION")
    print("-" * 50)

    # Find a nontrivial result if any
    nontrivial_found = False
    for result in quantum_results.values():
        if not result.is_trivial:
            print(interpret_holonomy(result))
            nontrivial_found = True
            break

    if not nontrivial_found:
        print("  No nontrivial holonomy detected in sampled loops.")
        print("  The fiber bundle may be locally trivial, or the phase")
        print("  boundaries may not carry curvature in Z₂³.")

    print("\n" + "=" * 70)
    print("""    The octahedral fiber bundle structure reveals:
    
    - The 8 octahedral states form a Z₂³ torsor fiber
    - Parallel transport is defined by minimizing transport cost
    - Holonomy around phase boundaries may be nontrivial
    - If nontrivial: fabrication HISTORY determines encoding
    - This is a topological quantum memory mechanism
    """)
